import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import BOT_TOKEN

# ---------- Логирование ----------
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- Кэш file_id для фотографий ----------
photo_cache: dict = {}


# ---------- "База данных" в памяти ----------
users: dict = {}


# ---------- FSM ----------
class Registration(StatesGroup):
    city = State()
    exams = State()
    scores = State()
    study_form = State()
    payment = State()


class EditProfile(StatesGroup):
    city = State()
    exams = State()
    scores = State()
    study_form = State()
    payment = State()


class Tinder(StatesGroup):
    active = State()


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
        "photo": (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/"
            "d/d0/Bauman_university.jpg/1280px-Bauman_university.jpg"
        ),
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
        "photo": (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/"
            "a/a5/Moscow_State_University_building.jpg/1280px-"
            "Moscow_State_University_building.jpg"
        ),
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
        "photo": (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/"
            "5/56/HSE_Moscow_building.jpg/1280px-HSE_Moscow_building.jpg"
        ),
        "exams": ["math", "inf", "ru"],
        "budget_places": 60,
        "paid_price": 420000,
        "min_score": 285,
        "form": "full",
        "years": 4,
        "description": (
            "Одна из самых сильных программ по разработке ПО в стране. "
            "Проектное обучение с 1 курса, стажировки в крупных IT-компаниях, "
            "много англоязычных курсов."
        ),
        "url": "https://www.hse.ru",
    },
    {
        "id": 4,
        "name": "МФТИ",
        "program": "Прикладные математика и физика",
        "city": "Долгопрудный",
        "photo": (
            "https://upload.wikimedia.org/wikipedia/commons/6/68/"
            "E7347-MFTI-campus-view.jpg"
        ),
        "exams": ["math", "phys", "ru"],
        "budget_places": 40,
        "paid_price": 400000,
        "min_score": 300,
        "form": "full",
        "years": 4,
        "description": (
            "Легендарный Физтех. Программа для тех, кто хочет заниматься "
            "фундаментальной наукой, физикой и математикой на мировом уровне. "
            "Сотрудничество с РАН и ведущими лабораториями."
        ),
        "url": "https://mipt.ru",
    },
    {
        "id": 5,
        "name": "Университет ИТМО",
        "program": "Программная инженерия",
        "city": "Санкт-Петербург",
        "photo": (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/"
            "4/4e/ITMO_University_building.jpg/1280px-ITMO_University_building.jpg"
        ),
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
        "photo": (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/"
            "8/8e/SPbGU_building.jpg/1280px-SPbGU_building.jpg"
        ),
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
        "photo": (
            "https://upload.wikimedia.org/wikipedia/commons/b/ba/"
            "Старый_копус_НГУ.jpg"
        ),
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
        "photo": (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/"
            "Главный_корпус_ТГУ_зимой.JPG/1280px-Главный_корпус_ТГУ_зимой.JPG"
        ),
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
        "photo": (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/"
            "f/f1/Главный_корпус_УрФУ.jpg/1280px-Главный_корпус_УрФУ.jpg"
        ),
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
        "photo": (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c9/"
            "КФУ_ночью.JPG/1280px-КФУ_ночью.JPG"
        ),
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
        "photo": (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/"
            "8/8d/Кампус_ДВФУ_на_о._Русский.jpg/1280px-"
            "Кампус_ДВФУ_на_о._Русский.jpg"
        ),
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
        "photo": (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/"
            "1/1c/Moscow_Plekhanov_Russian_Economic_University_1_2011.JPG/"
            "1280px-Moscow_Plekhanov_Russian_Economic_University_1_2011.JPG"
        ),
        "exams": ["math", "inf", "ru"],
        "budget_places": 20,
        "paid_price": 300000,
        "min_score": 250,
        "form": "part",
        "years": 4,
        "description": (
            "Программа на стыке IT и экономики: бизнес-аналитика, "
            "финансовое моделирование, разработка корпоративных систем. "
            "Есть очно-заочный формат для совмещения с работой."
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


def vuz_photo(vuz: dict):
    """Возвращает URL фото или None."""
    return vuz.get("photo") or None


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
        f"📚 <b>ЕГЭ:</b> {', '.join(exam_name(e) for e in v['exams'])}\n"
        f"💰 <b>Бюджет:</b> {v['budget_places']} мест\n"
        f"💵 <b>Платно:</b> {fmt_price(v['paid_price'])} ₽/год\n"
        f"📈 <b>Проходной балл:</b> {v['min_score']}\n"
        f"⏳ <b>Форма:</b> {STUDY_FORMS[v['form']]}, {v['years']} года\n\n"
        f"ℹ️ <b>О программе:</b>\n{v['description']}\n\n"
        f"🔗 {v['url']}"
    )


async def send_vuz_photo(target, vuz: dict, caption: str,
                         reply_markup=None, parse_mode=None):
    """Отправляет фото с подписью. Кэш file_id + фолбэк на текст."""
    vid = vuz["id"]

    # 1) file_id в кэше — моментально
    if vid in photo_cache:
        try:
            await target.answer_photo(
                photo_cache[vid], caption=caption,
                reply_markup=reply_markup, parse_mode=parse_mode,
            )
            return
        except Exception as e:
            logging.warning(f"file_id протух для вуза {vid}: {e}")
            photo_cache.pop(vid, None)

    # 2) Грузим по URL
    photo = vuz_photo(vuz)
    if not photo:
        await target.answer(
            caption, reply_markup=reply_markup, parse_mode=parse_mode
        )
        return

    try:
        sent = await target.answer_photo(
            photo, caption=caption,
            reply_markup=reply_markup, parse_mode=parse_mode,
        )
        if sent.photo:
            photo_cache[vid] = sent.photo[-1].file_id
    except Exception as e:
        logging.warning(f"Фото не ушло для вуза {vid}: {e}")
        await target.answer(
            caption, reply_markup=reply_markup, parse_mode=parse_mode
        )


def match_vuzes(user: dict) -> list:
    """Фильтрует каталог под профиль пользователя."""
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


# ---------- Клавиатуры ----------
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="⭐ Избранное")],
        [KeyboardButton(text="🗑 Исключённые")],
        [KeyboardButton(text="❤️ Выбрать вуз")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие...",
)

