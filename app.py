import sqlite3
import os
import re
import csv
import io
import json
import imaplib
import email
import xml.etree.ElementTree as ET
from email.header import decode_header
from datetime import datetime, date, timedelta
from collections import defaultdict
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
DB = os.path.join(os.path.dirname(__file__), "data.db")

# --- Known merchants (China mainstream + essential Apple/intl services) ---
# Order matters: more specific patterns must come before generic ones
MERCHANT_PATTERNS = {
    # === Apple (保留) ===
    "Apple Music": ["apple music"],
    "Apple TV+": ["apple tv"],
    "Apple App Store": ["app store", "appstore", "apple store"],
    "Apple iCloud": ["icloud", "apple services", "apple service", "apple.com/bill", "apple.com", "apple 扣费", "apple 消费", "apple"],

    # === AI 工具 ===
    "ChatGPT": ["openai", "chatgpt", "chat.gpt", "gpt-4", "gpt plus"],
    "Claude": ["anthropic", "claude"],
    "DeepSeek": ["deepseek"],
    "Kimi": ["kimi", "月之暗面", "moonshot"],
    "豆包": ["豆包", "doubao"],
    "文心一言": ["文心一言", "文心", "ernie bot"],
    "通义千问": ["通义千问", "通义", "tongyi"],
    "GitHub Copilot": ["github copilot", "copilot"],
    "Midjourney": ["midjourney"],
    "Cursor": ["cursor"],
    "秘塔AI": ["秘塔", "metaso"],

    # === 视频娱乐 ===
    "爱奇艺": ["爱奇艺", "iqiyi", "奇异果"],
    "腾讯视频": ["腾讯视频", "tencent video"],
    "优酷": ["优酷", "youku", "酷喵"],
    "芒果TV": ["芒果tv", "mgtv"],
    "哔哩哔哩": ["bilibili", "哔哩哔哩", "b站大会员", "b站"],
    "抖音": ["抖音", "douyin"],
    "快手": ["快手", "kuaishou"],

    # === 音乐/音频 ===
    "QQ音乐": ["qq音乐", "qq music", "qq音乐会员"],
    "网易云音乐": ["网易云音乐", "网易云", "netease cloud music"],
    "酷狗音乐": ["酷狗音乐", "酷狗", "kugou"],
    "喜马拉雅": ["喜马拉雅", "xmly", "himalaya"],
    "荔枝FM": ["荔枝", "荔枝fm", "lizhi"],
    "汽水音乐": ["汽水音乐"],

    # === 阅读/知识 ===
    "微信读书": ["微信读书", "weread"],
    "得到": ["得到", "dedao", "iget"],
    "樊登读书": ["樊登读书", "樊登"],
    "知乎盐选": ["知乎盐选", "知乎会员", "盐选"],
    "起点读书": ["起点读书", "起点", "qidian"],
    "番茄小说": ["番茄小说", "番茄免费小说"],
    "豆瓣": ["豆瓣", "douban"],

    # === 云存储 ===
    "百度网盘": ["百度网盘", "baidu wangpan", "baidunetdisk", "百度云", "百度网盘svip"],
    "阿里云盘": ["阿里云盘", "aliyundrive"],
    "夸克网盘": ["夸克网盘", "夸克", "quark"],
    "腾讯微云": ["微云", "weiyun"],
    "iCloud": ["icloud", "apple services", "apple service", "apple.com/bill", "apple.com", "apple 扣费", "apple 消费", "apple"],

    # === 效率办公 ===
    "WPS": ["wps", "金山文档", "wps会员"],
    "飞书": ["飞书", "feishu", "lark"],
    "钉钉": ["钉钉", "dingtalk"],
    "腾讯会议": ["腾讯会议", "tencent meeting", "voov"],
    "石墨文档": ["石墨文档", "石墨", "shimo"],
    "印象笔记": ["印象笔记", "evernote", "yinxiang"],
    "Notion": ["notion"],
    "幕布": ["幕布", "mubu"],
    "ProcessOn": ["processon"],

    # === 购物 ===
    "京东Plus": ["京东plus", "jd plus", "京东会员"],
    "淘宝88VIP": ["88vip", "88 vip", "淘宝会员"],
    "拼多多": ["拼多多", "pinduoduo", "拼多多会员"],
    "唯品会": ["唯品会", "vipshop"],

    # === 外卖/生活 ===
    "美团会员": ["美团会员", "美团外卖会员", "美团外卖"],
    "饿了么会员": ["饿了么会员", "饿了么超级会员", "饿了吗", "饿了么"],
    "盒马": ["盒马", "盒马鲜生", "hema", "freshippo"],
    "叮咚买菜": ["叮咚买菜", "叮咚"],
    "大众点评": ["大众点评", "点评", "dianping"],

    # === 社交/社区 ===
    "微博会员": ["微博会员", "微博", "weibo"],
    "小红书": ["小红书", "redbook", "xiaohongshu"],
    "知识星球": ["知识星球", "zsxq"],
    "QQ会员": ["qq会员", "qq超级会员", "qq vip", "qq svip"],

    # === 健身 ===
    "Keep会员": ["keep会员", "keep 会员", "keep"],
    "乐刻": ["乐刻", "乐刻运动", "leke"],

    # === 游戏 ===
    "Steam": ["steam"],

    # === 云服务/开发 ===
    "阿里云": ["阿里云", "aliyun"],
    "腾讯云": ["腾讯云", "tencent cloud", "qcloud"],
    "Vercel": ["vercel"],
    "GitHub": ["github", "github pro"],

    # === 国际服务（中国用户常用） ===
    "Netflix": ["netflix", "奈飞"],
    "Spotify": ["spotify"],
    "YouTube Premium": ["youtube premium", "youtube music"],
    "Disney+": ["disney+", "disney plus"],
    "Adobe": ["adobe", "photoshop", "premiere"],
    "Microsoft 365": ["microsoft 365", "office 365", "m365"],
    "Google One": ["google one", "google storage"],
    "AWS": ["aws", "amazon web services"],
    "Duolingo": ["duolingo", "多邻国"],
}

