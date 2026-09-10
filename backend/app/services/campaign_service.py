from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.schemas.campaign import CampaignRead


class CampaignService:
    """Read operations for marketing campaigns."""

    def list_campaigns(self, db: Session, *, skip: int = 0, limit: int = 100) -> list[CampaignRead]:
        rows = db.scalars(
            select(Campaign).order_by(Campaign.start_date.desc().nullslast())
            .offset(skip).limit(limit)
        ).all()
        return [CampaignRead.model_validate(r) for r in rows]

    def get_campaign(self, db: Session, campaign_id: int) -> CampaignRead | None:
        row = db.get(Campaign, campaign_id)
        return CampaignRead.model_validate(row) if row else None


campaign_service = CampaignService()
