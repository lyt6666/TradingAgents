# 📡 TradingAgents — AI 驱动 A 股量化交易系统

> 全自动选股 → 情报 → 策略 → 监控 → 回测，一条龙。

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek%20Chat-orange)](https://deepseek.com)
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

---

## 🎯 它能做什么

```
                  ┌─────────────────────┐
                  │    Web 看板:8080     │
                  └──────────┬──────────┘
                             │
  ┌───────────┬──────────┬───┴───┬──────────┬──────────┐
  │ 🎯 选股   │ 📊 情报  │ 💰 策略 │ 🔔 预警  │ 📉 回测  │
  │ 4种策略   │ 多维分析 │ 仓位分配 │ 实时监控  │ 历史验证 │
  │ AI 排序   │ 风险评分 │ 分批建仓 │ 止损止盈  │ 胜率统计 │
  └───────────┴──────────┴──────────┴──────────┴──────────┘
```

### 一键运行

```bash
./run_pipeline.sh momentum 3        # 动量策略，选 Top 3
./run_pipeline.sh volume 5 --ta     # 放量突破，含深度分析
./run_pipeline.sh oversold 10 --pick-only  # 只选股不看情报
```

---

## 🏗 系统架构

### 模块清单

| 模块 | 位置 | 职责 |
|:----|:----|:-----|
| **选股引擎** | `stock_picker.py` | 全市场扫描 → 策略筛选 → DeepSeek AI 排序 |
| **情报 Agent** | `intel_agent.py` | 政策/资金/技术/情绪 多维分析 |
| **组合策略** | `portfolio_engine.py` | 仓位分配 + 风控规则 + 建仓节奏 |
| **记忆系统** | `trade_memory.py` | 推荐记录 + 涨跌跟踪 + 胜率统计 |
| **预警监控** | `watchman.py` | 每日持仓检查 + 止损/止盈/超买预警 |
| **回测引擎** | `backtest_engine.py` | 多策略对比 + 收益率/胜率/夏普/回撤 |
| **Web 看板** | `web/app.py` | Tailwind UI + K线图 + iPad 自适应 |

### 四种选股策略

| 策略 | 逻辑 | 适用行情 |
|:----|:----|:---------|
| 📈 **放量突破** | 量比>1.5 + 站上MA20 + 涨幅2%~9.8% | 震荡/上涨 |
| 💰 **价值低估** | PE<20 + PB<2 + ROE>8% + 市值>50亿 | 左侧/价值 |
| 🚀 **动量趋势** | 站上MA20+MA60 + 多头排列 + 涨幅>5% | 趋势上涨 |
| 🔄 **超跌反弹** | RSI<35 + 跌幅>10% + 市值>30亿 | 大跌后反弹 |

### 技术栈

- **后端**: Python 3.10+ / FastAPI / uvicorn
- **AI**: DeepSeek Chat API (OpenAI compatible)
- **前端**: Tailwind CSS / TradingView Lightweight Charts
- **数据**: Mock (当前) → akshare (计划接入)
- **部署**: launchd (macOS常驻) / crontab (每日09:00预警)

---

## 🚀 快速开始

### 环境要求
```bash
python3 -V  # >= 3.10
pip3 install fastapi uvicorn jinja2 aiofiles
```

### 启动
```bash
cd TradingAgents

# 后台运行看板
python3 web/app.py &
# 浏览器打开 http://localhost:8080

# 或者一键跑流水线
./run_pipeline.sh volume 3
```

### Web 看板功能

| 面板 | 功能 |
|:----|:-----|
| **状态卡片** | 运行次数、股票数、推荐数、待处理预警 |
| **策略选择** | 4种策略，点选切换 |
| **当前推荐** | 股票详情 + K线走势图 (点击展开) |
| **预警列表** | 止损/止盈/超买/超卖，一键确认 |
| **运行历史** | 每次推荐的股票列表 |
| **回测引擎** | 单策略回测 + 全策略排名对比 |

---

## ⏰ 每日定时任务

crontab 已预设每天 09:00 自动检查预警：

```bash
crontab -l
# 0 9 * * * cd /tmp/TradingAgents && python3 watchman.py >> output/watchman.log 2>&1
```

macOS 启动时自动启动看板：
```bash
launchctl load ~/Library/LaunchAgents/com.tradingagents.web.plist
```

---

## 🗺 路线图

- [x] Mock 数据选股引擎
- [x] AI 排序 (DeepSeek)
- [x] 情报搜集 Agent
- [x] 组合策略引擎
- [x] 记忆追踪系统
- [x] 持仓预警监控
- [x] 回测引擎
- [x] Web 看板 (含K线图)
- [ ] 接入 akshare 实时 A 股数据
- [ ] 多策略组合运行
- [ ] 飞书推送集成
- [ ] 回测真实历史数据

---

## 📄 License

MIT

---

**Built with 🐾 by [TauricResearch](https://github.com/TauricResearch)**
