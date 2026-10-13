from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import User, PracticeSession, PracticeResponse, ExerciseCategory
from schemas import DashboardSummaryResponse
from services.analytics_service import get_dashboard_summary
from dependencies import get_current_user

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns dynamic dashboard summary metrics for the authenticated user."""
    return get_dashboard_summary(
        user_id=current_user.id,
        user_name=current_user.name,
        db=db
    )


@router.get("/recent-activity")
def dashboard_recent_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns recent practice activity for authenticated user."""
    sessions = (
        db.query(PracticeSession)
        .filter(
            PracticeSession.user_id == current_user.id,
            PracticeSession.completion_status == "completed"
        )
        .order_by(PracticeSession.created_at.desc())
        .limit(5)
        .all()
    )

    activities = []
    for s in sessions:
        # Compute session average accuracy
        avg_score = (
            db.query(func.avg(PracticeResponse.similarity_score))
            .filter(PracticeResponse.session_id == s.id)
            .scalar()
        )
        cat_name = "General Practice"
        if s.category_id:
            cat = db.query(ExerciseCategory).filter(ExerciseCategory.id == s.category_id).first()
            if cat:
                cat_name = cat.name

        activities.append({
            "session_id": s.id,
            "category": cat_name,
            "exercise_count": s.exercise_count,
            "duration_seconds": s.duration_seconds,
            "duration_formatted": f"{max(1, s.duration_seconds // 60)} min" if s.duration_seconds >= 60 else f"{s.duration_seconds} sec",
            "average_score": round(float(avg_score or 0.0), 1),
            "date": s.created_at.strftime("%b %d, %Y - %H:%M") if s.created_at else "Recent"
        })

    return {"status": "success", "data": activities}
