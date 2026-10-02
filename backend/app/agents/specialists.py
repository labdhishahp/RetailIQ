"""The specialist agents.

Each specialist owns a domain and a toolset, and investigates in one of two
modes (see base.py). In model mode the `mission` steers the model's own tool
choices. In rule mode `policy` makes the same kind of decisions explicitly:
it starts broad, reads the result, and only then decides whether to drill into
a product, check a competing explanation, or stop. Thresholds are written out
here so every rule finding traces back to the rule and the rows behind it.

Policies also raise `signals` — leads another specialist should follow — which
the lead investigator uses to plan its next round.
"""

import re

from app.agents.base import Agent, AgentResult, Context, Finding, Policy, call


def _derive(r: AgentResult, *values: float) -> None:
    """Register figures a rule computed from tool output, for the grounding check."""
    r._observations.append(list(values))


def _explain_product(d: dict, r: AgentResult) -> list[Finding]:
    """Tell apart the causes a product drilldown can distinguish."""
    out: list[Finding] = []
    if not d.get("found"):
        return out
    name, sku = d["name"], d["sku"]
    units, price = d["units_change_pct"], d["price_change_pct"]

    out_of_stock = [s for s in d["by_store"] if s["on_hand"] == 0 and s["prior_revenue_90d"] > 0]
    if out_of_stock:
        stores = ", ".join(s["store"] for s in out_of_stock[:3])
        out.append(Finding(
            f"{name} is out of stock at {stores}, where it previously sold — the decline is at "
            f"least partly supply-driven.", "critical", entity=sku))
        r.signal("stock_constrained", sku=sku, name=name)

    if price >= 3 and units < 0:
        out.append(Finding(
            f"Average selling price of {name} rose {price:+.1f}% "
            f"({d['avg_price_prior_4w']:,.2f} -> {d['avg_price_last_4w']:,.2f}) over the last 4 "
            f"weeks while units moved {units:+.1f}% — a price-led decline.", "warning",
            price, sku))
        r.signal("price_increase", sku=sku, name=name)
    elif price <= -3 and units <= 0:
        out.append(Finding(
            f"{name} is selling {price:+.1f}% cheaper than 4 weeks earlier but units moved "
            f"{units:+.1f}% — discounting is not buying volume.", "warning", price, sku))
        r.signal("discount_ineffective", sku=sku, name=name)

    lost_total = sum(s["revenue_lost"] for s in d["by_store"])
    worst = max(d["by_store"], key=lambda s: s["revenue_lost"], default=None)
    if worst and lost_total > 0 and len(d["by_store"]) > 1:
        share = round(worst["revenue_lost"] / lost_total * 100, 1)
        if share >= 60:
            _derive(r, share, lost_total)
            out.append(Finding(
                f"{share:.1f}% of the revenue lost on {name} is at {worst['store']} "
                f"({worst['revenue_lost']:,.0f} of {lost_total:,.0f}) — a location problem, "
                f"not a chain-wide one.", "warning", share, worst["store"]))
            r.signal("store_concentration", store=worst["store"], sku=sku, name=name)

    if not out and units < 0:
        out.append(Finding(
            f"{name} units moved {units:+.1f}% over 4 weeks at a stable price ({price:+.1f}%) "
            f"with stock available — a demand-led decline.", "warning", units, sku))
        r.signal("demand_decline", sku=sku, name=name)
    return out


