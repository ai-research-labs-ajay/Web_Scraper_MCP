
import feedparser
import json
import time
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

import requests
from bs4 import BeautifulSoup

# =========================
# CONFIG
# =========================
OUTPUT_FILE = "market_news.json"

seen_news = set()

RSS_FEEDS = {
    "Moneycontrol": "https://www.moneycontrol.com/stocksmarketsindia/",
    "EconomicTimes": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Reuters": "https://www.reuters.com/markets/",
    "CNBC": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "Bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
    "AlJazeera": "https://www.aljazeera.com/xml/rss/all.xml",
    "NYTimes": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    "Reddit": "https://www.reddit.com/r/stocks/.rss"
}

analyzer = SentimentIntensityAnalyzer()

# =========================
# 🔥 ADVANCED KEYWORDS (ADDED)
# =========================
BULLISH_KEYWORDS = {
    "bullish", "bull", "rally", "surge", "moon", "rocket",
    "breakout", "strong", "buy", "accumulate",
    "long", "golden cross"
}

BEARISH_KEYWORDS = {
    "bearish", "bear", "crash", "dump", "plunge",
    "sell-off", "downtrend", "weak", "sell",
    "short", "death cross"
}

FINANCIAL_KEYWORDS = {
    "support", "resistance", "breakout", "breakdown",
    "nifty", "banknifty", "sensex", "bse", "nse",
    "rsi", "macd", "bollinger", "volume"
}

GEOPOLITICAL_KEYWORDS = {
    "war", "conflict", "sanction", "fed", "rbi",
    "rate hike", "inflation", "recession"
}

# =========================
# BASE KEYWORDS
# =========================
KEYWORDS = [
    "nifty","bank nifty","sensex","market crash","inflation",
    "interest rate","rbi","fii","dii","expiry","pcr",
    "stocks","market","shares","trading",
    "breakout","support","resistance","rally","selloff"
]

HIGH_IMPACT = [
    "rbi policy","repo rate","rate hike","market crash",
    "recession","budget","war","fii selling","fed","interest cut"
]

# =========================
# SCORING (🔥 BOOST ADDED)
# =========================
def get_news_score(text):
    score = 0
    text = text.lower()

    # HIGH IMPACT
    for word in HIGH_IMPACT:
        if word in text:
            score += 5

    # NORMAL KEYWORDS
    for word in KEYWORDS:
        if word in text:
            score += 1

    # 🔥 NEW BOOST LOGIC (NO BREAK)
    for word in BULLISH_KEYWORDS:
        if word in text:
            score += 2

    for word in BEARISH_KEYWORDS:
        if word in text:
            score += 2

    for word in FINANCIAL_KEYWORDS:
        if word in text:
            score += 1

    for word in GEOPOLITICAL_KEYWORDS:
        if word in text:
            score += 2

    return score


def get_impact(score):
    if score >= 6:
        return "HIGH"
    elif score >= 3:
        return "MEDIUM"
    return "LOW"


# =========================
# BUILD ITEM
# =========================
def build_news_item(source, title, link, summary="", published=""):
    sentiment = analyzer.polarity_scores(title)
    score = get_news_score((title + summary).lower())

    return {
        "source": source,
        "title": title,
        "summary": summary,
        "link": link,
        "published": published,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "score": score,
        "impact": get_impact(score),
        "sentiment": sentiment["compound"],
        "sentiment_label": (
            "bullish" if sentiment["compound"] > 0.05
            else "bearish" if sentiment["compound"] < -0.05
            else "neutral"
        )
    }


