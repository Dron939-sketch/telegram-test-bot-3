"""
Variatica Bot - для aiogram 3.x
С определением пола, гендерными вопросами и отдельными интерпретациями
"""

import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
from interpretations import get_interpretation, NARRATIVE_NAMES

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Проверь переменные окружения")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==================== СОСТОЯНИЯ ====================

class UserState(StatesGroup):
    gender = State()               # Пол
    block1_question = State()       # Индекс вопроса блока 1
    block1_excludes = State()       # Исключённые нарративы
    narrative = State()             # Основной нарратив
    second_narrative = State()      # Второй нарратив
    block2_question = State()       # Индекс вопроса блока 2
    block2_resources = State()      # Собранные ресурсы

# ==================== ВОПРОСЫ ====================

# Вопрос 0: Определение пола
GENDER_QUESTION = {
    "text": "Для точного определения стратегии мне нужно знать твой пол",
    "options": {
        "М": {"text": "👨 Мужской", "gender": "М"},
        "Ж": {"text": "👩 Женский", "gender": "Ж"}
    }
}

# Блок 1: 8 вопросов для определения нарратива (метод исключения)
QUESTIONS_BLOCK1 = [
    {
        "text": "Какой отдых ты предпочитаешь?",
        "options": {
            "🔱": {"text": "Активный, соревновательный, спорт", "exclude": "ЧВ"},
            "🔨": {"text": "Созидательный — что-то сделать своими руками", "exclude": "СБ"},
            "📚": {"text": "Интеллектуальный — книги, головоломки", "exclude": "ТФ"},
            "🎭": {"text": "Развлекательный — тусовки, мероприятия", "exclude": "УБ"}
        }
    },
    {
        "text": "Что ты ценишь в людях больше всего?",
        "options": {
            "🥊": {"text": "Силу и уверенность", "exclude": "ЧВ"},
            "🛠️": {"text": "Трудолюбие и надёжность", "exclude": "СБ"},
            "📖": {"text": "Ум и глубину", "exclude": "ТФ"},
            "🎉": {"text": "Харизму и обаяние", "exclude": "УБ"}
        }
    },
    {
        "text": "Какая похвала для тебя ценнее?",
        "options": {
            "⚔️": {"text": "«Тебя стоит уважать»", "exclude": "ЧВ"},
            "⚙️": {"text": "«На тебя можно положиться»", "exclude": "СБ"},
            "🔬": {"text": "«Ты очень умный/умная»", "exclude": "ТФ"},
            "🎪": {"text": "«Ты душа компании»", "exclude": "УБ"}
        }
    },
    {
        "text": "В компании незнакомых людей ты сразу...",
        "options": {
            "👑": {"text": "Оцениваешь, кто тут главный", "exclude": "ЧВ"},
            "⏰": {"text": "Ищешь, с кем можно по делу поговорить", "exclude": "СБ"},
            "🤯": {"text": "Прислушиваешься к умным разговорам", "exclude": "ТФ"},
            "👻": {"text": "Смотришь, кто в центре внимания", "exclude": "УБ"}
        }
    },
    {
        "text": "Куда бы ты потратил(а) крупную сумму?",
        "options": {
            "🏛️": {"text": "На статусные вещи (машина, часы)", "exclude": "ЧВ"},
            "🏗️": {"text": "На инструменты, оборудование, свой цех", "exclude": "СБ"},
            "🧠": {"text": "На обучение, книги, исследования", "exclude": "ТФ"},
            "🌟": {"text": "На раскрутку имени, пиар", "exclude": "УБ"}
        }
    },
    {
        "text": "Что тебя бесит больше всего?",
        "options": {
            "💎": {"text": "Неуважение, когда меня не ставят ни во что", "exclude": "ЧВ"},
            "🏭": {"text": "Лень и халява других", "exclude": "СБ"},
            "📚": {"text": "Глупость и нежелание думать", "exclude": "ТФ"},
            "📢": {"text": "Когда меня игнорируют, не замечают", "exclude": "УБ"}
        }
    },
    {
        "text": "Какой подарок тебя порадует больше?",
        "options": {
            "🦁": {"text": "Эксклюзивная вещь, подчёркивающая статус", "exclude": "ЧВ"},
            "🐜": {"text": "Полезный инструмент или техника", "exclude": "СБ"},
            "🦉": {"text": "Редкая книга или доступ к знаниям", "exclude": "ТФ"},
            "🦚": {"text": "Приглашение на закрытое мероприятие", "exclude": "УБ"}
        }
    },
    {
        "text": "Чего ты боишься больше всего?",
        "options": {
            "📉": {"text": "Потерять авторитет, стать никем", "exclude": "ЧВ"},
            "💸": {"text": "Остаться без работы, без денег", "exclude": "СБ"},
            "🤦": {"text": "Показаться глупым/глупой", "exclude": "ТФ"},
            "👀": {"text": "Стать незаметным, скучным", "exclude": "УБ"}
        }
    }
]

