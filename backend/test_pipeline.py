"""
端到端集成测试 — 模拟完整 Agent 工作流 (Bilingual: English data)
nlp_extractor → matcher → risk_check → negotiator
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nlp_extractor import extract_listings, load_mock_data
from matcher import parse_user_need, match_listings
from risk_check import check_all_risks, RISK_LABELS
from negotiator import generate_message, generate_summary


def run_test():
    print("=" * 70)
    print("Campus Second-Hand Trading Agent — End-to-End Integration Test")
    print("=" * 70)

    # Step 1: Load chat data + NLP extraction
    print("\n[Step 1] Load chat data + NLP extraction")
    chat_data = load_mock_data()
    print(f"  Loaded {len(chat_data)} chat messages")

    listings = extract_listings(chat_data)
    print(f"  Extracted {len(listings)} valid listings")

    # Step 2: User need parsing
    print("\n[Step 2] User need parsing")
    test_cases = [
        ("looking for a bicycle, budget 300, on campus", "en"),
        ("want to buy an iPhone, budget 2000, east area", "en"),
        ("need a textbook, budget 20, on campus", "en"),
        ("looking for headphones", "en"),  # incomplete info test
        ("want a guitar, budget 200", "en"),  # missing location
    ]

    for msg, lang in test_cases:
        print(f"\n  Input: {msg}")
        need = parse_user_need(msg, lang=lang)
        print(f"  Product: {need['product_name']}")
        print(f"  Budget: {need['budget']}")
        print(f"  Location: {need['location']}")

        if not need["complete"]:
            field_names = {
                "product_name": "product name",
                "budget": "budget",
                "location": "location",
            }
            missing_names = [field_names.get(f, f) for f in need["missing"]]
            print(f"  >>> Incomplete, need to ask: {missing_names}")
            continue

        # Step 3: Matching
        print(f"  >>> Complete need, start matching...")
        matched = match_listings(listings, need)
        print(f"  Matched {len(matched)} listings")

        if not matched:
            print("  No matching listings found")
            continue

        # Step 4: Risk assessment + sorting
        print("\n[Step 3-4] Risk assessment + sorting")
        enriched = check_all_risks(matched, lang="en")
        for item in enriched[:5]:
            risk = item.get("risk_level", "unknown")
            label = RISK_LABELS["en"].get(risk, "?")
            print(f"    [{label}] {item['product_name']} | {item['price']} yuan | "
                  f"{item.get('condition', '?')} | contact={item.get('contact', 'N/A')} | "
                  f"score={item.get('match_score', 0)}")

        # Step 5: Message generation (pick first green/yellow item)
        green_items = [i for i in enriched if i["risk_level"] == "green"]
        if not green_items:
            green_items = [i for i in enriched if i["risk_level"] == "yellow"]
        if green_items:
            target = green_items[0]
            print(f"\n[Step 5] Generate message -> {target['product_name']}")
            msg = generate_message(target, need, lang="en")
            print(f"  Message ({len(msg)} chars):")
            print(f"  {msg}")
            summary = generate_summary(target, msg, lang="en")
            print(f"  Summary: {json.dumps(summary, ensure_ascii=False, indent=2)}")

    print("\n" + "=" * 70)
    print("Test complete!")
    print("=" * 70)


if __name__ == "__main__":
    run_test()