# =========================
# MONEYCONTROL
# =========================
def fetch_moneycontrol_html():
    news_list = []
    try:
        res = requests.get("https://www.moneycontrol.com/stocksmarketsindia/", headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")

        for a in soup.find_all("a"):
            title = a.get_text(strip=True)
            link = a.get("href")

            if not title or not link or "moneycontrol.com" not in link:
                continue

            if link in seen_news:
                continue

            news_list.append(build_news_item("Moneycontrol", title, link))
            seen_news.add(link)

    except Exception as e:
        print("❌ Moneycontrol Error:", e)

    return news_list


# =========================
# REUTERS
# =========================
def fetch_reuters_news(limit=20):
    news_list = []

    try:
        url = "https://www.reuters.com/markets/"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)

        soup = BeautifulSoup(res.text, "html.parser")

        links = soup.find_all("a")

        for a in links:
            title = a.get_text(strip=True)
            link = a.get("href")

            if not title or not link:
                continue

            if link.startswith("/"):
                link = "https://www.reuters.com" + link

            # 🔥 IMPORTANT FIX → REMOVE STRICT FILTER
            if "reuters.com" not in link:
                continue

            if link in seen_news:
                continue

            news_list.append(
                build_news_item("Reuters", title, link)
            )

            seen_news.add(link)

            if len(news_list) >= limit:
                break

        print("✅ Reuters fetched:", len(news_list))

    except Exception as e:
        print("❌ Reuters Error:", e)

    return news_list
# =========================
# TWITTER
# =========================
def fetch_twitter_news(query="NIFTY", limit=20):
    news_list = []

    NITTER_INSTANCES = [
        "https://nitter.poast.org",
        "https://nitter.net",
        "https://nitter.privacydev.net"
    ]

    headers = {"User-Agent": "Mozilla/5.0"}

    for base in NITTER_INSTANCES:
        try:
            url = f"{base}/search?q={query}&f=live"
            res = requests.get(url, headers=headers, timeout=10)

            if res.status_code != 200:
                continue

            soup = BeautifulSoup(res.text, "html.parser")
            tweets = soup.find_all("div", class_="tweet")

            if not tweets:
                continue  # try next instance

            for tweet in tweets[:limit]:
                text_elem = tweet.find("p", class_="tweet-text")
                text = text_elem.get_text(strip=True) if text_elem else ""

                date_elem = tweet.find("span", class_="tweet-date")
                date = date_elem.get_text(strip=True) if date_elem else ""

                if not text or text in seen_news:
                    continue

                news_list.append(
                    build_news_item("Twitter", text[:120], url, text, date)
                )

                seen_news.add(text)

            print(f"✅ Twitter fetched from {base}")
            return news_list  # stop after success

        except Exception as e:
            print(f"❌ Twitter {base} failed:", e)

    return news_list


# =========================
# FETCH NEWS
# =========================
def fetch_news():
    new_items = []

    new_items += fetch_moneycontrol_html()
    new_items += fetch_reuters_news()
    new_items += fetch_twitter_news()

    for source, url in RSS_FEEDS.items():
        if source in ["Moneycontrol", "Reuters"]:
            continue

        try:
            feed = feedparser.parse(url)

            for entry in feed.entries:
                if entry.link in seen_news:
                    continue

                news_item = build_news_item(
                    source,
                    entry.title,
                    entry.link,
                    entry.get("summary", "")
                )

                new_items.append(news_item)
                seen_news.add(entry.link)

        except Exception as e:
            print(f"❌ {source} RSS Error:", e)

    print("🔥 Total news fetched:", len(new_items))
    print("Twitter:", len(fetch_twitter_news()))
    print("Reuters:", len(fetch_reuters_news()))
    return new_items


# =========================
# SAVE
# =========================
def save_news(news):
    try:
        with open(OUTPUT_FILE, "r") as f:
            existing = json.load(f)
    except:
        existing = []

    existing.extend(news)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(existing, f, indent=4)


# =========================
# BACKGROUND SCRAPER
# =========================
def background_scraper(socketio):
    print("🚀 Real-Time Scraper Started...")

    while True:
        try:
            news = fetch_news()

            if news:
                save_news(news)
                socketio.emit("news_update", news)
            else:
                print("⚡ No news found")

        except Exception as e:
            print("❌ Error:", e)

        time.sleep(60)