# Общие вопросы для всех (5 вопросов)
COMMON_QUESTIONS = [
    {
        "text": "Какой у тебя рост?",
        "options": {
            "1": {"text": "Ниже 165 см", "scores": {"height": 2}},
            "2": {"text": "165-175 см", "scores": {"height": 4}},
            "3": {"text": "175-185 см", "scores": {"height": 6}},
            "4": {"text": "185-195 см", "scores": {"height": 8}},
            "5": {"text": "Выше 195 см", "scores": {"height": 10}}
        }
    },
    {
        "text": "Как часто ты болеешь?",
        "options": {
            "1": {"text": "Постоянно, каждый месяц", "scores": {"health": 2}},
            "2": {"text": "Несколько раз в год", "scores": {"health": 4}},
            "3": {"text": "Раз в год по сезону", "scores": {"health": 6}},
            "4": {"text": "Раз в несколько лет", "scores": {"health": 8}},
            "5": {"text": "Практически никогда", "scores": {"health": 10}}
        }
    },
    {
        "text": "Как ты оцениваешь свою внешность?",
        "options": {
            "1": {"text": "Меня не замечают", "scores": {"attractiveness": 2}},
            "2": {"text": "Обычная внешность", "scores": {"attractiveness": 4}},
            "3": {"text": "Симпатичный(ая)", "scores": {"attractiveness": 6}},
            "4": {"text": "Красивый(ая), привлекаю внимание", "scores": {"attractiveness": 8}},
            "5": {"text": "Модельная внешность", "scores": {"attractiveness": 10}}
        }
    },
    {
        "text": "В школе ты учился(ась)...",
        "options": {
            "1": {"text": "Еле тянул(а), двойки", "scores": {"intelligence": 2}},
            "2": {"text": "Тройки, кое-как", "scores": {"intelligence": 4}},
            "3": {"text": "Хорошист(ка), твердая 4", "scores": {"intelligence": 6}},
            "4": {"text": "Отличник(ца), легко давалось", "scores": {"intelligence": 8}},
            "5": {"text": "Участвовал(а) в олимпиадах", "scores": {"intelligence": 10}}
        }
    },
    {
        "text": "Сколько у тебя близких друзей?",
        "options": {
            "1": {"text": "Никого, я один(одна)", "scores": {"friends": 2}},
            "2": {"text": "1-2 друга", "scores": {"friends": 4}},
            "3": {"text": "3-5 друзей", "scores": {"friends": 6}},
            "4": {"text": "5-10 человек", "scores": {"friends": 8}},
            "5": {"text": "Целая команда, много друзей", "scores": {"friends": 10}}
        }
    }
]

