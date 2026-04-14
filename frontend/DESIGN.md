# Info-Hub Design System

> 设计哲学：交易工作台不是资讯门户，是决策工具。每一个像素都服务于判断。
> 灵感来源：Linear 的克制、Bloomberg 的密度、TradingView 的专业感

## 1. Visual Theme & Atmosphere

**设计哲学**：黑暗为主，浅色为辅。交易场景需要低干扰、高对比、长时间可视。
**情绪关键词**：专业、克制、密度优先、零装饰主义
**美学标签**：Dark-first、Data-dense、Functional minimalism

- 暗色模式是默认且主要的工作模式，承载 90% 使用场景
- 浅色模式不是简单的颜色翻转，而是暖色调（amber/cream），模拟纸张阅读感
- 拒绝花哨渐变、动画装饰——只有数据本身值得被强调
- 布局密度高于消费级应用，低于专业终端；目标是"一屏信息量最大化"

## 2. Color Palette & Roles

### 暗色主题（默认）

| 语义色名 | Hex 值 | 用途 |
|----------|--------|------|
| `--color-bg` | `#0a0e1a` | 页面底色，深空蓝 |
| `--color-surface` | `#111827` | 卡片/面板背景 |
| `--color-surface-elevated` | `#1e293b` | 弹出层/模态框背景 |
| `--color-border` | `#1e293b` | 分割线/边框 |
| `--color-border-hover` | `#334155` | hover 状态边框 |
| `--color-text` | `#f1f5f9` | 主文本 |
| `--color-text-secondary` | `#94a3b8` | 次要文本/标签 |
| `--color-text-tertiary` | `#64748b` | 弱化文本/时间戳 |
| `--color-accent` | `#38bdf8` | 主强调色（链接/激活态/图表线） |
| `--color-accent-dim` | `rgba(56,189,248,.12)` | 强调色半透明背景 |
| `--color-red` | `#ef4444` | 上涨（A股红涨绿跌） |
| `--color-red-dim` | `rgba(239,68,68,.12)` | 上涨标签背景 |
| `--color-green` | `#4ade80` | 下跌 |
| `--color-green-dim` | `rgba(74,222,128,.12)` | 下跌标签背景 |
| `--color-gold` | `#fbbf24` | 警告/重要提示 |
| `--color-gold-dim` | `rgba(251,191,36,.12)` | 警告背景 |
| `--color-orange` | `#fb923c` | 转强/关注 |
| `--color-orange-dim` | `rgba(251,146,60,.12)` | 转强标签背景 |
| `--color-purple` | `#a78bfa` | 缠论/技术分析 |
| `--color-purple-dim` | `rgba(167,139,250,.12)` | 缠论标签背景 |
| `--color-blue` | `#60a5fa` | 证据/新闻 |
| `--color-blue-dim` | `rgba(96,165,250,.12)` | 新闻标签背景 |

### 浅色主题

| 语义色名 | 值 | 说明 |
|----------|-----|------|
| `--color-bg` | `#f6f2e8` | 暖米色，模拟纸张 |
| `--color-surface` | `rgba(255,255,255,.88)` | 半透明白卡片 |
| `--color-surface-elevated` | `#ffffff` | 弹出层纯白 |
| `--color-border` | `rgba(31,41,55,.11)` | 淡灰边框 |
| `--color-border-hover` | `rgba(31,41,55,.22)` | hover 加深 |
| `--color-text` | `#1f2937` | 深灰文本 |
| `--color-text-secondary` | `#5b6472` | 中灰文本 |
| `--color-text-tertiary` | `#8b95a5` | 浅灰文本 |
| `--color-accent` | `#b45309` | 暖琥珀强调色 |
| `--color-accent-dim` | `rgba(180,83,9,.10)` | 强调背景 |
| `--color-red` | `#dc2626` | 上涨（加深以适应浅底） |
| `--color-red-dim` | `rgba(220,38,38,.10)` | 上涨背景 |
| `--color-green` | `#16a34a` | 下跌（加深） |
| `--color-green-dim` | `rgba(22,163,74,.10)` | 下跌背景 |
| `--color-gold` | `#d97706` | 警告（加深） |
| `--color-orange` | `#ea580c` | 转强（加深） |
| `--color-purple` | `#7c3aed` | 缠论（加深） |
| `--color-blue` | `#2563eb` | 新闻（加深） |

