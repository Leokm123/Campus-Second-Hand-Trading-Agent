"""
匹配模块 — AI 驱动的意图解析、语义匹配与智能评分

优先使用 LLM 实现:
1. 意图解析: 从用户自然语言中提取物品名/预算/地点
2. 语义匹配: 语义级别判断 listings 与用户需求的相关性
3. 智能评分: 综合价格、成色、描述质量等多维度 AI 评分

失败时自动回退到正则/关键词匹配。
"""

import re

# LLM 配置
try:
    from llm_config import llm_chat_json, llm_available
    _llm_ready = True
except ImportError:
    _llm_ready = False


# ================================================================
#  常量定义（正则降级方案使用）
# ================================================================

# 商品别名映射（用户口语 -> listing 关键词）
PRODUCT_ALIASES = {
    "高数": "高等数学",
    "线代": "线性代数",
    "四级": "四级",
    "六级": "六级",
    "考研": "考研",
    "手机": "iPhone",
    "电脑": "笔记本",
    "灯": "台灯",
    "锅": "电饭煲",
    "蛋器": "煮蛋器",
}

# 英文->中文 地点映射
EN_LOCATIONS = {
    "on campus": "校内", "campus": "校内",
    "east area": "东区", "east": "东区", "east gate": "东门",
    "west area": "西区", "west": "西区", "west gate": "西门",
    "south area": "南区", "south": "南区", "south gate": "南门",
    "north area": "北区", "north": "北区", "north gate": "北门",
}

# 英文->中文 商品名映射
EN_PRODUCTS = {
    "bicycle": "自行车", "bike": "自行车",
    "phone": "iPhone", "iphone": "iPhone", "smartphone": "iPhone",
    "textbook": "教材", "book": "教材", "calculus": "高等数学",
    "headphone": "耳机", "earphone": "耳机", "headphones": "耳机",
    "lamp": "台灯", "light": "台灯",
    "mouse": "鼠标",
    "kindle": "Kindle",
    "switch": "Switch",
    "ipad": "iPad",
    "guitar": "吉他",
    "cooker": "煮蛋器", "egg cooker": "煮蛋器",
    "bracelet": "手环", "band": "手环",
    "notebook": "笔记本", "laptop": "笔记本",
    "rice cooker": "电饭煲",
    "toothbrush": "牙刷",
}

# Build synonym groups from EN_PRODUCTS
SYNONYM_GROUPS = {}
for en_name, cn_name in EN_PRODUCTS.items():
    if cn_name not in SYNONYM_GROUPS:
        SYNONYM_GROUPS[cn_name] = [cn_name]
    if en_name not in SYNONYM_GROUPS[cn_name]:
        SYNONYM_GROUPS[cn_name].append(en_name)


# ================================================================
#  AI 意图解析
# ================================================================

