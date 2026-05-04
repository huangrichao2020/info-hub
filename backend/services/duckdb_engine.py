"""
DuckDB 查询引擎 — 全市场扫描加速层。
直接读取 Parquet 文件，替代逐文件 pandas 循环。
零迁移成本，与现有 LocalStockCache 共存。

灵感来源：龙马量化之路 第四章「数据是一切的基础」
"""
import os
import glob
import duckdb
import pandas as pd
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger("info-hub.duckdb_engine")


class DuckDBEngine:
    """全市场 DuckDB 查询引擎。"""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self._conn = None

    def _get_conn(self) -> duckdb.DuckDBPyConnection:
        """懒加载连接。"""
        if self._conn is None:
            self._conn = duckdb.connect()
            # 注册 parquet 目录，方便 SQL 引用
            self._conn.execute(f"""
                CREATE OR REPLACE VIEW market_data AS
                SELECT 
                    replace(regexp_extract(filename, '[^/]+[.]parquet$'), '.parquet', '') as symbol_raw,
                    date, open, high, low, close, volume, amount, turn
                FROM read_parquet('{self.data_dir}/*.parquet', filename=true)
            """)
        return self._conn

    def scan_all(self, where: str = "1=1", 
                 columns: str = "symbol_raw, date, open, high, low, close, volume",
                 order_by: str = "date DESC",
                 limit: int = None) -> pd.DataFrame:
        """全市场扫描。
        
        Args:
            where: WHERE 子句（不含 WHERE 关键字）
            columns: SELECT 列
            order_by: 排序
            limit: 限制行数
        """
        sql = f"SELECT {columns} FROM market_data WHERE {where}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit:
            sql += f" LIMIT {limit}"
        return self._get_conn().execute(sql).df()

    def scan_with_last_day(self, where: str = "1=1",
                           columns: str = "symbol_raw, date, open, high, low, close, volume") -> pd.DataFrame:
        """全市场扫描，只取每只股票最新一天的数据。
        适用于扫描选股场景（只需要最新信号）。
        """
        sql = f"""
            WITH ranked AS (
                SELECT {columns},
                       ROW_NUMBER() OVER (PARTITION BY symbol_raw ORDER BY date DESC) as rn
                FROM market_data
                WHERE {where}
            )
            SELECT * EXCLUDE (rn) FROM ranked WHERE rn = 1
            ORDER BY date DESC
        """
        return self._get_conn().execute(sql).df()

    def scan_ma25_up(self) -> pd.DataFrame:
        """扫描 MA25 向上的股票。"""
        sql = """
            WITH ranked AS (
                SELECT symbol_raw, date, close,
                       ROW_NUMBER() OVER (PARTITION BY symbol_raw ORDER BY date DESC) as rn
                FROM market_data
            ),
            latest AS (
                SELECT * FROM ranked WHERE rn <= 26
            ),
            ma_calc AS (
                SELECT symbol_raw, date, close,
                       AVG(close) OVER (PARTITION BY symbol_raw ORDER BY date 
                                       ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) as ma25
                FROM latest
            ),
            ma_final AS (
                SELECT symbol_raw, date, close, ma25,
                       LAG(ma25) OVER (PARTITION BY symbol_raw ORDER BY date) as ma25_prev
                FROM ma_calc
                WHERE date = (SELECT MAX(date) FROM ma_calc mc2 WHERE mc2.symbol_raw = ma_calc.symbol_raw)
            )
            SELECT 
                symbol_raw as symbol,
                date,
                round(close, 2) as close,
                round(ma25, 2) as ma25,
                round(ma25_prev, 2) as ma25_prev,
                CASE WHEN ma25 > ma25_prev THEN 'up' ELSE 'down' END as trend
            FROM ma_final
            WHERE ma25 > ma25_prev
            ORDER BY date DESC
        """
        return self._get_conn().execute(sql).df()

    def scan_volume_up(self, min_ratio: float = 1.5) -> pd.DataFrame:
        """扫描放量上涨：收盘涨 + 量比 >= min_ratio。"""
        sql = f"""
            WITH ranked AS (
                SELECT symbol_raw, date, close, volume,
                       ROW_NUMBER() OVER (PARTITION BY symbol_raw ORDER BY date DESC) as rn
                FROM market_data
            ),
            latest AS (
                SELECT * FROM ranked WHERE rn <= 26
            ),
            vol_calc AS (
                SELECT symbol_raw, date, close, volume,
                       AVG(volume) OVER (PARTITION BY symbol_raw ORDER BY date 
                                        ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) as vol_ma25,
                       LAG(close) OVER (PARTITION BY symbol_raw ORDER BY date) as prev_close
                FROM latest
                WHERE date = (SELECT MAX(date) FROM latest l2 WHERE l2.symbol_raw = latest.symbol_raw)
            )
            SELECT 
                symbol_raw as symbol,
                date,
                round(close, 2) as close,
                round(prev_close, 2) as prev_close,
                volume,
                round(vol_ma25, 0) as vol_ma25,
                round(volume / NULLIF(vol_ma25, 0), 2) as volume_ratio,
                round((close - prev_close) / NULLIF(prev_close, 0) * 100, 2) as close_change_pct,
                '放量上涨' as signal
            FROM vol_calc
            WHERE close > prev_close
              AND volume / NULLIF(vol_ma25, 0) >= {min_ratio}
            ORDER BY volume_ratio DESC
        """
        return self._get_conn().execute(sql).df()

    def scan_volume_divergence(self) -> pd.DataFrame:
        """扫描量价背离：股价在高位但缩量上涨。"""
        sql = """
            WITH ranked AS (
                SELECT symbol_raw, date, close, volume,
                       ROW_NUMBER() OVER (PARTITION BY symbol_raw ORDER BY date DESC) as rn
                FROM market_data
            ),
            latest AS (
                SELECT * FROM ranked WHERE rn <= 60
            ),
            vol_calc AS (
                SELECT symbol_raw, date, close, volume,
                       AVG(volume) OVER (PARTITION BY symbol_raw ORDER BY date 
                                        ROWS BETWEEN 24 PRECEDING AND CURRENT ROW) as vol_ma25,
                       LAG(close) OVER (PARTITION BY symbol_raw ORDER BY date) as prev_close,
                       MAX(close) OVER (PARTITION BY symbol_raw 
                                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as high_20d
                FROM latest
                WHERE date = (SELECT MAX(date) FROM latest l2 WHERE l2.symbol_raw = latest.symbol_raw)
            )
            SELECT 
                symbol_raw as symbol,
                date,
                round(close, 2) as close,
                round(high_20d, 2) as high_20d,
                round((close - prev_close) / NULLIF(prev_close, 0) * 100, 2) as close_change_pct,
                round(volume / NULLIF(vol_ma25, 0), 2) as volume_ratio,
                '量价背离' as signal
            FROM vol_calc
            WHERE close > prev_close
              AND volume / NULLIF(vol_ma25, 0) < 0.8
              AND close >= high_20d * 0.97
            ORDER BY close_change_pct DESC
        """
        return self._get_conn().execute(sql).df()

    def query(self, sql: str) -> pd.DataFrame:
        """执行任意 SQL 查询。"""
        return self._get_conn().execute(sql).df()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


# 全局单例
_engine: Optional[DuckDBEngine] = None


def get_engine(data_dir: str = None) -> DuckDBEngine:
    """获取 DuckDB 引擎单例。"""
    global _engine
    if _engine is None:
        if data_dir is None:
            data_dir = str(Path(__file__).parent.parent.parent / "data" / "historical")
        _engine = DuckDBEngine(data_dir)
    return _engine