CATEGORY_MAP = {
    # AI工具
    "ChatGPT": "AI工具", "Claude": "AI工具", "DeepSeek": "AI工具",
    "Kimi": "AI工具", "豆包": "AI工具", "文心一言": "AI工具", "通义千问": "AI工具",
    "GitHub Copilot": "AI工具", "Midjourney": "AI工具", "Cursor": "AI工具", "秘塔AI": "AI工具",
    # 视频娱乐
    "爱奇艺": "视频娱乐", "腾讯视频": "视频娱乐", "优酷": "视频娱乐", "芒果TV": "视频娱乐",
    "哔哩哔哩": "视频娱乐", "抖音": "视频娱乐", "快手": "视频娱乐",
    "Netflix": "视频娱乐", "YouTube Premium": "视频娱乐", "Disney+": "视频娱乐",
    # 音乐
    "QQ音乐": "音乐", "网易云音乐": "音乐", "酷狗音乐": "音乐", "喜马拉雅": "音乐",
    "荔枝FM": "音乐", "汽水音乐": "音乐", "Spotify": "音乐", "Apple Music": "音乐",
    # 阅读
    "微信读书": "阅读", "得到": "阅读", "樊登读书": "阅读", "知乎盐选": "阅读",
    "起点读书": "阅读", "番茄小说": "阅读", "豆瓣": "阅读",
    # 云存储
    "百度网盘": "云存储", "阿里云盘": "云存储", "夸克网盘": "云存储",
    "腾讯微云": "云存储", "iCloud": "云存储",
    "Google One": "云存储", "阿里云": "云存储", "腾讯云": "云存储", "AWS": "云存储",
    # 效率办公
    "WPS": "效率办公", "飞书": "效率办公", "钉钉": "效率办公", "腾讯会议": "效率办公",
    "石墨文档": "效率办公", "印象笔记": "效率办公", "Notion": "效率办公",
    "幕布": "效率办公", "ProcessOn": "效率办公",
    "Adobe": "效率办公", "Microsoft 365": "效率办公",
    # 购物
    "京东Plus": "购物", "淘宝88VIP": "购物", "拼多多": "购物", "唯品会": "购物",
    # 外卖生活
    "美团会员": "外卖生活", "饿了么会员": "外卖生活", "盒马": "外卖生活",
    "叮咚买菜": "外卖生活", "大众点评": "外卖生活",
    # 社交社区
    "微博会员": "社交社区", "小红书": "社交社区", "知识星球": "社交社区", "QQ会员": "社交社区",
    # 健身
    "Keep会员": "健身", "乐刻": "健身",
    # 游戏
    "Steam": "游戏",
    # 开发服务
    "Vercel": "开发服务", "GitHub": "开发服务",
    # 教育
    "Duolingo": "教育",
    # Apple
    "Apple iCloud": "云存储", "Apple Music": "音乐", "Apple TV+": "视频娱乐", "Apple App Store": "App Store",
}