tinder_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❤️ Нравится")],
        [KeyboardButton(text="👎 Не нравится")],
        [KeyboardButton(text="⬅️ Отменить"), KeyboardButton(text="ℹ️ Подробнее")],
        [KeyboardButton(text="🔙 В меню")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие...",
)


def exams_kb(selected):
    rows = []
    for name, code in EXAMS:
        mark = "✅ " if code in selected else ""
        rows.append(
            [InlineKeyboardButton(
                text=f"{mark}{name}", callback_data=f"exam:{code}"
            )]
        )
    rows.append([InlineKeyboardButton(
        text="Готово ➡️", callback_data="exam:done"
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def study_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"study:{code}")]
        for code, name in STUDY_FORMS.items()
    ])


def payment_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"pay:{code}")]
        for code, name in PAYMENTS.items()
    ])


def profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✏️ Изменить профиль", callback_data="edit:menu"
        )],
    ])


def edit_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏙 Город", callback_data="edit:city")],
        [InlineKeyboardButton(
            text="📚 Экзамены и баллы", callback_data="edit:exams"
        )],
        [InlineKeyboardButton(
            text="🎓 Форма обучения", callback_data="edit:study"
        )],
        [InlineKeyboardButton(
            text="💰 Финансирование", callback_data="edit:pay"
        )],
        [InlineKeyboardButton(
            text="🔄 Пройти опрос заново", callback_data="edit:full"
        )],
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="edit:cancel")],
    ])


