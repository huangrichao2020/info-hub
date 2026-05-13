"""
Service for incremental dump of A-share data.
Uses Baostock.
"""
import socket
socket.setdefaulttimeout(15)
import baostock as bs
import pandas as pd
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("info-hub.stock_engine.dump")

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "historical"

def is_stock(code):
    return code[:5] in ('sh.60', 'sz.00', 'sz.30')

def run_incremental_dump(start_date: str = "2021-01-01", limit: int = None):
    """Run the dump process."""
    logger.info(f"Starting stock dump from {start_date}")
    os.makedirs(DATA_DIR, exist_ok=True)

    lg = bs.login()
    if lg.error_code != '0':
        logger.error(f"Login failed: {lg.error_msg}")
        return {"status": "error", "msg": lg.error_msg}

    rs = bs.query_stock_basic()
    if rs.error_code != '0':
        bs.logout()
        return {"status": "error", "msg": rs.error_msg}

    rows = []
    while rs.next():
        rows.append(rs.get_row_data())
    df_list = pd.DataFrame(rows, columns=rs.fields)
    
    stocks = [c for c in df_list['code'] if is_stock(c)]
    if limit:
        stocks = stocks[:limit]
        
    logger.info(f"Found {len(stocks)} stocks.")
    
    today = datetime.now().strftime("%Y-%m-%d")
    success = 0
    fail = 0
    skipped = 0
    
    for i, code in enumerate(stocks):
        file_path = os.path.join(DATA_DIR, f"{code.replace('.', '_')}.parquet")
        
        try:
            # Check last date
            start_for_code = start_date
            if os.path.exists(file_path):
                try:
                    df_old = pd.read_parquet(file_path, columns=['date'])
                    if not df_old.empty:
                        last_date = str(df_old['date'].max())[:10]
                        if last_date >= today:
                            skipped += 1
                            continue
                        start_dt = datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)
                        start_for_code = start_dt.strftime("%Y-%m-%d")
                except Exception:
                    pass # Fall back to full dump

            # Fetch
            rs_hist = bs.query_history_k_data_plus(
                code,
                fields="date,open,high,low,close,volume,amount,turn",
                start_date=start_for_code,
                end_date=today,
                frequency="d",
                adjustflag="2"
            )
            
            hist_list = []
            if rs_hist.error_code == '0':
                while rs_hist.next():
                    hist_list.append(rs_hist.get_row_data())
            
            if hist_list:
                df_new = pd.DataFrame(hist_list, columns=rs_hist.fields)
                for col in ['open', 'high', 'low', 'close', 'volume', 'amount', 'turn']:
                    df_new[col] = pd.to_numeric(df_new[col], errors='coerce')
                df_new['date'] = pd.to_datetime(df_new['date'])
                
                if os.path.exists(file_path) and 'df_old' in locals():
                    df_final = pd.concat([df_old, df_new]).drop_duplicates(subset=['date']).sort_values('date')
                else:
                    df_final = df_new
                
                df_final.to_parquet(file_path, index=False)
                success += 1
            elif os.path.exists(file_path):
                # File exists but no new data — already up to date
                skipped += 1
            
            if (i + 1) % 500 == 0:
                logger.info(f"Progress: {i+1}/{len(stocks)}")
                
        except Exception as e:
            logger.error(f"Error for {code}: {e}")
            fail += 1
            
    bs.logout()
    logger.info(f"Dump complete. Success: {success}, Skipped: {skipped}, Failed: {fail}")
    return {"status": "ok", "success": success, "skipped": skipped, "failed": fail}
