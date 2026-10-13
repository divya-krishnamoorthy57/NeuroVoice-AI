from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session
from database import get_db
from models import (
    PracticeSession, PracticeResponse, Exercise, User, LegacyProgress
)
from schemas import (
    SpeechFeedbackRequest, SpeechFeedbackResponse,
    PracticeSessionStart, PracticeSessionResponse,
    PracticeResponseCreate, PracticeResponseDetail,
    PracticeSessionComplete, TTSRequest
)
from services.speech_feedback import evaluate_speech_similarity
from services.tts_service import synthesize_speech, get_tts_status
from dependencies import get_current_user

router = APIRouter()


@router.post("/feedback", response_model=SpeechFeedbackResponse)
def evaluate_feedback(req: SpeechFeedbackRequest):
    """
    Evaluates speech recognition output against target text using RapidFuzz
    and word-by-word token comparison with Tamil/English support. Does not require active session.
    """
    return evaluate_speech_similarity(
        target_text=req.target_text,
        spoken_text=req.spoken_text,
        exercise_type=req.exercise_type or "word",
        language=req.language or "en-US"
    )


@router.post("/sessions", response_model=PracticeSessionResponse, status_code=status.HTTP_201_CREATED)
def start_practice_session(
    data: PracticeSessionStart,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Starts or resumes an active practice session for the authenticated user with language tracking."""
    # Check for recently created (within 15 minutes) empty in_progress session for this user and language
    # to avoid polluting history with duplicate empty sessions on page reload or navigation
    fifteen_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=15)
    recent_empty_session = (
        db.query(PracticeSession)
        .filter(
            PracticeSession.user_id == current_user.id,
            PracticeSession.completion_status == "in_progress",
            PracticeSession.language == (data.language or "en-US"),
            PracticeSession.exercise_count == 0,
            PracticeSession.created_at >= fifteen_mins_ago
        )
        .order_by(PracticeSession.created_at.desc())
        .first()
    )
    if recent_empty_session:
        return PracticeSessionResponse.model_validate(recent_empty_session)

    session = PracticeSession(
        user_id=current_user.id,
        category_id=data.category_id,
        language=data.language or "en-US",
        start_time=datetime.now(timezone.utc),
        completion_status="in_progress",
        exercise_count=0,
        duration_seconds=0
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return PracticeSessionResponse.model_validate(session)


@router.get("/sessions", response_model=List[PracticeSessionResponse])
def list_practice_sessions(
    language: Optional[str] = Query(None, description="Filter sessions by language code"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns past practice sessions for the authenticated user, optionally filtered by language."""
    query = db.query(PracticeSession).filter(PracticeSession.user_id == current_user.id)
    if language:
        query = query.filter(PracticeSession.language.ilike(f"{language}%"))
    sessions = (
        query
        .order_by(PracticeSession.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [PracticeSessionResponse.model_validate(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=PracticeSessionResponse)
def get_practice_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves session details and responses. Enforces user ownership."""
    session = db.query(PracticeSession).filter(PracticeSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found")

    if session.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied: Cannot view another user's session")

    return PracticeSessionResponse.model_validate(session)


@router.post("/sessions/{session_id}/responses", response_model=PracticeResponseDetail)
def record_practice_response(
    session_id: int,
    data: PracticeResponseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Records an individual exercise response in the practice session with language tag.
    Also keeps legacy progress in sync for backward compatibility.
    """
    session = db.query(PracticeSession).filter(PracticeSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found")

    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot record response to another user's session")

    response_lang = data.language or session.language or "en-US"

    response_record = PracticeResponse(
        session_id=session.id,
        exercise_id=data.exercise_id,
        language=response_lang,
        target_text=data.target_text,
        recognized_text=data.recognized_text,
        similarity_score=data.similarity_score,
        matched_words=data.matched_words,
        missing_words=data.missing_words,
        attempt_number=data.attempt_number
    )
    db.add(response_record)

    # Increment exercise count in session
    session.exercise_count += 1

    # Keep legacy progress row synchronized
    legacy_prog = db.query(LegacyProgress).filter(LegacyProgress.user_id == current_user.id).first()
    if not legacy_prog:
        legacy_prog = LegacyProgress(user_id=current_user.id, words=0, images=0, phrases=0, correct=0, attempts=0)
        db.add(legacy_prog)

    legacy_prog.attempts += 1
    if data.similarity_score >= 70:
        legacy_prog.correct += 1

    # Detect practice category if exercise linked
    if data.exercise_id:
        ex = db.query(Exercise).filter(Exercise.id == data.exercise_id).first()
        if ex and ex.exercise_type == "word":
            legacy_prog.words += 1
        elif ex and ex.exercise_type in ["phrase", "sentence", "conversation"]:
            legacy_prog.phrases += 1

    db.commit()
    db.refresh(response_record)

    return PracticeResponseDetail.model_validate(response_record)


@router.post("/sessions/{session_id}/complete", response_model=PracticeSessionResponse)
def complete_practice_session(
    session_id: int,
    data: PracticeSessionComplete,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marks session as completed and records final duration."""
    session = db.query(PracticeSession).filter(PracticeSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found")

    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot complete another user's session")

    session.completion_status = "completed"
    now = datetime.now(timezone.utc)
    session.end_time = now

    if data.duration_seconds and data.duration_seconds > 0:
        session.duration_seconds = data.duration_seconds
    elif session.start_time:
        start_naive = session.start_time.replace(tzinfo=timezone.utc) if session.start_time.tzinfo is None else session.start_time
        duration = int((now - start_naive).total_seconds())
        session.duration_seconds = max(1, duration)

    db.commit()
    db.refresh(session)
    return PracticeSessionResponse.model_validate(session)


# ==========================================
# TEXT-TO-SPEECH (TTS) ENDPOINTS
# ==========================================

@router.get("/tts/status")
def get_speech_synthesis_status():
    """Returns TTS configuration, available neural voices, and active provider."""
    return get_tts_status()


@router.post("/tts/synthesize")
async def synthesize_text_to_speech(req: TTSRequest):
    """
    Synthesizes natural speech for practice words, sentences, or spoken feedback.
    Streams an audio/mpeg MP3 response.
    """
    try:
        audio_bytes = await synthesize_speech(
            text=req.text,
            language=req.language or "ta-IN",
            voice=req.voice,
            rate=req.rate if req.rate is not None else 0.8
        )
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=speech.mp3",
                "Cache-Control": "public, max-age=86400"
            }
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Speech synthesis service error: {str(e)}"
        )

