#!/usr/bin/env python3
"""
投资日历 + 中线方向股票池生成器
数据源: AKShare (东方财富)
输出: Markdown 报告 + JSON 股票池
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import json
import os

OUTPUT_DIR = "/root/info-hub/backend/data/invest_calendar"
os.makedirs(OUTPUT_DIR, exist_ok=True)

today = datetime.now()
today_str = today.strftime('%Y-%m-%d')
report_lines = []

def add(text):
    report_lines.append(text)

add(f"# 📅 A股投资日历 + 中线方向报告\n")
add(f"**日期**: {today_str} | **数据源**: AKShare/东方财富\n")

# ========== 1. 投资日历 ==========
add("## 一、近期投资日历事件\n")

# 1a. 大宗交易活跃
add("### 1.1 今日大宗交易\n")
try:
    df_dzjy = ak.stock_dzjy_mrmx(symbol='A股', start_date=today.strftime('%Y%m%d'), end_date=today.strftime('%Y%m%d'))
    if not df_dzjy.empty:
        df_dzjy['成交额'] = pd.to_numeric(df_dzjy['成交额'], errors='coerce')
        # 按股票汇总
        dzjy_summary = df_dzjy.groupby('证券简称').agg({
            '成交额': 'sum',
            '成交价': 'mean',
            '折溢率': 'mean',
            '证券代码': 'first'
        }).sort_values('成交额', ascending=False).head(10)
        for name, row in dzjy_summary.iterrows():
            amt = row['成交额'] / 1e4 if pd.notna(row['成交额']) else 0
            add(f"- **{name}**({row['证券代码']}): 成交 {amt:.0f} 万，成交价 {row['成交价']:.2f}，折溢率 {row['折溢率']:.2f}%")
    else:
        add("今日无大宗交易数据")
except Exception as e:
    add(f"获取失败: {e}")

add("")

# 1b. 机构龙虎榜
add("### 1.2 今日机构净买入 TOP10\n")
try:
    df_lhb = ak.stock_lhb_jgmmtj_em(start_date=today.strftime('%Y%m%d'), end_date=today.strftime('%Y%m%d'))
    if not df_lhb.empty:
        df_lhb['机构买入净额'] = pd.to_numeric(df_lhb['机构买入净额'], errors='coerce')
        df_lhb['涨跌幅'] = pd.to_numeric(df_lhb['涨跌幅'], errors='coerce')
        df_lhb['买方机构数'] = pd.to_numeric(df_lhb['买方机构数'], errors='coerce')
        top = df_lhb.sort_values('机构买入净额', ascending=False).head(10)
        for _, row in top.iterrows():
            net = row['机构买入净额'] / 1e4 if pd.notna(row['机构买入净额']) else 0
            add(f"- **{row['名称']}**({row['代码']}): 涨幅 {row['涨跌幅']:.1f}%，{int(row['买方机构数'])} 家机构买入，净额 {net:.0f} 万")
    else:
        add("今日无机构龙虎榜数据")
except Exception as e:
    add(f"获取失败: {e}")

add("")

# ========== 2. 中线方向股票池 ==========
add("## 二、中线方向股票池\n")

pool = []

# 2a. 高股息方向
add("### 2.1 高股息方向 (股息率 > 3%)\n")
try:
    df_fhps = ak.stock_fhps_em(date='20260331')
    df_fhps['现金分红-股息率'] = pd.to_numeric(df_fhps['现金分红-股息率'], errors='coerce')
    df_fhps['净利润同比增长'] = pd.to_numeric(df_fhps['净利润同比增长'], errors='coerce')
    high_div = df_fhps[df_fhps['现金分红-股息率'] > 0.02].sort_values('现金分红-股息率', ascending=False).head(10)
    
    for _, row in high_div.iterrows():
        div_rate = row['现金分红-股息率'] * 100
        profit_chg = row['净利润同比增长']
        pool.append({
            '方向': '高股息',
            '代码': str(row['代码']).zfill(6),
            '名称': row['名称'],
            '股息率': f"{div_rate:.2f}%",
            '净利增长': f"{profit_chg:.1f}%",
            '逻辑': f"股息率{div_rate:.1f}% | {row['方案进度']}"
        })
        add(f"- **{row['名称']}**({row['代码']}): 股息率 {div_rate:.2f}%，净利增长 {profit_chg:.1f}%，{row['方案进度']}")
    
    if high_div.empty:
        add("当前无股息率>2%标的")
except Exception as e:
    add(f"获取失败: {e}")

add("")

# 2b. 业绩高增长方向
add("### 2.2 业绩高增长 (净利+50% 且 毛利>30%)\n")
try:
    df_yjbb = ak.stock_yjbb_em(date='20260331')
    df_yjbb['净利润-同比增长'] = pd.to_numeric(df_yjbb['净利润-同比增长'], errors='coerce')
    df_yjbb['销售毛利率'] = pd.to_numeric(df_yjbb['销售毛利率'], errors='coerce')
    df_yjbb['营业总收入-同比增长'] = pd.to_numeric(df_yjbb['营业总收入-同比增长'], errors='coerce')
    
    # 过滤掉ST股和异常值
    df_clean = df_yjbb[~df_yjbb['股票简称'].str.contains('ST', na=False)]
    high_growth = df_clean[
        (df_clean['净利润-同比增长'] > 50) & 
        (df_clean['净利润-同比增长'] < 10000) &  # 过滤异常基数
        (df_clean['销售毛利率'] > 30)
    ].sort_values('净利润-同比增长', ascending=False).head(10)
    
    for _, row in high_growth.iterrows():
        pool.append({
            '方向': '业绩高增长',
            '代码': str(row['股票代码']).zfill(6),
            '名称': row['股票简称'],
            '股息率': '-',
            '净利增长': f"{row['净利润-同比增长']:.1f}%",
            '逻辑': f"净利+{row['净利润-同比增长']:.0f}% | 毛利{row['销售毛利率']:.1f}% | 营收+{row['营业总收入-同比增长']:.1f}%"
        })
        add(f"- **{row['股票简称']}**({row['股票代码']}): 净利+{row['净利润-同比增长']:.0f}%，毛利 {row['销售毛利率']:.1f}%，营收+{row['营业总收入-同比增长']:.1f}%")
    
    if high_growth.empty:
        add("无符合条件标的")
except Exception as e:
    add(f"获取失败: {e}")

add("")

# 2c. 机构资金方向
add("### 2.3 机构资金持续买入 (近3日龙虎榜)\n")
try:
    end = today.strftime('%Y%m%d')
    start = (today - timedelta(days=3)).strftime('%Y%m%d')
    df_lhb3 = ak.stock_lhb_jgmmtj_em(start_date=start, end_date=end)
    if not df_lhb3.empty:
        df_lhb3['机构买入净额'] = pd.to_numeric(df_lhb3['机构买入净额'], errors='coerce')
        inst_sum = df_lhb3.groupby(['代码','名称']).agg({
            '机构买入净额': 'sum',
            '买方机构数': 'mean'
        }).sort_values('机构买入净额', ascending=False).head(8)
        
        for (code, name), row in inst_sum.iterrows():
            net = row['机构买入净额'] / 1e4 if pd.notna(row['机构买入净额']) else 0
            pool.append({
                '方向': '机构资金',
                '代码': str(code).zfill(6),
                '名称': name,
                '股息率': '-',
                '净利增长': '-',
                '逻辑': f"近3日机构净买 {net:.0f} 万"
            })
            add(f"- **{name}**({code}): 近3日机构净买 {net:.0f} 万")
    else:
        add("近3日无机构龙虎榜数据")
except Exception as e:
    add(f"获取失败: {e}")

add("")

# ========== 3. 操作建议 ==========
add("## 三、中线操作建议\n")
add("1. **高股息**: 适合底仓配置，关注方案进度为'股东大会通过'的标的，等待股权登记日催化\n")
add("2. **业绩高增长**: 一季报刚披露完毕，关注中报延续性；净利增速>100%且营收同步增长的优先\n")
add("3. **机构资金**: 龙虎榜机构净买入连续2日以上的标的，中线趋势更可靠\n")
add("4. **风控**: 中线标的需结合周线趋势，跌破20周均线减仓\n")

# 保存报告
report = "\n".join(report_lines)
report_path = os.path.join(OUTPUT_DIR, f"report_{today_str}.md")
with open(report_path, 'w') as f:
    f.write(report)

# 保存股票池 JSON
if pool:
    df_pool = pd.DataFrame(pool)
    pool_path = os.path.join(OUTPUT_DIR, f"mid_pool_{today_str}.json")
    df_pool.to_json(pool_path, orient='records', force_ascii=False, indent=2)
    print(f"✅ 报告: {report_path}")
    print(f"✅ 股票池: {pool_path} ({len(pool)} 只)")
else:
    print("⚠️ 未筛选到标的")

print(report)
