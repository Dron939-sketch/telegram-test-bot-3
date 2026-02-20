
#!/usr/bin/env python3
"""
🔮 ТАЙНЫЙ ШЁПОТ: Виртуальная гадалка v5.0
Полная версия с 216 уникальными интерпретациями
Двухосевая архитектура: Нарратив (ценности) + Стратегия (поведение)
"""

import os
import logging
import random
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Загружаем токен
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ Токен не найден! Загляни в переменные окружения...")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==================== СОСТОЯНИЯ ====================

class UserState(StatesGroup):
    question_index = State()
    answers = State()
    last_message_id = State()
    gender = State()
    age_group = State()
    refining_narrative = State()
    primary_narrative = State()
    narrative_result = State()
    strategy_result = State()
    level_result = State()
    hypothesis = State()
    verification_round = State()
    verification_questions = State()
    verification_index = State()
    verification_answers = State()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_life_season(age: int) -> str:
    if age < 20: return "весна жизни 🌱"
    elif age < 30: return "начало лета ☀️"
    elif age < 40: return "разгар лета 🌻"
    elif age < 50: return "золотая осень 🍂"
    elif age < 60: return "бабье лето 🕸️"
    else: return "зима мудрости ❄️"

def get_separator() -> str:
    separators = [
        "✧═══════════════════════════✧",
        "🌸─────────────────────────🌸",
        "🌟═══════════════════════════🌟",
        "✨ * ✦ * ✦ * ✦ * ✦ * ✦ * ✦ * ✦ * ✦ * ✦ * ✦ * ✦ * ✦ * ✧",
        "☽═══════════════════════════☾",
    ]
    return random.choice(separators)

def get_mystic_symbol() -> str:
    symbols = ["🔮", "🕯️", "🌙", "⭐", "🌀", "💫", "✨", "🪷", "🌿", "🦉"]
    return random.choice(symbols)

def get_archetype_emoji(narrative: str, program: str) -> str:
    emoji_map = {
        ("СБ", "F1"): "🐺", ("СБ", "F2"): "🐺", ("СБ", "F3"): "🦉", ("СБ", "F4"): "🦎", ("СБ", "F5"): "🦊", ("СБ", "F6"): "🐑",
        ("ТФ", "F1"): "🐂", ("ТФ", "F2"): "🐎", ("ТФ", "F3"): "🦫", ("ТФ", "F4"): "🐌", ("ТФ", "F5"): "🐕", ("ТФ", "F6"): "🐖",
        ("УБ", "F1"): "🦅", ("УБ", "F2"): "🐁", ("УБ", "F3"): "🦉", ("УБ", "F4"): "🐙", ("УБ", "F5"): "🦜", ("УБ", "F6"): "🐑",
        ("ЧВ", "F1"): "🦚", ("ЧВ", "F2"): "🦔", ("ЧВ", "F3"): "🦢", ("ЧВ", "F4"): "🐠", ("ЧВ", "F5"): "🐬", ("ЧВ", "F6"): "🐚"
    }
    return emoji_map.get((narrative, program), "🔮")

# ==================== ВОПРОСЫ ====================

GENDER_QUESTION = {
    "text": "Кем ты приходишь в этот мир?",
    "options": {
        "М": {"text": "👨 Мужчиной", "scores": {"gender": "М"}},
        "Ж": {"text": "👩 Женщиной", "scores": {"gender": "Ж"}}
    }
}

AGE_QUESTION = {
    "text": "Сколько зим минуло с твоего рождения?",
    "options": {
        "1": {"text": "🌱 Меньше 20", "scores": {"age": 18, "age_group": "YOUNG"}},
        "2": {"text": "☀️ 20-25 лет", "scores": {"age": 22, "age_group": "YOUNG_ADULT"}},
        "3": {"text": "🌻 25-30 лет", "scores": {"age": 27, "age_group": "YOUNG_ADULT"}},
        "4": {"text": "🌳 30-35 лет", "scores": {"age": 32, "age_group": "ADULT"}},
        "5": {"text": "🌲 35-40 лет", "scores": {"age": 37, "age_group": "ADULT"}},
        "6": {"text": "🍂 40-45 лет", "scores": {"age": 42, "age_group": "MIDDLE"}},
        "7": {"text": "🍁 45-50 лет", "scores": {"age": 47, "age_group": "MIDDLE"}},
        "8": {"text": "❄️ 50-60 лет", "scores": {"age": 55, "age_group": "MATURE"}},
        "9": {"text": "🕯️ Больше 60", "scores": {"age": 65, "age_group": "ELDER"}}
    }
}