def favorites_kb(user_id: int):
    """Инлайн-клавиатура для списка избранного."""
    favs = users[user_id]["favorites"]
    rows = []
    for vid in favs:
        v = get_vuz_by_id(vid)
        if v:
            rows.append([
                InlineKeyboardButton(
                    text=f"👁 {v['name']}", callback_data=f"fav:open:{vid}"
                ),
                InlineKeyboardButton(
                    text="❌", callback_data=f"fav:remove:{vid}"
                ),
            ])
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def excluded_kb(user_id: int):
    """Инлайн-клавиатура для списка исключённых."""
    exc = users[user_id]["excluded"]
    rows = []
    for vid in exc:
        v = get_vuz_by_id(vid)
        if v:
            rows.append([
                InlineKeyboardButton(
                    text=f"👁 {v['name']}", callback_data=f"exc:open:{vid}"
                ),
                InlineKeyboardButton(
                    text="↩️ Вернуть", callback_data=f"exc:restore:{vid}"
                ),
            ])
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


# ==========================================================
# СТАРТ
# ==========================================================

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    if is_registered(message.from_user.id):
        await message.answer(
            f"С возвращением, {message.from_user.full_name}! 👋",
            reply_markup=main_keyboard,
        )
        return

    greeting = (
        f"Привет, {message.from_user.full_name}! 👋\n\n"
        f"Давай зарегистрируемся и подберём вуз мечты 🎓"
    )

    await message.answer(greeting, reply_markup=ReplyKeyboardRemove())
    await message.answer("🏙 В каком городе ты ищешь вуз?")
    await state.set_state(Registration.city)


# ==========================================================
# РЕГИСТРАЦИЯ
# ==========================================================

@dp.message(Registration.city, F.text)
async def reg_city(message: Message, state: FSMContext):
    city = message.text.strip()
    if len(city) < 2:
        await message.answer("Напиши, пожалуйста, название города.")
        return
    await state.update_data(city=city, selected_exams=[])
    await message.answer(
        f"Отлично, {city}! 🏙\n\n"
        f"📚 Выбери экзамены, которые ты сдавал(а).\n"
        f"Нажимай на предметы, чтобы отметить, затем — «Готово».",
        reply_markup=exams_kb([]),
    )
    await state.set_state(Registration.exams)


@dp.callback_query(Registration.exams, F.data.startswith("exam:"))
async def reg_exam_toggle(call: CallbackQuery, state: FSMContext):
    action = call.data.split(":", 1)[1]
    data = await state.get_data()
    selected = data.get("selected_exams", [])

    if action == "done":
        if len(selected) < 2:
            await call.answer("Выбери хотя бы 2 экзамена", show_alert=True)
            return
        await state.update_data(
            scores={}, score_queue=list(selected), score_index=0
        )
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await call.message.answer(
            f"✅ Экзамены выбраны.\n\n"
            f"Введи балл по предмету «{exam_name(selected[0])}» (0–100):"
        )
        await state.set_state(Registration.scores)
        await call.answer()
        return

    if action in selected:
        selected.remove(action)
    else:
        selected.append(action)

    await state.update_data(selected_exams=selected)
    try:
        await call.message.edit_reply_markup(reply_markup=exams_kb(selected))
    except Exception:
        pass
    await call.answer()


@dp.message(Registration.exams)
async def reg_exams_hint(message: Message):
    await message.answer("Выбери экзамены кнопками выше 👆 и нажми «Готово».")


