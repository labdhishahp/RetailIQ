from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_manager
from app.models import Alert, Decision, Recommendation, Report, Simulation, User
from app.schemas.insight import (
    AlertRead, DecisionCreate, DecisionRead, RecommendationAction, RecommendationRead,
    ReportCreate, ReportDetail, ReportRead, SimulationRead, SimulationRequest,
)
from app.services.alert_service import alert_service
from app.services.recommendation_service import recommendation_service
from app.services.report_service import report_service
from app.services.simulation_service import simulation_service

router = APIRouter(tags=["intelligence"])


# ---- recommendations -----------------------------------------------------

@router.get("/recommendations", response_model=list[RecommendationRead])
def list_recommendations(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), _: User = Depends(get_current_user),
):
    q = select(Recommendation).order_by(
        Recommendation.revenue_impact.desc(), Recommendation.created_at.desc()).limit(limit)
    if status_filter:
        q = q.where(Recommendation.status == status_filter)
    return db.scalars(q).all()


@router.post("/recommendations/generate", response_model=list[RecommendationRead])
def generate_recommendations(db: Session = Depends(get_db), _: User = Depends(require_manager)):
    recommendation_service.generate(db)
    return db.scalars(
        select(Recommendation).where(Recommendation.status == "pending")
        .order_by(Recommendation.revenue_impact.desc()).limit(50)).all()


@router.post("/recommendations/{rec_id}/action", response_model=RecommendationRead)
def act_on_recommendation(rec_id: int, payload: RecommendationAction,
                          db: Session = Depends(get_db), user: User = Depends(require_manager)):
    rec = recommendation_service.resolve(db, rec_id, status=payload.status, user_id=user.id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    # Accepting a recommendation records a decision so the outcome is tracked.
    count = db.scalar(select(func.count()).select_from(Decision)) or 0
    db.add(Decision(
        code=f"DEC-{count + 1:04d}", question=rec.title,
        recommendation_text=rec.rationale,
        status="accepted" if payload.status == "accepted" else "rejected",
        impact=rec.impact, confidence=rec.confidence,
        outcome=payload.note, recommendation_id=rec.id, created_by_id=user.id,
    ))
    db.commit()
    db.refresh(rec)
    return rec


# ---- decisions -----------------------------------------------------------

@router.get("/decisions", response_model=list[DecisionRead])
def list_decisions(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db),
                   _: User = Depends(get_current_user)):
    return db.scalars(
        select(Decision).order_by(Decision.created_at.desc()).limit(limit)).all()


@router.post("/decisions", response_model=DecisionRead, status_code=status.HTTP_201_CREATED)
def create_decision(payload: DecisionCreate, db: Session = Depends(get_db),
                    user: User = Depends(require_manager)):
    count = db.scalar(select(func.count()).select_from(Decision)) or 0
    decision = Decision(code=f"DEC-{count + 1:04d}", created_by_id=user.id,
                        **payload.model_dump())
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


# ---- simulations ---------------------------------------------------------

@router.post("/simulations/run")
def run_simulation(payload: SimulationRequest, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    try:
        return simulation_service.run(
            db, name=payload.name, discount_pct=payload.discount_pct,
            duration_days=payload.duration_days, product_skus=payload.product_skus,
            category=payload.category, extra_spend=payload.extra_spend, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/simulations", response_model=list[SimulationRead])
def list_simulations(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db),
                     _: User = Depends(get_current_user)):
    return db.scalars(
        select(Simulation).order_by(Simulation.created_at.desc()).limit(limit)).all()


# ---- alerts --------------------------------------------------------------

@router.get("/alerts", response_model=list[AlertRead])
def list_alerts(unread_only: bool = False, limit: int = Query(40, ge=1, le=200),
                db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return alert_service.list_alerts(db, limit=limit, unread_only=unread_only)


@router.post("/alerts/evaluate", response_model=list[AlertRead])
def evaluate_alerts(db: Session = Depends(get_db), _: User = Depends(require_manager)):
    alert_service.evaluate(db)
    return alert_service.list_alerts(db, limit=40)


@router.post("/alerts/{alert_id}/read", response_model=AlertRead)
def mark_alert_read(alert_id: int, db: Session = Depends(get_db),
                    _: User = Depends(get_current_user)):
    alert = alert_service.mark_read(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/alerts/read-all")
def mark_all_alerts_read(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return {"updated": alert_service.mark_all_read(db)}


# ---- reports -------------------------------------------------------------

@router.get("/reports", response_model=list[ReportRead])
def list_reports(limit: int = Query(30, ge=1, le=100), db: Session = Depends(get_db),
                 _: User = Depends(get_current_user)):
    return db.scalars(select(Report).order_by(Report.created_at.desc()).limit(limit)).all()


@router.post("/reports/generate", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
def generate_report(payload: ReportCreate, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    return report_service.generate(db, kind=payload.kind, user_id=user.id)


@router.get("/reports/{report_id}", response_model=ReportDetail)
def get_report(report_id: int, db: Session = Depends(get_db),
               _: User = Depends(get_current_user)):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/reports/{report_id}/download")
def download_report(report_id: int, fmt: str = Query("csv", pattern="^(csv|json)$"),
                    db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status != "ready":
        raise HTTPException(status_code=409, detail="Report is not ready")
    if fmt == "json":
        return Response(
            content=__import__("json").dumps(
                {"title": report.title, "summary": report.summary, "payload": report.payload},
                default=str, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{report.code}.json"'})
    return Response(
        content=report_service.to_csv(report), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{report.code}.csv"'})
