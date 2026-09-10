"""The specialist agents.

Each one queries the database through the tool layer and emits findings that
cite concrete numbers. Thresholds are explicit here rather than hidden in
prose, so a finding can always be traced to the rule and the rows behind it.
"""

import time

from sqlalchemy.orm import Session

from app.agents.base import Agent, AgentResult, Finding


def _timed(fn):
    def wrapper(self, db: Session, context: dict) -> AgentResult:
        start = time.perf_counter()
        result = fn(self, db, context)
        result.duration_ms = int((time.perf_counter() - start) * 1000)
        return result
    return wrapper


class SalesAgent(Agent):
    name, label, icon = "sales", "Sales Agent", "TrendingDown"
    task = "Analysing sales trends and revenue patterns"

    @_timed
    def run(self, db, context):
        r = AgentResult(agent=self.name, task=self.task)
        focus = context.get("focus_term", "")
        summary = self._call(db, r, "sales_summary", days=90)
        trend = self._call(db, r, "product_sales_trend", name_contains=focus, days=90)
        r.data = {"summary": summary, "products": trend[:8]}

        sev = "warning" if summary["revenue_change_pct"] < 0 else "info"
        r.findings.append(Finding(
            f"Revenue over the last 90 days is {summary['revenue']:,.0f} "
            f"({summary['revenue_change_pct']:+.1f}% vs the prior 90 days).",
            sev, summary["revenue_change_pct"]))

        decliners = [p for p in trend if p["change_pct"] < -5][:4]
        for p in decliners:
            r.findings.append(Finding(
                f"{p['name']} revenue fell {abs(p['change_pct']):.1f}% "
                f"({p['prior_revenue']:,.0f} -> {p['revenue']:,.0f}).",
                "critical" if p["change_pct"] < -20 else "warning",
                p["change_pct"], p["sku"]))
        if not decliners:
            r.findings.append(Finding("No product declined more than 5% period-over-period.", "info"))
        return r


class InventoryAgent(Agent):
    name, label, icon = "inventory", "Inventory Agent", "Package"
    task = "Checking stock levels, cover and turnover"

    @_timed
    def run(self, db, context):
        r = AgentResult(agent=self.name, task=self.task)
        focus = context.get("focus_term", "")
        status = self._call(db, r, "inventory_status", name_contains=focus)
        r.data = {"inventory": status[:8]}

        low = [s for s in status if s["below_reorder"]]
        urgent = [s for s in status if s["days_cover"] is not None and s["days_cover"] < 21]
        for s in urgent[:4]:
            r.findings.append(Finding(
                f"{s['name']} has {s['on_hand']} units — about {s['days_cover']} days of cover "
                f"at {s['daily_velocity']}/day.",
                "critical" if s["days_cover"] < 10 else "warning",
                float(s["days_cover"]), s["sku"]))
        if low:
            r.findings.append(Finding(
                f"{len(low)} product(s) are at or below their reorder level.",
                "warning", float(len(low))))
        stale = [s for s in status if s["daily_velocity"] == 0 and s["on_hand"] > 0]
        for s in stale[:2]:
            r.findings.append(Finding(
                f"{s['name']} has {s['on_hand']} units and no recorded sales in the last 90 days "
                f"({s['stock_value']:,.0f} tied up).", "warning", s["stock_value"], s["sku"]))
        if not r.findings:
            r.findings.append(Finding("Stock cover is healthy across the catalogue.", "info"))
        return r


class PricingAgent(Agent):
    name, label, icon = "pricing", "Pricing Agent", "DollarSign"
    task = "Comparing realised margin against list pricing"

    @_timed
    def run(self, db, context):
        r = AgentResult(agent=self.name, task=self.task)
        focus = context.get("focus_term", "")
        pricing = self._call(db, r, "pricing_position", name_contains=focus)
        r.data = {"pricing": pricing[:8]}

        discounted = [p for p in pricing if p["discount_vs_list_pct"] > 2 and p["units_90d"] > 0]
        for p in discounted[:3]:
            r.findings.append(Finding(
                f"{p['name']} is selling {p['discount_vs_list_pct']:.1f}% below list "
                f"({p['avg_selling_price']:,.2f} vs {p['list_price']:,.2f}), realised margin "
                f"{p['realised_margin_pct']:.1f}%.", "warning", p["discount_vs_list_pct"], p["sku"]))
        thin = [p for p in pricing if 0 < p["realised_margin_pct"] < 45 and p["units_90d"] > 0]
        for p in thin[:2]:
            r.findings.append(Finding(
                f"{p['name']} realises only {p['realised_margin_pct']:.1f}% margin.",
                "warning", p["realised_margin_pct"], p["sku"]))
        if not r.findings:
            r.findings.append(Finding("Realised margins are tracking list pricing.", "info"))
        return r


