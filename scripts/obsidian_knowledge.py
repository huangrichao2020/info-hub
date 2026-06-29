#!/usr/bin/env python3
"""
knowhub 方法论 → Obsidian 同步
- 3 份核心方法论
- 概念页（卡脖子 / 国产替代 / AI 算力 / 7 大赛道）
"""
import shutil
from pathlib import Path
from datetime import datetime

KNOWHUB_ROOT = Path("/Users/tingchi/.mavis/knowledge/knowhub")
VAULT_ROOT = Path.home() / "Documents" / "Obsidian Vault"
METHODOLOGY_DIR = VAULT_ROOT / "10-Wiki" / "Methodology"
CONCEPTS_DIR = VAULT_ROOT / "10-Wiki" / "Concepts"
TRADING_CONCEPTS = VAULT_ROOT / "10-Wiki" / "Trading" / "Concepts"

METHODOLOGY_DIR.mkdir(parents=True, exist_ok=True)
CONCEPTS_DIR.mkdir(parents=True, exist_ok=True)
TRADING_CONCEPTS.mkdir(parents=True, exist_ok=True)


def sync_methodology():
    """同步 3 份核心方法论"""
    sources = [
        ("serenity-choke-point.md", "Serenity 卡脖子框架"),
        ("prism-three-lens.md", "三棱镜三视角框架"),
        ("infohub-integration.md", "info-hub 集成方案"),
    ]

    for src_name, title in sources:
        src = KNOWHUB_ROOT / "domains" / "trading-review" / "methodology" / src_name
        if not src.exists():
            print(f"⚠️ {src} 不存在，跳过")
            continue

        # 加 frontmatter
        content = src.read_text(encoding="utf-8")
        frontmatter = f"""---
title: "{title}"
source: knowhub/trading-review/methodology/{src_name}
tags: [methodology, trading, serenity, prism]
created: 2026-06-30
auto_synced: true
---

"""
        full = frontmatter + content

        # 加 wikilink 替换（自动把标的/赛道转 wikilink）
        replacements = {
            "Serenity 卡脖子框架": "[[Serenity 卡脖子框架]]",
            "Serenity 框架": "[[Serenity 卡脖子框架]]",
            "三棱镜": "[[三棱镜三视角框架]]",
            "三棱镜框架": "[[三棱镜三视角框架]]",
            "卡脖子定位": "[[卡脖子定位]]",
            "国产替代": "[[国产替代]]",
            "AI 算力": "[[AI 算力]]",
            "AI算力": "[[AI 算力]]",
            "中船特气": "[[中船特气 688146]]",
            "云南锗业": "[[云南锗业 002428]]",
            "北方华创": "[[北方华创 002371]]",
            "兆易创新": "[[兆易创新 603986]]",
            "绿的谐波": "[[绿的谐波 688017]]",
            "电子特气": "[[电子特气]]",
            "半导体设备": "[[半导体设备]]",
            "半导体材料": "[[半导体材料]]",
            "NOR Flash": "[[NOR Flash]]",
            "磷化铟+锗": "[[磷化铟+锗]]",
            "机器人零部件": "[[机器人零部件]]",
            "碳化硅+远期": "[[碳化硅+远期]]",
        }

        for old, new in replacements.items():
            # 避免双重 wikilink
            content = content.replace(f"[[{old}]]", old)  # 先撤掉可能的 double
            content = content.replace(old, new)

        # 重新组装
        full = frontmatter + content

        out = METHODOLOGY_DIR / src_name
        out.write_text(full, encoding="utf-8")
        print(f"✅ {src_name} → {out}")


