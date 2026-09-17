# db.py
import logging
import pyodbc

from config_db import DB_CONNECTION_STRING

log = logging.getLogger(__name__)


def get_connection():
    """Возвращает новое соединение с БД."""
    return pyodbc.connect(DB_CONNECTION_STRING, autocommit=True)


# ==========================================================
# ПОЛЬЗОВАТЕЛИ
# ==========================================================

def get_user(vk_id: int) -> dict | None:
    """Возвращает пользователя по vk_id или None."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, vk_id, first_name, username, city, level, budget,
                   interests, onboarding_done, created_at
            FROM dbo.users
            WHERE vk_id = ?
        """, (vk_id,))
        row = cur.fetchone()
        if not row:
            return None
        user = {
            "id": row[0],
            "vk_id": row[1],
            "first_name": row[2],
            "username": row[3],
            "city": row[4],
            "level": row[5],
            "budget": row[6],
            "interests": row[7],
            "onboarding_done": bool(row[8]),
            "created_at": row[9],
        }
        # Подгружаем экзамены и баллы
        user["exams"] = get_user_exams(user["id"])
        user["scores"] = get_user_scores(user["id"])
        return user
    finally:
        conn.close()


def create_user(vk_id: int, first_name: str, username: str = None) -> int:
    """Создаёт пользователя, возвращает его id."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO dbo.users (vk_id, first_name, username, onboarding_done)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, 0)
        """, (vk_id, first_name, username))
        new_id = cur.fetchone()[0]
        log.info(f"Создан пользователь id={new_id} vk_id={vk_id}")
        return new_id
    finally:
        conn.close()


def update_user_profile(user_id: int, city: str, level: str, budget: str,
                        interests: str = None):
    """Обновляет профиль после онбординга."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE dbo.users
            SET city = ?, level = ?, budget = ?, interests = ?,
                onboarding_done = 1
            WHERE id = ?
        """, (city, level, budget, interests, user_id))
    finally:
        conn.close()


def update_user_city(user_id: int, city: str):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE dbo.users SET city = ? WHERE id = ?",
                    (city, user_id))
    finally:
        conn.close()


def update_user_budget(user_id: int, budget: str):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE dbo.users SET budget = ? WHERE id = ?",
                    (budget, user_id))
    finally:
        conn.close()


# ==========================================================
# ЭКЗАМЕНЫ ПОЛЬЗОВАТЕЛЯ
# ==========================================================

def get_exam_id_by_code(code: str) -> int | None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM dbo.exams WHERE code = ?", (code,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def get_user_exams(user_id: int) -> list[str]:
    """Возвращает список кодов экзаменов пользователя."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT e.code
            FROM dbo.user_exams ue
            JOIN dbo.exams e ON e.id = ue.exam_id
            WHERE ue.user_id = ?
        """, (user_id,))
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def set_user_exams(user_id: int, exam_codes: list[str]):
    """Перезаписывает экзамены пользователя."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM dbo.user_exams WHERE user_id = ?", (user_id,))
        for code in exam_codes:
            cur.execute("""
                INSERT INTO dbo.user_exams (user_id, exam_id)
                SELECT ?, id FROM dbo.exams WHERE code = ?
            """, (user_id, code))
    finally:
        conn.close()


# ==========================================================
# БАЛЛЫ ЕГЭ
# ==========================================================
# ВНИМАНИЕ: таблицы user_scores в нашей схеме не было.
# Если вы хотите хранить баллы — нужно добавить её:
#
#   CREATE TABLE dbo.user_scores (
#       user_id INT NOT NULL,
#       exam_id INT NOT NULL,
#       score   INT NOT NULL,
#       PRIMARY KEY (user_id, exam_id),
#       FOREIGN KEY (user_id) REFERENCES dbo.users(id) ON DELETE CASCADE,
#       FOREIGN KEY (exam_id) REFERENCES dbo.exams(id)
#   );
#
# Если баллы пока не нужны — просто не вызывайте эти функции.

def get_user_scores(user_id: int) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT e.code, us.score
            FROM dbo.user_scores us
            JOIN dbo.exams e ON e.id = us.exam_id
            WHERE us.user_id = ?
        """, (user_id,))
        return {row[0]: row[1] for row in cur.fetchall()}
    except Exception:
        # Таблицы может не быть — это ок для MVP
        return {}
    finally:
        conn.close()