def parse_user_need_llm(message, lang="zh"):
    """
    使用 LLM 从用户自然语言中提取意图信息。

    返回格式与 parse_user_need_regex 一致:
    {complete, missing, product_name, budget, location, raw}

    失败时返回 None，调用方应回退到正则解析。
    """
    if not _llm_ready or not llm_available():
        return None

    if lang == "en":
        system_prompt = """You are an intent parser for a campus second-hand trading assistant.
Extract the following from the user's message:
- product_name: what item the user wants to buy (string, or null if not mentioned)
- budget: maximum budget as a number (int, or null if not mentioned)
- location: preferred trade location (string, or null if not mentioned)

Return JSON only: {"product_name": ..., "budget": ..., "location": ...}
If a field is not mentioned in the user's message, set it to null.
No explanation, just the JSON."""
    else:
        system_prompt = """你是一个校园二手交易助手的意图解析器。
从用户消息中提取以下信息:
- product_name: 用户想买的物品名称（字符串，未提及则为null）
- budget: 预算上限（整数，未提及则为null）
- location: 期望交易地点（字符串，未提及则为null）

只返回JSON: {"product_name": ..., "budget": ..., "location": ...}
未提及的字段设为null。不要解释，只返回JSON。"""

    user_prompt = f"用户消息: {message}"

    print("[LLM] 正在用 AI 解析用户意图...")
    result = llm_chat_json(system_prompt, user_prompt, temperature=0.1, max_tokens=200)

    if result is None:
        print("[LLM] AI 意图解析失败，回退到正则")
        return None

    # 提取字段
    product_name = result.get("product_name")
    budget = result.get("budget")
    location = result.get("location")

    # 类型清理
    if product_name is not None:
        product_name = str(product_name).strip()
        if product_name.lower() in ("null", "none", "", "未提及"):
            product_name = None

    if budget is not None:
        try:
            budget = int(float(budget))
        except (ValueError, TypeError):
            budget = None

    if location is not None:
        location = str(location).strip()
        if location.lower() in ("null", "none", "", "未提及"):
            location = None

    # 检查完整性
    missing = []
    if not product_name:
        missing.append("product_name")
    if budget is None:
        missing.append("budget")
    if not location:
        missing.append("location")

    parsed = {
        "complete": len(missing) == 0,
        "missing": missing,
        "product_name": product_name,
        "budget": budget,
        "location": location,
        "raw": message,
    }

    print(f"[LLM] AI 意图解析: product={product_name}, budget={budget}, location={location}")
    return parsed


# ================================================================
#  AI 语义匹配 + 智能评分
# ================================================================

def match_listings_llm(listings, user_need, lang="zh"):
    """
    使用 LLM 进行语义匹配和智能评分。

    AI 负责判断:
    - 商品名称的语义相关性（如"自行车"匹配"捷安特ATX660""bike"等）
    - 价格是否在预算范围内
    - 地点是否兼容
    - 综合评分（价格40% + 成色30% + 描述完整度30%）

    返回排序后的匹配 listing 列表，失败时返回 None。
    """
    if not _llm_ready or not llm_available():
        return None

    if not listings:
        return None

    # 构建商品摘要文本
    listing_lines = []
    for i, l in enumerate(listings):
        name = l.get("product_name") or "?"
        price = l.get("price")
        price_str = str(int(price)) if price else "unknown"
        condition = l.get("condition") or "unknown"
        location = l.get("location") or "unknown"
        seller = l.get("seller") or "?"
        contact = l.get("contact") or "none"
        desc = (l.get("description") or "")[:150]
        category = l.get("category") or "other"

        listing_lines.append(
            f"[{i}] {name} | price={price_str} | condition={condition} | "
            f"location={location} | seller={seller} | contact={contact} | "
            f"category={category} | desc={desc}"
        )

    listings_text = "\n".join(listing_lines)

    user_product = user_need.get("product_name", "")
    user_budget = user_need.get("budget", "")
    user_location = user_need.get("location", "")

    if lang == "en":
        system_prompt = """You are a smart matching engine for a campus second-hand trading platform.
Given a user's need and a list of listings, determine which listings match and score them.

Matching rules:
- Product name: semantic match (e.g., "bicycle" matches "bike", "Giant ATX660", "Merida Duke")
- Price: must be within budget (or close, within 20% over)
- Location: should match or be compatible (e.g., "on campus" matches "East Area", "South Gate")
- Items without a listed location should still be included if they match product and price
- Exclude listings that are clearly not the same category of item

Return up to 10 matching listings. Scoring (0-100):
- Price attractiveness (40%): lower price relative to budget = higher score
- Condition (30%): better condition = higher score
- Description completeness (30%): more details and contact info = higher score

Return JSON array of matching listings (skip non-matching ones):
[{"index": 0, "score": 85, "reason": "Good price, good condition"}, ...]

Only return the JSON array, no explanation."""
    else:
        system_prompt = """你是校园二手交易平台的智能匹配引擎。
给定用户需求和一组商品列表，判断哪些商品匹配并评分。

匹配规则:
- 商品名称语义匹配（如"自行车"匹配"捷安特ATX660""bike""山地车"等）
- 价格需在预算范围内（或超出20%以内也可）
- 地点应匹配或兼容（如"校内"匹配"东区""南门"等校内区域）
- 无地点信息的商品，只要商品和价格匹配也应保留
- 排除明显不相关的商品

最多返回 10 个匹配商品。评分（0-100）:
- 价格吸引力(40%): 相对预算越低分越高
- 成色(30%): 成色越好分越高
- 描述完整度(30%): 信息越全、有联系方式分越高

返回JSON数组（只包含匹配的商品，不匹配的跳过）:
[{"index": 0, "score": 85, "reason": "价格合适，成色好"}, ...]

只返回JSON数组，不要解释。"""

    user_prompt = f"""用户需求:
- 物品: {user_product}
- 预算: {user_budget}
- 地点: {user_location}

商品列表:
{listings_text}

请返回匹配的商品及评分。"""

    print("[LLM] 正在用 AI 进行语义匹配...")
    result = llm_chat_json(system_prompt, user_prompt, temperature=0.1, max_tokens=3000)

    if result is None or not isinstance(result, list):
        print("[LLM] AI 匹配失败，回退到关键词匹配")
        return None

    # 将 AI 结果映射回 listing 对象
    matched = []
    for item in result:
        idx = item.get("index")
        if idx is None or not isinstance(idx, int):
            continue
        if idx < 0 or idx >= len(listings):
            continue

        listing = dict(listings[idx])  # 浅拷贝
        listing["match_score"] = item.get("score", 50)
        listing["match_reason"] = item.get("reason", "")
        matched.append(listing)

    # 按评分排序
    matched.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    print(f"[LLM] AI 匹配了 {len(matched)} 个商品")
    return matched


