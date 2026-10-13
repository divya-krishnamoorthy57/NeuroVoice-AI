from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User, PracticePlan, PracticePlanItem, Exercise
from schemas import PracticePlanSchema, GeneratePlanRequest, ExerciseSchema
from services.recommendation_service import generate_user_practice_plan
from dependencies import get_current_user

router = APIRouter()


@router.get("/active", response_model=PracticePlanSchema)
def get_active_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves current active personalized practice plan or creates an initial one."""
    plan = (
        db.query(PracticePlan)
        .filter(PracticePlan.user_id == current_user.id, PracticePlan.is_active == True)
        .order_by(PracticePlan.created_at.desc())
        .first()
    )

    if not plan:
        plan = generate_user_practice_plan(
            user_id=current_user.id,
            db=db,
            target_minutes=15,
            difficulty="beginner"
        )

    return plan


@router.post("/generate", response_model=PracticePlanSchema)
def generate_new_plan(
    req: GeneratePlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generates a new adaptive practice plan based on user preferences and history."""
    plan = generate_user_practice_plan(
        user_id=current_user.id,
        db=db,
        target_minutes=req.daily_target_minutes or 15,
        difficulty=req.difficulty_preference or "beginner"
    )
    return plan


@router.post("/items/{item_id}/complete")
def complete_plan_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marks a specific exercise in the plan as completed."""
    item = (
        db.query(PracticePlanItem)
        .join(PracticePlan, PracticePlanItem.plan_id == PracticePlan.id)
        .filter(PracticePlanItem.id == item_id, PracticePlan.user_id == current_user.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Plan item not found")

    item.completed = True
    item.completed_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "success", "message": "Plan item marked as completed"}
