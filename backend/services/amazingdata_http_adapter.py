"""AmazingData HTTP Adapter - 通过 SSH 隧道调用 Windows 上的 AmazingData Market Data API。
轻量级，不依赖 AmazingData SDK，适配 2GB 服务器环境。
"""
from __future__ import annotations

import os
import requests
from datetime import datetime, timedelta
from typing import Any, Optional

# 配置
AMAZINGDATA_HTTP_URL = os.environ.get(
    "AMAZINGDATA_HTTP_URL",
    "http://127.0.0.1:17713"
)
REQUEST_TIMEOUT = int(os.environ.get("AMAZINGDATA_HTTP_TIMEOUT", "10"))


class AmazingDataHTTPClient:
    """HTTP 客户端封装"""
    
    def __init__(self, base_url: str = AMAZINGDATA_HTTP_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.timeout = REQUEST_TIMEOUT
    
    def health_check(self) -> dict:
        """健康检查"""
        try:
            resp = self.session.get(f"{self.base_url}/health", timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_calendar(self, market: str = "SH") -> dict:
        """获取交易日历"""
        resp = self.session.get(
            f"{self.base_url}/api/v1/calendar",
            params={"market": market},
            timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    
    def get_kline(
        self,
        code: str,
        begin_date: str,
        end_date: str,
        interval: str = "day"
    ) -> dict:
        """
        获取 K 线数据
        
        Args:
            code: 股票代码 (e.g., "000001.SZ")
            begin_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            interval: 周期 (day/week/month/min1/min5/min15/min30/min60)
        """
        params = {
            "code": code,
            "begin_date": begin_date,
            "end_date": end_date,
        }
        
        # 根据 interval 选择端点
        if interval == "day":
            endpoint = "/api/v1/trading/daily-bars"
        else:
            endpoint = "/api/v1/kline"
            params["interval"] = interval
        
        resp = self.session.get(
            f"{self.base_url}{endpoint}",
            params=params,
            timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    
    def get_snapshot(self, codes: list[str]) -> dict:
        """获取实时快照"""
        resp = self.session.get(
            f"{self.base_url}/api/v1/snapshots",
            params={"codes": ",".join(codes)},
            timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    
    def get_code_list(self, limit: int = 100) -> dict:
        """获取代码列表"""
        resp = self.session.get(
            f"{self.base_url}/api/v1/code-list",
            params={"limit": limit},
            timeout=30  # 可能返回大量数据
        )
        resp.raise_for_status()
        return resp.json()


# 全局单例
_client: Optional[AmazingDataHTTPClient] = None


def get_client() -> AmazingDataHTTPClient:
    global _client
    if _client is None:
        _client = AmazingDataHTTPClient()
    return _client


def is_available() -> bool:
    """检查服务是否可用"""
    try:
        result = get_client().health_check()
        return result.get("status") == "ok"
    except Exception:
        return False
