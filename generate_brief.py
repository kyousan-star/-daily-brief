#!/usr/bin/env python3
"""美日金融市场 Daily Brief 生成器"""

import yfinance as yf
import os
from datetime import datetime, date, timedelta
import pytz

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

INDICES = [
    ("^GSPC",  "标普500",      "🇺🇸", "S&P 500"),
    ("^IXIC",  "纳斯达克",     "🇺🇸", "NASDAQ"),
    ("^DJI",   "道琼斯",       "🇺🇸", "DOW"),
    ("^RUT",   "罗素2000",     "🇺🇸", "Russell 2K"),
    ("^VIX",   "VIX恐慌指数",  "🇺🇸", "VIX"),
    ("^N225",  "日经225",      "🇯🇵", "Nikkei 225"),
    ("1306.T", "TOPIX ETF",    "🇯🇵", "TOPIX"),
]

FX_COMMODITIES = [
    ("JPY=X",    "美元/日元",   "💱"),
    ("CNY=X",    "美元/人民币", "💱"),
    ("EURUSD=X", "欧元/美元",   "💱"),
    ("^TNX",     "美债10Y(%)",  "🏦"),
    ("^IRX",     "美债2Y(%)",   "🏦"),
    ("CL=F",     "原油WTI",     "🛢️"),
    ("GC=F",     "黄金",        "🥇"),
    ("BTC-USD",  "比特币",      "₿"),
]

SECTOR_ETFS_US = [
    ("XLK",  "科技",    "XLK"),
    ("SOXX", "半导体",  "SOXX"),
    ("XLY",  "消费可选","XLY"),
    ("XLP",  "消费必需","XLP"),
    ("XLE",  "能源",    "XLE"),
    ("XAR",  "国防军工","XAR"),
]

SECTOR_ETFS_JP = [
    ("EWJ",  "日本综合", "EWJ"),
    ("HEWJ", "日本对冲", "HEWJ"),
    ("JPXN", "日本大盘", "JPXN"),
]

WATCHLIST_US = {
    "AI / 科技核心": [
        ("NVDA",  "英伟达",       "NVIDIA"),
        ("MSFT",  "微软",         "Microsoft"),
        ("AAPL",  "苹果",         "Apple"),
        ("META",  "Meta",         "Meta"),
        ("GOOGL", "谷歌",         "Alphabet"),
        ("AMZN",  "亚马逊",       "Amazon"),
    ],
    "半导体": [
        ("AMD",  "超微半导体",    "AMD"),
        ("AVGO", "博通",          "Broadcom"),
        ("TSM",  "台积电",        "TSMC"),
        ("QCOM", "高通",          "Qualcomm"),
        ("AMAT", "应用材料",      "AMAT"),
    ],
    "消费": [
        ("TSLA", "特斯拉",        "Tesla"),
        ("COST", "好市多",        "Costco"),
        ("WMT",  "沃尔玛",        "Walmart"),
        ("NKE",  "耐克",          "Nike"),
    ],
    "能源": [
        ("XOM", "埃克森美孚",     "ExxonMobil"),
        ("CVX", "雪佛龙",         "Chevron"),
        ("COP", "康菲石油",       "ConocoPhillips"),
    ],
    "国防 / 军工": [
        ("LMT", "洛克希德·马丁",  "Lockheed"),
        ("RTX", "雷神技术",       "RTX"),
        ("NOC", "诺斯罗普",       "Northrop"),
        ("GD",  "通用动力",       "Gen Dynamics"),
        ("BA",  "波音",           "Boeing"),
    ],
}

WATCHLIST_JP = {
    "科技 / 半导体": [
        ("6758.T", "索尼",        "Sony"),
        ("6861.T", "基恩士",      "Keyence"),
        ("6501.T", "日立",        "Hitachi"),
        ("8035.T", "东京电子",    "Tokyo Electron"),
    ],
    "消费 / 汽车": [
        ("7203.T", "丰田",        "Toyota"),
        ("7267.T", "本田",        "Honda"),
        ("7974.T", "任天堂",      "Nintendo"),
        ("9983.T", "优衣库",      "Fast Retailing"),
    ],
    "金融 / 综合": [
        ("9984.T", "软银",        "SoftBank"),
        ("8306.T", "三菱UFJ",     "MUFG"),
        ("9432.T", "NTT",         "NTT"),
    ],
}