def set_user_scores(user_id: int, scores: dict):
    """scores = {"math": 85, "ru": 90}"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM dbo.user_scores WHERE user_id = ?", (user_id,))
        for code, score in scores.items():
            cur.execute("""
                INSERT INTO dbo.user_scores (user_id, exam_id, score)
                SELECT ?, id, ? FROM dbo.exams WHERE code = ?
            """, (user_id, score, code))
    finally:
        conn.close()


# ==========================================================
# ПОДБОР ПРОГРАММ
# ==========================================================

def get_program_by_id(program_id: int) -> dict | None:
    """Возвращает программу со всеми полями для карточки."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                p.id, p.title, p.specialization, p.faculty,
                p.level, p.form, p.duration_years,
                p.budget_places, p.paid_cost,
                p.short_description, p.description, p.tags, p.url,
                s.code AS specialty_code, s.name AS specialty_name,
                u.short_name AS university, u.city
            FROM dbo.programs p
            JOIN dbo.universities u ON u.id = p.university_id
            LEFT JOIN dbo.specialties s ON s.id = p.specialty_id
            WHERE p.id = ? AND p.is_active = 1
        """, (program_id,))
        row = cur.fetchone()
        if not row:
            return None

        prog = {
            "id": row[0],
            "title": row[1],
            "specialization": row[2],
            "faculty": row[3],
            "level": row[4],
            "form": row[5],
            "duration_years": row[6],
            "budget_places": row[7],
            "paid_cost": row[8],
            "short_description": row[9],
            "description": row[10],
            "tags": row[11] or "[]",
            "url": row[12],
            "specialty_code": row[13],
            "specialty_name": row[14],
            "university": row[15],
            "city": row[16],
        }
        prog["exams"] = get_program_exams(program_id)
        return prog
    finally:
        conn.close()


def get_program_exams(program_id: int) -> list[str]:
    """Коды экзаменов программы."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT e.code
            FROM dbo.program_exams pe
            JOIN dbo.exams e ON e.id = pe.exam_id
            WHERE pe.program_id = ?
        """, (program_id,))
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def get_candidate_programs(user_id: int,
                           city: str | None = None,
                           user_exams: list[str] | None = None,
                           limit: int = 200) -> list[dict]:
    """
    Возвращает программы, которые ещё не свайпал пользователь,
    подходящие по городу и экзаменам.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()

        # Собираем SQL динамически
        sql = """
            SELECT
                p.id, p.title, p.specialization,
                s.code AS specialty_code,
                s.name AS specialty_name,
                u.city, u.short_name AS university,
                p.tags
            FROM dbo.programs p
            JOIN dbo.universities u ON u.id = p.university_id
            LEFT JOIN dbo.specialties s ON s.id = p.specialty_id
            WHERE p.is_active = 1
              AND p.id NOT IN (
                  SELECT program_id FROM dbo.swipes
                  WHERE user_id = (SELECT id FROM dbo.users WHERE vk_id = ?)
              )
        """
        params = [user_id]

        if city:
            sql += " AND LOWER(u.city) LIKE ?"
            params.append(f"%{city.lower()}%")

        sql += f" ORDER BY NEWID()"

        cur.execute(sql, params)
        rows = cur.fetchall()
    finally:
        conn.close()

    # Фильтрация по экзаменам в Python (проще, чем SQL-JOIN)
    user_exams_set = set(user_exams or [])
    result = []
    for row in rows:
        prog = {
            "id": row[0],
            "title": row[1],
            "specialization": row[2],
            "specialty_code": row[3],
            "specialty_name": row[4],
            "city": row[5],
            "university": row[6],
            "tags": row[7] or "[]",
        }
        # Проверяем, что все экзамены программы есть у пользователя
        prog_exams = get_program_exams(prog["id"])
        if not set(prog_exams).issubset(user_exams_set):
            continue
        result.append(prog)
        if len(result) >= limit:
            break

    return result


