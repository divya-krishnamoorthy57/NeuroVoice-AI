from datetime import datetime, timedelta, date
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import (
    PracticeSession, PracticeResponse, Exercise, ExerciseCategory,
    UserProfile, UserPracticePreference
)
from schemas import (
    DashboardSummaryResponse, ProgressSummaryResponse,
    CategoryProgressItem, RecommendedExercise
)


def calculate_user_streak(user_id: int, db: Session) -> int:
    """
    Calculates consecutive active practice days based on completed session timestamps.
    """
    sessions = (
        db.query(func.date(PracticeSession.created_at))
        .filter(
            PracticeSession.user_id == user_id,
            PracticeSession.completion_status == "completed"
        )
        .distinct()
        .order_by(func.date(PracticeSession.created_at).desc())
        .all()
    )

    if not sessions:
        return 0

    active_dates = []
    for s in sessions:
        if s[0] is not None:
            val = s[0]
            if isinstance(val, str):
                try:
                    active_dates.append(datetime.strptime(val[:10], "%Y-%m-%d").date())
                except Exception:
                    pass
            elif isinstance(val, datetime):
                active_dates.append(val.date())
            elif isinstance(val, date):
                active_dates.append(val)

    if not active_dates:
        return 0

    # Ensure uniqueness and sorted descending
    active_dates = sorted(list(set(active_dates)), reverse=True)

    today = date.today()
    yesterday = today - timedelta(days=1)

    latest_date = active_dates[0]
    # If user hasn't practiced today or yesterday, streak is broken
    if latest_date != today and latest_date != yesterday:
        return 0

    streak = 0
    current_check = latest_date

    for act_date in active_dates:
        if act_date == current_check:
            streak += 1
            current_check -= timedelta(days=1)
        else:
            break

    return streak


def get_dashboard_summary(user_id: int, user_name: str, db: Session) -> DashboardSummaryResponse:
    """
    Retrieves dynamic dashboard analytics computed from real database records.
    """
    # 1. Fetch user profile / preferences for daily goal
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    pref = db.query(UserPracticePreference).filter(UserPracticePreference.user_id == user_id).first()

    daily_goal_minutes = 15
    if pref and pref.daily_goal_minutes:
        daily_goal_minutes = pref.daily_goal_minutes
    elif profile and profile.daily_practice_goal:
        daily_goal_minutes = profile.daily_practice_goal

    # 2. Today's sessions & exercises
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_sessions = (
        db.query(PracticeSession)
        .filter(
            PracticeSession.user_id == user_id,
            PracticeSession.created_at >= today_start
        )
        .all()
    )

    today_practice_seconds = sum(s.duration_seconds for s in today_sessions)
    today_practice_minutes = round(today_practice_seconds / 60)
    today_completed_exercises = sum(s.exercise_count for s in today_sessions)

    daily_goal_percentage = min(
        100,
        int((today_practice_minutes / daily_goal_minutes) * 100) if daily_goal_minutes > 0 else 0
    )

    # 3. Overall totals
    all_sessions = (
        db.query(PracticeSession)
        .filter(PracticeSession.user_id == user_id)
        .all()
    )
    total_sessions_completed = len([s for s in all_sessions if s.completion_status == "completed"])
    total_completed_exercises = sum(s.exercise_count for s in all_sessions)

    # 4. Average accuracy from practice_responses
    avg_score = (
        db.query(func.avg(PracticeResponse.similarity_score))
        .join(PracticeSession, PracticeResponse.session_id == PracticeSession.id)
        .filter(PracticeSession.user_id == user_id)
        .scalar()
    )
    average_accuracy = round(float(avg_score or 0.0), 1)

    # 5. Learning streak
    streak_days = calculate_user_streak(user_id, db)

    # 6. Recommended next exercise
    # Find an exercise the user has NOT practiced recently
    practiced_exercise_ids = (
        db.query(PracticeResponse.exercise_id)
        .join(PracticeSession, PracticeResponse.session_id == PracticeSession.id)
        .filter(PracticeSession.user_id == user_id)
        .order_by(PracticeResponse.created_at.desc())
        .limit(20)
        .all()
    )
    recent_ids = {p[0] for p in practiced_exercise_ids if p[0] is not None}

    next_exercise = (
        db.query(Exercise)
        .filter(Exercise.is_active == True, ~Exercise.id.in_(recent_ids) if recent_ids else True)
        .order_by(Exercise.display_order.asc())
        .first()
    )

    if not next_exercise:
        next_exercise = db.query(Exercise).filter(Exercise.is_active == True).first()

    rec_schema = None
    if next_exercise:
        rec_schema = RecommendedExercise(
            id=next_exercise.id,
            title=next_exercise.title,
            target_text=next_exercise.target_text,
            exercise_type=next_exercise.exercise_type,
            difficulty=next_exercise.difficulty,
            prompt=next_exercise.prompt
        )

    return DashboardSummaryResponse(
        user_name=user_name,
        daily_goal_minutes=daily_goal_minutes,
        today_practice_minutes=today_practice_minutes,
        today_completed_exercises=today_completed_exercises,
        daily_goal_percentage=daily_goal_percentage,
        total_completed_exercises=total_completed_exercises,
        total_sessions_completed=total_sessions_completed,
        current_streak_days=streak_days,
        average_accuracy=average_accuracy,
        recommended_exercise=rec_schema
    )