def write_concept_pages():
    """写入概念页（卡脖子 / 国产替代 / AI 算力）"""
    concepts = {
        "卡脖子定位.md": {
            "name": "卡脖子定位",
            "title": "🔴 卡脖子定位",
            "definition": "**卡脖子**指一个产业链中**一旦断货，整个万亿级产业就要地震**的瓶颈环节。Serenity 框架的核心是找到这样的环节，分析卡脖子背后的 A 股标的。",
            "scoring": "卡脖子评分 1-10 分，10 分代表最极致卡脖子（如中船特气 WF6 断供 → 国内 5nm 停摆）。",
            "real_examples": [
                "**6 英寸磷化铟（InP）衬底**：海外住友/JX/AXT 占 95%，国内仅云南锗业稳定量产。一旦断货，全球 800G/1.6T 光模块产能停滞。",
                "**六氟化钨（WF6）**：7N 级全球唯一稳定量产（中船特气）。一旦断供，国内 3nm/5nm 产线直接停摆。",
                "**ArF 光刻胶**：国内唯一量产（南大光电）。一旦断供，国内 28nm 以下先进制程光刻工艺卡死。",
            ],
            "framework": "[[Serenity 卡脖子框架]]",
            "related": [
                "[[国产替代]] · [[AI 算力]] · [[Serenity 卡脖子框架]]",
                "[[中船特气 688146]] · [[云南锗业 002428]] · [[北方华创 002371]]",
            ],
            "tags": ["概念", "卡脖子", "Serenity"],
        },
        "国产替代.md": {
            "name": "国产替代",
            "title": "🇨🇳 国产替代",
            "definition": "**国产替代**指国内企业突破海外巨头的技术封锁，承接原本被外资垄断的产业链环节。Serenity 框架下，国产替代是卡脖子逻辑的核心兑现路径。",
            "categories": [
                "**半导体材料**：光刻胶（南大/彤程）、CMP（鼎龙/安集）、靶材（江丰）、ABF 载板（深南）",
                "**半导体设备**：刻蚀（中微/北方华创）、清洗（盛美）、PECVD（拓荆）",
                "**电子特气**：WF6（中船特气）、含氟特气（昊华/华特）",
                "**存储芯片**：NOR Flash（兆易）、EEPROM（普冉）",
                "**机器人核心部件**：谐波减速器（绿的谐波）、执行器（拓普）",
            ],
            "policy": "十五五规划将'集成电路、工业母机、高端仪器、基础软件'列为'决定性突破'重点领域。",
            "framework": "[[Serenity 卡脖子框架]]",
            "related": [
                "[[卡脖子定位]] · [[AI 算力]]",
                "[[南大光电 300346]] · [[北方华创 002371]] · [[兆易创新 603986]]",
            ],
            "tags": ["概念", "国产替代", "政策"],
        },
        "AI 算力.md": {
            "name": "AI 算力",
            "title": "🤖 AI 算力",
            "definition": "**AI 算力**指支撑 AI 训练和推理的硬件基础设施总称，包含 GPU/ASIC 芯片、HBM/DRAM 内存、800G/1.6T 光模块、AI 服务器 PCB、液冷散热等。Serenity 框架下，AI 算力是当前最大的卡脖子驱动赛道。",
            "key_chains": [
                "**上游材料**：InP 衬底（云南锗业）、电子特气（中船特气）",
                "**中游器件**：EML 激光器（源杰）、光模块（中际旭创/新易盛）",
                "**下游应用**：AI 数据中心、自动驾驶、卫星通信",
            ],
            "demand": "全球四大 CSP 资本开支 2025 年达 4000 亿美元，同比增长 60%。英伟达预计 2030 年全球 AI 基础设施市场规模 3-4 万亿美元。",
            "related_chains": [
                "**半导体设备**：北方华创/中微公司/盛美上海",
                "**半导体材料**：南大光电/江丰电子/鼎龙股份",
                "**NOR Flash**：兆易创新（端侧 AI + 车规 + 机器人）",
            ],
            "framework": "[[Serenity 卡脖子框架]]",
            "related": [
                "[[卡脖子定位]] · [[国产替代]]",
                "[[云南锗业 002428]] · [[中船特气 688146]] · [[兆易创新 603986]]",
            ],
            "tags": ["概念", "AI", "算力"],
        },
    }

    for filename, c in concepts.items():
        content = f"""---
title: "{c['title']}"
name: "{c['name']}"
tags: {c['tags']}
source: mavis-knowledge-base
created: 2026-06-30
---

# {c['title']}

## 📖 定义

{c['definition']}

"""

        if "scoring" in c:
            content += f"## 📊 评分体系\n\n{c['scoring']}\n\n"
        if "categories" in c:
            content += "## 🏷️ 分类\n\n"
            for cat in c["categories"]:
                content += f"- {cat}\n"
            content += "\n"
        if "key_chains" in c:
            content += "## 🔗 关键产业链\n\n"
            for chain in c["key_chains"]:
                content += f"- {chain}\n"
            content += "\n"
        if "demand" in c:
            content += f"## 📈 需求驱动\n\n{c['demand']}\n\n"
        if "policy" in c:
            content += f"## 🏛️ 政策支持\n\n{c['policy']}\n\n"
        if "related_chains" in c:
            content += "## 🔗 相关卡脖子环节\n\n"
            for chain in c["related_chains"]:
                content += f"- {chain}\n"
            content += "\n"
        if "real_examples" in c:
            content += "## 🎯 真实案例\n\n"
            for ex in c["real_examples"]:
                content += f"- {ex}\n"
            content += "\n"

        content += f"""## 🔗 关联笔记

{c['framework']}

"""
        for r in c["related"]:
            content += f"- {r}\n"

        content += """
---

*由 Mavis 自动生成的概念笔记 · 双向链接驱动 · 可在 Obsidian 中用 Ctrl/Cmd + G 查看关联*
"""
        out = CONCEPTS_DIR / filename
        out.write_text(content, encoding="utf-8")
        print(f"✅ 概念页: {out}")


