# Info-Hub

`info-hub` 现在是一个 **定制版 `uwillberich` 交易工作台**，核心只做两件事：

- `交易复盘`
- `转强选股`

其余模块保留，但已经降级为证据层或内容层，不再主导交易判断。

## 当前定位1334

决策顺序固定为：

1. 市场分类
   - `主线市场 / 独立龙头市场 / 区间/防御市场`
2. 概率情景
   - `基准 / 乐观 / 风险`
3. 时间门纪律
   - `09:00 / 09:25 / 09:30-10:00 / 14:00`
4. 证据补强
   - 问财、新闻、板块、涨停、量价数据

四条铁律：

- 先定方法论，再调工具
- 数据为辅，逻辑为主
- 不因数据好看改变市场判断
- tool 与 `uwillberich` 冲突时，信 `uwillberich`¥¥##¥

## 核心能力

### 1. 交易复盘

- 输入持仓组合，按 `uwillberich` 输出复盘
- 输出市场分类、`基准/乐观/风险`、持仓建议、时间门纪律、`可做/避免`
- 支持历史复盘回看
- 支持本地持仓模板

前端入口：
- `交易中枢`
- `交易复盘`

后端接口：
- `POST /api/review/generate`
- `GET /api/review/history`
- `GET /api/review/history/{id}`

### 2. 转强作战台

- 盘前生成主板转强候选池
- 使用问财筛选 + `uwillberich` 方法论统一评估
- 候选分层：`buy / watch / avoid`
- 候选综合评分：竞价强度 + 承接 + 消息支撑 + 方法论结论
- 历史回看
- 次日验证闭环

前端入口：
- `交易中枢`
- `转强作战台`

后端接口：
- `GET /api/turn-strong`
- `POST /api/turn-strong/generate`
- `POST /api/turn-strong/refresh`
- `GET /api/turn-strong/history`
- `GET /api/turn-strong/history/list`
- `GET /api/turn-strong/validation`

## 技术栈

- 前端：React 19 + Vite + Zustand + framer-motion
- 后端：FastAPI + APScheduler + SQLite + httpx
- LLM：Qwen / DashScope
- 方法论来源：桌面 `uwillberich` 项目

## 依赖关系

`info-hub` 直接依赖桌面 `uwillberich` 项目：

- `~/Desktop/uwillberich/skill/uwillberich/scripts/`
- `~/Desktop/uwillberich/skill/uwillberich/knowledge/`
- `~/Desktop/uwillberich/.qwen-env`
- `~/.uwillberich/runtime.env`

关键环境变量：

- `DASHSCOPE_API_KEY`
- `EM_API_KEY`
- `IWENCAI_BASE_URL`
- `IWENCAI_API_KEY`

## 启动

### 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

默认访问：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000/api/health`

## 验证

### 后端测试

```bash
cd backend
./.venv/bin/python -m unittest \
  tests.test_turn_strong_service \
  tests.test_turn_strong_history \
  tests.test_turn_strong_validation \
  tests.test_quant_market_service \
  tests.test_uwillberich_prompts
```

### 前端构建

```bash
cd frontend
npm run build
```

## 目录

```text
info-hub/
├── backend/
│   ├── config.py
│   ├── database.py
│   ├── llm/
│   │   ├── prompts.py
│   │   ├── methodology.py
│   │   └── uwillberich.py
│   ├── routers/
│   │   ├── review_report.py
│   │   ├── turn_strong.py
│   │   └── quant_market.py
│   ├── services/
│   │   ├── turn_strong_service.py
│   │   ├── quant_market_service.py
│   │   └── market_service.py
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/dashboard/TradeDeskPanel.tsx
│       ├── components/review-report/ReviewPanel.tsx
│       ├── components/turn-strong/TurnStrongPanel.tsx
│       ├── components/layout/
│       ├── config/sections.ts
│       ├── hooks/useStreamResponse.ts
│       └── stores/appStore.ts
└── 交接手册.md
```

## 当前状态

已经完成：

- `uwillberich-first` 后端编排
- 双核心前端信息架构
- 复盘历史与模板
- 转强历史与次日验证
- 前端面板懒加载
- 转强高频历史接口短 TTL 缓存

当前已知项：

- 前端主包仍有 `500kB+` 告警，但不影响构建与使用
- 缓存是单进程内存缓存，适合当前本地/单实例场景
- 更多工程化工作应优先做部署和分包，而不是再扩功能面
