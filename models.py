from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(20), default="user", nullable=False)  # "user" or "admin"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("PracticeSession", back_populates="user", cascade="all, delete-orphan")
    bookmarks = relationship("BookmarkedExercise", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPracticePreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    plans = relationship("PracticePlan", back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    age_range = Column(String(50), nullable=True)  # e.g., "18-35", "36-50", "51-65", "65+"
    preferred_language = Column(String(20), default="en-US", nullable=False)
    practice_preferences = Column(String(255), nullable=True)  # e.g. "words,phrases"
    daily_practice_goal = Column(Integer, default=10, nullable=False)  # in minutes or exercise count
    font_size_preference = Column(String(20), default="normal", nullable=False)  # "normal", "large", "x-large"
    high_contrast = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile")


class ExerciseCategory(Base):
    __tablename__ = "exercise_categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), default="message-circle", nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    exercises = relationship("Exercise", back_populates="category", cascade="all, delete-orphan")


class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("exercise_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(150), nullable=False)
    target_text = Column(Text, nullable=False)
    exercise_type = Column(String(50), default="word", nullable=False)  # "word", "phrase", "sentence", "conversation"
    difficulty = Column(String(20), default="beginner", nullable=False)  # "beginner", "intermediate", "advanced"
    prompt = Column(Text, nullable=True)
    hints = Column(Text, nullable=True)
    example_sentence = Column(Text, nullable=True)
    english_meaning = Column(Text, nullable=True)
    translated_sentence = Column(Text, nullable=True)
    language = Column(String(20), default="en-US", nullable=False)
    image_url = Column(String(255), nullable=True)
    audio_url = Column(String(255), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    category = relationship("ExerciseCategory", back_populates="exercises")
    responses = relationship("PracticeResponse", back_populates="exercise")
    bookmarks = relationship("BookmarkedExercise", back_populates="exercise", cascade="all, delete-orphan")


class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("exercise_categories.id", ondelete="SET NULL"), nullable=True)
    language = Column(String(20), default="en-US", nullable=False)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, default=0, nullable=False)
    exercise_count = Column(Integer, default=0, nullable=False)
    completion_status = Column(String(30), default="in_progress", nullable=False)  # "in_progress", "completed", "abandoned"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="sessions")
    responses = relationship("PracticeResponse", back_populates="session", cascade="all, delete-orphan")


class PracticeResponse(Base):
    __tablename__ = "practice_responses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id", ondelete="CASCADE"), nullable=True, index=True)
    language = Column(String(20), default="en-US", nullable=False)
    target_text = Column(Text, nullable=False)
    recognized_text = Column(Text, nullable=False)
    similarity_score = Column(Float, default=0.0, nullable=False)
    matched_words = Column(Text, nullable=True)  # JSON-encoded string or comma-separated
    missing_words = Column(Text, nullable=True)  # JSON-encoded string or comma-separated
    attempt_number = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("PracticeSession", back_populates="responses")
    exercise = relationship("Exercise", back_populates="responses")


class BookmarkedExercise(Base):
    __tablename__ = "bookmarked_exercises"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="bookmarks")
    exercise = relationship("Exercise", back_populates="bookmarks")


class UserPracticePreference(Base):
    __tablename__ = "user_practice_preferences"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    daily_goal_minutes = Column(Integer, default=15, nullable=False)
    preferred_categories = Column(Text, nullable=True)  # JSON array or comma separated
    preferred_duration = Column(Integer, default=10, nullable=False)
    preferred_language = Column(String(20), default="en-US", nullable=False)
    speech_rate = Column(Float, default=0.9, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="preferences")


class PracticePlan(Base):
    __tablename__ = "practice_plans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    daily_target_minutes = Column(Integer, default=15, nullable=False)
    target_exercises_per_day = Column(Integer, default=5, nullable=False)
    plan_notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="plans")
    items = relationship("PracticePlanItem", back_populates="plan", cascade="all, delete-orphan")


class PracticePlanItem(Base):
    __tablename__ = "practice_plan_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("practice_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    plan = relationship("PracticePlan", back_populates="items")
    exercise = relationship("Exercise")


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    subject = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Legacy table mapped so existing data is accessible
class LegacyProgress(Base):
    __tablename__ = "progress"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    words = Column(Integer, default=0)
    images = Column(Integer, default=0)
    phrases = Column(Integer, default=0)
    correct = Column(Integer, default=0)
    attempts = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())