# Мужские вопросы (5 вопросов)
MALE_QUESTIONS = [
    {
        "text": "Во сколько лет у тебя начал ломаться голос?",
        "options": {
            "1": {"text": "Очень рано, в 10-11 лет", "scores": {"testosterone": 9}},
            "2": {"text": "В 12-13 лет", "scores": {"testosterone": 7}},
            "3": {"text": "В 14-15 лет", "scores": {"testosterone": 6}},
            "4": {"text": "В 16-17 лет", "scores": {"testosterone": 4}},
            "5": {"text": "До сих пор не сломался", "scores": {"testosterone": 2}}
        }
    },
    {
        "text": "Как у тебя с растительностью на лице?",
        "options": {
            "1": {"text": "Растёт плохо, бреюсь раз в неделю", "scores": {"testosterone": 3}},
            "2": {"text": "Нормально, бреюсь через день", "scores": {"testosterone": 5}},
            "3": {"text": "Густая, бреюсь каждый день", "scores": {"testosterone": 7}},
            "4": {"text": "Очень густая, если не брить — борода", "scores": {"testosterone": 9}},
            "5": {"text": "Ношу бороду/усы", "scores": {"testosterone": 8}}
        }
    },
    {
        "text": "Какой автомобиль ты предпочитаешь?",
        "options": {
            "1": {"text": "Большой внедорожник, джип", "scores": {"car_type": "BIG", "compensation": 8}},
            "2": {"text": "Спортивную машину", "scores": {"car_type": "SPORT", "compensation": 7}},
            "3": {"text": "Надёжный седан, универсал", "scores": {"car_type": "PRACTICAL", "compensation": 5}},
            "4": {"text": "Маленький экономичный автомобиль", "scores": {"car_type": "SMALL", "compensation": 3}},
            "5": {"text": "У меня нет машины", "scores": {"car_type": "NONE", "compensation": 2}}
        }
    },
    {
        "text": "Ходишь ли ты в общественные бани, сауны?",
        "options": {
            "1": {"text": "Да, регулярно, не стесняюсь", "scores": {"body_confidence": 9}},
            "2": {"text": "Иногда хожу, нормально себя чувствую", "scores": {"body_confidence": 7}},
            "3": {"text": "Редко, немного стесняюсь", "scores": {"body_confidence": 5}},
            "4": {"text": "Не хожу, стесняюсь своего тела", "scores": {"body_confidence": 3}},
            "5": {"text": "Никогда не ходил и не пойду", "scores": {"body_confidence": 1}}
        }
    },
    {
        "text": "Сколько ты можешь отжаться от пола?",
        "options": {
            "1": {"text": "0-5 раз", "scores": {"strength": 2}},
            "2": {"text": "5-15 раз", "scores": {"strength": 4}},
            "3": {"text": "15-30 раз", "scores": {"strength": 6}},
            "4": {"text": "30-50 раз", "scores": {"strength": 8}},
            "5": {"text": "Больше 50", "scores": {"strength": 10}}
        }
    }
]

# Женские вопросы (5 вопросов)
FEMALE_QUESTIONS = [
    {
        "text": "Какой у тебя размер груди?",
        "options": {
            "1": {"text": "0-1 размер (маленькая)", "scores": {"breast_size": 3, "feminine_capital": 4}},
            "2": {"text": "2 размер", "scores": {"breast_size": 5, "feminine_capital": 6}},
            "3": {"text": "3 размер", "scores": {"breast_size": 7, "feminine_capital": 8}},
            "4": {"text": "4 размер и больше", "scores": {"breast_size": 9, "feminine_capital": 9}},
            "5": {"text": "Не хочу отвечать", "scores": {"breast_size": 5, "feminine_capital": 5}}
        }
    },
    {
        "text": "Во сколько лет у тебя начались месячные?",
        "options": {
            "1": {"text": "Очень рано, до 11 лет", "scores": {"hormonal": 8}},
            "2": {"text": "В 11-12 лет", "scores": {"hormonal": 7}},
            "3": {"text": "В 12-14 лет", "scores": {"hormonal": 6}},
            "4": {"text": "В 14-16 лет", "scores": {"hormonal": 4}},
            "5": {"text": "После 16 лет", "scores": {"hormonal": 3}}
        }
    },
    {
        "text": "Какой тип мужчин ты обычно выбираешь?",
        "options": {
            "1": {"text": "Сильных, доминантных, которые решают всё", "scores": {"mate_type": "АЛЬФА", "mate_strategy": "DEPENDENT"}},
            "2": {"text": "Уверенных, но с которыми можно договориться", "scores": {"mate_type": "БЕТА", "mate_strategy": "PARTNERSHIP"}},
            "3": {"text": "Умных, интеллектуалов", "scores": {"mate_type": "ГАММА", "mate_strategy": "INTELLECTUAL"}},
            "4": {"text": "Богатых, статусных, которые могут обеспечить", "scores": {"mate_type": "ДЕЛЬТА", "mate_strategy": "PROVIDER"}},
            "5": {"text": "Красивых, харизматичных", "scores": {"mate_type": "ОМЕГА", "mate_strategy": "STATUS"}}
        }
    },
    {
        "text": "Что для тебя важнее в мужчине?",
        "options": {
            "1": {"text": "Чтобы защищал и был надёжной стеной", "scores": {"mate_priority": "PROTECTION", "feminine_strategy": "ЗАВИСИМАЯ"}},
            "2": {"text": "Чтобы зарабатывал и обеспечивал", "scores": {"mate_priority": "PROVISION", "feminine_strategy": "ПРАГМАТИЧНАЯ"}},
            "3": {"text": "Чтобы понимал и поддерживал", "scores": {"mate_priority": "SUPPORT", "feminine_strategy": "ПАРТНЁРСКАЯ"}},
            "4": {"text": "Чтобы был управляемым", "scores": {"mate_priority": "CONTROL", "feminine_strategy": "ДОМИНАНТНАЯ"}},
            "5": {"text": "Чтобы с ним было весело", "scores": {"mate_priority": "FUN", "feminine_strategy": "ГЕДОНИСТИЧЕСКАЯ"}}
        }
    },
    {
        "text": "Как часто ты занимаешься спортом?",
        "options": {
            "1": {"text": "Вообще не занимаюсь", "scores": {"sport": 2}},
            "2": {"text": "Иногда, без фанатизма", "scores": {"sport": 4}},
            "3": {"text": "Регулярно 2-3 раза в неделю", "scores": {"sport": 6}},
            "4": {"text": "Часто, 4-5 раз в неделю", "scores": {"sport": 8}},
            "5": {"text": "Профессионально", "scores": {"sport": 10}}
        }
    }
]

