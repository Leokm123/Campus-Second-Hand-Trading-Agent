"""
砍价话术生成模块 — 根据商品信息和风险评估生成个性化微信消息

输入: listing dict (含商品信息+风险评估), lang ("zh"/"en")
输出: 自然、完整的微信消息文本（不再硬截断到150字）
"""

# LLM 配置
try:
    from llm_config import llm_chat, llm_available
    _llm_ready = True
except ImportError:
    _llm_ready = False


def generate_message_llm(listing, user_need=None, lang="zh"):
    """
    使用 LLM 生成砍价话术。
    失败时返回 None，调用方应回退到模板生成。
    """
    if not _llm_ready or not llm_available():
        return None

    product_name = listing.get("product_name") or "商品"
    price = listing.get("price")
    condition = listing.get("condition") or "未知"
    seller = listing.get("seller") or "同学"
    risk_level = listing.get("risk_level", "green")
    risk_reasons = listing.get("risk_reasons", [])
    location = listing.get("location") or "校内"

    price_text = f"{int(price)}元" if price else "未知"
    risk_text = "、".join(risk_reasons) if risk_reasons else "无明显风险"

    if lang == "en":
        if risk_level == "red":
            system_prompt = """You are a cautious college student writing a WeChat message to a seller of a secondhand item.

**CRITICAL: You MUST write the entire message in English. Even if the product information below is in Chinese, translate it and write the message in English only.**

**This listing has HIGH RISK. Reasons: """ + risk_text + """**

Write a short, polite inquiry message (max 150 chars) that:
1. Briefly expresses interest in the item
2. Asks the seller to provide MORE DETAILS (specific model, condition, photos, etc.)
3. Asks the seller to provide their CONTACT info (WeChat, phone) so you can chat further
4. Does NOT commit to a meetup or any price
5. Does NOT comment on whether the price is high/low (could be misused by scammers)
6. Does NOT say "seems reasonable" / "seems a bit low" / any price judgment
7. Keeps tone neutral and cautious

If the condition is in Chinese (e.g., "9成新"), convert it to English (e.g., "9/10 condition").
If the location is in Chinese (e.g., "南门"), convert it to English (e.g., "South Gate").

Return ONLY the message text, no quotes or explanation."""
            user_prompt = f"""Product: {product_name}
Listed price: {price_text}
Condition: {condition}
Seller: {seller}
Location: {location}
Risk level: RED (high risk — reasons: {risk_text})

Write a cautious inquiry message in ENGLISH asking for more details and contact info. Do NOT comment on the price."""
        else:
            system_prompt = """You are a friendly college student writing a WeChat message to a seller of a secondhand item.

**CRITICAL: You MUST write the entire message in English. Even if the product information below is in Chinese, translate it and write the message in English only.**

Write a natural, casual message (max 150 chars) that:
1. Shows interest in the item (use the item name in English)
2. Mentions the price casually (do NOT judge whether it's "reasonable", "low", "high" — just reference it naturally)
3. Suggests meeting up to inspect the item in person
4. Offers to pay on the spot if everything looks good

If the condition is in Chinese (e.g., "9成新"), convert it to English (e.g., "9/10 condition").
If the location is in Chinese (e.g., "南门"), convert it to English (e.g., "South Gate").

Return ONLY the message text, no quotes or explanation."""
            user_prompt = f"""Product: {product_name}
Price: {price_text}
Condition: {condition}
Seller: {seller}
Location: {location}
Risk level: {risk_level}
Risk notes: {risk_text}

Write a WeChat message to the seller in ENGLISH. Do NOT comment on whether the price is reasonable or low."""
    else:
        if risk_level == "red":
            system_prompt = """你是一个谨慎的大学生，要给二手群里的卖家发微信消息。

**重要：你必须用中文写这条消息。即使下面的商品信息包含英文，也要翻译成中文输出。**

**这条信息有高风险。原因: """ + risk_text + """**

写一条简短、礼貌的询问消息（不超过150字），要求:
1. 简单表达对商品感兴趣
2. 请卖家提供更多详情（具体型号、成色、照片等）
4. 询问卖家提供联系方式（微信、手机号）方便进一步沟通
5. 不要约定见面地点
6. 不要评价价格高低（可能被骗子利用）
7. 不要说"价格还行""有点低""挺划算"等任何价格判断
8. 语气保持中立谨慎

如果商品名是英文（如"Giant ATX660 bicycle"），可以保留品牌型号但用中文组织句子。
如果成色是英文（如"9/10 condition"），转换成中文（如"9成新"）。

只返回消息正文，不要加引号或解释。"""
            user_prompt = f"""商品: {product_name}
标价: {price_text}
成色: {condition}
卖家: {seller}
地点: {location}
风险等级: RED（高风险 — 原因: {risk_text}）

请用中文生成一条谨慎的询问消息，要求卖家提供更多详情和联系方式。不要评价价格。"""
        else:
            system_prompt = """你是一个大学生，要给二手群里的卖家发微信消息。

**重要：你必须用中文写这条消息。即使下面的商品信息包含英文，也要翻译成中文输出。**

写一条自然、口语化的消息（不超过150字），要求:
1. 表示对商品感兴趣
2. 随口提一下价格（不要判断价格"合理""有点低""挺划算"——只是自然地提到这个数字）
3. 建议见面看货
4. 如果满意可以当场交易

如果商品名是英文（如"Giant ATX660 bicycle"），可以保留品牌型号但用中文组织句子。
如果成色是英文（如"9/10 condition"），转换成中文（如"9成新"）。

只返回消息正文，不要加引号或解释。"""
            user_prompt = f"""商品: {product_name}
价格: {price_text}
成色: {condition}
卖家: {seller}
地点: {location}
风险等级: {risk_level}
风险原因: {risk_text}

请用中文生成一条发给卖家的微信消息。不要评价价格是否合理或偏低。"""

    print("[LLM] 正在用 AI 生成话术...")
    message = llm_chat(system_prompt, user_prompt, temperature=0.7, max_tokens=300)

    if message is None:
        print("[LLM] AI 话术生成失败，回退到模板")
        return None

    # 清理：去掉首尾引号
    message = message.strip().strip('"').strip("'").strip('"').strip('"').strip()

    return message


