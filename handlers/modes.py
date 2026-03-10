"""
Обработчики выбора и подтверждения режима
"""
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import COMMUNICATION_MODES
from models import UserContext
from keyboards import get_mode_selection_keyboard, get_mode_confirmation_keyboard
from formatters import bold
from bot_instance import user_contexts, safe_send_message
from states import TestStates


async def show_mode_selection(callback: CallbackQuery, state: FSMContext):
    """Показывает выбор режима общения"""
    user_id = callback.from_user.id
    data = await state.get_data()
    context = user_contexts.get(user_id)
    
    profile_data = data.get("profile_data", {})
    profile_code = profile_data.get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
    current_mode = context.communication_mode if context else "coach"
    mode_names = {
        "coach": "КОУЧ",
        "psychologist": "ПСИХОЛОГ",
        "trainer": "ТРЕНЕР"
    }
    mode_display = mode_names.get(current_mode, "КОУЧ")
    
    text = f"""
🧠 {bold('ФРЕДИ: ВЫБЕРИТЕ РЕЖИМ')}

Слушай, я могу быть разным. Хочешь конкретики — давай определимся, в каком качестве я сегодня буду полезен.

{bold('Твой профиль:')} {profile_code}
{bold('Сейчас активен:')} {mode_display}

🔮 {bold('КОУЧ')}

Если хочешь, чтобы я помог тебе самому найти решения.

{bold('ЧТО БУДУ ДЕЛАТЬ:')}
Задавать открытые вопросы, отражать твои мысли, направлять. Готовых ответов не дам — ты найдёшь их сам.

{bold('ЧТО ТЫ ПОЛУЧИШЬ:')}
• Жить станет легче — перестанешь закапываться в сомнениях
• Появится больше радости от простых вещей
• Начнёшь замечать возможности вместо проблем
• Перестанешь чувствовать вину за каждый шаг

🧠 {bold('ПСИХОЛОГ')}

Если хочешь копнуть вглубь, разобраться с причинами, а не следствиями.

{bold('ЧТО БУДУ ДЕЛАТЬ:')}
Исследовать твои глубинные паттерны, защитные механизмы, прошлый опыт. Пойдём к корню.

{bold('ЧТО ТЫ ПОЛУЧИШЬ:')}
• Перестанешь реагировать на триггеры — будешь выбирать реакцию сам
• Исчезнут старые сценарии, которые портили жизнь
• Поймёшь, откуда растут ноги у твоих страхов
• Внутри станет легче и спокойнее
• Перестанешь саботировать собственное счастье
• Отношения с собой и другими выйдут на новый уровень

⚡ {bold('ТРЕНЕР')}

Если нужны чёткие инструменты, навыки и результат.

{bold('ЧТО БУДУ ДЕЛАТЬ:')}
Формировать твои поведенческие и мыслительные навыки. Работаю по законам научения: правильные действия закрепляются, ненужные — угасают.

Научу мыслить системно — видеть структуру там, где раньше был хаос. Дам инструменты ТРИЗ, чтобы ты мог находить неочевидные решения.

{bold('ЧТО ТЫ ПОЛУЧИШЬ:')}

{bold('Публичное поведение — то, что видят другие:')}
• Научишься чётко формулировать мысли — тебя будут понимать с полуслова
• Освоишь алгоритмы ведения переговоров и убеждения
• Сформируешь полезные привычки и избавишься от вредных
• Будешь уверенно действовать в стрессовых ситуациях

{bold('Приватное поведение — то, что происходит внутри:')}
• Освоишь алгоритмы мыследеятельности — будешь думать быстрее и чётче
• Научишься выявлять противоречия и находить элегантные решения
• Сможешь управлять своим эмоциональным состоянием
• Создашь внутренние опоры, которые будут работать всегда

👇 {bold('Выбирай, в каком качестве я сегодня работаю:')}
"""
    
    keyboard = get_mode_selection_keyboard()
    
    await safe_send_message(callback.message, text, reply_markup=keyboard, delete_previous=True)
    await state.set_state(TestStates.mode_selection)


