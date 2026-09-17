import logging
import time

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

from config import VK_TOKEN, VK_GROUP_ID

# ---------- Логирование ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------- Инициализация ----------
vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, VK_GROUP_ID)

# ---------- "База данных" в памяти ----------
users: dict = {}

# ---------- Свой FSM ----------
# states[user_id] = {"state": "...", "data": {...}}
states: dict = {}

# ---------- Справочники ----------
EXAMS = [
    ("Русский язык", "ru"),
    ("Математика (профиль)", "math"),
    ("Физика", "phys"),
    ("Химия", "chem"),
    ("Информатика", "inf"),
    ("Биология", "bio"),
    ("История", "hist"),
    ("Обществознание", "soc"),
    ("Английский язык", "eng"),
    ("Литература", "lit"),
    ("География", "geo"),
]

STUDY_FORMS = {
    "full": "Очная",
    "part": "Очно-заочная",
    "corr": "Заочная",
    "any": "Не важно",
}

PAYMENTS = {
    "budget": "Бюджет",
    "paid": "Платно",
    "any": "Оба варианта",
}

# ---------- Каталог вузов ----------
VUZ_LIST = [
    {
        "id": 1,
        "name": "МГТУ им. Н.Э. Баумана",
        "program": "Прикладная информатика",
        "city": "Москва",
        "photo": None,
        "exams": ["math", "inf", "ru"],
        "budget_places": 25,
        "paid_price": 320000,
        "min_score": 270,
        "form": "full",
        "years": 4,
        "description": (
            "Одна из ведущих технических школ России. Программа готовит "
            "разработчиков ПО, аналитиков данных и архитекторов информационных "
            "систем. Сильная математическая база и много практики."
        ),
        "url": "https://bmstu.ru",
    },
    {
        "id": 2,
        "name": "МГУ им. М.В. Ломоносова",
        "program": "Прикладная математика и информатика (ВМК)",
        "city": "Москва",
        "photo": None,
        "exams": ["math", "inf", "ru"],
        "budget_places": 30,
        "paid_price": 380000,
        "min_score": 290,
        "form": "full",
        "years": 4,
        "description": (
            "Факультет ВМК — кузница кадров для Яндекса, Сбера и международных "
            "лабораторий. Акцент на алгоритмах, machine learning и "
            "суперкомпьютерных вычислениях."
        ),
        "url": "https://cs.msu.ru",
    },
    {
        "id": 3,
        "name": "НИУ ВШЭ",
        "program": "Программная инженерия",
        "city": "Москва",
        "photo": None,
        "exams": ["math", "inf", "ru"],
        "budget_places": 60,
        "paid_price": 420000,
        "min_score": 285,
        "form": "full",
        "years": 4,
        "description": (
            "Одна из самых сильных программ по разработке ПО в стране. "
            "Проектное обучение с 1 курса, стажировки в крупных IT-компаниях."
        ),
        "url": "https://www.hse.ru",
    },
    {
        "id": 4,
        "name": "МФТИ",
        "program": "Прикладные математика и физика",
        "city": "Долгопрудный",
        "photo": None,
        "exams": ["math", "phys", "ru"],
        "budget_places": 40,
        "paid_price": 400000,
        "min_score": 300,
        "form": "full",
        "years": 4,
        "description": (
            "Легендарный Физтех. Программа для тех, кто хочет заниматься "
            "фундаментальной наукой, физикой и математикой на мировом уровне."
        ),
        "url": "https://mipt.ru",
    },
    {
        "id": 5,
        "name": "Университет ИТМО",
        "program": "Программная инженерия",
        "city": "Санкт-Петербург",
        "photo": None,
        "exams": ["math", "inf", "ru"],
        "budget_places": 50,
        "paid_price": 350000,
        "min_score": 285,
        "form": "full",
        "years": 4,
        "description": (
            "Многократный чемпион мира по программированию (ICPC). "
            "Сильнейшие направления — Computer Science, робототехника, "
            "фотоника и AI."
        ),
        "url": "https://itmo.ru",
    },
    {
        "id": 6,
        "name": "СПбГУ",
        "program": "Прикладная математика и информатика",
        "city": "Санкт-Петербург",
        "photo": None,
        "exams": ["math", "inf", "ru"],
        "budget_places": 30,
        "paid_price": 340000,
        "min_score": 275,
        "form": "full",
        "years": 4,
        "description": (
            "Классический университет с сильной математической школой. "
            "Программа сочетает фундаментальную подготовку и современные "
            "курсы по машинному обучению."
        ),
        "url": "https://spbu.ru",
    },
    {
        "id": 7,
        "name": "НГУ",
        "program": "Физика",
        "city": "Новосибирск",
        "photo": None,
        "exams": ["math", "phys", "ru"],
        "budget_places": 35,
        "paid_price": 180000,
        "min_score": 260,
        "form": "full",
        "years": 4,
        "description": (
            "Новосибирский госуниверситет в Академгородке. Тесная связь с "
            "институтами СО РАН, лучшие условия для научной карьеры."
        ),
        "url": "https://nsu.ru",
    },
    {
        "id": 8,
        "name": "ТГУ",
        "program": "Прикладная информатика",
        "city": "Томск",
        "photo": None,
        "exams": ["math", "inf", "ru"],
        "budget_places": 40,
        "paid_price": 180000,
        "min_score": 240,
        "form": "full",
        "years": 4,
        "description": (
            "Один из старейших университетов Сибири. Программа по прикладной "
            "информатике ориентирована на промышленную разработку и анализ "
            "данных."
        ),
        "url": "https://tsu.ru",
    },
    {
        "id": 9,
        "name": "УрФУ",
        "program": "Информатика и вычислительная техника",
        "city": "Екатеринбург",
        "photo": None,
        "exams": ["math", "inf", "ru"],
        "budget_places": 45,
        "paid_price": 170000,
        "min_score": 235,
        "form": "full",
        "years": 4,
        "description": (
            "Крупнейший вуз Урала. Программа готовит специалистов по "
            "разработке ПО, embedded-системам и кибербезопасности."
        ),
        "url": "https://urfu.ru",
    },
    {
        "id": 10,
        "name": "КФУ",
        "program": "Прикладная информатика",
        "city": "Казань",
        "photo": None,
        "exams": ["math", "inf", "ru"],
        "budget_places": 50,
        "paid_price": 160000,
        "min_score": 230,
        "form": "full",
        "years": 4,
        "description": (
            "Казанский федеральный университет — один из старейших в России. "
            "Сильные партнёрства с IT-компаниями Татарстана."
        ),
        "url": "https://kpfu.ru",
    },
    {
        "id": 11,
        "name": "ДВФУ",
        "program": "Программная инженерия",
        "city": "Владивосток",
        "photo": None,
        "exams": ["math", "inf", "ru"],
        "budget_places": 30,
        "paid_price": 200000,
        "min_score": 225,
        "form": "full",
        "years": 4,
        "description": (
            "Крупнейший университет Дальнего Востока. Кампус на острове "
            "Русский, современные лаборатории и программы обмена с АТР."
        ),
        "url": "https://dvfu.ru",
    },
    {
        "id": 12,
        "name": "РЭУ им. Г.В. Плеханова",
        "program": "Прикладная информатика в экономике",
        "city": "Москва",
        "photo": None,
        "exams": ["math", "inf", "ru"],
        "budget_places": 20,
        "paid_price": 300000,
        "min_score": 250,
        "form": "part",
        "years": 4,
        "description": (
            "Программа на стыке IT и экономики: бизнес-аналитика, "
            "финансовое моделирование, разработка корпоративных систем."
        ),
        "url": "https://rea.ru",
    },
]


