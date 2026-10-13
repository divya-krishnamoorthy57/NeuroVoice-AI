import re
import string
import unicodedata
from typing import Optional, List, Dict
from rapidfuzz import fuzz
from schemas import SpeechFeedbackResponse, WordComparison

# Punctuation characters to strip (both Latin and Indic/Tamil punctuation marks)
PUNCTUATION_CHARS = string.punctuation + "“”‘’।॥—–…«»"
PUNCT_TABLE = str.maketrans("", "", PUNCTUATION_CHARS)

# Tamil accepted phonetic & colloquial variants
TAMIL_ACCEPTED_VARIANTS: Dict[str, List[str]] = {
    "தண்ணீர்": ["தண்ணி", "தண்ணீ"],
    "பால்": ["பாலு"],
    "சாதம்": ["சோறு", "சாதமு"],
    "இட்லி": ["இட்லீ", "இட்லிகள்"],
    "தோசை": ["தோச", "தோசை"],
    "ஆப்பிள்": ["ஆப்பிள் பழம்", "ஆப்பில்"],
    "வாழைப்பழம்": ["வாழை பழம்", "வாழைப்பழ"],
    "தேநீர்": ["டீ", "தேனீர்"],
    "காபி": ["காஃபி", "காப்பி"],
    "உணவு": ["சாப்பாடு"],
    "வீடு": ["வீட்டு"],
    "கதவு": ["கதவு"],
    "நாற்காலி": ["நாற்காலி", "சேர்"],
    "படுக்கை": ["படுக்கை", "கட்டில்"],
    "மேசை": ["மேஜை", "டேபிள்"],
    "கைபேசி": ["கைபேசி", "மொபைல்", "போன்"],
    "சாவி": ["சாவி"],
    "சமையலறை": ["சமையல் அறை"],
    "குளியலறை": ["குளியல் அறை", "பாத்ரூம்"],
    "விளக்கு": ["லைட்", "விளக்கு"],
    "அம்மா": ["அம்மா", "அம்மாள்"],
    "அப்பா": ["அப்பா"],
    "அக்கா": ["அக்கா"],
    "அண்ணன்": ["அண்ணா", "அண்ணன்"],
    "தம்பி": ["தம்பி"],
    "தங்கை": ["தங்கச்சி", "தங்கை"],
    "நண்பர்": ["நண்பன்", "தோழன்"],
    "மருத்துவர்": ["டாக்டர்", "மருத்துவர்"],
    "செவிலியர்": ["நர்ஸ்", "செவிலியர்"],
    "குழந்தை": ["பாப்பா", "பிள்ளை"],
    "உதவி": ["உதவி"],
    "வலி": ["நோவு", "வலி"],
    "ஓய்வு": ["ரெஸ்ட்", "ஓய்வு"],
    "பசி": ["பசிக்குது"],
    "தாகம்": ["தாகம்"],
    "கழிப்பறை": ["டாய்லெட்", "கழிவறை"],
    "மருந்து": ["மாத்திரை", "மருந்து"],
    "பை": ["பேக்", "கைப்பை", "பை"],
    "பல் துலக்கி": ["டூத் பிரஷ்", "பிரஷ்", "பல் பிரஷ்", "பல் துலக்கும் தூரிகை"],
    "ஆம்": ["ஆமாம்", "ஆமா"],
    "இல்லை": ["இல்ல", "இல்லை"],
    "நன்றி": ["ரொம்ப நன்றி", "மிக்க நன்றி", "நன்றிகள்"],
    "சாப்பிடு": ["சாப்பிடுங்க", "சாப்பிடுங்கள்", "சாப்டு"],
    "குடி": ["குடிங்க", "குடியுங்கள்"],
    "உட்கார்": ["உட்காரு", "உட்காருங்கள்"],
    "எழுந்திரு": ["எழுந்திருங்க", "எழுந்திருங்கள்"],
    "நட": ["நடங்க", "நடங்கள்"],
    "தூங்கு": ["தூங்குங்க", "தூங்குங்கள்"],
    "வா": ["வாங்க", "வாருங்கள்"],
    "போ": ["போங்க", "போங்கள்"],
    "திற": ["திறங்க", "திறங்கள்"],
    "மூடு": ["மூடுங்க", "மூடுங்கள்"],
    # Phrases variants (sandhi variations)
    "எனக்குத் தண்ணீர் வேண்டும்": [
        "எனக்கு தண்ணீர் வேண்டும்",
        "எனக்குத் தண்ணி வேண்டும்",
        "எனக்கு தண்ணி வேணும்",
        "எனக்குத் தண்ணீர் வேணும்"
    ],
    "எனக்குப் பசிக்கிறது": [
        "எனக்கு பசிக்கிறது",
        "எனக்குப் பசிக்குது",
        "எனக்கு பசிக்குது"
    ],
    "எனக்குத் தாகமாக இருக்கிறது": [
        "எனக்கு தாகமாக இருக்கிறது",
        "எனக்குத் தாகமா இருக்கு",
        "எனக்கு தாகமா இருக்கு"
    ],
    "எனக்கு உதவி செய்யுங்கள்": [
        "எனக்கு உதவி செய்யுங்க",
        "எனக்கு உதவி வேண்டும்"
    ],
    "நான் ஓய்வெடுக்க வேண்டும்": [
        "நான் ஓய்வு எடுக்க வேண்டும்",
        "நான் ஓய்வெடுக்க வேணும்",
        "நான் ஓய்வு எடுக்க வேணும்"
    ],
    "நான் வீட்டிற்குப் போக வேண்டும்": [
        "நான் வீட்டிற்கு போக வேண்டும்",
        "நான் வீட்டுக்குப் போக வேண்டும்",
        "நான் வீட்டுக்கு போக வேணும்",
        "நான் வீட்டுக்குப் போக வேணும்"
    ],
    "கதவைத் திறக்கவும்": [
        "கதவை திறக்கவும்",
        "கதவைத் திற",
        "கதவை திற",
        "கதவை திறங்க"
    ],
    "என் குடும்பத்தினரை அழைக்கவும்": [
        "என் குடும்பத்தை அழைக்கவும்",
        "என் குடும்பத்தை கூப்பிடுங்க",
        "என் குடும்பத்தினரை கூப்பிடுங்கள்"
    ],
    "எனக்கு மருத்துவர் வேண்டும்": [
        "எனக்கு டாக்டர் வேண்டும்",
        "எனக்கு மருத்துவர் வேணும்",
        "எனக்கு டாக்டர் வேணும்"
    ],
    "தயவுசெய்து உதவுங்கள்": [
        "தயவு செய்து உதவுங்கள்",
        "உதவுங்கள்",
        "தயவுசெய்து உதவி செய்யுங்கள்",
        "தயவு செய்து உதவி செய்யுங்க",
        "எனக்கு உதவி செய்யுங்கள்",
        "உதவி செய்யுங்கள்"
    ],
    "நான் உட்கார வேண்டும்": [
        "நான் உக்கார வேண்டும்",
        "நான் உட்கார வேணும்",
        "நான் உக்கார வேணும்",
        "உட்கார வேண்டும்"
    ],
    "என் கைப்பேசி எங்கே": [
        "என் கைபேசி எங்கே",
        "என் போன் எங்கே",
        "என் செல்போன் எங்கே",
        "என் கைப்பேசி எங்க",
        "என் கைபேசி எங்க",
        "என் போன் எங்க"
    ]
}


