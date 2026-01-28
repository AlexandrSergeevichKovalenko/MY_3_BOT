import asyncio
import logging
import os
import re
from typing import Any

import psycopg2

from backend.config_mistakes_data import (
    VALID_CATEGORIES,
    VALID_CATEGORIES_lower,
    VALID_SUBCATEGORIES,
    VALID_SUBCATEGORIES_lower,
)
from backend.openai_manager import client, get_or_create_openai_resources


DATABASE_URL = os.getenv("DATABASE_URL_RAILWAY")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL_RAILWAY не установлен для translation_workflow.")


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


async def check_translation(
    original_text: str,
    user_translation: str,
    sentence_number: int | None = None,
) -> tuple[str, list[str], list[str], int | None, str | None]:
    task_name = "check_translation"
    system_instruction_key = "check_translation"
    assistant_id, _ = await get_or_create_openai_resources(system_instruction_key, task_name)

    thread = await client.beta.threads.create()
    thread_id = thread.id

    score = None
    categories: list[str] = []
    subcategories: list[str] = []
    correct_translation = None

    user_message = f"""

    **Original sentence (Russian):** "{original_text}"
    **User's translation (German):** "{user_translation}"

    """

    for attempt in range(3):
        try:
            logging.info("GPT started working on sentence %s", original_text)
            await client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_message,
            )

            run = await client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id,
            )
            while True:
                run_status = await client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                if run_status.status == "completed":
                    break
                await asyncio.sleep(2)

            messages = await client.beta.threads.messages.list(thread_id=thread_id)
            last_message = messages.data[0]
            collected_text = last_message.content[0].text.value

            try:
                await client.beta.threads.delete(thread_id=thread_id)
            except Exception as exc:
                logging.warning("Не удалось удалить thread: %s", exc)

            logging.info("GPT response for sentence %s: %s", original_text, collected_text)

            score_str = (
                collected_text.split("Score: ")[-1].split("/")[0].strip()
                if "Score:" in collected_text
                else None
            )
            categories = (
                collected_text.split("Mistake Categories: ")[-1].split("\n")[0].split(", ")
                if "Mistake Categories:" in collected_text
                else []
            )
            subcategories = (
                collected_text.split("Subcategories: ")[-1].split("\n")[0].split(", ")
                if "Subcategories:" in collected_text
                else []
            )

            match = re.search(r"Correct Translation:\s*(.+?)(?:\n|\Z)", collected_text)
            if match:
                correct_translation = match.group(1).strip()

            categories = [
                re.sub(r"[^0-9a-zA-Z\s,+\-–]", "", cat).strip()
                for cat in categories
                if cat.strip()
            ]
            subcategories = [
                re.sub(r"[^0-9a-zA-Z\s,+\-–]", "", subcat).strip()
                for subcat in subcategories
                if subcat.strip()
            ]
            categories = [cat.strip() for cat in categories if cat.strip()]
            subcategories = [subcat.strip() for subcat in subcategories if subcat.strip()]

            if score_str and correct_translation:
                score = int(score_str) if score_str.isdigit() else None
                return collected_text, categories, subcategories, score, correct_translation

        except Exception as exc:
            logging.error(
                "Ошибка при проверке перевода (attempt %s, sentence %s): %s",
                attempt + 1,
                sentence_number,
                exc,
                exc_info=True,
            )
            await asyncio.sleep(1)

    return "Ошибка: не удалось проверить перевод.", [], [], 0, None