MACRO_EVENTS = [
    ("2026-04-22", "美联储褐皮书发布",          "med"),
    ("2026-04-24", "美国GDP初值 Q1",            "high"),
    ("2026-04-30", "美联储FOMC利率决议",        "high"),
    ("2026-05-01", "鲍威尔新闻发布会",          "high"),
    ("2026-05-02", "美国非农就业报告 (NFP)",    "high"),
    ("2026-05-07", "美国CPI通胀数据",           "high"),
    ("2026-05-13", "日本GDP初值 Q1",            "med"),
    ("2026-05-15", "美国零售销售数据",          "med"),
    ("2026-05-20", "日本央行政策会议",          "high"),
]


# ── 数据获取 ───────────────────────────────────────────
def fetch_quote(ticker: str) -> dict:
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        price = fi.last_price
        prev  = fi.previous_close
        if price and prev:
            chg_pct = (price - prev) / prev * 100
            chg_pt  = price - prev
            return {
                "price": price,
                "change_pct": chg_pct,
                "change_pt": chg_pt,
                "prev_close": prev,
                "year_change": getattr(fi, "year_change", None),
                "fifty_two_week_high": getattr(fi, "fifty_two_week_high", None),
                "fifty_two_week_low":  getattr(fi, "fifty_two_week_low", None),
            }
    except Exception:
        pass
    return {"price": None, "change_pct": None, "change_pt": None, "prev_close": None,
            "year_change": None, "fifty_two_week_high": None, "fifty_two_week_low": None}

def fetch_stock_detail(ticker: str) -> dict:
    """拉取分析师目标价、市值等（较慢，仅用于个股）"""
    try:
        info = yf.Ticker(ticker).info
        return {
            "target_mean_price": info.get("targetMeanPrice"),
            "market_cap": info.get("marketCap"),
            "recommendation": info.get("recommendationKey", ""),
            "revenue_growth": info.get("revenueGrowth"),
        }
    except Exception:
        return {}

def fetch_all(tickers: list) -> dict:
    results = {}
    for t in tickers:
        results[t] = fetch_quote(t)
    return results


# ── 格式化 ─────────────────────────────────────────────
def fmt_price(v, decimals=2):
    if v is None:
        return "—"
    if v >= 10000:
        return f"{v:,.0f}"
    if v >= 1000:
        return f"{v:,.1f}"
    return f"{v:.{decimals}f}"

def fmt_pct(v, show_sign=True):
    if v is None:
        return "—"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%"

def fmt_pt(v, decimals=2):
    if v is None:
        return ""
    sign = "+" if v >= 0 else ""
    if abs(v) >= 100:
        return f"{sign}{v:.0f}点"
    return f"{sign}{v:.{decimals}f}点"

def fmt_mcap(v):
    if not v:
        return ""
    if v >= 1e12:
        return f"市值 ${v/1e12:.1f}万亿"
    if v >= 1e9:
        return f"市值 ${v/1e9:.0f}亿"
    return ""

def pct_color(v):
    if v is None:
        return "#888"
    return "#00c47a" if v >= 0 else "#ff4d4d"

def arrow(v):
    if v is None:
        return ""
    return "▲" if v >= 0 else "▼"

def rec_label(r):
    m = {"strongBuy": "强力买入", "buy": "买入", "hold": "持有",
         "sell": "卖出", "strongSell": "强力卖出"}
    return m.get(r, "")

def near_52w_high(price, high, threshold=0.03):
    if price and high:
        return (high - price) / high < threshold
    return False

def near_52w_low(price, low, threshold=0.03):
    if price and low:
        return (price - low) / low < threshold
    return False


