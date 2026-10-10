"""
NLP 信息提取模块 — 从群聊文本中提取结构化商品信息 (Bilingual: Chinese + English)

输入: 群聊消息列表 [{sender, content, time}]
输出: 结构化 listing 列表 [{product_name, price, condition, seller, contact, description, category, location, source_text}]
"""

import json
import os
import re

# LLM 配置
try:
    from llm_config import llm_chat_json, llm_available
    _llm_ready = True
except ImportError:
    _llm_ready = False


# 非交易消息关键词 (Chinese + English)
NON_TRADE_KEYWORDS = [
    # Chinese
    "闲鱼", "请问", "感谢", "有没有人出", "求购", "有人出", "群里有",
    "多少钱", "怎么", "哪里", "推荐", "谢谢", "牛", "厉害", "大佬",
    # English
    "xianyu", "looking for", "budget around", "thanks",
    "repair", "selling fast", "is anyone", "anyone selling a",
    "is there", "how much", "anyone have",
]

# 出售关键词 (Chinese + English)
SELL_KEYWORDS = ["出", "出售", "出货", "出物", "转让", "闲置",
                 "selling", "for sale", "wts", "second-hand"]

# 品类关键词映射 (Chinese + English keywords)
CATEGORY_MAP = {
    "自行车": ["自行车", "捷安特", "美利达", "飞鸽", "永久", "山地车", "公路车", "ATX", "公爵",
              "bicycle", "bike", "giant", "merida", "duke", "forever", "flying pigeon"],
    "教材": ["课本", "高数", "高等数学", "线性代数", "物理学", "考研", "四级", "六级", "教材", "真题", "大纲",
            "textbook", "calculus", "linear algebra", "higher mathematics", "university physics",
            "cet-4", "past papers", "politics outline", "grad politics"],
    "电子产品": ["iPhone", "iPad", "Switch", "Kindle", "耳机", "鼠标", "笔记本电脑", "手环", "充电器", "降噪", "OLED", "RTX",
                "mouse", "laptop", "headphones", "band", "charger", "noise-canceling"],
    "生活用品": ["台灯", "牙刷", "电饭煲", "煮蛋器", "吉他", "日记本", "日记笔记本",
                "lamp", "toothbrush", "rice cooker", "egg cooker", "guitar", "notebook", "diary"],
}

# 中文地点关键词
LOCATIONS = ["校内", "南门", "北门", "东门", "西门", "东区", "西区", "南区", "北区"]

# English → Chinese location mapping
EN_LOCATIONS_MAP = {
    "on campus": "校内",
    "south gate": "南门",
    "north gate": "北门",
    "east gate": "东门",
    "west gate": "西门",
    "east area": "东区",
    "west area": "西区",
    "south area": "南区",
    "north area": "北区",
}


def is_trade_message(content):
    """判断是否是交易消息 (Bilingual)"""
    content_lower = content.lower()
    # Check non-trade keywords first (case-insensitive for English)
    for kw in NON_TRADE_KEYWORDS:
        if kw in content or kw.lower() in content_lower:
            return False
    # Check sell keywords (case-insensitive for English)
    for kw in SELL_KEYWORDS:
        if kw in content or kw.lower() in content_lower:
            return True
    # Fallback: has price + category keyword → trade message
    has_price = bool(re.search(r'\d{2,6}\s*元?', content))
    has_category = any(
        kw in content or kw.lower() in content_lower
        for kws in CATEGORY_MAP.values()
        for kw in kws if len(kw) >= 2
    )
    if has_price and has_category:
        return True
    return False