def get_progress_summary(user_id: int, db: Session, language: Optional[str] = None) -> ProgressSummaryResponse:
    """
    Computes progress metrics, weekly activity chart data, category breakdown,
    and score trends for dedicated Progress screen, optionally filtered by language.
    """
    session_query = db.query(PracticeSession).filter(PracticeSession.user_id == user_id)
    if language:
        session_query = session_query.filter(PracticeSession.language.ilike(f"{language}%"))
    sessions = session_query.order_by(PracticeSession.created_at.asc()).all()

    total_sessions = len([s for s in sessions if s.completion_status == "completed"])
    total_exercises = sum(s.exercise_count for s in sessions)
    total_seconds = sum(s.duration_seconds for s in sessions)
    total_practice_time_minutes = round(total_seconds / 60)

    # Average score
    score_query = (
        db.query(func.avg(PracticeResponse.similarity_score))
        .join(PracticeSession, PracticeResponse.session_id == PracticeSession.id)
        .filter(PracticeSession.user_id == user_id)
    )
    if language:
        score_query = score_query.filter(PracticeResponse.language.ilike(f"{language}%"))
    avg_score = score_query.scalar()
    average_similarity_score = round(float(avg_score or 0.0), 1)

    # Streak
    current_streak = calculate_user_streak(user_id, db)

    # Category breakdown
    categories = db.query(ExerciseCategory).filter(ExerciseCategory.is_active == True).all()
    category_breakdown: List[CategoryProgressItem] = []

    for cat in categories:
        cat_query = (
            db.query(
                func.count(PracticeResponse.id),
                func.avg(PracticeResponse.similarity_score)
            )
            .join(Exercise, PracticeResponse.exercise_id == Exercise.id)
            .join(PracticeSession, PracticeResponse.session_id == PracticeSession.id)
            .filter(
                PracticeSession.user_id == user_id,
                Exercise.category_id == cat.id
            )
        )
        if language:
            cat_query = cat_query.filter(PracticeResponse.language.ilike(f"{language}%"))
        cat_stats = cat_query.first()
        attempts = cat_stats[0] if cat_stats and cat_stats[0] else 0
        avg_cat_score = round(float(cat_stats[1] or 0.0), 1) if cat_stats and cat_stats[1] else 0.0

        category_breakdown.append(
            CategoryProgressItem(
                category_name=cat.name,
                slug=cat.slug,
                attempts=attempts,
                average_score=avg_cat_score
            )
        )

    # Weekly activity (last 7 days)
    today = date.today()
    weekly_activity = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())

        day_sessions = []
        for s in sessions:
            if s.created_at:
                c_date = s.created_at.date() if hasattr(s.created_at, "date") else datetime.fromisoformat(str(s.created_at)[:19]).date()
                if c_date == day:
                    day_sessions.append(s)
        mins = round(sum(s.duration_seconds for s in day_sessions) / 60)
        exs = sum(s.exercise_count for s in day_sessions)

        weekly_activity.append({
            "date": day.strftime("%a %d"),
            "minutes": mins,
            "exercises": exs
        })

    # Chronological score trends (last 10 completed sessions)
    score_trends = []
    completed_sessions = [s for s in sessions if s.completion_status == "completed"][-10:]
    for s in completed_sessions:
        s_score = (
            db.query(func.avg(PracticeResponse.similarity_score))
            .filter(PracticeResponse.session_id == s.id)
            .scalar()
        )
        score_trends.append({
            "session_id": s.id,
            "date": s.created_at.strftime("%b %d, %H:%M") if s.created_at else f"Session #{s.id}",
            "score": round(float(s_score or 0.0), 1)
        })

    return ProgressSummaryResponse(
        total_sessions=total_sessions,
        total_exercises=total_exercises,
        total_practice_time_minutes=total_practice_time_minutes,
        average_similarity_score=average_similarity_score,
        current_streak=current_streak,
        category_breakdown=category_breakdown,
        weekly_activity=weekly_activity,
        score_trends=score_trends
    )