@dp.message(Registration.scores, F.text)
async def reg_score(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or not (0 <= int(text) <= 100):
        await message.answer("Пожалуйста, введи число от 0 до 100.")
        return

    score = int(text)
    data = await state.get_data()
    scores = data.get("scores", {})
    queue = data.get("score_queue", [])
    idx = data.get("score_index", 0)

    scores[queue[idx]] = score
    idx += 1

    if idx < len(queue):
        await state.update_data(scores=scores, score_index=idx)
        await message.answer(
            f"Введи балл по предмету «{exam_name(queue[idx])}» (0–100):"
        )
    else:
        await state.update_data(scores=scores)
        await message.answer(
            "🎓 Отлично! Теперь выбери форму обучения:",
            reply_markup=study_kb(),
        )
        await state.set_state(Registration.study_form)


@dp.callback_query(Registration.study_form, F.data.startswith("study:"))
async def reg_study(call: CallbackQuery, state: FSMContext):
    form = call.data.split(":", 1)[1]
    await state.update_data(study_form=form)
    try:
        await call.message.edit_text(
            f"Форма обучения: <b>{STUDY_FORMS[form]}</b>\n\n"
            f"💰 Теперь выбери тип финансирования:",
            reply_markup=payment_kb(),
            parse_mode="HTML",
        )
    except Exception:
        await call.message.answer(
            "💰 Выбери тип финансирования:",
            reply_markup=payment_kb(),
        )
    await state.set_state(Registration.payment)
    await call.answer()


@dp.message(Registration.study_form)
async def reg_study_hint(message: Message):
    await message.answer("Выбери форму обучения кнопками выше 👆")


@dp.callback_query(Registration.payment, F.data.startswith("pay:"))
async def reg_payment(call: CallbackQuery, state: FSMContext):
    pay = call.data.split(":", 1)[1]
    data = await state.get_data()
    uid = call.from_user.id
    old = users.get(uid, {})

    users[uid] = {
        "user_id": uid,
        "registered": True,
        "city": data["city"],
        "exams": data["selected_exams"],
        "scores": data["scores"],
        "study_form": data["study_form"],
        "payment": pay,
        "favorites": old.get("favorites", []),
        "excluded": old.get("excluded", []),
        "seen": old.get("seen", set()),
        "last_action": None,   # для кнопки "Отменить"
    }

    try:
        await call.message.edit_text("🎉 Регистрация завершена!")
    except Exception:
        pass

    await call.message.answer(
        "Теперь ты можешь подбирать вузы! Нажми «❤️ Выбрать вуз» в меню.",
        reply_markup=main_keyboard,
    )
    await state.clear()
    await call.answer()


@dp.message(Registration.payment)
async def reg_payment_hint(message: Message):
    await message.answer("Выбери вариант финансирования кнопками выше 👆")


# ==========================================================
# ПРОФИЛЬ
# ==========================================================

@dp.message(F.text == "👤 Профиль")
async def show_profile(message: Message):
    uid = message.from_user.id
    if not is_registered(uid):
        await message.answer("Сначала пройди регистрацию командой /start 🙂")
        return

    u = users[uid]
    scores_lines = "\n".join(
        f"  • {exam_name(code)}: <b>{u['scores'][code]}</b>"
        for code in u["exams"]
    )
    total = sum(u["scores"].values())

    await message.answer(
        f"👤 <b>Твой профиль</b>\n\n"
        f"🏙 Город: {u['city']}\n"
        f"📚 Экзамены:\n{scores_lines}\n"
        f"🧮 Сумма баллов: <b>{total}</b>\n\n"
        f"🎓 Форма: {STUDY_FORMS[u['study_form']]}\n"
        f"💰 Финансирование: {PAYMENTS[u['payment']]}\n"
        f"⭐ Избранное: {len(u['favorites'])}\n"
        f"🗑 Исключённые: {len(u['excluded'])}",
        parse_mode="HTML",
        reply_markup=profile_kb(),
    )


# ==========================================================
# ИЗБРАННОЕ
# ==========================================================

@dp.message(F.text == "⭐ Избранное")
async def show_favorites(message: Message, state: FSMContext):
    uid = message.from_user.id
    if not is_registered(uid):
        await message.answer("Сначала пройди регистрацию командой /start 🙂")
        return

    await state.clear()

    favs = users[uid]["favorites"]
    if not favs:
        await message.answer("Тут будут твои сохранённые вузы ⭐\nПока пусто.")
        return

    lines = ["⭐ <b>Твои избранные вузы:</b>\n"]
    for i, vid in enumerate(favs, 1):
        v = get_vuz_by_id(vid)
        if v:
            lines.append(
                f"{i}. 🎓 <b>{v['program']}</b>\n"
                f"   🏛 {v['name']}, {v['city']}\n"
                f"   📈 Проходной: {v['min_score']}"
            )
    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=favorites_kb(uid),
    )


