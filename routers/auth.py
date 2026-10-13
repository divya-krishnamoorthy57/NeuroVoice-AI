from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User, UserProfile
from schemas import UserCreate, UserLogin, TokenResponse, UserResponse
from auth import hash_password, verify_password, create_access_token
from dependencies import get_current_user

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Registers a new user and returns JWT token."""
    # Check if email is already registered
    existing_user = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists. Please log in."
        )

    # Hash password
    hashed_pwd = hash_password(user_in.password)

    new_user = User(
        name=user_in.name.strip(),
        email=user_in.email.lower().strip(),
        password=hashed_pwd,
        role="user",
        is_active=True
    )
    db.add(new_user)
    db.flush()

    # Create associated user profile
    new_profile = UserProfile(
        user_id=new_user.id,
        age_range=user_in.age_range,
        daily_practice_goal=user_in.daily_practice_goal or 10,
        preferred_language="en-US"
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_user)

    # Generate token
    token = create_access_token({"sub": str(new_user.id), "user_id": new_user.id, "email": new_user.email})

    return TokenResponse(
        status="success",
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user)
    )


@router.post("/login", response_model=TokenResponse)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    """Authenticates user and returns JWT token."""
    user = db.query(User).filter(User.email == user_in.email.lower().strip()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not verify_password(user_in.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is currently deactivated. Please contact support."
        )

    token = create_access_token({"sub": str(user.id), "user_id": user.id, "email": user.email})

    return TokenResponse(
        status="success",
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Returns currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Client logout confirmation."""
    return {"status": "success", "message": "Successfully logged out"}