# ── 市场叙事生成 ──────────────────────────────────────
def generate_headline(data: dict) -> str:
    """从数据中提炼今日市场核心叙事"""
    parts = []

    sp = data.get("^GSPC", {})
    nq = data.get("^IXIC", {})
    dj = data.get("^DJI", {})
    vix = data.get("^VIX", {})
    n225 = data.get("^N225", {})
    jpy = data.get("JPY=X", {})
    gold = data.get("GC=F", {})
    oil = data.get("CL=F", {})
    tnx = data.get("^TNX", {})

    sp_chg  = sp.get("change_pct")
    nq_chg  = nq.get("change_pct")
    dj_chg  = dj.get("change_pct")
    vix_val = vix.get("price")
    n225_chg = n225.get("change_pct")
    jpy_val = jpy.get("price")
    gold_chg = gold.get("change_pct")
    oil_chg  = oil.get("change_pct")
    tnx_val  = tnx.get("price")

    # 美股整体判断
    us_chgs = [c for c in [sp_chg, nq_chg, dj_chg] if c is not None]
    if us_chgs:
        avg = sum(us_chgs) / len(us_chgs)
        all_up = all(c > 0.5 for c in us_chgs)
        all_down = all(c < -0.5 for c in us_chgs)
        if all_up and avg > 1.0:
            parts.append(f"美股三大指数集体大涨，S&P 500 {fmt_pct(sp_chg)}")
        elif all_up:
            parts.append(f"美股普涨，S&P 500 {fmt_pct(sp_chg)}")
        elif all_down and avg < -1.0:
            parts.append(f"美股三大指数集体下跌，S&P 500 {fmt_pct(sp_chg)}")
        elif all_down:
            parts.append(f"美股承压回落，S&P 500 {fmt_pct(sp_chg)}")
        else:
            parts.append(f"美股分化，S&P 500 {fmt_pct(sp_chg)}")

    # VIX 情绪
    if vix_val is not None:
        if vix_val >= 30:
            parts.append(f"VIX {vix_val:.1f} 市场恐慌情绪偏高")
        elif vix_val >= 20:
            parts.append(f"VIX {vix_val:.1f} 市场波动适中")
        elif vix_val < 14:
            parts.append(f"VIX {vix_val:.1f} 市场情绪极度平静")

    # 日股
    if n225_chg is not None:
        if abs(n225_chg) > 0.8:
            direction = "走强" if n225_chg > 0 else "走弱"
            parts.append(f"日经225 {direction} {fmt_pct(n225_chg)}")

    # 美元/日元
    if jpy_val is not None:
        if jpy_val >= 155:
            parts.append(f"日元偏弱，美元/日元 {jpy_val:.1f}")
        elif jpy_val <= 142:
            parts.append(f"日元走强，美元/日元 {jpy_val:.1f}")

    # 黄金
    if gold_chg is not None and abs(gold_chg) > 0.8:
        direction = "上涨" if gold_chg > 0 else "下跌"
        parts.append(f"黄金 {direction} {fmt_pct(gold_chg)}")

    # 原油
    if oil_chg is not None and abs(oil_chg) > 1.5:
        direction = "大涨" if oil_chg > 0 else "大跌"
        parts.append(f"原油 {direction} {fmt_pct(oil_chg)}")

    # 美债
    if tnx_val is not None:
        if tnx_val >= 4.8:
            parts.append(f"美债10Y利率 {tnx_val:.2f}% 处于高位")
        elif tnx_val <= 3.8:
            parts.append(f"美债10Y利率 {tnx_val:.2f}% 回落")

    if not parts:
        return "市场整体平稳，波动有限"
    return " · ".join(parts[:4])


def generate_stock_highlight(ticker: str, base: dict, detail: dict) -> str:
    """为单只股票生成亮点文字"""
    highlights = []
    yc = base.get("year_change")
    high52 = base.get("fifty_two_week_high")
    low52  = base.get("fifty_two_week_low")
    price  = base.get("price")
    target = detail.get("target_mean_price")
    mcap   = detail.get("market_cap")
    rec    = detail.get("recommendation", "")
    rev_g  = detail.get("revenue_growth")

    if mcap:
        highlights.append(fmt_mcap(mcap))

    if yc is not None:
        sign = "+" if yc >= 0 else ""
        highlights.append(f"年涨幅 {sign}{yc*100:.0f}%")

    if price and high52 and near_52w_high(price, high52):
        highlights.append("接近52周高点")
    elif price and low52 and near_52w_low(price, low52):
        highlights.append("⚠️ 接近52周低点")

    if price and target and price > 0:
        upside = (target - price) / price * 100
        if abs(upside) > 5:
            sign = "+" if upside >= 0 else ""
            highlights.append(f"分析师目标价 ${target:.0f}（{sign}{upside:.0f}%空间）")

    if rec and rec in ("strongBuy", "buy"):
        highlights.append(f"分析师评级：{rec_label(rec)}")

    if rev_g is not None and abs(rev_g) > 0.1:
        sign = "+" if rev_g >= 0 else ""
        highlights.append(f"营收增速 {sign}{rev_g*100:.0f}%")

    return "，".join(highlights[:3]) if highlights else "—"