def extract_price(content):
    """提取价格 (Bilingual: 元/块/yuan)"""
    patterns = [
        r'(\d+(?:\.\d+)?)\s*元',
        r'(\d+(?:\.\d+)?)\s*块',
        r'(\d+(?:\.\d+)?)\s*yuan',
        r'(\d+(?:\.\d+)?)\s*each',
        r'价格\s*(\d+(?:\.\d+)?)',
        r'(\d+(?:\.\d+)?)\s*(?:带|送|包)',
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            price = float(match.group(1))
            if 1 <= price <= 100000:
                return price
    # 纯数字价格（无单位）— 排除紧邻字母的数字（型号如ATX660, 128G, iPhone 12）
    matches = re.findall(r'(?<![a-zA-Z\d])(\d{2,6})(?![a-zA-Z\d])', content + ' ')
    if matches:
        # 优先选3位以上数字（更可能是价格）
        sorted_matches = sorted(matches, key=len, reverse=True)
        for m in sorted_matches:
            price = float(m)
            if 5 <= price <= 100000:
                return price
    return None


def extract_contact(content):
    """提取联系方式 (Bilingual: 微信/WeChat/wx/contact/VX)"""
    patterns = [
        r'微信\s*[:：]?\s*([a-zA-Z0-9_ ]+)',
        r'WeChat\s*[:：]?\s*([a-zA-Z0-9_ ]+)',
        r'contact\s*[:：]?\s*([a-zA-Z0-9_ ]+)',
        r'wx_?\s*[:：]?\s*([a-zA-Z0-9_ ]+)',
        r'联系\s*[:：]?\s*([a-zA-Z0-9_ ]+)',
        r'VX\s*[:：]?\s*([a-zA-Z0-9_ ]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    # "私聊" or "DM" indicates seller wants contact but didn't provide
    if "私聊" in content or re.search(r'\bDM\b', content, re.IGNORECASE):
        return None
    return None


def extract_condition(content):
    """提取成色 (Bilingual: Chinese 成新 / English X/10 condition, brand new)"""
    patterns = [
        # Chinese
        (r'全新(?:未(?:用|拆))?(?:没用过)?', "全新"),
        (r'10成新|十成新', "10成新"),
        (r'9成新|九成新', "9成新"),
        (r'8成新|八成新', "8成新"),
        (r'7成新|七成新', "7成新"),
        (r'6成新|六成新', "6成新"),
        (r'5成新|五成新', "5成新"),
        (r'全新没用过', "全新"),
        # English
        (r'brand new never used', "全新"),
        (r'brand new', "全新"),
        (r'never used', "全新"),
        (r'10/10\s*condition', "10成新"),
        (r'9/10\s*condition', "9成新"),
        (r'8/10\s*condition', "8成新"),
        (r'7/10\s*condition', "7成新"),
        (r'6/10\s*condition', "6成新"),
        (r'5/10\s*condition', "5成新"),
    ]
    for pattern, label in patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return label
    return None


def extract_location(content):
    """提取交易地点 (Bilingual: Chinese + English)"""
    # Check Chinese locations first
    for loc in LOCATIONS:
        if loc in content:
            return loc
    # Check English locations (case-insensitive)
    content_lower = content.lower()
    for en_loc, cn_loc in EN_LOCATIONS_MAP.items():
        if en_loc in content_lower:
            return cn_loc
    return None


def extract_product_name(content, category):
    """提取商品名称 (Bilingual: Chinese + English)"""
    clean = content

    # --- Step 1: Remove prefixes ---
    # English: "Selling", "Anyone want"
    clean = re.sub(r'^Selling\s+', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'^Anyone want\s+', '', clean, flags=re.IGNORECASE)
    # Chinese: "出" prefix
    if clean.startswith("出"):
        clean = clean[1:].strip()

    # --- Step 2: Comma-split approach — take first segment as product name ---
    if ',' in clean or '，' in clean:
        clean_normalized = clean.replace('，', ',')
        first = clean_normalized.split(',')[0].strip()
        # If there's a "?" before the first comma, take text before "?"
        if '?' in first or '？' in first:
            qpos = min(
                first.index('?') if '?' in first else len(first),
                first.index('？') if '？' in first else len(first),
            )
            before_q = first[:qpos].strip()
            if len(before_q) >= 2:
                first = before_q
        # Remove trailing question mark (safety)
        first = re.sub(r'[？?]+$', '', first).strip()
        if len(first) >= 2:
            # Quick cleanup: remove embedded price/contact/condition from first segment
            first = re.sub(r'\d+(?:\.\d+)?\s*yuan', '', first, flags=re.IGNORECASE).strip()
            first = re.sub(r'\d+(?:\.\d+)?\s*元', '', first).strip()
            first = re.sub(r'WeChat\s*[:：]?\s*[a-zA-Z0-9_]+', '', first, flags=re.IGNORECASE).strip()
            first = re.sub(r'\d+/10\s*condition', '', first, flags=re.IGNORECASE).strip()
            first = re.sub(r'brand new(?:\s+never\s+used)?', '', first, flags=re.IGNORECASE).strip()
            # Remove trailing whitespace/punctuation
            first = re.sub(r'[，,。！？、\s]+$', '', first).strip()
            if len(first) >= 2:
                return first

    # --- Step 3: Fallback — full regex cleanup (for messages without commas) ---
    clean = content
    # Remove "Selling" prefix
    clean = re.sub(r'^Selling\s+', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'^Anyone want\s+', '', clean, flags=re.IGNORECASE)
    if clean.startswith("出"):
        clean = clean[1:].strip()
    # Remove price patterns
    clean = re.sub(r'\d+(?:\.\d+)?\s*元', '', clean)
    clean = re.sub(r'\d+(?:\.\d+)?\s*块', '', clean)
    clean = re.sub(r'\d+(?:\.\d+)?\s*yuan', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\d+(?:\.\d+)?\s*each', '', clean, flags=re.IGNORECASE)
    # Remove contact patterns
    clean = re.sub(r'微信\s*[:：]?\s*[a-zA-Z0-9_]+', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'WeChat\s*[:：]?\s*[a-zA-Z0-9_]+', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'联系\s*[:：]?\s*[a-zA-Z0-9_]+', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'contact\s+[a-zA-Z0-9_]+', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'wx_?\s*[:：]?\s*[a-zA-Z0-9_]+', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'VX\s*[:：]?\s*[a-zA-Z0-9_]+', '', clean, flags=re.IGNORECASE)
    # Remove Chinese condition patterns
    for cond in ["全新没用过", "全新未拆", "全新", "10成新", "十成新",
                 "9成新", "九成新", "8成新", "八成新",
                 "7成新", "七成新", "6成新", "六成新",
                 "5成新", "五成新", "成新"]:
        clean = clean.replace(cond, '')
    # Remove English condition patterns
    clean = re.sub(r'\d+/10\s*condition', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'brand new never used', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'brand new', '', clean, flags=re.IGNORECASE)
    # Remove Chinese locations
    for loc in LOCATIONS:
        clean = clean.replace(loc, '')
    # Remove English locations
    for en_loc in EN_LOCATIONS_MAP:
        clean = re.sub(re.escape(en_loc), '', clean, flags=re.IGNORECASE)
    # Remove Chinese trade words
    clean = re.sub(r'交易|自提|当面|包邮|有意|出售|出货|出物|转让|闲置|私聊|求购|联系|送[^，。 ]*|带[^，。 ]*', '', clean)
    # Remove English trade words
    clean = re.sub(r'\btrade\b|\bpickup\b|\bshipping\b|\bfree\b|\bavailable\b|\binterested\b|\bDM\b|\bwith\b|\beach\b|\bbrand\b', '', clean, flags=re.IGNORECASE)
    # Remove standalone price numbers (3+ digits, avoid model numbers)
    clean = re.sub(r'(?<=\s)\d{3,6}(?=\s|$)', '', clean)
    clean = re.sub(r'(?<=出)\s*\d{3,6}(?=\s|$)', '', clean)
    # Clean up punctuation and whitespace
    clean = re.sub(r'[，,。！？、\s]+', ' ', clean).strip()
    # Remove trailing 1-2 digit numbers (e.g., "40" in "电饭煲 3L 40")
    clean = re.sub(r'\s+\d{1,2}$', '', clean)
    clean = clean.strip()
    # If too short, use category
    if len(clean) < 2 and category:
        clean = category
    return clean if clean else None


def extract_category(content):
    """提取品类 (Bilingual, case-insensitive)"""
    content_lower = content.lower()
    for category, keywords in CATEGORY_MAP.items():
        for kw in keywords:
            if kw in content or kw.lower() in content_lower:
                return category
    return None


def extract_listings_llm(chat_data, lang="zh"):
    """
    使用 LLM 从群聊消息中提取二手交易出售信息。
    失败时返回 None，调用方应回退到 extract_listings_regex()。

    Args:
        chat_data: list of {sender, content, time}
        lang: 输出语言 ("zh" / "en") — 影响 category 和 location 字段
    """
    if not _llm_ready or not llm_available():
        return None

    # 构建聊天文本
    lines = []
    for i, msg in enumerate(chat_data, 1):
        sender = msg.get("sender", "")
        content = msg.get("content", "")
        lines.append(f"{i}. {sender}: {content}")
    chat_text = "\n".join(lines)

    if lang == "en":
        system_prompt = """You are an information extraction assistant. Extract second-hand trade listings from campus group chat messages.

**CRITICAL Language Rules:**
1. product_name: Keep the ORIGINAL language from the message (do NOT translate).
2. description: Return the ORIGINAL message text verbatim — no translation, no paraphrasing.
3. condition: Keep original language ("9/10 condition", "brand new", etc.).
4. **category and location MUST be in English** regardless of message language:
   - category: One of "Bicycle", "Textbook", "Electronics", "Daily Items", "Other"
   - location: One of "On Campus", "South Gate", "North Gate", "East Gate", "West Gate", "East Area", "West Area", "South Area", "North Area", or null
5. Only extract "for sale" messages (containing "selling", "for sale", "wts", "second-hand" etc.). Skip non-trade messages.
6. Fields per listing:
   - product_name: item name (original language, keep brand + model)
   - price: number, no unit
   - condition: condition (original language)
   - seller: sender name
   - contact: contact info (original language, e.g. "WeChat xxx"), null if none
   - description: full original message text (verbatim)
   - category: "Bicycle"/"Textbook"/"Electronics"/"Daily Items"/"Other"
   - location: "On Campus"/"South Gate"/etc. or null
7. Skip non-sale messages entirely.
8. Return JSON array, nothing else.

Example output:
[{"product_name":"Giant ATX660 bicycle","price":250,"condition":"9/10 condition","seller":"Zhang","contact":"WeChat zhang123","description":"Selling Giant ATX660 bicycle, 9/10 condition, 250 yuan, WeChat zhang123, South Gate","category":"Bicycle","location":"South Gate"}]"""
    else:
        system_prompt = """你是一个信息提取助手。从校园二手交易群聊消息中提取出售信息。

**重要规则:**
1. 保持原始语言：如果群聊消息是中文，所有字段必须用中文返回；如果是英文，可用英文。不要翻译！
2. description 字段必须原样返回原始消息全文，不要翻译、不要改写、不要总结。
3. product_name 字段使用原始消息中的语言，优先保留品牌+型号+品类关键词（如"捷安特ATX660自行车"）。
4. 只提取"出售"类消息（含"出""转让""闲置""selling""for sale"等关键词），忽略闲聊、求购、讨论。
5. 每条出售信息提取以下字段:
   - product_name: 商品名称（保留原语言）
   - price: 价格（数字，无单位）
   - condition: 成色（如"9成新""全新""8/10 condition"，无法判断则null）
   - seller: 卖家昵称
   - contact: 联系方式（如"微信xxx""WeChat xxx"，无则null）
   - description: 原始消息全文（原样返回，禁止翻译）
   - category: 品类（自行车/教材/电子产品/生活用品/其他）
   - location: 交易地点（校内/南门/北门/东门/西门/东区/西区/南区/北区，英文 campus/south gate/north gate/east gate/west gate/east area/west area/south area/north area，无则null）
6. 如果一条消息不是出售信息，跳过它。
7. 返回 JSON 数组，不要有其他文字。

示例输出:
[{"product_name":"捷安特ATX660自行车","price":250,"condition":"9成新","seller":"张同学","contact":"微信zhang123","description":"出捷安特ATX660 9成新 250元 南门交易 微信zhang123","category":"自行车","location":"南门"}]"""

    user_prompt = f"请从以下群聊消息中提取出售信息:\n\n{chat_text}"

    print("[LLM] 正在用 AI 提取商品信息...")
    result = llm_chat_json(system_prompt, user_prompt, temperature=0.1, max_tokens=3000)

    if result is None or not isinstance(result, list):
        print("[LLM] AI 提取失败或结果为空，回退到正则提取")
        return None

    # 后处理：补充 id 和 source_text
    listings = []
    for i, item in enumerate(result, 1):
        # 确保必要字段存在
        listing = {
            "id": i,
            "product_name": item.get("product_name") or item.get("category") or "未知商品",
            "price": item.get("price"),
            "condition": item.get("condition"),
            "seller": item.get("seller") or "未知",
            "contact": item.get("contact"),
            "description": item.get("description") or "",
            "category": item.get("category"),
            "location": item.get("location"),
            "source_text": item.get("description") or "",
        }
        # 价格转 float
        if listing["price"] is not None:
            try:
                listing["price"] = float(listing["price"])
            except (ValueError, TypeError):
                listing["price"] = None
        listings.append(listing)

    print(f"[LLM] AI 提取了 {len(listings)} 个商品信息")
    return listings


# 英文类别名称（用于英文模式的正则降级）
CATEGORY_EN_MAP = {
    "Bicycle": ["bicycle", "bike", "giant", "merida", "duke", "forever", "flying pigeon", "atx"],
    "Textbook": ["textbook", "calculus", "linear algebra", "higher mathematics",
                  "university physics", "cet-4", "cet-6", "past papers", "politics outline"],
    "Electronics": ["iphone", "ipad", "switch", "kindle", "headphones", "mouse", "laptop",
                    "band", "charger", "noise-canceling", "oled", "rtx"],
    "Daily Items": ["lamp", "toothbrush", "rice cooker", "egg cooker", "guitar", "notebook", "diary"],
}

# 英文地点关键词 -> 标准英文地点名
EN_LOCATIONS_REGEX = {
    "on campus": "On Campus",
    "campus": "On Campus",
    "south gate": "South Gate",
    "north gate": "North Gate",
    "east gate": "East Gate",
    "west gate": "West Gate",
    "east area": "East Area",
    "west area": "West Area",
    "south area": "South Area",
    "north area": "North Area",
}


def extract_category_en(content):
    """英文模式下的品类提取"""
    content_lower = content.lower()
    for category, keywords in CATEGORY_EN_MAP.items():
        for kw in keywords:
            if kw in content_lower:
                return category
    return None


def extract_location_en(content):
    """英文模式下的地点提取"""
    content_lower = content.lower()
    for en_loc, std_loc in sorted(EN_LOCATIONS_REGEX.items(), key=lambda x: len(x[0]), reverse=True):
        if en_loc in content_lower:
            return std_loc
    return None


def extract_listings_regex(chat_data, lang="zh"):
    """
    正则提取（作为 LLM 降级方案）

    Args:
        chat_data: list of {sender, content, time}
        lang: 输出语言 ("zh" / "en")

    Returns:
        list of listing dicts
    """
    listings = []
    listing_id = 0

    for msg in chat_data:
        content = msg.get("content", "")
        sender = msg.get("sender", "")

        if not is_trade_message(content):
            continue

        price = extract_price(content)
        contact = extract_contact(content)
        condition = extract_condition(content)

        # 根据语言选择提取方式
        if lang == "en":
            location = extract_location_en(content)
            category = extract_category_en(content)
        else:
            location = extract_location(content)
            category = extract_category(content)

        product_name = extract_product_name(content, category)

        if not product_name and not category:
            continue

        listing_id += 1
        listing = {
            "id": listing_id,
            "product_name": product_name or category or "未知商品",
            "price": price,
            "condition": condition,
            "seller": sender,
            "contact": contact,
            "description": content,
            "category": category,
            "location": location,
            "source_text": content,
        }
        listings.append(listing)

    return listings


def _normalize_location(loc, lang="zh"):
    """把常见英文/中文地点统一标准化"""
    if not loc:
        return None
    loc_str = str(loc).strip()
    key = loc_str.lower()

    if lang == "en":
        # 中文 -> 英文；英文已标准化则保留
        return EN_LOCATIONS_MAP.get(loc_str) or EN_LOCATIONS_MAP.get(key) or loc_str

    # zh: 英文 -> 中文；中文已标准化则保留
    return EN_LOCATIONS_MAP.get(key) or loc_str


def _normalize_condition(cond):
    """把英文成色描述统一转为中文成色"""
    if not cond:
        return None
    cond_str = str(cond).strip().lower()
    mapping = {
        "brand new never used": "全新",
        "brand new": "全新",
        "never used": "全新",
        "10/10 condition": "10成新",
        "9/10 condition": "9成新",
        "8/10 condition": "8成新",
        "7/10 condition": "7成新",
        "6/10 condition": "6成新",
        "5/10 condition": "5成新",
        "10/10": "10成新",
        "9/10": "9成新",
        "8/10": "8成新",
        "7/10": "7成新",
        "6/10": "6成新",
        "5/10": "5成新",
    }
    return mapping.get(cond_str) or cond_str


def extract_listings(chat_data, lang="zh"):
    """
    从群聊消息中提取二手交易出售信息 (Bilingual)

    优先使用 LLM 提取，失败时自动回退到正则提取。
    提取后会用正则再补全缺失的 location / condition / contact。

    Args:
        chat_data: list of {sender, content, time}
        lang: 输出语言 ("zh" / "en") — 影响 category 和 location 字段

    Returns:
        list of listing dicts
    """
    # 先尝试 LLM 提取
    listings = extract_listings_llm(chat_data, lang=lang)
    if listings is None:
        # 回退到正则提取
        listings = extract_listings_regex(chat_data, lang=lang)

    # 后处理：补全缺失字段
    for item in listings:
        content = item.get("description") or item.get("source_text") or ""
        if not item.get("location"):
            # 先用通用双语函数尝试提取
            loc = extract_location(content)
            if not loc:
                loc = extract_location_en(content)
            item["location"] = _normalize_location(loc, lang)
        else:
            item["location"] = _normalize_location(item["location"], lang)

        if not item.get("condition"):
            cond = extract_condition(content)
            item["condition"] = _normalize_condition(cond)
        else:
            item["condition"] = _normalize_condition(item["condition"])

        if not item.get("contact"):
            item["contact"] = extract_contact(content)

    return listings


def load_mock_data(filepath=None):
    """加载模拟群聊数据"""
    if filepath is None:
        filepath = os.path.join(os.path.dirname(__file__), "..", "data", "mock_chats.json")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    data = load_mock_data()
    print(f"Loaded {len(data)} chat messages")
    print()

    listings = extract_listings(data)
    print(f"Extracted {len(listings)} listings:")
    print()

    for l in listings:
        print(f"  #{l['id']} {l['product_name']} | {l['price']} yuan | {l['condition']} | seller={l['seller']} | contact={l['contact']} | location={l['location']}")
        print(f"     category: {l['category']}")
        print(f"     source: {l['source_text'][:80]}")
        print()

    # Stats
    print(f"--- Stats ---")
    print(f"With price: {sum(1 for l in listings if l['price'])}")
    print(f"Without price: {sum(1 for l in listings if not l['price'])}")
    print(f"With contact: {sum(1 for l in listings if l['contact'])}")
    print(f"Without contact: {sum(1 for l in listings if not l['contact'])}")
    print(f"With condition: {sum(1 for l in listings if l['condition'])}")
    print(f"With location: {sum(1 for l in listings if l['location'])}")
