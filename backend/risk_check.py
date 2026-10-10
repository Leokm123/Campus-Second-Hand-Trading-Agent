"""
风险评估模块 — AI 驱动的智能风险评估

优先使用 LLM 对商品进行智能风险评估，判断:
- 价格异常（过低/过高）
- 描述模糊/信息缺失
- 联系方式可信度
- 综合风险等级（red/yellow/green）

失败时自动回退到规则引擎。
"""

# LLM 配置
try:
    from llm_config import llm_chat_json, llm_available
    _llm_ready = True
except ImportError:
    _llm_ready = False


RED = "red"
YELLOW = "yellow"
GREEN = "green"

# 多语言风险原因（降级方案使用）
RISK_REASONS = {
    "zh": {
        "no_contact": "无联系方式",
        "low_price": "价格异常偏低",
        "short_desc": "描述过于简略",
        "brief_desc": "描述不够详细",
        "no_condition": "无成色信息",
        "safe": "信息完整，无明显风险",
    },
    "en": {
        "no_contact": "No contact info",
        "low_price": "Unusually low price",
        "short_desc": "Description too brief",
        "brief_desc": "Description lacks detail",
        "no_condition": "No condition info",
        "safe": "Complete info, no obvious risk",
    },
}

RISK_LABELS = {
    "zh": {"green": "推荐", "yellow": "可考虑", "red": "不建议"},
    "en": {"green": "Recommended", "yellow": "Consider", "red": "Not Recommended"},
}

RISK_COLORS = {
    "green": "#5DCAA5",
    "yellow": "#FAC775",
    "red": "#F09595",
}


# ================================================================
#  AI 风险评估
# ================================================================

def check_risk_llm(listing, lang="zh"):
    """
    使用 LLM 对单个 listing 进行智能风险评估。

    AI 负责判断:
    - 价格是否异常（过低可能诈骗，过高可能虚报）
    - 描述是否模糊/信息是否缺失
    - 联系方式是否存在/可信
    - 是否有其他可疑信号

    返回 {risk_level, reasons} 或 None（失败时）。
    """
    if not _llm_ready or not llm_available():
        return None

    product_name = listing.get("product_name") or "unknown"
    price = listing.get("price")
    price_str = str(int(price)) if price else "unknown"
    condition = listing.get("condition") or "unknown"
    seller = listing.get("seller") or "unknown"
    contact = listing.get("contact") or "none"
    description = listing.get("description") or ""
    location = listing.get("location") or "unknown"
    category = listing.get("category") or "other"

    if lang == "en":
        system_prompt = """You are a risk assessment engine for a campus second-hand trading platform.
Evaluate the risk level of a listing based on:

1. Price anomaly: Is the price suspiciously low (possible scam) or unreasonably high?
2. Description quality: Is the description detailed enough? Are key details missing?
3. Contact info: Is there a valid contact method (WeChat ID, phone, etc.)?
4. Condition info: Is the item condition stated?
5. Overall credibility: Does the listing look genuine?

Risk levels:
- "red": High risk (no contact, suspiciously low price, extremely vague description)
- "yellow": Medium risk (missing some info, slightly vague, no condition stated)
- "green": Low risk (complete info, reasonable price, has contact)

Return JSON: {"risk_level": "red"/"yellow"/"green", "reasons": ["reason1", "reason2"]}
For green listings, reasons can be ["No obvious risk, info is complete"].
Only return the JSON, no explanation."""
    else:
        system_prompt = """你是校园二手交易平台的风险评估引擎。
评估一个商品列表的风险等级，判断依据:

1. 价格异常: 价格是否过低（可能诈骗）或过高（可能虚报）？
2. 描述质量: 描述是否足够详细？关键信息是否缺失？
3. 联系方式: 是否有有效的联系方式（微信号、手机号等）？
4. 成色信息: 是否说明了商品成色？
5. 整体可信度: 这条出售信息看起来真实可信吗？

风险等级:
- "red": 高风险（无联系方式、价格异常低、描述极其模糊）
- "yellow": 中等风险（部分信息缺失、描述不够详细、无成色信息）
- "green": 低风险（信息完整、价格合理、有联系方式）

返回JSON: {"risk_level": "red"/"yellow"/"green", "reasons": ["原因1", "原因2"]}
对于 green 商品，reasons 可以是 ["信息完整，无明显风险"]。
只返回JSON，不要解释。"""

    user_prompt = f"""商品信息:
- 商品名: {product_name}
- 价格: {price_str}
- 成色: {condition}
- 卖家: {seller}
- 联系方式: {contact}
- 地点: {location}
- 品类: {category}
- 原始描述: {description}

请评估风险等级。"""

    print("[LLM] 正在用 AI 评估风险...")
    result = llm_chat_json(system_prompt, user_prompt, temperature=0.1, max_tokens=300)

    if result is None:
        print("[LLM] AI 风险评估失败，回退到规则引擎")
        return None

    risk_level = result.get("risk_level", "green")
    reasons = result.get("reasons", [])

    # 校验 risk_level
    if risk_level not in ("red", "yellow", "green"):
        risk_level = "green"

    # 确保 reasons 是列表
    if not isinstance(reasons, list):
        reasons = [str(reasons)] if reasons else []

    print(f"[LLM] AI 风险评估: {risk_level} - {reasons}")
    return {
        "risk_level": risk_level,
        "reasons": reasons if reasons else ["信息完整，无明显风险"],
    }


