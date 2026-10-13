from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from database import get_db
from models import Exercise, ExerciseCategory, BookmarkedExercise, User
from schemas import ExerciseSchema, CategorySchema
from dependencies import get_optional_current_user, get_current_user

router = APIRouter()


@router.get("/categories", response_model=List[CategorySchema])
def get_categories(db: Session = Depends(get_db)):
    """Returns all active exercise categories with count of active exercises."""
    categories = (
        db.query(ExerciseCategory)
        .filter(ExerciseCategory.is_active == True)
        .order_by(ExerciseCategory.display_order.asc())
        .all()
    )

    result = []
    for cat in categories:
        count = (
            db.query(Exercise)
            .filter(Exercise.category_id == cat.id, Exercise.is_active == True)
            .count()
        )
        schema = CategorySchema.model_validate(cat)
        schema.exercise_count = count
        result.append(schema)

    return result


@router.get("/", response_model=List[ExerciseSchema])
def list_exercises(
    search: Optional[str] = Query(None, description="Search term for title or target text"),
    category: Optional[str] = Query(None, description="Category slug or ID"),
    difficulty: Optional[str] = Query(None, description="beginner, intermediate, or advanced"),
    exercise_type: Optional[str] = Query(None, description="word, phrase, sentence, or conversation"),
    language: Optional[str] = Query(None, description="Language code: en, ta, en-US, ta-IN"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns exercise library filtered by category, difficulty, type, language, and keyword search.
    Indicates whether the exercise is bookmarked by the requesting user.
    """
    query = db.query(Exercise).filter(Exercise.is_active == True)

    if language:
        query = query.filter(Exercise.language.ilike(f"{language.strip()}%"))

    if category:
        if category.isdigit():
            query = query.filter(Exercise.category_id == int(category))
        else:
            query = query.join(ExerciseCategory, Exercise.category_id == ExerciseCategory.id).filter(
                ExerciseCategory.slug == category
            )

    if difficulty:
        query = query.filter(Exercise.difficulty == difficulty.lower())

    if exercise_type:
        type_clean = exercise_type.lower().strip()
        if type_clean == "sentence":
            sentence_cond = Exercise.exercise_type == "sentence"
            if language:
                sentence_cond = and_(sentence_cond, Exercise.language.ilike(f"{language.strip()}%"))
            sentence_count = db.query(Exercise).filter(sentence_cond, Exercise.is_active == True).count()
            if sentence_count > 0:
                query = query.filter(Exercise.exercise_type == "sentence")
            else:
                query = query.filter(Exercise.exercise_type.in_(["sentence", "phrase"]))
        elif type_clean == "phrase":
            query = query.filter(Exercise.exercise_type.in_(["phrase", "sentence"]))
        elif type_clean == "image":
            image_cond = Exercise.exercise_type == "image"
            if language:
                image_cond = and_(image_cond, Exercise.language.ilike(f"{language.strip()}%"))
            image_count = db.query(Exercise).filter(image_cond, Exercise.is_active == True).count()
            if image_count > 0:
                query = query.filter(Exercise.exercise_type == "image")
            else:
                query = query.filter(
                    or_(
                        Exercise.exercise_type == "image",
                        and_(Exercise.exercise_type == "word", Exercise.image_url != None)
                    )
                )
        else:
            query = query.filter(Exercise.exercise_type == type_clean)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Exercise.title.ilike(search_pattern),
                Exercise.target_text.ilike(search_pattern),
                Exercise.prompt.ilike(search_pattern),
                Exercise.english_meaning.ilike(search_pattern)
            )
        )

    exercises = query.order_by(Exercise.display_order.asc(), Exercise.id.asc()).offset(offset).limit(limit).all()

    # User bookmarks
    bookmarked_ids = set()
    if current_user:
        bookmarks = (
            db.query(BookmarkedExercise.exercise_id)
            .filter(BookmarkedExercise.user_id == current_user.id)
            .all()
        )
        bookmarked_ids = {b[0] for b in bookmarks}

    result = []
    for ex in exercises:
        ex_dict = ExerciseSchema.model_validate(ex)
        if ex.category:
            ex_dict.category_name = ex.category.name
        ex_dict.is_bookmarked = (ex.id in bookmarked_ids)
        result.append(ex_dict)

    return result


@router.get("/bookmarked/list", response_model=List[ExerciseSchema])
def get_bookmarked_exercises(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns exercises saved/bookmarked by current user."""
    exercises = (
        db.query(Exercise)
        .join(BookmarkedExercise, Exercise.id == BookmarkedExercise.exercise_id)
        .filter(BookmarkedExercise.user_id == current_user.id, Exercise.is_active == True)
        .order_by(BookmarkedExercise.created_at.desc())
        .all()
    )

    result = []
    for ex in exercises:
        ex_dict = ExerciseSchema.model_validate(ex)
        if ex.category:
            ex_dict.category_name = ex.category.name
        ex_dict.is_bookmarked = True
        result.append(ex_dict)

    return result


@router.get("/{exercise_id}", response_model=ExerciseSchema)
def get_exercise_by_id(
    exercise_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Returns a specific exercise by ID."""
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id, Exercise.is_active == True).first()
    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found"
        )

    is_bookmarked = False
    if current_user:
        bm = db.query(BookmarkedExercise).filter(
            BookmarkedExercise.user_id == current_user.id,
            BookmarkedExercise.exercise_id == exercise.id
        ).first()
        is_bookmarked = (bm is not None)

    ex_dict = ExerciseSchema.model_validate(exercise)
    if exercise.category:
        ex_dict.category_name = exercise.category.name
    ex_dict.is_bookmarked = is_bookmarked
    return ex_dict


@router.post("/{exercise_id}/bookmark")
def toggle_bookmark(
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggles bookmark status of an exercise for current user."""
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    existing = db.query(BookmarkedExercise).filter(
        BookmarkedExercise.user_id == current_user.id,
        BookmarkedExercise.exercise_id == exercise_id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        return {"status": "success", "is_bookmarked": False, "message": "Bookmark removed"}
    else:
        new_bm = BookmarkedExercise(user_id=current_user.id, exercise_id=exercise_id)
        db.add(new_bm)
        db.commit()
        return {"status": "success", "is_bookmarked": True, "message": "Exercise bookmarked"}