# Реакции на стресс (5 вопросов) - общие для всех
STRESS_QUESTIONS = [
    {
        "text": "В детстве, когда на тебя кричали, твое лицо...",
        "options": {
            "1": {"text": "Краснело", "scores": {"stress_response": "FIGHT"}},
            "2": {"text": "Бледнело", "scores": {"stress_response": "FLIGHT"}},
            "3": {"text": "Каменело, застывало", "scores": {"stress_response": "FREEZE"}},
            "4": {"text": "Становилось тряпичным", "scores": {"stress_response": "PLAY_DEAD"}},
            "5": {"text": "Расплывалось в улыбке", "scores": {"stress_response": "FAWN"}},
            "6": {"text": "Становилось пустым", "scores": {"stress_response": "SURRENDER"}}
        }
    },
    {
        "text": "Когда кто-то лезет без очереди, ты...",
        "options": {
            "1": {"text": "Громко делаю замечание", "scores": {"conflict": "FIGHT"}},
            "2": {"text": "Молча злюсь", "scores": {"conflict": "FREEZE"}},
            "3": {"text": "Думаю «да и ладно»", "scores": {"conflict": "SURRENDER"}},
            "4": {"text": "Пытаюсь объяснить вежливо", "scores": {"conflict": "FAWN"}},
            "5": {"text": "Ухожу в другую очередь", "scores": {"conflict": "FLIGHT"}}
        }
    },
    {
        "text": "В конфликте ты скорее...",
        "options": {
            "1": {"text": "Нападаю первый", "scores": {"conflict_style": "FIGHT"}},
            "2": {"text": "Защищаюсь, но не бью", "scores": {"conflict_style": "FREEZE"}},
            "3": {"text": "Пытаюсь договориться", "scores": {"conflict_style": "FAWN"}},
            "4": {"text": "Ухожу от конфликта", "scores": {"conflict_style": "FLIGHT"}},
            "5": {"text": "Уступаю", "scores": {"conflict_style": "SURRENDER"}}
        }
    },
    {
        "text": "После сильного стресса ты...",
        "options": {
            "1": {"text": "Ещё долго заведён(а)", "scores": {"recovery": 2}},
            "2": {"text": "Быстро прихожу в норму", "scores": {"recovery": 8}},
            "3": {"text": "Чувствую опустошение", "scores": {"recovery": 4}},
            "4": {"text": "Хочется есть сладкое", "scores": {"recovery": 5}},
            "5": {"text": "Хочется спать", "scores": {"recovery": 6}}
        }
    },
    {
        "text": "Как быстро ты засыпаешь после тяжёлого дня?",
        "options": {
            "1": {"text": "Мгновенно", "scores": {"sleep": 10, "nervous": 8}},
            "2": {"text": "Минут 10-15", "scores": {"sleep": 8, "nervous": 6}},
            "3": {"text": "Долго ворочаюсь", "scores": {"sleep": 4, "nervous": 4}},
            "4": {"text": "Не могу уснуть", "scores": {"sleep": 2, "nervous": 2}},
            "5": {"text": "Просыпаюсь ночью", "scores": {"sleep": 3, "nervous": 3}}
        }
    }
]

