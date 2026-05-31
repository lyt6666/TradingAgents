#!/usr/bin/env python3
"""
📡 TradingAgents Web UI — FastAPI 后端
用法:  python3 web/app.py
      浏览器打开 http://localhost:8080
"""

import sys, os, json, asyncio, subprocess, time, warnings
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import uvicorn

warnings.filterwarnings("ignore")

BASE = Path("/tmp/TradingAgents")
OUT = BASE / "output"
INDEX_HTML = BASE / "web" / "index.html"

app = FastAPI(title="TradingAgents Dashboard")


# ===== 数据接口 =====
def load_json(path):
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def round2(v):
    if v is None: return 0
    return round(float(v), 2)


@app.get("/", response_class=HTMLResponse)
async def index():
    if INDEX_HTML.exists():
        return HTMLResponse(content=INDEX_HTML.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Not Found</h1>", status_code=404)


@app.get("/api/status")
async def api_status():
    memory = load_json(OUT / "trade_memory.json")
    alerts = load_json(OUT / "alerts.json")
    picks = load_json(OUT / "latest_picks.json")

    total_stocks = len(memory.get("recommendations", {}))
    total_recos = sum(len(s) for s in memory.get("recommendations", {}).values())
    total_runs = sum(len(s.get("stocks", [])) for s in memory.get("runs", []))
    unack_alerts = len([a for a in alerts.get("alerts", []) if not a.get("acknowledged")])

    last_run = memory["runs"][-1] if memory.get("runs") else None

    return {
        "total_runs": total_runs,
        "total_stocks": total_stocks,
        "total_recos": total_recos,
        "unack_alerts": unack_alerts,
        "last_run": last_run,
        "current_picks": picks if isinstance(picks, list) else [],
        "has_alerts": unack_alerts > 0,
    }


@app.get("/api/picks/latest")
async def api_latest_picks():
    picks = load_json(OUT / "latest_picks.json")
    return {"picks": picks if isinstance(picks, list) else []}


@app.get("/api/history")
async def api_history():
    memory = load_json(OUT / "trade_memory.json")
    runs = memory.get("runs", [])
    return {"runs": list(reversed(runs))}


@app.get("/api/alerts")
async def api_alerts():
    alerts = load_json(OUT / "alerts.json")
    unack = [a for a in alerts.get("alerts", []) if not a.get("acknowledged")]
    acked = [a for a in alerts.get("alerts", []) if a.get("acknowledged")]
    return {"unacknowledged": list(reversed(unack)), "acknowledged": list(reversed(acked))}


@app.post("/api/pipeline/run")
async def api_run_pipeline(background_tasks: BackgroundTasks, data: dict):
    strategy = data.get("strategy", "volume")
    top = data.get("top", 3)

    async def run():
        env = os.environ.copy()
        env["DEEPSEEK_API_KEY"] = "sk-677696e8d5fb45b6b4a22ad23e773b41"
        env["PYTHONPATH"] = str(BASE)

        await asyncio.create_subprocess_exec(
            "python3", str(BASE / "stock_picker.py"),
            "--strategy", strategy, "--top", str(top),
            cwd=str(BASE), env=env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.create_subprocess_exec(
            "python3", str(BASE / "intel_agent.py"),
            cwd=str(BASE), env=env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.sleep(2)
        await asyncio.create_subprocess_exec(
            "python3", str(BASE / "portfolio_engine.py"),
            "--file", str(OUT / "latest_picks.json"),
            cwd=str(BASE), env=env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.sleep(1)
        await asyncio.create_subprocess_exec(
            "python3", str(BASE / "trade_memory.py"), "record",
            cwd=str(BASE), env=env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

    background_tasks.add_task(run)
    return {"status": "started", "strategy": strategy, "top": top}


@app.post("/api/alerts/acknowledge")
async def api_acknowledge_alerts():
    alerts = load_json(OUT / "alerts.json")
    for a in alerts.get("alerts", []):
        a["acknowledged"] = True
    with open(OUT / "alerts.json", "w") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)
    return {"status": "ok"}


@app.get("/api/strategies")
async def api_strategies():
    return {
        "strategies": [
            {"id": "volume", "name": "放量突破", "emoji": "📈", "color": "#3b82f6", "desc": "成交量放大 + 价格突破均线，短线资金活跃信号"},
            {"id": "value", "name": "价值低估", "emoji": "💰", "color": "#10b981", "desc": "低PE + 低PB + 高ROE，基本面优秀的便宜货"},
            {"id": "momentum", "name": "动量趋势", "emoji": "🚀", "color": "#f59e0b", "desc": "近期涨幅靠前 + 均线多头排列，趋势跟踪策略"},
            {"id": "oversold", "name": "超跌反弹", "emoji": "🔄", "color": "#ef4444", "desc": "RSI超卖 + 跌幅过大，可能的反弹机会"},
        ]
    }


@app.get("/api/backtest")
async def api_backtest(strategy: str = "volume", all_strategies: bool = False):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BASE)

    if all_strategies:
        proc = await asyncio.create_subprocess_exec(
            "python3", str(BASE / "backtest_engine.py"), "--all-strategies",
            cwd=str(BASE), env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    else:
        proc = await asyncio.create_subprocess_exec(
            "python3", str(BASE / "backtest_engine.py"),
            "--strategy", strategy,
            cwd=str(BASE), env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    await proc.communicate()
    return load_json(OUT / "backtest_results.json")


@app.get("/api/backtest/data")
async def api_backtest_data():
    return load_json(OUT / "backtest_results.json")


@app.get("/api/analytics/performance")
async def api_performance():
    """策略表现分析数据"""
    backtest = load_json(OUT / "backtest_results.json")
    memory = load_json(OUT / "trade_memory.json")
    comparison = backtest.get("comparison", {})

    strategies_data = []
    for sid in ["volume", "value", "momentum", "oversold"]:
        b = comparison.get(sid, {})
        strategies_data.append({
            "id": sid,
            "return": round2(b.get("total_return_pct")),
            "win_rate": round2(b.get("win_rate")),
            "sharpe": round2(b.get("sharpe_ratio")),
            "drawdown": round2(b.get("max_drawdown_pct")),
            "trades": b.get("total_trades", 0),
        })

    return {
        "strategies": strategies_data,
        "total_history_runs": len(memory.get("runs", [])),
        "last_updated": backtest.get("comparison_time", datetime.now().strftime("%Y-%m-%d %H:%M")),
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"📡 TradingAgents Dashboard → http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