class CampaignAgent(Agent):
    name, label, icon = "campaign", "Campaign Agent", "Megaphone"
    task = "Reviewing campaign spend and return"

    @_timed
    def run(self, db, context):
        r = AgentResult(agent=self.name, task=self.task)
        campaigns = self._call(db, r, "campaign_status")
        r.data = {"campaigns": campaigns}
        active = [c for c in campaigns if c["status"] == "active"]
        for c in active:
            if c["roi"] < 2.5:
                r.findings.append(Finding(
                    f"Campaign '{c['name']}' ({c['channel']}) is returning {c['roi']:.1f}x on "
                    f"{c['spent']:,.0f} spent — below the 2.5x target.",
                    "warning" if c["roi"] >= 1.5 else "critical", c["roi"], c["code"]))
        best = max(campaigns, key=lambda c: c["roi"], default=None)
        if best and best["roi"] > 0:
            r.findings.append(Finding(
                f"Best performing channel is {best['channel']} via '{best['name']}' at "
                f"{best['roi']:.1f}x.", "info", best["roi"], best["code"]))
        if not r.findings:
            r.findings.append(Finding("No active campaigns to assess.", "info"))
        return r


class CustomerAgent(Agent):
    name, label, icon = "customer", "Customer Agent", "Users"
    task = "Analysing segment mix and churn exposure"

    @_timed
    def run(self, db, context):
        r = AgentResult(agent=self.name, task=self.task)
        health = self._call(db, r, "customer_health")
        r.data = health
        if health["at_risk_count"]:
            exposure = sum(c["spend"] for c in health["at_risk"])
            r.findings.append(Finding(
                f"{health['at_risk_count']} customers are at risk or churned, representing "
                f"{exposure:,.0f} in lifetime spend.",
                "critical" if exposure > 20000 else "warning", exposure))
        top = max(health["segments"], key=lambda s: s["spend_share_pct"], default=None)
        if top:
            r.findings.append(Finding(
                f"The {top['segment']} segment is {top['customers']} customers and "
                f"{top['spend_share_pct']:.1f}% of spend.",
                "warning" if top["spend_share_pct"] > 60 else "info", top["spend_share_pct"]))
        return r


class KnowledgeAgent(Agent):
    name, label, icon = "knowledge", "Knowledge Agent", "BookOpen"
    task = "Retrieving relevant policy and context documents"

    @_timed
    def run(self, db, context):
        r = AgentResult(agent=self.name, task=self.task)
        hits = self._call(db, r, "search_knowledge_base", query=context["question"], limit=4)
        r.data = {"citations": hits}
        for h in hits[:3]:
            r.findings.append(Finding(
                f"{h['title']} ({h['doc_type']}): {h['excerpt'][:180].strip()}…",
                "info", h["similarity"], f"doc:{h['document_id']}"))
        if not hits:
            r.findings.append(Finding("No supporting documents matched this question.", "info"))
        return r


class StoreAgent(Agent):
    name, label, icon = "store", "Store Agent", "Warehouse"
    task = "Comparing performance across locations"

    @_timed
    def run(self, db, context):
        r = AgentResult(agent=self.name, task=self.task)
        stores = self._call(db, r, "store_performance")
        r.data = {"stores": stores}
        if stores:
            worst, best = min(stores, key=lambda s: s["growth"]), max(stores, key=lambda s: s["growth"])
            r.findings.append(Finding(
                f"{best['store']} is growing fastest at {best['growth']:+.1f}%.", "info", best["growth"]))
            if worst["growth"] < 0:
                r.findings.append(Finding(
                    f"{worst['store']} is contracting at {worst['growth']:+.1f}% on "
                    f"{worst['revenue']:,.0f} revenue.", "warning", worst["growth"]))
        return r


SPECIALISTS: dict[str, type[Agent]] = {
    a.name: a for a in
    [SalesAgent, InventoryAgent, PricingAgent, CampaignAgent, CustomerAgent, StoreAgent, KnowledgeAgent]
}