# Матрица ролей (для отображения названия)
ROLES_MATRIX = {
    "СБ": {1: "БОМЖ", 2: "ШНЫРЬ", 3: "СМОТРЯЩИЙ", 4: "ВОЛЬНЫЙ СТРЕЛОК", 5: "РАЗВОДЯЩИЙ", 6: "ПАХАН"},
    "ТФ": {1: "ИЖДИВЕНЕЦ", 2: "НАЁМНЫЙ РАБОЧИЙ", 3: "АРЕНДОДАТЕЛЬ", 4: "САМОЗАНЯТЫЙ", 5: "СЕЛЛЕР", 6: "ПРОИЗВОДИТЕЛЬ"},
    "УБ": {1: "ЛЖЕЭКСПЕРТ", 2: "НАЁМНЫЙ СПЕЦИАЛИСТ", 3: "НАСТАВНИК", 4: "ИССЛЕДОВАТЕЛЬ", 5: "ПРОДАВЕЦ ЗНАНИЙ", 6: "ТЕОРЕТИК"},
    "ЧВ": {1: "ТУСОВЩИК", 2: "ПРОЕКТНЫЙ", 3: "АМБАССАДОР", 4: "АРТИСТ", 5: "АГЕНТ", 6: "МЕДИАМАГНАТ"}
}

# Соответствие реакции на стресс и уровня
BIOCHEMICAL_TO_LEVEL = {
    "FIGHT": 6,
    "FLIGHT": 4,
    "FREEZE": 3,
    "PLAY_DEAD": 2,
    "FAWN": 5,
    "SURRENDER": 1
}

# ==================== ХЕНДЛЕРЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Начало теста - определение пола"""
    builder = InlineKeyboardBuilder()
    for key, option in GENDER_QUESTION["options"].items():
        builder.button(text=option["text"], callback_data=f"gender_{key}")
    builder.adjust(1)  # Вертикальное расположение
    
    await message.answer(
        "🧠 *Вариатика: твоя жизненная стратегия*\n\n"
        "Я задам несколько вопросов, чтобы определить твою стратегию.\n"
        "Отвечай честно — это важно для точного попадания.\n\n"
        f"*Первый вопрос:*\n{GENDER_QUESTION['text']}",
        reply_markup=builder.as_markup()
    )
    await state.set_state(UserState.gender)

