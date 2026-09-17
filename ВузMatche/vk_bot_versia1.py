import json
import random
from collections import Counter

import matcher

import logging

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

from config import VK_TOKEN, VK_GROUP_ID
import db

# ==========================================================
# ЛОГИРОВАНИЕ
# ==========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

# ==========================================================
# ИНИЦИАЛИЗАЦИЯ
# ==========================================================
vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, VK_GROUP_ID)

# FSM в памяти: states[user_id] = {"state": "...", "data": {...}}
states: dict = {}

def tinder_keyboard() -> str:
    kb = VkKeyboard(one_time=False)
    kb.add_button("❤️ Нравится", color=VkKeyboardColor.POSITIVE)
    kb.add_button("👎 Не нравится", color=VkKeyboardColor.NEGATIVE)
    kb.add_line()
    kb.add_button("ℹ️ Подробнее", color=VkKeyboardColor.PRIMARY)
    kb.add_button("⬅️ Отменить", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("🚪 Завершить", color=VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()


def tinder_finish_keyboard() -> str:
    kb = VkKeyboard(one_time=False)
    kb.add_button("⭐ Мои рекомендации", color=VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("❤️ Избранное", color=VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("🔍 Похожие на мои выборы", color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("🌍 Другие направления", color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("🏠 В меню", color=VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()



def format_card(prog: dict) -> str:
    """Короткая карточка для ленты."""
    lines = [f"🎓 {prog['title']}"]
    if prog.get("specialization"):
        lines.append(f"📌 Профиль: {prog['specialization']}")
    if prog.get("specialty_code"):
        lines.append(f"🔖 Код: {prog['specialty_code']}")
    lines.append(f"🏛 {prog['university']}")
    lines.append(f"📍 {prog['city']}")

    exams = prog.get("exams")
    if exams is None:
        exams = db.get_program_exams(prog["id"])
    if exams:
        lines.append(f"📚 ЕГЭ: {', '.join(exam_name(e) for e in exams)}")

    if prog.get("budget_places"):
        lines.append(f"💰 Бюджет: {prog['budget_places']} мест")
    if prog.get("paid_cost"):
        lines.append(f"💵 Платно: {prog['paid_cost']:,} ₽/год".replace(",", " "))
    if prog.get("duration_years"):
        lines.append(f"⏳ {prog['duration_years']} года")

    return "\n".join(lines)


def format_card_details(prog: dict) -> str:
    """Расширенная карточка."""
    parts = [format_card(prog)]
    if prog.get("short_description"):
        parts.append(f"\n📝 {prog['short_description']}")
    if prog.get("description"):
        parts.append(f"\n{prog['description']}")
    if prog.get("url"):
        parts.append(f"\n🔗 {prog['url']}")
    return "\n".join(parts)

# ==========================================================
# СПРАВОЧНИКИ
# ==========================================================
EXAMS = [
    ("Русский язык", "russian"),
    ("Математика (профиль)", "math"),
    ("Физика", "physics"),
    ("Химия", "chemistry"),
    ("Информатика", "informatics"),
    ("Биология", "biology"),
    ("История", "history"),
    ("Обществознание", "social"),
    ("Английский язык", "english"),
    ("Литература", "literature"),
    ("География", "geography"),
]

STUDY_FORMS = {
    "full": "Очная",
    "part": "Очно-заочная",
    "corr": "Заочная",
    "any": "Не важно",
}

STUDY_FORM_BY_NAME = {
    "Очная": "full",
    "Очно-заочная": "part",
    "Заочная": "corr",
    "Не важно": "any",
}

PAYMENTS = {
    "budget": "Бюджет",
    "paid": "Платно",
    "any": "Оба варианта",
}

PAYMENT_BY_NAME = {
    "Бюджет": "budget",
    "Платно": "paid",
    "Оба варианта": "any",
}


def exam_name(code: str) -> str:
    return next((n for n, c in EXAMS if c == code), code)


# ==========================================================
# ОТПРАВКА СООБЩЕНИЙ
# ==========================================================
def send_message(user_id: int, text: str, keyboard: str = None):
    params = {
        "user_id": user_id,
        "message": text,
        "random_id": get_random_id(),
    }
    if keyboard is not None:
        params["keyboard"] = keyboard
    try:
        vk.messages.send(**params)
    except Exception as e:
        log.error(f"Ошибка отправки сообщения {user_id}: {e}")


# ==========================================================
# КЛАВИАТУРЫ
# ==========================================================
def main_keyboard() -> str:
    kb = VkKeyboard(one_time=False)
    kb.add_button("👤 Профиль", color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("✏️ Изменить данные", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("❤️ Перейти к подбору", color=VkKeyboardColor.POSITIVE)
    return kb.get_keyboard()


def welcome_keyboard() -> str:
    """Для существующего пользователя."""
    kb = VkKeyboard(one_time=False)
    kb.add_button("✏️ Изменить данные", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("❤️ Перейти к подбору", color=VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("👤 Профиль", color=VkKeyboardColor.PRIMARY)
    return kb.get_keyboard()


def exams_reply_kb() -> str:
    """Reply-клавиатура с номерами экзаменов (1..11) + Готово."""
    kb = VkKeyboard(one_time=False)
    for i, (name, code) in enumerate(EXAMS):
        kb.add_button(str(i + 1), color=VkKeyboardColor.SECONDARY)
        if i % 4 == 3:
            kb.add_line()
    if len(EXAMS) % 4 != 0:
        kb.add_line()
    kb.add_button("Готово ✅", color=VkKeyboardColor.POSITIVE)
    return kb.get_keyboard()


def study_reply_kb() -> str:
    kb = VkKeyboard(one_time=False)
    kb.add_button("Очная", color=VkKeyboardColor.PRIMARY)
    kb.add_button("Очно-заочная", color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("Заочная", color=VkKeyboardColor.PRIMARY)
    kb.add_button("Не важно", color=VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()


def payment_reply_kb() -> str:
    kb = VkKeyboard(one_time=False)
    kb.add_button("Бюджет", color=VkKeyboardColor.POSITIVE)
    kb.add_button("Платно", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("Оба варианта", color=VkKeyboardColor.PRIMARY)
    return kb.get_keyboard()


def edit_menu_reply_kb() -> str:
    """Меню редактирования на reply-кнопках."""
    kb = VkKeyboard(one_time=False)
    kb.add_button("🏙 Город", color=VkKeyboardColor.PRIMARY)
    kb.add_button("📚 Экзамены", color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("🎓 Форма обучения", color=VkKeyboardColor.PRIMARY)
    kb.add_button("💰 Финансирование", color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("🔄 Пройти опрос заново", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("🔙 Отмена", color=VkKeyboardColor.NEGATIVE)
    return kb.get_keyboard()


# ==========================================================
# ТЕКСТЫ
# ==========================================================
def exams_list_text(selected: list) -> str:
    lines = ["📚 Выбери экзамены, которые ты сдавал(а).\n",
             "Нажимай на номера, чтобы отметить или снять отметку.\n"]
    for i, (name, code) in enumerate(EXAMS, 1):
        mark = "✅" if code in selected else "▫️"
        lines.append(f"{mark} {i}. {name}")
    lines.append(f"\nВыбрано: {len(selected)}")
    lines.append("Когда закончишь — нажми «Готово ✅».")
    return "\n".join(lines)


def profile_text(user: dict) -> str:
    exams = user.get("exams", [])
    exams_text = ", ".join(exam_name(c) for c in exams) if exams else "—"
    return (
        f"👤 Твой профиль\n\n"
        f"🏙 Город: {user.get('city') or '—'}\n"
        f"📚 Экзамены: {exams_text}\n"
        f"💰 Финансирование: {PAYMENTS.get(user.get('budget'), '—')}\n"
    )


# ==========================================================
# ОНБОРДИНГ
# ==========================================================
def start_registration(user_id: int, user_name: str):
    states[user_id] = {"state": "reg_city", "data": {"selected_exams": []}}
    send_message(
        user_id,
        f"Привет, {user_name}! 👋\n\n"
        f"Давай познакомимся и подберём направление 🎓\n\n"
        f"🏙 В каком городе ты ищешь вуз?",
    )


def handle_reg_city(user_id: int, text: str):
    city = text.strip()
    if len(city) < 2:
        send_message(user_id, "Напиши, пожалуйста, название города.")
        return
    st = states[user_id]
    st["data"]["city"] = city
    st["data"]["selected_exams"] = []
    st["state"] = "reg_exams"
    send_message(
        user_id,
        exams_list_text([]),
        keyboard=exams_reply_kb(),
    )


def handle_reg_exam_text(user_id: int, text: str):
    st = states.get(user_id)
    if not st or st["state"] != "reg_exams":
        return

    selected = st["data"].get("selected_exams", [])

    if text == "Готово ✅":
        if len(selected) < 2:
            send_message(user_id, "Выбери хотя бы 2 экзамена.")
            return
        st["data"]["selected_exams"] = selected
        st["state"] = "reg_study"
        send_message(
            user_id,
            "🎓 Отлично! Теперь выбери форму обучения:",
            keyboard=study_reply_kb(),
        )
        return

    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(EXAMS):
            name, code = EXAMS[idx]
            if code in selected:
                selected.remove(code)
                prefix = f"➖ {name} убран"
            else:
                selected.append(code)
                prefix = f"✅ {name} добавлен"
            st["data"]["selected_exams"] = selected
            send_message(
                user_id,
                prefix + "\n\n" + exams_list_text(selected),
                keyboard=exams_reply_kb(),
            )
        return

    send_message(user_id, "Нажми номер экзамена или «Готово ✅».")


def handle_reg_study_text(user_id: int, text: str):
    st = states.get(user_id)
    if not st or st["state"] != "reg_study":
        return
    code = STUDY_FORM_BY_NAME.get(text)
    if not code:
        send_message(user_id, "Выбери форму обучения кнопками ниже.")
        return
    st["data"]["study_form"] = code
    st["state"] = "reg_payment"
    send_message(
        user_id,
        f"Форма обучения: {STUDY_FORMS[code]}\n\n"
        f"💰 Теперь выбери тип финансирования:",
        keyboard=payment_reply_kb(),
    )


def handle_reg_payment_text(user_id: int, text: str, user_name: str):
    st = states.get(user_id)
    if not st or st["state"] != "reg_payment":
        return
    pay = PAYMENT_BY_NAME.get(text)
    if not pay:
        send_message(user_id, "Выбери вариант финансирования кнопками ниже.")
        return
    data = st["data"]

    # Ищем пользователя в БД
    user = db.get_user(user_id)
    if not user:
        user_id_db = db.create_user(
            vk_id=user_id,
            first_name=user_name,
            username=None,
        )
    else:
        user_id_db = user["id"]

    # Обновляем профиль
    db.update_user_profile(
        user_id=user_id_db,
        city=data["city"],
        level="bachelor",
        budget=pay,
        interests=None,
    )
    db.set_user_exams(user_id_db, data["selected_exams"])

    states.pop(user_id, None)
    send_message(
        user_id,
        "🎉 Профиль сохранён!\n\n"
        "Теперь ты можешь подбирать направления. "
        "Нажми «❤️ Перейти к подбору».",
        keyboard=welcome_keyboard(),
    )


# ==========================================================
# ПРОФИЛЬ
# ==========================================================
def show_profile(user_id: int):
    user = db.get_user(user_id)
    if not user or not user["onboarding_done"]:
        send_message(user_id, "Сначала пройди регистрацию — напиши «Начать».")
        return
    send_message(
        user_id,
        profile_text(user),
        keyboard=main_keyboard(),
    )


# ==========================================================
# РЕДАКТИРОВАНИЕ ПРОФИЛЯ
# ==========================================================
def edit_menu(user_id: int):
    user = db.get_user(user_id)
    if not user or not user["onboarding_done"]:
        send_message(user_id, "Сначала пройди регистрацию.")
        return
    states.pop(user_id, None)
    send_message(
        user_id,
        "✏️ Что хочешь изменить?",
        keyboard=edit_menu_reply_kb(),
    )


def edit_cancel(user_id: int):
    states.pop(user_id, None)
    send_message(user_id, "Ок, ничего не меняем 🙂", keyboard=main_keyboard())


def edit_city_start(user_id: int):
    states[user_id] = {"state": "edit_city", "data": {}}
    send_message(user_id, "🏙 Введи новый город:")


def edit_city_save(user_id: int, text: str):
    city = text.strip()
    if len(city) < 2:
        send_message(user_id, "Напиши, пожалуйста, название города.")
        return
    user = db.get_user(user_id)
    if user:
        db.update_user_city(user["id"], city)
    states.pop(user_id, None)
    send_message(
        user_id,
        f"✅ Город обновлён: {city}",
        keyboard=main_keyboard(),
    )


def edit_exams_start(user_id: int):
    user = db.get_user(user_id)
    current = user.get("exams", []) if user else []
    states[user_id] = {
        "state": "edit_exams",
        "data": {"selected_exams": list(current)},
    }
    send_message(
        user_id,
        "📚 Отметь экзамены заново:\n\n" + exams_list_text(current),
        keyboard=exams_reply_kb(),
    )


def edit_exam_toggle(user_id: int, text: str):
    st = states.get(user_id)
    if not st or st["state"] != "edit_exams":
        return
    selected = st["data"].get("selected_exams", [])

    if text == "Готово ✅":
        if len(selected) < 2:
            send_message(user_id, "Выбери хотя бы 2 экзамена.")
            return
        user = db.get_user(user_id)
        if user:
            db.set_user_exams(user["id"], selected)
        states.pop(user_id, None)
        send_message(
            user_id,
            "✅ Экзамены обновлены.",
            keyboard=main_keyboard(),
        )
        return

    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(EXAMS):
            name, code = EXAMS[idx]
            if code in selected:
                selected.remove(code)
                prefix = f"➖ {name} убран"
            else:
                selected.append(code)
                prefix = f"✅ {name} добавлен"
            st["data"]["selected_exams"] = selected
            send_message(
                user_id,
                prefix + "\n\n" + exams_list_text(selected),
                keyboard=exams_reply_kb(),
            )
        return

    send_message(user_id, "Нажми номер экзамена или «Готово ✅».")


def edit_study_start(user_id: int):
    states[user_id] = {"state": "edit_study", "data": {}}
    send_message(user_id, "🎓 Выбери новую форму обучения:",
                 keyboard=study_reply_kb())


def edit_study_save(user_id: int, text: str):
    st = states.get(user_id)
    if not st or st["state"] != "edit_study":
        return
    code = STUDY_FORM_BY_NAME.get(text)
    if not code:
        send_message(user_id, "Выбери форму обучения кнопками ниже.")
        return
    # В БД отдельного поля под форму нет — просто подтверждаем
    states.pop(user_id, None)
    send_message(
        user_id,
        f"✅ Форма обучения: {STUDY_FORMS[code]}",
        keyboard=main_keyboard(),
    )


def edit_pay_start(user_id: int):
    states[user_id] = {"state": "edit_pay", "data": {}}
    send_message(user_id, "💰 Выбери новый тип финансирования:",
                 keyboard=payment_reply_kb())


def edit_pay_save(user_id: int, text: str):
    st = states.get(user_id)
    if not st or st["state"] != "edit_pay":
        return
    pay = PAYMENT_BY_NAME.get(text)
    if not pay:
        send_message(user_id, "Выбери вариант финансирования кнопками ниже.")
        return
    user = db.get_user(user_id)
    if user:
        db.update_user_budget(user["id"], pay)
    states.pop(user_id, None)
    send_message(
        user_id,
        f"✅ Финансирование: {PAYMENTS[pay]}",
        keyboard=main_keyboard(),
    )


def edit_full_start(user_id: int):
    states[user_id] = {"state": "reg_city", "data": {"selected_exams": []}}
    send_message(
        user_id,
        "🔄 Пройдём опрос заново.\n\n"
        "🏙 В каком городе ты ищешь вуз?",
    )


# ==========================================================
# ТИНДЕР (заглушка)
# ==========================================================
def start_tinder(user_id: int):
    user = db.get_user(user_id)
    if not user or not user["onboarding_done"]:
        send_message(user_id, "Сначала пройди регистрацию.")
        return
    send_message(
        user_id,
        "🔎 Подбор направлений — в разработке.\n"
        "Скоро здесь появится свайп-лента!",
        keyboard=main_keyboard(),
    )


# ==========================================================
# РОУТИНГ
# ==========================================================
def route_message(user_id: int, text: str, user_name: str):
    st = states.get(user_id)
    state = st["state"] if st else None
    text_clean = text.strip()

    # --- FSM по состояниям ---
    if state == "reg_city":
        handle_reg_city(user_id, text_clean)
        return
    if state == "reg_exams":
        handle_reg_exam_text(user_id, text_clean)
        return
    if state == "reg_study":
        handle_reg_study_text(user_id, text_clean)
        return
    if state == "reg_payment":
        handle_reg_payment_text(user_id, text_clean, user_name)
        return
    if state == "edit_city":
        edit_city_save(user_id, text_clean)
        return
    if state == "edit_exams":
        edit_exam_toggle(user_id, text_clean)
        return
    if state == "edit_study":
        edit_study_save(user_id, text_clean)
        return
    if state == "edit_pay":
        edit_pay_save(user_id, text_clean)
        return

    # --- Команды меню ---
    text_lower = text_clean.lower()

    if text_lower in ("начать", "start", "/start", "привет"):
        user = db.get_user(user_id)
        if user and user["onboarding_done"]:
            send_message(
                user_id,
                f"С возвращением, {user_name}! 👋\n\n"
                f"У меня уже есть твои данные:\n\n"
                f"{profile_text(user)}\n"
                f"Что делаем?",
                keyboard=welcome_keyboard(),
            )
        else:
            start_registration(user_id, user_name)
        return

    # --- Кнопки существующего пользователя ---
    if text_clean == "👤 Профиль":
        show_profile(user_id)
        return
    if text_clean == "✏️ Изменить данные":
        edit_menu(user_id)
        return
    if text_clean == "❤️ Перейти к подбору":
        start_tinder(user_id)
        return

    # --- Кнопки меню редактирования ---
    if text_clean == "🏙 Город":
        edit_city_start(user_id)
        return
    if text_clean == "📚 Экзамены":
        edit_exams_start(user_id)
        return
    if text_clean == "🎓 Форма обучения":
        edit_study_start(user_id)
        return
    if text_clean == "💰 Финансирование":
        edit_pay_start(user_id)
        return
    if text_clean == "🔄 Пройти опрос заново":
        edit_full_start(user_id)
        return
    if text_clean == "🔙 Отмена":
        edit_cancel(user_id)
        return

    # --- Фолбэк ---
    send_message(
        user_id,
        "Не понимаю 🤔 Напиши «Начать», чтобы открыть меню.",
    )


# ==========================================================
# ЗАПУСК
# ==========================================================
def main():
    log.info("Бот запущен. Ожидаю сообщения...")
    for event in longpoll.listen():
        try:
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.obj.message
                user_id = msg["from_id"]
                text = msg.get("text", "")
                try:
                    user_info = vk.users.get(user_ids=user_id)[0]
                    user_name = user_info["first_name"]
                except Exception:
                    user_name = "друг"
                log.info(f"[MSG] {user_id}: {text!r}")
                route_message(user_id, text, user_name)

            elif event.type == VkBotEventType.MESSAGE_EVENT:
                # Игнорируем: у нас нет inline-кнопок
                pass

        except Exception as e:
            log.exception(f"Ошибка в обработке события: {e}")


def start_tinder(user_id: int):
    user = db.get_user(user_id)
    if not user or not user["onboarding_done"]:
        send_message(user_id, "Сначала пройди регистрацию.")
        return

    # Загружаем пул кандидатов
    candidates = db.get_candidate_programs(
        user_id=user_id,
        city=user["city"],
        user_exams=user["exams"],
    )
    if not candidates:
        send_message(
            user_id,
            "😔 По твоим критериям не нашлось ни одной программы.\n"
            "Попробуй изменить город или экзамены.",
            keyboard=main_keyboard(),
        )
        return

    # Перемешиваем пул — он будет постепенно «таять» при выборе
    random.shuffle(candidates)

    states[user_id] = {
        "state": "tinder",
        "data": {
            "pool": candidates,        # оставшиеся
            "current": None,            # текущая программа
            "history": [],              # для «Отменить»
            "swipes_count": 0,
            "seen_codes_session": Counter(),
        },
    }
    send_message(user_id, "🔎 Начнём подбор!", keyboard=tinder_keyboard())
    _send_next_card(user_id)


def _send_next_card(user_id: int):
    st = states.get(user_id)
    if not st or st["state"] != "tinder":
        return

    data = st["data"]
    pool = data["pool"]

    if not pool:
        _finish_tinder(user_id, reason="empty")
        return

    stats = db.get_swipes_stats(user_id)
    prog = matcher.pick_next_program(
        candidates=pool,
        stats=stats,
        seen_codes_session=data["seen_codes_session"],
        swipes_count=data["swipes_count"],
    )
    if not prog:
        _finish_tinder(user_id, reason="empty")
        return

    # Убираем из пула, ставим как текущую
    pool.remove(prog)
    data["current"] = prog
    data["history"].append(prog)

    send_message(user_id, format_card(prog), keyboard=tinder_keyboard())


def tinder_like(user_id: int):
    st = states.get(user_id)
    if not st or st["state"] != "tinder":
        return
    prog = st["data"].get("current")
    if not prog:
        return

    db.save_swipe(user_id, prog["id"], "like")
    db.add_to_favorites(user_id, prog["id"])

    st["data"]["swipes_count"] += 1
    code = prog.get("specialty_code") or "unknown"
    st["data"]["seen_codes_session"][code] += 1

    send_message(user_id, f"❤️ Добавлено в избранное: {prog['title']}")
    _send_next_card(user_id)


def tinder_dislike(user_id: int):
    st = states.get(user_id)
    if not st or st["state"] != "tinder":
        return
    prog = st["data"].get("current")
    if not prog:
        return

    db.save_swipe(user_id, prog["id"], "dislike")

    st["data"]["swipes_count"] += 1
    code = prog.get("specialty_code") or "unknown"
    st["data"]["seen_codes_session"][code] += 1

    _send_next_card(user_id)


def tinder_undo(user_id: int):
    st = states.get(user_id)
    if not st or st["state"] != "tinder":
        return
    history = st["data"].get("history", [])
    if len(history) < 2:
        send_message(user_id, "Ты уже в начале списка 🙂")
        return

    # Убираем текущую
    current = history.pop()
    # Возвращаем предыдущую
    prev = history[-1]
    # Откатываем свайп
    db.delete_swipe(user_id, current["id"])
    db.remove_from_favorites(user_id, current["id"])

    st["data"]["current"] = prev
    st["data"]["swipes_count"] = max(0, st["data"]["swipes_count"] - 1)

    send_message(user_id, "↩️ Вернулись к предыдущей:")
    send_message(user_id, format_card(prev), keyboard=tinder_keyboard())


def tinder_more(user_id: int):
    st = states.get(user_id)
    if not st or st["state"] != "tinder":
        return
    prog = st["data"].get("current")
    if not prog:
        return
    send_message(user_id, format_card_details(prog), keyboard=tinder_keyboard())


def _finish_tinder(user_id: int, reason: str = "user"):
    """Завершение сессии тиндера."""
    st = states.get(user_id)
    if st and st["state"] == "tinder":
        swipes = st["data"].get("swipes_count", 0)
    else:
        swipes = 0

    states.pop(user_id, None)

    if reason == "empty":
        text = (
            "🎉 Ты просмотрел все подходящие программы!\n\n"
            f"Свайпов за сессию: {swipes}\n\n"
            "Что дальше?"
        )
    else:
        text = (
            f"🚪 Сессия завершена. Свайпов: {swipes}\n\n"
            "Что дальше?"
        )

    send_message(user_id, text, keyboard=tinder_finish_keyboard())


def tinder_finish(user_id: int):
    _finish_tinder(user_id, reason="user")


# ==========================================================
# ЭКРАНЫ ПОСЛЕ ЗАВЕРШЕНИЯ
# ==========================================================

def show_recommendations(user_id: int):
    """Топ программ по весам — «Мои рекомендации»."""
    user = db.get_user(user_id)
    if not user:
        return
    stats = db.get_swipes_stats(user_id)

    if stats["total_likes"] == 0:
        send_message(
            user_id,
            "🤷 Пока нечего рекомендовать — ты ещё ничего не лайкнул.\n"
            "Пройди подбор, чтобы бот понял твои предпочтения.",
            keyboard=tinder_finish_keyboard(),
        )
        return

    candidates = db.get_candidate_programs(
        user_id=user_id,
        city=user["city"],
        user_exams=user["exams"],
    )
    if not candidates:
        send_message(
            user_id,
            "😔 Больше нет новых программ по твоим критериям.",
            keyboard=tinder_finish_keyboard(),
        )
        return

    # Считаем веса и берём топ-5
    scored = []
    for p in candidates:
        s = matcher.score_program(p, stats, Counter())
        scored.append((s, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:5]

    lines = ["⭐ Мои рекомендации:\n"]
    for i, (s, p) in enumerate(top, 1):
        lines.append(
            f"{i}. 🎓 {p['title']}\n"
            f"   🏛 {p['university']}, {p['city']}\n"
            f"   🔖 {p.get('specialty_code') or '—'}"
        )
    send_message(user_id, "\n".join(lines), keyboard=tinder_finish_keyboard())


def show_favorites(user_id: int):
    favs = db.get_favorites(user_id)
    if not favs:
        send_message(
            user_id,
            "⭐ Избранное пусто. Пройди подбор и лайкни что-нибудь.",
            keyboard=tinder_finish_keyboard(),
        )
        return

    lines = [f"❤️ Избранное ({len(favs)}):\n"]
    for i, p in enumerate(favs, 1):
        lines.append(
            f"{i}. 🎓 {p['title']}\n"
            f"   🏛 {p['university']}, {p['city']}\n"
            f"   🔖 {p.get('specialty_code') or '—'}"
        )
    send_message(user_id, "\n".join(lines), keyboard=tinder_finish_keyboard())


def show_similar(user_id: int):
    """Похожие на лайкнутые — по коду или тегам."""
    user = db.get_user(user_id)
    if not user:
        return
    stats = db.get_swipes_stats(user_id)

    if stats["total_likes"] == 0:
        send_message(
            user_id,
            "Сначала лайкни что-нибудь, чтобы я понял, что тебе нравится.",
            keyboard=tinder_finish_keyboard(),
        )
        return

    candidates = db.get_candidate_programs(
        user_id=user_id,
        city=user["city"],
        user_exams=user["exams"],
    )
    similar = matcher.filter_for_similar(candidates, stats)
    if not similar:
        send_message(
            user_id,
            "🤷 Похожих программ больше не нашлось.",
            keyboard=tinder_finish_keyboard(),
        )
        return

    random.shuffle(similar)
    top = similar[:5]

    lines = ["🔍 Похожие на твои выборы:\n"]
    for i, p in enumerate(top, 1):
        lines.append(
            f"{i}. 🎓 {p['title']}\n"
            f"   🏛 {p['university']}, {p['city']}\n"
            f"   🔖 {p.get('specialty_code') or '—'}"
        )
    send_message(user_id, "\n".join(lines), keyboard=tinder_finish_keyboard())


def show_other(user_id: int):
    """Другие направления — НЕ похожие на лайкнутые."""
    user = db.get_user(user_id)
    if not user:
        return
    stats = db.get_swipes_stats(user_id)

    candidates = db.get_candidate_programs(
        user_id=user_id,
        city=user["city"],
        user_exams=user["exams"],
    )
    other = matcher.filter_for_other(candidates, stats)
    if not other:
        send_message(
            user_id,
            "🌍 Других направлений по твоим критериям не нашлось.",
            keyboard=tinder_finish_keyboard(),
        )
        return

    random.shuffle(other)
    top = other[:5]

    lines = ["🌍 Другие направления (не из твоих выборов):\n"]
    for i, p in enumerate(top, 1):
        lines.append(
            f"{i}. 🎓 {p['title']}\n"
            f"   🏛 {p['university']}, {p['city']}\n"
            f"   🔖 {p.get('specialty_code') or '—'}"
        )
    send_message(user_id, "\n".join(lines), keyboard=tinder_finish_keyboard())

def route_message(user_id: int, text: str, user_name: str):
    st = states.get(user_id)
    state = st["state"] if st else None
    text_clean = text.strip()

    # ======================================================
    # FSM: онбординг и редактирование
    # ======================================================
    if state == "reg_city":
        handle_reg_city(user_id, text_clean)
        return
    if state == "reg_exams":
        handle_reg_exam_text(user_id, text_clean)
        return
    if state == "reg_study":
        handle_reg_study_text(user_id, text_clean)
        return
    if state == "reg_payment":
        handle_reg_payment_text(user_id, text_clean, user_name)
        return
    if state == "edit_city":
        edit_city_save(user_id, text_clean)
        return
    if state == "edit_exams":
        edit_exam_toggle(user_id, text_clean)
        return
    if state == "edit_study":
        edit_study_save(user_id, text_clean)
        return
    if state == "edit_pay":
        edit_pay_save(user_id, text_clean)
        return

    # ======================================================
    # ТИНДЕР (когда пользователь листает карточки)
    # ======================================================
    if state == "tinder":
        if text_clean == "❤️ Нравится":
            tinder_like(user_id)
            return
        if text_clean == "👎 Не нравится":
            tinder_dislike(user_id)
            return
        if text_clean == "ℹ️ Подробнее":
            tinder_more(user_id)
            return
        if text_clean == "⬅️ Отменить":
            tinder_undo(user_id)
            return
        if text_clean == "🚪 Завершить":
            tinder_finish(user_id)
            return
        # Если пользователь написал что-то другое — подсказка
        send_message(
            user_id,
            "Используй кнопки ниже: ❤️ / 👎 / ℹ️ / ⬅️ / 🚪",
            keyboard=tinder_keyboard(),
        )
        return

    # ======================================================
    # ЭКРАНЫ ПОСЛЕ ЗАВЕРШЕНИЯ ТИНДЕРА
    # ======================================================
    if text_clean == "⭐ Мои рекомендации":
        show_recommendations(user_id)
        return
    if text_clean == "❤️ Избранное":
        show_favorites(user_id)
        return
    if text_clean == "🔍 Похожие на мои выборы":
        show_similar(user_id)
        return
    if text_clean == "🌍 Другие направления":
        show_other(user_id)
        return
    if text_clean == "🏠 В меню":
        states.pop(user_id, None)
        send_message(user_id, "Ты в меню.", keyboard=main_keyboard())
        return

    # ======================================================
    # КОМАНДЫ ГЛАВНОГО МЕНЮ
    # ======================================================
    text_lower = text_clean.lower()

    if text_lower in ("начать", "start", "/start", "привет"):
        user = db.get_user(user_id)
        if user and user["onboarding_done"]:
            send_message(
                user_id,
                f"С возвращением, {user_name}! 👋\n\n"
                f"{profile_text(user)}\n"
                f"Что делаем?",
                keyboard=welcome_keyboard(),
            )
        else:
            start_registration(user_id, user_name)
        return

    if text_clean == "👤 Профиль":
        show_profile(user_id)
        return

    if text_clean == "✏️ Изменить данные":
        edit_menu(user_id)
        return

    if text_clean == "❤️ Перейти к подбору":
        start_tinder(user_id)
        return

    # ======================================================
    # МЕНЮ РЕДАКТИРОВАНИЯ
    # ======================================================
    if text_clean == "🏙 Город":
        edit_city_start(user_id)
        return
    if text_clean == "📚 Экзамены":
        edit_exams_start(user_id)
        return
    if text_clean == "🎓 Форма обучения":
        edit_study_start(user_id)
        return
    if text_clean == "💰 Финансирование":
        edit_pay_start(user_id)
        return
    if text_clean == "🔄 Пройти опрос заново":
        edit_full_start(user_id)
        return
    if text_clean == "🔙 Отмена":
        edit_cancel(user_id)
        return

    # ======================================================
    # ФОЛБЭК
    # ======================================================
    send_message(
        user_id,
        "Не понимаю 🤔\n"
        "Напиши «Начать», чтобы открыть меню.",
        keyboard=main_keyboard(),
    )


if __name__ == "__main__":
    main()