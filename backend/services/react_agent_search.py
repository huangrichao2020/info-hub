async def _search_stock_info_impl(query: str) -> dict:
    """搜索股票相关信息（基于 Jina Reader，Agent-Reach 底层能力）

    搜索范围限制：
    - 只允许股票代码、名称、板块关键词
    - 禁止搜索非股票相关内容
    """
    import re
    import httpx

    # 安全过滤：只允许股票相关关键词
    stock_keywords = [
        # 通用金融词汇
        '股票', '股', '板块', '概念', '行情', '分析', '财报',
        '业绩', '涨停', '跌停', '龙虎榜', '资金', '主力',
        '北向', '南向', 'ETF', '基金', '债券', '期货',
        'A 股', '港股', '美股', '纳斯达克', '道琼斯',
        '上证', '深证', '创业板', '科创', '北交',
        # 常见公司/股票名称
        '茅台', '腾讯', '阿里', '百度', '京东', '拼多多',
        '平安', '招商', '工商', '建设', '农业', '中国',
        '万科', '保利', '碧桂园', '恒大',
        '宁德', '比亚迪', '宁德时代', '隆基',
        '中芯', '华为', '小米', '字节',
        # 行业板块
        '新能源', '芯片', '半导体', '医药', '白酒',
        '军工', '航天', '航空', '银行', '保险',
        '券商', '地产', '物业', '物流', '电商',
        '汽车', '电池', '光伏', '风电', '储能',
        'AI', '人工智能', '大数据', '云计算',
        '消费', '零售', '餐饮', '旅游',
    ]

    # 检查是否包含股票代码（6 位数字）
    has_code = bool(re.search(r'\d{6}', query))
    # 检查是否包含股票关键词
    has_stock_kw = any(kw in query for kw in stock_keywords)

    if not (has_code or has_stock_kw):
        return {
            "error": "搜索内容必须与股票相关（股票代码、名称、板块等）。我只能提供 A 股/港股/美股市场相关信息。"
        }

    # 构建搜索 URL：用 Jina Reader 搜索雪球个股页面
    # Jina Reader 是 Agent-Reach 底层使用的网页读取服务
    search_url = f"https://s.jina.ai/{query}"

    try:
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            response = await client.get(search_url, headers={
                "User-Agent": "Mozilla/5.0",
                "X-With-Generated-Alt": "true",
            })
            response.raise_for_status()
            content = response.text[:3000]  # 限制返回长度
            return {
                "query": query,
                "source": "jina_reader",
                "content": content,
            }
    except Exception as exc:
        return {"error": f"搜索失败：{exc}"}
