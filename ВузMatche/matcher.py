# matcher.py
"""
Простой алгоритм подбора карточек без ML.
"""
import json
import random
from collections import Counter


WARMUP_SWIPES = 5
TRANSITION_SWIPES = 10


def _safe_json(s: str) -> list:
    """Парсит JSON-строку, возвращает список. При ошибке — пустой список."""
    try:
        return json.loads(s) if s else []
    except Exception:
        return []


def score_program(prog: dict, stats: dict,
                  seen_codes_session: Counter) -> float:
    """Считает вес программы под вкусы пользователя."""
    score = 0.0

    code = prog.get("specialty_code")
    tags = _safe_json(prog.get("tags", "[]"))

    likes_by_code = stats["likes_by_code"]
    dislikes_by_code = stats["dislikes_by_code"]
    likes_by_tag = stats["likes_by_tag"]
    dislikes_by_tag = stats["dislikes_by_tag"]

    if code:
        score += 3.0 * likes_by_code.get(code, 0)
        score -= 3.0 * dislikes_by_code.get(code, 0)

    for t in tags:
        score += 1.0 * likes_by_tag.get(t, 0)
        score -= 1.0 * dislikes_by_tag.get(t, 0)

    # Штраф за переизбыток одного кода в текущей сессии
    if code:
        score -= 1.5 * seen_codes_session.get(code, 0)

    return score


def pick_next_program(candidates: list, stats: dict,
                      seen_codes_session: Counter,
                      swipes_count: int):
    """
    Возвращает одну программу по правилам фазы.
    candidates — уже отфильтрованные (город, экзамены, не свайпали).
    """
    if not candidates:
        return None

    # Фаза 1 — разогрев: случайные из разных кодов
    if swipes_count < WARMUP_SWIPES:
        by_code: dict = {}
        for p in candidates:
            code = p.get("specialty_code") or "unknown"
            by_code.setdefault(code, []).append(p)
        available_codes = [c for c in by_code if c not in seen_codes_session]
        if not available_codes:
            available_codes = list(by_code.keys())
        code = random.choice(available_codes)
        return random.choice(by_code[code])

    # Фаза 2 — переход: смешиваем случайные и по интересам
    if swipes_count < TRANSITION_SWIPES:
        if random.random() < 0.5:
            return random.choice(candidates)

    # Фаза 3 — основная: сортируем по score с шумом
    scored = []
    for p in candidates:
        s = score_program(p, stats, seen_codes_session)
        s += random.uniform(0, 1.5)
        scored.append((s, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:5]
    return random.choice(top)[1]


def filter_for_similar(candidates: list, stats: dict) -> list:
    """
    Программы, похожие на лайкнутые:
    тот же код специальности или пересечение тегов.
    """
    liked_codes = set(stats["likes_by_code"].keys())
    liked_tags = set(stats["likes_by_tag"].keys())

    result = []
    for p in candidates:
        code = p.get("specialty_code")
        tags = set(_safe_json(p.get("tags", "[]")))
        if code in liked_codes or (tags & liked_tags):
            result.append(p)
    return result


def filter_for_other(candidates: list, stats: dict) -> list:
    """
    Программы, НЕ похожие на лайкнутые —
    для расширения кругозора.
    """
    liked_codes = set(stats["likes_by_code"].keys())
    liked_tags = set(stats["likes_by_tag"].keys())

    result = []
    for p in candidates:
        code = p.get("specialty_code")
        tags = set(_safe_json(p.get("tags", "[]")))
        if code not in liked_codes and not (tags & liked_tags):
            result.append(p)
    return result