"""
Agent Framework — Multi-Agent Collaboration + Parallel Execution + Self-Validation

Architecture:
    OrchestratorAgent
    +-- plan()               -> task decomposition (visible to user)
    +-- execute_pipeline()   -> parallel execution
    |   +-- MatcherAgent     (semantic match + score)      --|
    |   +-- RiskCheckAgent   (risk assessment)              --|  PARALLEL
    +-- merge()              -> combine results
    +-- validate()           -> self-check output quality
    +-- adapt()              -> dynamic suggestions

Each Agent:
    - Has a name, role, and execution log
    - Can retry on LLM failure
    - Reports decisions back to Orchestrator
"""

import time
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed

from nlp_extractor import extract_listings
from matcher import parse_user_need, match_listings
from risk_check import check_all_risks, get_risk_label
from negotiator import generate_message, generate_summary


# ================================================================
#  Agent Log
# ================================================================

class AgentLog:
    """Single log entry from an Agent's execution."""

    def __init__(self, agent, action, detail="", status="info", duration=None):
        self.agent = agent
        self.action = action
        self.detail = detail
        self.status = status       # info / success / warning / error / parallel
        self.duration = duration
        self.timestamp = time.time()

    def to_dict(self):
        return {
            "agent": self.agent,
            "action": self.action,
            "detail": self.detail,
            "status": self.status,
            "duration": round(self.duration, 2) if self.duration else None,
        }


# ================================================================
#  Agent Base
# ================================================================

class Agent:
    """Base agent wrapper with logging."""

    def __init__(self, name, role):
        self.name = name
        self.role = role
        self.logs = []

    def log(self, action, detail="", status="info", duration=None):
        entry = AgentLog(self.name, action, detail, status, duration=duration)
        self.logs.append(entry)
        print(f"[{self.name}] {action}: {detail}")
        return entry

    def clear_logs(self):
        self.logs = []

    def get_logs(self):
        return [log.to_dict() for log in self.logs]


# ================================================================
#  Sub-Agents
# ================================================================

class CollectorAgent(Agent):
    """Collector Agent - NLP extraction from chat data."""

    def __init__(self):
        super().__init__("Collector", "NLP Info Extraction")

    def execute(self, chat_data, lang="zh"):
        self.clear_logs()
        self.log("Start", f"Reading {len(chat_data)} chat messages")

        start = time.time()
        listings = extract_listings(chat_data, lang=lang)
        duration = time.time() - start

        trade_count = len(listings)
        non_trade = len(chat_data) - trade_count

        self.log("Extraction complete",
                 f"Extracted {trade_count} listings, filtered {non_trade} non-trade messages",
                 "success", duration)

        return listings, duration


class MatcherAgent(Agent):
    """Matcher Agent - semantic matching + scoring."""

    def __init__(self):
        super().__init__("Matcher", "Semantic Match + Score")

    def execute(self, listings, user_need, lang="zh"):
        self.clear_logs()
        product = user_need.get("product_name", "?")
        budget = user_need.get("budget", "?")
        location = user_need.get("location", "?")

        self.log("Start", f"Matching: {product} / <={budget} yuan / {location}")

        start = time.time()
        matched = match_listings(listings, user_need, lang=lang)
        duration = time.time() - start

        self.log("Match complete",
                 f"{len(matched)} / {len(listings)} listings matched",
                 "success", duration)

        if matched:
            top = matched[0]
            self.log("Top match",
                     f"{top.get('product_name')} | score={top.get('match_score', 0)}",
                     "info")

        if not matched:
            self.log("No matches", "Suggest adjusting budget or location", "warning")

        return matched, duration


class RiskCheckAgent(Agent):
    """RiskCheck Agent - risk assessment (runs in parallel with Matcher)."""

    def __init__(self):
        super().__init__("RiskCheck", "Risk Assessment")

    def execute(self, listings, lang="zh"):
        """Assess risk for all listings (independent of matching)."""
        self.clear_logs()
        self.log("Start", f"Assessing risk for {len(listings)} listings")

        start = time.time()
        enriched = check_all_risks(listings, lang)
        duration = time.time() - start

        green = sum(1 for l in enriched if l.get("risk_level") == "green")
        yellow = sum(1 for l in enriched if l.get("risk_level") == "yellow")
        red = sum(1 for l in enriched if l.get("risk_level") == "red")

        self.log("Assessment complete",
                 f"Green {green} / Yellow {yellow} / Red {red}",
                 "success", duration)

        # Log individual high-risk items
        for item in enriched:
            if item.get("risk_level") == "red":
                reasons = item.get("risk_reasons", [])
                self.log("High risk",
                         f"{item.get('product_name')}: {'; '.join(reasons)}",
                         "error")

        return enriched, duration