@dp.callback_query(lambda c: c.data.startswith('gender_'))
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора пола"""
    await callback.answer()
    gender = callback.data.split('_')[1]
    await state.update_data(gender=gender)
    
    # Переходим к блоку 1
    await state.set_state(UserState.block1_question)
    await state.update_data(block1_question=0, block1_excludes=[])
    await ask_block1_question(callback.from_user.id, 0, state)

async def ask_block1_question(user_id, question_index, state: FSMContext):
    """Задать вопрос из блока 1"""
    q = QUESTIONS_BLOCK1[question_index]
    builder = InlineKeyboardBuilder()
    for emoji, option in q["options"].items():
        builder.button(text=f"{emoji} {option['text']}", callback_data=f"b1_{question_index}_{emoji}")
    builder.adjust(1)  # Вертикальное расположение
    
    await bot.send_message(
        user_id, 
        f"*Вопрос {question_index+1}/8:*\n{q['text']}", 
        reply_markup=builder.as_markup()
    )

@dp.callback_query(lambda c: c.data.startswith('b1_'))
async def process_block1_answer(callback: types.CallbackQuery, state: FSMContext):
    """Обработка ответа на вопрос блока 1"""
    await callback.answer()
    _, q_index_str, emoji = callback.data.split('_')
    q_index = int(q_index_str)
    
    data = await state.get_data()
    excludes = data.get('block1_excludes', [])
    excluded = QUESTIONS_BLOCK1[q_index]["options"][emoji]["exclude"]
    excludes.append(excluded)
    await state.update_data(block1_excludes=excludes)
    
    if q_index + 1 < len(QUESTIONS_BLOCK1):
        await ask_block1_question(callback.from_user.id, q_index + 1, state)
    else:
        await determine_narrative(callback.from_user.id, state)

async def determine_narrative(user_id, state: FSMContext):
    """Определение нарратива методом исключения"""
    data = await state.get_data()
    excludes = data.get('block1_excludes', [])
    
    counts = {"СБ": 0, "ТФ": 0, "УБ": 0, "ЧВ": 0}
    for ex in excludes:
        counts[ex] += 1
    
    sorted_narratives = sorted(counts.items(), key=lambda x: x[1])
    narrative = sorted_narratives[0][0]
    second_narrative = sorted_narratives[1][0] if sorted_narratives[1][1] - sorted_narratives[0][1] <= 1 else None
    
    await state.update_data(narrative=narrative, second_narrative=second_narrative)
    await state.set_state(UserState.block2_question)
    await state.update_data(block2_question=0, block2_resources={})
    
    gender = data.get('gender')
    gender_text = "мужчина" if gender == "М" else "женщина"
    
    await bot.send_message(
        user_id, 
        f"🎯 *Определено:* ты — *{gender_text}* в мире *{NARRATIVE_NAMES[narrative]}*.\n\n"
        f"Теперь 15 вопросов о твоих ресурсах и реакциях.",
        reply_markup=None
    )
    
    await ask_block2_question(user_id, 0, state)

async def ask_block2_question(user_id, question_index, state: FSMContext):
    """Задать вопрос из блока 2 с учётом пола"""
    data = await state.get_data()
    gender = data.get('gender')
    
    # Определяем, какой вопрос задавать
    if question_index < 5:
        # Общие вопросы
        q = COMMON_QUESTIONS[question_index]
    elif question_index < 10:
        # Гендерно-специфичные вопросы
        if gender == "М":
            q = MALE_QUESTIONS[question_index - 5]
        else:
            q = FEMALE_QUESTIONS[question_index - 5]
    else:
        # Вопросы про стресс
        q = STRESS_QUESTIONS[question_index - 10]
    
    builder = InlineKeyboardBuilder()
    for key, option in q["options"].items():
        text = option['text'] if len(option['text']) <= 40 else option['text'][:38] + ".."
        builder.button(text=text, callback_data=f"b2_{question_index}_{key}")
    builder.adjust(1)  # Вертикальное расположение
    
    await bot.send_message(
        user_id, 
        f"*Вопрос {question_index+1}/15:*\n{q['text']}", 
        reply_markup=builder.as_markup()
    )

@dp.callback_query(lambda c: c.data.startswith('b2_'))
async def process_block2_answer(callback: types.CallbackQuery, state: FSMContext):
    """Обработка ответа на вопрос блока 2"""
    await callback.answer()
    _, q_index_str, answer_key = callback.data.split('_')
    q_index = int(q_index_str)
    
    data = await state.get_data()
    gender = data.get('gender')
    resources = data.get('block2_resources', {})
    
    # Определяем, из какого массива вопрос
    if q_index < 5:
        q = COMMON_QUESTIONS[q_index]
    elif q_index < 10:
        if gender == "М":
            q = MALE_QUESTIONS[q_index - 5]
        else:
            q = FEMALE_QUESTIONS[q_index - 5]
    else:
        q = STRESS_QUESTIONS[q_index - 10]
    
    scores = q["options"][answer_key]["scores"]
    
    for key, value in scores.items():
        resources[key] = value
    
    await state.update_data(block2_resources=resources)
    
    if q_index + 1 < 15:
        await ask_block2_question(callback.from_user.id, q_index + 1, state)
    else:
        await show_result(callback.from_user.id, state)

async def show_result(user_id, state: FSMContext):
    """Показать финальный результат"""
    data = await state.get_data()
    gender = data.get('gender')
    narrative = data.get('narrative')
    second_narrative = data.get('second_narrative')
    resources = data.get('block2_resources', {})
    
    # Определяем уровень
    level = BIOCHEMICAL_TO_LEVEL.get(resources.get('stress_response', 'FREEZE'), 3)
    
    # Корректировка по физическим данным
    if gender == "М":
        if resources.get('testosterone', 0) > 7 and resources.get('strength', 0) > 6:
            level = min(6, level + 1)
        if resources.get('body_confidence', 0) < 3:
            level = max(1, level - 1)
    else:
        if resources.get('feminine_capital', 0) > 7:
            level = min(6, level + 1)
        if resources.get('breast_size', 0) > 7 and resources.get('attractiveness', 0) > 6:
            level = min(6, level + 1)
    
    # Получаем интерпретацию из отдельного файла
    role = ROLES_MATRIX[narrative][level]
    interpretation = get_interpretation(gender, narrative, level, second_narrative)
    
    # Формируем результат
    result = f"🎯 *Твой фокус:*\n\n"
    result += f"Ты — *{role}* в мире *{NARRATIVE_NAMES[narrative]}*.\n\n"
    result += f"{interpretation}\n\n"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Пройти заново", callback_data="restart")
    builder.adjust(1)
    
    await bot.send_message(user_id, result, reply_markup=builder.as_markup())
    await state.clear()

@dp.callback_query(lambda c: c.data == 'restart')
async def restart_test(callback: types.CallbackQuery, state: FSMContext):
    """Перезапуск теста"""
    await callback.answer()
    await cmd_start(callback.message, state)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