# ================================================================
#  正则降级方案（原有逻辑）
# ================================================================

def _match_keyword(text, keyword):
    """Check if keyword appears in text (with word boundary for English words)"""
    if re.match(r'^[a-zA-Z]+$', keyword):
        return bool(re.search(r'\b' + re.escape(keyword) + r'\b', text))
    else:
        return keyword in text


def _get_synonyms(word):
    """Get synonym list for a word (case-insensitive)"""
    word_lower = word.lower()
    for cn_name, synonyms in SYNONYM_GROUPS.items():
        if word_lower in [s.lower() for s in synonyms]:
            return [s.lower() for s in synonyms]
    for alias, canonical in PRODUCT_ALIASES.items():
        if word == alias or word == canonical:
            group = SYNONYM_GROUPS.get(canonical, [])
            result = [alias.lower(), canonical.lower()]
            for s in group:
                if s.lower() not in result:
                    result.append(s.lower())
            return result
    return [word_lower]


def parse_user_need_regex(message, lang="zh"):
    """
    正则解析用户需求（降级方案）

    Args:
        message: 用户输入文本
        lang: 语言 ("zh"/"en")

    Returns:
        {complete, missing, product_name, budget, location, raw}
    """
    result = {
        "complete": False,
        "missing": [],
        "product_name": None,
        "budget": None,
        "location": None,
        "raw": message,
    }

    # ===== 提取预算 =====
    budget_match = re.search(r'预算\s*(\d+)', message)
    if budget_match:
        result["budget"] = int(budget_match.group(1))
    if result["budget"] is None:
        budget_match = re.search(r'(?:budget|under|max)\s*(\d+)', message, re.IGNORECASE)
        if budget_match:
            result["budget"] = int(budget_match.group(1))
    if result["budget"] is None:
        budget_match = re.search(r'(\d+)\s*[-到]\s*(\d+)\s*元', message)
        if budget_match:
            result["budget"] = int(budget_match.group(2))
    if result["budget"] is None:
        budget_match = re.search(r'(\d+)\s*元', message)
        if budget_match:
            result["budget"] = int(budget_match.group(1))
    if result["budget"] is None:
        budget_match = re.search(r'(\d+)\s*yuan', message, re.IGNORECASE)
        if budget_match:
            result["budget"] = int(budget_match.group(1))
    if result["budget"] is None:
        matches = re.findall(r'(?<![a-zA-Z\d])(\d{2,6})(?![a-zA-Z\d])', message + ' ')
        if matches:
            result["budget"] = max(int(m) for m in matches)

    # ===== 提取地点 =====
    locations = ["校内", "南门", "北门", "东门", "西门", "东区", "西区", "南区", "北区", "校内交易"]
    for loc in locations:
        if loc in message:
            result["location"] = "校内" if loc == "校内交易" else loc
            break
    if not result["location"]:
        msg_lower = message.lower()
        for en_loc, cn_loc in sorted(EN_LOCATIONS.items(), key=lambda x: len(x[0]), reverse=True):
            if en_loc in msg_lower:
                result["location"] = cn_loc
                break

    # ===== 提取物品名 =====
    clean = message
    clean = re.sub(r'预算\s*\d+', '', clean)
    clean = re.sub(r'(?:budget|under|max)\s*\d+', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\d+\s*[-到]\s*\d+\s*元', '', clean)
    clean = re.sub(r'\d+\s*元', '', clean)
    clean = re.sub(r'\d+\s*yuan', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'(?<![a-zA-Z\d])\d{2,6}(?![a-zA-Z\d])', '', clean + ' ')
    for loc in locations:
        clean = clean.replace(loc, '')
    for en_loc in sorted(EN_LOCATIONS.keys(), key=len, reverse=True):
        clean = re.sub(re.escape(en_loc), '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'交易|出售|出货|出物|购买|想要|求购|求一本|second-hand|second hand|trade', '', clean, flags=re.IGNORECASE)
    for _ in range(3):
        clean = re.sub(r'^(帮我找|帮我买|帮我找个|帮我买个|想买|想找个|想买个|想要|需要|求购|求一本|求|购买|帮我|帮|买|找|个|一本|二手)\s*', '', clean)
    clean = re.sub(r'^二手', '', clean).strip()
    for _ in range(3):
        clean = re.sub(r'^(looking for|want to buy|want a|want|need a|need|find me a|find a|find|i need|i want|i\'m looking for|buy a|buy|an|a|the|some)\b\s*', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'[，,。！？]+', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean_lower = clean.lower()
    for en_name, cn_name in EN_PRODUCTS.items():
        if en_name == clean_lower or re.search(r'\b' + re.escape(en_name) + r'\b', clean_lower):
            clean = cn_name
            break
    if len(clean) > 0:
        result["product_name"] = clean

    # ===== 检查完整性 =====
    missing = []
    if not result["product_name"]:
        missing.append("product_name")
    if result["budget"] is None:
        missing.append("budget")
    if not result["location"]:
        missing.append("location")
    result["missing"] = missing
    result["complete"] = len(missing) == 0

    return result


def match_listings_regex(listings, user_need):
    """
    关键词匹配（降级方案）

    Args:
        listings: extract_listings 的输出
        user_need: parse_user_need 的输出

    Returns:
        排序后的匹配 listing 列表（最多返回 10 条）
    """
    matched = []

    user_product = user_need.get("product_name", "")
    synonyms = _get_synonyms(user_product) if user_product else []

    for listing in listings:
        # 物品名匹配
        if user_product:
            name = (listing.get("product_name") or "").lower()
            desc = (listing.get("description") or "").lower()
            category = (listing.get("category") or "").lower()

            direct_match = any(_match_keyword(name, syn) for syn in synonyms)
            desc_match = any(_match_keyword(desc, syn) for syn in synonyms)
            category_match = any(_match_keyword(category, syn) for syn in synonyms)

            alias_match = False
            for alias, canonical in PRODUCT_ALIASES.items():
                if alias in user_product:
                    canon_synonyms = _get_synonyms(canonical)
                    if any(syn in name or syn in desc for syn in canon_synonyms):
                        alias_match = True
                        break

            if not (direct_match or desc_match or category_match or alias_match):
                continue

        # 预算过滤：允许价格最多超出预算 20%，超出会降分但不直接排除
        price_ok = True
        over_budget_ratio = 0.0
        if user_need["budget"] and listing.get("price"):
            price = listing["price"]
            budget = user_need["budget"]
            if price > budget * 1.2:
                continue
            if price > budget:
                over_budget_ratio = (price - budget) / budget
                price_ok = False

        # 地点匹配：地点不匹配时降分，但不直接排除；listing 无地点也保留
        location_ok = True
        if user_need["location"] and listing.get("location"):
            user_loc = user_need["location"]
            list_loc = listing["location"] or ""
            if user_loc == "校内":
                campus_areas = ["校内", "东区", "西区", "南区", "北区", "东门", "西门", "南门", "北门"]
                if list_loc not in campus_areas:
                    location_ok = False
            else:
                if user_loc.lower() not in list_loc.lower() and list_loc.lower() not in user_loc.lower():
                    location_ok = False

        # 评分
        score = _calculate_score_regex(listing, user_need)
        # 地点不匹配的惩罚
        if not location_ok:
            score -= 15
        # 超出预算惩罚（按超出比例，最高扣 25 分）
        if not price_ok:
            score -= int(over_budget_ratio * 100 + 10)
        listing["match_score"] = max(0, score)
        matched.append(listing)

    matched.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return matched[:10]


def _calculate_score_regex(listing, user_need):
    """规则评分（降级方案）"""
    score = 0

    # 价格匹配度 (40分)
    budget = user_need.get("budget")
    price = listing.get("price")
    if budget and price:
        ratio = price / budget
        if ratio <= 0.7:
            score += 40
        elif ratio <= 0.9:
            score += 30
        elif ratio <= 1.0:
            score += 20
    elif price:
        score += 10

    # 成色 (30分)
    condition = (listing.get("condition") or "").lower()
    if "全新" in condition or "10成" in condition:
        score += 30
    elif "9成" in condition or "九成" in condition:
        score += 25
    elif "8成" in condition or "八成" in condition:
        score += 20
    elif "7成" in condition or "七成" in condition:
        score += 15
    elif condition:
        score += 10

    # 描述完整度 (30分)
    desc = listing.get("description") or ""
    contact = listing.get("contact")
    if len(desc) >= 20:
        score += 15
    elif len(desc) >= 10:
        score += 10
    elif len(desc) > 0:
        score += 5
    if contact:
        score += 15

    return score


# ================================================================
#  主入口 — AI 优先，降级到正则
# ================================================================

def parse_user_need(message, lang="zh"):
    """
    解析用户需求，提取三项必要信息

    优先使用 AI 意图解析，失败时回退到正则解析。

    Args:
        message: 用户输入文本
        lang: 语言 ("zh"/"en")

    Returns:
        {complete, missing, product_name, budget, location, raw}
    """
    # 先尝试 AI 解析
    llm_result = parse_user_need_llm(message, lang)
    if llm_result is not None:
        return llm_result

    # 回退到正则解析
    return parse_user_need_regex(message, lang)


def match_listings(listings, user_need, lang="zh"):
    """
    根据用户需求过滤和排序 listings

    优先使用 AI 语义匹配，失败时回退到关键词匹配。

    Args:
        listings: extract_listings 的输出
        user_need: parse_user_need 的输出
        lang: 语言 ("zh"/"en")

    Returns:
        排序后的匹配 listing 列表
    """
    # 先尝试 AI 匹配
    llm_result = match_listings_llm(listings, user_need, lang)
    if llm_result is not None:
        return llm_result

    # 回退到关键词匹配
    return match_listings_regex(listings, user_need)


if __name__ == "__main__":
    # Test AI intent parsing
    test_msgs = [
        "帮我找个二手自行车，预算300，校内交易",
        "looking for a bicycle, budget 300, on campus",
        "我想买个自行车",
    ]
    for msg in test_msgs:
        need = parse_user_need(msg, lang="zh" if any(c > '\u4e00' for c in msg) else "en")
        print(f"Input: {msg}")
        print(f"  Parsed: {need}")
        print()