def generate_message(listing, user_need=None, lang="zh"):
    """
    生成砍价话术

    优先使用 LLM 生成，失败时自动回退到模板生成。

    Args:
        listing: 商品信息 dict
        user_need: 用户需求 dict (可选)
        lang: 语言 ("zh" / "en")

    Returns:
        str: 自然、完整的微信消息
    """
    # 先尝试 LLM 生成
    llm_result = generate_message_llm(listing, user_need, lang)
    if llm_result is not None:
        return llm_result

    # 回退到模板生成
    return generate_message_template(listing, user_need, lang)


def generate_message_template(listing, user_need=None, lang="zh"):
    """
    模板生成（原逻辑，作为 LLM 降级方案）
    """
    product_name = listing.get("product_name") or ("商品" if lang == "zh" else "item")
    price = listing.get("price")
    condition = listing.get("condition") or ""
    seller = listing.get("seller") or ("同学" if lang == "zh" else "there")
    risk_level = listing.get("risk_level", "green")

    if lang == "en":
        if risk_level == "red":
            # 高风险：不评价价格、不约定见面，只询问详情和联系方式
            parts = []
            parts.append(f"Hi, I saw your listing for {product_name} in the group chat. ")
            parts.append("I'd like to know more details (model, condition, photos). ")
            parts.append("Could you share your contact info so we can chat further?")
            message = "".join(parts)
        else:
            parts = []
            parts.append(f"Hi, I saw your listing for {product_name} in the group chat. ")

            if condition:
                condition_en = _condition_to_en(condition)
                parts.append(f"It's {condition_en}, ")

            parts.append("I'm quite interested. ")

            if price:
                price_str = f"{int(price)}" if price == int(price) else f"{price}"
                parts.append(f"You mentioned {price_str} yuan, ")

                if risk_level == "green":
                    parts.append("sounds good. ")
                else:  # yellow
                    parts.append("would you be open to a small discount? ")

            parts.append("Could we meet up so I can see it in person? If everything looks good, I can trade on the spot.")

            message = "".join(parts)
    else:
        if risk_level == "red":
            # 高风险：不评价价格、不约定见面，只询问详情和联系方式
            parts = []
            parts.append(f"你好，看到你在群里发的{product_name}，")
            parts.append("想了解一下具体情况（型号、成色、照片等）。")
            parts.append("方便的话可以加个联系方式进一步沟通吗？")
            message = "".join(parts)
        else:
            parts = []
            parts.append(f"你好，看到你在群里出{product_name}，")

            if condition:
                parts.append(f"{condition}的，")

            parts.append("我比较感兴趣。")

            if price:
                price_str = f"{int(price)}" if price == int(price) else f"{price}"
                parts.append(f"你说的{price_str}元，")

                if risk_level == "green":
                    parts.append("价格还行。")
                else:  # yellow
                    parts.append("能稍微让一点吗？")

            parts.append("方便的话可以见面看看实物吗？没问题的话我可以当面交易。")

            message = "".join(parts)

    return message


def _condition_to_en(condition):
    """成色中文转英文"""
    mapping = {
        "全新": "brand new",
        "全新没用过": "brand new, never used",
        "10成新": "10/10 condition",
        "9成新": "9/10 condition",
        "8成新": "8/10 condition",
        "7成新": "7/10 condition",
        "6成新": "6/10 condition",
        "5成新": "5/10 condition",
    }
    for key, val in mapping.items():
        if key in condition:
            return val
    return condition


def generate_summary(listing, message, lang="zh"):
    """生成交易方案摘要"""
    return {
        "product_name": listing.get("product_name"),
        "price": listing.get("price"),
        "seller": listing.get("seller"),
        "contact": listing.get("contact"),
        "risk_level": listing.get("risk_level"),
        "risk_reasons": listing.get("risk_reasons"),
        "message": message,
        "reminder": "见面验货后再付款，不要提前转账。" if lang == "zh" else "Inspect the item in person before paying. Never transfer money in advance.",
    }


if __name__ == "__main__":
    test_listing = {
        "product_name": "飞鸽自行车",
        "price": 180,
        "condition": "8成新",
        "seller": "董同学",
        "contact": "微信dong_bike",
        "risk_level": "green",
    }
    print("=== 中文 ===")
    print(generate_message(test_listing, lang="zh"))
    print()
    print("=== English ===")
    print(generate_message(test_listing, lang="en"))