def write_track_pages():
    """写入 7 大赛道概念页（每个赛道一个 .md）"""
    tracks = [
        {
            "name": "磷化铟+锗",
            "emoji": "🥇",
            "tagline": "AI 光模块心脏",
            "core": "AI 算力 800G/1.6T 光模块上游",
            "stocks": ["云南锗业 002428", "有研新材 600206", "光智科技 300566"],
            "key_metric": "国内自给率 < 5%（InP 衬底）",
            "price_trend": "锗价年内涨 50-80%，InP 订单排到 2028 年",
        },
        {
            "name": "电子特气",
            "emoji": "🥈",
            "tagline": "先进制程血液",
            "core": "AI 芯片 3nm/5nm 工艺必备",
            "stocks": ["中船特气 688146", "昊华科技 600378", "华特气体 688268"],
            "key_metric": "WF6 价格 500%+ 涨幅",
            "price_trend": "海外 7 月可能因钨出口管制断供",
        },
        {
            "name": "NOR Flash",
            "emoji": "🥉",
            "tagline": "端侧 AI + 车规",
            "core": "AI 设备 + 车规 + 机器人 MCU",
            "stocks": ["兆易创新 603986", "普冉股份 688766", "佰维存储 688525"],
            "key_metric": "NOR 全球第二 23.2%（兆易）",
            "price_trend": "海外巨头退出利基市场",
        },
        {
            "name": "机器人零部件",
            "emoji": "🤖",
            "tagline": "量产元年",
            "core": "人形机器人 + 工业机器人核心部件",
            "stocks": ["绿的谐波 688017", "埃斯顿 002747", "拓普集团 601689"],
            "key_metric": "全球出货 +700%（2026）",
            "price_trend": "量产元年，特斯拉 Optimus 供应链",
        },
        {
            "name": "半导体设备",
            "emoji": "🏭",
            "tagline": "十五五重点",
            "core": "刻蚀/沉积/清洗/PECVD 国产替代",
            "stocks": ["北方华创 002371", "中微公司 688012", "盛美上海 688082", "拓荆科技 688072"],
            "key_metric": "设备国产化率 < 30%",
            "price_trend": "十五五政策核心支持",
        },
        {
            "name": "半导体材料",
            "emoji": "🧪",
            "tagline": "国产化 10-20% → 30-50%",
            "core": "光刻胶/CMP/靶材/封装",
            "stocks": ["南大光电 300346", "江丰电子 300666", "鼎龙股份 300054", "安集科技 688019", "彤程新材 603650", "深南电路 002916", "雅克科技 002409"],
            "key_metric": "材料国产化率 10-20%（5 年长坡）",
            "price_trend": "国产替代加速",
        },
        {
            "name": "碳化硅+远期",
            "emoji": "🚀",
            "tagline": "新能源 + 军工 + 机器人",
            "core": "800V 高压快充 + 航空发动机 + 人形机器人骨架",
            "stocks": ["天岳先进 688234", "三安光电 600703", "露笑科技 002617", "中复神鹰 688295", "光威复材 300699", "宝钛股份 600456"],
            "key_metric": "SiC 紧缺持续至 2028",
            "price_trend": "T1200 碳纤维全球首发",
        },
    ]

    for t in tracks:
        stocks_md = "\n".join(f"- [[{s}]]" for s in t["stocks"])
        content = f"""---
track: "{t['name']}"
emoji: "{t['emoji']}"
tagline: "{t['tagline']}"
tags: [track, chokepoint, "{t['name']}"]
---

# {t['emoji']} [[{t['name']}]]

> **{t['tagline']}**

## 🎯 核心定位

{t['core']}

## 📊 关键指标

- **核心数据**：{t['key_metric']}
- **价格走势**：{t['price_trend']}

## 📈 核心标的（{len(t['stocks'])} 只）

{stocks_md}

## 🔗 关联笔记

- 框架：[[Serenity 卡脖子框架]]
- 概念：[[卡脖子定位]] · [[国产替代]] · [[AI 算力]]
- 总索引：[[卡脖子分析 MOC]]

---

*由 Mavis 自动维护的赛道笔记 · {datetime.now().strftime('%Y-%m-%d')}*
"""
        out = TRADING_CONCEPTS / f"{t['name']}.md"
        out.write_text(content, encoding="utf-8")
        print(f"✅ 赛道页: {t['name']}")


