# RetailIQ

**Agentic Retail Decision Intelligence Platform**

AI-powered decision intelligence for retail businesses. Ask questions in natural language — RetailIQ automatically investigates sales, inventory, pricing, campaigns, and customers to generate business recommendations.

## Tech Stack

- React 19 + Vite
- Tailwind CSS 4
- React Router 7
- Framer Motion
- Lucide React
- Recharts
- Context API

## Getting Started

```bash
cd retailiq
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

## Pages

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/` | Executive KPIs, charts, alerts |
| Products | `/products` | Product catalog with filters |
| Inventory | `/inventory` | Stock health, heatmap, reorders |
| Customers | `/customers` | Customer segments and activity |
| Sales Analytics | `/analytics` | Revenue, profit, growth charts |
| Campaign Analytics | `/campaigns` | Marketing ROI and performance |
| AI Copilot | `/copilot` | Natural language business intelligence |
| Reports | `/reports` | Executive reports with AI summaries |
| Decision History | `/history` | Timeline of AI recommendations |
| Settings | `/settings` | Platform preferences |
| Profile | `/profile` | User profile and activity |

## AI Copilot Demo

Try asking: **"Why are shampoo sales decreasing?"**

RetailIQ deploys 7 specialized AI agents (Planner → Sales → Inventory → Pricing → Campaign → Customer → Recommendation Engine) and produces a structured recommendation with evidence, confidence score, and next steps.

## Build

```bash
npm run build
npm run preview
```
