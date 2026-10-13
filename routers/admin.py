from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import (
    User, Exercise, ExerciseCategory, PracticeSession, PracticeResponse, ContactMessage
)
from schemas import (
    AdminStatsResponse, ExerciseSchema, ExerciseCreate, ExerciseUpdate,
    CategorySchema, CategoryCreate, ContactMessageResponse
)
from dependencies import get_current_admin

router = APIRouter()


@router.get("/stats", response_model=AdminStatsResponse)
def get_admin_stats(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Returns administrative platform metrics."""
    total_users = db.query(User).count()
    total_exercises = db.query(Exercise).count()
    total_sessions = db.query(PracticeSession).count()
    total_responses = db.query(PracticeResponse).count()
    unread_contacts = db.query(ContactMessage).filter(ContactMessage.is_read == False).count()

    return AdminStatsResponse(
        total_users=total_users,
        total_exercises=total_exercises,
        total_sessions=total_sessions,
        total_responses=total_responses,
        unread_contacts=unread_contacts
    )


# --- EXERCISE MANAGEMENT ---

@router.get("/exercises", response_model=List[ExerciseSchema])
def admin_list_exercises(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Lists all exercises including inactive ones for administrative management."""
    exercises = db.query(Exercise).order_by(Exercise.id.asc()).all()
    result = []
    for ex in exercises:
        ex_dict = ExerciseSchema.model_validate(ex)
        if ex.category:
            ex_dict.category_name = ex.category.name
        result.append(ex_dict)
    return result


@router.post("/exercises", response_model=ExerciseSchema, status_code=status.HTTP_201_CREATED)
def admin_create_exercise(
    ex_in: ExerciseCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Creates a new exercise."""
    new_exercise = Exercise(
        category_id=ex_in.category_id,
        title=ex_in.title.strip(),
        target_text=ex_in.target_text.strip(),
        exercise_type=ex_in.exercise_type,
        difficulty=ex_in.difficulty,
        prompt=ex_in.prompt,
        hints=ex_in.hints,
        image_url=ex_in.image_url,
        audio_url=ex_in.audio_url,
        display_order=ex_in.display_order,
        is_active=ex_in.is_active
    )
    db.add(new_exercise)
    db.commit()
    db.refresh(new_exercise)
    return ExerciseSchema.model_validate(new_exercise)


@router.put("/exercises/{exercise_id}", response_model=ExerciseSchema)
def admin_update_exercise(
    exercise_id: int,
    ex_in: ExerciseUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Updates an existing exercise."""
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    for field, val in ex_in.model_dump(exclude_unset=True).items():
        setattr(exercise, field, val)

    db.commit()
    db.refresh(exercise)
    return ExerciseSchema.model_validate(exercise)


@router.delete("/exercises/{exercise_id}")
def admin_delete_exercise(
    exercise_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Deactivates or deletes an exercise."""
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    # Soft delete / deactivation preferred
    exercise.is_active = False
    db.commit()
    return {"status": "success", "message": "Exercise deactivated successfully"}


# --- CATEGORY MANAGEMENT ---

@router.get("/categories", response_model=List[CategorySchema])
def admin_list_categories(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Lists all exercise categories."""
    categories = db.query(ExerciseCategory).order_by(ExerciseCategory.display_order.asc()).all()
    return [CategorySchema.model_validate(c) for c in categories]


@router.post("/categories", response_model=CategorySchema, status_code=status.HTTP_201_CREATED)
def admin_create_category(
    cat_in: CategoryCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Creates a new category."""
    existing = db.query(ExerciseCategory).filter(
        (ExerciseCategory.slug == cat_in.slug) | (ExerciseCategory.name == cat_in.name)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category name or slug already exists")

    new_cat = ExerciseCategory(**cat_in.model_dump())
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return CategorySchema.model_validate(new_cat)


# --- CONTACT MESSAGES ---

@router.get("/contacts", response_model=List[ContactMessageResponse])
def admin_list_contacts(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Lists submitted contact messages for review."""
    messages = db.query(ContactMessage).order_by(ContactMessage.created_at.desc()).all()
    return [ContactMessageResponse.model_validate(m) for m in messages]


@router.put("/contacts/{contact_id}/read")
def admin_mark_contact_read(
    contact_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Marks contact message as read."""
    msg = db.query(ContactMessage).filter(ContactMessage.id == contact_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    msg.is_read = True
    db.commit()
    return {"status": "success", "message": "Marked as read"}
