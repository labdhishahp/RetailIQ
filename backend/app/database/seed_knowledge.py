"""Knowledge-base corpus seeded for RAG retrieval.

These are the unstructured documents the copilot's Knowledge Agent retrieves
from: pricing and replenishment policy, supplier terms, category playbooks and
competitor intelligence. They give the agents context the relational tables
cannot express.
"""

DOCUMENTS: list[dict] = [
    {
        "title": "Pricing and Discount Policy",
        "doc_type": "policy",
        "source": "Commercial Handbook v4",
        "content": """RetailIQ Pricing and Discount Policy

Standard margin floors. Every category carries a minimum realised gross margin.
Personal Care and Home & Living must not fall below 50%. Electronics must not
fall below 40% because of higher unit costs. Groceries operate on a 45% floor.
Apparel and Sports & Outdoors hold a 48% floor.

Discount authority. Discounts up to 10% off list may be approved by a store
manager. Discounts between 10% and 25% require category manager sign-off and a
written margin impact assessment. Discounts above 25% require commercial
director approval and are only permitted for clearance of dead stock or
end-of-life product lines.

Promotional bundling. Bundled promotions are preferred over straight price cuts
because they protect the reference price of the headline product. A bundle
should pair a declining product with an attached accessory or complementary
consumable from the same category.

Competitor response. Price matching is not automatic. When a competitor
discounts a comparable product, the category manager assesses whether the
affected line is price-elastic. Inelastic lines should hold price and respond
with marketing rather than discounting.

Margin recovery. Where realised selling price has drifted more than 8% below
list for a sustained period, the line must be reviewed. Persistent drift
usually indicates unmanaged store-level discounting rather than a deliberate
promotion.""",
    },
    {
        "title": "Inventory Replenishment Standard",
        "doc_type": "policy",
        "source": "Operations Manual",
        "content": """Inventory Replenishment Standard

Reorder triggers. A stocking location must raise a purchase order when on-hand
quantity falls to or below the reorder level. Where daily sales velocity gives
fewer than 14 days of cover, the reorder is treated as urgent regardless of the
reorder level.

Cover targets. The business targets 30 to 45 days of cover for fast-moving
lines and 60 to 90 days for slow-moving lines. Cover below 10 days is a
critical exception and must be escalated the same day.

Safety stock. Safety stock is set at roughly two weeks of average velocity.
Products with volatile demand, particularly seasonal apparel and promotional
electronics, carry a higher buffer during their peak window.

Dead stock. Stock with no recorded movement for 60 days is classified as dead.
Dead stock should be cleared through markdown, bundling or transfer to a store
with demonstrated demand. Capital tied up in dead stock is reported monthly.

Overstock. Holding more than twice the reorder level is treated as overstock.
Overstock ties up working capital and increases obsolescence risk, and should
be corrected by pausing replenishment rather than by immediate markdown.

Fill rate. The chain targets a fill rate above 95%. Fill rate below 80%
indicates systemic under-ordering rather than isolated stockouts.""",
    },
    {
        "title": "Campaign Performance Playbook",
        "doc_type": "playbook",
        "source": "Marketing Operations",
        "content": """Campaign Performance Playbook

ROI targets. Every active campaign is measured against a 2.5x return on ad
spend. Campaigns below 2.5x are reviewed at the next weekly trading meeting.
Campaigns below 1.5x are candidates for immediate suspension and budget
reallocation.

Channel characteristics. Email consistently delivers the highest return
because it addresses an existing customer base at negligible marginal cost.
Search advertising performs well for high-intent categories such as
Electronics. Social media drives reach and new customer acquisition but
typically returns lower immediate ROI. Display is the weakest performer and is
used for brand presence rather than direct response.

Budget reallocation. When a campaign underperforms, budget should move to the
best-returning channel for the same category rather than being withdrawn
entirely, so category presence is maintained.

Attribution window. Conversions are attributed on a 14-day window. Campaigns
should not be judged before they have run for at least two full weeks.

Win-back campaigns. Lapsed customer win-back sequences reliably outperform
prospecting on cost per conversion. A customer who has not ordered in 60 days
should enter the win-back sequence automatically.""",
    },
    {
        "title": "Supplier Terms Summary",
        "doc_type": "contract",
        "source": "Procurement",
        "content": """Supplier Terms Summary

BeautyCare Ltd. Supplies Personal Care lines. Standard lead time is 14 days.
Volume discount of 8% applies on orders above 500 units and 12% above 1000
units. Contract renews annually; the current term expires within the next
quarter and should be renegotiated with reference to volume growth.

TechSound Inc. Supplies Electronics. Lead time is 21 days, extending to 35 days
in the pre-holiday period. No volume discount below 250 units. Returns for
faulty stock are accepted within 30 days.

GreenBean Co. Supplies Groceries, principally coffee and tea. Lead time is 7
days. Pricing is indexed to commodity markets and is reviewed quarterly.

SportFlex. Supplies Apparel and Sports & Outdoors. Lead time is 28 days.
Minimum order quantity is 100 units per SKU. Seasonal ranges must be committed
one season ahead.

NutriMax. Supplies nutrition and grocery lines. Lead time is 10 days. Short
shelf-life products must be ordered against forecast rather than reorder point.

HomeGlow. Supplies Home & Living. Lead time is 21 days. Offers a 10% discount
on consolidated multi-SKU orders above 300 units.""",
    },
    {
        "title": "Competitor Intelligence Briefing",
        "doc_type": "competitor",
        "source": "Category Insights",
        "content": """Competitor Intelligence Briefing

BrandX. The principal competitor in Personal Care. Runs aggressive periodic
discounting, typically 20% off shampoo and conditioner lines timed to the start
of each quarter. Their promotions are short and deep rather than sustained.
Historically our share in Personal Care dips during their promotional windows
and recovers within six weeks without intervention.

ValueMart. Competes primarily on Groceries with an everyday-low-price
positioning. Difficult to beat on headline price; we compete on range and
organic credentials rather than price.

TechDirect. Online-only Electronics competitor with a narrow range and fast
delivery. Strong on headline devices, weak on accessories, which is where our
attach rate advantage lies.

Market observations. Category-wide softness in Apparel has been observed across
the market this year and is not specific to our range. Electronics demand has
shifted towards mid-price devices. Personal Care remains the most
promotionally-driven category and the most sensitive to competitor activity.

Response guidance. Short competitor promotions rarely justify a matching price
cut. Sustained competitor price moves, held for more than eight weeks, do
warrant a structural price review.""",
    },
    {
        "title": "Customer Segmentation Guide",
        "doc_type": "playbook",
        "source": "Customer Insights",
        "content": """Customer Segmentation Guide

Segment definitions. VIP customers have lifetime spend above 4,000. Premium
customers fall between 1,800 and 4,000. All other active customers are
Regular. Segments are recalculated from actual transaction history rather than
being assigned manually.

Churn definition. A customer with no order in the last 60 days is flagged at
risk. A customer with no order in 120 days is treated as churned. Churn among
VIP customers is disproportionately damaging because of their spend
concentration.

Concentration risk. Where a single segment accounts for more than 60% of total
spend, the business carries concentration risk and should invest in broadening
the base.

Retention levers. The most effective retention levers in order of measured
impact are: personalised win-back offers, early access to new ranges, and free
delivery thresholds. Blanket discounting is the least effective and erodes
margin among customers who would have purchased anyway.

Attach rate. Personal Care shows the strongest attach behaviour: customers
buying shampoo frequently add conditioner within the same basket. This makes
bundling particularly effective in that category.""",
    },
    {
        "title": "Store Operations Notes",
        "doc_type": "note",
        "source": "Retail Operations",
        "content": """Store Operations Notes

Store profiles. Downtown is the flagship, highest footfall and broadest range.
Mall Plaza performs well at weekends and during promotional periods. Airport
carries a reduced range weighted to travel-friendly formats and achieves higher
margin per unit. Suburban serves a family demographic with strong grocery and
home performance. Online serves the whole market and grows fastest but carries
fulfilment cost.

Transfer policy. Stock may be transferred between stores where one location
holds overstock and another is below reorder level. Transfers are preferred
over markdown for products with demonstrated demand elsewhere in the chain.

Regional variation. The Central and East regions index highest on Electronics.
North indexes on Groceries and Home & Living. Global, which is the online
channel, indexes on Apparel.

Seasonality. Trading builds through the final quarter of the year. Weekend
trading runs roughly 35% above weekday levels across physical stores.""",
    },
]