# --- Bank SMS patterns (Chinese banks) ---
BANK_SMS_PATTERNS = [
    # 尾号XXXX卡 消费/支出/扣款 XX元
    re.compile(r'(?:您|你|尊敬的用户).*?(?:尾号|卡号|账户).*?(\d{4}).*?(?:消费|支出|扣款|扣费|支付|交易).*?(\d+(?:\.\d{1,2})?)元'),
    # 【XX银行】消费/支出
    re.compile(r'【.{0,8}(?:银行|支付)】.*?(?:消费|支出|扣款).*?(\d+(?:\.\d{1,2})?)元'),
    # 通用: XX元 支出/消费
    re.compile(r'(?:支出|消费|扣款|支付|付费|续费).*?(\d+(?:\.\d{1,2})?)元'),
    # 通用: $XX.XX / ¥XX
    re.compile(r'[$¥￥]\s*(\d+(?:\.\d{1,2})?)'),
    # 人民币XX元
    re.compile(r'(?:人民币|CNY)\s*(\d+(?:\.\d{1,2})?)元?'),
]

# --- Date patterns in SMS ---
SMS_DATE_PATTERNS = [
    re.compile(r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})日?'),
    re.compile(r'(\d{1,2})月(\d{1,2})日'),
    re.compile(r'(\d{4})-(\d{2})-(\d{2})'),
]


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '其他',
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'CNY',
                cycle TEXT NOT NULL DEFAULT 'monthly',
                next_renewal TEXT,
                notes TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'CNY',
                tx_date TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'manual',
                raw_data TEXT
            )
        """)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def detect_merchant(text: str):
    lower = text.lower()
    for name, patterns in MERCHANT_PATTERNS.items():
        for p in patterns:
            if p in lower:
                return name, CATEGORY_MAP.get(name, "其他")
    return None, None


def parse_amount(s: str) -> float:
    s = s.strip().replace("¥", "").replace("$", "").replace("€", "").replace("￥", "").replace(",", "").replace(" ", "")
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    s = re.sub(r'^(支出|收入|支|收)\s*', '', s)
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_date(s: str) -> str:
    s = s.strip()
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y年%m月%d日", "%m/%d/%Y", "%d/%m/%Y"]:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s.split(" ")[0].split("T")[0]


def detect_currency(text: str) -> str:
    """Detect currency from text. Default CNY for Chinese content."""
    # CNY indicators (check first, most common)
    if re.search(r'¥|￥|元|人民币|CNY', text):
        return "CNY"
    # Foreign currency indicators
    if re.search(r'\$|USD|US\$', text) and not re.search(r'¥|￥|元', text):
        return "USD"
    if re.search(r'€|EUR', text):
        return "EUR"
    if re.search(r'HK\$|HKD|港元|港币', text):
        return "HKD"
    return "CNY"  # default CNY


# ---------------------------------------------------------------------------
#  Smart text parser: SMS, notifications, free-form billing text
# ---------------------------------------------------------------------------

def parse_sms_text(text: str) -> list[dict]:
    """Parse a single SMS or billing notification into structured transaction data."""
    results = []
    text_clean = text.replace("\n", " ").replace("\r", " ")

    # Try bank SMS patterns for amounts
    amounts = []
    for pat in BANK_SMS_PATTERNS:
        for m in pat.finditer(text_clean):
            try:
                amount = float(m.group(2)) if len(m.groups()) >= 2 else float(m.group(1))
                if 1 < amount < 50000:
                    amounts.append(amount)
            except (ValueError, IndexError):
                continue

    # Also try generic amount extraction
    generic_amounts = re.findall(r'(?:¥|￥|\$|USD|元|美元)?\s*(\d+(?:\.\d{1,2})?)\s*(?:元|USD|CNY|美元)?', text_clean)
    for a in generic_amounts:
        try:
            val = float(a)
            if 1 < val < 50000 and val not in amounts:
                amounts.append(val)
        except ValueError:
            continue

    # Detect merchant
    name, cat = detect_merchant(text_clean)

    # Detect date
    tx_date = date.today().isoformat()
    for pat in SMS_DATE_PATTERNS:
        m = pat.search(text_clean)
        if m:
            try:
                if len(m.groups()) == 3:
                    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                else:
                    y = date.today().year
                    mo, d = int(m.group(1)), int(m.group(2))
                tx_date = date(y, mo, d).isoformat()
                break
            except ValueError:
                continue

    currency = detect_currency(text_clean)

    # If we found a known merchant
    if name:
        # Use the first reasonable amount
        amount = amounts[0] if amounts else 0
        results.append({
            "merchant": name,
            "category": cat,
            "amount": amount,
            "currency": currency,
            "date": tx_date,
            "raw": text[:300],
        })
    elif amounts:
        # Unknown merchant but has amount — try to extract merchant name from text
        # Common patterns: "XXX扣费", "XXX续费", "XXX会员"
        merchant_match = re.search(r'(?:【?\s*([^】\]]+?)\s*】?.*?)(?:扣费|续费|会员|订阅|支付|付款)', text_clean)
        if merchant_match:
            candidate = merchant_match.group(1).strip()
            if len(candidate) > 1 and len(candidate) < 30:
                name2, cat2 = detect_merchant(candidate)
                results.append({
                    "merchant": name2 or candidate,
                    "category": cat2 or "其他",
                    "amount": amounts[0],
                    "currency": currency,
                    "date": tx_date,
                    "raw": text[:300],
                })
        else:
            # Generic: treat whole text as source
            results.append({
                "merchant": "未知商户",
                "category": "其他",
                "amount": amounts[0],
                "currency": currency,
                "date": tx_date,
                "raw": text[:300],
            })

    return results


# ---------------------------------------------------------------------------
#  SMS backup parsers
# ---------------------------------------------------------------------------

def parse_sms_xml(file_stream) -> list[dict]:
    """Parse Android SMS XML backup file."""
    text = file_stream.read().decode("utf-8-sig")
    root = ET.fromstring(text)
    transactions = []

    for sms in root.iter("sms"):
        body = sms.get("body", "")
        date_ms = sms.get("date", "0")
        if not body:
            continue

        # Convert millisecond timestamp to date
        try:
            ts = int(date_ms) / 1000
            tx_date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        except (ValueError, OSError):
            tx_date = date.today().isoformat()

        parsed = parse_sms_text(body)
        for p in parsed:
            p["date"] = p.get("date") or tx_date
            transactions.append(p)

    return transactions


def parse_sms_csv(file_stream) -> list[dict]:
    """Parse iOS SMS export CSV (from iMazing or similar tools)."""
    text = file_stream.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    transactions = []

    for row in reader:
        body = row.get("Body") or row.get("body") or row.get("Text") or row.get("text") or row.get("内容") or ""
        date_str = row.get("Date") or row.get("date") or row.get("日期") or row.get("Sent") or ""

        if not body:
            continue

        tx_date = parse_date(date_str) if date_str else date.today().isoformat()
        parsed = parse_sms_text(body)
        for p in parsed:
            p["date"] = p.get("date") or tx_date
            transactions.append(p)

    return transactions


# ---------------------------------------------------------------------------
#  Routes: CRUD
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def stats():
    with get_db() as conn:
        monthly = conn.execute("SELECT SUM(amount) FROM subscriptions WHERE status='active' AND cycle='monthly'").fetchone()[0] or 0
        yearly_raw = conn.execute("SELECT SUM(amount) FROM subscriptions WHERE status='active' AND cycle='yearly'").fetchone()[0] or 0
        quarterly = conn.execute("SELECT SUM(amount) FROM subscriptions WHERE status='active' AND cycle='quarterly'").fetchone()[0] or 0
        weekly = conn.execute("SELECT SUM(amount) FROM subscriptions WHERE status='active' AND cycle='weekly'").fetchone()[0] or 0
        total_monthly = round(monthly + yearly_raw / 12 + quarterly / 3 + weekly * 4.33, 2)
        active_count = conn.execute("SELECT COUNT(*) FROM subscriptions WHERE status='active'").fetchone()[0]
        total_count = conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0]
        cat_breakdown = conn.execute("SELECT category, SUM(amount) as total FROM subscriptions WHERE status='active' GROUP BY category ORDER BY total DESC").fetchall()
        upcoming = conn.execute("SELECT * FROM subscriptions WHERE status='active' AND next_renewal IS NOT NULL ORDER BY next_renewal ASC LIMIT 5").fetchall()

    return jsonify({
        "total_monthly": total_monthly,
        "total_yearly": round(total_monthly * 12, 2),
        "active_count": active_count,
        "total_count": total_count,
        "category_breakdown": [{"category": r["category"], "total": round(r["total"], 2)} for r in cat_breakdown],
        "upcoming": [dict(r) for r in upcoming],
    })


@app.route("/api/subscriptions")
def list_subscriptions():
    category = request.args.get("category", "")
    status = request.args.get("status", "active")
    query = "SELECT * FROM subscriptions WHERE 1=1"
    params = []
    if category:
        query += " AND category = ?"; params.append(category)
    if status != "all":
        query += " AND status = ?"; params.append(status)
    query += " ORDER BY next_renewal ASC"
    with get_db() as conn:
        return jsonify([dict(r) for r in conn.execute(query, params).fetchall()])


@app.route("/api/subscriptions", methods=["POST"])
def create_subscription():
    data = request.json
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO subscriptions (name, category, amount, currency, cycle, next_renewal, notes, status) VALUES (?,?,?,?,?,?,?,?)",
            (data["name"], data.get("category", "其他"), data["amount"], data.get("currency", "CNY"),
             data.get("cycle", "monthly"), data.get("next_renewal"), data.get("notes", ""), data.get("status", "active")),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM subscriptions WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/subscriptions/<int:sid>", methods=["PUT"])
def update_subscription(sid):
    data = request.json
    with get_db() as conn:
        conn.execute(
            "UPDATE subscriptions SET name=?,category=?,amount=?,currency=?,cycle=?,next_renewal=?,notes=?,status=?,updated_at=datetime('now','localtime') WHERE id=?",
            (data["name"], data.get("category", "其他"), data["amount"], data.get("currency", "CNY"),
             data.get("cycle", "monthly"), data.get("next_renewal"), data.get("notes", ""), data.get("status", "active"), sid),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM subscriptions WHERE id = ?", (sid,)).fetchone()
    return jsonify(dict(row))


@app.route("/api/subscriptions/<int:sid>", methods=["DELETE"])
def delete_subscription(sid):
    with get_db() as conn:
        conn.execute("DELETE FROM subscriptions WHERE id = ?", (sid,))
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/categories")
def categories():
    with get_db() as conn:
        rows = conn.execute("SELECT DISTINCT category FROM subscriptions ORDER BY category").fetchall()
    return jsonify([r["category"] for r in rows])


# ---------------------------------------------------------------------------
#  Smart text parse endpoint
# ---------------------------------------------------------------------------

@app.route("/api/parse/text", methods=["POST"])
def parse_text():
    """Parse free-form billing text (SMS, email, notification) and extract subscriptions."""
    text = request.json.get("text", "").strip()
    if not text:
        return jsonify({"error": "请输入文本"}), 400

    # Split by lines if multiple messages pasted
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    all_results = []

    # If it looks like multiple SMS messages (each line is a message), parse each separately
    for line in lines:
        results = parse_sms_text(line)
        all_results.extend(results)

    # If no results from individual lines, try the whole text as one
    if not all_results:
        all_results = parse_sms_text(text)

    # Deduplicate by merchant
    seen = set()
    unique = []
    for r in all_results:
        key = r["merchant"]
        if key not in seen:
            seen.add(key)
            # Estimate cycle
            cycle = "monthly"
            name = r["merchant"]
            unique.append({
                "name": name,
                "category": r["category"],
                "amount": r["amount"],
                "currency": r["currency"],
                "cycle": cycle,
                "next_renewal": r["date"],
                "notes": r["raw"][:100],
            })

    return jsonify({
        "total_found": len(unique),
        "subscriptions": unique,
    })


# ---------------------------------------------------------------------------
#  SMS backup upload
# ---------------------------------------------------------------------------

@app.route("/api/import/sms", methods=["POST"])
def import_sms():
    """Upload SMS backup file (Android XML or iOS CSV)."""
    if "file" not in request.files:
        return jsonify({"error": "未上传文件"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "空文件"}), 400

    filename = file.filename.lower()
    try:
        if filename.endswith(".xml"):
            transactions = parse_sms_xml(file)
        elif filename.endswith(".csv"):
            transactions = parse_sms_csv(file)
        else:
            return jsonify({"error": "不支持的文件格式，请上传 XML 或 CSV 文件"}), 400
    except ET.ParseError as e:
        return jsonify({"error": f"XML 解析失败: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"文件解析失败: {str(e)}"}), 400

    if not transactions:
        return jsonify({"error": "未从短信中识别出账单信息"}), 400

    # Save transactions
    with get_db() as conn:
        for tx in transactions:
            conn.execute(
                "INSERT INTO transactions (merchant, amount, currency, tx_date, source, raw_data) VALUES (?,?,?,?,?,?)",
                (tx["merchant"], tx["amount"], tx.get("currency", "CNY"), tx["date"], "sms", tx.get("raw", "")),
            )
        conn.commit()

    # For SMS: return all known-merchant transactions as subscriptions (even single occurrence)
    # For unknown merchants: still require recurring pattern
    known = []; unknown = []
    for tx in transactions:
        name, cat = detect_merchant(tx.get("raw", tx["merchant"]))
        if name:
            known.append(tx)
        else:
            unknown.append(tx)

    found = []
    seen_known = set()
    for tx in known:
        name, cat = detect_merchant(tx.get("raw", tx["merchant"]))
        if name and name not in seen_known:
            seen_known.add(name)
            currency = tx.get("currency", detect_currency(tx.get("raw", "")))
            found.append({
                "name": name, "category": cat, "amount": tx["amount"],
                "currency": currency, "cycle": "monthly",
                "next_renewal": tx["date"], "occurrences": 1,
                "date_range": tx["date"],
            })

    # For unknowns, still do recurring detection
    recur = detect_recurring(unknown)
    found.extend(recur)

    return jsonify({
        "total_transactions": len(transactions),
        "detected_subscriptions": len(found),
        "subscriptions": found,
    })


# ---------------------------------------------------------------------------
#  CSV import (unchanged)
# ---------------------------------------------------------------------------

def parse_csv_file(file_stream) -> list[dict]:
    text = file_stream.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    headers = [h.lower().strip() for h in (reader.fieldnames or [])]
    col_map = {}
    for h in headers:
        if any(k in h for k in ["交易对方", "商户", "merchant", "对方", "交易对象", "商品", "description", "name"]):
            col_map.setdefault("merchant", h)
        if any(k in h for k in ["金额", "amount", "金额(元)", "交易金额"]):
            col_map.setdefault("amount", h)
        if any(k in h for k in ["交易时间", "时间", "date", "time", "日期"]):
            col_map.setdefault("date", h)
        if any(k in h for k in ["收/支", "收支", "类型", "type", "交易类型"]):
            col_map.setdefault("type", h)
        if any(k in h for k in ["商品说明", "商品", "备注", "memo", "note", "说明"]):
            col_map.setdefault("memo", h)

    if "merchant" not in col_map and "amount" not in col_map:
        field_names = reader.fieldnames or []
        if len(field_names) >= 3:
            col_map = {"date": field_names[0], "merchant": field_names[1], "amount": field_names[-2]}

    rows = []
    for row in reader:
        merchant = row.get(col_map.get("merchant", ""), "").strip()
        amount_raw = row.get(col_map.get("amount", ""), "0").strip()
        date_raw = row.get(col_map.get("date", ""), "").strip()
        memo = row.get(col_map.get("memo", ""), "").strip()
        tx_type = row.get(col_map.get("type", ""), "").strip()

        if not merchant or not amount_raw:
            continue
        amount = parse_amount(amount_raw)
        if "收入" in tx_type:
            continue
        amount = abs(amount)
        if amount < 0.01:
            continue
        tx_date = parse_date(date_raw) if date_raw else date.today().isoformat()
        rows.append({"merchant": merchant, "amount": round(amount, 2), "date": tx_date, "raw": f"{merchant} | {memo} | {tx_type} | {amount_raw}"})
    return rows


def detect_recurring(transactions: list[dict]) -> list[dict]:
    by_merchant = defaultdict(list)
    for tx in transactions:
        name, cat = detect_merchant(tx["raw"])
        key = name or tx["merchant"]
        by_merchant[key].append(tx)

    found = []
    for merchant, txs in by_merchant.items():
        if len(txs) < 2:
            continue
        amounts = [t["amount"] for t in txs]
        avg_amount = sum(amounts) / len(amounts)
        consistent = all(abs(a - avg_amount) / max(avg_amount, 0.01) < 0.15 for a in amounts)
        if not consistent:
            continue

        name, cat = detect_merchant(merchant)
        if name is None:
            name = merchant; cat = "其他"

        dates = sorted(set(t["date"] for t in txs))
        cycle = "monthly"
        if len(dates) >= 2:
            d1 = datetime.strptime(dates[0], "%Y-%m-%d")
            d2 = datetime.strptime(dates[-1], "%Y-%m-%d")
            avg_interval = (d2 - d1).days / (len(dates) - 1)
            if avg_interval > 300: cycle = "yearly"
            elif avg_interval > 70: cycle = "quarterly"
            elif avg_interval < 10: cycle = "weekly"

        last_date = max(dates)
        found.append({
            "name": name, "category": cat, "amount": round(avg_amount, 2),
            "currency": "CNY", "cycle": cycle, "next_renewal": last_date,
            "occurrences": len(txs), "date_range": f"{min(dates)} ~ {max(dates)}",
        })
    return found


@app.route("/api/import/csv", methods=["POST"])
def import_csv():
    if "file" not in request.files:
        return jsonify({"error": "未上传文件"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "空文件"}), 400
    try:
        transactions = parse_csv_file(file)
    except Exception as e:
        return jsonify({"error": f"CSV 解析失败: {str(e)}"}), 400
    if not transactions:
        return jsonify({"error": "未能从文件中识别出交易记录，请检查格式"}), 400

    with get_db() as conn:
        for tx in transactions:
            conn.execute("INSERT INTO transactions (merchant, amount, currency, tx_date, source, raw_data) VALUES (?,?,?,?,?,?)",
                         (tx["merchant"], tx["amount"], "CNY", tx["date"], "csv", tx["raw"]))
        conn.commit()

    found = detect_recurring(transactions)
    return jsonify({"total_transactions": len(transactions), "detected_subscriptions": len(found), "subscriptions": found})


# ---------------------------------------------------------------------------
#  Email IMAP scanning
# ---------------------------------------------------------------------------

EMAIL_CONFIG = {}

def decode_email_header(value) -> str:
    if value is None: return ""
    parts = decode_header(value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try: result.append(part.decode(charset or "utf-8", errors="replace"))
            except: result.append(part.decode("utf-8", errors="replace"))
        else: result.append(str(part))
    return " ".join(result)


def scan_emails(host: str, email_addr: str, password: str, days: int = 90) -> list[dict]:
    search_senders = ["apple.com", "netflix.com", "spotify.com", "openai.com", "google.com", "microsoft.com", "adobe.com", "notion.so", "github.com", "dropbox.com", "figma.com", "midjourney.com", "anthropic.com", "deepseek.com"]
    search_subjects = ["receipt", "invoice", "bill", "subscription", "renewal", "收据", "账单", "发票", "订阅", "续费", "扣款", "支付"]
    try:
        mail = imaplib.IMAP4_SSL(host, 993)
        mail.login(email_addr, password)
        mail.select("INBOX")
    except Exception as e:
        raise RuntimeError(f"邮箱连接失败: {str(e)}")

    since_date = (date.today() - timedelta(days=days)).strftime("%d-%b-%Y")
    found = []; seen = set()

    try:
        for sender in search_senders:
            try:
                status, msg_ids = mail.search(None, f'(FROM "{sender}" SINCE {since_date})')
                if status == "OK":
                    for mid in msg_ids[0].split():
                        _process_email(mail, mid, found, seen)
            except: continue
        for subj in search_subjects:
            try:
                status, msg_ids = mail.search(None, f'(SUBJECT "{subj}" SINCE {since_date})')
                if status == "OK":
                    for mid in msg_ids[0].split():
                        _process_email(mail, mid, found, seen)
            except: continue
    finally:
        try: mail.close(); mail.logout()
        except: pass
    return found


def _process_email(mail, msg_id, found: list, seen: set):
    try:
        status, data = mail.fetch(msg_id, "(RFC822)")
        if status != "OK": return
        msg = email.message_from_bytes(data[0][1])
    except: return

    subject = decode_email_header(msg["Subject"])
    sender = decode_email_header(msg.get("From", ""))
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() in ("text/plain", "text/html"):
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode(part.get_content_charset() or "utf-8", errors="replace") + "\n"
                except: continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload: body = payload.decode("utf-8", errors="replace")
        except: pass

    combined = f"{subject} {sender} {body[:2000]}"
    name, cat = detect_merchant(combined)
    if name is None or name in seen: return
    seen.add(name)

    amounts = re.findall(r'(?:USD|US\$|\$|¥|￥|CNY|EUR|€)\s*(\d+(?:\.\d{1,2})?)', combined)
    amounts += re.findall(r'(\d+(?:\.\d{1,2})?)\s*(?:USD|CNY|EUR|元|美元|欧元)', combined)
    amount = float(amounts[0]) if amounts else 0

    currency = "CNY"
    if re.search(r'\$|USD|US\$', combined): currency = "USD"
    elif re.search(r'€|EUR', combined): currency = "EUR"

    cycle = "yearly" if re.search(r'annual|yearly|年|每年', combined, re.IGNORECASE) else "monthly"

    found.append({"name": name, "category": cat, "amount": amount, "currency": currency, "cycle": cycle, "source": "email", "subject": subject, "sender": sender[:80]})


@app.route("/api/email/config", methods=["POST"])
def save_email_config():
    data = request.json
    EMAIL_CONFIG["host"] = data.get("host", "imap.gmail.com")
    EMAIL_CONFIG["email"] = data.get("email", "")
    EMAIL_CONFIG["password"] = data.get("password", "")
    return jsonify({"ok": True})


@app.route("/api/email/scan", methods=["POST"])
def trigger_email_scan():
    if not EMAIL_CONFIG.get("email"):
        return jsonify({"error": "请先配置邮箱连接"}), 400
    try:
        results = scan_emails(EMAIL_CONFIG["host"], EMAIL_CONFIG["email"], EMAIL_CONFIG["password"],
                              days=int(request.json.get("days", 90)) if request.json else 90)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"扫描失败: {str(e)}"}), 500
    return jsonify({"total_found": len(results), "subscriptions": results})


# ---------------------------------------------------------------------------
#  Unified auto-scan: run all available scanners at once
# ---------------------------------------------------------------------------

@app.route("/api/auto-scan", methods=["POST"])
def auto_scan():
    """Run all available scanners. Requires prior config for email."""
    all_subs = []

    # 1. Email scan (if configured)
    if EMAIL_CONFIG.get("email"):
        try:
            email_results = scan_emails(EMAIL_CONFIG["host"], EMAIL_CONFIG["email"], EMAIL_CONFIG["password"], days=90)
            all_subs.extend(email_results)
        except Exception:
            pass  # email scan is best-effort

    # 2. Scan recently imported transactions for new patterns
    with get_db() as conn:
        recent = conn.execute(
            "SELECT * FROM transactions ORDER BY tx_date DESC LIMIT 500"
        ).fetchall()
    if recent:
        txs = [{"merchant": r["merchant"], "amount": r["amount"], "date": r["tx_date"], "raw": r["raw_data"] or r["merchant"]} for r in recent]
        csv_subs = detect_recurring(txs)
        all_subs.extend(csv_subs)

    # Deduplicate
    seen = set()
    unique = []
    for s in all_subs:
        if s["name"] not in seen:
            seen.add(s["name"])
            unique.append(s)

    return jsonify({"total_found": len(unique), "subscriptions": unique})


# ---------------------------------------------------------------------------
#  Batch import
# ---------------------------------------------------------------------------

@app.route("/api/subscriptions/batch-import", methods=["POST"])
def batch_import():
    items = request.json.get("items", [])
    count = 0
    with get_db() as conn:
        for item in items:
            conn.execute(
                "INSERT INTO subscriptions (name, category, amount, currency, cycle, next_renewal, notes, status) VALUES (?,?,?,?,?,?,?,'active')",
                (item["name"], item.get("category", "其他"), item["amount"], item.get("currency", "CNY"),
                 item.get("cycle", "monthly"), item.get("next_renewal"), item.get("notes", "")),
            )
            count += 1
        conn.commit()
    return jsonify({"imported": count})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=8765)