async def show_mode_selected(callback: CallbackQuery, state: FSMContext, mode: str):
    """Показывает экран подтверждения выбранного режима"""
    user_id = callback.from_user.id
    data = await state.get_data()
    context = user_contexts.get(user_id)
    user_name = context.name if context and context.name else "друг"
    
    profile_data = data.get("profile_data", {})
    profile_code = profile_data.get('display_name', 'СБ-4_ТФ-4_УБ-4_ЧВ-4')
    
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    # Тексты для разных режимов
    mode_texts = {
        "coach": {
            "title": f"ты выбрал режим: 🔮 КОУЧ",
            "description": "Отлично! Теперь я буду работать в партнёрском стиле — задавать вопросы, отражать твои мысли, помогать тебе самому находить решения.",
            "changes": [
                "Я не буду давать готовых ответов — ты будешь находить их сам",
                "Буду направлять вопросами, а не указаниями",
                "Сфокусируемся на твоих целях и твоём видении"
            ],
            "how_next": "Ты ставишь мне цель — и я просчитываю маршрут из точки А в точку Б. Всё последующее взаимодействие будет определяться тем, куда ты хочешь прийти."
        },
        "psychologist": {
            "title": f"ты выбрал режим: 🧠 ПСИХОЛОГ",
            "description": "Хорошо. Теперь я буду работать в глубинном стиле — исследовать твои паттерны, защитные механизмы, прошлый опыт. Пойдём к корню.",
            "changes": [
                "Будем копать вглубь, а не скользить по поверхности",
                "Сфокусируемся на причинах, а не следствиях",
                "Я буду использовать терапевтические техники"
            ],
            "how_next": "Ты ставишь мне цель — я просчитываю маршрут и определяю места, которые нужно проработать. Точки, где застревают старые сценарии. Узлы, которые держат систему."
        },
        "trainer": {
            "title": f"ты выбрал режим: ⚡ ТРЕНЕР",
            "description": "Отлично! Теперь я буду работать в тренировочном стиле — давать чёткие инструкции, упражнения, ставить дедлайны. Требовать выполнения.",
            "changes": [
                "Буду формировать твои поведенческие и мыслительные навыки",
                "Получишь конкретные инструменты и алгоритмы",
                "Сфокусируемся на действиях и результате"
            ],
            "how_next": "Ты ставишь мне цель — я просчитываю маршрут и составляю список навыков, которые тебе понадобятся. Чему придётся научиться. Какие алгоритмы освоить."
        }
    }
    
    t = mode_texts.get(mode, mode_texts["coach"])
    
    changes_text = "\n".join([f"• {change}" for change in t["changes"]])
    
    full_text = f"""
🧠 {bold('ФРЕДИ: РЕЖИМ ВЫБРАН')}

{user_name}, {bold(t["title"])}

{t["description"]}

{bold('Что меняется:')}
{changes_text}

{bold('Твой профиль:')} {profile_code}

{bold('Как дальше:')}
{t["how_next"]}

👇 {bold(f'С чего начнём, {user_name}?')}
"""
    
    keyboard = get_mode_confirmation_keyboard()
    
    await safe_send_message(callback.message, full_text, reply_markup=keyboard, delete_previous=True)
    await state.set_state(TestStates.results)


async def set_mode_coach(callback: CallbackQuery, state: FSMContext):
    """Устанавливает режим КОУЧ"""
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    
    if context:
        context.communication_mode = "coach"
    
    await state.update_data(communication_mode="coach")
    await callback.answer("✅ Режим КОУЧ активирован")
    await show_mode_selected(callback, state, "coach")


async def set_mode_psychologist(callback: CallbackQuery, state: FSMContext):
    """Устанавливает режим ПСИХОЛОГ"""
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    
    if context:
        context.communication_mode = "psychologist"
    
    await state.update_data(communication_mode="psychologist")
    await callback.answer("✅ Режим ПСИХОЛОГ активирован")
    await show_mode_selected(callback, state, "psychologist")


async def set_mode_trainer(callback: CallbackQuery, state: FSMContext):
    """Устанавливает режим ТРЕНЕР"""
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    
    if context:
        context.communication_mode = "trainer"
    
    await state.update_data(communication_mode="trainer")
    await callback.answer("✅ Режим ТРЕНЕР активирован")
    await show_mode_selected(callback, state, "trainer")