### 数据置信度标注（来自 graphify "诚实优于黑盒"）

| 语义色名 | 值 | 用途 |
|----------|-----|------|
| `--confidence-extracted` | `#4ade80` | 数据来自实际采集（绿色圆点） |
| `--confidence-inferred` | `#fbbf24` | 数据为推断/估算（黄色圆点） |
| `--confidence-ambiguous` | `#ef4444` | 数据存疑待查（红色圆点） |

## 3. Typography Rules

**字体族**：`system-ui, "PingFang SC", "Hiragino Sans GB", -apple-system, sans-serif`

### 字号层级（基于 1rem = 16px）

| 层级 | 字号 (rem) | 字重 | 行高 | 用途 |
|------|------------|------|------|------|
| `display` | 2.25 | 800 | 1.1 | 页面标题（极少使用） |
| `h1` | 1.68 | 700 | 1.2 | 模块标题 |
| `h2` | 1.36 | 700 | 1.25 | 区块标题 |
| `h3` | 1.15 | 600 | 1.3 | 卡片标题 |
| `body-lg` | 1 | 400 | 1.5 | 正文 |
| `body-sm` | 0.92 | 400 | 1.4 | 次要文本 |
| `body-xs` | 0.84 | 400 | 1.3 | 辅助文本 |
| `caption` | 0.76 | 500 | 1.2 | 标签/徽章 |
| `mono-sm` | 0.82 | 400 | 1.2 | 数据/数字（等宽） |

**字间距**：
- 标题：`letter-spacing: -0.03em`
- 正文：默认
- 数字/代码：`font-variant-numeric: tabular-nums`

**严禁**：在组件内随意定义 `em` 字号（如 `.68em`、`.72em`），必须使用上述语义层级。

## 4. Component Stylings

### 卡片（Card）

```css
基础卡片:
  background: var(--color-surface)
  border: 1px solid var(--color-border)
  border-radius: 12px
  padding: 16px

紧凑卡片:
  background: var(--color-surface)
  border: 1px solid var(--color-border)
  border-radius: 8px
  padding: 10px

高级卡片:
  background: rgba(15,23,42,.56)
  backdrop-filter: blur(8px)
  border: 1px solid rgba(148,163,184,.12)
  border-radius: 16px
  padding: 20px
```

### 按钮（Button）

```css
主按钮:
  background: var(--color-accent)
  color: var(--color-bg)
  border-radius: 8px
  padding: 8px 16px
  font-size: 0.92rem
  font-weight: 600

次按钮:
  background: var(--color-accent-dim)
  color: var(--color-accent)
  border: 1px solid transparent
  border-radius: 8px
  padding: 6px 12px
  font-size: 0.84rem

幽灵按钮:
  background: transparent
  color: var(--color-text-secondary)
  padding: 6px 10px
  border-radius: 6px

hover: borderColor 变为 var(--color-accent)
```

### 徽章（Badge）

```css
默认徽章:
  font-size: 0.76rem
  font-weight: 500
  padding: 2px 8px
  border-radius: 999px
  background: var(--color-accent-dim)
  color: var(--color-accent)

红色徽章: background: var(--color-red-dim), color: var(--color-red)
绿色徽章: background: var(--color-green-dim), color: var(--color-green)
金色徽章: background: var(--color-gold-dim), color: var(--color-gold)
```

### 输入框（Input）

```css
输入框:
  background: var(--color-surface)
  border: 1px solid var(--color-border)
  border-radius: 8px
  padding: 8px 12px
  color: var(--color-text)
  font-size: 0.92rem

focus:
  borderColor: var(--color-accent)
  outline: none
```

## 5. Layout Principles

### 间距系统（基于 4px 基准）

| Token | 值 (px) | 用途 |
|-------|---------|------|
| `space-1` | 4 | 极紧凑（图标内边距） |
| `space-2` | 8 | 紧凑（元素间距） |
| `space-3` | 12 | 中等（卡片内元素） |
| `space-4` | 16 | 标准（卡片内边距） |
| `space-5` | 20 | 大间距（区块间） |
| `space-6` | 24 | 区块间距 |
| `space-8` | 32 | 页面级间距 |
| `space-10` | 40 | 极少使用 |

