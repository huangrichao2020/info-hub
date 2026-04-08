# Info-Hub 全网资讯中枢

集成自媒体爆文方法论 + 股票交易方法论的桌面端全能资讯项目。后端定时采集全网数据，前端 8 大板块一站式呈现。

---

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | React 19 + Vite + TailwindCSS v4 + Zustand + framer-motion |
| 后端 | Python FastAPI + APScheduler + httpx |
| 数据库 | SQLite（info-hub 独立库 + 读取 uwillberich 现有库）|
| LLM | Qwen (DashScope OpenAI-compatible API) |

---

## 快速启动

### 1. 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install httpx[socks]  # 如果有 SOCKS 代理

uvicorn main:app --reload --port 8000
```

后端启动后会自动：
- 初始化 SQLite 数据库 (`~/.info-hub/info_hub.sqlite3`)
- 启动定时采集任务（热搜 15 分钟、新闻 30 分钟）
- 注册 8 个路由模块

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173（如被占用会自动换端口）

### 3. 环境依赖

后端通过 `config.py` 自动加载以下文件，无需手动配置：

| 文件 | 内容 | 必须 |
|---|---|---|
| `~/.uwillberich/runtime.env` | EM_API_KEY, MX_APIKEY (东方财富/妙想) | 板块 5/6/7 需要 |
| `~/Desktop/uwillberich/.qwen-env` | DASHSCOPE_API_KEY | 板块 4/8 + 翻译需要 |
| `~/Desktop/uwillberich/skill/uwillberich/scripts/` | Python 模块 (通过 sys.path 引用) | 板块 5/6/7 需要 |

---

## 8 大板块

| # | 板块 | 路由前缀 | 数据来源 | 热度排序 |
|---|---|---|---|---|
| 1 | AI 新闻 | `/api/ai-news` | Google AI RSS + 36kr RSS | 关键词+来源+时效算分 |
| 2 | 自媒体爆款 | `/api/viral` | 六平台热搜交叉分析 | 跨平台综合热度 |
| 3 | 热门话题 | `/api/trending` | 百度/微博/知乎/头条/抖音/小红书 | 原生热度值 |
| 4 | 一键写文 | `/api/article` | Qwen LLM 生成 (SSE) | — |
| 5 | 财经新闻 | `/api/fin-news` | 东方财富/新浪/财联社/同花顺 | 关键词+来源+时效算分 |
| 6 | 热门板块 | `/api/sectors` | 东方财富行情 API | 涨跌幅 |
| 7 | 涨停分析 | `/api/zt` | 妙想 (MX) API | 换手率→人气分 |
| 8 | 复盘报告 | `/api/review` | 腾讯行情 + Qwen LLM (SSE) | — |

---

## 六平台热搜采集

| 平台 | API 端点 | 认证 | 风险 |
|---|---|---|---|
| 百度 | `top.baidu.com/board` (HTML 内嵌 JSON) | 无 | 稳定 |
| 微博 | `weibo.com/ajax/side/hotSearch` | Referer 头 | 稳定 |
| 知乎 | `zhihu.com/api/v3/feed/topstory/hot-list-web` | 无 | 稳定 |
| 头条 | `toutiao.com/hot-event/hot-board/` | 无 | 稳定 |
| 抖音 | `aweme.snssdk.com/aweme/v1/hot/search/list/` | UA=okhttp3 | 稳定 (Mobile SDK) |
| 小红书 | `edith.xiaohongshu.com/api/sns/v1/search/hot_list` | 硬编码 shield 令牌 | **可能失效** |

**小红书降级方案**：如果 shield 令牌失效，改用公共代理 `https://60s-api.viki.moe/v2/rednote`

---

## 热度排序算法

所有内容按热度排序，算法因数据源不同而异：

### 热搜/爆款（原生热度值）
直接使用各平台返回的 heat_score / hot_value，跨平台比较时按归一化处理。

### AI 新闻（计算热度 1-1000）
```
热度 = (关键词命中分 + 标题特征分) × 来源权重 × 时效衰减
```
- **关键词**：OpenAI=40, GPT/Claude=35, DeepSeek=40, 大模型=25, 芯片=20 等
- **来源权重**：36kr=1.3, google-ai=1.0
- **时效衰减**：半衰期 12 小时，指数衰减

### 财经新闻（计算热度 1-1000）
```
热度 = (关键词命中分 + 标题特征分) × 来源权重 × 时效衰减
```
- **关键词**：涨停=40, 央行/降息/加息=30, 利好/利空=25, AI/芯片=20 等
- **来源权重**：财联社=1.3, 东方财富=1.1
- **时效衰减**：半衰期 8 小时（财经时效更强）