def get_narrative_questions(gender, age_group):
    if gender == "М":
        if age_group in ["YOUNG", "YOUNG_ADULT"]:
            return [
                {
                    "text": "Представь: пятница, ты свободен, никто не требует. Куда потянет?",
                    "options": {
                        "1": {"text": "🔥 Рвануть в зал или в танчики", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🛠️ Что-то починить, смастерить", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "📚 Зависнуть на научпопе", "scores": {"narrative": "УБ"}},
                        "4": {"text": "🎉 Тусоваться с друзьями", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {
                    "text": "Закрой глаза и вспомни человека, которого ты реально уважаешь. За что?",
                    "options": {
                        "1": {"text": "⚔️ Уверенность, характер", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🛡️ Надёжность, держит слово", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "🧠 Ум, с ним есть о чём", "scores": {"narrative": "УБ"}},
                        "4": {"text": "🎭 Лёгкость, юмор", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {
                    "text": "Если бы фея шепнула тебе самую приятную правду — что бы это было?",
                    "options": {
                        "1": {"text": "👑 «Ты крутой, тебя уважают»", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🤝 «На тебя можно положиться»", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "📖 «Ты очень умный»", "scores": {"narrative": "УБ"}},
                        "4": {"text": "✨ «С тобой так весело»", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {
                    "text": "Ты в новой компании. Что включается первым?",
                    "options": {
                        "1": {"text": "👁️ Сканирую, кто тут главный", "scores": {"narrative": "СБ"}},
                        "2": {"text": "💼 Ищу, с кем о деле", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👂 Слушаю, о чём говорят", "scores": {"narrative": "УБ"}},
                        "4": {"text": "🤝 Со всеми знакомлюсь", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {
                    "text": "Упала лишняя тысяча. На что уйдёт?",
                    "options": {
                        "1": {"text": "⌚ Что-то статусное", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🔧 Инструмент, полезное", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "📘 Книгу или курс", "scores": {"narrative": "УБ"}},
                        "4": {"text": "🍻 Поход с друзьями", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {
                    "text": "Что реально заводит в людях?",
                    "options": {
                        "1": {"text": "👑 Когда не знают места", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🪚 Когда халтурят", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "🤯 Когда тупят", "scores": {"narrative": "УБ"}},
                        "4": {"text": "😴 Когда скучные", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {
                    "text": "Какой подарок заставит сердце биться чаще?",
                    "options": {
                        "1": {"text": "💎 Дорогая статусная вещь", "scores": {"narrative": "СБ"}},
                        "2": {"text": "⚙️ Что-то полезное для дела", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "🧩 Интеллектуальная игра", "scores": {"narrative": "УБ"}},
                        "4": {"text": "🎟️ Билет на концерт", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {
                    "text": "Чего боишься до дрожи?",
                    "options": {
                        "1": {"text": "👻 Стать никем, потерять уважение", "scores": {"narrative": "СБ"}},
                        "2": {"text": "💸 Остаться без денег, без работы", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "🤦 Показаться глупым", "scores": {"narrative": "УБ"}},
                        "4": {"text": "👤 Стать незаметным, скучным", "scores": {"narrative": "ЧВ"}}
                    }
                }
            ]
        else:
            return [
                {
                    "text": "Свободный вечер. Куда?",
                    "options": {
                        "1": {"text": "🍖 С друзьями, шашлыки", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🏠 Дома, с семьёй", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "📖 За книгой", "scores": {"narrative": "УБ"}},
                        "4": {"text": "✈️ Выезд, путешествие", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {
                    "text": "Что главное в человеке?",
                    "options": {
                        "1": {"text": "⚔️ Характер, стержень", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🤝 Порядочность", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "🦉 Мудрость, опыт", "scores": {"narrative": "УБ"}},
                        "4": {"text": "💖 Душевность", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {
                    "text": "Какие слова дороги?",
                    "options": {
                        "1": {"text": "👑 «Ты добился всего сам»", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🤝 «На тебя можно положиться»", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "📚 «Ты мудрый»", "scores": {"narrative": "УБ"}},
                        "4": {"text": "🕊️ «С тобой спокойно»", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {
                    "text": "В незнакомой компании?",
                    "options": {
                        "1": {"text": "👁️ Кто главный?", "scores": {"narrative": "СБ"}},
                        "2": {"text": "💼 С кем о деле?", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👂 Слушаю", "scores": {"narrative": "УБ"}},
                        "4": {"text": "🤝 Общаюсь со всеми", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {
                    "text": "На что потратишь премию?",
                    "options": {
                        "1": {"text": "⌚ На статус", "scores": {"narrative": "СБ"}},
                        "2": {"text": "💰 Отложу, вложу", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "📚 На обучение", "scores": {"narrative": "УБ"}},
                        "4": {"text": "✈️ На путешествие", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {
                    "text": "Что раздражает?",
                    "options": {
                        "1": {"text": "👑 Неуважение", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🪚 Безответственность", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "🤯 Глупость", "scores": {"narrative": "УБ"}},
                        "4": {"text": "😴 Пустота", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {
                    "text": "Какой подарок?",
                    "options": {
                        "1": {"text": "💎 Дорогой, статусный", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🔧 Полезный в хозяйстве", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "📚 Книга, издание", "scores": {"narrative": "УБ"}},
                        "4": {"text": "🎟️ Впечатление", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {
                    "text": "Чего опасаешься?",
                    "options": {
                        "1": {"text": "👻 Потерять уважение", "scores": {"narrative": "СБ"}},
                        "2": {"text": "💸 Остаться без средств", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "🤦 Деградировать", "scores": {"narrative": "УБ"}},
                        "4": {"text": "👤 Одиночества", "scores": {"narrative": "ЧВ"}}
                    }
                }
            ]
    else:
        if age_group in ["YOUNG", "YOUNG_ADULT"]:
            return [
                {
                    "text": "Как любишь выходной?",
                    "options": {
                        "1": {"text": "👯 С подругами, в кафе", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "🏠 Дома, с семьёй", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "💪 Спорт, уход за собой", "scores": {"narrative": "СБ"}},
                        "4": {"text": "📚 Читаю, познавательное", "scores": {"narrative": "УБ"}}
                    }
                },
                {
                    "text": "Что важно в человеке?",
                    "options": {
                        "1": {"text": "🎭 Чувство юмора", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "🤝 Надёжность, забота", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "⚔️ Уверенность, сила", "scores": {"narrative": "СБ"}},
                        "4": {"text": "🧠 Ум, интеллект", "scores": {"narrative": "УБ"}}
                    }
                },
                {
                    "text": "Какой комплимент приятен?",
                    "options": {
                        "1": {"text": "✨ «Ты красивая, стильная»", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "🤗 «Ты заботливая, добрая»", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👑 «Ты сильная, с характером»", "scores": {"narrative": "СБ"}},
                        "4": {"text": "📖 «С тобой интересно»", "scores": {"narrative": "УБ"}}
                    }
                },
                {
                    "text": "В новой компании?",
                    "options": {
                        "1": {"text": "🤝 Со всеми знакомлюсь", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "👀 Присматриваюсь", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👁️ Кто тут главный?", "scores": {"narrative": "СБ"}},
                        "4": {"text": "👂 Наблюдаю, слушаю", "scores": {"narrative": "УБ"}}
                    }
                },
                {
                    "text": "На что потратишь?",
                    "options": {
                        "1": {"text": "👗 На одежду, косметику", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "💰 Отложу, на будущее", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👑 На статусное", "scores": {"narrative": "СБ"}},
                        "4": {"text": "📚 На курсы, обучение", "scores": {"narrative": "УБ"}}
                    }
                },
                {
                    "text": "Что бесит?",
                    "options": {
                        "1": {"text": "😴 Скучные", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "🪚 Безответственные", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👑 Хамство, неуважение", "scores": {"narrative": "СБ"}},
                        "4": {"text": "🤯 Глупость", "scores": {"narrative": "УБ"}}
                    }
                },
                {
                    "text": "Какой подарок?",
                    "options": {
                        "1": {"text": "💍 Красивая вещь", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "🔧 Что-то нужное", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "💎 Что-то дорогое", "scores": {"narrative": "СБ"}},
                        "4": {"text": "📚 Книга, курс", "scores": {"narrative": "УБ"}}
                    }
                },
                {
                    "text": "Чего боишься?",
                    "options": {
                        "1": {"text": "👤 Одиночества", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "💸 Бедности, нужды", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👻 Потерять уважение", "scores": {"narrative": "СБ"}},
                        "4": {"text": "🤦 Деградации", "scores": {"narrative": "УБ"}}
                    }
                }
            ]
        else:
            return [
                {
                    "text": "Как любишь проводить время?",
                    "options": {
                        "1": {"text": "👨‍👩‍👧 С семьёй", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "🏡 По дому, на даче", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👯 С подругами", "scores": {"narrative": "СБ"}},
                        "4": {"text": "📚 Читаю", "scores": {"narrative": "УБ"}}
                    }
                },
                {
                    "text": "Что главное в человеке?",
                    "options": {
                        "1": {"text": "💖 Доброта, душевность", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "🤝 Надёжность", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "⚔️ Характер", "scores": {"narrative": "СБ"}},
                        "4": {"text": "🦉 Мудрость, опыт", "scores": {"narrative": "УБ"}}
                    }
                },
                {
                    "text": "Какие слова дороги?",
                    "options": {
                        "1": {"text": "👩‍👧 «Ты замечательная мать»", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "🤝 «На тебя можно положиться»", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👑 «Тебя уважают»", "scores": {"narrative": "СБ"}},
                        "4": {"text": "📚 «Ты мудрая»", "scores": {"narrative": "УБ"}}
                    }
                },
                {
                    "text": "В незнакомой компании?",
                    "options": {
                        "1": {"text": "🤝 Общаюсь со всеми", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "👀 Присматриваюсь", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👁️ Кто главный?", "scores": {"narrative": "СБ"}},
                        "4": {"text": "👂 Наблюдаю", "scores": {"narrative": "УБ"}}
                    }
                },
                {
                    "text": "На что потратишь?",
                    "options": {
                        "1": {"text": "👶 На детей, внуков", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "💰 Отложу", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "💎 На статусное", "scores": {"narrative": "СБ"}},
                        "4": {"text": "✈️ На путешествие", "scores": {"narrative": "УБ"}}
                    }
                },
                {
                    "text": "Что раздражает?",
                    "options": {
                        "1": {"text": "💔 Чёрствость", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "🪚 Безответственность", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👑 Хамство", "scores": {"narrative": "СБ"}},
                        "4": {"text": "🤯 Глупость", "scores": {"narrative": "УБ"}}
                    }
                },
                {
                    "text": "Какой подарок?",
                    "options": {
                        "1": {"text": "💝 Внимание, забота", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "🔧 Что-то нужное", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "💎 Дорогое", "scores": {"narrative": "СБ"}},
                        "4": {"text": "📚 Книга", "scores": {"narrative": "УБ"}}
                    }
                },
                {
                    "text": "Чего опасаешься?",
                    "options": {
                        "1": {"text": "👤 Одиночества", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "💸 Бедности", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👻 Потерять уважение", "scores": {"narrative": "СБ"}},
                        "4": {"text": "🤦 Деградации", "scores": {"narrative": "УБ"}}
                    }
                }
            ]

def get_narrative_refinement_questions(primary_narrative, gender):
    refinement_db = {
        "СБ": [
            {
                "text": "В конфликте с подчинённым ты скорее...",
                "options": {
                    "1": {"text": "👑 Просто укажу ему место", "scores": {"second": "СБ"}},
                    "2": {"text": "🧠 Объясню, почему не прав", "scores": {"second": "УБ"}},
                    "3": {"text": "👀 Сделаю замечание при всех", "scores": {"second": "ЧВ"}},
                    "4": {"text": "💰 Лишу премии", "scores": {"second": "ТФ"}}
                }
            },
            {
                "text": "Кого из этих троих уважаешь больше?",
                "options": {
                    "1": {"text": "👑 Того, кто всего добился сам", "scores": {"second": "СБ"}},
                    "2": {"text": "🧠 Того, кто умный стратег", "scores": {"second": "УБ"}},
                    "3": {"text": "✨ Того, кто харизматичный лидер", "scores": {"second": "ЧВ"}},
                    "4": {"text": "💪 Того, кто пахал как лошадь", "scores": {"second": "ТФ"}}
                }
            },
            {
                "text": "Что важнее в команде?",
                "options": {
                    "1": {"text": "📐 Чёткая иерархия", "scores": {"second": "СБ"}},
                    "2": {"text": "🎯 Все понимают цель", "scores": {"second": "УБ"}},
                    "3": {"text": "💕 Хорошая атмосфера", "scores": {"second": "ЧВ"}},
                    "4": {"text": "⚙️ Каждый делает своё", "scores": {"second": "ТФ"}}
                }
            },
            {
                "text": "Если тебя публично унизили...",
                "options": {
                    "1": {"text": "⚔️ Сразу отвечу", "scores": {"second": "СБ"}},
                    "2": {"text": "🦉 Придумаю план мести", "scores": {"second": "УБ"}},
                    "3": {"text": "🎭 Сохраню лицо при всех", "scores": {"second": "ЧВ"}},
                    "4": {"text": "💪 Уйду и докажу делом", "scores": {"second": "ТФ"}}
                }
            }
        ],
        "ТФ": [
            {
                "text": "Начальник дал дурацкое задание...",
                "options": {
                    "1": {"text": "💪 Сделаю, потому что надо", "scores": {"second": "ТФ"}},
                    "2": {"text": "🤝 Попробую договориться", "scores": {"second": "СБ"}},
                    "3": {"text": "🧠 Объясню, почему глупо", "scores": {"second": "УБ"}},
                    "4": {"text": "💬 Пожалуюсь коллегам", "scores": {"second": "ЧВ"}}
                }
            },
            {
                "text": "Что главное в работе?",
                "options": {
                    "1": {"text": "💰 Стабильность и зарплата", "scores": {"second": "ТФ"}},
                    "2": {"text": "👑 Возможность влиять", "scores": {"second": "СБ"}},
                    "3": {"text": "🧠 Интересные задачи", "scores": {"second": "УБ"}},
                    "4": {"text": "👥 Коллектив", "scores": {"second": "ЧВ"}}
                }
            },
            {
                "text": "Как отдыхаешь после работы?",
                "options": {
                    "1": {"text": "😴 Ничего не делаю", "scores": {"second": "ТФ"}},
                    "2": {"text": "💪 В спортзале", "scores": {"second": "СБ"}},
                    "3": {"text": "📚 Читаю, узнаю новое", "scores": {"second": "УБ"}},
                    "4": {"text": "🎉 С друзьями", "scores": {"second": "ЧВ"}}
                }
            },
            {
                "text": "Чего боишься в работе?",
                "options": {
                    "1": {"text": "💸 Остаться без денег", "scores": {"second": "ТФ"}},
                    "2": {"text": "👻 Потерять уважение", "scores": {"second": "СБ"}},
                    "3": {"text": "🤦 Отупеть", "scores": {"second": "УБ"}},
                    "4": {"text": "👤 Остаться одному", "scores": {"second": "ЧВ"}}
                }
            }
        ],
        "УБ": [
            {
                "text": "Узнал что-то новое...",
                "options": {
                    "1": {"text": "🧠 Просто запомнил", "scores": {"second": "УБ"}},
                    "2": {"text": "💪 Думаю, как применить", "scores": {"second": "ТФ"}},
                    "3": {"text": "👑 Проверяю, кто сказал", "scores": {"second": "СБ"}},
                    "4": {"text": "💬 Делюсь с другими", "scores": {"second": "ЧВ"}}
                }
            },
            {
                "text": "Что важнее в книге?",
                "options": {
                    "1": {"text": "🧠 Глубина мысли", "scores": {"second": "УБ"}},
                    "2": {"text": "💪 Практическая польза", "scores": {"second": "ТФ"}},
                    "3": {"text": "👑 Кто автор", "scores": {"second": "СБ"}},
                    "4": {"text": "📖 Читабельность", "scores": {"second": "ЧВ"}}
                }
            },
            {
                "text": "В споре с глупым...",
                "options": {
                    "1": {"text": "🤐 Перестаю спорить", "scores": {"second": "УБ"}},
                    "2": {"text": "📊 Доказываю фактами", "scores": {"second": "ТФ"}},
                    "3": {"text": "👑 Давлю авторитетом", "scores": {"second": "СБ"}},
                    "4": {"text": "🎭 Высмеиваю при всех", "scores": {"second": "ЧВ"}}
                }
            },
            {
                "text": "Какой учёный ближе?",
                "options": {
                    "1": {"text": "🧠 Затворник, копает вглубь", "scores": {"second": "УБ"}},
                    "2": {"text": "💪 Изобретатель", "scores": {"second": "ТФ"}},
                    "3": {"text": "👑 Академик-управленец", "scores": {"second": "СБ"}},
                    "4": {"text": "🎙️ Популяризатор", "scores": {"second": "ЧВ"}}
                }
            }
        ],
        "ЧВ": [
            {
                "text": "Не позвали на тусовку...",
                "options": {
                    "1": {"text": "😢 Расстроюсь", "scores": {"second": "ЧВ"}},
                    "2": {"text": "👑 Выясню, кто главный", "scores": {"second": "СБ"}},
                    "3": {"text": "🧠 Придумаю, как попасть", "scores": {"second": "УБ"}},
                    "4": {"text": "💪 Пойду в другое место", "scores": {"second": "ТФ"}}
                }
            },
            {
                "text": "Что важнее в компании?",
                "options": {
                    "1": {"text": "💕 Чтобы меня ценили", "scores": {"second": "ЧВ"}},
                    "2": {"text": "👑 Кто здесь главный", "scores": {"second": "СБ"}},
                    "3": {"text": "🧠 О чём говорят", "scores": {"second": "УБ"}},
                    "4": {"text": "💪 Чем занимаются", "scores": {"second": "ТФ"}}
                }
            },
            {
                "text": "Как заводишь знакомства?",
                "options": {
                    "1": {"text": "💬 Просто общаюсь", "scores": {"second": "ЧВ"}},
                    "2": {"text": "👑 Через влиятельных", "scores": {"second": "СБ"}},
                    "3": {"text": "🧠 Через общие интересы", "scores": {"second": "УБ"}},
                    "4": {"text": "💪 Через работу", "scores": {"second": "ТФ"}}
                }
            },
            {
                "text": "Чего боишься в отношениях?",
                "options": {
                    "1": {"text": "👤 Одиночества", "scores": {"second": "ЧВ"}},
                    "2": {"text": "👻 Потерять уважение", "scores": {"second": "СБ"}},
                    "3": {"text": "🤦 Быть непонятым", "scores": {"second": "УБ"}},
                    "4": {"text": "💸 Стать обузой", "scores": {"second": "ТФ"}}
                }
            }
        ]
    }
    return refinement_db.get(primary_narrative, refinement_db["СБ"])

COMMON_RESOURCES_QUESTIONS = [
    {
        "text": "Какое у тебя образование?",
        "options": {
            "1": {"text": "📖 Неполное среднее", "scores": {"education": 2}},
            "2": {"text": "📚 Среднее (школа)", "scores": {"education": 4}},
            "3": {"text": "📗 Среднее специальное", "scores": {"education": 6}},
            "4": {"text": "📘 Высшее", "scores": {"education": 8}},
            "5": {"text": "📙 Два и более / учёная степень", "scores": {"education": 10}}
        }
    },
    {
        "text": "Кем ты работаешь?",
        "options": {
            "1": {"text": "🛌 Не работаю", "scores": {"job": "DEPENDENT", "income": 1}},
            "2": {"text": "🔧 Рабочий, персонал", "scores": {"job": "WORKER", "income": 3}},
            "3": {"text": "💼 Офисный работник", "scores": {"job": "OFFICE", "income": 4}},
            "4": {"text": "👨‍⚕️ Специалист (врач, учитель...)", "scores": {"job": "PROFESSIONAL", "income": 5}},
            "5": {"text": "👑 Руководитель, начальник", "scores": {"job": "MANAGER", "income": 7}},
            "6": {"text": "🏢 Свой бизнес", "scores": {"job": "BUSINESS", "income": 8}},
            "7": {"text": "💻 Фрилансер", "scores": {"job": "FREELANCE", "income": 5}},
            "8": {"text": "🎨 Творческая профессия", "scores": {"job": "CREATIVE", "income": 4}}
        }
    },
    {
        "text": "Как у тебя с деньгами?",
        "options": {
            "1": {"text": "🍞 Едва хватает на еду", "scores": {"money": 1}},
            "2": {"text": "🏠 Хватает на жизнь", "scores": {"money": 3}},
            "3": {"text": "🚗 Могу покупать крупные вещи", "scores": {"money": 5}},
            "4": {"text": "💰 Обеспечен(а), есть накопления", "scores": {"money": 7}},
            "5": {"text": "💎 Богат(а), деньги не проблема", "scores": {"money": 9}}
        }
    },
    {
        "text": "Где ты живёшь?",
        "options": {
            "1": {"text": "🏚️ Снимаю угол/комнату", "scores": {"housing": 1}},
            "2": {"text": "🏡 С родителями/родственниками", "scores": {"housing": 2}},
            "3": {"text": "🏢 Снимаю квартиру", "scores": {"housing": 3}},
            "4": {"text": "🏠 Своя квартира/дом", "scores": {"housing": 5}},
            "5": {"text": "🏰 Несколько объектов", "scores": {"housing": 8}}
        }
    },
    {
        "text": "Какой у тебя рост?",
        "options": {
            "1": {"text": "📏 Ниже 160 см", "scores": {"height": 2}},
            "2": {"text": "📏 160-170 см", "scores": {"height": 4}},
            "3": {"text": "📏 170-180 см", "scores": {"height": 6}},
            "4": {"text": "📏 180-190 см", "scores": {"height": 8}},
            "5": {"text": "📏 Выше 190 см", "scores": {"height": 10}}
        }
    },
    {
        "text": "Как оцениваешь свою внешность?",
        "options": {
            "1": {"text": "👤 Меня не замечают", "scores": {"looks": 2}},
            "2": {"text": "👥 Обычная внешность", "scores": {"looks": 4}},
            "3": {"text": "✨ Симпатичный(ая)", "scores": {"looks": 6}},
            "4": {"text": "🌟 Красивый(ая)", "scores": {"looks": 8}},
            "5": {"text": "💫 Модельная внешность", "scores": {"looks": 10}}
        }
    },
    {
        "text": "Как часто болеешь?",
        "options": {
            "1": {"text": "🤒 Постоянно", "scores": {"health": 2}},
            "2": {"text": "😷 Несколько раз в год", "scores": {"health": 4}},
            "3": {"text": "🤧 Раз в год", "scores": {"health": 6}},
            "4": {"text": "💪 Раз в несколько лет", "scores": {"health": 8}},
            "5": {"text": "🦾 Практически никогда", "scores": {"health": 10}}
        }
    },
    {
        "text": "Как у тебя с семьёй?",
        "options": {
            "1": {"text": "👤 Никогда не был(а) в браке", "scores": {"marriage": 0}},
            "2": {"text": "💑 В браке / в отношениях", "scores": {"marriage": 1}},
            "3": {"text": "💔 Разведен(а)", "scores": {"marriage": 0}},
            "4": {"text": "🕯️ Вдовец/вдова", "scores": {"marriage": 0}}
        }
    },
    {
        "text": "Есть ли у тебя дети?",
        "options": {
            "1": {"text": "👤 Нет детей", "scores": {"children": 0}},
            "2": {"text": "👶 Один ребёнок", "scores": {"children": 1}},
            "3": {"text": "👧👦 Двое детей", "scores": {"children": 2}},
            "4": {"text": "👨‍👩‍👧‍👦 Трое и больше", "scores": {"children": 3}}
        }
    },
    {
        "text": "Сколько близких друзей?",
        "options": {
            "1": {"text": "👤 Никого, я один(а)", "scores": {"friends": 1}},
            "2": {"text": "🤝 1-2 друга", "scores": {"friends": 3}},
            "3": {"text": "👥 3-5 друзей", "scores": {"friends": 5}},
            "4": {"text": "👪 5-10 человек", "scores": {"friends": 7}},
            "5": {"text": "🤗 Много друзей", "scores": {"friends": 9}}
        }
    }
]

def get_ancient_program_questions(gender):
    common = [
        {
            "text": "В опасной ситуации твоё тело...",
            "options": {
                "1": {"text": "⚔️ Рвётся в бой", "scores": {"ancient": "F1"}},
                "2": {"text": "🏃 Ноги сами несут", "scores": {"ancient": "F2"}},
                "3": {"text": "🧊 Каменеет, не двинуться", "scores": {"ancient": "F3"}},
                "4": {"text": "😶 Отключается, как не со мной", "scores": {"ancient": "F4"}},
                "5": {"text": "🙏 Ищет, кого умолять", "scores": {"ancient": "F5"}},
                "6": {"text": "🏳️ Опускает руки", "scores": {"ancient": "F6"}}
            }
        },
        {
            "text": "Если кто-то лезет без очереди...",
            "options": {
                "1": {"text": "⚔️ Сразу высказываю", "scores": {"ancient": "F1"}},
                "2": {"text": "🏃 Молчу, не хочу связываться", "scores": {"ancient": "F2"}},
                "3": {"text": "🧊 Жду, может кто скажет", "scores": {"ancient": "F3"}},
                "4": {"text": "😶 Смотрю в телефон, не замечаю", "scores": {"ancient": "F4"}},
                "5": {"text": "🙏 Вежливо прошу", "scores": {"ancient": "F5"}},
                "6": {"text": "🏳️ Ухожу в конец", "scores": {"ancient": "F6"}}
            }
        },
        {
            "text": "Что говорят о тебе близкие?",
            "options": {
                "1": {"text": "⚔️ Жёсткий, несгибаемый", "scores": {"ancient": "F1"}},
                "2": {"text": "🏃 Ускользающий, неуловимый", "scores": {"ancient": "F2"}},
                "3": {"text": "🧊 Непробиваемый, холодный", "scores": {"ancient": "F3"}},
                "4": {"text": "😶 Витает в облаках", "scores": {"ancient": "F4"}},
                "5": {"text": "🙏 Удобный, покладистый", "scores": {"ancient": "F5"}},
                "6": {"text": "🏳️ Сломленный, уставший", "scores": {"ancient": "F6"}}
            }
        },
        {
            "text": "Как часто выкладываешь фото?",
            "options": {
                "1": {"text": "⚔️ Каждый день, блог", "scores": {"ancient": "F1"}},
                "2": {"text": "🏃 Редко, не люблю", "scores": {"ancient": "F2"}},
                "3": {"text": "🧊 Только в сторис, на день", "scores": {"ancient": "F3"}},
                "4": {"text": "😶 Почти никогда", "scores": {"ancient": "F4"}},
                "5": {"text": "🙏 Регулярно, веду страницу", "scores": {"ancient": "F5"}},
                "6": {"text": "🏳️ Вообще не выкладываю", "scores": {"ancient": "F6"}}
            }
        }
    ]
    
    if gender == "М":
        male_specific = [
            {
                "text": "Как часто ходишь в баню?",
                "options": {
                    "1": {"text": "⚔️ Часто, своя баня", "scores": {"ancient": "F1"}},
                    "2": {"text": "🏃 Никогда, не люблю", "scores": {"ancient": "F2"}},
                    "3": {"text": "🧊 Иногда с друзьями", "scores": {"ancient": "F3"}},
                    "4": {"text": "😶 Раз в год, с работы", "scores": {"ancient": "F4"}},
                    "5": {"text": "🙏 Регулярно", "scores": {"ancient": "F5"}},
                    "6": {"text": "🏳️ Нет, не хожу", "scores": {"ancient": "F6"}}
                }
            },
            {
                "text": "Какая у тебя машина?",
                "options": {
                    "1": {"text": "⚔️ Спортивная, быстрая", "scores": {"ancient": "F1"}},
                    "2": {"text": "🏃 Нет, не нужна", "scores": {"ancient": "F2"}},
                    "3": {"text": "🧊 Эконом, чтобы ездила", "scores": {"ancient": "F3"}},
                    "4": {"text": "😶 Дорогая, статусная", "scores": {"ancient": "F4"}},
                    "5": {"text": "🙏 Надёжная, семейная", "scores": {"ancient": "F5"}},
                    "6": {"text": "🏳️ Старая, разваливается", "scores": {"ancient": "F6"}}
                }
            }
        ]
        return common + male_specific
    else:
        female_specific = [
            {
                "text": "Как одеваешься летом?",
                "options": {
                    "1": {"text": "⚔️ Открыто, люблю внимание", "scores": {"ancient": "F1"}},
                    "2": {"text": "🏃 Закрыто, не люблю", "scores": {"ancient": "F2"}},
                    "3": {"text": "🧊 Как удобно", "scores": {"ancient": "F3"}},
                    "4": {"text": "😶 Скромно, но аккуратно", "scores": {"ancient": "F4"}},
                    "5": {"text": "🙏 Чтобы нравиться другим", "scores": {"ancient": "F5"}},
                    "6": {"text": "🏳️ Всё равно", "scores": {"ancient": "F6"}}
                }
            },
            {
                "text": "В отношениях ты чаще...",
                "options": {
                    "1": {"text": "⚔️ Настаиваю на своём", "scores": {"ancient": "F1"}},
                    "2": {"text": "🏃 Ухожу, если что не так", "scores": {"ancient": "F2"}},
                    "3": {"text": "🧊 Молчу, терплю", "scores": {"ancient": "F3"}},
                    "4": {"text": "😶 Отключаюсь", "scores": {"ancient": "F4"}},
                    "5": {"text": "🙏 Уступаю, чтобы не ссориться", "scores": {"ancient": "F5"}},
                    "6": {"text": "🏳️ Мне всё равно", "scores": {"ancient": "F6"}}
                }
            }
        ]
        return common + female_specific

# ==================== ВЕРИФИКАЦИЯ ====================

def get_verification_questions(hypothesis):
    narrative = hypothesis["narrative"]
    program = hypothesis["program"]
    
    verification_db = {
        ("СБ", "F1"): [
            {
                "text": "В детстве, когда обижали, ты...",
                "options": {
                    "1": {"text": "⚔️ Дал сдачи, даже если слабее", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "🏃 Убежал и спрятался", "scores": {"verify": "СБ+F2"}},
                    "3": {"text": "🧊 Замер и терпел", "scores": {"verify": "СБ+F3"}},
                    "4": {"text": "🙏 Пошёл жаловаться", "scores": {"verify": "СБ+F5"}}
                }
            },
            {
                "text": "Кого уважаешь больше?",
                "options": {
                    "1": {"text": "⚔️ Того, кто может постоять", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "🏃 Того, кто уходит от конфликтов", "scores": {"verify": "СБ+F2"}},
                    "3": {"text": "🧠 Того, кто всё просчитывает", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "🎭 Того, кто со всеми дружит", "scores": {"verify": "ЧВ+F5"}}
                }
            },
            {
                "text": "Каким животным был бы?",
                "options": {
                    "1": {"text": "🐺 Волк, лев", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "🐇 Заяц, лань", "scores": {"verify": "СБ+F2"}},
                    "3": {"text": "🦉 Сова, лис", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "🐕 Собака", "scores": {"verify": "ТФ+F5"}}
                }
            }
        ],
        ("СБ", "F2"): [
            {
                "text": "В конфликте на работе...",
                "options": {
                    "1": {"text": "⚔️ Стою до конца", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "🏃 Ухожу от разговора", "scores": {"verify": "СБ+F2"}},
                    "3": {"text": "🧠 Анализирую", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "🙏 Ищу компромисс", "scores": {"verify": "СБ+F5"}}
                }
            },
            {
                "text": "Что страшнее?",
                "options": {
                    "1": {"text": "👻 Потерять власть", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "🏃 Оказаться в ловушке", "scores": {"verify": "СБ+F2"}},
                    "3": {"text": "🤦 Выглядеть глупо", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "👤 Быть отвергнутым", "scores": {"verify": "ЧВ+F5"}}
                }
            }
        ],
        ("ТФ", "F1"): [
            {
                "text": "Когда аврал на работе...",
                "options": {
                    "1": {"text": "⚔️ Работаю ещё жёстче", "scores": {"verify": "ТФ+F1"}},
                    "2": {"text": "🏃 Ищу, кто поможет", "scores": {"verify": "ТФ+F2"}},
                    "3": {"text": "🧊 Теряюсь", "scores": {"verify": "ТФ+F3"}},
                    "4": {"text": "🙏 Договариваюсь", "scores": {"verify": "ТФ+F5"}}
                }
            },
            {
                "text": "Как принимаешь решения?",
                "options": {
                    "1": {"text": "⚔️ Быстро, интуитивно", "scores": {"verify": "ТФ+F1"}},
                    "2": {"text": "🏃 Ухожу от решений", "scores": {"verify": "ТФ+F2"}},
                    "3": {"text": "🧠 Анализирую долго", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "🙏 Советуюсь", "scores": {"verify": "ЧВ+F5"}}
                }
            }
        ],
        ("УБ", "F3"): [
            {
                "text": "В стрессе ты...",
                "options": {
                    "1": {"text": "⚔️ Действую", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "🏃 Суечусь", "scores": {"verify": "ЧВ+F2"}},
                    "3": {"text": "🧊 Застываю", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "😶 Отключаюсь", "scores": {"verify": "УБ+F4"}}
                }
            },
            {
                "text": "Что говорят близкие?",
                "options": {
                    "1": {"text": "⚔️ Упрямый", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "🎭 Эмоциональный", "scores": {"verify": "ЧВ+F2"}},
                    "3": {"text": "🧠 В облаках витает", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "🤝 Надёжный", "scores": {"verify": "ТФ+F3"}}
                }
            }
        ],
        ("ЧВ", "F2"): [
            {
                "text": "На вечеринке ты...",
                "options": {
                    "1": {"text": "🎭 В центре", "scores": {"verify": "ЧВ+F1"}},
                    "2": {"text": "🏃 В стороне, наблюдаю", "scores": {"verify": "ЧВ+F2"}},
                    "3": {"text": "🧊 Со знакомыми", "scores": {"verify": "ЧВ+F3"}},
                    "4": {"text": "🙏 Всеми дружу", "scores": {"verify": "ЧВ+F5"}}
                }
            },
            {
                "text": "Что страшнее?",
                "options": {
                    "1": {"text": "👻 Быть в центре", "scores": {"verify": "ЧВ+F2"}},
                    "2": {"text": "💔 Быть отвергнутым", "scores": {"verify": "ЧВ+F5"}},
                    "3": {"text": "🤦 Выглядеть глупо", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "👑 Потерять контроль", "scores": {"verify": "СБ+F1"}}
                }
            }
        ]
    }
    
    key = (narrative, program)
    if key in verification_db:
        return verification_db[key]
    
    return [
        {
            "text": "Как реагируешь на неожиданности?",
            "options": {
                "1": {"text": "⚔️ Сразу действую", "scores": {"verify": "F1"}},
                "2": {"text": "🏃 Стараюсь уйти", "scores": {"verify": "F2"}},
                "3": {"text": "🧊 Замираю", "scores": {"verify": "F3"}},
                "4": {"text": "😶 Не замечаю", "scores": {"verify": "F4"}}
            }
        },
        {
            "text": "Что важнее?",
            "options": {
                "1": {"text": "👑 Быть уважаемым", "scores": {"verify": "СБ"}},
                "2": {"text": "💰 Быть обеспеченным", "scores": {"verify": "ТФ"}},
                "3": {"text": "🧠 Быть умным", "scores": {"verify": "УБ"}},
                "4": {"text": "💖 Быть любимым", "scores": {"verify": "ЧВ"}}
            }
        }
    ]

# ==================== ФУНКЦИИ ОПРЕДЕЛЕНИЯ ====================

def get_narrative_from_answers(answers):
    scores = {"СБ": 0, "ТФ": 0, "УБ": 0, "ЧВ": 0}
    
    for i in range(8):
        key = f'narrative_{i}'
        if key in answers:
            narr = answers[key]
            if narr in scores:
                scores[narr] += 1
    
    second_scores = {"СБ": 0, "ТФ": 0, "УБ": 0, "ЧВ": 0}
    for i in range(4):
        key = f'narrative_refine_{i}'
        if key in answers:
            narr = answers[key]
            if narr in second_scores:
                second_scores[narr] += 1
    
    if sum(scores.values()) == 0:
        return "СБ", None
    
    main = max(scores.items(), key=lambda x: x[1])[0]
    
    if sum(second_scores.values()) > 0:
        second = max(second_scores.items(), key=lambda x: x[1])[0]
        if second == main:
            second = None
    else:
        sorted_narr = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        second = sorted_narr[1][0] if len(sorted_narr) > 1 and sorted_narr[1][1] > 2 else None
    
    return main, second

def get_ancient_program(answers):
    scores = {"F1": 0, "F2": 0, "F3": 0, "F4": 0, "F5": 0, "F6": 0}
    sequence = []
    
    for i in range(6):  # 6 вопросов о программах
        key = f'ancient_{i}'
        if key in answers:
            program = answers[key]
            if program in scores:
                scores[program] += 1
                sequence.append(program)
    
    if sum(scores.values()) == 0:
        return "F3", None
    
    main = max(scores.items(), key=lambda x: x[1])[0]
    
    cascade = None
    if len(sequence) >= 3:
        if sequence[0] == "F3" and sequence[1] == "F2" and sequence[2] == "F1":
            cascade = "F3→F2→F1 (Страх→Бегство→Атака)"
        elif sequence[0] == "F3" and sequence[1] == "F5" and sequence[2] == "F6":
            cascade = "F3→F5→F6 (Ступор→Заискивание→Сдача)"
        elif sequence[0] == "F1" and sequence[1] == "F2" and sequence[2] == "F3":
            cascade = "F1→F2→F3 (Атака→Бегство→Ступор)"
        elif sequence[0] == "F5" and sequence[1] == "F1" and sequence[2] == "F6":
            cascade = "F5→F1→F6 (Заискивание→Срыв→Сдача)"
    
    return main, cascade

def get_level(data, narrative):
    base = 3
    
    if data.get('money', 0) > 7: base += 1
    if data.get('housing', 0) > 7: base += 1
    if data.get('education', 0) > 8: base += 1
    if data.get('looks', 0) > 8: base += 1
    if data.get('friends', 0) > 7: base += 1
    
    if data.get('money', 5) < 3: base -= 1
    if data.get('health', 5) < 3: base -= 1
    
    gender = data.get('gender', 'М')
    if gender == 'Ж':
        if data.get('marriage', 0) > 1: base += 1
    else:
        if data.get('height', 0) > 8: base += 1
    
    return max(1, min(6, base))

def verify_hypothesis(verification_answers, hypothesis):
    if not verification_answers:
        return False, hypothesis
    
    narrative_confirm = 0
    program_confirm = 0
    total_narrative = 0
    total_program = 0
    
    alt_narrative = {"СБ": 0, "ТФ": 0, "УБ": 0, "ЧВ": 0}
    alt_program = {"F1": 0, "F2": 0, "F3": 0, "F4": 0, "F5": 0, "F6": 0}
    
    for answer in verification_answers:
        if "+" in answer:
            narr, prog = answer.split("+")
            total_narrative += 1
            total_program += 1
            
            if narr == hypothesis["narrative"]:
                narrative_confirm += 1
            else:
                if narr in alt_narrative:
                    alt_narrative[narr] += 1
            
            if prog == hypothesis["program"]:
                program_confirm += 1
            else:
                if prog in alt_program:
                    alt_program[prog] += 1
        else:
            if answer in ["СБ", "ТФ", "УБ", "ЧВ"]:
                total_narrative += 1
                if answer == hypothesis["narrative"]:
                    narrative_confirm += 1
                else:
                    if answer in alt_narrative:
                        alt_narrative[answer] += 1
            elif answer in ["F1", "F2", "F3", "F4", "F5", "F6"]:
                total_program += 1
                if answer == hypothesis["program"]:
                    program_confirm += 1
                else:
                    if answer in alt_program:
                        alt_program[answer] += 1
    
    narrative_success = narrative_confirm >= total_narrative / 2 if total_narrative > 0 else True
    program_success = program_confirm >= total_program / 2 if total_program > 0 else True
    
    if narrative_success and program_success:
        return True, hypothesis
    
    new_narrative = hypothesis["narrative"]
    new_program = hypothesis["program"]
    
    if not narrative_success and total_narrative > 0:
        candidates = [(k, v) for k, v in alt_narrative.items() if v > 0]
        if candidates:
            new_narrative = max(candidates, key=lambda x: x[1])[0]
    
    if not program_success and total_program > 0:
        candidates = [(k, v) for k, v in alt_program.items() if v > 0]
        if candidates:
            new_program = max(candidates, key=lambda x: x[1])[0]
    
    new_hypothesis = {
        "narrative": new_narrative,
        "program": new_program,
        "level": hypothesis["level"],
        "second": hypothesis.get("second"),
        "cascade": hypothesis.get("cascade")
    }
    
    return False, new_hypothesis

# ==================== 216 УНИКАЛЬНЫХ ИНТЕРПРЕТАЦИЙ ====================

def get_final_interpretation(gender, narrative, program, level, second_narrative, cascade, age):
    
    narrative_names = {
        "СБ": "Власть",
        "ТФ": "Труд",
        "УБ": "Знание",
        "ЧВ": "Внимание"
    }
    
    program_names = {
        "F1": "Бей ⚔️",
        "F2": "Беги 🏃",
        "F3": "Замри 🧊",
        "F4": "Притворись мёртвым 😶",
        "F5": "Заискивай 🙏",
        "F6": "Сдайся 🏳️"
    }
    
    roles = {
        ("СБ", "F1"): "Хищник", ("СБ", "F2"): "Одиночка", ("СБ", "F3"): "Наблюдатель", ("СБ", "F4"): "Тень", ("СБ", "F5"): "Шестёрка", ("СБ", "F6"): "Бомж",
        ("ТФ", "F1"): "Мастер-кулак", ("ТФ", "F2"): "Шабашник", ("ТФ", "F3"): "Хранитель", ("ТФ", "F4"): "Лодырь", ("ТФ", "F5"): "Угодливый", ("ТФ", "F6"): "Иждивенец",
        ("УБ", "F1"): "Воин истины", ("УБ", "F2"): "Скептик", ("УБ", "F3"): "Мудрец", ("УБ", "F4"): "Пустышка", ("УБ", "F5"): "Популяризатор", ("УБ", "F6"): "Дурак",
        ("ЧВ", "F1"): "Скандалист", ("ЧВ", "F2"): "Отшельник", ("ЧВ", "F3"): "Загадка", ("ЧВ", "F4"): "Серость", ("ЧВ", "F5"): "Лапочка", ("ЧВ", "F6"): "Изгой"
    }
    
    role = roles.get((narrative, program), "Путник")
    emoji = get_archetype_emoji(narrative, program)
    
    # ===== 216 УНИКАЛЬНЫХ ТЕКСТОВ =====
    # Каждая комбинация (нарратив + программа + уровень) имеет свой текст
    
    # ----- СБ + F1 + уровни 1-6 -----
    texts_sb_f1 = {
        1: "Ты — щенок в стае хищников. В тебе есть агрессия, но нет силы. Ты рычишь, но тебя не боятся. Твой путь — наращивать мускулы и учиться ждать. Пока ты только учишься быть хищником.",
        2: "Ты — молодой волк. Ты уже можешь кусаться, но вожаки ещё сильнее. Ты бросаешь вызов, но пока проигрываешь. Терпение и хитрость — твоё оружие. Ты набираешь силу.",
        3: "Ты — боец в стае. Ты дерёшься за место, и у тебя есть шансы. Ты уже заставил себя уважать, но до вершины ещё далеко. Ты в середине иерархии и рвёшься вверх.",
        4: "Ты — приближённый к вожаку. Ты силён, тебя боятся и слушаются. Ты можешь многое, но над тобой ещё есть кто-то. Ты в элите, но не на вершине.",
        5: "Ты — один из вожаков. Твоё слово много значит. Ты дерёшься за власть с равными. Ты почти на вершине, осталось немного.",
        6: "Ты — вожак стаи. Ты устанавливаешь правила. Ты — альфа. Тебя боятся, уважают, идут за тобой. Ты достиг вершины в мире силы."
    }
    
    # ----- СБ + F2 + уровни 1-6 -----
    texts_sb_f2 = {
        1: "Ты — одиночка на обочине. Ты чувствуешь силу, но боишься за неё бороться. Ты убегаешь от конфликтов, даже когда мог бы победить. Ты слаб, но не хочешь это признавать.",
        2: "Ты — волк-одиночка, который держится подальше от стаи. Ты можешь постоять за себя, но предпочитаешь не ввязываться. Ты независим, но одинок.",
        3: "Ты — тот, кто уходит от разборок. Ты выбрал путь независимости. Ты ни с кем не борешься, но и никто тебе не указ. Твоя сила — в свободе.",
        4: "Ты — уважаемый одиночка. Ты вне иерархии, но с тобой считаются. Ты ни на кого не нападаешь, но и себя в обиду не дашь. Ты сам по себе, и это твой выбор.",
        5: "Ты — независимый игрок. Ты не лезешь в стаю, но у тебя есть влияние. К тебе приходят за советом, но ты никому не подчиняешься. Ты — свободный стратег.",
        6: "Ты — легендарный одиночка. Ты вне любой иерархии, но твой авторитет непререкаем. Ты ни за кем не идёшь и никого не ведёшь — ты просто есть, и это выше любой власти."
    }
    
    # ----- СБ + F3 + уровни 1-6 -----
    texts_sb_f3 = {
        1: "Ты — незаметный наблюдатель. Ты смотришь, как другие борются за власть, и молчишь. Ты боишься вступить в игру. Твоя позиция — в тени, и ты там в безопасности.",
        2: "Ты — тот, кто видит расклады. Ты понимаешь, кто главный, кто сильный, но не лезешь. Ты ждёшь своего часа. Терпение — твоя добродетель.",
        3: "Ты — смотрящий. Ты видишь всё, что происходит. Ты знаешь, но не вмешиваешься. К тебе приходят за оценкой ситуации. Ты — глаза и уши иерархии.",
        4: "Ты — уважаемый наблюдатель. Ты можешь влиять, просто сказав слово. Ты не дерёшься, но твоё мнение учитывают. Ты — мудрец в мире силы.",
        5: "Ты — серый кардинал. Ты не на виду, но ты управляешь. Ты знаешь всё и всех. Ты выбираешь, кто будет драться, а кто уйдёт. Твоя сила — в знании.",
        6: "Ты — теневая власть. Ты не показываешься, но весь мир силы вращается вокруг тебя. Ты — тот, кто никогда не дерётся, но всегда побеждает."
    }
    
    # ----- СБ + F4 + уровни 1-6 -----
    texts_sb_f4 = {
        1: "Ты — тень среди теней. Тебя вообще не видно. Ты научился быть незаметным, чтобы выжить. Но ты перестарался — тебя нет.",
        2: "Ты — призрак. Ты есть, но тебя не замечают. Ты прячешься от конфликтов, но цена — невидимость. Тебя не трогают, но и не зовут.",
        3: "Ты — незаметный, но нужный. Ты умеешь исчезать, когда опасно, и появляться, когда нужно. Ты — тот, кого не помнят, но без кого не обойтись.",
        4: "Ты — мастер маскировки в мире силы. Ты умеешь притворяться слабым, когда силён. Ты выживаешь там, где другие гибнут. Твоя сила — в невидимости.",
        5: "Ты — тот, кого никто не видит, но кто видит всех. Ты используешь свою незаметность как оружие. Ты появляешься из тени и исчезаешь обратно.",
        6: "Ты — легенда. О тебе ходят слухи, но никто не знает, существуешь ли ты на самом деле. Ты достиг совершенства в искусстве быть никем, чтобы быть всем."
    }
    
    # ----- СБ + F5 + уровни 1-6 -----
    texts_sb_f5 = {
        1: "Ты — шестёрка при слабом. Ты прибился к кому-то, кто чуть сильнее тебя. Ты угождаешь, подлизываешься, терпишь. Это даёт тебе крохи безопасности.",
        2: "Ты — свита при маленьком авторитете. Ты выбрал быть при сильных, чтобы выжить. Ты умеешь угождать, но часто забываешь о себе. Ты нужен, но не важен.",
        3: "Ты — приближённый. Ты при сильном, и тебя уже замечают. Ты умеешь вовремя поддакнуть и вовремя промолчать. Твоя лояльность — твой капитал.",
        4: "Ты — правая рука лидера. Тебе доверяют, тебя слушают. Ты при власти, хоть и не у власти. Ты влияешь через того, кому служишь.",
        5: "Ты — серый кардинал при вожаке. Ты управляешь тем, кто управляет. Твоя власть — через заискивание, ставшее искусством. Ты — трон за троном.",
        6: "Ты — тот, кто всегда при сильных, но сам стал сильным. Ты прошёл путь от шестёрки до доверенного лица. Ты умеешь дружить с властью, не теряя себя."
    }
    
    # ----- СБ + F6 + уровни 1-6 -----
    texts_sb_f6 = {
        1: "Ты — никто. Ты выпал из иерархии. Ты не борешься, не просишь, не прячешься. Ты просто плывёшь по течению. Ты никому не нужен, и тебе ничего не нужно.",
        2: "Ты — сдавшийся. Ты когда-то пытался, но проиграл. Теперь ты не лезешь. Ты существуешь, но не живёшь. Ты на дне и не пытаешься всплыть.",
        3: "Ты — принявший поражение. Ты смирился со своим положением. Ты не ждёшь перемен, не борешься за место. Ты просто есть.",
        4: "Ты — философ на дне. Ты решил, что власть — это зло, и ушёл в тень. Ты не участвуешь в игре, но наблюдаешь за ней. Ты выше этой суеты? Или просто слабее?",
        5: "Ты — отшельник от власти. Ты мог бы быть при сильных, но выбрал уйти. Ты не сдался — ты отказался. Это твой осознанный выбор.",
        6: "Ты — будда на обочине. Ты достиг просветления в отказе от власти. Ты не участвуешь в иерархии, но тебя уважают за мудрость отстранения. Ты выше всех."
    }
    
    # ----- ТФ + F1 + уровни 1-6 -----
    texts_tf_f1 = {
        1: "Ты — новичок с кулаками. Ты хочешь работать жёстко, но у тебя пока нет ни навыков, ни силы. Ты рвёшься в бой, но пока проигрываешь. Учись, прежде чем бить.",
        2: "Ты — работяга с характером. Ты уже умеешь работать, но твоя агрессия мешает. Ты лезешь в драку там, где можно договориться. Остынь, и дело пойдёт лучше.",
        3: "Ты — мастер своего дела. Ты работаешь жёстко, быстро, качественно. Тебя ценят, но побаиваются. Ты — лучший в своей нише, но не выходишь за её пределы.",
        4: "Ты — бригадир с кулаками. Ты не просто работаешь — ты организуешь. Твоя жёсткость помогает делу. Ты пробиваешь стены, которые другим не по зубам.",
        5: "Ты — хозяин своего дела. Ты создал бизнес или мастерскую, где ты — главный. Ты работаешь жёстко и требуешь того же от других. Ты — уважаемый мастер.",
        6: "Ты — легенда труда. Ты достиг всего своим потом и агрессией. Ты построил империю своими руками. Ты — пример для подражания и страх для конкурентов."
    }
    
    # ----- ТФ + F2 + уровни 1-6 -----
    texts_tf_f2 = {
        1: "Ты — шабашник-неудачник. Ты хватаешься за любую работу, но нигде не задерживаешься. Ты бегаешь от сложностей. Остановись, выбери одно дело и сделай его.",
        2: "Ты — вечный временщик. Ты перебегаешь с места на место, ищешь, где лучше. Но везде есть свои минусы. Может, дело не в месте, а в тебе?",
        3: "Ты — наёмник. Ты идёшь туда, где платят. Ты не привязан к одному месту, и это твоя сила. Ты умеешь быстро адаптироваться и менять сферы.",
        4: "Ты — свободный художник труда. Ты выбираешь проекты, которые тебе интересны. Ты не привязан к одному месту, но у тебя есть имя. К тебе приходят сами.",
        5: "Ты — востребованный специалист. Тебя зовут, за тобой охотятся. Ты выбираешь, где работать. Ты не бегаешь — ты паришь над рынком труда.",
        6: "Ты — легенда фриланса. Ты создал себя сам. Ты работаешь, где хочешь, когда хочешь и сколько хочешь. Ты — идеал свободного труда."
    }
    
    # ----- ТФ + F3 + уровни 1-6 -----
    texts_tf_f3 = {
        1: "Ты — застывший на месте. Ты не знаешь, куда двигаться, и просто стоишь. Ты боишься перемен. Но жизнь проходит мимо. Шевелись, пока не поздно.",
        2: "Ты — хранитель рутины. Ты делаешь одно и то же годами. Это стабильно, но скучно. Ты не растешь. Попробуй что-то новое — мир не рухнет.",
        3: "Ты — надёжный работник. Ты держишься за своё место и делаешь своё дело хорошо. На тебе держится стабильность. Ты — опора, но не лидер.",
        4: "Ты — хранитель традиций. Ты знаешь дело досконально и передаёшь знания другим. Ты — живая история своего ремесла. Тебя ценят за опыт.",
        5: "Ты — мудрец труда. Ты видел всё, ты знаешь всё. Ты уже не бегаешь и не суетишься — ты просто делаешь своё дело идеально. Ты — эталон.",
        6: "Ты — легенда, застывшая в вечности. Твоё имя стало нарицательным. Ты достиг совершенства в неподвижности — теперь ты сам стандарт качества."
    }
    
    # ----- ТФ + F4 + уровни 1-6 -----
    texts_tf_f4 = {
        1: "Ты — лодырь. Ты не работаешь, а делаешь вид. Ты отбываешь время, имитируешь активность. Но внутри пусто. Найди дело, которое зажжёт тебя.",
        2: "Ты — симулянт. Ты притворяешься занятым, но результат нулевой. Ты обманываешь начальство, но в первую очередь — себя. Ты способен на большее.",
        3: "Ты — профессиональный бездельник. Ты научился делать вид, что работаешь, так, что никто не замечает. Но ты не развиваешься. Ты стоишь на месте.",
        4: "Ты — тот, кто делает минимум. Ты выбрал стратегию экономии энергии. Ты не горишь, но и не падаешь. Тебя не уволят, но и не повысят.",
        5: "Ты — философ лени. Ты считаешь, что работа — не главное. Ты нашел способ получать деньги, не напрягаясь. Ты доволен, но... не гордишься.",
        6: "Ты — гуру безделья. Ты достиг просветления: ты понял, что счастье не в работе. Ты живёшь в своё удовольствие, и тебе плевать на мнение других."
    }
    
    # ----- ТФ + F5 + уровни 1-6 -----
    texts_tf_f5 = {
        1: "Ты — угодливый новичок. Ты стараешься, выслуживаешься, ждёшь похвалы. Но начальство пользуется тобой. Научись ценить себя, иначе сгорят.",
        2: "Ты — исполнительный подхалим. Ты умеешь вовремя поддакнуть и выполнить любую просьбу. Тебя любят, но не уважают. Ты — удобный работник.",
        3: "Ты — ценный помощник. Ты умеешь угодить начальству, но и дело делаешь. Ты при сильных, но и сам чего-то стоишь. Ты — сервис с качеством.",
        4: "Ты — правая рука руководителя. Тебе доверяют, тебя слушают. Твоя лояльность стала твоим капиталом. Ты влияешь через того, кому служишь.",
        5: "Ты — серый кардинал в бизнесе. Ты управляешь теми, кто управляет. Ты — тень за троном. Твоя сила — в умении быть незаменимым для сильных.",
        6: "Ты — легенда сервиса. Ты построил карьеру на умении угождать, но не потерял себя. Ты — пример того, как можно быть при сильных и оставаться личностью."
    }
    
    # ----- ТФ + F6 + уровни 1-6 -----
    texts_tf_f6 = {
        1: "Ты — иждивенец. Ты не работаешь и не ищешь. Ты живёшь за счёт других. Ты сдался в трудовой борьбе. Но ты способен на большее, просто забыл об этом.",
        2: "Ты — сдавшийся работник. Ты когда-то пытался, но тебя сломали. Теперь ты не веришь в себя. Ты существуешь на пособие или на шее у близких.",
        3: "Ты — принявший поражение. Ты смирился, что не добьёшься успеха в труде. Ты не ищешь работу, не пытаешься. Ты просто плывёшь по течению.",
        4: "Ты — философ на иждивении. Ты решил, что работа — это не твоё. Ты живёшь как можешь. Ты не гордишься, но и не стыдишься. Ты принял свой выбор.",
        5: "Ты — отшельник от труда. Ты мог бы работать, но выбрал иной путь. Ты живёшь просто, без амбиций. Ты свободен от гонки за деньгами.",
        6: "Ты — будда безделья. Ты достиг нирваны в отказе от труда. Ты не работаешь, но ты счастлив. Ты — живое доказательство, что счастье не в деньгах."
    }
    
    # ----- УБ + F1 + уровни 1-6 -----
    texts_ub_f1 = {
        1: "Ты — воин-неуч. Ты дерёшься за правду, но знаний не хватает. Ты споришь, но проигрываешь аргументы. Учись, прежде чем воевать.",
        2: "Ты — агрессивный дилетант. Ты нахватался верхушек и теперь лезешь в споры. Ты бесишься, когда проигрываешь. Смири гордыню и углубляй знания.",
        3: "Ты — боец за истину. Ты знаешь достаточно, чтобы отстаивать свою позицию. Ты умеешь спорить и доказывать. Ты — уважаемый оппонент.",
        4: "Ты — воин интеллекта. Ты не просто знаешь — ты умеешь уничтожать аргументы противника. Твоё оружие — логика. Тебя боятся в дискуссиях.",
        5: "Ты — генерал от знаний. Ты создал свою школу, свою теорию. Ты ведёшь за собой последователей. Ты — лидер в своей области.",
        6: "Ты — император истины. Твои идеи правят миром. Ты не просто знаешь — ты создаёшь реальность. Ты — вершина интеллектуальной иерархии."
    }
    
    # ----- УБ + F2 + уровни 1-6 -----
    texts_ub_f2 = {
        1: "Ты — неуч. Ты не хочешь знать, боишься знаний. Ты уходишь от сложных тем. Но мир сложнее, чем ты думаешь. Не бойся глубины.",
        2: "Ты — поверхностный человек. Ты скользишь по верхам, не углубляясь. Ты боишься, что знания откроют правду, которую ты не готов принять.",
        3: "Ты — скептик. Ты не веришь в знания, пока не проверишь. Ты осторожен, и это правильно. Но не перекрывай себе путь к новому.",
        4: "Ты — избегающий глубины. Ты умён, но не хочешь копать. Ты выбираешь лёгкие пути. Ты много теряешь, но тебе и так комфортно.",
        5: "Ты — философ-беглец. Ты понял, что знания бесконечны, и решил не гнаться. Ты выбрал свой уровень и остановился. Ты доволен, но мог бы больше.",
        6: "Ты — мудрец-отшельник. Ты знаешь достаточно, чтобы не искать больше. Ты ушёл от гонки за знаниями и нашёл покой. Ты — будда познания."
    }
    
    # ----- УБ + F3 + уровни 1-6 -----
    texts_ub_f3 = {
        1: "Ты — ученик. Ты впитываешь знания, но пока молчишь. Ты не готов делиться, боишься ошибиться. Учись, но помни: когда-то придётся говорить.",
        2: "Ты — накопитель знаний. Ты читаешь, смотришь, запоминаешь. Но ты не применяешь и не передаёшь. Знания без действия мертвы.",
        3: "Ты — молчаливый мудрец. Ты много знаешь, но говоришь мало. К тебе приходят за советом. Ты — живая энциклопедия, но только для избранных.",
        4: "Ты — хранитель знаний. Ты — библиотекарь мудрости. Ты систематизируешь, хранишь, передаёшь. Ты — важное звено в цепи познания.",
        5: "Ты — оракул. К тебе приходят за ответами. Ты не ищешь знания — они сами приходят к тебе. Ты — источник мудрости для других.",
        6: "Ты — абсолютное знание в покое. Ты достиг всего, что можно было познать, и замер в вечности. Ты — живой памятник мудрости."
    }
    
    # ----- УБ + F4 + уровни 1-6 -----
    texts_ub_f4 = {
        1: "Ты — пустышка. Ты делаешь вид, что умный. Цитируешь, повторяешь, но внутри пусто. Ты боишься, что это заметят. Начни учиться по-настоящему.",
        2: "Ты — имитатор ума. Ты научился создавать видимость глубины. Ты говоришь умные слова, но не понимаешь их. Ты обманываешь других, но в первую очередь себя.",
        3: "Ты — профессиональный пустышка. Ты так долго притворялся, что сам поверил. Но в критический момент истина всплывёт. Настоящие знания спасут.",
        4: "Ты — хамелеон от интеллекта. Ты умеешь казаться умным в любой компании. Ты адаптируешься, подстраиваешься. Ты — актёр, а не мыслитель.",
        5: "Ты — мастер иллюзий. Ты построил карьеру на видимости ума. Тебя считают гением, но ты знаешь правду. Ты боишься разоблачения.",
        6: "Ты — легенда притворства. Ты достиг вершин, не имея настоящих знаний. Ты — парадокс: пустота, которую все считают глубиной. Но ты несчастлив."
    }
    
    # ----- УБ + F5 + уровни 1-6 -----
    texts_ub_f5 = {
        1: "Ты — подхалим от знаний. Ты повторяешь за умными, чтобы понравиться. Ты не имеешь своего мнения. Найди свой голос, иначе так и останешься эхом.",
        2: "Ты — угодливый ученик. Ты соглашаешься с учителями, чтобы заслужить похвалу. Ты не споришь, даже если не согласен. Смелость иметь своё мнение.",
        3: "Ты — популяризатор. Ты умеешь объяснять сложное простым языком. Тебя любят слушатели. Ты — мост между знанием и массами.",
        4: "Ты — любимец публики. Ты умеешь подать знания так, что все в восторге. Ты — звезда лекций. Но не теряешь ли ты глубину ради популярности?",
        5: "Ты — медийный интеллектуал. Ты — лицо знаний. Тебя приглашают на ТВ, твои книги продаются. Ты — бренд, а не просто учёный.",
        6: "Ты — икона интеллекта. Ты достиг вершин популярности благодаря уму. Тебя обожают массы. Ты — звезда, которая светит знаниями."
    }
    
    # ----- УБ + F6 + уровни 1-6 -----
    texts_ub_f6 = {
        1: "Ты — дурак. Ты не хочешь знать и понимать. «Моя хата с краю». Но жизнь накажет за невежество. Открой глаза, пока не поздно.",
        2: "Ты — отказавшийся от ума. Ты когда-то пытался понять, но сдался. Теперь ты не лезешь в сложные темы. Ты выбрал неведение как защиту.",
        3: "Ты — смирившийся с глупостью. Ты признал, что знания — не твоё. Ты живёшь просто, не заморачиваясь. Ты не страдаешь, но и не растёшь.",
        4: "Ты — философ незнания. Ты решил, что истина непознаваема, и перестал искать. Ты — скептик, дошедший до абсолюта. Ты в тупике.",
        5: "Ты — отшельник от интеллекта. Ты мог бы быть умным, но выбрал иной путь. Ты живёшь без глубоких мыслей. Ты свободен от гонки за истиной.",
        6: "Ты — будда неведения. Ты достиг просветления в отказе от знаний. Ты не думаешь — ты просто есть. Ты — воплощение покоя в пустоте."
    }
    
    # ----- ЧВ + F1 + уровни 1-6 -----
    texts_chv_f1 = {
        1: "Ты — скандалист-неудачник. Ты привлекаешь внимание, но тебя не любят. Твой хайп — негативный. Люди обсуждают, но не уважают. Научись привлекать добром.",
        2: "Ты — эпатажный персонаж. Ты эпатируешь, провоцируешь, чтобы быть в центре. О тебе говорят, но часто плохо. Ты хочешь любой популярности.",
        3: "Ты — медийный хулиган. Ты умеешь создавать шум. Ты — тот, о ком говорят. Ты — скандальная, но заметная фигура. Ты на слуху.",
        4: "Ты — звезда скандалов. Ты — главный ньюсмейкер. Твои выходы обсуждают все. Ты — король хайпа. Тебя ненавидят, но слушают.",
        5: "Ты — легенда эпатажа. Ты построил карьеру на скандалах. Ты — бренд, который всегда в центре. Ты — тот, кого цитируют.",
        6: "Ты — император внимания через скандал. Ты достиг вершин: весь мир говорит о тебе. Ты — символ эпохи, даже если в негативном ключе."
    }
    
    # ----- ЧВ + F2 + уровни 1-6 -----
    texts_chv_f2 = {
        1: "Ты — затворник. Ты боишься людей, прячешься от внимания. Ты одинок и страдаешь. Но ты хочешь, чтобы тебя нашли. Выйди из тени.",
        2: "Ты — скромный одиночка. Ты не лезешь в центр, держишься в стороне. Ты хочешь внимания, но боишься его. Ты — невидимка по собственному желанию.",
        3: "Ты — наблюдатель. Ты смотришь на тусовки со стороны, не участвуя. Тебя не видно, но ты видишь всех. Ты — тихий, но не пустой.",
        4: "Ты — избирательный отшельник. Ты не лезешь в толпу, но у тебя есть близкие. Ты выбираешь качество, а не количество. Ты — камерная звезда.",
        5: "Ты — загадочный невидимка. О тебе ходят слухи, но тебя никто не видел. Ты создал ауру тайны. Ты — легенда в тени.",
        6: "Ты — абсолютная загадка. Ты достиг совершенства в невидимости. Тебя нет, но о тебе говорят. Ты — миф, который сильнее реальности."
    }
    
    # ----- ЧВ + F3 + уровни 1-6 -----
    texts_chv_f3 = {
        1: "Ты — немой. Ты молчишь, и тебя не слышно. Ты замер в углу и боишься пошевелиться. Ты есть, но тебя нет. Оживи, заговори.",
        2: "Ты — тихий. Ты мало говоришь, но иногда тебя замечают. Твоё молчание — защита. Но оно же и тюрьма. Рискни сказать слово.",
        3: "Ты — загадка. Ты молчишь, и это привлекает. Люди хотят узнать, что у тебя внутри. Твоё молчание — твоя сила.",
        4: "Ты — интрига. Ты говоришь мало, но каждое слово — событие. Ты — человек-тайна. К тебе тянутся, чтобы разгадать.",
        5: "Ты — культовая фигура молчания. Ты почти не появляешься, но тебя обожают. Твоё молчание — легенда. Ты — икона загадочности.",
        6: "Ты — абсолютное молчание. Ты не говоришь, но тебя слышат все. Ты достиг совершенства: твоя тишина говорит громче любых слов."
    }
    
    # ----- ЧВ + F4 + уровни 1-6 -----
    texts_chv_f4 = {
        1: "Ты — серый. Ты сливаешься с толпой, тебя не видно. Ты — как все, точнее — никакой. Ты потерял себя в попытке быть незаметным.",
        2: "Ты — незаметный. Тебя не помнят, не замечают, не ищут. Ты есть, но тебя нет. Ты привык, но внутри пустота.",
        3: "Ты — фоновый. Ты — часть декораций. Ты нужен, но тебя не ценят. Ты — массовка в чужой жизни. Пора стать главным героем.",
        4: "Ты — профессиональная серость. Ты научился быть незаметным так, что это стало твоей работой. Ты — невидимка, но тебе за это платят.",
        5: "Ты — мастер маскировки. Ты можешь быть кем угодно, оставаясь никем. Ты — хамелеон, который сливается с любым фоном.",
        6: "Ты — абсолютная пустота. Ты достиг совершенства в невидимости. Ты — ничто, и это твоя сверхсила. Ты свободен от необходимости быть."
    }
    
    # ----- ЧВ + F5 + уровни 1-6 -----
    texts_chv_f5 = {
        1: "Ты — лапочка-новичок. Ты всем улыбаешься, со всеми дружишь. Тебя любят, но не за то, кто ты есть. Ты теряешь себя в угоду другим.",
        2: "Ты — всеобщий любимец. Ты умеешь нравиться, умеешь угождать. Ты — душа компании, но только на поверхности. Где настоящий ты?",
        3: "Ты — профессиональный друг. Ты умеешь быть приятным для всех. Тебя зовут, тебя любят. Ты — мастер социальных связей.",
        4: "Ты — звезда обаяния. Ты умеешь очаровывать. Люди тянутся к тебе. Ты — центр притяжения, но не за счёт глубины, а за счёт тепла.",
        5: "Ты — кумир публики. Тебя обожают массы. Твоя улыбка — твой капитал. Ты — тот, кого хотят видеть и слышать.",
        6: "Ты — икона любви. Ты достиг вершин популярности через доброту и обаяние. Тебя боготворят. Ты — символ того, что быть хорошим выгодно."
    }
    
    # ----- ЧВ + F6 + уровни 1-6 -----
    texts_chv_f6 = {
        1: "Ты — изгой. Ты выпал из общения, из жизни. Никому не нужен, всеми забыт. Ты один. Но ты не всегда был таким. Вспомни себя.",
        2: "Ты — забытый. О тебе не вспоминают, тебя не зовут. Ты существуешь в вакууме. Ты сдался в социальной борьбе.",
        3: "Ты — принявший одиночество. Ты смирился, что ты один. Ты не ищешь общения, не ждёшь звонков. Ты — отшельник поневоле.",
        4: "Ты — философ одиночества. Ты решил, что люди — это боль, и ушёл в себя. Ты не страдаешь, ты выбрал это. Но счастлив ли ты?",
        5: "Ты — отшельник по призванию. Ты мог бы быть в центре, но выбрал тишину. Ты — мудрец, ушедший от суеты. Тебя уважают за выбор.",
        6: "Ты — абсолютное одиночество. Ты достиг нирваны в отказе от людей. Ты не нуждаешься в них. Ты — сам себе вселенная."
    }
    
    # Собираем словари для каждого нарратива
    narrative_texts = {
        "СБ": { "F1": texts_sb_f1, "F2": texts_sb_f2, "F3": texts_sb_f3, "F4": texts_sb_f4, "F5": texts_sb_f5, "F6": texts_sb_f6 },
        "ТФ": { "F1": texts_tf_f1, "F2": texts_tf_f2, "F3": texts_tf_f3, "F4": texts_tf_f4, "F5": texts_tf_f5, "F6": texts_tf_f6 },
        "УБ": { "F1": texts_ub_f1, "F2": texts_ub_f2, "F3": texts_ub_f3, "F4": texts_ub_f4, "F5": texts_ub_f5, "F6": texts_ub_f6 },
        "ЧВ": { "F1": texts_chv_f1, "F2": texts_chv_f2, "F3": texts_chv_f3, "F4": texts_chv_f4, "F5": texts_chv_f5, "F6": texts_chv_f6 }
    }
    
    # Получаем базовый текст для комбинации
    base_text = narrative_texts.get(narrative, {}).get(program, {}).get(level, "Ты — уникальная комбинация, для которой ещё не придумали описания.")
    
    # Второй нарратив
    second_text = ""
    if second_narrative and second_narrative != narrative:
        second_names = {
            "СБ": "власть", "ТФ": "труд", "УБ": "знание", "ЧВ": "внимание"
        }
        second_text = f"\n\n🌟 **Твой второй мир:** *{narrative_names[second_narrative]}* — ты не только живёшь в мире {narrative_names[narrative].lower()}, но и используешь {second_names[second_narrative]} как инструмент. Это даёт тебе гибкость и понимание других реальностей."
    
    # Каскад
    cascade_text = ""
    if cascade:
        cascade_text = f"\n\n🔄 **Твой природный каскад:** {cascade} — в стрессе ты проходишь эту цепочку реакций. Это твой автоматический сценарий. Осознав его, ты сможешь управлять собой в критических ситуациях."
    
    # Уровень подробно
    level_descriptions = {
        1: "Ты в самом начале пути. У тебя мало ресурсов, мало влияния, мало силы. Но это не навсегда. Каждый великий когда-то был никем. Твой уровень — это стартовая площадка.",
        2: "Ты уже не на дне, но ещё не в середине. У тебя есть немного ресурсов, немного влияния. Ты растешь, но медленно. Поднажми — следующий уровень ближе, чем кажется.",
        3: "Ты крепкий середняк. У тебя достаточно ресурсов, чтобы чувствовать себя уверенно. Тебя замечают, с тобой считаются. Ты — основа любой системы. Без таких, как ты, мир рухнет.",
        4: "Ты на подъёме. У тебя есть ресурсы, имя, влияние. Ты уже в элите, но ещё не на вершине. Ты видишь тех, кто выше, и знаешь, что скоро догонишь.",
        5: "Ты в высшей лиге. У тебя много ресурсов, власти, связей. Ты — один из тех, кто принимает решения. Мало кто может тебе указывать. Ты почти на вершине.",
        6: "Ты на вершине. У тебя максимум ресурсов для твоего мира. Ты сам устанавливаешь правила. Ты — тот, на кого равняются. Выше только небо."
    }
    
    level_desc = level_descriptions.get(level, "")
    
    # Возрастная мудрость
    age_wisdom = {
        "весна жизни": "Ты в начале пути. У тебя есть время на ошибки и эксперименты. Пробуй, ошибайся, вставай — всё ещё впереди.",
        "начало лета": "Ты в расцвете сил. Энергия бьёт ключом, амбиции зашкаливают. Самое время для рывка. Не тормози.",
        "разгар лета": "Ты уже многое понял, но ещё полон сил. Золотое время для реализации планов. Ты достаточно опытен, чтобы не ошибаться, и достаточно молод, чтобы рисковать.",
        "золотая осень": "Ты достиг зрелости. Опыт и мудрость позволяют тебе видеть то, что не видят молодые. Ты — наставник и опора.",
        "бабье лето": "Ты ещё полон сил, но уже понимаешь ценность покоя. Ты заслужил право не спешить. Ты можешь наслаждаться плодами своего труда.",
        "зима мудрости": "Ты видел многое. Твой опыт бесценен. Ты уже не бежишь — ты наблюдаешь и передаёшь знания. Ты — хранитель мудрости."
    }
    
    season = get_life_season(age)
    season_text = age_wisdom.get(season.split()[0], "")
    
    # Полный текст
    full_text = (
        f"{emoji} **Твой архетип:** *{role}*\n\n"
        f"{base_text}\n\n"
        f"**📊 Твой уровень:** {level}\n{level_desc}\n\n"
        f"**🌿 Твой возраст:** {season}\n{season_text}"
        f"{second_text}"
        f"{cascade_text}"
    )
    
    return full_text

# ==================== ХЕНДЛЕРЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data and data.get('answers'):
        user_name = message.from_user.first_name or "путник"
        mystic = get_mystic_symbol()
        
        welcome_back = (
            f"{mystic} *Ты вернулся, {user_name}...* {mystic}\n\n"
            f"{get_separator()}\n\n"
            f"Я помню твою душу. Хочешь продолжить?\n\n"
            f"• 🔄 *Заново* — откроешь новые грани\n"
            f"• 👀 *Результаты* — заглянешь в уже открытое"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Пройти заново", callback_data="restart")
        builder.button(text="👀 Мои результаты", callback_data="show_results")
        builder.adjust(1)
        
        await message.answer(welcome_back, reply_markup=builder.as_markup())
        return
    
    user_name = message.from_user.first_name or "путник"
    mystic = get_mystic_symbol()
    
    intro = (
        f"{mystic} *Тайный шёпот* {mystic}\n\n"
        f"Здравствуй, {user_name}...\n\n"
        f"{get_separator()}\n\n"
        f"Я вижу твою душу сквозь время. Хочешь узнать, кто ты на самом деле?\n\n"
        f"За несколько вопросов я расскажу:\n"
        f"• 🌍 *В каком мире ты живёшь*\n"
        f"• ⚡ *Как ты реагируешь на угрозы*\n"
        f"• 🎭 *Кто ты в этом мире*\n"
        f"• 🔥 *Что ждёт тебя впереди*\n\n"
        f"{get_separator()}\n\n"
        f"*Готов заглянуть за завесу?*"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔮 Начать", callback_data="start_test")
    builder.button(text="❓ Что это?", callback_data="why_details")
    builder.adjust(1)
    
    await message.answer(intro, reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data == "why_details")
async def why_details(callback: types.CallbackQuery):
    await callback.answer()
    
    explanation = (
        f"🔮 *Немного правды* 🔮\n\n"
        f"{get_separator()}\n\n"
        f"Я не колдую — я *читаю тебя*.\n\n"
        f"Каждый твой ответ — ключ к твоей природе:\n"
        f"• 🧠 *Как ты мыслишь* — твой нарратив\n"
        f"• 💓 *Как ты реагируешь* — твоя стратегия\n"
        f"• 🚀 *Куда тебе двигаться* — твой путь\n\n"
        f"{get_separator()}\n\n"
        f"*Готов?*"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔮 Да", callback_data="start_test")
    builder.adjust(1)
    
    await callback.message.edit_text(explanation, reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data == "start_test")
async def start_test(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    await state.clear()
    await state.update_data(
        answers={}, 
        last_message_id=None,
        verification_round=0,
        verification_answers=[]
    )
    await state.set_state(UserState.question_index)
    
    mystic = get_mystic_symbol()
    await callback.message.edit_text(
        f"{mystic} *Сосредоточься...*\n\n"
        f"Я задам несколько вопросов. Отвечай честно.\n\n"
        f"*Первый вопрос...*"
    )
    await asyncio.sleep(2)
    
    await ask_gender_question(callback.from_user.id, state)

async def ask_gender_question(user_id, state: FSMContext):
    data = await state.get_data()
    
    last_id = data.get('last_message_id')
    if last_id:
        try:
            await bot.delete_message(user_id, last_id)
        except:
            pass
    
    builder = InlineKeyboardBuilder()
    for key, option in GENDER_QUESTION["options"].items():
        builder.button(text=option["text"], callback_data=f"gender_{key}")
    builder.adjust(1)
    
    sent = await bot.send_message(
        user_id,
        f"{get_mystic_symbol()} *Вопрос 1/33*\n\n"
        f"*{GENDER_QUESTION['text']}*",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(last_message_id=sent.message_id, question_index=0)

async def ask_age_question(user_id, state: FSMContext):
    data = await state.get_data()
    
    last_id = data.get('last_message_id')
    if last_id:
        try:
            await bot.delete_message(user_id, last_id)
        except:
            pass
    
    builder = InlineKeyboardBuilder()
    for key, option in AGE_QUESTION["options"].items():
        builder.button(text=option["text"], callback_data=f"age_{key}")
    builder.adjust(2)
    
    sent = await bot.send_message(
        user_id,
        f"{get_mystic_symbol()} *Вопрос 2/33*\n\n"
        f"*{AGE_QUESTION['text']}*",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(last_message_id=sent.message_id, question_index=1)

async def ask_question(user_id, index, state: FSMContext):
    data = await state.get_data()
    answers = data.get('answers', {})
    gender = answers.get('gender', 'М')
    age_group = answers.get('age_group', 'ADULT')
    
    last_id = data.get('last_message_id')
    if last_id:
        try:
            await bot.delete_message(user_id, last_id)
        except:
            pass
    
    total_questions = 33
    
    if index < 2:
        return
    elif index < 10:  # 8 нарративных (2-9)
        narrative_q_idx = index - 2
        questions = get_narrative_questions(gender, age_group)
        q = questions[narrative_q_idx]
        block = "МИР, В КОТОРОМ ТЫ ЖИВЁШЬ"
        q_num = index + 1
        prefix = "narrative"
    elif index < 14:  # 4 уточняющих (10-13)
        return
    elif index < 24:  # 10 ресурсных (14-23)
        res_q_idx = index - 14
        q = COMMON_RESOURCES_QUESTIONS[res_q_idx]
        block = "ТВОИ ДАРЫ И РЕСУРСЫ"
        q_num = index + 1
        prefix = "res"
    else:  # 6 древних программ (24-29)
        ancient_q_idx = index - 24
        questions = get_ancient_program_questions(gender)
        if ancient_q_idx < len(questions):
            q = questions[ancient_q_idx]
            block = "ТВОЯ ПРИРОДНАЯ СТИХИЯ"
            q_num = index + 1
            prefix = "ancient"
        else:
            await start_verification(user_id, state)
            return
    
    progress = "█" * int((index + 1) / total_questions * 10) + "░" * (10 - int((index + 1) / total_questions * 10))
    
    builder = InlineKeyboardBuilder()
    for key, option in q["options"].items():
        score_key = list(option["scores"].keys())[0]
        score_value = option["scores"][score_key]
        callback_data = f"ans_{index}_{key}_{prefix}_{score_key}_{score_value}"
        if len(callback_data) > 64:
            callback_data = f"ans_{index}_{key}"
        builder.button(text=option["text"], callback_data=callback_data)
    builder.adjust(1)
    
    sent = await bot.send_message(
        user_id,
        f"{get_mystic_symbol()} *{block} • Вопрос {q_num}/{total_questions}*\n"
        f"`{progress}`\n\n"
        f"*{q['text']}*",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(last_message_id=sent.message_id)

async def ask_narrative_refinement_question(user_id, index, state: FSMContext):
    data = await state.get_data()
    answers = data.get('answers', {})
    primary = data.get('primary_narrative', 'СБ')
    gender = answers.get('gender', 'М')
    
    questions = get_narrative_refinement_questions(primary, gender)
    
    if index >= len(questions):
        await ask_question(user_id, 14, state)
        return
    
    q = questions[index]
    
    last_id = data.get('last_message_id')
    if last_id:
        try:
            await bot.delete_message(user_id, last_id)
        except:
            pass
    
    builder = InlineKeyboardBuilder()
    for key, option in q["options"].items():
        callback_data = f"refine_{index}_{key}_{option['scores']['second']}"
        builder.button(text=option["text"], callback_data=callback_data)
    builder.adjust(1)
    
    q_num = index + 10
    total = 33
    
    progress = "█" * int((q_num) / total * 10) + "░" * (10 - int((q_num) / total * 10))
    
    sent = await bot.send_message(
        user_id,
        f"{get_mystic_symbol()} *УТОЧНЕНИЕ • Вопрос {q_num}/33*\n"
        f"`{progress}`\n\n"
        f"*{q['text']}*",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(last_message_id=sent.message_id)

async def ask_verification_question(user_id, state: FSMContext):
    data = await state.get_data()
    hypothesis = data.get('hypothesis')
    v_index = data.get('verification_index', 0)
    v_questions = data.get('verification_questions', [])
    
    if not v_questions or v_index >= len(v_questions):
        await finish_verification(user_id, state)
        return
    
    q = v_questions[v_index]
    
    last_id = data.get('last_message_id')
    if last_id:
        try:
            await bot.delete_message(user_id, last_id)
        except:
            pass
    
    builder = InlineKeyboardBuilder()
    for key, option in q["options"].items():
        score = option["scores"]["verify"]
        callback_data = f"verif_{v_index}_{key}_{score}"
        builder.button(text=option["text"], callback_data=callback_data)
    builder.adjust(1)
    
    round_num = data.get('verification_round', 1)
    
    sent = await bot.send_message(
        user_id,
        f"{get_mystic_symbol()} *ПРОВЕРКА • Круг {round_num}*\n\n"
        f"Твои ответы сложились в образ... но не обманываешь ли ты себя?\n\n"
        f"*{q['text']}*",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(
        last_message_id=sent.message_id,
        verification_index=v_index + 1
    )

async def finish_verification(user_id, state: FSMContext):
    data = await state.get_data()
    hypothesis = data.get('hypothesis')
    verification_answers = data.get('verification_answers', [])
    round_num = data.get('verification_round', 1)
    
    success, new_hypothesis = verify_hypothesis(verification_answers, hypothesis)
    
    if success or round_num >= 2:
        await show_fortune(user_id, state, new_hypothesis)
    else:
        new_questions = get_verification_questions(new_hypothesis)
        await state.update_data(
            hypothesis=new_hypothesis,
            verification_round=round_num + 1,
            verification_index=0,
            verification_answers=[],
            verification_questions=new_questions
        )
        
        mystic = get_mystic_symbol()
        await bot.send_message(
            user_id,
            f"{mystic} *Интересно...*\n\n"
            f"Твои ответы заставили меня задуматься. Позволь уточнить."
        )
        await asyncio.sleep(2)
        
        await ask_verification_question(user_id, state)

@dp.callback_query(lambda c: c.data.startswith('gender_'))
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    gender = callback.data.split('_')[1]
    
    data = await state.get_data()
    answers = data.get('answers', {})
    answers['gender'] = gender
    
    await state.update_data(answers=answers)
    
    try:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
    except:
        pass
    
    await ask_age_question(callback.from_user.id, state)

@dp.callback_query(lambda c: c.data.startswith('age_'))
async def process_age(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    age_key = callback.data.split('_')[1]
    age_data = AGE_QUESTION["options"][age_key]["scores"]
    
    data = await state.get_data()
    answers = data.get('answers', {})
    answers['age'] = age_data['age']
    answers['age_group'] = age_data['age_group']
    
    await state.update_data(answers=answers)
    
    try:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
    except:
        pass
    
    await ask_question(callback.from_user.id, 2, state)

@dp.callback_query(lambda c: c.data.startswith('ans_'))
async def process_answer(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    parts = callback.data.split('_')
    idx = int(parts[1])
    key = parts[2]
    
    data = await state.get_data()
    answers = data.get('answers', {})
    gender = answers.get('gender', 'М')
    age_group = answers.get('age_group', 'ADULT')
    
    if len(parts) > 5:
        prefix = parts[3]
        score_key = parts[4]
        score_value = parts[5]
    else:
        if idx < 10:
            questions = get_narrative_questions(gender, age_group)
            q_idx = idx - 2
            q = questions[q_idx]
            score_key = list(q["options"][key]["scores"].keys())[0]
            score_value = q["options"][key]["scores"][score_key]
            prefix = "narrative"
        elif idx < 24:
            q_idx = idx - 14
            q = COMMON_RESOURCES_QUESTIONS[q_idx]
            score_key = list(q["options"][key]["scores"].keys())[0]
            score_value = q["options"][key]["scores"][score_key]
            prefix = "res"
        else:
            questions = get_ancient_program_questions(gender)
            q_idx = idx - 24
            q = questions[q_idx]
            score_key = list(q["options"][key]["scores"].keys())[0]
            score_value = q["options"][key]["scores"][score_key]
            prefix = "ancient"
    
    if prefix == "narrative":
        answers[f'narrative_{idx-2}'] = score_value
    elif prefix == "res":
        answers[score_key] = int(score_value) if score_value.isdigit() else score_value
    elif prefix == "ancient":
        answers[f'ancient_{idx-24}'] = score_value
    
    await state.update_data(answers=answers)
    
    try:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
    except:
        pass
    
    if idx == 9:
        narrative, _ = get_narrative_from_answers(answers)
        await state.update_data(refining_narrative=True, primary_narrative=narrative)
        await ask_narrative_refinement_question(callback.from_user.id, 0, state)
    elif idx + 1 >= 30:
        await start_verification(callback.from_user.id, state)
    else:
        await ask_question(callback.from_user.id, idx + 1, state)

@dp.callback_query(lambda c: c.data.startswith('refine_'))
async def process_refinement(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    parts = callback.data.split('_')
    idx = int(parts[1])
    second = parts[3]
    
    data = await state.get_data()
    answers = data.get('answers', {})
    answers[f'narrative_refine_{idx}'] = second
    
    await state.update_data(answers=answers)
    
    try:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
    except:
        pass
    
    if idx + 1 < 4:
        await ask_narrative_refinement_question(callback.from_user.id, idx + 1, state)
    else:
        await ask_question(callback.from_user.id, 14, state)

@dp.callback_query(lambda c: c.data.startswith('verif_'))
async def process_verification(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    parts = callback.data.split('_')
    v_idx = int(parts[1])
    score = parts[3]
    
    data = await state.get_data()
    verification_answers = data.get('verification_answers', [])
    verification_answers.append(score)
    
    await state.update_data(verification_answers=verification_answers)
    
    try:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
    except:
        pass
    
    await ask_verification_question(callback.from_user.id, state)

@dp.callback_query(lambda c: c.data == "restart")
async def restart(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await cmd_start(callback.message, state)

@dp.callback_query(lambda c: c.data == "show_results")
async def show_results(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    if data.get('answers'):
        hypothesis = data.get('hypothesis')
        if hypothesis:
            await show_fortune(callback.from_user.id, state, hypothesis)
        else:
            answers = data.get('answers', {})
            narrative, second = get_narrative_from_answers(answers)
            program, cascade = get_ancient_program(answers)
            level = get_level(answers, narrative)
            hypothesis = {
                "narrative": narrative,
                "program": program,
                "level": level,
                "second": second,
                "cascade": cascade
            }
            await show_fortune(callback.from_user.id, state, hypothesis)
    else:
        await callback.message.answer("❌ Нет сохранённых результатов. Начни сначала /start")

async def start_verification(user_id, state: FSMContext):
    data = await state.get_data()
    answers = data.get('answers', {})
    
    narrative, second = get_narrative_from_answers(answers)
    program, cascade = get_ancient_program(answers)
    level = get_level(answers, narrative)
    
    hypothesis = {
        "narrative": narrative,
        "program": program,
        "level": level,
        "second": second,
        "cascade": cascade
    }
    
    logger.info(f"🔍 ГИПОТЕЗА: {hypothesis}")
    
    v_questions = get_verification_questions(hypothesis)
    
    await state.update_data(
        hypothesis=hypothesis,
        verification_round=1,
        verification_index=0,
        verification_answers=[],
        verification_questions=v_questions
    )
    
    mystic = get_mystic_symbol()
    await bot.send_message(
        user_id,
        f"{mystic} *Я почти вижу твою суть...*\n\n"
        f"Осталось проверить, не обманываешь ли ты сам себя."
    )
    await asyncio.sleep(2)
    
    await ask_verification_question(user_id, state)

async def show_fortune(user_id, state: FSMContext, hypothesis):
    data = await state.get_data()
    answers = data.get('answers', {})
    
    gender = answers.get('gender', 'М')
    age = answers.get('age', 30)
    user = await bot.get_chat(user_id)
    user_name = user.first_name or "путник"
    
    narrative = hypothesis["narrative"]
    program = hypothesis["program"]
    level = hypothesis["level"]
    second = hypothesis.get("second")
    cascade = hypothesis.get("cascade")
    
    last_id = data.get('last_message_id')
    if last_id:
        try:
            await bot.delete_message(user_id, last_id)
        except:
            pass
    
    logger.info(f"🔍 ФИНАЛ: нарратив={narrative}, программа={program}, уровень={level}")
    
    interpretation = get_final_interpretation(
        gender=gender, 
        narrative=narrative, 
        program=program, 
        level=level, 
        second_narrative=second,
        cascade=cascade,
        age=age
    )
    
    season = get_life_season(age)
    sep = get_separator()
    mystic = get_mystic_symbol()
    
    narrative_names = {
        "СБ": "Власть",
        "ТФ": "Труд",
        "УБ": "Знание",
        "ЧВ": "Внимание"
    }
    
    program_names = {
        "F1": "⚔️ Бей",
        "F2": "🏃 Беги",
        "F3": "🧊 Замри",
        "F4": "😶 Притворись",
        "F5": "🙏 Заискивай",
        "F6": "🏳️ Сдайся"
    }
    
    header = (
        f"{mystic} *Судьба {user_name}* {mystic}\n\n"
        f"{sep}\n"
        f"🌿 {season} — {age} лет\n"
        f"📜 Твой мир: *{narrative_names[narrative]}*\n"
        f"⚡ Твоя программа: *{program_names[program]}*\n"
        f"📊 Твой уровень: *{level}*\n"
        f"{sep}\n\n"
    )
    
    await bot.send_chat_action(user_id, action="typing")
    await asyncio.sleep(2)
    
    full_text = header + interpretation
    
    if len(full_text) > 4000:
        mid = len(full_text) // 2
        break_point = full_text.rfind('\n', 0, mid)
        if break_point == -1:
            break_point = mid
        
        part1 = full_text[:break_point]
        part2 = full_text[break_point:]
        
        await bot.send_message(user_id, part1)
        await asyncio.sleep(1)
        await bot.send_message(user_id, part2)
    else:
        await bot.send_message(user_id, full_text)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Ещё раз", callback_data="restart")
    builder.adjust(1)
    
    await bot.send_message(
        user_id,
        f"{mystic} *Что дальше?* {mystic}\n\n"
        f"Хочешь заглянуть в судьбу снова?",
        reply_markup=builder.as_markup()
    )
    
    await state.clear()

# ==================== ЗАПУСК ====================

async def main():
    print("\n" + "="*60)
    print("🔮 ТАЙНЫЙ ШЁПОТ v5.0 — 216 УНИКАЛЬНЫХ ПОРТРЕТОВ")
    print("="*60)
    print("🚀 Бот запущен и готов к работе...")
    print("📊 4 нарратива × 6 программ × 6 уровней = 216 комбинаций")
    print("➕ Второй нарратив и каскады добавляют глубины\n")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
