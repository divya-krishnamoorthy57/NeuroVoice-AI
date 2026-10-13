from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User, UserProfile
from schemas import UserProfileSchema, UserProfileUpdate
from dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=UserProfileSchema)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves authenticated user's profile."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return UserProfileSchema(
        id=profile.id,
        user_id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        age_range=profile.age_range,
        preferred_language=profile.preferred_language,
        practice_preferences=profile.practice_preferences,
        daily_practice_goal=profile.daily_practice_goal,
        font_size_preference=profile.font_size_preference,
        high_contrast=profile.high_contrast,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    )


@router.put("/", response_model=UserProfileSchema)
def update_profile(
    profile_in: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates authenticated user's profile and basic info."""
    if profile_in.name is not None and profile_in.name.strip():
        current_user.name = profile_in.name.strip()

    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    if profile_in.age_range is not None:
        profile.age_range = profile_in.age_range
    if profile_in.preferred_language is not None:
        profile.preferred_language = profile_in.preferred_language
    if profile_in.practice_preferences is not None:
        profile.practice_preferences = profile_in.practice_preferences
    if profile_in.daily_practice_goal is not None:
        profile.daily_practice_goal = max(1, min(120, profile_in.daily_practice_goal))
    if profile_in.font_size_preference is not None:
        profile.font_size_preference = profile_in.font_size_preference
    if profile_in.high_contrast is not None:
        profile.high_contrast = profile_in.high_contrast

    db.commit()
    db.refresh(current_user)
    db.refresh(profile)

    return UserProfileSchema(
        id=profile.id,
        user_id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        age_range=profile.age_range,
        preferred_language=profile.preferred_language,
        practice_preferences=profile.practice_preferences,
        daily_practice_goal=profile.daily_practice_goal,
        font_size_preference=profile.font_size_preference,
        high_contrast=profile.high_contrast,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    )
