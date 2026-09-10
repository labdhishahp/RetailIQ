"""Response shapes for aggregate/analytics endpoints.

These deliberately mirror the shapes the existing frontend components already
consume, so the UI does not need restructuring. All money values are plain
floats (JSON numbers), never Decimal strings.
"""

from pydantic import BaseModel


class KpiMetric(BaseModel):
    value: float
    change: float
    trend: str  # 'up' | 'down'


class KpiSummary(BaseModel):
    revenue: KpiMetric
    orders: KpiMetric
    profit: KpiMetric
    healthScore: KpiMetric


class RevenuePoint(BaseModel):
    month: str
    revenue: float
    profit: float
    orders: int


class MonthlySalesPoint(BaseModel):
    month: str
    sales: int


class InventoryTrendPoint(BaseModel):
    week: str
    stock: int
    turnover: float


class StoreComparisonRow(BaseModel):
    store: str
    revenue: float
    orders: int
    growth: float


class CategorySalesRow(BaseModel):
    category: str
    value: float  # percentage share
    revenue: float


class TopProductRow(BaseModel):
    id: int
    name: str
    category: str
    sales: int
    revenue: float
    growth: float
    stock: int


class ProductOverviewRow(BaseModel):
    """Product enriched with cross-store stock and computed margin."""

    id: str  # SKU — the human-facing identifier the UI displays and searches
    name: str
    category: str
    supplier: str | None
    price: float
    cost: float
    stock: int
    status: str
    margin: float


class InventorySummary(BaseModel):
    totalSKUs: int
    totalValue: float
    turnoverRate: float
    fillRate: float


class LowStockRow(BaseModel):
    id: str
    name: str
    current: int
    reorder: int
    daysLeft: int
    product_id: int | None = None
    store_id: int | None = None
    store: str | None = None


class DeadStockRow(BaseModel):
    id: str
    name: str
    daysIdle: int
    value: float
    units: int


class OverstockRow(BaseModel):
    id: str
    name: str
    current: int
    optimal: int
    excess: int


class ReorderRow(BaseModel):
    id: str
    name: str
    qty: int
    cost: float
    urgency: str
    product_id: int | None = None
    store_id: int | None = None
    store: str | None = None


class WarehouseRow(BaseModel):
    name: str
    capacity: float
    skus: int
    value: float


class HeatmapRow(BaseModel):
    category: str
    w1: int
    w2: int
    w3: int
    w4: int
    w5: int
    w6: int
    w7: int
    w8: int


class InventoryOverview(BaseModel):
    summary: InventorySummary
    lowStock: list[LowStockRow]
    deadStock: list[DeadStockRow]
    overstock: list[OverstockRow]
    reorderSuggestions: list[ReorderRow]
    warehouses: list[WarehouseRow]
    heatmap: list[HeatmapRow]


class SalesPeriodPoint(BaseModel):
    label: str
    revenue: float
    profit: float
    orders: int
    growth: float


class CampaignPerformanceRow(BaseModel):
    channel: str
    spend: float
    revenue: float
    roi: float