def get_swipes_stats(user_id: int) -> dict:
    """
    Возвращает статистику свайпов:
      likes_by_code: {code: count}
      dislikes_by_code: {code: count}
      likes_by_tag: {tag: count}
      dislikes_by_tag: {tag: count}
      total_likes: int
      total_dislikes: int
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                s.action,
                sp.code AS specialty_code,
                p.tags
            FROM dbo.swipes s
            JOIN dbo.programs p ON p.id = s.program_id
            LEFT JOIN dbo.specialties sp ON sp.id = p.specialty_id
            JOIN dbo.users u ON u.id = s.user_id
            WHERE u.vk_id = ?
        """, (user_id,))
        rows = cur.fetchall()
    finally:
        conn.close()

    import json
    likes_by_code: dict = {}
    dislikes_by_code: dict = {}
    likes_by_tag: dict = {}
    dislikes_by_tag: dict = {}
    total_likes = 0
    total_dislikes = 0

    for action, code, tags_json in rows:
        try:
            tags = json.loads(tags_json) if tags_json else []
        except Exception:
            tags = []

        if action == "like":
            total_likes += 1
            if code:
                likes_by_code[code] = likes_by_code.get(code, 0) + 1
            for t in tags:
                likes_by_tag[t] = likes_by_tag.get(t, 0) + 1
        elif action == "dislike":
            total_dislikes += 1
            if code:
                dislikes_by_code[code] = dislikes_by_code.get(code, 0) + 1
            for t in tags:
                dislikes_by_tag[t] = dislikes_by_tag.get(t, 0) + 1

    return {
        "likes_by_code": likes_by_code,
        "dislikes_by_code": dislikes_by_code,
        "likes_by_tag": likes_by_tag,
        "dislikes_by_tag": dislikes_by_tag,
        "total_likes": total_likes,
        "total_dislikes": total_dislikes,
    }


def get_favorites(user_id: int) -> list[dict]:
    """Список избранного для отображения."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.id, p.title, p.specialization,
                   u.short_name AS university, u.city,
                   s.code AS specialty_code
            FROM dbo.favorites f
            JOIN dbo.programs p ON p.id = f.program_id
            JOIN dbo.universities u ON u.id = p.university_id
            LEFT JOIN dbo.specialties s ON s.id = p.specialty_id
            JOIN dbo.users us ON us.id = f.user_id
            WHERE us.vk_id = ?
            ORDER BY f.created_at DESC
        """, (user_id,))
        return [
            {
                "id": r[0], "title": r[1], "specialization": r[2],
                "university": r[3], "city": r[4], "specialty_code": r[5],
            }
            for r in cur.fetchall()
        ]
    finally:
        conn.close()


def save_swipe(user_id: int, program_id: int, action: str):
    """Записывает свайп. action: 'like' / 'dislike'."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        # Находим внутренний id пользователя
        cur.execute("SELECT id FROM dbo.users WHERE vk_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            return
        user_id_db = row[0]

        # INSERT если ещё нет, иначе UPDATE
        cur.execute("""
            IF EXISTS (SELECT 1 FROM dbo.swipes
                       WHERE user_id = ? AND program_id = ?)
                UPDATE dbo.swipes SET action = ?
                WHERE user_id = ? AND program_id = ?
            ELSE
                INSERT INTO dbo.swipes (user_id, program_id, action)
                VALUES (?, ?, ?)
        """, (user_id_db, program_id, action,
              user_id_db, program_id,
              user_id_db, program_id, action))
    finally:
        conn.close()


def add_to_favorites(user_id: int, program_id: int):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM dbo.users WHERE vk_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            return
        user_id_db = row[0]
        cur.execute("""
            IF NOT EXISTS (SELECT 1 FROM dbo.favorites
                           WHERE user_id = ? AND program_id = ?)
                INSERT INTO dbo.favorites (user_id, program_id)
                VALUES (?, ?)
        """, (user_id_db, program_id, user_id_db, program_id))
    finally:
        conn.close()


def remove_from_favorites(user_id: int, program_id: int):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM dbo.users WHERE vk_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            return
        user_id_db = row[0]
        cur.execute("""
            DELETE FROM dbo.favorites
            WHERE user_id = ? AND program_id = ?
        """, (user_id_db, program_id))
    finally:
        conn.close()


def delete_swipe(user_id: int, program_id: int):
    """Удаляет свайп — для кнопки «Отменить»."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM dbo.users WHERE vk_id = ?", (user_id,))
        row = cur.fetchone()
        if not row:
            return
        user_id_db = row[0]
        cur.execute("""
            DELETE FROM dbo.swipes
            WHERE user_id = ? AND program_id = ?
        """, (user_id_db, program_id))
    finally:
        conn.close()