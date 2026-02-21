#!/usr/bin/env python3
"""
🧠 ПСИХОЛОГИЧЕСКИЙ ПРОФАЙЛЕР: ТРИ ТЕСТА ЛИЧНОСТИ
Версия 5.0 - Базовый тест + MBTI + Психология близости
"""

import os
import logging
import random
import asyncio
import sys
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
    raise ValueError("❌ Токен не найден! Проверьте файл .env")

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==================== СОСТОЯНИЯ ====================

class UserState(StatesGroup):
    # Основные этапы
    question_index = State()        # Индекс текущего вопроса
    answers = State()               # Все ответы
    last_message_id = State()       # ID последнего сообщения
    gender = State()                # Пол пользователя
    age_group = State()             # Возрастная группа
    test_mode = State()              # Режим теста: "original", "mbti", "sexual"
    test_completed = State()         # Флаг завершения теста
    
    # Этап верификации (для классического режима)
    hypothesis = State()            # Текущая гипотеза {нарратив, программа, уровень}
    verification_round = State()    # Номер попытки верификации
    verification_questions = State() # Список верификационных вопросов
    verification_index = State()     # Индекс текущего верификационного вопроса
    verification_answers = State()   # Ответы на верификацию
    
    # Для MBTI
    mbti_questions = State()         # Список вопросов MBTI
    mbti_total = State()             # Общее количество MBTI вопросов
    
    # Для сексуального теста
    sexual_current = State()         # Индекс текущего вопроса
    sexual_scores = State()          # Баллы по категориям
    sexual_last_answered = State()   # Последний отвеченный вопрос
    sexual_processing = State()      # Флаг обработки

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_age_range(age: int) -> str:
    """Определяет возрастную категорию"""
    if age < 20: return "🌱 до 20 лет"
    elif age < 25: return "🌿 20-25 лет"
    elif age < 30: return "🍀 25-30 лет"
    elif age < 35: return "🌳 30-35 лет"
    elif age < 40: return "🌲 35-40 лет"
    elif age < 45: return "🍁 40-45 лет"
    elif age < 50: return "🍂 45-50 лет"
    else: return "🍃 50-55 лет"

def get_life_season(age: int) -> str:
    """Определяет возрастную категорию (для обратной совместимости)"""
    return get_age_range(age)

def get_progress_bar(current, total, length=10):
    """Возвращает прогресс-бар"""
    filled = int((current / total) * length)
    return "█" * filled + "░" * (length - filled)


# ==================== ВОПРОС 0: ПОЛ ====================
GENDER_QUESTION = {
    "text": "Ваш пол:",
    "options": {
        "М": {"text": "👨 Мужской", "scores": {"gender": "М"}},
        "Ж": {"text": "👩 Женский", "scores": {"gender": "Ж"}}
    }
}

# ==================== ВОПРОС 1: ВОЗРАСТ ====================
AGE_QUESTION = {
    "text": "Ваш возраст:",
    "options": {
        "1": {"text": "20-25 лет", "scores": {"age": 22, "age_group": "YOUNG_ADULT"}},
        "2": {"text": "25-30 лет", "scores": {"age": 27, "age_group": "YOUNG_ADULT"}},
        "3": {"text": "30-35 лет", "scores": {"age": 32, "age_group": "ADULT"}},
        "4": {"text": "35-40 лет", "scores": {"age": 37, "age_group": "ADULT"}},
        "5": {"text": "40-45 лет", "scores": {"age": 42, "age_group": "MIDDLE"}},
        "6": {"text": "45-50 лет", "scores": {"age": 47, "age_group": "MIDDLE"}},
        "7": {"text": "50-55 лет", "scores": {"age": 52, "age_group": "MATURE"}}
    }
}

# ==================== ИМПОРТ МОДУЛЕЙ ====================

# Базовый тест
try:
    from interpretations import get_interpretation, NARRATIVE_NAMES, MALE_STRATEGIES, FEMALE_STRATEGIES
    logger.info(f"✅ Модуль интерпретаций загружен успешно")
    logger.info(f"📊 Мужских стратегий: {len(MALE_STRATEGIES)}")
    logger.info(f"📊 Женских стратегий: {len(FEMALE_STRATEGIES)}")
    
    if FEMALE_STRATEGIES:
        female_keys = list(FEMALE_STRATEGIES.keys())
        logger.info(f"📝 Примеры женских ключей: {female_keys[:5]}")
        
        test_keys = ["ЧВ_3_F3", "СБ_3_F3", "ТФ_3_F3", "УБ_3_F3"]
        for key in test_keys:
            if key in FEMALE_STRATEGIES:
                logger.info(f"✅ Найден ключ {key}")
            else:
                logger.warning(f"⚠️ Отсутствует ключ {key}")
    else:
        logger.error("❌ ЖЕНСКИЕ СТРАТЕГИИ НЕ ЗАГРУЖЕНЫ!")
        
except Exception as e:
    logger.error(f"❌ Ошибка загрузки интерпретаций: {e}")
    NARRATIVE_NAMES = {"СБ": "⚡ Силовой мир", "ТФ": "🔧 Мир труда", "УБ": "📚 Мир знаний", "ЧВ": "🎭 Мир внимания"}
    MALE_STRATEGIES = {}
    FEMALE_STRATEGIES = {}
    
    def get_interpretation(gender, narrative, level, age, program, second_narrative, third_narrative):
        return f"Интерпретация для {narrative} уровня {level}"

# MBTI тест
try:
    from mbti_questions import get_mbti_questions, MBTI_SCALE, calculate_mbti_type, get_mbti_interpretation
    logger.info(f"✅ Модуль MBTI загружен успешно")
    
    test_questions = get_mbti_questions("М")
    logger.info(f"📊 Загружено {len(test_questions)} MBTI вопросов")
    
except Exception as e:
    logger.error(f"❌ Ошибка загрузки MBTI: {e}")
    MBTI_SCALE = {
        "1": {"text": "❌ Совершенно не согласен", "value": 1},
        "2": {"text": "⚠️ Скорее не согласен", "value": 2},
        "3": {"text": "⚪ Нейтрально", "value": 3},
        "4": {"text": "✅ Скорее согласен", "value": 4},
        "5": {"text": "👍 Полностью согласен", "value": 5}
    }
    
    def get_mbti_questions(gender):
        questions = []
        for i in range(81):
            questions.append({
                "text": f"Тестовый вопрос MBTI #{i+1}. Оцените по шкале от 1 до 5.",
                "dimension": "EI",
                "direction": "E",
                "reverse": False,
                "index": i
            })
        return questions
    
    def calculate_mbti_type(answers):
        return {"type": "ISTJ", "type_name": "Инспектор", "preferences": {"EI": 0, "SN": 0, "TF": 0, "JP": 0}, "validation": {"warnings": [], "valid": True}}
    
    def get_mbti_interpretation(mbti_result, gender, age):
        return "MBTI интерпретация временно недоступна"

# Сексуальный тест
try:
    from sexual_questions import SEXUAL_QUESTIONS
    from sexual_interpretations import (
        TEMPERAMENT_TYPES, FETISH_TYPES, FORMATS,
        get_temperament_type, get_top_fetishes, 
        get_format_readiness, format_sexual_profile
    )
    from sexual_handlers import (
        sexual_test_start, sexual_ask_question,
        sexual_handle_answer, sexual_finish, sexual_premium
    )
    logger.info(f"✅ Модуль сексуального теста загружен успешно")
    logger.info(f"📊 Загружено {len(SEXUAL_QUESTIONS)} сексуальных вопросов")
    logger.info(f"📊 Типов темперамента: {len(TEMPERAMENT_TYPES)}")
    logger.info(f"📊 Типов фетишей: {len(FETISH_TYPES)}")
except Exception as e:
    logger.error(f"❌ Ошибка загрузки сексуального теста: {e}")
    SEXUAL_QUESTIONS = []
    TEMPERAMENT_TYPES = {}
    FETISH_TYPES = {}
    FORMATS = {}
    
    def get_temperament_type(scores): 
        return {"name": "Не определен", "emoji": "❓", "description": "Временная заглушка"}
    
    def get_top_fetishes(scores, top_n=3): 
        return []
    
    def get_format_readiness(scores): 
        return {"ready": [], "interested": [], "not_interested": []}
    
    def format_sexual_profile(a,b,c): 
        return "Сексуальный профиль временно недоступен"
    
    async def sexual_test_start(*args, **kwargs): pass
    async def sexual_ask_question(*args, **kwargs): pass
    async def sexual_handle_answer(*args, **kwargs): pass
    async def sexual_finish(*args, **kwargs): pass
    async def sexual_premium(*args, **kwargs): pass
