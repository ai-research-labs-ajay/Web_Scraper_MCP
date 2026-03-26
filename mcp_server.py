from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import os

# ✅ IMPORT ALL REQUIRED FUNCTIONS
from scraper import (
    fetch_news,
    fetch_twitter_news,
    fetch_reuters_news
)

app = FastAPI()

# 🔐 API KEY (use ENV in production)
API_KEY = os.getenv("API_KEY", "ajay-secret")

# =========================
# REQUEST MODEL
# =========================
class ToolRequest(BaseModel):
    tool: str
    input: dict = {}

# =========================
# FILTER FUNCTION
# =========================
def filter_news(news, condition):
    return [n for n in news if condition(n)]

# =========================
# SAFE FETCH (🔥 FIXED)
# =========================
def safe_fetch_news():
    try:
        return fetch_news()   # ✅ FIX: remove seen param
    except Exception as e:
        print("❌ Scraper Error:", e)
        return []

# =========================
# MCP ENDPOINT
# =========================
@app.post("/mcp")
def handle_mcp(req: ToolRequest, x_api_key: str = Header(None)):

    # 🔐 AUTH
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 🔥 FETCH NEWS
    news = safe_fetch_news()

    print("🔥 Total news fetched:", len(news))

    # =========================
    # TOOL HANDLERS
    # =========================
    if req.tool == "get_market_news":
        return {"status": "success", "data": news}

    elif req.tool == "get_high_impact_news":
        return {
            "status": "success",
            "data": filter_news(news, lambda x: x.get("impact") == "HIGH")
        }

    elif req.tool == "get_bullish_news":
        return {
            "status": "success",
            "data": filter_news(news, lambda x: x.get("sentiment_label") == "bullish")
        }

    elif req.tool == "get_bearish_news":
        return {
            "status": "success",
            "data": filter_news(news, lambda x: x.get("sentiment_label") == "bearish")
        }

    elif req.tool == "get_trading_signals":
        signals = []

        for n in news:
            try:
                if n["sentiment_label"] == "bullish" and n["impact"] == "HIGH":
                    signal = "BUY"
                elif n["sentiment_label"] == "bearish" and n["impact"] == "HIGH":
                    signal = "SELL"
                else:
                    signal = "HOLD"

                signals.append({
                    "title": n["title"],
                    "signal": signal,
                    "impact": n["impact"],
                    "source": n["source"]
                })

            except Exception as e:
                print("⚠️ Signal error:", e)

        return {"status": "success", "data": signals}

    elif req.tool == "get_intraday_alerts":
        return {
            "status": "success",
            "data": filter_news(news, lambda x: x.get("impact") == "HIGH")
        }

    elif req.tool == "get_fii_dii_sentiment":
        return {
            "status": "success",
            "data": filter_news(
                news,
                lambda x: "fii" in x["title"].lower() or "dii" in x["title"].lower()
            )
        }

    elif req.tool == "get_sources":
        return {
            "status": "success",
            "data": list(set([n["source"] for n in news]))
        }

    return {"status": "error", "message": "Unknown tool"}

# =========================
# HEALTH CHECK
# =========================
@app.get("/")
def home():
    return {"message": "🚀 MCP Server Running"}