class SalesAgent(Agent):
    name, label, icon = "sales", "Sales Agent", "TrendingDown"
    task = "Analysing sales trends and revenue patterns"
    tools = ("sales_summary", "product_sales_trend", "category_performance",
             "product_drilldown", "store_performance")
    mission = ("You explain revenue movement: how big it is, which products or categories "
               "drive it, and — for the biggest mover — whether the cause is demand, price, "
               "stock or a single store (product_drilldown separates these).")

    def policy(self, ctx: Context, r: AgentResult) -> Policy:
        findings: list[Finding] = []
        summary = yield call("sales_summary", days=90)
        findings.append(Finding(
            f"Revenue over the last 90 days is {summary['revenue']:,.0f} "
            f"({summary['revenue_change_pct']:+.1f}% vs the prior 90 days).",
            "warning" if summary["revenue_change_pct"] < 0 else "info",
            summary["revenue_change_pct"]))

        trend = yield call("product_sales_trend", name_contains=ctx.focus_term, days=90)
        decliners = [p for p in trend if p["change_pct"] < -5]
        for p in decliners[:3]:
            findings.append(Finding(
                f"{p['name']} revenue fell {abs(p['change_pct']):.1f}% "
                f"({p['prior_revenue']:,.0f} -> {p['revenue']:,.0f}).",
                "critical" if p["change_pct"] < -20 else "warning", p["change_pct"], p["sku"]))

        if decliners and decliners[0]["change_pct"] <= -10:
            worst = decliners[0]
            r.signal("product_decline", sku=worst["sku"], name=worst["name"])
            drill = yield call("product_drilldown", sku=worst["sku"])
            findings += _explain_product(drill, r)
        elif not decliners:
            findings.append(Finding("No product declined more than 5% period-over-period.", "info"))
            if not ctx.focus_term and summary["revenue_change_pct"] < 0:
                # Revenue is down but no single product explains it: look wider.
                cats = yield call("category_performance")
                weak = [c for c in cats if c["change_pct"] < 0]
                if weak:
                    c = weak[0]
                    findings.append(Finding(
                        f"{c['category']} is the weakest category at {c['change_pct']:+.1f}% "
                        f"({c['share_pct']:.1f}% of revenue).", "warning", c["change_pct"]))
                    r.signal("category_decline", category=c["category"])
        return findings


class InventoryAgent(Agent):
    name, label, icon = "inventory", "Inventory Agent", "Package"
    task = "Checking stock levels, cover and turnover"
    tools = ("inventory_status", "product_drilldown")
    mission = ("You assess stock risk: days of cover, reorder breaches and dead stock, and — for "
               "the most urgent product — where in the network the stock actually sits.")

    def policy(self, ctx: Context, r: AgentResult) -> Policy:
        findings: list[Finding] = []
        status = yield call("inventory_status", name_contains=ctx.focus_term)
        if ctx.focus_term and not status:
            # The focus matched nothing stocked; widen rather than report nothing.
            findings.append(Finding(f"No stocked product matches '{ctx.focus_term}'.", "info"))
            status = yield call("inventory_status", name_contains="")

        urgent = [s for s in status if s["days_cover"] is not None and s["days_cover"] < 21]
        low = [s for s in status if s["below_reorder"]]
        stale = [s for s in status if s["daily_velocity"] == 0 and s["on_hand"] > 0]
        for s in urgent[:4]:
            findings.append(Finding(
                f"{s['name']} has {s['on_hand']} units — about {s['days_cover']} days of cover "
                f"at {s['daily_velocity']}/day.",
                "critical" if s["days_cover"] < 10 else "warning", float(s["days_cover"]), s["sku"]))
            r.signal("stock_risk", sku=s["sku"], name=s["name"])
        if low:
            _derive(r, len(low))
            findings.append(Finding(
                f"{len(low)} product(s) are at or below their reorder level.", "warning", float(len(low))))
        for s in stale[:2]:
            findings.append(Finding(
                f"{s['name']} has {s['on_hand']} units and no recorded sales in the last 90 days "
                f"({s['stock_value']:,.0f} tied up).", "warning", s["stock_value"], s["sku"]))
            r.signal("dead_stock", sku=s["sku"], name=s["name"])

        if urgent:
            top = urgent[0]
            drill = yield call("product_drilldown", sku=top["sku"])
            stores = drill.get("by_store", []) if drill.get("found") else []
            empty = [s for s in stores if s["on_hand"] == 0]
            holding = max(stores, key=lambda s: s["on_hand"], default=None)
            total = drill.get("on_hand_total") or 0
            if empty and holding and holding["on_hand"] > 0:
                findings.append(Finding(
                    f"{top['name']}: {holding['store']} holds {holding['on_hand']} of {total} units "
                    f"while {', '.join(s['store'] for s in empty[:3])} hold none — rebalance "
                    f"before the next purchase order lands.", "warning", entity=top["sku"]))
            elif empty:
                findings.append(Finding(
                    f"{top['name']} is out of stock at {', '.join(s['store'] for s in empty[:3])}.",
                    "critical", entity=top["sku"]))

        if not findings:
            findings.append(Finding("Stock cover is healthy across the catalogue.", "info"))
        return findings


