#!/usr/bin/env python3
"""每日自动更新市场数据缓存（近3个月全市场行情）"""
import baostock as bs
import pandas as pd
import json, time, os, sys
from datetime import datetime, timedelta

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BACKEND_DIR, 'data', 'cache')
CACHE_PATH = os.path.join(CACHE_DIR, 'full_market_3m.json')

os.makedirs(CACHE_DIR, exist_ok=True)

end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

print(f"[{datetime.now().isoformat()}] 开始更新市场数据缓存: {start_date} ~ {end_date}")

bs.login()

# 1. 获取行业分类
rs = bs.query_stock_industry()
industry_df = rs.get_data()[['code','code_name','industry']]
industry_df = industry_df[industry_df['industry'] != '']
print(f"行业分类股票: {len(industry_df)}")

# 2. 批量拉取行情
all_results = []
skipped = 0
start = time.time()

for idx, row in industry_df.iterrows():
    code = row['code']
    try:
        rs = bs.query_history_k_data_plus(
            code, "date,close,volume,turn",
            start_date=start_date, end_date=end_date,
            frequency="d", adjustflag="2"
        )
        df = rs.get_data()
        df = df.replace('', pd.NA)
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df = df.dropna(subset=['close'])
        if len(df) < 2:
            skipped += 1
            continue
        df = df.sort_values('date')
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        if prev['close'] <= 0:
            skipped += 1
            continue
        
        change_pct = round((latest['close'] - prev['close']) / prev['close'] * 100, 2)
        
        all_results.append({
            'code': code,
            'name': row['code_name'],
            'industry': row['industry'],
            'close': round(float(latest['close']), 2),
            'volume': round(float(latest.get('volume', 0) or 0), 0),
            'turn': round(float(latest.get('turn', 0) or 0), 2),
            'change_pct': change_pct,
            'date': str(latest['date'])[:10],
        })
    except:
        skipped += 1
    
    if (idx+1) % 1000 == 0:
        print(f"  进度: {idx+1}/{len(industry_df)} 有效:{len(all_results)} ({time.time()-start:.0f}s)")

elapsed = time.time() - start
stock_df = pd.DataFrame(all_results)
print(f"拉取完成: {len(stock_df)}只有效, {skipped}只跳过, 耗时{elapsed:.0f}s")

if len(stock_df) == 0:
    print("ERROR: 无有效数据，跳过更新")
    sys.exit(1)

# 3. 板块排行
sector = stock_df.groupby('industry').agg(
    stock_count=('code','count'),
    avg_change=('change_pct','mean'),
    median_change=('change_pct','median'),
    up_count=('change_pct', lambda x: (x>0).sum()),
    down_count=('change_pct', lambda x: (x<0).sum()),
).reset_index()
sector = sector[sector['stock_count']>=3].sort_values('avg_change', ascending=False)

sector_records = []
for _, s in sector.iterrows():
    sector_records.append({
        'name': s['industry'],
        'stock_count': int(s['stock_count']),
        'avg_change': round(float(s['avg_change']), 2),
        'median_change': round(float(s['median_change']), 2),
        'up_count': int(s['up_count']),
        'down_count': int(s['down_count']),
    })

# 4. 涨停/跌停
zt = stock_df[stock_df['change_pct']>=9.9].sort_values('change_pct', ascending=False)
dt_list = stock_df[stock_df['change_pct']<=-9.9].sort_values('change_pct')

# 5. 市场统计
total_market = {
    'up_count': int(len(stock_df[stock_df['change_pct']>0])),
    'down_count': int(len(stock_df[stock_df['change_pct']<0])),
    'flat_count': int(len(stock_df[stock_df['change_pct']==0])),
    'avg_change': round(float(stock_df['change_pct'].mean()), 2),
}

# 6. 保存缓存
cache = {
    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'latest_date': stock_df['date'].mode().iloc[0],
    'total_stocks': len(stock_df),
    'sectors': sector_records,
    'zt_stocks': zt.to_dict('records'),
    'dt_stocks': dt_list.to_dict('records'),
    'market_stats': total_market,
    'all_stocks': stock_df.to_dict('records'),
}

with open(CACHE_PATH, 'w') as f:
    json.dump(cache, f, ensure_ascii=False, default=str)

print(f"\n缓存已保存: {CACHE_PATH} ({os.path.getsize(CACHE_PATH)/1024:.0f}KB)")
print(f"  板块: {len(sector_records)}, 涨停: {len(zt)}, 跌停: {len(dt_list)}")
print(f"  上涨: {total_market['up_count']} 下跌: {total_market['down_count']}")

bs.logout()
print("更新完成")