# ==========================================================
# УТИЛИТЫ
# ==========================================================

def get_vuz_by_id(vid: int):
    return next((v for v in VUZ_LIST if v["id"] == vid), None)


def exam_name(code: str) -> str:
    return next((n for n, c in EXAMS if c == code), code)


def fmt_price(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def format_vuz_short(v: dict) -> str:
    pay_part = (
        f" / платно: {fmt_price(v['paid_price'])} ₽/год"
        if v["paid_price"] else ""
    )
    return (
        f"🎓 {v['program']}\n"
        f"🏛 {v['name']}\n"
        f"📍 {v['city']}\n"
        f"📚 ЕГЭ: {', '.join(exam_name(e) for e in v['exams'])}\n"
        f"💰 Бюджет: {v['budget_places']} мест{pay_part}\n"
        f"📈 Проходной балл: {v['min_score']}\n"
        f"⏳ Форма: {STUDY_FORMS[v['form']]}, {v['years']} года"
    )


def format_vuz_details(v: dict) -> str:
    return (
        f"📚 ЕГЭ: {', '.join(exam_name(e) for e in v['exams'])}\n"
        f"💰 Бюджет: {v['budget_places']} мест\n"
        f"💵 Платно: {fmt_price(v['paid_price'])} ₽/год\n"
        f"📈 Проходной балл: {v['min_score']}\n"
        f"⏳ Форма: {STUDY_FORMS[v['form']]}, {v['years']} года\n\n"
        f"ℹ️ О программе:\n{v['description']}\n\n"
        f"🔗 {v['url']}"
    )


def match_vuzes(user: dict) -> list:
    user_exams = set(user["exams"])
    user_form = user["study_form"]
    user_pay = user["payment"]
    user_city = user["city"].strip().lower()

    matched = []
    for v in VUZ_LIST:
        if not set(v["exams"]).issubset(user_exams):
            continue
        if user_form != "any" and v["form"] != user_form:
            continue
        if user_pay == "budget" and v["budget_places"] == 0:
            continue
        if user_pay == "paid" and not v["paid_price"]:
            continue
        matched.append(v)

    city_first = [
        v for v in matched if user_city and user_city in v["city"].lower()
    ]
    others = [v for v in matched if v not in city_first]
    return city_first + others


def is_registered(user_id: int) -> bool:
    return user_id in users and users[user_id].get("registered", False)


# ==========================================================
# ОТПРАВКА СООБЩЕНИЙ
# ==========================================================

def send_message(user_id: int, text: str, keyboard: str = None,
                 attachment: str = None):
    """Универсальная отправка сообщения пользователю."""
    params = {
        "user_id": user_id,
        "message": text,
        "random_id": get_random_id(),
    }
    if keyboard is not None:
        params["keyboard"] = keyboard
    if attachment:
        params["attachment"] = attachment
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
    kb.add_button("⭐ Избранное", color=VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("🗑 Исключённые", color=VkKeyboardColor.NEGATIVE)
    kb.add_line()
    kb.add_button("❤️ Выбрать вуз", color=VkKeyboardColor.POSITIVE)
    return kb.get_keyboard()


def tinder_keyboard() -> str:
    kb = VkKeyboard(one_time=False)
    kb.add_button("❤️ Нравится", color=VkKeyboardColor.POSITIVE)
    kb.add_line()
    kb.add_button("👎 Не нравится", color=VkKeyboardColor.NEGATIVE)
    kb.add_line()
    kb.add_button("⬅️ Отменить", color=VkKeyboardColor.SECONDARY)
    kb.add_button("ℹ️ Подробнее", color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("🔙 В меню", color=VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()


# Список экзаменов делим на две страницы
EXAMS_PAGE_1 = EXAMS[:6]   # 6 экзаменов
EXAMS_PAGE_2 = EXAMS[6:]   # 5 экзаменов


def exams_kb_page(selected: list, page: int = 1) -> str:
    """Inline-клавиатура выбора экзаменов. Постранично."""
    kb = VkKeyboard(inline=True)
    items = EXAMS_PAGE_1 if page == 1 else EXAMS_PAGE_2

    for i, (name, code) in enumerate(items):
        mark = "✅ " if code in selected else ""
        kb.add_button(
            f"{mark}{name}",
            color=VkKeyboardColor.PRIMARY,
            payload={"cmd": "exam", "code": code},
        )
        if i % 3 == 2:
            kb.add_line()

    if len(items) % 3 != 0:
        kb.add_line()

    # Навигация
    if page == 1:
        kb.add_button(
            "Дальше ➡️",
            color=VkKeyboardColor.SECONDARY,
            payload={"cmd": "exam", "code": "page2"},
        )
    else:
        kb.add_button(
            "⬅️ Назад",
            color=VkKeyboardColor.SECONDARY,
            payload={"cmd": "exam", "code": "page1"},
        )
        kb.add_button(
            "Готово ✅",
            color=VkKeyboardColor.POSITIVE,
            payload={"cmd": "exam", "code": "done"},
        )

    return kb.get_keyboard()


# Псевдоним для совместимости — используется в edit_exams_start
def exams_kb(selected: list) -> str:
    return exams_kb_page(selected, page=1)


def study_kb() -> str:
    kb = VkKeyboard(inline=True)
    for i, (code, name) in enumerate(STUDY_FORMS.items()):
        kb.add_button(
            name,
            color=VkKeyboardColor.PRIMARY,
            payload={"cmd": "study", "code": code},
        )
        if i % 2 == 1:
            kb.add_line()
    return kb.get_keyboard()


def payment_kb() -> str:
    kb = VkKeyboard(inline=True)
    for i, (code, name) in enumerate(PAYMENTS.items()):
        kb.add_button(
            name,
            color=VkKeyboardColor.PRIMARY,
            payload={"cmd": "pay", "code": code},
        )
        if i % 2 == 1:
            kb.add_line()
    return kb.get_keyboard()


def profile_kb() -> str:
    kb = VkKeyboard(inline=True)
    kb.add_button(
        "✏️ Изменить профиль",
        color=VkKeyboardColor.PRIMARY,
        payload={"cmd": "edit", "code": "menu"},
    )
    return kb.get_keyboard()


def edit_menu_kb() -> str:
    kb = VkKeyboard(inline=True)
    kb.add_button("🏙 Город", color=VkKeyboardColor.PRIMARY,
                  payload={"cmd": "edit", "code": "city"})
    kb.add_line()
    kb.add_button("📚 Экзамены и баллы", color=VkKeyboardColor.PRIMARY,
                  payload={"cmd": "edit", "code": "exams"})
    kb.add_line()
    kb.add_button("🎓 Форма обучения", color=VkKeyboardColor.PRIMARY,
                  payload={"cmd": "edit", "code": "study"})
    kb.add_line()
    kb.add_button("💰 Финансирование", color=VkKeyboardColor.PRIMARY,
                  payload={"cmd": "edit", "code": "pay"})
    kb.add_line()
    kb.add_button("🔄 Пройти опрос заново", color=VkKeyboardColor.SECONDARY,
                  payload={"cmd": "edit", "code": "full"})
    kb.add_line()
    kb.add_button("🔙 Отмена", color=VkKeyboardColor.NEGATIVE,
                  payload={"cmd": "edit", "code": "cancel"})
    return kb.get_keyboard()


def favorites_kb(user_id: int) -> str:
    favs = users[user_id]["favorites"]
    if not favs:
        return None
    kb = VkKeyboard(inline=True)
    for vid in favs:
        v = get_vuz_by_id(vid)
        if v:
            kb.add_button(
                f"👁 {v['name'][:30]}",
                color=VkKeyboardColor.PRIMARY,
                payload={"cmd": "fav_open", "vid": vid},
            )
            kb.add_button(
                "❌",
                color=VkKeyboardColor.NEGATIVE,
                payload={"cmd": "fav_remove", "vid": vid},
            )
            kb.add_line()
    return kb.get_keyboard()


def excluded_kb(user_id: int) -> str:
    exc = users[user_id]["excluded"]
    if not exc:
        return None
    kb = VkKeyboard(inline=True)
    for vid in exc:
        v = get_vuz_by_id(vid)
        if v:
            kb.add_button(
                f"👁 {v['name'][:30]}",
                color=VkKeyboardColor.PRIMARY,
                payload={"cmd": "exc_open", "vid": vid},
            )
            kb.add_button(
                "↩️",
                color=VkKeyboardColor.POSITIVE,
                payload={"cmd": "exc_restore", "vid": vid},
            )
            kb.add_line()
    return kb.get_keyboard()


# ==========================================================
# РЕГИСТРАЦИЯ
# ==========================================================

def start_registration(user_id: int, user_name: str):
    states[user_id] = {"state": "reg_city", "data": {"selected_exams": []}}
    send_message(
        user_id,
        f"Привет, {user_name}! 👋\n\n"
        f"Давай зарегистрируемся и подберём вуз мечты 🎓\n\n"
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
        f"Отлично, {city}! 🏙\n\n"
        f"📚 Выбери экзамены, которые ты сдавал(а).\n"
        f"Нажимай на предметы, чтобы отметить, затем — «Готово».",
        keyboard=exams_kb([]),
    )


def handle_reg_exam(user_id: int, payload: dict):
    st = states.get(user_id)
    if not st or st["state"] != "reg_exams":
        return
    action = payload.get("code")
    selected = st["data"].get("selected_exams", [])

    # Переключение страниц
    if action == "page2":
        send_message(user_id, "Выбери экзамены (стр. 2):",
                     keyboard=exams_kb_page(selected, page=2))
        return
    if action == "page1":
        send_message(user_id, "Выбери экзамены (стр. 1):",
                     keyboard=exams_kb_page(selected, page=1))
        return

    if action == "done":
        if len(selected) < 2:
            send_message(user_id, "Выбери хотя бы 2 экзамена.")
            return
        st["data"]["scores"] = {}
        st["data"]["score_queue"] = list(selected)
        st["data"]["score_index"] = 0
        st["state"] = "reg_scores"
        send_message(
            user_id,
            f"✅ Экзамены выбраны.\n\n"
            f"Введи балл по предмету «{exam_name(selected[0])}» (0–100):",
        )
        return

    # Тоггл экзамена
    if action in selected:
        selected.remove(action)
    else:
        selected.append(action)
    st["data"]["selected_exams"] = selected

    # Возвращаемся на ту же страницу, откуда пришёл клик
    page = 1 if action in dict(EXAMS_PAGE_1).values() else 2
    send_message(user_id, "Отметь экзамены:",
                 keyboard=exams_kb_page(selected, page=page))


def handle_reg_score(user_id: int, text: str):
    st = states.get(user_id)
    if not st or st["state"] != "reg_scores":
        return
    text = text.strip()
    if not text.isdigit() or not (0 <= int(text) <= 100):
        send_message(user_id, "Пожалуйста, введи число от 0 до 100.")
        return
    score = int(text)
    scores = st["data"]["scores"]
    queue = st["data"]["score_queue"]
    idx = st["data"]["score_index"]
    scores[queue[idx]] = score
    idx += 1
    if idx < len(queue):
        st["data"]["score_index"] = idx
        send_message(
            user_id,
            f"Введи балл по предмету «{exam_name(queue[idx])}» (0–100):",
        )
    else:
        st["state"] = "reg_study"
        send_message(
            user_id,
            "🎓 Отлично! Теперь выбери форму обучения:",
            keyboard=study_kb(),
        )


def handle_reg_study(user_id: int, payload: dict):
    st = states.get(user_id)
    if not st or st["state"] != "reg_study":
        return
    form = payload.get("code")
    st["data"]["study_form"] = form
    st["state"] = "reg_payment"
    send_message(
        user_id,
        f"Форма обучения: {STUDY_FORMS[form]}\n\n"
        f"💰 Теперь выбери тип финансирования:",
        keyboard=payment_kb(),
    )


def handle_reg_payment(user_id: int, payload: dict):
    st = states.get(user_id)
    if not st or st["state"] != "reg_payment":
        return
    pay = payload.get("code")
    data = st["data"]
    old = users.get(user_id, {})

    users[user_id] = {
        "user_id": user_id,
        "registered": True,
        "city": data["city"],
        "exams": data["selected_exams"],
        "scores": data["scores"],
        "study_form": data["study_form"],
        "payment": pay,
        "favorites": old.get("favorites", []),
        "excluded": old.get("excluded", []),
        "seen": old.get("seen", set()),
        "last_action": None,
    }

    states.pop(user_id, None)
    send_message(
        user_id,
        "🎉 Регистрация завершена!\n\n"
        "Теперь ты можешь подбирать вузы! Нажми «❤️ Выбрать вуз» в меню.",
        keyboard=main_keyboard(),
    )


# ==========================================================
# ПРОФИЛЬ
# ==========================================================

def show_profile(user_id: int):
    if not is_registered(user_id):
        send_message(user_id, "Сначала пройди регистрацию — напиши «Начать».")
        return
    u = users[user_id]
    scores_lines = "\n".join(
        f"  • {exam_name(code)}: {u['scores'][code]}"
        for code in u["exams"]
    )
    total = sum(u["scores"].values())
    send_message(
        user_id,
        f"👤 Твой профиль\n\n"
        f"🏙 Город: {u['city']}\n"
        f"📚 Экзамены:\n{scores_lines}\n"
        f"🧮 Сумма баллов: {total}\n\n"
        f"🎓 Форма: {STUDY_FORMS[u['study_form']]}\n"
        f"💰 Финансирование: {PAYMENTS[u['payment']]}\n"
        f"⭐ Избранное: {len(u['favorites'])}\n"
        f"🗑 Исключённые: {len(u['excluded'])}",
        keyboard=profile_kb(),
    )


# ==========================================================
# ИЗБРАННОЕ
# ==========================================================

def show_favorites(user_id: int):
    if not is_registered(user_id):
        send_message(user_id, "Сначала пройди регистрацию.")
        return
    states.pop(user_id, None)
    favs = users[user_id]["favorites"]
    if not favs:
        send_message(user_id, "Тут будут твои сохранённые вузы ⭐\nПока пусто.")
        return
    lines = ["⭐ Твои избранные вузы:\n"]
    for i, vid in enumerate(favs, 1):
        v = get_vuz_by_id(vid)
        if v:
            lines.append(
                f"{i}. 🎓 {v['program']}\n"
                f"   🏛 {v['name']}, {v['city']}\n"
                f"   📈 Проходной: {v['min_score']}"
            )
    send_message(
        user_id,
        "\n".join(lines),
        keyboard=favorites_kb(user_id),
    )


def fav_open(user_id: int, vid: int):
    vuz = get_vuz_by_id(vid)
    if not vuz:
        send_message(user_id, "Вуз не найден 🤷")
        return
    send_message(user_id, format_vuz_short(vuz))


def fav_remove(user_id: int, vid: int):
    vuz = get_vuz_by_id(vid)
    if not vuz:
        return
    if vid in users[user_id]["favorites"]:
        users[user_id]["favorites"].remove(vid)
    if vid not in users[user_id]["excluded"]:
        users[user_id]["excluded"].append(vid)
    users[user_id]["seen"].add(vid)
    send_message(
        user_id,
        f"❌ «{vuz['name']}» убран из избранного.\n"
        f"Он перемещён в «🗑 Исключённые».",
    )


# ==========================================================
# ИСКЛЮЧЁННЫЕ
# ==========================================================

def show_excluded(user_id: int):
    if not is_registered(user_id):
        send_message(user_id, "Сначала пройди регистрацию.")
        return
    states.pop(user_id, None)
    exc = users[user_id]["excluded"]
    if not exc:
        send_message(user_id, "Тут пока пусто. Ты никого не исключал 👍")
        return
    lines = ["🗑 Исключённые вузы:\n"]
    for i, vid in enumerate(exc, 1):
        v = get_vuz_by_id(vid)
        if v:
            lines.append(
                f"{i}. 🎓 {v['program']}\n"
                f"   🏛 {v['name']}, {v['city']}\n"
                f"   📈 Проходной: {v['min_score']}"
            )
    send_message(user_id, "\n".join(lines), keyboard=excluded_kb(user_id))


def exc_open(user_id: int, vid: int):
    vuz = get_vuz_by_id(vid)
    if not vuz:
        send_message(user_id, "Вуз не найден 🤷")
        return
    send_message(user_id, format_vuz_short(vuz))


def exc_restore(user_id: int, vid: int):
    vuz = get_vuz_by_id(vid)
    if not vuz:
        return
    if vid in users[user_id]["excluded"]:
        users[user_id]["excluded"].remove(vid)
    users[user_id]["seen"].discard(vid)
    send_message(
        user_id,
        f"↩️ «{vuz['name']}» возвращён в подборку.\n"
        f"Он снова появится в тиндере.",
    )


# ==========================================================
# ТИНДЕР
# ==========================================================

def build_queue(user: dict) -> list:
    matched = match_vuzes(user)
    seen = user.get("seen", set())
    fresh = [v for v in matched if v["id"] not in seen]
    old = [v for v in matched if v["id"] in seen]
    return fresh + old


def send_next_vuz(user_id: int):
    st = states.get(user_id)
    if not st or st["state"] != "tinder":
        return
    queue_ids = st["data"].get("queue", [])
    idx = st["data"].get("index", 0)

    if idx >= len(queue_ids):
        send_message(
            user_id,
            "Пока это все вузы, которые подходят под твои критерии 🎉\n"
            "Загляни в «⭐ Избранное» или измени фильтры.",
            keyboard=main_keyboard(),
        )
        states.pop(user_id, None)
        return

    vuz = get_vuz_by_id(queue_ids[idx])
    if not vuz:
        st["data"]["index"] = idx + 1
        send_next_vuz(user_id)
        return

    send_message(user_id, format_vuz_short(vuz))


def start_tinder(user_id: int):
    if not is_registered(user_id):
        send_message(user_id, "Сначала пройди регистрацию.")
        return
    user = users[user_id]
    queue = build_queue(user)
    if not queue:
        send_message(
            user_id,
            "По твоим фильтрам не нашлось ни одного вуза 😔\n"
            "Попробуй поменять критерии.",
        )
        return
    states[user_id] = {
        "state": "tinder",
        "data": {"queue": [v["id"] for v in queue], "index": 0},
    }
    send_message(user_id, "Начнём поиск! 🔎", keyboard=tinder_keyboard())
    send_next_vuz(user_id)


def tinder_like(user_id: int):
    st = states.get(user_id)
    if not st or st["state"] != "tinder":
        return
    queue_ids = st["data"]["queue"]
    idx = st["data"]["index"]
    if idx < len(queue_ids):
        vid = queue_ids[idx]
        user = users[user_id]
        if vid not in user["favorites"]:
            user["favorites"].append(vid)
        user["seen"].add(vid)
        user["last_action"] = ("like", vid)
    st["data"]["index"] = idx + 1
    send_next_vuz(user_id)


def tinder_dislike(user_id: int):
    st = states.get(user_id)
    if not st or st["state"] != "tinder":
        return
    queue_ids = st["data"]["queue"]
    idx = st["data"]["index"]
    if idx < len(queue_ids):
        vid = queue_ids[idx]
        user = users[user_id]
        user["seen"].add(vid)
        if vid not in user["excluded"]:
            user["excluded"].append(vid)
        user["last_action"] = ("dislike", vid)
    st["data"]["index"] = idx + 1
    send_next_vuz(user_id)


def tinder_undo(user_id: int):
    st = states.get

def tinder_undo(user_id: int):
    st = states.get(user_id)
    if not st or st["state"] != "tinder":
        return
    queue_ids = st["data"]["queue"]
    idx = st["data"]["index"]

    if idx <= 0:
        send_message(user_id, "Ты уже в начале списка 🙂")
        return

    new_idx = idx - 1
    prev_id = queue_ids[new_idx]
    user = users[user_id]
    action = user.get("last_action")

    if action and action[1] == prev_id:
        if action[0] == "like":
            if prev_id in user["favorites"]:
                user["favorites"].remove(prev_id)
        elif action[0] == "dislike":
            if prev_id in user["excluded"]:
                user["excluded"].remove(prev_id)
        user["last_action"] = None

    user["seen"].discard(prev_id)
    st["data"]["index"] = new_idx

    vuz = get_vuz_by_id(prev_id)
    if vuz:
        send_message(user_id, "↩️ Вернулись к предыдущему вузу:")
        send_message(user_id, format_vuz_short(vuz))
    else:
        send_next_vuz(user_id)


def tinder_more(user_id: int):
    st = states.get(user_id)
    if not st or st["state"] != "tinder":
        return
    queue_ids = st["data"]["queue"]
    idx = st["data"]["index"]
    if idx >= len(queue_ids):
        send_message(user_id, "Сейчас нечего показывать 🤷")
        return
    vuz = get_vuz_by_id(queue_ids[idx])
    if not vuz:
        send_message(user_id, "Информация недоступна 🤷")
        return
    send_message(
        user_id,
        f"🎓 {vuz['program']}\n"
        f"🏛 {vuz['name']}\n"
        f"📍 {vuz['city']}\n\n" + format_vuz_details(vuz),
    )


def tinder_menu(user_id: int):
    states.pop(user_id, None)
    send_message(user_id, "Вы в меню.", keyboard=main_keyboard())


# ==========================================================
# РЕДАКТИРОВАНИЕ ПРОФИЛЯ
# ==========================================================

def edit_menu(user_id: int):
    if not is_registered(user_id):
        send_message(user_id, "Сначала пройди регистрацию.")
        return
    states.pop(user_id, None)
    send_message(
        user_id,
        "✏️ Что хочешь изменить?\n\n"
        "Избранное и история просмотров сохранятся.",
        keyboard=edit_menu_kb(),
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
    users[user_id]["city"] = city
    users[user_id]["seen"] = set()
    states.pop(user_id, None)
    send_message(
        user_id,
        f"✅ Город обновлён: {city}\nИстория просмотров сброшена.",
        keyboard=main_keyboard(),
    )


def edit_exams_start(user_id: int):
    states[user_id] = {"state": "edit_exams", "data": {"selected_exams": []}}
    send_message(
        user_id,
        "📚 Выбери экзамены заново и введи баллы:",
        keyboard=exams_kb([]),
    )


def edit_exam_toggle(user_id: int, payload: dict):
    st = states.get(user_id)
    if not st or st["state"] != "edit_exams":
        return
    action = payload.get("code")
    selected = st["data"].get("selected_exams", [])

    if action == "page2":
        send_message(user_id, "Выбери экзамены (стр. 2):",
                     keyboard=exams_kb_page(selected, page=2))
        return
    if action == "page1":
        send_message(user_id, "Выбери экзамены (стр. 1):",
                     keyboard=exams_kb_page(selected, page=1))
        return

    if action == "done":
        if len(selected) < 2:
            send_message(user_id, "Выбери хотя бы 2 экзамена.")
            return
        st["data"]["scores"] = {}
        st["data"]["score_queue"] = list(selected)
        st["data"]["score_index"] = 0
        st["state"] = "edit_scores"
        send_message(
            user_id,
            f"✅ Экзамены обновлены.\n\n"
            f"Введи балл по предмету «{exam_name(selected[0])}» (0–100):",
        )
        return

    if action in selected:
        selected.remove(action)
    else:
        selected.append(action)
    st["data"]["selected_exams"] = selected
    page = 1 if action in dict(EXAMS_PAGE_1).values() else 2
    send_message(user_id, "Отметь экзамены:",
                 keyboard=exams_kb_page(selected, page=page))


def edit_score_save(user_id: int, text: str):
    st = states.get(user_id)
    if not st or st["state"] != "edit_scores":
        return
    text = text.strip()
    if not text.isdigit() or not (0 <= int(text) <= 100):
        send_message(user_id, "Пожалуйста, введи число от 0 до 100.")
        return
    score = int(text)
    scores = st["data"]["scores"]
    queue = st["data"]["score_queue"]
    idx = st["data"]["score_index"]
    scores[queue[idx]] = score
    idx += 1
    if idx < len(queue):
        st["data"]["score_index"] = idx
        send_message(
            user_id,
            f"Введи балл по предмету «{exam_name(queue[idx])}» (0–100):",
        )
        return

    users[user_id]["exams"] = queue
    users[user_id]["scores"] = scores
    users[user_id]["seen"] = set()
    states.pop(user_id, None)
    send_message(
        user_id,
        "✅ Экзамены и баллы обновлены.\nИстория просмотров сброшена.",
        keyboard=main_keyboard(),
    )


def edit_study_start(user_id: int):
    states[user_id] = {"state": "edit_study", "data": {}}
    send_message(user_id, "🎓 Выбери новую форму обучения:", keyboard=study_kb())


def edit_study_save(user_id: int, payload: dict):
    form = payload.get("code")
    users[user_id]["study_form"] = form
    users[user_id]["seen"] = set()
    states.pop(user_id, None)
    send_message(
        user_id,
        f"✅ Форма обучения: {STUDY_FORMS[form]}",
        keyboard=main_keyboard(),
    )


def edit_pay_start(user_id: int):
    states[user_id] = {"state": "edit_pay", "data": {}}
    send_message(user_id, "💰 Выбери новый тип финансирования:", keyboard=payment_kb())


def edit_pay_save(user_id: int, payload: dict):
    pay = payload.get("code")
    users[user_id]["payment"] = pay
    users[user_id]["seen"] = set()
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
        "🔄 Пройдём опрос заново.\n"
        "Избранное и история просмотров сохранятся.\n\n"
        "🏙 В каком городе ты ищешь вуз?",
    )


# ==========================================================
# РОУТИНГ CALLBACK-КНОПОК
# ==========================================================

def handle_callback(user_id: int, payload: dict):
    cmd = payload.get("cmd")
    if cmd == "exam":
        # может быть reg_exams или edit_exams
        st = states.get(user_id)
        if st and st["state"] == "reg_exams":
            handle_reg_exam(user_id, payload)
        elif st and st["state"] == "edit_exams":
            edit_exam_toggle(user_id, payload)
    elif cmd == "study":
        st = states.get(user_id)
        if st and st["state"] == "reg_study":
            handle_reg_study(user_id, payload)
        elif st and st["state"] == "edit_study":
            edit_study_save(user_id, payload)
    elif cmd == "pay":
        st = states.get(user_id)
        if st and st["state"] == "reg_payment":
            handle_reg_payment(user_id, payload)
        elif st and st["state"] == "edit_pay":
            edit_pay_save(user_id, payload)
    elif cmd == "edit":
        code = payload.get("code")
        if code == "menu":
            edit_menu(user_id)
        elif code == "cancel":
            edit_cancel(user_id)
        elif code == "city":
            edit_city_start(user_id)
        elif code == "exams":
            edit_exams_start(user_id)
        elif code == "study":
            edit_study_start(user_id)
        elif code == "pay":
            edit_pay_start(user_id)
        elif code == "full":
            edit_full_start(user_id)
    elif cmd == "fav_open":
        fav_open(user_id, payload["vid"])
    elif cmd == "fav_remove":
        fav_remove(user_id, payload["vid"])
    elif cmd == "exc_open":
        exc_open(user_id, payload["vid"])
    elif cmd == "exc_restore":
        exc_restore(user_id, payload["vid"])


# ==========================================================
# РОУТИНГ ТЕКСТОВЫХ СООБЩЕНИЙ
# ==========================================================

def route_message(user_id: int, text: str, user_name: str):
    st = states.get(user_id)
    state = st["state"] if st else None

    # Сначала — состояния FSM
    if state == "reg_city":
        handle_reg_city(user_id, text)
        return
    if state == "reg_scores":
        handle_reg_score(user_id, text)
        return
    if state == "edit_city":
        edit_city_save(user_id, text)
        return
    if state == "edit_scores":
        edit_score_save(user_id, text)
        return

    # Затем — команды меню
    text_lower = text.strip().lower()

    if text_lower in ("начать", "start", "/start", "привет"):
        if is_registered(user_id):
            send_message(
                user_id,
                f"С возвращением, {user_name}! 👋",
                keyboard=main_keyboard(),
            )
        else:
            start_registration(user_id, user_name)
        return

    if text == "👤 Профиль":
        show_profile(user_id)
        return
    if text == "⭐ Избранное":
        show_favorites(user_id)
        return
    if text == "🗑 Исключённые":
        show_excluded(user_id)
        return
    if text == "❤️ Выбрать вуз":
        start_tinder(user_id)
        return

    # Кнопки тиндера
    if state == "tinder":
        if text == "❤️ Нравится":
            tinder_like(user_id)
            return
        if text == "👎 Не нравится":
            tinder_dislike(user_id)
            return
        if text == "⬅️ Отменить":
            tinder_undo(user_id)
            return
        if text == "ℹ️ Подробнее":
            tinder_more(user_id)
            return
        if text == "🔙 В меню":
            tinder_menu(user_id)
            return

    # Фолбэк
    send_message(user_id, f"Вы написали: {text}")


# ==========================================================
# ЗАПУСК
# ==========================================================

def main():
    log.info("Бот запущен. Ожидаю сообщения...")
    for event in longpoll.listen():
        try:
            # Новое сообщение
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.obj.message
                user_id = msg["from_id"]
                text = msg.get("text", "")
                # Имя пользователя
                try:
                    user_info = vk.users.get(user_ids=user_id)[0]
                    user_name = user_info["first_name"]
                except Exception:
                    user_name = "друг"
                log.info(f"[MSG] {user_id}: {text}")
                route_message(user_id, text, user_name)

            # Нажатие inline-кнопки
            elif event.type == VkBotEventType.MESSAGE_EVENT:
                user_id = event.obj.user_id
                payload = event.obj.payload or {}
                log.info(f"[CB] {user_id}: {payload}")
                # Подтверждаем получение события (убирает «часики»)
                try:
                    vk.messages.sendMessageEventAnswer(
                        event_id=event.obj.event_id,
                        user_id=user_id,
                        peer_id=event.obj.peer_id,
                    )
                except Exception:
                    pass
                handle_callback(user_id, payload)

        except Exception as e:
            log.exception(f"Ошибка в обработке события: {e}")


if __name__ == "__main__":
    main()