def check_all_risks_llm(listings, lang="zh"):
    """
    使用 LLM 批量风险评估（逐条调用）。

    返回添加了 risk_level 和 risk_reasons 的列表，失败时返回 None。
    """
    results = []
    for listing in listings:
        risk = check_risk_llm(listing, lang)
        if risk is None:
            return None  # 有一条失败，整体回退

        listing["risk_level"] = risk["risk_level"]
        listing["risk_reasons"] = risk["reasons"]
        results.append(listing)

    return results


# ================================================================
#  规则引擎降级方案（原有逻辑）
# ================================================================

def check_risk_rules(listing, lang="zh"):
    """
    规则引擎风险评估（降级方案）

    规则:
    - 无联系方式 + 描述极短 -> red
    - 价格异常低 (< 30元非教材类) -> red
    - 无联系方式 / 描述简略 / 无成色信息 -> yellow
    - 正常信息 -> green
    """
    tr = RISK_REASONS.get(lang, RISK_REASONS["zh"])
    reasons = []

    contact = listing.get("contact")
    price = listing.get("price")
    product_name = listing.get("product_name") or ""
    description = listing.get("description") or ""
    condition = listing.get("condition")

    if not contact or contact == "null":
        reasons.append(tr["no_contact"])

    # 价格异常低
    book_kw = "书" if lang == "zh" else "book"
    textbook_kw = "教材" if lang == "zh" else "textbook"
    is_book = (listing.get("category") == "教材" or
               book_kw in product_name or textbook_kw in product_name or
               book_kw in description or textbook_kw in description)
    if price and price < 30 and not is_book:
        reasons.append(tr["low_price"])

    # 描述模糊
    if len(description) < 5:
        reasons.append(tr["short_desc"])
    elif len(description) < 10:
        reasons.append(tr["brief_desc"])

    # 无成色信息
    if not condition or condition == "null":
        reasons.append(tr["no_condition"])

    # 判定风险等级：只有强危险信号才标红
    has_red_signal = (tr["low_price"] in reasons or
                      (tr["no_contact"] in reasons and tr["short_desc"] in reasons))
    has_yellow_signal = len(reasons) > 0

    if has_red_signal:
        risk_level = RED
    elif has_yellow_signal:
        risk_level = YELLOW
    else:
        risk_level = GREEN

    return {
        "risk_level": risk_level,
        "reasons": reasons if reasons else [tr["safe"]],
    }


def check_all_risks_rules(listings, lang="zh"):
    """规则引擎批量风险评估（降级方案）"""
    results = []
    for listing in listings:
        risk = check_risk_rules(listing, lang)
        listing["risk_level"] = risk["risk_level"]
        listing["risk_reasons"] = risk["reasons"]
        results.append(listing)
    return results


# ================================================================
#  主入口 — AI 优先，降级到规则
# ================================================================

def check_risk(listing, lang="zh"):
    """
    对单个 listing 进行风险评估

    优先使用 AI 评估，失败时回退到规则引擎。

    Args:
        listing: 商品信息 dict
        lang: 语言 ("zh"/"en")

    Returns:
        {risk_level: "red"/"yellow"/"green", reasons: [str]}
    """
    # 先尝试 AI 评估
    llm_result = check_risk_llm(listing, lang)
    if llm_result is not None:
        return llm_result

    # 回退到规则引擎
    return check_risk_rules(listing, lang)


def check_all_risks(listings, lang="zh"):
    """
    批量风险评估

    优先使用 AI 评估，失败时回退到规则引擎。

    Args:
        listings: 商品列表
        lang: 语言 ("zh"/"en")

    Returns:
        添加了 risk_level 和 risk_reasons 的列表
    """
    # 先尝试 AI 评估
    llm_result = check_all_risks_llm(listings, lang)
    if llm_result is not None:
        return llm_result

    # 回退到规则引擎
    return check_all_risks_rules(listings, lang)


def get_risk_label(level, lang="zh"):
    """获取风险标签文字"""
    labels = RISK_LABELS.get(lang, RISK_LABELS["zh"])
    return labels.get(level, "?")


if __name__ == "__main__":
    test_listing = {
        "product_name": "飞鸽自行车",
        "price": 180,
        "condition": "8成新",
        "seller": "董同学",
        "contact": "微信dong_bike",
        "description": "出飞鸽自行车 8成新 180 校内交易 微信dong_bike",
    }
    print("=== AI 风险评估 ===")
    r = check_risk(test_listing, "zh")
    print(f"风险: {r['risk_level']}, 原因: {r['reasons']}")
