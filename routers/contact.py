from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from models import ContactMessage
from schemas import ContactMessageCreate, ContactMessageResponse

router = APIRouter()


@router.post("/", response_model=ContactMessageResponse, status_code=status.HTTP_201_CREATED)
def submit_contact_message(
    msg_in: ContactMessageCreate,
    db: Session = Depends(get_db)
):
    """Submits validated contact message and stores it in the database."""
    new_message = ContactMessage(
        name=msg_in.name.strip(),
        email=msg_in.email.strip().lower(),
        subject=msg_in.subject.strip(),
        message=msg_in.message.strip(),
        is_read=False
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return ContactMessageResponse.model_validate(new_message)
