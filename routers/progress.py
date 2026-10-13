import io
import csv
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import (
    User, PracticeSession, PracticeResponse, Exercise, ExerciseCategory, LegacyProgress
)
from schemas import ProgressSummaryResponse
from services.analytics_service import get_progress_summary
from dependencies import get_current_user

router = APIRouter()


@router.get("/summary", response_model=ProgressSummaryResponse)
def progress_summary(
    language: Optional[str] = Query(None, description="Optional language code filter: en, ta, en-US, ta-IN"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns comprehensive progress metrics, weekly activity, and score trends, optionally filtered by language."""
    return get_progress_summary(user_id=current_user.id, db=db, language=language)


@router.get("/history")
def progress_history(
    language: Optional[str] = Query(None, description="Optional language code filter: en, ta, en-US, ta-IN"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns chronological session and response history for authenticated user, optionally filtered by language."""
    query = db.query(PracticeSession).filter(PracticeSession.user_id == current_user.id)
    if language:
        query = query.filter(PracticeSession.language.ilike(f"{language}%"))

    sessions = (
        query
        .order_by(PracticeSession.created_at.desc())
        .limit(50)
        .all()
    )

    history = []
    for s in sessions:
        responses = (
            db.query(PracticeResponse)
            .filter(PracticeResponse.session_id == s.id)
            .order_by(PracticeResponse.created_at.asc())
            .all()
        )
        avg_score = (
            sum(r.similarity_score for r in responses) / len(responses)
            if responses else 0.0
        )
        history.append({
            "session_id": s.id,
            "language": s.language or "en-US",
            "date": s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else None,
            "duration_seconds": s.duration_seconds,
            "exercise_count": s.exercise_count,
            "average_score": round(avg_score, 1),
            "status": s.completion_status,
            "responses": [
                {
                    "target_text": r.target_text,
                    "english_meaning": r.exercise.english_meaning if r.exercise and r.exercise.english_meaning else None,
                    "exercise_type": r.exercise.exercise_type if r.exercise and r.exercise.exercise_type else "word",
                    "recognized_text": r.recognized_text,
                    "similarity_score": r.similarity_score,
                    "attempt_number": r.attempt_number,
                    "language": r.language or s.language or "en-US"
                }
                for r in responses
            ]
        })

    return {"status": "success", "data": history}


@router.get("/category-breakdown")
def progress_category_breakdown(
    language: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns performance breakdown by exercise category."""
    summary = get_progress_summary(user_id=current_user.id, db=db, language=language)
    return {"status": "success", "data": summary.category_breakdown}


@router.get("/export")
def export_progress_csv(
    language: Optional[str] = Query(None, description="Optional language filter for CSV export"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Exports authenticated user's practice history as a UTF-8 with BOM CSV file preserving Tamil Unicode."""
    query = (
        db.query(PracticeResponse, PracticeSession, Exercise)
        .join(PracticeSession, PracticeResponse.session_id == PracticeSession.id)
        .outerjoin(Exercise, PracticeResponse.exercise_id == Exercise.id)
        .filter(PracticeSession.user_id == current_user.id)
    )

    if language:
        query = query.filter(PracticeResponse.language.ilike(f"{language}%"))

    responses = query.order_by(PracticeResponse.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date",
        "Session ID",
        "Language",
        "Activity Type",
        "Target Text",
        "English Meaning",
        "Recognized Text",
        "Similarity Score (%)",
        "Attempt Number"
    ])

    for resp, sess, ex in responses:
        eng_meaning = ex.english_meaning if ex and ex.english_meaning else ""
        act_type = ex.exercise_type.capitalize() if ex and ex.exercise_type else "Word"
        writer.writerow([
            resp.created_at.strftime("%Y-%m-%d %H:%M:%S") if resp.created_at else "",
            sess.id,
            resp.language or sess.language or "en-US",
            act_type,
            resp.target_text,
            eng_meaning,
            resp.recognized_text,
            resp.similarity_score,
            resp.attempt_number
        ])

    csv_data = output.getvalue()
    # Encode with utf-8-sig so Excel and all spreadsheet software render Tamil script properly
    encoded_bytes = csv_data.encode("utf-8-sig")
    lang_suffix = f"_{language}" if language else ""
    filename = f"neurovoice_progress_{current_user.id}{lang_suffix}_{datetime.now().strftime('%Y%m%d')}.csv"

    return Response(
        content=encoded_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==========================================
# LEGACY ROUTES (PRESERVED FOR COMPATIBILITY)
# ==========================================

@router.post("/save")
def legacy_save_progress(data: dict, db: Session = Depends(get_db)):
    """Legacy endpoint supporting existing frontend components."""
    user_id = data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")

    practice_type = data.get("practice_type", "word")
    accuracy = int(data.get("accuracy", 0))
    is_correct = 1 if accuracy >= 70 else 0

    prog = db.query(LegacyProgress).filter(LegacyProgress.user_id == user_id).first()
    if not prog:
        prog = LegacyProgress(
            user_id=user_id,
            words=1 if practice_type == "word" else 0,
            images=1 if practice_type == "image" else 0,
            phrases=1 if practice_type == "phrase" else 0,
            correct=is_correct,
            attempts=1
        )
        db.add(prog)
    else:
        prog.attempts += 1
        prog.correct += is_correct
        if practice_type == "word":
            prog.words += 1
        elif practice_type == "image":
            prog.images += 1
        elif practice_type == "phrase":
            prog.phrases += 1

    db.commit()
    return {"status": "success", "message": "Progress saved successfully"}


@router.get("/{user_id}")
def legacy_get_progress(user_id: int, db: Session = Depends(get_db)):
    """Legacy endpoint returning progress dictionary."""
    prog = db.query(LegacyProgress).filter(LegacyProgress.user_id == user_id).first()
    if not prog:
        return {
            "status": "success",
            "data": {"words": 0, "images": 0, "phrases": 0, "correct": 0, "attempts": 0}
        }
    return {
        "status": "success",
        "data": {
            "words": prog.words,
            "images": prog.images,
            "phrases": prog.phrases,
            "correct": prog.correct,
            "attempts": prog.attempts
        }
    }


@router.get("/coach/{user_id}")
def legacy_coaching_tip(user_id: int, db: Session = Depends(get_db)):
    """Legacy coaching tip endpoint."""
    prog = db.query(LegacyProgress).filter(LegacyProgress.user_id == user_id).first()
    if not prog or prog.attempts == 0:
        return {"tip": "Start practicing daily for steady progress and speech clarity."}

    accuracy = (prog.correct / prog.attempts) * 100
    if accuracy >= 90:
        tip = "Excellent articulation! Keep maintaining your consistent daily practice."
    elif accuracy >= 70:
        tip = "Good steady progress! Focus on speaking slowly and breathing gently between phrases."
    else:
        tip = "Every attempt builds strength. Try listening to the audio model twice before repeating."

    return {"accuracy": round(accuracy, 2), "tip": tip}