class NegotiatorAgent(Agent):
    """Negotiator Agent - message generation."""

    def __init__(self):
        super().__init__("Negotiator", "Message Generation")

    def execute(self, listing, lang="zh"):
        self.clear_logs()
        risk = listing.get("risk_level", "green")
        self.log("Start",
                 f"Generating message for {listing.get('product_name')} (risk={risk})")

        start = time.time()
        message = generate_message(listing, lang=lang)
        duration = time.time() - start

        self.log("Generation complete", f"{len(message)} chars", "success", duration)

        if risk == "red":
            self.log("Risk strategy",
                     "High-risk item: no price judgment, ask for details + contact only",
                     "warning")

        return message, duration


# ================================================================
#  Orchestrator
# ================================================================

class OrchestratorAgent(Agent):
    """
    Orchestrator - plans, coordinates parallel execution, validates, adapts.

    Parallel strategy:
        Matcher and RiskCheck run simultaneously in a ThreadPoolExecutor.
        RiskCheck assesses ALL listings (not just matched ones),
        so it can start immediately without waiting for Matcher.
        After both complete, merge: keep only matched items + their risk info.
    """

    def __init__(self):
        super().__init__("Orchestrator", "Task Planning + Coordination")
        self.matcher = MatcherAgent()
        self.risk_checker = RiskCheckAgent()
        self.negotiator = NegotiatorAgent()

    def plan(self, user_need, listing_count):
        """Generate a visible task plan before execution."""
        product = user_need.get("product_name", "?")
        budget = user_need.get("budget", "?")
        location = user_need.get("location", "?")

        steps = [
            {
                "step": 1,
                "agent": "Matcher",
                "action": f"Semantic match: {product} / <={budget} yuan / {location}",
                "status": "pending",
            },
            {
                "step": 2,
                "agent": "RiskCheck",
                "action": "Risk assessment (parallel with Step 1)",
                "status": "pending",
                "parallel": True,
            },
            {
                "step": 3,
                "agent": "Orchestrator",
                "action": "Merge results, sort by risk + score",
                "status": "pending",
            },
            {
                "step": 4,
                "agent": "Orchestrator",
                "action": "Self-validate output quality",
                "status": "pending",
            },
        ]

        self.log("Task decomposition", f"Generated {len(steps)} execution steps", "info")
        return steps

    def execute_pipeline(self, listings, user_need, lang="zh"):
        """
        Execute the Agent pipeline with parallel execution.

        Returns:
            (results, all_logs, parallel_info)
        """
        all_logs = []

        # === Phase 1: Parallel Execution ===
        self.log("Parallel start", "Matcher + RiskCheck executing simultaneously", "parallel")

        start_total = time.time()

        # Deep copy listings for RiskCheck (avoid data races)
        listings_for_risk = [copy.deepcopy(l) for l in listings]

        with ThreadPoolExecutor(max_workers=2) as pool:
            # Task A: Semantic match
            match_future = pool.submit(
                self.matcher.execute, listings, user_need, lang
            )
            # Task B: Risk assessment on ALL listings (independent of matching)
            risk_future = pool.submit(
                self.risk_checker.execute, listings_for_risk, lang
            )

            matched, match_duration = match_future.result()
            all_risked, risk_duration = risk_future.result()

        total_duration = time.time() - start_total

        self.log("Parallel complete",
                 f"Matcher: {match_duration:.2f}s | RiskCheck: {risk_duration:.2f}s | "
                 f"Total: {total_duration:.2f}s",
                 "success")

        # === Phase 2: Merge Results ===
        self.log("Merging", f"Matched {len(matched)} + Risk-assessed {len(all_risked)}", "info")

        # Build risk lookup by (product_name, seller)
        risk_lookup = {}
        for item in all_risked:
            key = (item.get("product_name"), item.get("seller"))
            risk_lookup[key] = {
                "risk_level": item.get("risk_level", "green"),
                "risk_reasons": item.get("risk_reasons", []),
            }

        # Merge risk info into matched items
        for item in matched:
            key = (item.get("product_name"), item.get("seller"))
            risk_info = risk_lookup.get(key, {"risk_level": "green", "risk_reasons": []})
            item["risk_level"] = risk_info["risk_level"]
            item["risk_reasons"] = risk_info["risk_reasons"]

        # === Phase 3: Sort ===
        risk_order = {"green": 0, "yellow": 1, "red": 2}
        matched.sort(key=lambda x: (
            risk_order.get(x.get("risk_level", "green"), 0),
            -x.get("match_score", 0),
        ))

        self.log("Sort complete", "Order: green -> yellow -> red (by score within each)", "info")

        # === Phase 4: Self-Validation ===
        self._validate(matched, user_need)

        # Collect all logs (order: Matcher, RiskCheck, Orchestrator)
        all_logs.extend(self.matcher.get_logs())
        all_logs.extend(self.risk_checker.get_logs())
        all_logs.extend(self.get_logs())

        parallel_info = {
            "parallel": True,
            "matcher": {
                "duration": round(match_duration, 2),
                "status": "done",
            },
            "risk_checker": {
                "duration": round(risk_duration, 2),
                "status": "done",
                "parallel_with": "matcher",
            },
            "total": round(total_duration, 2),
        }

        return matched, all_logs, parallel_info

    def _validate(self, results, user_need):
        """Self-validation: check result quality."""
        if not results:
            self.log("Validation", "No matches found - suggest adjusting needs", "warning")
            return

        green = sum(1 for r in results if r.get("risk_level") == "green")
        yellow = sum(1 for r in results if r.get("risk_level") == "yellow")
        red = sum(1 for r in results if r.get("risk_level") == "red")

        self.log("Validation passed",
                 f"Recommended {green} / Consider {yellow} / Not recommended {red}",
                 "success")

        # Warn if all results are high-risk
        if green == 0 and yellow == 0 and red > 0:
            self.log("Risk warning",
                     "All matched items have high risk - proceed with caution",
                     "error")

        # Warn if top result is red
        if results and results[0].get("risk_level") == "red":
            self.log("Sort warning",
                     "Top result is high-risk - no green/yellow items available",
                     "warning")

    def adapt(self, results, user_need):
        """Generate dynamic adaptation suggestions."""
        suggestions = []

        if not results:
            budget = user_need.get("budget", 0)
            if budget:
                suggestions.append(
                    f"No matches found. Try increasing budget to ~{int(budget * 1.3)} "
                    f"or expanding trade location."
                )
            else:
                suggestions.append("No matches found. Try adjusting your search criteria.")
            return suggestions

        red_count = sum(1 for r in results if r.get("risk_level") == "red")
        total = len(results)

        if total > 0 and red_count > total / 2:
            suggestions.append(
                "More than half of matched items have high risk. "
                "Consider expanding your search or lowering expectations."
            )

        # Suggest next steps if we have green items
        green_items = [r for r in results if r.get("risk_level") == "green"]
        if green_items:
            top = green_items[0]
            suggestions.append(
                f"Top recommendation: {top.get('product_name')} "
                f"at {top.get('price', '?')} yuan. "
                f"Click to generate a negotiation message."
            )

        return suggestions

    def negotiate(self, listing, lang="zh"):
        """Delegate to NegotiatorAgent."""
        message, duration = self.negotiator.execute(listing, lang=lang)
        return message, self.negotiator.get_logs()