def get_this_week_events():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    upcoming = []
    for ev_date_str, desc, level in MACRO_EVENTS:
        ev_date = date.fromisoformat(ev_date_str)
        if monday <= ev_date <= monday + timedelta(days=13):
            upcoming.append((ev_date, desc, level))
    return sorted(upcoming, key=lambda x: x[0])


# ── HTML 生成 ──────────────────────────────────────────
def build_html(data: dict, stock_details: dict) -> str:
    et_tz = pytz.timezone("America/New_York")
    now_et = datetime.now(et_tz)
    today_str = now_et.strftime("%Y-%m-%d")
    time_str  = now_et.strftime("%Y-%m-%d %H:%M ET")
    weekday   = ["周一","周二","周三","周四","周五","周六","周日"][now_et.weekday()]

    headline = generate_headline(data)

    # ── 大盘卡片 ──
    def index_card(ticker, cn_name, flag, en_name):
        d = data.get(ticker, {})
        price = d.get("price")
        chg_pct = d.get("change_pct")
        chg_pt  = d.get("change_pt")
        yc = d.get("year_change")
        col = pct_color(chg_pct)
        ar = arrow(chg_pct)
        price_str = fmt_price(price, 0 if price and price > 100 else 2)
        pt_str = fmt_pt(chg_pt, 0 if chg_pt and abs(chg_pt) > 10 else 2) if chg_pt else ""
        yc_str = f"年涨幅 {'+' if yc and yc>=0 else ''}{yc*100:.1f}%" if yc is not None else ""
        is_vix = ticker == "^VIX"
        sentiment = ""
        if is_vix and price:
            if price >= 30:   sentiment = "· 市场恐慌"
            elif price >= 20: sentiment = "· 波动偏高"
            else:             sentiment = "· 情绪平稳"
        return f"""
        <div class="idx-card">
          <div class="idx-header">
            <span class="idx-flag">{flag}</span>
            <span class="idx-name">{cn_name}</span>
            <span class="idx-en">{en_name}</span>
          </div>
          <div class="idx-price">{price_str}</div>
          <div class="idx-chg" style="color:{col}">
            {ar} {fmt_pct(chg_pct)} {pt_str}{sentiment}
          </div>
          <div class="idx-yc">{yc_str}</div>
        </div>"""

    us_cards = "".join(index_card(*row) for row in INDICES if row[2] == "🇺🇸")
    jp_cards = "".join(index_card(*row) for row in INDICES if row[2] == "🇯🇵")

    # ── 汇率大宗 ──
    def fx_row(ticker, name, icon):
        d = data.get(ticker, {})
        price = d.get("price")
        chg = d.get("change_pct")
        col = pct_color(chg)
        ar = arrow(chg)
        return f"""
        <div class="fx-row">
          <span class="fx-icon">{icon}</span>
          <span class="fx-name">{name}</span>
          <span class="fx-price">{fmt_price(price)}</span>
          <span class="fx-chg" style="color:{col}">{ar} {fmt_pct(chg)}</span>
        </div>"""

    fx_html = "".join(fx_row(t, n, i) for t, n, i in FX_COMMODITIES)

    # ── 板块ETF ──
    def sector_card(ticker, label, etf_code):
        d = data.get(ticker, {})
        c = d.get("change_pct")
        col = pct_color(c)
        bg = "rgba(0,196,122,0.10)" if (c or 0) >= 0 else "rgba(255,77,77,0.10)"
        ar = arrow(c)
        return f"""
        <div class="sc-card" style="background:{bg};border-color:{col}40">
          <div class="sc-label">{label}</div>
          <div class="sc-etf">{etf_code}</div>
          <div class="sc-pct" style="color:{col}">{ar} {fmt_pct(c)}</div>
        </div>"""

    sc_us = "".join(sector_card(*row) for row in SECTOR_ETFS_US)
    sc_jp = "".join(sector_card(*row) for row in SECTOR_ETFS_JP)

    # ── 个股表格 ──
    def stock_table(section_name, stocks):
        rows = ""
        for ticker, cn_name, en_name in stocks:
            d = data.get(ticker, {})
            price = d.get("price")
            chg = d.get("change_pct")
            col = pct_color(chg)
            ar = arrow(chg)
            price_str = fmt_price(price)
            chg_str = fmt_pct(chg)
            detail = stock_details.get(ticker, {})
            highlight = generate_stock_highlight(ticker, d, detail)
            currency = "¥" if ticker.endswith(".T") else "$"
            rows += f"""
            <tr>
              <td class="st-ticker">{ticker.replace('.T','')}</td>
              <td class="st-name"><span class="st-cn">{cn_name}</span><span class="st-en">{en_name}</span></td>
              <td class="st-price">{currency}{price_str}</td>
              <td class="st-chg" style="color:{col}">{ar} {chg_str}</td>
              <td class="st-hl">{highlight}</td>
            </tr>"""
        return f"""
        <div class="stock-section">
          <div class="ss-title">{section_name}</div>
          <table class="stock-table">
            <thead><tr>
              <th>代码</th><th>公司</th><th>最新价</th><th>涨跌幅</th><th>亮点</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>"""

    wl_us_html = "".join(stock_table(sec, stocks) for sec, stocks in WATCHLIST_US.items())
    wl_jp_html = "".join(stock_table(sec, stocks) for sec, stocks in WATCHLIST_JP.items())

    # ── 宏观事件 ──
    events = get_this_week_events()
    ev_html = ""
    if events:
        for ev_date, desc, level in events:
            days_away = (ev_date - date.today()).days
            if days_away == 0:   when = "今天"
            elif days_away == 1: when = "明天"
            elif days_away < 0:  when = f"{-days_away}天前"
            else:                when = ev_date.strftime("%m/%d")
            badge = '<span class="badge-high">重要</span>' if level == "high" else '<span class="badge-med">关注</span>'
            ev_html += f"""
            <div class="ev-row">
              <span class="ev-when">{when}</span>
              {badge}
              <span class="ev-desc">{desc}</span>
            </div>"""
    else:
        ev_html = '<div class="ev-empty">近两周暂无重大事件</div>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>美日金融市场 Daily Brief · {today_str}</title>
