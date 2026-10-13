from typing import List
from sqlalchemy.orm import Session
from models import (
    Exercise, ExerciseCategory, PracticeResponse, PracticeSession,
    PracticePlan, PracticePlanItem, UserPracticePreference
)


def generate_user_practice_plan(user_id: int, db: Session, target_minutes: int = 15, difficulty: str = "beginner") -> PracticePlan:
    """
    Generates a structured practice plan from available exercises using transparent rules:
    1. Selects exercises matching user preferred categories.
    2. Prioritizes exercises not practiced recently.
    3. Blends beginner and intermediate items based on average matching scores.
    """
    # Deactivate existing active plans for this user
    db.query(PracticePlan).filter(
        PracticePlan.user_id == user_id,
        PracticePlan.is_active == True
    ).update({"is_active": False})

    # Check user preferences
    pref = db.query(UserPracticePreference).filter(UserPracticePreference.user_id == user_id).first()
    category_slugs = []
    if pref and pref.preferred_categories:
        category_slugs = [c.strip() for c in pref.preferred_categories.split(",") if c.strip()]

    # Find recently practiced exercise IDs
    recent_responses = (
        db.query(PracticeResponse.exercise_id)
        .join(PracticeSession, PracticeResponse.session_id == PracticeSession.id)
        .filter(PracticeSession.user_id == user_id)
        .order_by(PracticeResponse.created_at.desc())
        .limit(10)
        .all()
    )
    recent_ids = {r[0] for r in recent_responses if r[0] is not None}

    # Query exercises
    query = db.query(Exercise).filter(Exercise.is_active == True)
    if category_slugs:
        query = query.join(ExerciseCategory, Exercise.category_id == ExerciseCategory.id).filter(
            ExerciseCategory.slug.in_(category_slugs)
        )

    # Prefer non-recent exercises
    candidates = query.all()
    if not candidates:
        candidates = db.query(Exercise).filter(Exercise.is_active == True).all()

    # Sort candidates prioritizing those not recently practiced
    sorted_candidates = sorted(
        candidates,
        key=lambda e: (e.id in recent_ids, e.difficulty != difficulty, e.display_order)
    )

    # Pick 5 recommended exercises for a 15-minute plan (approx. 3 min per exercise)
    plan_exercise_count = max(3, min(8, target_minutes // 3))
    selected_exercises = sorted_candidates[:plan_exercise_count]

    plan = PracticePlan(
        user_id=user_id,
        daily_target_minutes=target_minutes,
        target_exercises_per_day=len(selected_exercises),
        plan_notes="Curated practice suggestions based on non-recent exercises and your practice preferences.",
        is_active=True
    )
    db.add(plan)
    db.flush()

    for idx, ex in enumerate(selected_exercises):
        item = PracticePlanItem(
            plan_id=plan.id,
            exercise_id=ex.id,
            order_index=idx + 1,
            completed=False
        )
        db.add(item)

    db.commit()
    db.refresh(plan)
    return plan