def write_methodology_index():
    """写方法论 MOC 索引页"""
    content = """---
tags: [moc, methodology, trading]
---

# 📐 方法论 MOC

> **Map of Content** · Mavis 沉淀的交易方法论 · Karpathy LLM Wiki 风格

## 🎯 三大核心框架

### 🔴 [[Serenity 卡脖子框架]]
**核心心法**：沿产业链向上游追溯，找到"一旦断货，万亿产业地震"的关键节点。
- **来源**：GitHub fadewalk/serenity-stock-choke v2.0
- **A 股适配**：5 大特色维度（政策权重 / 主力结构 / 散户情绪 / 壳价值 / 国产替代）
- **应用**：info-hub 集成 4 个端点 + 29 只卡脖子标的深度分析

### 🟣 [[三棱镜三视角框架]]
**核心心法**：三个虚构人格覆盖投资决策的三层闭环。
- **Seri**：供应链卡脖子（中长期）
- **道士**：宏观先行（中长期）
- **Cat**：技术执行（短期）
- **来源**：GitHub destiny520537work-lab/fate-skill v3.1.0

### 🔵 [[info-hub 集成方案]]
**核心心法**：把方法论工程化到现有系统。
- **后端集成**：4 个新端点（choke-point + three-lens 单股/批量）
- **前端组件**：Sidebar 入口 + ChokePointPanel
- **cron 自动化**：每日 S/A/B 扫描 + commit/push

## 📐 辅助框架

- **8 节周报骨架**：标题 → 结论 → 盘面 → 日历 → 方向 → 风险 → 操作 → 方法论声明
- **方法论声明 > 免责声明**：把"防御性写作"变成"展示性写作"
- **三视角辩论模式**：精准找假设 + 策略性让步 + 沉默式轻蔑

## 🔗 关联笔记

- 概念：[[卡脖子定位]] · [[国产替代]] · [[AI 算力]]
- 应用：[[每日机会 MOC]] · [[卡脖子分析 MOC]]
- Karpathy 范式：[[Karpathy LLM Wiki 范式]]

---

*由 Mavis 自动维护 · knowhub 镜像*
"""
    out = METHODOLOGY_DIR / "_index.md"
    out.write_text(content, encoding="utf-8")
    print(f"✅ 方法论 MOC: {out}")


if __name__ == "__main__":
    print("==== 同步方法论 ====")
    sync_methodology()
    print("\n==== 写概念页 ====")
    write_concept_pages()
    print("\n==== 写赛道页 ====")
    write_track_pages()
    print("\n==== 方法论 MOC ====")
    write_methodology_index()
    print("\n✅ 全部完成")