<style>
:root {{
  --bg: #0d1117;
  --surface: #161b22;
  --surface2: #1c2128;
  --border: #30363d;
  --text: #e6edf3;
  --muted: #8b949e;
  --green: #00c47a;
  --red: #ff4d4d;
  --accent: #58a6ff;
  --gold: #f0b429;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: var(--bg); color: var(--text); font-family: -apple-system,BlinkMacSystemFont,'PingFang SC','Segoe UI',sans-serif; font-size: 14px; padding: 24px; }}
.page {{ max-width: 1200px; margin: 0 auto; }}

/* ── Header ── */
.header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }}
.header-left {{ display: flex; align-items: center; gap: 12px; }}
.header-icon {{ font-size: 22px; }}
.header-title {{ font-size: 22px; font-weight: 800; color: var(--accent); }}
.header-date {{ font-size: 13px; color: var(--muted); background: var(--surface); border: 1px solid var(--border); border-radius: 20px; padding: 4px 12px; }}

/* ── Headline ── */
.headline {{ background: var(--surface2); border-left: 3px solid var(--gold); border-radius: 0 8px 8px 0; padding: 12px 16px; margin-bottom: 20px; font-size: 14px; color: #ddd; line-height: 1.6; }}
.headline-icon {{ color: var(--gold); margin-right: 6px; }}

/* ── Section title ── */
.section-title {{ font-size: 13px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: .6px; margin-bottom: 12px; display: flex; align-items: center; gap: 6px; }}
.section-title::after {{ content: ''; flex: 1; height: 1px; background: var(--border); margin-left: 8px; }}

/* ── Card ── */
.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 18px; }}