@dp.callback_query(F.data.startswith("fav:open:"))
async def fav_open(call: CallbackQuery):
    vid = int(call.data.split(":")[2])
    vuz = get_vuz_by_id(vid)
    if not vuz:
        await call.answer("Вуз не найден 🤷", show_alert=True)
        return

    await send_vuz_photo(call.message, vuz, format_vuz_short(vuz))
    await call.answer()


@dp.callback_query(F.data.startswith("fav:remove:"))
async def fav_remove(call: CallbackQuery):
    uid = call.from_user.id
    vid = int(call.data.split(":")[2])
    vuz = get_vuz_by_id(vid)

    if vid in users[uid]["favorites"]:
        users[uid]["favorites"].remove(vid)
    # Добавляем в исключённые, чтобы можно было вернуть
    if vid not in users[uid]["excluded"]:
        users[uid]["excluded"].append(vid)
    users[uid]["seen"].add(vid)

    try:
        await call.message.edit_text(
            f"❌ «{vuz['name']}» убран из избранного.\n"
            f"Он перемещён в «🗑 Исключённые».",
        )
    except Exception:
        pass
    await call.answer("Убрано из избранного")


# ==========================================================
# ИСКЛЮЧЁННЫЕ
# ==========================================================

@dp.message(F.text == "🗑 Исключённые")
async def show_excluded(message: Message, state: FSMContext):
    uid = message.from_user.id
    if not is_registered(uid):
        await message.answer("Сначала пройди регистрацию командой /start 🙂")
        return

    await state.clear()

    exc = users[uid]["excluded"]
    if not exc:
        await message.answer("Тут пока пусто. Ты никого не исключал 👍")
        return

    lines = ["🗑 <b>Исключённые вузы:</b>\n"]
    for i, vid in enumerate(exc, 1):
        v = get_vuz_by_id(vid)
        if v:
            lines.append(
                f"{i}. 🎓 <b>{v['program']}</b>\n"
                f"   🏛 {v['name']}, {v['city']}\n"
                f"   📈 Проходной: {v['min_score']}"
            )
    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=excluded_kb(uid),
    )


@dp.callback_query(F.data.startswith("exc:open:"))
async def exc_open(call: CallbackQuery):
    vid = int(call.data.split(":")[2])
    vuz = get_vuz_by_id(vid)
    if not vuz:
        await call.answer("Вуз не найден 🤷", show_alert=True)
        return

    await send_vuz_photo(call.message, vuz, format_vuz_short(vuz))
    await call.answer()


@dp.callback_query(F.data.startswith("exc:restore:"))
async def exc_restore(call: CallbackQuery):
    uid = call.from_user.id
    vid = int(call.data.split(":")[2])
    vuz = get_vuz_by_id(vid)

    if vid in users[uid]["excluded"]:
        users[uid]["excluded"].remove(vid)
    users[uid]["seen"].discard(vid)

    try:
        await call.message.edit_text(
            f"↩️ «{vuz['name']}» возвращён в подборку.\n"
            f"Он снова появится в тиндере.",
        )
    except Exception:
        pass
    await call.answer("Возвращено в подборку")


# ==========================================================
# ТИНДЕР
# ==========================================================

async def build_queue(user: dict) -> list:
    matched = match_vuzes(user)
    seen = user.get("seen", set())
    fresh = [v for v in matched if v["id"] not in seen]
    old = [v for v in matched if v["id"] in seen]
    return fresh + old