def is_tamil_text(text: str) -> bool:
    """Detects whether text contains Tamil Unicode script (U+0B80 - U+0BFF)."""
    return bool(re.search(r"[\u0B80-\u0BFF]", text or ""))


def normalize_text(text: str) -> str:
    """
    Normalizes string with Unicode NFC composition, strips punctuation,
    collapses duplicate spaces, and converts to lowercase.
    Preserves Tamil characters and diacritics.
    """
    if not text:
        return ""
    # Unicode NFC normalization to compose combining marks
    text = unicodedata.normalize("NFC", text)
    # Remove punctuation
    text = text.translate(PUNCT_TABLE)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def evaluate_speech_similarity(
    target_text: str,
    spoken_text: str,
    exercise_type: str = "word",
    language: Optional[str] = "en-US"
) -> SpeechFeedbackResponse:
    """
    Compares target text and spoken recognition transcript using Unicode NFC normalization,
    RapidFuzz fuzzy string matching, Tamil dialect/sandhi variant recognition,
    and word-by-word token comparison.
    """
    clean_target = normalize_text(target_text)
    clean_spoken = normalize_text(spoken_text)

    is_tamil = is_tamil_text(target_text) or (language and language.lower().startswith("ta"))

    disclaimer = (
        "உரை ஒற்றுமை மதிப்பீடு என்பது ஒரு ஒப்பீட்டு அளவீடு மட்டுமே; இது மருத்துவ மதிப்பீடு அல்ல."
        if is_tamil
        else "Text similarity score is an algorithmic string comparison aid and not a clinical diagnostic assessment."
    )

    # Empty spoken text check (not penalized as a negative failure, but handled with clear guidance)
    if not clean_spoken:
        suggestion = (
            "உங்கள் குரலைத் தெளிவாகக் கேட்க முடியவில்லை. மீண்டும் முயற்சி செய்யலாம்."
            if is_tamil
            else "No speech was detected. Please verify your microphone permissions and try speaking clearly."
        )
        return SpeechFeedbackResponse(
            target_text=target_text,
            spoken_text="",
            similarity_score=0.0,
            is_exact_match=False,
            matched_words=[],
            missing_words=clean_target.split() if clean_target else [],
            detailed_words=[WordComparison(word=w, status="missing") for w in clean_target.split()],
            suggestion=suggestion,
            disclaimer=disclaimer
        )

    # Check for direct exact match
    is_exact = (clean_target == clean_spoken)

    # RapidFuzz similarity score calculation
    ratio_score = float(fuzz.ratio(clean_target, clean_spoken))
    token_score = float(fuzz.token_sort_ratio(clean_target, clean_spoken))

    if exercise_type == "word" or len(clean_target.split()) <= 1:
        base_score = ratio_score
    else:
        base_score = round((ratio_score * 0.6) + (token_score * 0.4), 1)

    # Check against known acceptable Tamil variants
    if is_tamil and clean_target in TAMIL_ACCEPTED_VARIANTS:
        for variant in TAMIL_ACCEPTED_VARIANTS[clean_target]:
            v_norm = normalize_text(variant)
            if v_norm == clean_spoken:
                base_score = 100.0
                is_exact = True
                break
            v_ratio = float(fuzz.ratio(v_norm, clean_spoken))
            if v_ratio > base_score:
                base_score = v_ratio

    score = max(0.0, min(100.0, round(base_score, 1)))

    # Word-level breakdown
    target_tokens = clean_target.split()
    spoken_tokens = clean_spoken.split()

    matched_words: List[str] = []
    missing_words: List[str] = []
    detailed_words: List[WordComparison] = []

    spoken_tokens_set = list(spoken_tokens)

    for word in target_tokens:
        best_match_idx = -1
        best_match_score = 0
        for idx, sp_word in enumerate(spoken_tokens_set):
            tok_sim = fuzz.ratio(word, sp_word)
            if tok_sim >= 75 and tok_sim > best_match_score:
                best_match_score = tok_sim
                best_match_idx = idx

        if best_match_idx >= 0:
            matched_words.append(word)
            detailed_words.append(WordComparison(word=word, status="matched"))
            spoken_tokens_set.pop(best_match_idx)
        else:
            missing_words.append(word)
            detailed_words.append(WordComparison(word=word, status="missing"))

    # Generate supportive, respectful feedback in user's target language
    if is_tamil:
        if score >= 90:
            suggestion = "மிகவும் நன்று! அருமையாகச் சொன்னீர்கள்!"
        elif score >= 75:
            suggestion = "நன்றாக முயற்சி செய்தீர்கள். மீண்டும் முயற்சி செய்யலாம்."
        elif score >= 45:
            suggestion = "பரவாயில்லை. மீண்டும் கேட்டுப் பேசிப் பாருங்கள்."
        else:
            suggestion = "பரவாயில்லை. மீண்டும் கேட்டுப் பேசிப் பாருங்கள்."
    else:
        if score >= 90:
            suggestion = "Excellent articulation! Your pronunciation was clear, fluent, and well-recognized."
        elif score >= 75:
            suggestion = "Great attempt! You matched the main sounds. Try speaking slightly slower to catch every syllable."
        elif score >= 50:
            suggestion = "Good effort! Listen to the audio model once more, focus on the missing words, and try again."
        else:
            suggestion = "Practice makes steady progress! Take a calm breath, listen to the prompt, and repeat at your own pace."

    return SpeechFeedbackResponse(
        target_text=target_text,
        spoken_text=spoken_text,
        similarity_score=score,
        is_exact_match=is_exact,
        matched_words=matched_words,
        missing_words=missing_words,
        detailed_words=detailed_words,
        suggestion=suggestion,
        disclaimer=disclaimer
    )
