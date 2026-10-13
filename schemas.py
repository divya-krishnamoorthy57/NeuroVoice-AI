from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ==========================================
# AUTHENTICATION SCHEMAS
# ==========================================

class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    confirm_password: Optional[str] = None
    age_range: Optional[str] = None
    daily_practice_goal: Optional[int] = 10


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    status: str = "success"
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ==========================================
# PROFILE & PREFERENCES SCHEMAS
# ==========================================

class UserProfileSchema(BaseModel):
    id: Optional[int] = None
    user_id: int
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    age_range: Optional[str] = None
    preferred_language: str = "en-US"
    practice_preferences: Optional[str] = "words,phrases,sentences"
    daily_practice_goal: int = 10
    font_size_preference: str = "normal"
    high_contrast: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    age_range: Optional[str] = None
    preferred_language: Optional[str] = None
    practice_preferences: Optional[str] = None
    daily_practice_goal: Optional[int] = None
    font_size_preference: Optional[str] = None
    high_contrast: Optional[bool] = None


class UserPreferenceSchema(BaseModel):
    daily_goal_minutes: int = 15
    preferred_categories: Optional[str] = "word-practice,phrase-practice"
    preferred_duration: int = 10
    preferred_language: str = "en-US"
    speech_rate: float = 0.9

    model_config = ConfigDict(from_attributes=True)


class UserPreferenceUpdate(BaseModel):
    daily_goal_minutes: Optional[int] = None
    preferred_categories: Optional[str] = None
    preferred_duration: Optional[int] = None
    preferred_language: Optional[str] = None
    speech_rate: Optional[float] = None


# ==========================================
# EXERCISE & CATEGORY SCHEMAS
# ==========================================

class CategorySchema(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    icon: str = "message-circle"
    display_order: int = 0
    is_active: bool = True
    exercise_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    icon: str = "message-circle"
    display_order: int = 0
    is_active: bool = True


class ExerciseSchema(BaseModel):
    id: int
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    title: str
    target_text: str
    exercise_type: str  # "word", "phrase", "sentence", "conversation"
    difficulty: str     # "beginner", "intermediate", "advanced"
    prompt: Optional[str] = None
    hints: Optional[str] = None
    example_sentence: Optional[str] = None
    english_meaning: Optional[str] = None
    translated_sentence: Optional[str] = None
    language: str = "en-US"
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    display_order: int = 0
    is_active: bool = True
    is_bookmarked: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)


class ExerciseCreate(BaseModel):
    category_id: Optional[int] = None
    title: str
    target_text: str
    exercise_type: str = "word"
    difficulty: str = "beginner"
    prompt: Optional[str] = None
    hints: Optional[str] = None
    example_sentence: Optional[str] = None
    english_meaning: Optional[str] = None
    translated_sentence: Optional[str] = None
    language: str = "en-US"
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    display_order: int = 0
    is_active: bool = True


class ExerciseUpdate(BaseModel):
    category_id: Optional[int] = None
    title: Optional[str] = None
    target_text: Optional[str] = None
    exercise_type: Optional[str] = None
    difficulty: Optional[str] = None
    prompt: Optional[str] = None
    hints: Optional[str] = None
    example_sentence: Optional[str] = None
    english_meaning: Optional[str] = None
    translated_sentence: Optional[str] = None
    language: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


# ==========================================
# PRACTICE & FEEDBACK SCHEMAS
# ==========================================

class SpeechFeedbackRequest(BaseModel):
    target_text: str
    spoken_text: str
    exercise_type: Optional[str] = "word"
    language: Optional[str] = "en-US"


class WordComparison(BaseModel):
    word: str
    status: str  # "matched", "missing", "extra"


class SpeechFeedbackResponse(BaseModel):
    target_text: str
    spoken_text: str
    similarity_score: float
    is_exact_match: bool
    matched_words: List[str]
    missing_words: List[str]
    detailed_words: List[WordComparison]
    suggestion: str
    disclaimer: str = "Text similarity score is an algorithmic string comparison aid and not a clinical diagnostic assessment."


class PracticeSessionStart(BaseModel):
    category_id: Optional[int] = None
    language: Optional[str] = "en-US"


class PracticeResponseCreate(BaseModel):
    exercise_id: Optional[int] = None
    target_text: str
    recognized_text: str
    similarity_score: float
    matched_words: Optional[str] = None
    missing_words: Optional[str] = None
    attempt_number: int = 1
    language: Optional[str] = "en-US"


class PracticeResponseDetail(BaseModel):
    id: int
    session_id: int
    exercise_id: Optional[int]
    language: str = "en-US"
    target_text: str
    recognized_text: str
    similarity_score: float
    attempt_number: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PracticeSessionComplete(BaseModel):
    duration_seconds: Optional[int] = None


class PracticeSessionResponse(BaseModel):
    id: int
    user_id: int
    category_id: Optional[int]
    language: str = "en-US"
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: int
    exercise_count: int
    completion_status: str
    responses: Optional[List[PracticeResponseDetail]] = []

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# DASHBOARD & PROGRESS SCHEMAS
# ==========================================

class RecommendedExercise(BaseModel):
    id: int
    title: str
    target_text: str
    exercise_type: str
    difficulty: str
    prompt: Optional[str]


class DashboardSummaryResponse(BaseModel):
    user_name: str
    daily_goal_minutes: int
    today_practice_minutes: int
    today_completed_exercises: int
    daily_goal_percentage: int
    total_completed_exercises: int
    total_sessions_completed: int
    current_streak_days: int
    average_accuracy: float
    recommended_exercise: Optional[RecommendedExercise] = None


class CategoryProgressItem(BaseModel):
    category_name: str
    slug: str
    attempts: int
    average_score: float


class ProgressSummaryResponse(BaseModel):
    total_sessions: int
    total_exercises: int
    total_practice_time_minutes: int
    average_similarity_score: float
    current_streak: int
    category_breakdown: List[CategoryProgressItem]
    weekly_activity: List[dict]  # [{"date": "2026-10-12", "minutes": 15, "exercises": 6}]
    score_trends: List[dict]     # [{"session_id": 1, "date": "...", "score": 85.0}]


# ==========================================
# PRACTICE PLAN SCHEMAS
# ==========================================

class PracticePlanItemSchema(BaseModel):
    id: int
    exercise_id: int
    exercise: Optional[ExerciseSchema] = None
    order_index: int
    completed: bool
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PracticePlanSchema(BaseModel):
    id: int
    user_id: int
    daily_target_minutes: int
    target_exercises_per_day: int
    plan_notes: Optional[str]
    is_active: bool
    items: List[PracticePlanItemSchema] = []

    model_config = ConfigDict(from_attributes=True)


class GeneratePlanRequest(BaseModel):
    daily_target_minutes: Optional[int] = 15
    preferred_categories: Optional[List[str]] = None
    difficulty_preference: Optional[str] = "beginner"


# ==========================================
# CONTACT MESSAGE SCHEMAS
# ==========================================

class ContactMessageCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    subject: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=10, max_length=2000)


class ContactMessageResponse(BaseModel):
    id: int
    name: str
    email: str
    subject: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# ADMIN SCHEMAS
# ==========================================

class AdminStatsResponse(BaseModel):
    total_users: int
    total_exercises: int
    total_sessions: int
    total_responses: int
    unread_contacts: int


# ==========================================
# TEXT-TO-SPEECH (TTS) SCHEMAS
# ==========================================

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    language: Optional[str] = "ta-IN"
    voice: Optional[str] = None
    rate: Optional[float] = 0.8