/* ── Index cards ── */
.idx-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; }}
.idx-card {{ background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 14px; }}
.idx-header {{ display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }}
.idx-flag {{ font-size: 14px; }}
.idx-name {{ font-size: 12px; color: var(--muted); }}
.idx-en {{ font-size: 11px; color: #444d56; margin-left: auto; }}
.idx-price {{ font-size: 22px; font-weight: 700; margin-bottom: 4px; font-variant-numeric: tabular-nums; }}
.idx-chg {{ font-size: 13px; font-weight: 600; margin-bottom: 3px; }}
.idx-yc {{ font-size: 11px; color: var(--muted); }}

/* ── FX ── */
.fx-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 6px; }}
.fx-row {{ display: flex; align-items: center; gap: 8px; padding: 7px 10px; background: var(--surface2); border-radius: 6px; }}
.fx-icon {{ width: 18px; text-align: center; font-size: 13px; }}
.fx-name {{ color: var(--muted); flex: 1; font-size: 13px; }}
.fx-price {{ font-variant-numeric: tabular-nums; font-size: 13px; }}
.fx-chg {{ font-weight: 600; font-size: 13px; min-width: 70px; text-align: right; font-variant-numeric: tabular-nums; }}

/* ── Sector ETF ── */
.sc-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 8px; }}
.sc-card {{ border: 1px solid; border-radius: 8px; padding: 12px 10px; text-align: center; }}
.sc-label {{ font-size: 12px; color: var(--muted); margin-bottom: 3px; }}
.sc-etf {{ font-size: 11px; color: #555; margin-bottom: 6px; }}
.sc-pct {{ font-size: 18px; font-weight: 700; }}

/* ── Stock table ── */
.stock-section {{ margin-bottom: 16px; }}
.ss-title {{ font-size: 13px; font-weight: 600; color: var(--accent); padding: 6px 0 8px 8px; border-left: 3px solid var(--accent); margin-bottom: 8px; }}
.stock-table {{ width: 100%; border-collapse: collapse; }}
.stock-table thead tr {{ border-bottom: 1px solid var(--border); }}
.stock-table th {{ padding: 7px 10px; text-align: left; font-size: 11px; color: var(--muted); font-weight: 600; letter-spacing: .3px; }}
.stock-table tbody tr {{ border-bottom: 1px solid #1a1f25; transition: background .15s; }}
.stock-table tbody tr:hover {{ background: var(--surface2); }}
.stock-table td {{ padding: 9px 10px; vertical-align: middle; }}
.st-ticker {{ font-weight: 700; color: var(--accent); font-size: 13px; width: 70px; }}
.st-name {{ width: 140px; }}
.st-cn {{ display: block; font-size: 13px; }}
.st-en {{ display: block; font-size: 11px; color: var(--muted); }}
.st-price {{ font-variant-numeric: tabular-nums; font-size: 14px; font-weight: 600; width: 90px; }}
.st-chg {{ font-weight: 700; font-size: 13px; width: 80px; font-variant-numeric: tabular-nums; }}
.st-hl {{ font-size: 12px; color: var(--muted); }}

/* ── Events ── */
.ev-row {{ display: flex; align-items: center; gap: 10px; padding: 9px 0; border-bottom: 1px solid var(--border); }}
.ev-row:last-child {{ border-bottom: none; }}
.ev-when {{ width: 44px; color: var(--muted); font-size: 13px; flex-shrink: 0; }}
.badge-high {{ background: rgba(255,77,77,.12); color: #ff4d4d; border: 1px solid rgba(255,77,77,.25); border-radius: 4px; padding: 1px 7px; font-size: 11px; flex-shrink: 0; }}
.badge-med  {{ background: rgba(88,166,255,.08); color: var(--accent); border: 1px solid rgba(88,166,255,.2); border-radius: 4px; padding: 1px 7px; font-size: 11px; flex-shrink: 0; }}
.ev-desc {{ font-size: 13px; flex: 1; }}
.ev-empty {{ color: var(--muted); padding: 12px 0; font-size: 13px; }}

/* ── Layout ── */
.mb16 {{ margin-bottom: 16px; }}
.row2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }}
.data-source {{ font-size: 11px; color: var(--muted); text-align: right; margin-top: 4px; }}

@media (max-width: 800px) {{
  .row2 {{ grid-template-columns: 1fr; }}
  .idx-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}
</style>
</head>
<body>
<div class="page">

  <!-- Header -->
  <div class="header">
    <div class="header-left">
      <span class="header-icon">📊</span>
      <span class="header-title">美日金融市场 Daily Brief</span>
    </div>
    <span class="header-date">📅 {today_str} · {weekday}</span>
  </div>

  <!-- Headline -->
  <div class="headline">
    <span class="headline-icon">⚡</span>{headline}
  </div>

  <!-- 大盘指数 -->
  <div class="row2">
    <div class="card mb16" style="margin-bottom:0">
      <div class="section-title">🇺🇸 美国大盘</div>
      <div class="idx-grid">{us_cards}</div>
      <div class="data-source">数据源：Yahoo Finance · {time_str}</div>
    </div>
    <div class="card" style="margin-bottom:0">
      <div class="section-title">🇯🇵 日本大盘</div>
      <div class="idx-grid">{jp_cards}</div>
    </div>
  </div>

  <!-- 汇率 & 大宗商品 -->
  <div class="card mb16" style="margin-top:16px">
    <div class="section-title">💱 汇率 · 债券 · 大宗商品</div>
    <div class="fx-grid">{fx_html}</div>
  </div>

  <!-- 板块 ETF -->
  <div class="row2">
    <div class="card">
      <div class="section-title">🔥 美国板块 ETF</div>
      <div class="sc-grid">{sc_us}</div>
    </div>
    <div class="card">
      <div class="section-title">🔥 日本板块 ETF</div>
      <div class="sc-grid">{sc_jp}</div>
    </div>
  </div>

  <!-- 个股 Watchlist -->
  <div class="row2" style="margin-top:16px">
    <div class="card">
      <div class="section-title">📈 美股 Watchlist</div>
      {wl_us_html}
    </div>
    <div class="card">
      <div class="section-title">📈 日股 Watchlist</div>
      {wl_jp_html}
    </div>
  </div>

  <!-- 宏观事件 -->
  <div class="card" style="margin-top:16px">
    <div class="section-title">📅 近期宏观事件</div>
    {ev_html}
  </div>

</div>
</body>
</html>"""


# ── 主程序 ─────────────────────────────────────────────
def main():
    print("正在拉取市场数据...")

    all_tickers = list(dict.fromkeys(
        [t for t, *_ in INDICES] +
        [t for t, *_ in FX_COMMODITIES] +
        [t for t, *_ in SECTOR_ETFS_US] +
        [t for t, *_ in SECTOR_ETFS_JP] +
        [t for stocks in WATCHLIST_US.values() for t, *_ in stocks] +
        [t for stocks in WATCHLIST_JP.values() for t, *_ in stocks]
    ))

    data = fetch_all(all_tickers)
    print(f"行情数据拉取完成，共 {len(data)} 个标的")

    # 拉取个股详情（分析师目标价等）
    stock_tickers = list(dict.fromkeys(
        [t for stocks in WATCHLIST_US.values() for t, *_ in stocks] +
        [t for stocks in WATCHLIST_JP.values() for t, *_ in stocks]
    ))
    print(f"正在拉取 {len(stock_tickers)} 只个股详情...")
    stock_details = {}
    for t in stock_tickers:
        stock_details[t] = fetch_stock_detail(t)
    print("个股详情拉取完成")

    html = build_html(data, stock_details)

    et_tz = pytz.timezone("America/New_York")
    today_str = datetime.now(et_tz).strftime("%Y-%m-%d")
    output_path = os.path.join(OUTPUT_DIR, f"daily_brief_{today_str}.html")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ 已保存: {output_path}")
    return output_path


if __name__ == "__main__":
    main()