# ==================== БЛОК 1: НАРРАТИВ (8 вопросов) ====================
def get_narrative_questions(gender, age_group):
    """Возвращает вопросы для определения нарратива с учетом пола и возраста"""
    
    if gender == "М":
        if age_group in ["YOUNG", "YOUNG_ADULT"]:
            # Молодые мужчины
            return [
                {  # Вопрос 2. Свободное время
                    "text": "Как вы обычно проводите свободное время?",
                    "options": {
                        "1": {"text": "🏋️ Спорт или компьютерные игры", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🔧 Что-то мастерю/ремонтирую", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "📚 Смотрю образовательный контент", "scores": {"narrative": "УБ"}},
                        "4": {"text": "🍻 Встречаюсь с друзьями", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 3. Что ценишь в людях
                    "text": "Какое качество вы больше всего цените в людях?",
                    "options": {
                        "1": {"text": "💪 Уверенность, характер", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🤝 Надёжность, ответственность", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "🧠 Ум, интеллект", "scores": {"narrative": "УБ"}},
                        "4": {"text": "😊 Чувство юмора, лёгкость", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 4. Комплимент
                    "text": "Какой комплимент вам наиболее приятен?",
                    "options": {
                        "1": {"text": "👑 «Ты крутой, тебя уважают»", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🛡️ «На тебя всегда можно положиться»", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "🎓 «Ты очень умный»", "scores": {"narrative": "УБ"}},
                        "4": {"text": "🎉 «С тобой очень весело»", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 5. Новая компания
                    "text": "В незнакомой компании вы обычно...",
                    "options": {
                        "1": {"text": "👀 Присматриваюсь, кто здесь главный", "scores": {"narrative": "СБ"}},
                        "2": {"text": "💼 Ищу, с кем можно поговорить о деле", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👂 Слушаю, о чем говорят", "scores": {"narrative": "УБ"}},
                        "4": {"text": "🗣️ Легко знакомлюсь со всеми", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 6. Деньги
                    "text": "Если бы у вас появилась свободная тысяча рублей, вы бы потратили на...",
                    "options": {
                        "1": {"text": "⌚ Что-то статусное (кроссовки, часы)", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🔨 Полезный инструмент или вещь", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "📖 Книгу или обучающий курс", "scores": {"narrative": "УБ"}},
                        "4": {"text": "🎉 Поход с друзьями", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 7. Что бесит
                    "text": "Что вас больше всего раздражает в людях?",
                    "options": {
                        "1": {"text": "👊 Панибратство, неуважение", "scores": {"narrative": "СБ"}},
                        "2": {"text": "📉 Безответственность, халтура", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "🤔 Глупость, недалёкость", "scores": {"narrative": "УБ"}},
                        "4": {"text": "😴 Скука, с ними неинтересно", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 8. Подарок
                    "text": "Какой подарок вас порадует больше всего?",
                    "options": {
                        "1": {"text": "💎 Дорогая статусная вещь", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🛠️ Что-то полезное для дома/работы", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "📚 Интеллектуальная игра, книга", "scores": {"narrative": "УБ"}},
                        "4": {"text": "🎫 Впечатление (билет на концерт)", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 9. Страх
                    "text": "Чего вы боитесь больше всего?",
                    "options": {
                        "1": {"text": "👎 Потерять уважение, стать никем", "scores": {"narrative": "СБ"}},
                        "2": {"text": "💰 Остаться без денег, без работы", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "🤦 Показаться глупым", "scores": {"narrative": "УБ"}},
                        "4": {"text": "😔 Одиночества", "scores": {"narrative": "ЧВ"}}
                    }
                }
            ]
        else:
            # Зрелые мужчины
            return [
                {  # Вопрос 2. Свободное время
                    "text": "Как вы предпочитаете проводить свободное время?",
                    "options": {
                        "1": {"text": "🍖 С друзьями, шашлыки, баня", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🏠 Дома, с семьёй, по хозяйству", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "📖 За книгой, познавательное", "scores": {"narrative": "УБ"}},
                        "4": {"text": "✈️ Путешествия, выезды на природу", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 3. Что ценишь в людях
                    "text": "Что для вас главное в человеке?",
                    "options": {
                        "1": {"text": "💪 Характер, внутренний стержень", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🤝 Порядочность, надёжность", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "🧠 Мудрость, жизненный опыт", "scores": {"narrative": "УБ"}},
                        "4": {"text": "❤️ Душевность, теплота", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 4. Комплимент
                    "text": "Какие слова для вас самые дорогие?",
                    "options": {
                        "1": {"text": "👑 «Ты добился всего сам»", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🛡️ «На тебя можно положиться»", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "🎓 «С тобой интересно говорить»", "scores": {"narrative": "УБ"}},
                        "4": {"text": "😊 «С тобой хорошо и спокойно»", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 5. Новая компания
                    "text": "В незнакомой компании вы обычно...",
                    "options": {
                        "1": {"text": "👀 Присматриваюсь, кто здесь главный", "scores": {"narrative": "СБ"}},
                        "2": {"text": "💼 Ищу, с кем можно поговорить по делу", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👂 Слушаю, вникаю в разговоры", "scores": {"narrative": "УБ"}},
                        "4": {"text": "🗣️ Легко общаюсь со всеми", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 6. Деньги
                    "text": "На что вы потратите неожиданную премию?",
                    "options": {
                        "1": {"text": "⌚ На что-то статусное (часы, машина)", "scores": {"narrative": "СБ"}},
                        "2": {"text": "💰 Отложу, вложу в дело", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "📚 На обучение, саморазвитие", "scores": {"narrative": "УБ"}},
                        "4": {"text": "✈️ На путешествие, впечатления", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 7. Что бесит
                    "text": "Что вас раздражает в других?",
                    "options": {
                        "1": {"text": "👊 Неуважение, панибратство", "scores": {"narrative": "СБ"}},
                        "2": {"text": "📉 Безответственность", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "🤔 Глупость, нежелание думать", "scores": {"narrative": "УБ"}},
                        "4": {"text": "😴 Пустота, с ними не о чем говорить", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 8. Подарок
                    "text": "Какой подарок вас обрадует?",
                    "options": {
                        "1": {"text": "💎 Дорогой, статусный", "scores": {"narrative": "СБ"}},
                        "2": {"text": "🛠️ Полезный, нужный в хозяйстве", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "📚 Книга, редкое издание", "scores": {"narrative": "УБ"}},
                        "4": {"text": "🎫 Впечатление, путешествие", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 9. Страх
                    "text": "Чего вы опасаетесь в жизни?",
                    "options": {
                        "1": {"text": "👎 Потерять уважение, статус", "scores": {"narrative": "СБ"}},
                        "2": {"text": "💰 Остаться без средств", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "🤦 Деградировать, отупеть", "scores": {"narrative": "УБ"}},
                        "4": {"text": "😔 Одиночества", "scores": {"narrative": "ЧВ"}}
                    }
                }
            ]
    else:  # Женщины
        if age_group in ["YOUNG", "YOUNG_ADULT"]:
            # Молодые женщины
            return [
                {  # Вопрос 2. Свободное время
                    "text": "Как вы любите проводить выходной?",
                    "options": {
                        "1": {"text": "👯 С подругами, по магазинам, в кафе", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "🏠 Дома, с семьёй, готовлю, убираю", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "💪 Занимаюсь собой, спорт, уход", "scores": {"narrative": "СБ"}},
                        "4": {"text": "📚 Читаю, смотрю познавательное", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 3. Что ценишь в людях
                    "text": "Что для вас важно в человеке?",
                    "options": {
                        "1": {"text": "😊 Чувство юмора, лёгкость", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "🤝 Надёжность, забота", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "💪 Уверенность, сила", "scores": {"narrative": "СБ"}},
                        "4": {"text": "🧠 Ум, интеллект", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 4. Комплимент
                    "text": "От какого комплимента вам приятнее?",
                    "options": {
                        "1": {"text": "✨ «Ты красивая, стильная»", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "💝 «Ты заботливая, добрая»", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👑 «Ты сильная, с характером»", "scores": {"narrative": "СБ"}},
                        "4": {"text": "🎓 «С тобой интересно»", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 5. Новая компания
                    "text": "В новой компании вы...",
                    "options": {
                        "1": {"text": "🗣️ Со всеми знакомлюсь, общаюсь", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "👀 Присматриваюсь, слушаю", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👑 Оцениваю, кто тут главный", "scores": {"narrative": "СБ"}},
                        "4": {"text": "👂 Наблюдаю, анализирую", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 6. Деньги
                    "text": "На что потратите неожиданную сумму?",
                    "options": {
                        "1": {"text": "👗 На одежду, косметику", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "💰 Отложу, на будущее", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "💎 На что-то статусное (сумка, часы)", "scores": {"narrative": "СБ"}},
                        "4": {"text": "📚 На курсы, обучение", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 7. Что бесит
                    "text": "Что вас раздражает в других?",
                    "options": {
                        "1": {"text": "😴 Скучные, с ними неинтересно", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "📉 Безответственные", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👊 Хамство, неуважение", "scores": {"narrative": "СБ"}},
                        "4": {"text": "🤔 Глупость, недалёкость", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 8. Подарок
                    "text": "Какой подарок вас порадует?",
                    "options": {
                        "1": {"text": "💍 Красивая вещь, украшение", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "🎁 Что-то нужное, полезное", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "💎 Что-то дорогое, статусное", "scores": {"narrative": "СБ"}},
                        "4": {"text": "📚 Книга, курс, развитие", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 9. Страх
                    "text": "Чего вы боитесь больше всего?",
                    "options": {
                        "1": {"text": "😔 Одиночества", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "💰 Бедности, нужды", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👎 Потерять уважение, статус", "scores": {"narrative": "СБ"}},
                        "4": {"text": "🤦 Глупости, деградации", "scores": {"narrative": "УБ"}}
                    }
                }
            ]
        else:
            # Зрелые женщины
            return [
                {  # Вопрос 2. Свободное время
                    "text": "Как вы любите проводить время?",
                    "options": {
                        "1": {"text": "👨‍👩‍👧‍👦 С семьёй, с детьми/внуками", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "🏡 По дому, на даче", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👯 С подругами, встречи", "scores": {"narrative": "СБ"}},
                        "4": {"text": "📚 Читаю, узнаю новое", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 3. Что ценишь в людях
                    "text": "Что для вас главное в человеке?",
                    "options": {
                        "1": {"text": "❤️ Доброта, душевность", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "🤝 Надёжность, порядочность", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "💪 Характер, достоинство", "scores": {"narrative": "СБ"}},
                        "4": {"text": "🧠 Мудрость, опыт", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 4. Комплимент
                    "text": "Какие слова для вас дороги?",
                    "options": {
                        "1": {"text": "👩‍👧 «Ты замечательная мать/бабушка»", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "🛡️ «На тебя можно положиться»", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👑 «Тебя уважают»", "scores": {"narrative": "СБ"}},
                        "4": {"text": "🎓 «Ты мудрая»", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 5. Новая компания
                    "text": "В незнакомой компании вы...",
                    "options": {
                        "1": {"text": "🗣️ Легко общаюсь со всеми", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "👀 Присматриваюсь, не сразу открываюсь", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👑 Оцениваю, кто здесь главный", "scores": {"narrative": "СБ"}},
                        "4": {"text": "👂 Наблюдаю, слушаю", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 6. Деньги
                    "text": "На что потратите неожиданную сумму?",
                    "options": {
                        "1": {"text": "👨‍👩‍👧 На детей, внуков, семью", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "💰 Отложу, на старость", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "💎 На что-то статусное, дорогое", "scores": {"narrative": "СБ"}},
                        "4": {"text": "✈️ На путешествие, впечатления", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 7. Что бесит
                    "text": "Что вас раздражает в людях?",
                    "options": {
                        "1": {"text": "💔 Черствость, равнодушие", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "📉 Безответственность", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👊 Хамство, неуважение", "scores": {"narrative": "СБ"}},
                        "4": {"text": "🤔 Глупость, нежелание думать", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 8. Подарок
                    "text": "Какой подарок вас порадует?",
                    "options": {
                        "1": {"text": "💝 Внимание, забота, сюрприз", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "🎁 Что-то нужное, полезное", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "💎 Что-то дорогое, статусное", "scores": {"narrative": "СБ"}},
                        "4": {"text": "📚 Книга, впечатления", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 9. Страх
                    "text": "Чего вы опасаетесь?",
                    "options": {
                        "1": {"text": "😔 Одиночества", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "💰 Бедности, немощи", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "👎 Потерять уважение", "scores": {"narrative": "СБ"}},
                        "4": {"text": "🤦 Деградации", "scores": {"narrative": "УБ"}}
                    }
                }
            ]

# ==================== БЛОК 2: РЕСУРСЫ (10 вопросов) ====================
COMMON_RESOURCES_QUESTIONS = [
    {  # Вопрос 10. Образование
        "text": "Какое у вас образование?",
        "options": {
            "1": {"text": "🏫 Неполное среднее", "scores": {"education": 2, "edu_level": "LOW"}},
            "2": {"text": "📚 Среднее (школа)", "scores": {"education": 4, "edu_level": "MEDIUM"}},
            "3": {"text": "🎓 Среднее специальное", "scores": {"education": 6, "edu_level": "MEDIUM"}},
            "4": {"text": "🎓 Высшее", "scores": {"education": 8, "edu_level": "HIGH"}},
            "5": {"text": "📚 Два и более / учёная степень", "scores": {"education": 10, "edu_level": "VERY_HIGH"}}
        }
    },
    {  # Вопрос 11. Работа
        "text": "Кем вы работаете?",
        "options": {
            "1": {"text": "💤 Не работаю", "scores": {"job": "DEPENDENT", "income": 1}},
            "2": {"text": "🔧 Рабочий, персонал", "scores": {"job": "WORKER", "income": 3}},
            "3": {"text": "💼 Офисный работник", "scores": {"job": "OFFICE", "income": 4}},
            "4": {"text": "👨‍⚕️ Специалист (врач, учитель, инженер)", "scores": {"job": "PROFESSIONAL", "income": 5}},
            "5": {"text": "👔 Руководитель, начальник", "scores": {"job": "MANAGER", "income": 7}},
            "6": {"text": "💼 Свой бизнес", "scores": {"job": "BUSINESS", "income": 8}},
            "7": {"text": "💻 Фрилансер", "scores": {"job": "FREELANCE", "income": 5}},
            "8": {"text": "🎨 Творческая профессия", "scores": {"job": "CREATIVE", "income": 4}}
        }
    },
    {  # Вопрос 12. Доход
        "text": "Как вы оцениваете своё материальное положение?",
        "options": {
            "1": {"text": "🍞 Едва хватает на еду", "scores": {"money": 1}},
            "2": {"text": "💰 Хватает на жизнь", "scores": {"money": 3}},
            "3": {"text": "💳 Могу покупать крупные вещи", "scores": {"money": 5}},
            "4": {"text": "🏦 Обеспечен(а), есть накопления", "scores": {"money": 7}},
            "5": {"text": "💎 Богат(а), деньги не проблема", "scores": {"money": 9}}
        }
    },
    {  # Вопрос 13. Жильё
        "text": "Где вы живёте?",
        "options": {
            "1": {"text": "🏚️ Снимаю угол/комнату", "scores": {"housing": 1}},
            "2": {"text": "🏠 С родителями/родственниками", "scores": {"housing": 2}},
            "3": {"text": "🏢 Снимаю квартиру", "scores": {"housing": 3}},
            "4": {"text": "🏡 Своя квартира/дом", "scores": {"housing": 5}},
            "5": {"text": "🏘️ Несколько объектов", "scores": {"housing": 8}}
        }
    },
    {  # Вопрос 14. Рост
        "text": "Какой у вас рост?",
        "options": {
            "1": {"text": "📏 Ниже 160 см", "scores": {"height": 2}},
            "2": {"text": "📏 160-170 см", "scores": {"height": 4}},
            "3": {"text": "📏 170-180 см", "scores": {"height": 6}},
            "4": {"text": "📏 180-190 см", "scores": {"height": 8}},
            "5": {"text": "📏 Выше 190 см", "scores": {"height": 10}}
        }
    },
    {  # Вопрос 15. Внешность
        "text": "Как вы оцениваете свою внешность?",
        "options": {
            "1": {"text": "👤 Меня не замечают", "scores": {"looks": 2}},
            "2": {"text": "👤 Обычная внешность", "scores": {"looks": 4}},
            "3": {"text": "✨ Симпатичный(ая)", "scores": {"looks": 6}},
            "4": {"text": "🌟 Красивый(ая)", "scores": {"looks": 8}},
            "5": {"text": "💫 Модельная внешность", "scores": {"looks": 10}}
        }
    },
    {  # Вопрос 16. Здоровье
        "text": "Как часто вы болеете?",
        "options": {
            "1": {"text": "🏥 Постоянно", "scores": {"health": 2}},
            "2": {"text": "🤧 Несколько раз в год", "scores": {"health": 4}},
            "3": {"text": "😷 Раз в год", "scores": {"health": 6}},
            "4": {"text": "💪 Раз в несколько лет", "scores": {"health": 8}},
            "5": {"text": "🦸 Практически никогда", "scores": {"health": 10}}
        }
    },
    {  # Вопрос 17. Семейное положение
        "text": "Какое у вас семейное положение?",
        "options": {
            "1": {"text": "👤 Никогда не был(а) в браке", "scores": {"marriage": 0, "marriages": 0}},
            "2": {"text": "💑 В браке / в отношениях", "scores": {"marriage": 1, "marriages": 1}},
            "3": {"text": "💔 Разведен(а)", "scores": {"marriage": 0, "marriages": 1}},
            "4": {"text": "🕯️ Вдовец/вдова", "scores": {"marriage": 0, "marriages": 1}}
        }
    },
    {  # Вопрос 18. Дети
        "text": "Есть ли у вас дети?",
        "options": {
            "1": {"text": "👤 Нет детей", "scores": {"children": 0, "kids": 0}},
            "2": {"text": "👶 Один ребёнок", "scores": {"children": 1, "kids": 1}},
            "3": {"text": "👧👦 Двое детей", "scores": {"children": 2, "kids": 2}},
            "4": {"text": "👨‍👩‍👧‍👦 Трое и больше", "scores": {"children": 3, "kids": 3}}
        }
    },
    {  # Вопрос 19. Друзья
        "text": "Сколько у вас близких друзей?",
        "options": {
            "1": {"text": "👤 Никого, я один(а)", "scores": {"friends": 1, "social": 1}},
            "2": {"text": "👥 1-2 друга", "scores": {"friends": 3, "social": 3}},
            "3": {"text": "👥 3-5 друзей", "scores": {"friends": 5, "social": 5}},
            "4": {"text": "👥 5-10 человек", "scores": {"friends": 7, "social": 7}},
            "5": {"text": "👥 Много друзей", "scores": {"friends": 9, "social": 9}}
        }
    }
]

# ==================== БЛОК 3: ПОВЕДЕНЧЕСКИЕ СТРАТЕГИИ (7 вопросов) ====================
def get_ancient_program_questions(gender):
    """Возвращает вопросы для определения поведенческих стратегий (F1-F6)"""
    
    # Общие для всех вопросы
    common = [
        {  # Вопрос 20. Спорт
            "text": "Каким спортом вы занимаетесь?",
            "options": {
                "1": {"text": "😴 Никаким, не люблю", "scores": {"ancient": "F2"}},
                "2": {"text": "🏃 Бег, плавание", "scores": {"ancient": "F2"}},
                "3": {"text": "🏋️ Тренажерный зал", "scores": {"ancient": "F1"}},
                "4": {"text": "🥊 Единоборства, бокс", "scores": {"ancient": "F1"}},
                "5": {"text": "🧘 Йога, растяжка", "scores": {"ancient": "F3"}}
            }
        },
        {  # Вопрос 21. Конфликты
            "text": "Если кто-то лезет без очереди, вы...",
            "options": {
                "1": {"text": "😶 Молчу, не хочу связываться", "scores": {"ancient": "F2"}},
                "2": {"text": "📱 Смотрю в телефон, не замечаю", "scores": {"ancient": "F4"}},
                "3": {"text": "⏳ Жду, может кто-то другой скажет", "scores": {"ancient": "F3"}},
                "4": {"text": "😊 Вежливо делаю замечание", "scores": {"ancient": "F5"}},
                "5": {"text": "😠 Сразу высказываю", "scores": {"ancient": "F1"}}
            }
        },
        {  # Вопрос 22. Соцсети
            "text": "Как часто вы выкладываете свои фото?",
            "options": {
                "1": {"text": "🚫 Никогда, не люблю", "scores": {"ancient": "F2"}},
                "2": {"text": "📱 Только в сторис, на день", "scores": {"ancient": "F3"}},
                "3": {"text": "📅 Раз в месяц, по настроению", "scores": {"ancient": "F6"}},
                "4": {"text": "📸 Регулярно, веду страницу", "scores": {"ancient": "F5"}},
                "5": {"text": "📷 Каждый день, блог", "scores": {"ancient": "F1"}}
            }
        },
        {  # Вопрос 23. Отношение к телу
            "text": "Как вы относитесь к своему телу?",
            "options": {
                "1": {"text": "😔 Стесняюсь, не нравится", "scores": {"ancient": "F2"}},
                "2": {"text": "😐 Нормально, не задумываюсь", "scores": {"ancient": "F3"}},
                "3": {"text": "🙂 Принимаю, что есть", "scores": {"ancient": "F6"}},
                "4": {"text": "💆 Забочусь, ухаживаю", "scores": {"ancient": "F5"}},
                "5": {"text": "💪 Горжусь, показываю", "scores": {"ancient": "F1"}}
            }
        },
        {  # Вопрос 24. Сны
            "text": "Какие сны вам чаще снятся?",
            "options": {
                "1": {"text": "⚔️ Драки, погони, опасность", "scores": {"ancient": "F1"}},
                "2": {"text": "🏃 Что убегаю, прячусь", "scores": {"ancient": "F2"}},
                "3": {"text": "🧊 Зависаю, не могу пошевелиться", "scores": {"ancient": "F3"}},
                "4": {"text": "🎬 Странные, как в кино", "scores": {"ancient": "F4"}},
                "5": {"text": "😴 Не помню, редко снятся", "scores": {"ancient": "F6"}}
            }
        }
    ]
    
    # Гендерно-специфичные вопросы
    if gender == "М":
        male_specific = [
            {  # Вопрос 25. Баня
                "text": "Как часто вы ходите в баню?",
                "options": {
                    "1": {"text": "🚫 Никогда, не люблю", "scores": {"ancient": "F2"}},
                    "2": {"text": "📅 Раз в год, с работы", "scores": {"ancient": "F5"}},
                    "3": {"text": "🍻 Иногда с друзьями", "scores": {"ancient": "F3"}},
                    "4": {"text": "📆 Регулярно, раз в месяц", "scores": {"ancient": "F6"}},
                    "5": {"text": "🔥 Часто, своя баня", "scores": {"ancient": "F1"}}
                }
            },
            {  # Вопрос 26. Борода
                "text": "Как у вас с бородой?",
                "options": {
                    "1": {"text": "🪒 Не растёт, гладко брею", "scores": {"ancient": "F6"}},
                    "2": {"text": "🌱 Щетина, немного", "scores": {"ancient": "F3"}},
                    "3": {"text": "🧔 Небольшая бородка", "scores": {"ancient": "F5"}},
                    "4": {"text": "🧔 Густая борода", "scores": {"ancient": "F1"}},
                    "5": {"text": "🧔 Очень густая", "scores": {"ancient": "F1"}}
                }
            },
            {  # Вопрос 27. Машина
                "text": "Какая у вас машина?",
                "options": {
                    "1": {"text": "🚫 Нет, не нужна", "scores": {"ancient": "F2"}},
                    "2": {"text": "🚗 Эконом, чтобы ездила", "scores": {"ancient": "F3"}},
                    "3": {"text": "🚙 Надёжная, семейная", "scores": {"ancient": "F5"}},
                    "4": {"text": "🏎️ Спортивная, быстрая", "scores": {"ancient": "F1"}},
                    "5": {"text": "💎 Дорогая, статусная", "scores": {"ancient": "F1"}}
                }
            }
        ]
        return common + male_specific
    else:
        # Женщины
        female_specific = [
            {  # Вопрос 25. Одежда
                "text": "Как вы одеваетесь летом?",
                "options": {
                    "1": {"text": "🧥 Закрыто, не люблю открытое", "scores": {"ancient": "F2"}},
                    "2": {"text": "👕 Как удобно, не задумываюсь", "scores": {"ancient": "F3"}},
                    "3": {"text": "👚 Скромно, но аккуратно", "scores": {"ancient": "F5"}},
                    "4": {"text": "👗 Открыто, нравится внимание", "scores": {"ancient": "F1"}},
                    "5": {"text": "👙 Очень откровенно", "scores": {"ancient": "F1"}}
                }
            },
            {  # Вопрос 26. Отношения
                "text": "В отношениях с мужчиной вы чаще...",
                "options": {
                    "1": {"text": "🤝 Уступаю, чтобы не ссориться", "scores": {"ancient": "F5"}},
                    "2": {"text": "😶 Молчу, терплю", "scores": {"ancient": "F3"}},
                    "3": {"text": "🚶 Ухожу, если что не так", "scores": {"ancient": "F2"}},
                    "4": {"text": "💬 Договариваюсь, ищу компромисс", "scores": {"ancient": "F6"}},
                    "5": {"text": "👊 Настаиваю на своём", "scores": {"ancient": "F1"}}
                }
            },
            {  # Вопрос 27. Интим
                "text": "В интимной близости вам важнее...",
                "options": {
                    "1": {"text": "💝 Чтобы партнёр был доволен", "scores": {"ancient": "F5"}},
                    "2": {"text": "😌 Чтобы я была довольна", "scores": {"ancient": "F1"}},
                    "3": {"text": "😐 Чтобы было комфортно", "scores": {"ancient": "F3"}},
                    "4": {"text": "😣 Чтобы не было больно", "scores": {"ancient": "F2"}},
                    "5": {"text": "🤷 Мне всё равно", "scores": {"ancient": "F6"}}
                }
            }
        ]
        return common + female_specific

# ==================== БЛОК 4: ВЕРИФИКАЦИОННЫЕ ВОПРОСЫ ====================

def get_verification_questions(hypothesis):
    """
    Возвращает вопросы для проверки гипотезы
    hypothesis = {"narrative": "СБ", "program": "F1", "level": 3}
    """
    narrative = hypothesis["narrative"]
    program = hypothesis["program"]
    
    logger.info(f"🔍 Получаем верификационные вопросы для {narrative}+{program}")
    
    # База верификационных вопросов (полная версия)
    verification_db = {
        # ===== СБ + F1 =====
        ("СБ", "F1"): [
            {
                "text": "Вспомните случай из детства, когда вас сильно обидели. Что вы сделали?",
                "options": {
                    "1": {"text": "⚔️ Дал сдачи, даже если был слабее", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "🏃 Убежал и спрятался", "scores": {"verify": "ЧВ+F2"}},
                    "3": {"text": "🧊 Замер и терпел", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "😢 Заплакал и пошёл жаловаться", "scores": {"verify": "ТФ+F5"}}
                }
            },
            {
                "text": "Кого вы больше уважаете?",
                "options": {
                    "1": {"text": "🦁 Того, кто может постоять за себя", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "🐇 Того, кто избегает конфликтов", "scores": {"verify": "ЧВ+F2"}},
                    "3": {"text": "🦉 Того, кто всё просчитывает", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "🐕 Того, кто со всеми дружит", "scores": {"verify": "ТФ+F5"}}
                }
            },
            {
                "text": "Если бы вы были животным, каким?",
                "options": {
                    "1": {"text": "🦁 Лев, волк", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "🐇 Заяц, лань", "scores": {"verify": "ЧВ+F2"}},
                    "3": {"text": "🦉 Сова, лис", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "🐕 Собака (домашняя)", "scores": {"verify": "ТФ+F5"}}
                }
            }
        ],
        
        # ===== СБ + F2 =====
        ("СБ", "F2"): [
            {
                "text": "Когда назревает конфликт, вы...",
                "options": {
                    "1": {"text": "⚔️ Иду на обострение", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "🏃 Стараюсь уйти, избежать", "scores": {"verify": "СБ+F2"}},
                    "3": {"text": "🧊 Замираю и жду", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "🤝 Пытаюсь договориться", "scores": {"verify": "ТФ+F5"}}
                }
            },
            {
                "text": "Что для вас страшнее?",
                "options": {
                    "1": {"text": "👎 Потерять уважение", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "⚠️ Оказаться в опасности", "scores": {"verify": "СБ+F2"}},
                    "3": {"text": "🤦 Выглядеть глупо", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "😔 Быть отвергнутым", "scores": {"verify": "ЧВ+F5"}}
                }
            }
        ],
        
        # ===== СБ + F3 =====
        ("СБ", "F3"): [
            {
                "text": "В стрессовой ситуации вы...",
                "options": {
                    "1": {"text": "⚔️ Нападаю первым", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "🧊 Ухожу в себя", "scores": {"verify": "СБ+F3"}},
                    "3": {"text": "🤔 Анализирую", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "🤝 Ищу поддержку", "scores": {"verify": "ЧВ+F5"}}
                }
            }
        ],
        
        # ===== СБ + F4 =====
        ("СБ", "F4"): [
            {
                "text": "Когда на вас давят, вы...",
                "options": {
                    "1": {"text": "⚔️ Давлю в ответ", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "👻 Делаю вид, что не замечаю", "scores": {"verify": "СБ+F4"}},
                    "3": {"text": "🧊 Замираю", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "🤝 Уступаю", "scores": {"verify": "ТФ+F5"}}
                }
            }
        ],
        
        # ===== СБ + F5 =====
        ("СБ", "F5"): [
            {
                "text": "Как вы ведёте себя с начальником?",
                "options": {
                    "1": {"text": "🤝 Стараюсь угодить, соглашаюсь", "scores": {"verify": "СБ+F5"}},
                    "2": {"text": "⚔️ Могу поспорить, если не прав", "scores": {"verify": "УБ+F1"}},
                    "3": {"text": "😐 Держусь независимо", "scores": {"verify": "ЧВ+F2"}},
                    "4": {"text": "👻 Делаю вид, что не замечаю", "scores": {"verify": "ТФ+F3"}}
                }
            },
            {
                "text": "Что вы чувствуете, когда вас критикуют?",
                "options": {
                    "1": {"text": "😢 Обиду и желание оправдаться", "scores": {"verify": "СБ+F5"}},
                    "2": {"text": "😠 Злость, хочется ответить", "scores": {"verify": "УБ+F1"}},
                    "3": {"text": "😳 Стыд, хочется провалиться", "scores": {"verify": "ЧВ+F2"}},
                    "4": {"text": "😐 Мне всё равно", "scores": {"verify": "ТФ+F6"}}
                }
            }
        ],
        
        # ===== СБ + F6 =====
        ("СБ", "F6"): [
            {
                "text": "Когда не получается добиться цели...",
                "options": {
                    "1": {"text": "⚔️ Усиливаю напор", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "😔 Бросаю, значит не судьба", "scores": {"verify": "СБ+F6"}},
                    "3": {"text": "🤔 Ищу другой путь", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "🤝 Прошу помощи", "scores": {"verify": "ЧВ+F5"}}
                }
            }
        ],
        
        # ===== ТФ + F1 =====
        ("ТФ", "F1"): [
            {
                "text": "Как вы добиваетесь целей?",
                "options": {
                    "1": {"text": "⚔️ Напролом, любой ценой", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "📋 Планомерно, шаг за шагом", "scores": {"verify": "ТФ+F1"}},
                    "3": {"text": "🔄 Ищу обходные пути", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "🤝 Через связи и знакомства", "scores": {"verify": "ЧВ+F5"}}
                }
            },
            {
                "text": "Что для вас главное в работе?",
                "options": {
                    "1": {"text": "🎯 Результат любой ценой", "scores": {"verify": "ТФ+F1"}},
                    "2": {"text": "⚖️ Стабильность", "scores": {"verify": "ТФ+F3"}},
                    "3": {"text": "💰 Деньги", "scores": {"verify": "ТФ+F5"}},
                    "4": {"text": "🏆 Признание", "scores": {"verify": "СБ+F5"}}
                }
            }
        ],
        
        # ===== ТФ + F2 =====
        ("ТФ", "F2"): [
            {
                "text": "Если на работе аврал...",
                "options": {
                    "1": {"text": "💪 Беру всё на себя", "scores": {"verify": "ТФ+F1"}},
                    "2": {"text": "🏃 Стараюсь исчезнуть", "scores": {"verify": "ТФ+F2"}},
                    "3": {"text": "🐢 Работаю в своём темпе", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "🤝 Ищу, кто поможет", "scores": {"verify": "ЧВ+F5"}}
                }
            }
        ],
        
        # ===== ТФ + F3 =====
        ("ТФ", "F3"): [
            {
                "text": "Когда на работе аврал, вы...",
                "options": {
                    "1": {"text": "😵 Теряюсь, не знаю за что хвататься", "scores": {"verify": "ТФ+F3"}},
                    "2": {"text": "💪 Мобилизуюсь и работаю быстрее", "scores": {"verify": "ТФ+F1"}},
                    "3": {"text": "🤝 Ищу, кто поможет", "scores": {"verify": "ЧВ+F5"}},
                    "4": {"text": "🧊 Ухожу в себя, отключаюсь", "scores": {"verify": "УБ+F4"}}
                }
            },
            {
                "text": "Как вы принимаете важные решения?",
                "options": {
                    "1": {"text": "🤔 Долго сомневаюсь, не решаюсь", "scores": {"verify": "ТФ+F3"}},
                    "2": {"text": "⚡ Быстро, интуитивно", "scores": {"verify": "СБ+F1"}},
                    "3": {"text": "🗣️ Советуюсь с другими", "scores": {"verify": "ЧВ+F5"}},
                    "4": {"text": "📊 Анализирую все варианты", "scores": {"verify": "УБ+F3"}}
                }
            }
        ],
        
        # ===== ТФ + F4 =====
        ("ТФ", "F4"): [
            {
                "text": "Когда начальник требует невозможного...",
                "options": {
                    "1": {"text": "⚔️ Спорю и доказываю", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "🏥 Ухожу в больничный", "scores": {"verify": "ТФ+F4"}},
                    "3": {"text": "👻 Делаю вид, что делаю", "scores": {"verify": "ТФ+F4"}},
                    "4": {"text": "🚪 Увольняюсь", "scores": {"verify": "ТФ+F2"}}
                }
            }
        ],
        
        # ===== ТФ + F5 =====
        ("ТФ", "F5"): [
            {
                "text": "Как вы строите отношения с начальством?",
                "options": {
                    "1": {"text": "🤝 Стараюсь угодить", "scores": {"verify": "ТФ+F5"}},
                    "2": {"text": "📏 Держу дистанцию", "scores": {"verify": "УБ+F3"}},
                    "3": {"text": "⚔️ Могу поспорить", "scores": {"verify": "СБ+F1"}},
                    "4": {"text": "😇 Подлизываюсь", "scores": {"verify": "ТФ+F5"}}
                }
            }
        ],
        
        # ===== ТФ + F6 =====
        ("ТФ", "F6"): [
            {
                "text": "Если не дают повышение...",
                "options": {
                    "1": {"text": "⚔️ Борюсь до конца", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "😔 Смиряюсь", "scores": {"verify": "ТФ+F6"}},
                    "3": {"text": "🚪 Ищу другую работу", "scores": {"verify": "ТФ+F2"}},
                    "4": {"text": "🤝 Прошу помощи у влиятельных лиц", "scores": {"verify": "ЧВ+F5"}}
                }
            }
        ],
        
        # ===== ЧВ + F1 =====
        ("ЧВ", "F1"): [
            {
                "text": "Как вы добиваетесь внимания?",
                "options": {
                    "1": {"text": "📢 Громко заявляю о себе", "scores": {"verify": "ЧВ+F1"}},
                    "2": {"text": "🤝 Помогаю другим", "scores": {"verify": "ЧВ+F5"}},
                    "3": {"text": "🌑 Ухожу в тень", "scores": {"verify": "ЧВ+F2"}},
                    "4": {"text": "🧠 Выделяюсь умом", "scores": {"verify": "УБ+F3"}}
                }
            }
        ],
        
        # ===== ЧВ + F2 =====
        ("ЧВ", "F2"): [
            {
                "text": "Как вы ведёте себя на вечеринках?",
                "options": {
                    "1": {"text": "🎉 Стараюсь быть в центре", "scores": {"verify": "ЧВ+F1"}},
                    "2": {"text": "👀 Держусь в стороне, наблюдаю", "scores": {"verify": "ЧВ+F2"}},
                    "3": {"text": "👥 Общаюсь только со знакомыми", "scores": {"verify": "ТФ+F3"}},
                    "4": {"text": "🚫 Вообще не хожу", "scores": {"verify": "УБ+F2"}}
                }
            },
            {
                "text": "Что для вас страшнее?",
                "options": {
                    "1": {"text": "🎯 Оказаться в центре внимания", "scores": {"verify": "ЧВ+F2"}},
                    "2": {"text": "💔 Быть отвергнутым", "scores": {"verify": "ЧВ+F5"}},
                    "3": {"text": "🤦 Выглядеть глупо", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "😠 Потерять контроль", "scores": {"verify": "СБ+F1"}}
                }
            }
        ],
        
        # ===== ЧВ + F3 =====
        ("ЧВ", "F3"): [
            {
                "text": "В новой компании вы...",
                "options": {
                    "1": {"text": "🗣️ Сразу знакомлюсь со всеми", "scores": {"verify": "ЧВ+F1"}},
                    "2": {"text": "😳 Стесняюсь, молчу", "scores": {"verify": "ЧВ+F3"}},
                    "3": {"text": "👀 Наблюдаю", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "🤝 Ищу одного человека", "scores": {"verify": "ТФ+F5"}}
                }
            }
        ],
        
        # ===== ЧВ + F4 =====
        ("ЧВ", "F4"): [
            {
                "text": "Когда вас игнорируют...",
                "options": {
                    "1": {"text": "📢 Добиваюсь внимания", "scores": {"verify": "ЧВ+F1"}},
                    "2": {"text": "😔 Ухожу в себя", "scores": {"verify": "ЧВ+F4"}},
                    "3": {"text": "😐 Делаю вид, что мне всё равно", "scores": {"verify": "ЧВ+F4"}},
                    "4": {"text": "👥 Нахожу других людей", "scores": {"verify": "ЧВ+F2"}}
                }
            }
        ],
        
        # ===== ЧВ + F5 =====
        ("ЧВ", "F5"): [
            {
                "text": "Как вы заводите друзей?",
                "options": {
                    "1": {"text": "🤝 Стараюсь быть полезным", "scores": {"verify": "ЧВ+F5"}},
                    "2": {"text": "⏳ Жду, когда позовут", "scores": {"verify": "ЧВ+F3"}},
                    "3": {"text": "🗣️ Сам предлагаю дружбу", "scores": {"verify": "ЧВ+F1"}},
                    "4": {"text": "😐 Мне никто не нужен", "scores": {"verify": "УБ+F4"}}
                }
            }
        ],
        
        # ===== ЧВ + F6 =====
        ("ЧВ", "F6"): [
            {
                "text": "Если вас не принимают в компанию...",
                "options": {
                    "1": {"text": "😔 Навязываюсь", "scores": {"verify": "ЧВ+F5"}},
                    "2": {"text": "😢 Ухожу и переживаю", "scores": {"verify": "ЧВ+F6"}},
                    "3": {"text": "👥 Нахожу других", "scores": {"verify": "ЧВ+F2"}},
                    "4": {"text": "😐 Мне всё равно", "scores": {"verify": "УБ+F4"}}
                }
            }
        ],
        
        # ===== УБ + F1 =====
        ("УБ", "F1"): [
            {
                "text": "В споре вы...",
                "options": {
                    "1": {"text": "⚔️ Настаиваю на своём", "scores": {"verify": "УБ+F1"}},
                    "2": {"text": "📊 Привожу аргументы", "scores": {"verify": "УБ+F3"}},
                    "3": {"text": "🤝 Уступаю", "scores": {"verify": "ТФ+F5"}},
                    "4": {"text": "🏃 Ухожу от спора", "scores": {"verify": "ЧВ+F2"}}
                }
            }
        ],
        
        # ===== УБ + F2 =====
        ("УБ", "F2"): [
            {
                "text": "Если вас критикуют...",
                "options": {
                    "1": {"text": "⚔️ Спорю и доказываю", "scores": {"verify": "УБ+F1"}},
                    "2": {"text": "🏃 Ухожу от разговора", "scores": {"verify": "УБ+F2"}},
                    "3": {"text": "😔 Замыкаюсь", "scores": {"verify": "ЧВ+F3"}},
                    "4": {"text": "👂 Прислушиваюсь", "scores": {"verify": "УБ+F3"}}
                }
            }
        ],
        
        # ===== УБ + F3 =====
        ("УБ", "F3"): [
            {
                "text": "Когда нужно быстро решить проблему...",
                "options": {
                    "1": {"text": "⚡ Действую интуитивно", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "🤔 Анализирую, но долго", "scores": {"verify": "УБ+F3"}},
                    "3": {"text": "🗣️ Прошу совета", "scores": {"verify": "ЧВ+F5"}},
                    "4": {"text": "⏳ Откладываю", "scores": {"verify": "ТФ+F3"}}
                }
            }
        ],
        
        # ===== УБ + F4 =====
        ("УБ", "F4"): [
            {
                "text": "В стрессовой ситуации вы...",
                "options": {
                    "1": {"text": "👻 Отключаюсь, как будто это не со мной", "scores": {"verify": "УБ+F4"}},
                    "2": {"text": "😰 Начинаю суетиться", "scores": {"verify": "ЧВ+F2"}},
                    "3": {"text": "🧊 Застываю, не могу пошевелиться", "scores": {"verify": "ТФ+F3"}},
                    "4": {"text": "⚔️ Действую агрессивно", "scores": {"verify": "СБ+F1"}}
                }
            },
            {
                "text": "Что говорят о вас близкие?",
                "options": {
                    "1": {"text": "☁️ Что я витаю в облаках", "scores": {"verify": "УБ+F4"}},
                    "2": {"text": "😭 Что я слишком эмоциональный", "scores": {"verify": "ЧВ+F2"}},
                    "3": {"text": "🛡️ Что я надёжный", "scores": {"verify": "ТФ+F3"}},
                    "4": {"text": "👊 Что я упрямый", "scores": {"verify": "СБ+F1"}}
                }
            }
        ],
        
        # ===== УБ + F5 =====
        ("УБ", "F5"): [
            {
                "text": "Как вы убеждаете людей?",
                "options": {
                    "1": {"text": "👊 Давлю авторитетом", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "📊 Привожу факты", "scores": {"verify": "УБ+F3"}},
                    "3": {"text": "🤝 Угождаю", "scores": {"verify": "УБ+F5"}},
                    "4": {"text": "✨ Очаровываю", "scores": {"verify": "ЧВ+F5"}}
                }
            }
        ],
        
        # ===== УБ + F6 =====
        ("УБ", "F6"): [
            {
                "text": "Если не можете решить задачу...",
                "options": {
                    "1": {"text": "⚔️ Бьюсь до конца", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "😔 Бросаю", "scores": {"verify": "УБ+F6"}},
                    "3": {"text": "🔄 Ищу другой способ", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "🗣️ Прошу помочь", "scores": {"verify": "ЧВ+F5"}}
                }
            }
        ]
    }
    
    # Ищем точное совпадение
    key = (narrative, program)
    if key in verification_db:
        questions = verification_db[key]
        logger.info(f"✅ Найдены специализированные вопросы ({len(questions)} шт.) для {key}")
        return questions
    
    # Если нет точного, возвращаем универсальные вопросы
    logger.info(f"⚠️ Спецвопросы для {key} не найдены, использую универсальные")
    return [
        {
            "text": "Как вы обычно реагируете на неожиданности?",
            "options": {
                "1": {"text": "⚔️ Сразу действую", "scores": {"verify": "F1"}},
                "2": {"text": "🏃 Стараюсь уйти от ситуации", "scores": {"verify": "F2"}},
                "3": {"text": "🧊 Замираю, оцениваю", "scores": {"verify": "F3"}},
                "4": {"text": "👻 Как будто не замечаю", "scores": {"verify": "F4"}}
            }
        },
        {
            "text": "Что для вас важнее в жизни?",
            "options": {
                "1": {"text": "👑 Быть уважаемым", "scores": {"verify": "СБ"}},
                "2": {"text": "💰 Быть обеспеченным", "scores": {"verify": "ТФ"}},
                "3": {"text": "🧠 Быть умным", "scores": {"verify": "УБ"}},
                "4": {"text": "❤️ Быть любимым", "scores": {"verify": "ЧВ"}}
            }
        }
    ]

# ==================== ФУНКЦИИ ОПРЕДЕЛЕНИЯ ====================

def get_narrative_from_answers(answers):
    """Определяет нарратив на основе ответов"""
    scores = {"СБ": 0, "ТФ": 0, "УБ": 0, "ЧВ": 0}
    
    logger.info(f"📋 Все ключи answers: {list(answers.keys())}")
    
    # Собираем все narrative из ответов
    narrative_keys = [k for k in answers.keys() if k.startswith('narrative_')]
    logger.info(f"🔑 Найдены narrative ключи: {narrative_keys}")
    
    for i in range(8):  # Только 8 нарративных вопросов
        key = f'narrative_{i}'
        if key in answers:
            narr = answers[key]
            if narr and narr in scores:
                scores[narr] += 1
                logger.info(f"✅ {key} = {narr}")
            else:
                logger.warning(f"⚠️ Неверное значение нарратива: {narr}")
        else:
            logger.warning(f"❌ Отсутствует {key}")
    
    # Если нет данных - используем дефолтный на основе пола
    if sum(scores.values()) == 0:
        gender = answers.get('gender', 'М')
        logger.warning(f"⚠️ Нет нарративных ответов, использую дефолт для пола {gender}")
        return ("СБ" if gender == "М" else "ЧВ"), None, None
    
    # Сортируем
    sorted_narr = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    main = sorted_narr[0][0]
    second = None
    third = None
    
    if len(sorted_narr) > 1 and sorted_narr[1][1] > 0:
        second = sorted_narr[1][0]
    
    if len(sorted_narr) > 2 and sorted_narr[2][1] > 0:
        third = sorted_narr[2][0]
    
    logger.info(f"📊 Нарративы: main={main}, second={second}, third={third}, scores={dict(scores)}")
    
    return main, second, third

def get_ancient_program(answers):
    """Определяет доминирующую поведенческую стратегию (F1-F6)"""
    scores = {"F1": 0, "F2": 0, "F3": 0, "F4": 0, "F5": 0, "F6": 0}
    
    # Собираем все ancient из ответов
    ancient_keys = [k for k in answers.keys() if k.startswith('ancient_')]
    logger.info(f"🔑 Найдены ancient ключи: {ancient_keys}")
    
    for key in ancient_keys:
        program = answers[key]
        if program in scores:
            scores[program] += 1
            logger.info(f"✅ {key} = {program}")
        else:
            logger.warning(f"⚠️ Неизвестная программа: {program}")
    
    logger.info(f"📊 Поведенческие стратегии: {dict(scores)}")
    
    # Если нет данных - дефолт
    if sum(scores.values()) == 0:
        logger.warning("⚠️ Нет данных о стратегиях, использую F3")
        return "F3"
    
    return max(scores.items(), key=lambda x: x[1])[0]

def get_level(data, narrative):
    """Определяет уровень (1-6) на основе ресурсов"""
    base = 3
    
    # Бонусы
    if data.get('money', 0) > 7:
        base += 1
        logger.info(f"💰 Бонус за доход: {data.get('money')} -> +1")
    if data.get('housing', 0) > 7:
        base += 1
        logger.info(f"🏠 Бонус за жильё: {data.get('housing')} -> +1")
    if data.get('education', 0) > 8:
        base += 1
        logger.info(f"🎓 Бонус за образование: {data.get('education')} -> +1")
    if data.get('looks', 0) > 8:
        base += 1
        logger.info(f"👀 Бонус за внешность: {data.get('looks')} -> +1")
    if data.get('friends', 0) > 7:
        base += 1
        logger.info(f"👥 Бонус за социальные связи: {data.get('friends')} -> +1")
    
    # Штрафы
    if data.get('money', 5) < 3:
        base -= 1
        logger.info(f"⚠️ Штраф за низкий доход: {data.get('money')} -> -1")
    if data.get('health', 5) < 3:
        base -= 1
        logger.info(f"⚠️ Штраф за здоровье: {data.get('health')} -> -1")
    
    level = max(1, min(6, base))
    logger.info(f"📊 Итоговый уровень: {level}")
    return level

def get_role_name(narrative, level, gender):
    """Название роли (для заголовка)"""
    roles_male = {
        "СБ": ["Начинающий", "Активный", "Уверенный", "Лидер", "Авторитет", "Мастер"],
        "ТФ": ["Стажёр", "Исполнитель", "Профессионал", "Эксперт", "Мастер", "Руководитель"],
        "УБ": ["Любопытный", "Знающий", "Умный", "Мудрый", "Гений", "Мыслитель"],
        "ЧВ": ["Незаметный", "Заметный", "Популярный", "Звезда", "Кумир", "Легенда"]
    }
    roles_female = {
        "СБ": ["Начинающая", "Активная", "Уверенная", "Лидер", "Авторитет", "Мастер"],
        "ТФ": ["Стажёрка", "Исполнительница", "Профессионал", "Эксперт", "Мастер", "Руководительница"],
        "УБ": ["Любопытная", "Знающая", "Умная", "Мудрая", "Гений", "Мыслительница"],
        "ЧВ": ["Незаметная", "Заметная", "Популярная", "Звезда", "Кумир", "Легенда"]
    }
    return (roles_female if gender == 'Ж' else roles_male)[narrative][level-1]

def verify_hypothesis(verification_answers, hypothesis):
    """
    Проверяет, подтверждается ли гипотеза
    Возвращает (успех, новая_гипотеза)
    """
    if not verification_answers:
        logger.info("❌ Нет ответов для верификации")
        return False, hypothesis
    
    logger.info(f"🔍 Проверка гипотезы {hypothesis} с ответами {verification_answers}")
    
    # Считаем подтверждения
    confirm_count = 0
    alternative_scores = {"СБ": 0, "ТФ": 0, "УБ": 0, "ЧВ": 0, 
                          "F1": 0, "F2": 0, "F3": 0, "F4": 0, "F5": 0, "F6": 0}
    
    for answer in verification_answers:
        if "+" in answer:  # Формат "СБ+F1"
            parts = answer.split("+")
            if len(parts) == 2:
                narr, prog = parts
                if narr == hypothesis["narrative"] and prog == hypothesis["program"]:
                    confirm_count += 1
                    logger.info(f"✅ Ответ {answer} подтверждает гипотезу")
                else:
                    if narr in alternative_scores:
                        alternative_scores[narr] += 1
                    if prog in alternative_scores:
                        alternative_scores[prog] += 1
                    logger.info(f"🔄 Ответ {answer} указывает на {narr}+{prog}")
        else:
            if answer == hypothesis["narrative"] or answer == hypothesis["program"]:
                confirm_count += 1
                logger.info(f"✅ Ответ {answer} подтверждает гипотезу")
            else:
                if answer in alternative_scores:
                    alternative_scores[answer] += 1
                    logger.info(f"🔄 Ответ {answer} указывает на {answer}")
    
    # Если большинство подтверждает - успех
    if confirm_count >= len(verification_answers) / 2:
        logger.info(f"🎉 Гипотеза подтверждена ({confirm_count}/{len(verification_answers)})")
        return True, hypothesis
    
    # Находим альтернативы
    logger.info(f"📊 Альтернативные оценки: {alternative_scores}")
    
    narr_options = [(k, v) for k, v in alternative_scores.items() if k in ["СБ","ТФ","УБ","ЧВ"] and v > 0]
    prog_options = [(k, v) for k, v in alternative_scores.items() if k in ["F1","F2","F3","F4","F5","F6"] and v > 0]
    
    new_narrative = max(narr_options, key=lambda x: x[1])[0] if narr_options else hypothesis["narrative"]
    new_program = max(prog_options, key=lambda x: x[1])[0] if prog_options else hypothesis["program"]
    
    new_hypothesis = {
        "narrative": new_narrative,
        "program": new_program,
        "level": hypothesis["level"]
    }
    
    logger.info(f"🔄 Гипотеза скорректирована: {hypothesis} -> {new_hypothesis}")
    
    return False, new_hypothesis

# ==================== ХЕНДЛЕРЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Начало тестирования - выбор теста"""
    
    data = await state.get_data()
    
    # Проверяем незавершённый тест
    if data and data.get('answers') and data.get('test_mode') and not data.get('test_completed'):
        user_name = message.from_user.first_name or "пользователь"
        mode_names = {
            "original": "🔬 базовый",
            "mbti": "📊 MBTI",
            "sexual": "💞 психология близости"
        }
        test_mode_display = mode_names.get(data.get('test_mode'), "тест")
        
        welcome_back = (
            f"🧠 <b>Продолжим?</b>\n\n"
            f"У вас есть незавершённый {test_mode_display} тест, {user_name}.\n\n"
            f"• 🔄 Начать заново\n"
            f"• 👀 Продолжить"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Начать заново", callback_data="restart")
        builder.button(text="👀 Продолжить", callback_data="continue_test")
        builder.adjust(1)
        
        await message.answer(welcome_back, reply_markup=builder.as_markup())
        return
    
    # Главное меню выбора теста
    user_name = message.from_user.first_name or "пользователь"
    
    intro = (
        f"🧠 <b>Психологический профайлер</b>\n\n"
        f"Здравствуйте, {user_name}!\n\n"
        f"Выберите тест:\n\n"
        f"🔬 <b>Базовый тест</b> — 27 вопросов\n"
        f"   Оригинальная методика\n\n"
        f"📊 <b>MBTI тест</b> — 81 вопрос\n"
        f"   Научно-обоснованная типология\n\n"
        f"💞 <b>Психология близости</b> — 24 вопроса\n"
        f"   Понимание себя в отношениях"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔬 Базовый тест (27)", callback_data="mode_original")
    builder.button(text="📊 MBTI тест (81)", callback_data="mode_mbti")
    builder.button(text="💞 Психология близости (24)", callback_data="mode_sexual")
    builder.button(text="ℹ️ Подробнее", callback_data="info")
    builder.adjust(1)
    
    await message.answer(intro, reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data == "continue_test")
async def continue_test(callback: types.CallbackQuery, state: FSMContext):
    """Продолжить незавершённый тест"""
    await callback.answer()
    
    data = await state.get_data()
    test_mode = data.get('test_mode', 'original')
    answers = data.get('answers', {})
    
    if test_mode == "mbti":
        mbti_answers = [k for k in answers.keys() if k.startswith('mbti_')]
        answered = len(mbti_answers)
        total = data.get('mbti_total', 81)
        
        if answered >= total:
            await show_result(callback.from_user.id, state)
        else:
            await state.update_data(last_message_id=None)
            await ask_question(callback.from_user.id, answered + 2, state)
            
    elif test_mode == "sexual":
        current = data.get('sexual_current', 0)
        if current >= len(SEXUAL_QUESTIONS):
            await sexual_finish(callback, state)
        else:
            await state.update_data(last_message_id=None)
            await sexual_ask_question(callback, state)
            
    else:  # original
        narrative_answers = [k for k in answers.keys() if k.startswith('narrative_')]
        res_keys = ['education', 'money', 'housing', 'health', 'friends', 'looks', 'height', 'job', 'marriage', 'children']
        res_answers = [k for k in answers.keys() if k in res_keys]
        ancient_answers = [k for k in answers.keys() if k.startswith('ancient_')]
        
        answered = len(narrative_answers) + len(res_answers) + len(ancient_answers)
        
        if answered >= 27:
            await start_verification(callback.from_user.id, state)
        else:
            await state.update_data(last_message_id=None)
            await ask_question(callback.from_user.id, answered + 2, state)

@dp.callback_query(lambda c: c.data == "info")
async def show_info(callback: types.CallbackQuery):
    """Информация о тестах"""
    await callback.answer()
    
    info_text = (
        f"🧠 <b>О тестах</b>\n\n"
        f"🔬 <b>Базовый тест:</b>\n"
        f"27 вопросов о ваших предпочтениях, ресурсах и поведенческих стратегиях.\n"
        f"Определяет ваш тип (СБ, ТФ, УБ, ЧВ) и уровень развития.\n\n"
        f"📊 <b>MBTI тест:</b>\n"
        f"81 вопрос. Определяет ваш тип личности по системе Майерс-Бриггс.\n"
        f"Оценивает 4 дихотомии: Экстраверсия-Интроверсия, Сенсорика-Интуиция, "
        f"Мышление-Чувство, Суждение-Восприятие.\n\n"
        f"💞 <b>Психология близости:</b>\n"
        f"24 вопроса о ваших предпочтениях в отношениях.\n"
        f"Определяет ваш тип: Лидер, Эмоционал, Партнёр, Исследователь, "
        f"Сенсорный, Романтик, Гедонист, Интеллектуал.\n\n"
        f"<i>Все ответы конфиденциальны и используются только для расчёта профиля.</i>"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔬 Базовый", callback_data="mode_original")
    builder.button(text="📊 MBTI", callback_data="mode_mbti")
    builder.button(text="💞 Психология близости", callback_data="mode_sexual")
    builder.button(text="◀️ Назад", callback_data="back_to_start")
    builder.adjust(2, 1, 1)
    
    await callback.message.edit_text(info_text, reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data == "back_to_start")
async def back_to_start(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await callback.answer()
    await state.clear()
    await cmd_start(callback.message, state)

@dp.callback_query(lambda c: c.data.startswith('mode_'))
async def process_mode(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора режима теста"""
    await callback.answer()
    
    mode = callback.data.split('_')[1]
    logger.info(f"🎮 Выбран режим: {mode}")
    
    # Очищаем состояние для нового теста
    await state.clear()
    await state.update_data(
        answers={}, 
        last_message_id=None,
        test_mode=mode,
        test_completed=False
    )
    await state.set_state(UserState.question_index)
    
    # Для сексуального теста инициализируем структуру баллов
    if mode == "sexual":
        await state.update_data(
            sexual_current=0,
            sexual_last_answered=-1,
            sexual_processing=False,
            sexual_scores={
                "temperament": {"PREDATOR": 0, "ARTIST": 0, "OBSERVER": 0, "PLAYER": 0},
                "fetishes": {"SMELL": 0, "MATERIALS": 0, "BODY_PARTS": 0, "SITUATIONS": 0},
                "formats": {
                    "MHM": 0, "HWH": 0, "SWING": 0, "BDSM_DOM": 0, "BDSM_SUB": 0,
                    "BDSM_LIGHT": 0, "ROLE_PLAY": 0, "RISK": 0, "TOYS": 0, "VIDEO": 0,
                    "VIRTUAL": 0, "MONO": 0, "TRADITION": 0, "ADAPT": 0
                }
            }
        )
    
    if mode == "mbti":
        await callback.message.edit_text(
            f"📊 <b>MBTI тест</b>\n\n"
            f"Тест содержит 81 вопрос. Отвечайте честно, выбирая вариант от 1 до 5.\n\n"
            f"<i>Шкала ответов:</i>\n"
            f"1 — ❌ Совершенно не согласен\n"
            f"2 — ⚠️ Скорее не согласен\n"
            f"3 — ⚪ Нейтрально\n"
            f"4 — ✅ Скорее согласен\n"
            f"5 — 👍 Полностью согласен\n\n"
            f"*Начинаем...*"
        )
        await asyncio.sleep(2)
        await ask_gender_question(callback.from_user.id, state)
        
    elif mode == "sexual":
        await callback.message.edit_text(
            f"💞 <b>Тест: Психология близости</b>\n\n"
            f"24 вопроса о ваших предпочтениях в отношениях.\n\n"
            f"Отвечайте честно — это поможет лучше понять себя.\n\n"
            f"*Начинаем...*"
        )
        await asyncio.sleep(2)
        
        # 👇 ИСПРАВЛЕНО: прямой вызов без обёртки
        logger.info("🎯 Запуск сексуального теста")
        
        # Удаляем сообщение "Начинаем..."
        try:
            await callback.message.delete()
        except:
            pass
        
        # Запрашиваем пол и возраст
        await ask_gender_question(callback.from_user.id, state)
        
    else:
        await callback.message.edit_text(
            f"🔬 <b>Базовый тест</b>\n\n"
            f"Тест содержит 27 вопросов о ваших предпочтениях, ресурсах и поведении.\n\n"
            f"*Начинаем...*"
        )
        await asyncio.sleep(2)
        await ask_gender_question(callback.from_user.id, state)
async def ask_gender_question(user_id, state: FSMContext):
    """Вопрос о поле"""
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
        f"📋 <b>Вопрос 1/2</b>\n\n"
        f"{GENDER_QUESTION['text']}",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(last_message_id=sent.message_id)

async def ask_age_question(user_id, state: FSMContext):
    """Вопрос о возрасте"""
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
        f"📋 <b>Вопрос 2/2</b>\n\n"
        f"{AGE_QUESTION['text']}",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(last_message_id=sent.message_id)

async def ask_age_question(user_id, state: FSMContext):
    """Вопрос о возрасте"""
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
        f"📋 <b>Вопрос 2/2</b>\n\n"
        f"{AGE_QUESTION['text']}",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(last_message_id=sent.message_id)

@dp.callback_query(lambda c: c.data.startswith('gender_'))
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    """Обработка пола"""
    await callback.answer()
    
    gender = callback.data.split('_')[1]
    logger.info(f"👤 Пол: {gender}")
    
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
    """Обработка возраста"""
    await callback.answer()
    
    age_key = callback.data.split('_')[1]
    age_data = AGE_QUESTION["options"][age_key]["scores"]
    
    logger.info(f"📅 Возраст: {age_data['age']} лет")
    
    data = await state.get_data()
    answers = data.get('answers', {})
    answers['age'] = age_data['age']
    answers['age_group'] = age_data['age_group']
    
    await state.update_data(answers=answers)
    
    try:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
    except:
        pass
    
    test_mode = data.get('test_mode', 'original')
    
    if test_mode == "mbti":
        # MBTI тест
        gender = answers.get('gender', 'М')
        mbti_questions = get_mbti_questions(gender)
        await state.update_data(
            mbti_questions=mbti_questions,
            mbti_total=len(mbti_questions)
        )
        await ask_question(callback.from_user.id, 2, state)
        
    elif test_mode == "sexual":
        # 👇 ИСПРАВЛЕНО: запускаем первый вопрос сексуального теста
        logger.info("🎯 Запуск первого вопроса сексуального теста")
        await sexual_ask_question(callback, state)
        
    else:
        # Базовый тест
        await ask_question(callback.from_user.id, 2, state)
async def ask_question(user_id, index, state: FSMContext):
    """Задаёт вопрос для базового или MBTI теста"""
    data = await state.get_data()
    answers = data.get('answers', {})
    gender = answers.get('gender', 'М')
    age_group = answers.get('age_group', 'ADULT')
    test_mode = data.get('test_mode', 'original')
    
    last_id = data.get('last_message_id')
    if last_id:
        try:
            await bot.delete_message(user_id, last_id)
        except:
            pass
    
    if test_mode == "mbti":
        # MBTI режим
        mbti_questions = data.get('mbti_questions', [])
        total = data.get('mbti_total', 81)
        
        # ИСПРАВЛЕНИЕ: правильный расчёт индекса
        answered_questions = len([k for k in answers.keys() if k.startswith('mbti_')])
        current_question = answered_questions
        
        if current_question >= len(mbti_questions):
            await show_result(user_id, state)
            return
        
        q = mbti_questions[current_question]
        progress = get_progress_bar(current_question + 1, total)
        
        builder = InlineKeyboardBuilder()
        for key, scale in MBTI_SCALE.items():
            builder.button(text=scale["text"], callback_data=f"mbti_{current_question}_{key}")
        builder.adjust(1)
        
        sent = await bot.send_message(
            user_id,
            f"📊 <b>Вопрос {current_question+1}/{total}</b>\n"
            f"<code>{progress}</code>\n\n"
            f"{q['text']}",
            reply_markup=builder.as_markup()
        )
        
        await state.update_data(last_message_id=sent.message_id)
        
    elif test_mode == "sexual":
        # Сексуальный тест обрабатывается отдельно
        pass
        
    else:
        # Базовый режим
        total_questions = 27
        
        if index < 2:
            return
        elif index < 10:  # Нарративные вопросы
            q_idx = index - 2
            questions = get_narrative_questions(gender, age_group)
            if q_idx >= len(questions):
                await ask_question(user_id, 10, state)
                return
            q = questions[q_idx]
            block = "ОСНОВНОЙ"
            q_num = index + 1
            prefix = "narrative"
            
        elif index < 20:  # Ресурсные вопросы
            res_idx = index - 10
            if res_idx >= len(COMMON_RESOURCES_QUESTIONS):
                await ask_question(user_id, 20, state)
                return
            q = COMMON_RESOURCES_QUESTIONS[res_idx]
            block = "ДОПОЛНИТЕЛЬНО"
            q_num = index + 1
            prefix = "res"
            
        else:  # Поведенческие вопросы
            prog_idx = index - 20
            questions = get_ancient_program_questions(gender)
            if prog_idx >= len(questions):
                await start_verification(user_id, state)
                return
            q = questions[prog_idx]
            block = "ПОВЕДЕНИЕ"
            q_num = index + 1
            prefix = "ancient"
        
        progress = get_progress_bar(index + 1, total_questions)
        
        builder = InlineKeyboardBuilder()
        for key, option in q["options"].items():
            score_key = list(option["scores"].keys())[0]
            score_value = option["scores"][score_key]
            callback_data = f"ans_{index}_{key}_{prefix}_{score_key}_{score_value}"
            if len(callback_data) > 64:
                callback_data = f"ans_{index}_{key}"
            builder.button(text=option["text"], callback_data=callback_data[:64])
        builder.adjust(1)
        
        sent = await bot.send_message(
            user_id,
            f"🔬 <b>{block} • Вопрос {q_num}/{total_questions}</b>\n"
            f"<code>{progress}</code>\n\n"
            f"{q['text']}",
            reply_markup=builder.as_markup()
        )
        
        await state.update_data(last_message_id=sent.message_id)

@dp.callback_query(lambda c: c.data.startswith('mbti_'))
async def process_mbti_answer(callback: types.CallbackQuery, state: FSMContext):
    """Обработка MBTI ответов"""
    await callback.answer()
    
    parts = callback.data.split('_')
    # ИСПРАВЛЕНИЕ: правильное извлечение данных
    q_index = int(parts[1])
    value = int(parts[2])
    
    logger.info(f"📝 Получен MBTI ответ на вопрос {q_index+1}")
    
    data = await state.get_data()
    answers = data.get('answers', {})
    
    answers[f'mbti_{q_index}'] = value
    await state.update_data(answers=answers)
    
    try:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
    except:
        pass
    
    mbti_total = data.get('mbti_total', 81)
    
    # ИСПРАВЛЕНИЕ: правильная проверка завершения
    answered = len([k for k in answers.keys() if k.startswith('mbti_')])
    
    if answered >= mbti_total:
        logger.info(f"✅ Все MBTI вопросы отвечены")
        await show_result(callback.from_user.id, state)
    else:
        # Передаём следующий индекс
        await ask_question(callback.from_user.id, answered + 2, state)

@dp.message(Command("debug"))
async def cmd_debug(message: types.Message, state: FSMContext):
    """Отладка - показать состояние"""
    data = await state.get_data()
    answers = data.get('answers', {})
    mbti_answers = [k for k in answers.keys() if k.startswith('mbti_')]
    
    debug_text = (
        f"🔍 <b>Отладка</b>\n\n"
        f"Режим: {data.get('test_mode', 'не задан')}\n"
        f"Отвечено MBTI: {len(mbti_answers)}/{data.get('mbti_total', 81)}\n"
        f"Всего ответов: {len(answers)}\n\n"
        f"Последний ответ: {mbti_answers[-1] if mbti_answers else 'нет'}"
    )
    
    await message.answer(debug_text)
@dp.callback_query(lambda c: c.data.startswith('mbti_'))
async def process_mbti_answer(callback: types.CallbackQuery, state: FSMContext):
    """Обработка MBTI ответов"""
    await callback.answer()
    
    parts = callback.data.split('_')
    idx = int(parts[1])
    value = int(parts[2])
    
    mbti_idx = idx - 2
    logger.info(f"📝 Получен MBTI ответ на вопрос {mbti_idx+1}")
    
    data = await state.get_data()
    answers = data.get('answers', {})
    
    answers[f'mbti_{mbti_idx}'] = value
    await state.update_data(answers=answers)
    
    try:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
    except:
        pass
    
    mbti_total = data.get('mbti_total', 81)
    if mbti_idx + 1 >= mbti_total:
        logger.info(f"✅ Все MBTI вопросы отвечены")
        await show_result(callback.from_user.id, state)
    else:
        await ask_question(callback.from_user.id, idx + 1, state)

@dp.callback_query(lambda c: c.data.startswith('verif_'))
async def process_verification(callback: types.CallbackQuery, state: FSMContext):
    """Обработка верификационных ответов"""
    await callback.answer()
    
    parts = callback.data.split('_')
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

async def ask_verification_question(user_id, state: FSMContext):
    """Задаёт верификационный вопрос"""
    data = await state.get_data()
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
        builder.button(text=option["text"], callback_data=f"verif_{v_index}_{key}_{score}")
    builder.adjust(1)
    
    round_num = data.get('verification_round', 1)
    
    sent = await bot.send_message(
        user_id,
        f"🔍 <b>Уточнение • Круг {round_num}</b>\n\n"
        f"{q['text']}",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(
        last_message_id=sent.message_id,
        verification_index=v_index + 1
    )

async def finish_verification(user_id, state: FSMContext):
    """Завершение верификации"""
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
        
        await bot.send_message(
            user_id,
            f"🔄 <b>Уточним...</b>\n\n"
            f"Ваши ответы требуют дополнительной проверки."
        )
        await asyncio.sleep(2)
        
        await ask_verification_question(user_id, state)

async def start_verification(user_id, state: FSMContext):
    """Начинает верификацию для базового теста"""
    data = await state.get_data()
    answers = data.get('answers', {})
    
    narrative, second, third = get_narrative_from_answers(answers)
    program = get_ancient_program(answers)
    level = get_level(answers, narrative)
    
    if not narrative:
        narrative = "СБ"
        program = "F3"
        level = 3
    
    hypothesis = {
        "narrative": narrative,
        "program": program,
        "level": level,
        "second": second,
        "third": third
    }
    
    v_questions = get_verification_questions(hypothesis)
    
    await state.update_data(
        hypothesis=hypothesis,
        verification_round=1,
        verification_index=0,
        verification_answers=[],
        verification_questions=v_questions
    )
    
    await bot.send_message(
        user_id,
        f"🔍 <b>Уточнение</b>\n\n"
        f"Осталось несколько вопросов для точности..."
    )
    await asyncio.sleep(2)
    
    await ask_verification_question(user_id, state)

async def show_fortune(user_id, state: FSMContext, hypothesis):
    """Показывает результат для классического режима"""
    data = await state.get_data()
    answers = data.get('answers', {})
    
    gender = answers.get('gender', 'М')
    age = answers.get('age', 30)
    
    try:
        user = await bot.get_chat(user_id)
        user_name = user.first_name or "пользователь"
    except:
        user_name = "пользователь"
    
    narrative = hypothesis["narrative"]
    program = hypothesis["program"]
    level = hypothesis["level"]
    second = hypothesis.get("second")
    third = hypothesis.get("third")
    
    role = get_role_name(narrative, level, gender)
    
    last_id = data.get('last_message_id')
    if last_id:
        try:
            await bot.delete_message(user_id, last_id)
        except:
            pass
    
    interpretation_data = get_interpretation(
        gender=gender, 
        narrative=narrative, 
        level=level, 
        age=age,
        program=program,
        second_narrative=second, 
        third_narrative=third
    )
    
    if isinstance(interpretation_data, dict):
        detstvo = interpretation_data.get("детство", "")
        identichnost = interpretation_data.get("идентичность", "")
        okruzhenie = interpretation_data.get("окружение", "")
        
        interpretation = f"""<b>📋 Характеристика:</b>
{detstvo}

<b>🎭 Особенности личности:</b>
{identichnost}

<b>🌍 Социальная среда:</b>
{okruzhenie}"""
    else:
        interpretation = str(interpretation_data)
    
    age_range = get_age_range(age)
    
    ancient_names = {
        "F1": "⚔️ Активная защита",
        "F2": "🏃 Избегание",
        "F3": "🧊 Замирание",
        "F4": "👻 Игнорирование",
        "F5": "🤝 Приспособление",
        "F6": "🧘 Принятие"
    }
    
    header = (
        f"🧠 <b>Результаты: {user_name}</b>\n\n"
        f"👤 Возраст: {age_range}\n"
        f"📊 Стратегия: <b>{ancient_names.get(program, program)}</b>\n"
        f"🎭 Тип: <b>{NARRATIVE_NAMES[narrative]}</b>\n"
        f"📈 Уровень: <b>{level}/6</b>\n\n"
    )
    
    await bot.send_chat_action(user_id, action="typing")
    await asyncio.sleep(1)
    
    full_text = header + interpretation
    
    if len(full_text) > 4000:
        parts = [full_text[i:i+4000] for i in range(0, len(full_text), 4000)]
        for i, part in enumerate(parts):
            await bot.send_message(user_id, part)
            await asyncio.sleep(0.5)
    else:
        await bot.send_message(user_id, full_text)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Пройти заново", callback_data="restart")
    builder.adjust(1)
    
    await bot.send_message(
        user_id,
        f"📋 <b>Что дальше?</b>\n\n"
        f"Хотите пройти тест ещё раз?",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(test_completed=True)
    await state.clear()

async def show_result(user_id, state: FSMContext):
    """Показывает MBTI результат"""
    data = await state.get_data()
    answers = data.get('answers', {})
    
    gender = answers.get('gender', 'М')
    age = answers.get('age', 30)
    
    try:
        user = await bot.get_chat(user_id)
        user_name = user.first_name or "пользователь"
    except:
        user_name = "пользователь"
    
    last_id = data.get('last_message_id')
    if last_id:
        try:
            await bot.delete_message(user_id, last_id)
        except:
            pass
    
    mbti_result = calculate_mbti_type(answers)
    interpretation = get_mbti_interpretation(mbti_result, gender, age)
    
    age_range = get_age_range(age)
    
    header = (
        f"🧠 <b>Результаты MBTI: {user_name}</b>\n\n"
        f"👤 Возраст: {age_range}\n"
        f"📊 Тип: <b>{mbti_result['type']} — {mbti_result['type_name']}</b>\n\n"
    )
    
    if not mbti_result['validation'].get('valid', True):
        warnings = "\n".join(mbti_result['validation'].get('warnings', []))
        header += f"⚠️ <b>Примечание:</b>\n{warnings}\n\n"
    
    await bot.send_chat_action(user_id, action="typing")
    await asyncio.sleep(1)
    
    full_text = header + interpretation
    
    if len(full_text) > 4000:
        parts = [full_text[i:i+4000] for i in range(0, len(full_text), 4000)]
        for i, part in enumerate(parts):
            await bot.send_message(user_id, part)
            await asyncio.sleep(0.5)
    else:
        await bot.send_message(user_id, full_text)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Пройти заново", callback_data="restart")
    builder.adjust(1)
    
    await bot.send_message(
        user_id,
        f"📋 <b>Что дальше?</b>\n\n"
        f"Хотите пройти тест ещё раз?",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(test_completed=True)
    await state.clear()

@dp.callback_query(lambda c: c.data == "restart")
async def restart(callback: types.CallbackQuery, state: FSMContext):
    """Перезапуск теста"""
    logger.info("🔄 Перезапуск теста")
    await callback.answer()
    await state.clear()
    await cmd_start(callback.message, state)

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Помощь"""
    help_text = (
        f"🧠 <b>Помощь</b>\n\n"
        f"• /start — начать тестирование\n"
        f"• /help — показать это сообщение\n\n"
        f"<b>О тестах:</b>\n"
        f"🔬 Базовый тест: 27 вопросов\n"
        f"📊 MBTI тест: 81 вопрос\n"
        f"💞 Психология близости: 24 вопроса\n\n"
        f"<b>Шкала ответов MBTI:</b>\n"
        f"1 — ❌ Совершенно не согласен\n"
        f"2 — ⚠️ Скорее не согласен\n"
        f"3 — ⚪ Нейтрально\n"
        f"4 — ✅ Скорее согласен\n"
        f"5 — 👍 Полностью согласен"
    )
    
    await message.answer(help_text)

# ==================== ПОДКЛЮЧЕНИЕ ОБРАБОТЧИКОВ СЕКСУАЛЬНОГО ТЕСТА ====================

# ==================== ПОДКЛЮЧЕНИЕ ОБРАБОТЧИКОВ СЕКСУАЛЬНОГО ТЕСТА ====================

@dp.callback_query(lambda c: c.data and c.data.startswith('sexual_'))
async def sexual_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик всех callback'ов сексуального теста"""
    
    # Проверяем, что это действительно сексуальный тест
    data = await state.get_data()
    test_mode = data.get('test_mode')
    
    if test_mode != 'sexual':
        return
    
    logger.info(f"🎯 Сексуальный тест: {callback.data}")
    
    try:
        if callback.data.startswith('sexual_ask'):
            # Запрос вопроса (sexual_ask_0)
            await sexual_ask_question(callback, state)
            
        elif callback.data.startswith('sexual_ans'):
            # Ответ на вопрос (sexual_ans_0_a)
            await sexual_handle_answer(callback, state)
            
        elif callback.data == 'sexual_finish':
            # Завершение теста
            await sexual_finish(callback, state)
            
        elif callback.data == 'sexual_premium':
            # Премиум версия
            await sexual_premium(callback, state)
            
        elif callback.data == 'sexual_back':
            # Назад к результатам
            await sexual_finish(callback, state)
            
        else:
            logger.warning(f"Неизвестный callback: {callback.data}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка в sexual_handler: {e}", exc_info=True)
        await callback.answer("⚠️ Произошла ошибка", show_alert=True)
# ==================== ЗАПУСК ====================

async def main():
    """Запуск бота"""
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Вебхук сброшен")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось сбросить вебхук: {e}")
    
    print("\n" + "="*50)
    print("🧠 ПСИХОЛОГИЧЕСКИЙ ПРОФАЙЛЕР v5.0")
    print("="*50)
    print("🚀 Бот запущен")
    print("📝 Логирование включено")
    print("="*50 + "\n")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