async def send_next_vuz(target, state: FSMContext):
    data = await state.get_data()
    queue_ids = data.get("queue", [])
    idx = data.get("index", 0)

    if idx >= len(queue_ids):
        await target.answer(
            "Пока это все вузы, которые подходят под твои критерии 🎉\n"
            "Загляни в «⭐ Избранное» или измени фильтры через /start.",
            reply_markup=main_keyboard,
        )
        await state.clear()
        return

    vuz = get_vuz_by_id(queue_ids[idx])
    if not vuz:
        await state.update_data(index=idx + 1)
        await send_next_vuz(target, state)
        return

    await send_vuz_photo(target, vuz, format_vuz_short(vuz))


@dp.message(F.text == "❤️ Выбрать вуз")
async def start_tinder(message: Message, state: FSMContext):
    uid = message.from_user.id
    if not is_registered(uid):
        await message.answer("Сначала пройди регистрацию командой /start 🙂")
        return

    user = users[uid]
    queue = await build_queue(user)
    if not queue:
        await message.answer(
            "По твоим фильтрам не нашлось ни одного вуза 😔\n"
            "Попробуй поменять критерии — /start."
        )
        return

    await state.set_state(Tinder.active)
    await state.update_data(queue=[v["id"] for v in queue], index=0)
    await message.answer("Начнём поиск! 🔎", reply_markup=tinder_keyboard)
    await send_next_vuz(message, state)


@dp.message(Tinder.active, F.text == "❤️ Нравится")
async def tinder_like(message: Message, state: FSMContext):
    uid = message.from_user.id
    data = await state.get_data()
    queue_ids = data.get("queue", [])
    idx = data.get("index", 0)

    if idx < len(queue_ids):
        vid = queue_ids[idx]
        user = users[uid]
        if vid not in user["favorites"]:
            user["favorites"].append(vid)
        user["seen"].add(vid)
        user["last_action"] = ("like", vid)

    await state.update_data(index=idx + 1)
    await send_next_vuz(message, state)


@dp.message(Tinder.active, F.text == "👎 Не нравится")
async def tinder_dislike(message: Message, state: FSMContext):
    uid = message.from_user.id
    data = await state.get_data()
    queue_ids = data.get("queue", [])
    idx = data.get("index", 0)

    if idx < len(queue_ids):
        vid = queue_ids[idx]
        user = users[uid]
        user["seen"].add(vid)
        if vid not in user["excluded"]:
            user["excluded"].append(vid)
        user["last_action"] = ("dislike", vid)

    await state.update_data(index=idx + 1)
    await send_next_vuz(message, state)


@dp.message(Tinder.active, F.text == "⬅️ Отменить")
async def tinder_undo(message: Message, state: FSMContext):
    uid = message.from_user.id
    data = await state.get_data()
    queue_ids = data.get("queue", [])
    idx = data.get("index", 0)

    if idx <= 0:
        await message.answer("Ты уже в начале списка 🙂")
        return

    new_idx = idx - 1
    prev_id = queue_ids[new_idx]
    user = users[uid]
    action = user.get("last_action")

    # Откатываем последнее действие
    if action and action[1] == prev_id:
        if action[0] == "like":
            if prev_id in user["favorites"]:
                user["favorites"].remove(prev_id)
        elif action[0] == "dislike":
            if prev_id in user["excluded"]:
                user["excluded"].remove(prev_id)
        user["last_action"] = None

    user["seen"].discard(prev_id)

    await state.update_data(index=new_idx)
    vuz = get_vuz_by_id(prev_id)
    if vuz:
        await message.answer("↩️ Вернулись к предыдущему вузу:")
        await send_vuz_photo(message, vuz, format_vuz_short(vuz))
    else:
        await send_next_vuz(message, state)


