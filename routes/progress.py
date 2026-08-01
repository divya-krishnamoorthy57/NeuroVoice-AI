from fastapi import APIRouter
from database import get_connection

router = APIRouter()


# =========================
# SAVE PROGRESS
# =========================

@router.post("/save")
def save_progress(data: dict):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        user_id = data["user_id"]
        practice_type = data["practice_type"]
        accuracy = int(data["accuracy"])


        cursor.execute(
            "SELECT * FROM progress WHERE user_id=%s",
            (user_id,)
        )

        progress = cursor.fetchone()


        is_correct = 1 if accuracy >= 70 else 0



        if progress:


            if practice_type == "word":

                cursor.execute(
                    """
                    UPDATE progress
                    SET
                        words = words + 1,
                        attempts = attempts + 1,
                        correct = correct + %s
                    WHERE user_id=%s
                    """,
                    (is_correct, user_id)
                )


            elif practice_type == "image":

                cursor.execute(
                    """
                    UPDATE progress
                    SET
                        images = images + 1,
                        attempts = attempts + 1,
                        correct = correct + %s
                    WHERE user_id=%s
                    """,
                    (is_correct, user_id)
                )


            elif practice_type == "phrase":

                cursor.execute(
                    """
                    UPDATE progress
                    SET
                        phrases = phrases + 1,
                        attempts = attempts + 1,
                        correct = correct + %s
                    WHERE user_id=%s
                    """,
                    (is_correct, user_id)
                )



        else:


            words = 1 if practice_type == "word" else 0
            images = 1 if practice_type == "image" else 0
            phrases = 1 if practice_type == "phrase" else 0


            cursor.execute(
                """
                INSERT INTO progress
                (
                    user_id,
                    words,
                    images,
                    phrases,
                    correct,
                    attempts
                )
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (
                    user_id,
                    words,
                    images,
                    phrases,
                    is_correct,
                    1
                )
            )



        conn.commit()


        return {
            "status": "success",
            "message": "Progress saved successfully"
        }



    finally:

        cursor.close()
        conn.close()





# =========================
# GET PROGRESS
# =========================

@router.get("/{user_id}")
def get_progress(user_id: int):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)


    try:

        cursor.execute(
            """
            SELECT
                words,
                images,
                phrases,
                correct,
                attempts
            FROM progress
            WHERE user_id=%s
            """,
            (user_id,)
        )


        progress = cursor.fetchone()



        if not progress:

            progress = {
                "words": 0,
                "images": 0,
                "phrases": 0,
                "correct": 0,
                "attempts": 0
            }



        return {

            "status": "success",

            "data": progress

        }



    finally:

        cursor.close()
        conn.close()






# =========================
# AI COACHING TIP
# =========================

@router.get("/coach/{user_id}")
def coaching_tip(user_id: int):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)


    try:


        cursor.execute(
            """
            SELECT
                correct,
                attempts
            FROM progress
            WHERE user_id=%s
            """,
            (user_id,)
        )


        progress = cursor.fetchone()



        if not progress:

            return {

                "tip":
                "Start practicing daily for better communication."

            }




        correct = progress["correct"]
        attempts = progress["attempts"]



        accuracy = 0


        if attempts > 0:

            accuracy = (correct / attempts) * 100





        if accuracy >= 90:

            tip = (
                "Excellent pronunciation! "
                "Keep maintaining your daily practice."
            )


        elif accuracy >= 70:

            tip = (
                "Good progress! "
                "Try speaking slowly and clearly."
            )


        else:

            tip = (
                "Keep practicing. "
                "Focus on each word and sentence."
            )



        return {

            "accuracy": round(accuracy, 2),

            "tip": tip

        }



    finally:

        cursor.close()
        conn.close()