async def log_translation_mistake(
    user_id: int,
    original_text: str,
    user_translation: str,
    categories: list[str],
    subcategories: list[str],
    score: int,
    correct_translation: str | None,
) -> None:
    if categories:
        logging.info("Categories from log_translation_mistake: %s", ", ".join(categories))
    if subcategories:
        logging.info("Subcategories from log_translation_mistake: %s", ", ".join(subcategories))

    valid_combinations = []
    for cat in categories:
        cat_lower = cat.lower()
        for subcat in subcategories:
            subcat_lower = subcat.lower()
            if cat_lower in VALID_SUBCATEGORIES_lower and subcat_lower in VALID_SUBCATEGORIES_lower[cat_lower]:
                valid_combinations.append((cat_lower, subcat_lower))

    if not valid_combinations:
        valid_combinations.append(("Other mistake", "Unclassified mistake"))

    valid_combinations = list(set(valid_combinations))

    for main_category, sub_category in valid_combinations:
        main_category = next(
            (cat for cat in VALID_CATEGORIES if cat.lower() == main_category),
            main_category,
        )
        sub_category = next(
            (subcat for subcat in VALID_SUBCATEGORIES.get(main_category, []) if subcat.lower() == sub_category),
            sub_category,
        )

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id_for_mistake_table
                    FROM bt_3_daily_sentences
                    WHERE sentence=%s
                    LIMIT 1;
                    """,
                    (original_text,),
                )
                result = cursor.fetchone()
                sentence_id = result[0] if result else None

                cursor.execute(
                    """
                    INSERT INTO bt_3_detailed_mistakes (
                        user_id, sentence, added_data, main_category, sub_category, mistake_count, sentence_id,
                        correct_translation, score
                    ) VALUES (%s, %s, NOW(), %s, %s, 1, %s, %s, %s)
                    ON CONFLICT (user_id, sentence, main_category, sub_category)
                    DO UPDATE SET
                        mistake_count = bt_3_detailed_mistakes.mistake_count + 1,
                        attempt = bt_3_detailed_mistakes.attempt + 1,
                        last_seen = NOW(),
                        score = EXCLUDED.score;
                    """,
                    (user_id, original_text, main_category, sub_category, sentence_id, correct_translation, score),
                )


async def check_user_translation_webapp(
    user_id: int,
    username: str | None,
    translations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not translations:
        return []

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT unique_id, id_for_mistake_table, id, sentence, session_id
            FROM bt_3_daily_sentences
            WHERE date = CURRENT_DATE AND user_id = %s;
            """,
            (user_id,),
        )
        allowed_rows = cursor.fetchall()
        allowed_by_mistake_id = {
            row[1]: {
                "unique_id": row[0],
                "sentence_id": row[2],
                "sentence": row[3],
                "session_id": row[4],
            }
            for row in allowed_rows
        }

        results: list[dict[str, Any]] = []

        for entry in translations:
            sentence_id_for_mistake = entry.get("id_for_mistake_table")
            if isinstance(sentence_id_for_mistake, str) and sentence_id_for_mistake.isdigit():
                sentence_id_for_mistake = int(sentence_id_for_mistake)
            user_translation = (entry.get("translation") or "").strip()
            if not sentence_id_for_mistake or not user_translation:
                continue

            if sentence_id_for_mistake not in allowed_by_mistake_id:
                results.append(
                    {
                        "sentence_number": None,
                        "error": "Предложение не принадлежит пользователю или не найдено.",
                    }
                )
                continue

            sentence_info = allowed_by_mistake_id[sentence_id_for_mistake]
            sentence_number = sentence_info["unique_id"]
            original_text = sentence_info["sentence"]
            session_id = sentence_info["session_id"]
            sentence_pk_id = sentence_info["sentence_id"]

            cursor.execute(
                """
                SELECT id FROM bt_3_translations
                WHERE user_id = %s AND sentence_id = %s AND timestamp::date = CURRENT_DATE;
                """,
                (user_id, sentence_pk_id),
            )

            existing_translation = cursor.fetchone()
            if existing_translation:
                results.append(
                    {
                        "sentence_number": sentence_number,
                        "error": "Вы уже переводили это предложение.",
                    }
                )
                continue

            try:
                feedback, categories, subcategories, score, correct_translation = await check_translation(
                    original_text,
                    user_translation,
                    sentence_number,
                )
            except Exception as exc:
                logging.error("Ошибка при проверке перевода №%s: %s", sentence_number, exc, exc_info=True)
                results.append(
                    {
                        "sentence_number": sentence_number,
                        "error": "Ошибка: не удалось проверить перевод.",
                    }
                )
                continue

            score_value = int(score) if score and str(score).isdigit() else 50

            cursor.execute(
                """
                INSERT INTO bt_3_translations (user_id, id_for_mistake_table, session_id, username, sentence_id,
                user_translation, score, feedback)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    user_id,
                    sentence_id_for_mistake,
                    session_id,
                    username,
                    sentence_pk_id,
                    user_translation,
                    score_value,
                    feedback,
                ),
            )
            conn.commit()

            cursor.execute(
                """
                SELECT COUNT(*) FROM bt_3_detailed_mistakes
                WHERE sentence_id = %s AND user_id = %s;
                """,
                (sentence_id_for_mistake, user_id),
            )

            was_in_mistakes = cursor.fetchone()[0] > 0

            if was_in_mistakes:
                if score_value >= 85:
                    cursor.execute(
                        """
                        SELECT attempt
                        FROM bt_3_attempts
                        WHERE id_for_mistake_table = %s AND user_id = %s;
                        """,
                        (sentence_id_for_mistake, user_id),
                    )

                    result = cursor.fetchone()
                    total_attempts = (result[0] or 0) + 1

                    cursor.execute(
                        """
                        INSERT INTO bt_3_successful_translations (user_id, sentence_id, score, attempt, date)
                        VALUES (%s, %s, %s, %s, NOW());
                        """,
                        (user_id, sentence_id_for_mistake, score_value, total_attempts),
                    )

                    cursor.execute(
                        """
                        DELETE FROM bt_3_detailed_mistakes
                        WHERE sentence_id = %s AND user_id = %s;
                        """,
                        (sentence_id_for_mistake, user_id),
                    )

                    cursor.execute(
                        """
                        DELETE FROM bt_3_attempts
                        WHERE id_for_mistake_table = %s AND user_id= %s;
                        """,
                        (sentence_id_for_mistake, user_id),
                    )

                    conn.commit()
                else:
                    cursor.execute(
                        """
                        INSERT INTO bt_3_attempts (user_id, id_for_mistake_table, timestamp)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (user_id, id_for_mistake_table)
                        DO UPDATE SET
                            attempt = bt_3_attempts.attempt + 1,
                            timestamp= NOW();
                        """,
                        (sentence_id_for_mistake, user_id),
                    )
                    conn.commit()
            else:
                if score_value >= 80:
                    cursor.execute(
                        """
                        INSERT INTO bt_3_successful_translations (user_id, sentence_id, score, attempt, date)
                        VALUES(%s, %s, %s, %s, NOW());
                        """,
                        (user_id, sentence_id_for_mistake, score_value, 1),
                    )
                    conn.commit()
                else:
                    cursor.execute(
                        """
                        INSERT INTO bt_3_attempts (user_id, id_for_mistake_table)
                        VALUES (%s, %s)
                        ON CONFLICT (user_id, id_for_mistake_table)
                        DO UPDATE SET attempt = bt_3_attempts.attempt + 1;
                        """,
                        (user_id, sentence_id_for_mistake),
                    )
                    conn.commit()

                    await log_translation_mistake(
                        user_id,
                        original_text,
                        user_translation,
                        categories,
                        subcategories,
                        score_value,
                        correct_translation,
                    )

            results.append(
                {
                    "sentence_number": sentence_number,
                    "score": score_value,
                    "original_text": original_text,
                    "user_translation": user_translation,
                    "correct_translation": correct_translation,
                    "feedback": feedback,
                }
            )

        results.sort(key=lambda item: item.get("sentence_number") or 0)
        return results

    finally:
        cursor.close()
        conn.close()


def build_user_daily_summary(user_id: int, username: str | None) -> str | None:
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(DISTINCT ds.id) AS total_sentences,
                    COUNT(DISTINCT t.id) AS translated,
                    (COUNT(DISTINCT ds.id) - COUNT(DISTINCT t.id)) AS missed,
                    COALESCE(p.avg_time, 0) AS avg_time_minutes,
                    COALESCE(p.total_time, 0) AS total_time_minutes,
                    COALESCE(AVG(t.score), 0) AS avg_score,
                    COALESCE(AVG(t.score), 0)
                        - (COALESCE(p.avg_time, 0) * 1)
                        - ((COUNT(DISTINCT ds.id) - COUNT(DISTINCT t.id)) * 20) AS final_score
                FROM bt_3_daily_sentences ds
                LEFT JOIN bt_3_translations t
                    ON ds.user_id = t.user_id
                    AND ds.id = t.sentence_id
                LEFT JOIN (
                    SELECT user_id,
                        AVG(EXTRACT(EPOCH FROM (end_time - start_time))/60) AS avg_time,
                        SUM(EXTRACT(EPOCH FROM (end_time - start_time))/60) AS total_time
                    FROM bt_3_user_progress
                    WHERE completed = TRUE
                        AND start_time::date = CURRENT_DATE
                    GROUP BY user_id
                ) p ON ds.user_id = p.user_id
                WHERE ds.date = CURRENT_DATE AND ds.user_id = %s
                GROUP BY ds.user_id, p.avg_time, p.total_time;
                """,
                (user_id,),
            )
            row = cursor.fetchone()

    if not row:
        return None

    total_sentences, translated, missed, avg_minutes, total_minutes, avg_score, final_score = row
    display_name = username or f"user_{user_id}"

    return (
        f"📊 Итоги пользователя {display_name}:\n"
        f"📜 Всего предложений: {total_sentences}\n"
        f"✅ Переведено: {translated}\n"
        f"🚨 Не переведено: {missed}\n"
        f"⏱ Время среднее: {avg_minutes:.1f} мин\n"
        f"⏱ Время общее: {total_minutes:.1f} мин\n"
        f"🎯 Средняя оценка: {avg_score:.1f}/100\n"
        f"🏆 Итоговый балл: {final_score:.1f}"
    )