@dp.message(Tinder.active, F.text == "ℹ️ Подробнее")
async def tinder_more(message: Message, state: FSMContext):
    data = await state.get_data()
    queue_ids = data.get("queue", [])
    idx = data.get("index", 0)

    if idx >= len(queue_ids):
        await message.answer("Сейчас нечего показывать 🤷")
        return

    vuz = get_vuz_by_id(queue_ids[idx])
    if not vuz:
        await message.answer("Информация недоступна 🤷")
        return

    short_caption = (
        f"🎓 <b>{vuz['program']}</b>\n"
        f"🏛 <b>{vuz['name']}</b>\n"
        f"📍 {vuz['city']}"
    )
    details = format_vuz_details(vuz)

    await send_vuz_photo(
        message, vuz, short_caption, parse_mode="HTML"
    )
    await message.answer(details, parse_mode="HTML")


@dp.message(Tinder.active, F.text == "🔙 В меню")
async def tinder_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Вы в меню.", reply_markup=main_keyboard)


# ==========================================================
# РЕДАКТИРОВАНИЕ ПРОФИЛЯ
# ==========================================================

@dp.callback_query(F.data == "edit:menu")
async def edit_menu(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    if not is_registered(uid):
        await call.answer("Сначала пройди регистрацию 🙂", show_alert=True)
        return

    await state.clear()
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await call.message.answer(
        "✏️ Что хочешь изменить?\n\n"
        "<i>Избранное и история просмотров сохранятся.</i>",
        reply_markup=edit_menu_kb(),
        parse_mode="HTML",
    )
    await call.answer()


@dp.callback_query(F.data == "edit:cancel")
async def edit_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await call.message.edit_text("Ок, ничего не меняем 🙂")
    except Exception:
        pass
    await call.message.answer("Ты в меню.", reply_markup=main_keyboard)
    await call.answer()


# ---------- Город ----------
@dp.callback_query(F.data == "edit:city")
async def edit_city_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("🏙 Введи новый город:")
    await state.set_state(EditProfile.city)
    await call.answer()


@dp.message(EditProfile.city, F.text)
async def edit_city_save(message: Message, state: FSMContext):
    city = message.text.strip()
    if len(city) < 2:
        await message.answer("Напиши, пожалуйста, название города.")
        return

    users[message.from_user.id]["city"] = city
    users[message.from_user.id]["seen"] = set()
    await state.clear()
    await message.answer(
        f"✅ Город обновлён: <b>{city}</b>\n"
        f"История просмотров сброшена.",
        reply_markup=main_keyboard,
        parse_mode="HTML",
    )


# ---------- Экзамены ----------
@dp.callback_query(F.data == "edit:exams")
async def edit_exams_start(call: CallbackQuery, state: FSMContext):
    await state.update_data(selected_exams=[])
    await call.message.edit_text(
        "📚 Выбери экзамены заново и введи баллы:",
        reply_markup=exams_kb([]),
    )
    await state.set_state(EditProfile.exams)
    await call.answer()


@dp.callback_query(EditProfile.exams, F.data.startswith("exam:"))
async def edit_exam_toggle(call: CallbackQuery, state: FSMContext):
    action = call.data.split(":", 1)[1]
    data = await state.get_data()
    selected = data.get("selected_exams", [])

    if action == "done":
        if len(selected) < 2:
            await call.answer("Выбери хотя бы 2 экзамена", show_alert=True)
            return
        await state.update_data(
            scores={}, score_queue=list(selected), score_index=0
        )
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await call.message.answer(
            f"✅ Экзамены обновлены.\n\n"
            f"Введи балл по предмету «{exam_name(selected[0])}» (0–100):"
        )
        await state.set_state(EditProfile.scores)
        await call.answer()
        return

    if action in selected:
        selected.remove(action)
    else:
        selected.append(action)

    await state.update_data(selected_exams=selected)
    try:
        await call.message.edit_reply_markup(reply_markup=exams_kb(selected))
    except Exception:
        pass
    await call.answer()


@dp.message(EditProfile.exams)
async def edit_exams_hint(message: Message):
    await message.answer("Выбери экзамены кнопками выше 👆 и нажми «Готово».")


@dp.message(EditProfile.scores, F.text)
async def edit_score_save(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or not (0 <= int(text) <= 100):
        await message.answer("Пожалуйста, введи число от 0 до 100.")
        return

    score = int(text)
    data = await state.get_data()
    scores = data.get("scores", {})
    queue = data.get("score_queue", [])
    idx = data.get("score_index", 0)

    scores[queue[idx]] = score
    idx += 1

    if idx < len(queue):
        await state.update_data(scores=scores, score_index=idx)
        await message.answer(
            f"Введи балл по предмету «{exam_name(queue[idx])}» (0–100):"
        )
        return

    uid = message.from_user.id
    users[uid]["exams"] = queue
    users[uid]["scores"] = scores
    users[uid]["seen"] = set()

    await state.clear()
    await message.answer(
        "✅ Экзамены и баллы обновлены.\n"
        "История просмотров сброшена — в подборке могут появиться новые вузы.",
        reply_markup=main_keyboard,
    )


# ---------- Форма обучения ----------
@dp.callback_query(F.data == "edit:study")
async def edit_study_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "🎓 Выбери новую форму обучения:",
        reply_markup=study_kb(),
    )
    await state.set_state(EditProfile.study_form)
    await call.answer()


@dp.callback_query(EditProfile.study_form, F.data.startswith("study:"))
async def edit_study_save(call: CallbackQuery, state: FSMContext):
    form = call.data.split(":", 1)[1]
    users[call.from_user.id]["study_form"] = form
    users[call.from_user.id]["seen"] = set()

    try:
        await call.message.edit_text(
            f"✅ Форма обучения: <b>{STUDY_FORMS[form]}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await call.message.answer("Готово!", reply_markup=main_keyboard)
    await state.clear()
    await call.answer()


@dp.message(EditProfile.study_form)
async def edit_study_hint(message: Message):
    await message.answer("Выбери форму обучения кнопками выше 👆")


# ---------- Финансирование ----------
@dp.callback_query(F.data == "edit:pay")
async def edit_pay_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "💰 Выбери новый тип финансирования:",
        reply_markup=payment_kb(),
    )
    await state.set_state(EditProfile.payment)
    await call.answer()


@dp.callback_query(EditProfile.payment, F.data.startswith("pay:"))
async def edit_pay_save(call: CallbackQuery, state: FSMContext):
    pay = call.data.split(":", 1)[1]
    users[call.from_user.id]["payment"] = pay
    users[call.from_user.id]["seen"] = set()

    try:
        await call.message.edit_text(
            f"✅ Финансирование: <b>{PAYMENTS[pay]}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await call.message.answer("Готово!", reply_markup=main_keyboard)
    await state.clear()
    await call.answer()


@dp.message(EditProfile.payment)
async def edit_pay_hint(message: Message):
    await message.answer("Выбери вариант финансирования кнопками выше 👆")


# ---------- Пройти заново ----------
@dp.callback_query(F.data == "edit:full")
async def edit_full_start(call: CallbackQuery, state: FSMContext):
    await state.update_data(selected_exams=[])
    try:
        await call.message.edit_text(
            "🔄 Пройдём опрос заново.\n"
            "Избранное и история просмотров сохранятся.\n\n"
            "🏙 В каком городе ты ищешь вуз?"
        )
    except Exception:
        pass
    await state.set_state(Registration.city)
    await call.answer()


# ==========================================================
# ФОЛБЭК
# ==========================================================

@dp.message(F.text)
async def echo(message: Message):
    await message.answer(f"Вы написали: {message.text}")


# ---------- Запуск ----------
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except (KeyboardInterrupt, SystemExit):
            print("Бот остановлен.")