class PricingAgent(Agent):
    name, label, icon = "pricing", "Pricing Agent", "DollarSign"
    task = "Comparing realised margin against list pricing"
    tools = ("pricing_position", "product_drilldown")
    mission = ("You assess pricing: where products sell below list, where realised margin is "
               "thin, and whether the deepest discount is actually buying volume.")

    def policy(self, ctx: Context, r: AgentResult) -> Policy:
        findings: list[Finding] = []
        pricing = yield call("pricing_position", name_contains=ctx.focus_term)
        discounted = [p for p in pricing if p["discount_vs_list_pct"] > 2 and p["units_90d"] > 0]
        for p in discounted[:3]:
            findings.append(Finding(
                f"{p['name']} is selling {p['discount_vs_list_pct']:.1f}% below list "
                f"({p['avg_selling_price']:,.2f} vs {p['list_price']:,.2f}), realised margin "
                f"{p['realised_margin_pct']:.1f}%.", "warning", p["discount_vs_list_pct"], p["sku"]))
        thin = [p for p in pricing if 0 < p["realised_margin_pct"] < 45 and p["units_90d"] > 0]
        for p in thin[:2]:
            findings.append(Finding(
                f"{p['name']} realises only {p['realised_margin_pct']:.1f}% margin.",
                "warning", p["realised_margin_pct"], p["sku"]))

        if discounted:
            top = discounted[0]
            drill = yield call("product_drilldown", sku=top["sku"])
            if drill.get("found"):
                units = drill["units_change_pct"]
                if units > 0:
                    findings.append(Finding(
                        f"The discount on {top['name']} is buying volume: units {units:+.1f}% over "
                        f"the last 4 weeks.", "info", units, top["sku"]))
                else:
                    findings.append(Finding(
                        f"The discount on {top['name']} is not buying volume: units {units:+.1f}% "
                        f"over the last 4 weeks, so margin is being given away.",
                        "warning", units, top["sku"]))
                    r.signal("discount_ineffective", sku=top["sku"], name=top["name"])
        if not findings:
            findings.append(Finding("Realised margins are tracking list pricing.", "info"))
        return findings


class CampaignAgent(Agent):
    name, label, icon = "campaign", "Campaign Agent", "Megaphone"
    task = "Reviewing campaign spend and return"
    tools = ("campaign_status", "sales_summary")
    mission = ("You assess marketing: which campaigns return below the 2.5x ROI target, which "
               "channel performs best, and whether active spend is moving revenue at all.")

    def policy(self, ctx: Context, r: AgentResult) -> Policy:
        findings: list[Finding] = []
        campaigns = yield call("campaign_status")
        weak = [c for c in campaigns if c["status"] == "active" and c["roi"] < 2.5]
        for c in weak:
            findings.append(Finding(
                f"Campaign '{c['name']}' ({c['channel']}) is returning {c['roi']:.1f}x on "
                f"{c['spent']:,.0f} spent — below the 2.5x target.",
                "warning" if c["roi"] >= 1.5 else "critical", c["roi"], c["code"]))
            r.signal("campaign_underperform", code=c["code"])
        best = max(campaigns, key=lambda c: c["roi"], default=None)
        if best and best["roi"] > 0:
            findings.append(Finding(
                f"Best performing channel is {best['channel']} via '{best['name']}' at "
                f"{best['roi']:.1f}x.", "info", best["roi"], best["code"]))

        if weak:
            # Under-target spend matters more if it is not moving the topline.
            recent = yield call("sales_summary", days=30)
            spend = sum(c["spent"] for c in weak)
            _derive(r, spend, len(weak))
            if recent["revenue_change_pct"] <= 0:
                findings.append(Finding(
                    f"{spend:,.0f} of spend across {len(weak)} under-target campaign(s) has not "
                    f"lifted revenue: the last 30 days are {recent['revenue_change_pct']:+.1f}% "
                    f"on the prior 30.", "warning", recent["revenue_change_pct"]))
        if not findings:
            findings.append(Finding("No active campaigns to assess.", "info"))
        return findings


