from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from database import init_db
from routes import user, speech, progress

app = FastAPI(
    title="NeuroVoice AI API",
    version="1.0"
)

# Allow React frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database
@app.on_event("startup")
def startup_event():
    init_db()

# Test API
@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "THIS IS MY MAIN.PY",
        "version": "TEST123"
    }

# Authentication Routes
app.include_router(
    user.router,
    prefix="/auth",
    tags=["Authentication"]
)

# Speech Routes
app.include_router(
    speech.router,
    prefix="/speech",
    tags=["Speech"]
)
app.include_router(
    progress.router,
    prefix="/progress",
    tags=["Progress"]
)