### 涨停分析（换手率→人气分）
- 换手率 × 5，上限 100（20% 换手率 = 满分）

---

## 自动翻译

AI 新闻采集时自动检测非中文内容（中文字符占比 ≤ 30%），调用 Qwen 翻译为中文后再入库。翻译只执行一次，不浪费 token。

---

## 数据刷新机制

| 层 | 策略 |
|---|---|
| 后端定时采集 | 热搜 15 分钟、AI 新闻 30 分钟、财经新闻 30 分钟 |
| 前端自动刷新 | 早 9 点 / 晚 9 点各自动刷一次 |
| 前端手动刷新 | Header 右上角刷新按钮，点击后当前板块重新拉数据 |
| 切换 Tab | 自动重新拉取该板块数据 |

---

## API 概览

### 资讯类
```
GET  /api/ai-news              # AI新闻 (?keyword=&page=1)
GET  /api/trending             # 六平台热搜 (?platform=baidu|weibo|zhihu|toutiao|douyin|xiaohongshu)
GET  /api/viral/trending       # 跨平台爆款
GET  /api/fin-news             # 财经新闻 (?source=&keyword=&hours=24)
```

### 行情类
```
GET  /api/sectors/indices      # 大盘指数快照
GET  /api/sectors/movers       # 板块涨跌 (?limit=10&rising=true)
GET  /api/sectors/flow         # 资金流向
GET  /api/zt/today             # 今日涨停
GET  /api/zt/lianban           # 连板股
```

### LLM 生成类 (SSE 流式)
```
POST /api/article/generate     # 一键生成文章 {topic, platform, word_count?}
POST /api/review/generate      # 一键复盘报告 {portfolio: [{code,name,shares,cost_price}]}
```

### 系统
```
GET  /api/health               # 健康检查
POST /api/*/refresh            # 手动触发采集
```

---

## 目录结构

```
info-hub/
├── backend/
│   ├── main.py                # FastAPI 入口
│   ├── config.py              # 配置 + sys.path 注入
│   ├── database.py            # SQLite 建表
│   ├── scheduler.py           # APScheduler 定时任务
│   ├── requirements.txt
│   ├── llm/
│   │   ├── qwen_client.py     # DashScope API (同步+流式)
│   │   ├── prompts.py         # 文章/复盘提示词模板
│   │   └── methodology.py     # 爆文+交易方法论
│   ├── routers/               # 8 个路由模块
│   └── services/              # 6 个业务服务
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api/client.ts      # Axios + /api 代理
│   │   ├── stores/appStore.ts # Zustand (section, theme, refresh)
│   │   ├── hooks/             # useStreamResponse
│   │   ├── types/
│   │   └── components/
│   │       ├── layout/        # AppShell, Sidebar, Header
│   │       ├── common/        # NewsCard, LoadingSkeleton
│   │       └── [8 panels]     # 各板块组件
│   ├── package.json
│   └── vite.config.ts         # Vite + TailwindCSS + /api 代理
```

---

## 数据库

### info-hub 独立库 (`~/.info-hub/info_hub.sqlite3`)
- `ai_news` — AI 新闻（含 heat_score）
- `trending_topics` — 六平台热搜
- `viral_content` — 跨平台爆款
- `generated_articles` — LLM 生成的文章
- `review_reports` — LLM 生成的复盘报告
- `scheduler_state` — 定时任务状态

### uwillberich 只读库
- `~/.uwillberich/news-collector/news.sqlite3` — 财经新闻（读取+计算热度）

---

## 两大方法论

### 自媒体爆文方法论
**爆款 = 情绪钩子 × 信息密度 × 平台适配**
- 微信：22 字标题 + 情绪词，2000-3500 字，总分总
- 头条：30 字标题 + 关键词前置，1500-2500 字，SEO 导向
- 知乎：问题式标题，2000-5000 字，论证导向

### 股票交易方法论
**复盘框架：环境 → 技术 → 消息 → 板块 → 评估 → 策略**
- 市场环境 → 个股技术 → 消息驱动 → 持仓评估 → 操作建议

---

## 已知问题 & 后续

- [ ] 小红书 shield 令牌可能失效，需监控
- [ ] 财经新闻 DB 需先运行 uwillberich 的 news_collector 采集一次
- [ ] 可增加更多 RSS 源提升 AI 新闻覆盖面
- [ ] 热度算法可引入用户点击反馈进一步优化