# ================================================================
#  Singleton
# ================================================================

_orchestrator = None


def get_orchestrator():
    """Get or create the singleton OrchestratorAgent."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = OrchestratorAgent()
    return _orchestrator


if __name__ == "__main__":
    # Quick test
    from nlp_extractor import load_mock_data

    chat_data = load_mock_data()
    orch = get_orchestrator()

    # Simulate user need
    user_need = {
        "product_name": "bicycle",
        "budget": 300,
        "location": "on campus",
        "complete": True,
        "missing": [],
    }

    print("=" * 60)
    print("Orchestrator Test")
    print("=" * 60)

    # Step 1: Extract listings
    listings, _ = CollectorAgent().execute(chat_data, lang="en")
    print(f"\nExtracted {len(listings)} listings")

    # Step 2: Plan
    plan = orch.plan(user_need, len(listings))
    print("\n--- Task Plan ---")
    for step in plan:
        print(f"  Step {step['step']}: [{step['agent']}] {step['action']}")

    # Step 3: Execute pipeline
    print("\n--- Executing Pipeline ---")
    results, logs, parallel_info = orch.execute_pipeline(listings, user_need, lang="en")

    print(f"\n--- Results ({len(results)}) ---")
    for r in results[:5]:
        print(f"  [{r.get('risk_level', '?')}] {r.get('product_name')} | "
              f"{r.get('price', '?')} yuan | score={r.get('match_score', 0)}")

    print(f"\n--- Parallel Info ---")
    print(f"  {parallel_info}")

    print(f"\n--- Agent Logs ({len(logs)}) ---")
    for log in logs:
        print(f"  [{log['agent']}] {log['action']}: {log['detail']} ({log['status']})")

    # Step 4: Adapt
    suggestions = orch.adapt(results, user_need)
    print(f"\n--- Suggestions ---")
    for s in suggestions:
        print(f"  - {s}")