async def choose_mode(callback: CallbackQuery, state: FSMContext, mode: str):
    """Выбор режима общения"""
    user_id = callback.from_user.id
    
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
    
    mode_map = {
        "hard": "trainer",
        "medium": "coach",
        "soft": "psychologist"
    }
    new_mode = mode_map.get(mode, mode)
    
    user_contexts[user_id].communication_mode = new_mode
    mode_info = COMMUNICATION_MODES[new_mode]
    
    await safe_send_message(
        callback.message,
        f"{mode_info['emoji']} {bold(f'Режим выбран: {mode_info["display_name"]}')}\n\n"
        f"{mode_info['responsibility']}\n\n"
        f"Теперь давайте познакомимся поближе.",
        delete_previous=True
    )
    
    await asyncio.sleep(1)
    
    context = user_contexts[user_id]
    if not (context.city and context.gender and context.age):
        from .context import start_context
        await start_context(callback, state)
    else:
        intro_text = f"""
🧠 {bold('ВИРТУАЛЬНЫЙ ПСИХОЛОГ')}

🔍 {bold('5 ЭТАПОВ ТЕСТИРОВАНИЯ:')}

ЭТАП 1: Конфигурация восприятия
ЭТАП 2: Конфигурация мышления
ЭТАП 3: Конфигурация поведения
ЭТАП 4: Точка роста
ЭТАП 5: Глубинные паттерны

⏱ {bold('Всего 15 минут')}

👇 {bold('Начинаем?')}
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 НАЧАТЬ ТЕСТ", callback_data="show_stage_1_intro")]
        ])
        
        await callback.message.answer(intro_text, reply_markup=keyboard)


async def back_to_mode_selected(callback: CallbackQuery, state: FSMContext):
    """Возврат к экрану выбранного режима"""
    data = await state.get_data()
    mode = data.get("communication_mode", "coach")
    await show_mode_selected(callback, state, mode)


async def show_main_menu(message: Message, context: UserContext):
    """Показывает главное меню до теста"""
    from keyboards import get_main_menu_keyboard
    
    await context.update_weather()
    
    day_context = context.get_day_context()
    
    welcome_text = f"{context.get_greeting(context.name)}\n\n"
    
    if context.weather_cache:
        weather = context.weather_cache
        welcome_text += f"{weather['icon']} {weather['description']}, {weather['temp']}°C\n"
    
    if day_context['is_weekend']:
        welcome_text += f"🏖 Сегодня выходной! Как настроение?\n\n"
    elif 9 <= day_context['hour'] < 18:
        welcome_text += f"💼 Рабочее время. Чем займёмся?\n\n"
    else:
        welcome_text += f"🏡 Личное время. Есть что обсудить?\n\n"
    
    welcome_text += f"👇 {bold('Выберите действие:')}"
    
    keyboard = get_main_menu_keyboard()
    
    await safe_send_message(message, welcome_text, reply_markup=keyboard)


async def show_main_menu_after_mode(message: Message, context: UserContext):
    """Показывает главное меню после выбора режима"""
    from keyboards import get_main_menu_after_mode_keyboard
    
    mode_config = COMMUNICATION_MODES.get(context.communication_mode, COMMUNICATION_MODES["coach"])
    
    await context.update_weather()
    day_context = context.get_day_context()
    
    text = f"{mode_config['emoji']} {bold(f'РЕЖИМ {mode_config["display_name"]}')}\n\n"
    text += context.get_greeting(context.name) + "\n"
    text += f"📅 Сегодня {day_context['weekday']}, {day_context['day']} {day_context['month']}, {day_context['time_str']}\n"
    
    if context.weather_cache:
        weather = context.weather_cache
        text += f"{weather['icon']} {weather['description']}, {weather['temp']}°C\n\n"
    
    text += f"🧠 {bold('ЧЕМ ЗАЙМЁМСЯ?')}\n\n"
    
    if context.communication_mode == "coach":
        text += "• Задать вопрос — я помогу найти ответ внутри себя\n"
    elif context.communication_mode == "psychologist":
        text += "• Расскажите, что у вас на душе — я помогу исследовать глубинные паттерны\n"
    elif context.communication_mode == "trainer":
        text += "• Поставьте задачу — я дам конкретные шаги\n"
    
    text += "• Выбрать тему — отношения, деньги, самоощущение\n"
    text += "• Послушать сказку — для глубокой работы\n"
    text += "• Посмотреть портрет — напомнить себе, кто вы"
    
    keyboard = get_main_menu_after_mode_keyboard()
    
    await safe_send_message(message, text, reply_markup=keyboard)
