"""
Flask 后端 API — 校园二手交易 Agent

运行: python app.py
端口: 5000
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
import json
import re

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nlp_extractor import extract_listings, load_mock_data
from matcher import parse_user_need, match_listings
from risk_check import check_all_risks, get_risk_label
from negotiator import generate_message, generate_summary
from wxauto_sender import send_message, check_wechat_status

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# 全局状态
_extracted_listings = None      # AI提取的全部候选listings（等用户确认）
_confirmed_listings = None      # 用户确认导入的listings（用于匹配）


def parse_chat_text(text):
    """
    将粘贴的纯文本聊天记录解析为结构化消息列表

    支持格式:
    - 张同学: 出捷安特自行车 250元
    - [14:30] 张同学: 出捷安特自行车 250元
    - 张同学 出捷安特自行车 250元（空格分隔）
    - JSON数组格式
    """
    text = text.strip()
    if not text:
        return []

    # 尝试 JSON 格式
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    messages = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue

        # [time] sender: content
        m = re.match(r'\[?(\d{1,2}[:：]\d{2})\]?\s*(.+?)[:：]\s*(.+)', line)
        if m:
            messages.append({
                "sender": m.group(2).strip(),
                "content": m.group(3).strip(),
                "time": m.group(1)
            })
            continue

        # sender: content 或 sender：content
        m = re.match(r'(.+?)[:：]\s*(.+)', line)
        if m:
            sender = m.group(1).strip()
            content = m.group(2).strip()
            # 排除过长或过短的sender
            if 1 < len(sender) <= 20:
                messages.append({
                    "sender": sender,
                    "content": content,
                    "time": ""
                })
                continue

        # 整行作为content（无sender）
        messages.append({
            "sender": "Unknown",
            "content": line,
            "time": ""
        })

    return messages


def get_listings():
    """获取已确认导入的 listings"""
    global _confirmed_listings, _extracted_listings
    if _confirmed_listings is not None:
        return _confirmed_listings
    # 降级：如果没有确认导入，自动加载演示数据
    if _extracted_listings is None:
        chat_data = load_mock_data()
        _extracted_listings = extract_listings(chat_data)
    return _extracted_listings


# ==================== 导入相关 API ====================

@app.route("/api/import", methods=["POST"])
def api_import():
    """导入聊天数据，AI提取商品信息返回给用户确认"""
    global _extracted_listings
    data = request.get_json() or {}
    if not data:
        return jsonify({"status": "error", "error": "Missing request data"}), 400

    source = data.get("source", "demo")
    text = data.get("text", "")
    lang = data.get("lang", "zh")

    if source == "demo":
        chat_data = load_mock_data()
    elif source == "text":
        chat_data = parse_chat_text(text)
        if not chat_data:
            err = "无法解析聊天文本，请检查格式" if lang == "zh" else "Cannot parse chat text, check format"
            return jsonify({"status": "error", "error": err}), 400
    elif source == "file":
        chat_data = parse_chat_text(text)
        if not chat_data:
            err = "无法解析文件内容" if lang == "zh" else "Cannot parse file content"
            return jsonify({"status": "error", "error": err}), 400
    else:
        err = "未知数据源" if lang == "zh" else "Unknown data source"
        return jsonify({"status": "error", "error": err}), 400

    # AI提取商品信息（按 lang 返回对应语言的 category/location）
    _extracted_listings = extract_listings(chat_data, lang=lang)

    # 统计
    trade_count = len(_extracted_listings)
    non_trade_count = len(chat_data) - trade_count

    # 构建返回结果
    listings_preview = []
    for item in _extracted_listings:
        listings_preview.append({
            "id": item["id"],
            "product_name": item.get("product_name"),
            "price": item.get("price"),
            "condition": item.get("condition"),
            "seller": item.get("seller"),
            "contact": item.get("contact"),
            "location": item.get("location"),
            "category": item.get("category"),
            "source_text": item.get("source_text", "")[:80],
        })

    if lang == "en":
        msg = f"Extracted {trade_count} listings from {len(chat_data)} messages"
    else:
        msg = f"从 {len(chat_data)} 条消息中提取了 {trade_count} 个商品信息"

    return jsonify({
        "status": "success",
        "total_messages": len(chat_data),
        "trade_count": trade_count,
        "non_trade_count": non_trade_count,
        "listings": listings_preview,
        "message": msg
    })


@app.route("/api/confirm-import", methods=["POST"])
def api_confirm_import():
    """用户确认导入选中的 listings"""
    global _confirmed_listings, _extracted_listings
    data = request.get_json() or {}
    if "listing_ids" not in data:
        err = "缺少 listing_ids" if data.get("lang", "zh") == "zh" else "Missing listing_ids"
        return jsonify({"status": "error", "error": err}), 400
    lang = data.get("lang", "zh")

    if _extracted_listings is None:
        err = "请先导入数据" if lang == "zh" else "Please import data first"
        return jsonify({"status": "error", "error": err}), 400

    listing_ids = set(data["listing_ids"])

    # 全选的情况
    if not listing_ids:
        _confirmed_listings = list(_extracted_listings)
    else:
        _confirmed_listings = [l for l in _extracted_listings if l["id"] in listing_ids]

    if lang == "en":
        msg = f"Successfully imported {len(_confirmed_listings)} listings"
    else:
        msg = f"成功导入 {len(_confirmed_listings)} 个商品信息"
    return jsonify({
        "status": "success",
        "count": len(_confirmed_listings),
        "message": msg
    })


@app.route("/api/listings", methods=["GET"])
def api_listings():
    """查看已导入的 listings"""
    listings = get_listings()
    return jsonify({
        "status": "success",
        "count": len(listings),
        "listings": [{
            "id": l.get("id"),
            "product_name": l.get("product_name"),
            "price": l.get("price"),
            "seller": l.get("seller"),
            "category": l.get("category"),
        } for l in listings]
    })


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """重置导入状态，重新选择数据源"""
    global _extracted_listings, _confirmed_listings
    _extracted_listings = None
    _confirmed_listings = None
    return jsonify({"status": "success", "message": "Reset complete, ready to re-import"})


# ==================== 主业务 API ====================

@app.route("/api/start", methods=["POST"])
def api_start():
    """接收用户需求，启动 Agent 工作流"""
    data = request.get_json() or {}
    if "message" not in data:
        err = "缺少 message 字段" if data.get("lang", "zh") == "zh" else "Missing message field"
        return jsonify({"status": "error", "error": err}), 400

    message = data["message"]
    lang = data.get("lang", "zh")

    # 从前端接收多轮对话上下文（之前轮次已确认的信息）
    context = data.get("context") or {}

    user_need = parse_user_need(message, lang)

    # 合并上下文：新解析的字段优先，旧字段作为兜底
    merged = {
        "product_name": user_need.get("product_name") or context.get("product_name"),
        "budget": user_need.get("budget") if user_need.get("budget") is not None else context.get("budget"),
        "location": user_need.get("location") or context.get("location"),
    }
    user_need["product_name"] = merged["product_name"]
    user_need["budget"] = merged["budget"]
    user_need["location"] = merged["location"]

    # 重新计算 missing
    missing_fields = []
    if not user_need["product_name"]:
        missing_fields.append("product_name")
    if user_need["budget"] is None:
        missing_fields.append("budget")
    if not user_need["location"]:
        missing_fields.append("location")
    user_need["missing"] = missing_fields
    user_need["complete"] = len(missing_fields) == 0

    # 信息完整性检查
    if not user_need["complete"]:
        missing_fields = user_need["missing"]
        if lang == "en":
            field_names = {
                "product_name": "item name",
                "budget": "budget",
                "location": "trade location",
            }
            missing_names = [field_names.get(f, f) for f in missing_fields]
            question = "Just need to confirm: what are the " + ", ".join(missing_names) + "?"
        else:
            field_names = {
                "product_name": "物品名称",
                "budget": "预算",
                "location": "交易地点",
            }
            missing_names = [field_names.get(f, f) for f in missing_fields]
            question = "还需要确认一下：" + "、".join(missing_names) + "分别是什么？"
        return jsonify({
            "status": "need_more_info",
            "question": question,
            "missing": missing_fields,
            "parsed": {
                "product_name": user_need["product_name"],
                "budget": user_need["budget"],
                "location": user_need["location"],
            },
        })

    # 执行 Agent 工作流
    steps = []
    listings = get_listings()
    if lang == "en":
        steps.append(f"Read {len(listings)} listings from imported data (AI extracted)")
    else:
        steps.append(f"读取 {len(listings)} 个商品（AI 提取）")

    matched = match_listings(listings, user_need, lang=lang)
    if lang == "en":
        steps.append(f"AI semantic matching -> {len(matched)} found")
    else:
        steps.append(f"AI 语义匹配 → {len(matched)} 个符合")

    enriched = check_all_risks(matched, lang)
    if lang == "en":
        steps.append("AI risk assessment complete")
    else:
        steps.append("AI 风险评估完成")

    # 构建 Result cards
    results = []
    for item in enriched:
        results.append({
            "id": len(results) + 1,
            "product_name": item.get("product_name"),
            "price": item.get("price"),
            "condition": item.get("condition"),
            "seller": item.get("seller"),
            "contact": item.get("contact"),
            "description": item.get("description"),
            "location": item.get("location"),
            "risk_level": item.get("risk_level"),
            "risk_reasons": item.get("risk_reasons"),
            "recommendation": get_risk_label(item.get("risk_level"), lang),
            "match_score": item.get("match_score", 0),
        })

    return jsonify({
        "status": "complete",
        "steps": steps,
        "parsed_need": {
            "product_name": user_need["product_name"],
            "budget": user_need["budget"],
            "location": user_need["location"],
        },
        "results": results,
    })


@app.route("/api/negotiate", methods=["POST"])
def api_negotiate():
    """用户选择商品，生成砍价话术"""
    data = request.get_json() or {}
    if "listing" not in data:
        err = "缺少 listing 字段" if data.get("lang", "zh") == "zh" else "Missing listing field"
        return jsonify({"status": "error", "error": err}), 400

    listing = data["listing"]
    lang = data.get("lang", "zh")
    message = generate_message(listing, lang=lang)
    summary = generate_summary(listing, message, lang=lang)

    return jsonify({
        "status": "success",
        "message": message,
        "contact": listing.get("seller"),
        "summary": summary,
    })


@app.route("/api/send", methods=["POST"])
def api_send():
    """用户确认，wxauto 自动发送微信消息"""
    data = request.get_json() or {}
    lang = data.get("lang", "zh")
    if "contact" not in data or "message" not in data:
        err = "缺少 contact 或 message 字段" if lang == "zh" else "Missing contact or message field"
        return jsonify({"status": "error", "error": err}), 400

    contact = data["contact"]
    message = data["message"]

    result = send_message(contact, message)

    if lang == "en":
        reminder = "Message sent to seller. Reminder: inspect the item in person before paying. Never transfer money in advance."
    else:
        reminder = "已发送消息给卖家。提醒：见面验货后再付款，不要提前转账。"

    return jsonify({
        "status": result["status"],
        "contact": result.get("contact"),
        "message_sent": message if result["status"] == "success" else None,
        "error": result.get("error"),
        "reminder": reminder,
    })


@app.route("/api/wechat/status", methods=["GET"])
def api_wechat_status():
    """检查微信客户端状态"""
    status = check_wechat_status()
    return jsonify(status)


@app.route("/", methods=["GET"])
def index():
    """提供前端页面"""
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    print("=" * 50)
    print("校园二手交易 Agent — 后端服务")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)
