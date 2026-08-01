from fastapi import APIRouter, HTTPException
import mysql.connector

from database import get_connection
from auth import hash_password, verify_password, create_access_token
from schemas import UserCreate, UserLogin

router = APIRouter()


@router.post("/register")
def register(user: UserCreate):

    conn = get_connection()
    cursor = conn.cursor()

    try:
        hashed_password = hash_password(user.password)

        cursor.execute(
            """
            INSERT INTO users (name, email, password)
            VALUES (%s, %s, %s)
            """,
            (
                user.name,
                user.email,
                hashed_password
            )
        )

        conn.commit()

        return {
            "status": "success",
            "message": "User registered successfully"
        }

    except mysql.connector.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()
        conn.close()


@router.post("/login")
def login(user: UserLogin):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM users WHERE email=%s",
            (user.email,)
        )

        db_user = cursor.fetchone()

        if not db_user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        if not verify_password(
            user.password,
            db_user["password"]
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid password"
            )

        token = create_access_token(
            {
                "user_id": db_user["id"],
                "email": db_user["email"]
            }
        )

        return {
            "status": "success",
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": db_user["id"],
                "name": db_user["name"],
                "email": db_user["email"]
            }
        }

    finally:
        cursor.close()
        conn.close()