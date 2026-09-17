# vk_bot_reg.py
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


if __name__ == "__main__":
    main()