**严禁**：使用不在上述体系中的间距值（如 6px、14px、22px）。

### 容器宽度

| 断点 | 宽度 | 用途 |
|------|------|------|
| `max-w-narrow` | 720px | 窄面板（如日志/侧栏） |
| `max-w-default` | 1240px | 默认内容宽度 |
| `max-w-wide` | 1440px | 宽面板（如交易中枢） |

### 留白哲学

- 信息密度 > 呼吸感：交易场景需要数据密度，但不能牺牲可读性
- 垂直间距略大于水平间距：人眼对垂直节奏更敏感
- 第一屏必须完整展示核心操作区

## 6. Depth & Elevation

当前项目 **无阴影**，深度通过以下方式实现：

| 层级 | 实现方式 | 用途 |
|------|----------|------|
| `z-flat` | 无边框/无背景 | 静态内容 |
| `z-card` | `border: 1px solid var(--color-border)` | 卡片/面板 |
| `z-elevated` | `backdrop-filter: blur(8px)` + 半透明背景 | 弹出层/悬浮面板 |
| `z-overlay` | 纯背景色 + `z-index: 100` | 模态框/下拉菜单 |
| `z-toast` | `z-index: 200` | 通知/提示 |

**新增阴影系统**（仅在弹出层和模态框中使用）：

```css
shadow-sm: 0 1px 2px rgba(0,0,0,.24)
shadow-md: 0 4px 12px rgba(0,0,0,.32)
shadow-lg: 0 8px 24px rgba(0,0,0,.40)
```

## 7. Do's and Don'ts

### Do's

- ✅ 使用语义化色名（`--color-red`），不用 hex 值
- ✅ 使用间距 token（`space-3` = 12px），不用魔数
- ✅ 使用字号层级（`h2`、`body-sm`），不用随机 em
- ✅ 提取共享组件到 `components/common/`
- ✅ 标注数据置信度（采集/推断/存疑）
- ✅ 新组件先想：是否会在两个以上地方复用？

### Don'ts

- ❌ 在组件内定义 `style={{ color: '#ef4444' }}`——用 `var(--color-red)`
- ❌ 复制粘贴 `Metric`、`ActionButton`、`Card` 组件
- ❌ 创建超过 3 层的组件嵌套目录
- ❌ 在单个文件中超过 400 行代码（拆分！）
- ❌ 添加装饰性动画（数据变化本身就足够吸引人）
- ❌ 使用 `TBD`、`TODO`、`later` 占位符

## 8. Responsive Behavior

### 断点策略

| 断点 | 宽度 | 行为 |
|------|------|------|
| `sm` | 640px | 移动端：侧栏隐藏，全宽卡片 |
| `md` | 768px | 平板：可选侧栏 |
| `lg` | 1024px | 桌面：默认布局 |
| `xl` | 1280px | 大桌面：宽面板 |

### 移动端适配

- 侧栏默认折叠，通过汉堡菜单展开
- 卡片全宽，无 `maxWidth` 限制
- 触控区域最小 44×44px
- 字体不缩小，优先减少列数

## 9. Agent Prompt Guide

**给 AI 的标准化提示词**（复制以下模板生成匹配的 UI）：

```
你正在为 Info-Hub 交易工作台生成 UI 组件。请严格遵循以下设计规范：

1. 颜色：只使用 DESIGN.md 中定义的语义色 CSS 变量
   示例：var(--color-red), var(--color-accent), var(--color-surface)

2. 间距：使用 4px 基准的间距系统（4/8/12/16/20/24/32）

3. 字号：使用 DESIGN.md 定义的字号层级，不要用 em 单位

4. 卡片：基础卡片 = 背景 var(--color-surface) + 1px 边框 + 12px 圆角

5. 按钮：主按钮用 var(--color-accent) 背景，次按钮用半透明背景

6. 状态：hover 时 borderColor 变为 var(--color-accent)

7. 文件位置：共享组件放到 src/components/common/

生成代码时，优先使用 Tailwind CSS 工具类，必要时用 inline style + CSS 变量。
```