class CustomerAgent(Agent):
    name, label, icon = "customer", "Customer Agent", "Users"
    task = "Analysing segment mix and churn exposure"
    tools = ("customer_health", "campaign_status")
    mission = ("You assess the customer base: churn exposure, segment concentration, and which "
               "channel is best placed for a win-back.")

    def policy(self, ctx: Context, r: AgentResult) -> Policy:
        findings: list[Finding] = []
        health = yield call("customer_health")
        if health["at_risk_count"]:
            exposure = health["at_risk_spend"]
            findings.append(Finding(
                f"{health['at_risk_count']} customers are at risk or churned, representing "
                f"{exposure:,.0f} in lifetime spend.",
                "critical" if exposure > 20000 else "warning", exposure))
            r.signal("churn_exposure", customers=health["at_risk_count"])
        top = max(health["segments"], key=lambda s: s["spend_share_pct"], default=None)
        if top:
            findings.append(Finding(
                f"The {top['segment']} segment is {top['customers']} customers and "
                f"{top['spend_share_pct']:.1f}% of spend.",
                "warning" if top["spend_share_pct"] > 60 else "info", top["spend_share_pct"]))

        if health["at_risk_count"]:
            campaigns = yield call("campaign_status")
            active = [c for c in campaigns if c["status"] == "active" and c["roi"] > 0]
            best = max(active, key=lambda c: c["roi"], default=None)
            if best:
                findings.append(Finding(
                    f"The best-returning active channel for a win-back is {best['channel']} "
                    f"('{best['name']}', {best['roi']:.1f}x).", "info", best["roi"], best["code"]))
        return findings


class StoreAgent(Agent):
    name, label, icon = "store", "Store Agent", "Warehouse"
    task = "Comparing performance across locations"
    tools = ("store_performance",)
    mission = "You compare locations: which stores grow, which contract, and by how much."

    def policy(self, ctx: Context, r: AgentResult) -> Policy:
        findings: list[Finding] = []
        stores = yield call("store_performance")
        if stores:
            worst = min(stores, key=lambda s: s["growth"])
            best = max(stores, key=lambda s: s["growth"])
            findings.append(Finding(
                f"{best['store']} is growing fastest at {best['growth']:+.1f}%.", "info", best["growth"]))
            if worst["growth"] < 0:
                findings.append(Finding(
                    f"{worst['store']} is contracting at {worst['growth']:+.1f}% on "
                    f"{worst['revenue']:,.0f} revenue.", "warning", worst["growth"]))
                r.signal("store_decline", store=worst["store"])
        return findings


_STOP = {"what", "which", "why", "how", "are", "is", "the", "our", "we", "do", "does", "should",
         "this", "that", "with", "for", "and", "need", "needs", "there", "any", "about"}


class KnowledgeAgent(Agent):
    name, label, icon = "knowledge", "Knowledge Agent", "BookOpen"
    task = "Retrieving relevant policy and context documents"
    tools = ("search_knowledge_base",)
    mission = ("You find the company policy, playbook or context that governs what the other "
               "agents found. Search with specific terms; if results are thin, reformulate.")

    def policy(self, ctx: Context, r: AgentResult) -> Policy:
        query = ctx.objective or ctx.question
        hits = yield call("search_knowledge_base", query=query, limit=4)
        if len(hits) < 2:
            # Thin results: retry with the question's content words only.
            words = [w for w in re.findall(r"[a-z]{3,}", ctx.question.lower()) if w not in _STOP]
            retry = " ".join(words) or ctx.question
            if retry != query:
                more = yield call("search_knowledge_base", query=retry, limit=4)
                seen = {h["chunk_id"] for h in hits}
                hits = hits + [h for h in more if h["chunk_id"] not in seen]
        findings = [
            Finding(f"{h['title']} ({h['doc_type']}): {h['excerpt'][:180].strip()}…",
                    "info", h["similarity"], f"doc:{h['document_id']}")
            for h in hits[:3]
        ]
        if not findings:
            findings.append(Finding("No supporting documents matched this question.", "info"))
        return findings


SPECIALISTS: dict[str, type[Agent]] = {
    a.name: a for a in
    [SalesAgent, InventoryAgent, PricingAgent, CampaignAgent, CustomerAgent, StoreAgent, KnowledgeAgent]
}
