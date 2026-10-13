from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User, UserPracticePreference
from schemas import UserPreferenceSchema, UserPreferenceUpdate
from dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=UserPreferenceSchema)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves practice preferences for authenticated user."""
    pref = db.query(UserPracticePreference).filter(UserPracticePreference.user_id == current_user.id).first()
    if not pref:
        pref = UserPracticePreference(
            user_id=current_user.id,
            daily_goal_minutes=15,
            preferred_categories="word-practice,phrase-practice",
            preferred_duration=10,
            preferred_language="en-US",
            speech_rate=0.9
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)

    return UserPreferenceSchema.model_validate(pref)


@router.put("/", response_model=UserPreferenceSchema)
def update_preferences(
    pref_in: UserPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates practice preferences for authenticated user."""
    pref = db.query(UserPracticePreference).filter(UserPracticePreference.user_id == current_user.id).first()
    if not pref:
        pref = UserPracticePreference(user_id=current_user.id)
        db.add(pref)

    if pref_in.daily_goal_minutes is not None:
        pref.daily_goal_minutes = max(5, min(120, pref_in.daily_goal_minutes))
    if pref_in.preferred_categories is not None:
        pref.preferred_categories = pref_in.preferred_categories
    if pref_in.preferred_duration is not None:
        pref.preferred_duration = max(5, min(60, pref_in.preferred_duration))
    if pref_in.preferred_language is not None:
        pref.preferred_language = pref_in.preferred_language
    if pref_in.speech_rate is not None:
        pref.speech_rate = max(0.5, min(1.5, pref_in.speech_rate))

    db.commit()
    db.refresh(pref)
    return UserPreferenceSchema.model_validate(pref)
