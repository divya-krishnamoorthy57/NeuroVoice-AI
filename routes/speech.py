from fastapi import APIRouter
from pydantic import BaseModel
from rapidfuzz import fuzz

router = APIRouter()

class SpeechRequest(BaseModel):
    expected_word: str
    spoken_word: str

@router.post("/check")
def check_speech(data: SpeechRequest):
    expected = data.expected_word.lower()
    spoken = data.spoken_word.lower()

    accuracy = fuzz.ratio(expected, spoken)

    if accuracy >= 90:
        message = "Excellent pronunciation!"
    elif accuracy >= 70:
        message = "Good try, keep practicing!"
    else:
        message = "Practice again!"

    return {
        "expected_word": expected,
        "spoken_word": spoken,
        "accuracy": round(accuracy, 2),
        "message": message,
    }