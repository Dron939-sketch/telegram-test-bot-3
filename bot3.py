#!/usr/bin/env python3
"""
🔮 ТАЙНЫЙ ШЁПОТ: Виртуальная гадалка v3.0
С верификационным блоком для подтверждения гипотез
Полная версия с поддержкой 168 стратегий
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
from interpretations import get_interpretation, NARRATIVE_NAMES

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
    # Основные этапы
    question_index = State()        # Индекс текущего вопроса
    answers = State()               # Все ответы
    last_message_id = State()       # ID последнего сообщения
    gender = State()                # Пол пользователя
    age_group = State()             # Возрастная группа
    
    # Этап верификации
    hypothesis = State()            # Текущая гипотеза {нарратив, программа, уровень}
    verification_round = State()    # Номер попытки верификации
    verification_questions = State() # Список верификационных вопросов
    verification_index = State()     # Индекс текущего верификационного вопроса
    verification_answers = State()   # Ответы на верификацию

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_life_season(age: int) -> str:
    """Определяет время года жизни по возрасту"""
    if age < 20: return "весна жизни 🌱"
    elif age < 30: return "начало лета ☀️"
    elif age < 40: return "разгар лета 🌻"
    elif age < 50: return "золотая осень 🍂"
    elif age < 60: return "бабье лето 🕸️"
    else: return "зима мудрости ❄️"

def get_separator() -> str:
    """Возвращает красивый разделитель"""
    separators = [
        "✧═══════════════════════════✧",
        "🌸─────────────────────────🌸",
        "🌟═══════════════════════════🌟",
        "✨ * ✦ * ✦ * ✦ * ✦ * ✦ * ✦ * ✦ * ✦ * ✦ * ✦ * ✦ * ✦ * ✧",
        "☽═══════════════════════════☾",
    ]
    return random.choice(separators)

def get_mystic_symbol() -> str:
    """Возвращает мистический символ"""
    symbols = ["🔮", "🕯️", "🌙", "⭐", "🌀", "💫", "✨", "🪷", "🌿", "🦉"]
    return random.choice(symbols)

# ==================== ВОПРОС 0: ПОЛ ====================
GENDER_QUESTION = {
    "text": "Кем ты приходишь в этот мир?",
    "options": {
        "М": {"text": "👨 Мужчиной", "scores": {"gender": "М"}},
        "Ж": {"text": "👩 Женщиной", "scores": {"gender": "Ж"}}
    }
}

# ==================== ВОПРОС 1: ВОЗРАСТ ====================
AGE_QUESTION = {
    "text": "Сколько зим минуло с твоего рождения?",
    "options": {
        "1": {"text": "Меньше 20", "scores": {"age": 18, "age_group": "YOUNG"}},
        "2": {"text": "20-25 лет", "scores": {"age": 22, "age_group": "YOUNG_ADULT"}},
        "3": {"text": "25-30 лет", "scores": {"age": 27, "age_group": "YOUNG_ADULT"}},
        "4": {"text": "30-35 лет", "scores": {"age": 32, "age_group": "ADULT"}},
        "5": {"text": "35-40 лет", "scores": {"age": 37, "age_group": "ADULT"}},
        "6": {"text": "40-45 лет", "scores": {"age": 42, "age_group": "MIDDLE"}},
        "7": {"text": "45-50 лет", "scores": {"age": 47, "age_group": "MIDDLE"}},
        "8": {"text": "50-60 лет", "scores": {"age": 55, "age_group": "MATURE"}},
        "9": {"text": "Больше 60", "scores": {"age": 65, "age_group": "ELDER"}}
    }
}

# ==================== БЛОК 1: НАРРАТИВ (8 вопросов) ====================
def get_narrative_questions(gender, age_group):
    """Возвращает вопросы для определения нарратива с учетом пола и возраста"""
    
    if gender == "М":
        if age_group in ["YOUNG", "YOUNG_ADULT"]:
            # Молодые мужчины
            return [
                {  # Вопрос 2. Свободное время
                    "text": "Если выдается свободный вечер, ты скорее...",
                    "options": {
                        "1": {"text": "В спортзал или поиграть в танчики", "scores": {"narrative": "СБ"}},
                        "2": {"text": "Что-то починить, смастерить", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Зависнуть в ютубе на научпопе", "scores": {"narrative": "УБ"}},
                        "4": {"text": "Тусоваться с друзьями", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 3. Что ценишь в людях
                    "text": "Какое качество в человеке для тебя самое важное?",
                    "options": {
                        "1": {"text": "Уверенность, характер", "scores": {"narrative": "СБ"}},
                        "2": {"text": "Надёжность, слово держит", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Ум, с ним есть о чём поговорить", "scores": {"narrative": "УБ"}},
                        "4": {"text": "Лёгкость, чувство юмора", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 4. Комплимент
                    "text": "От какого комплимента ты растаешь?",
                    "options": {
                        "1": {"text": "«Ты крутой, тебя все уважают»", "scores": {"narrative": "СБ"}},
                        "2": {"text": "«На тебя всегда можно положиться»", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "«Ты очень умный»", "scores": {"narrative": "УБ"}},
                        "4": {"text": "«С тобой так весело»", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 5. Новая компания
                    "text": "Попадая в новую компанию, ты...",
                    "options": {
                        "1": {"text": "Присматриваюсь, кто тут главный", "scores": {"narrative": "СБ"}},
                        "2": {"text": "Ищу, с кем можно поговорить о деле", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Слушаю, о чём говорят", "scores": {"narrative": "УБ"}},
                        "4": {"text": "Со всеми знакомлюсь, шучу", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 6. Деньги
                    "text": "Если бы у тебя была лишняя тысяча, потратил бы на...",
                    "options": {
                        "1": {"text": "Что-то статусное (кроссовки, часы)", "scores": {"narrative": "СБ"}},
                        "2": {"text": "Инструмент или полезную вещь", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Книгу или курс", "scores": {"narrative": "УБ"}},
                        "4": {"text": "Поход с друзьями", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 7. Что бесит
                    "text": "Что тебя больше всего бесит в людях?",
                    "options": {
                        "1": {"text": "Когда они не знают своего места", "scores": {"narrative": "СБ"}},
                        "2": {"text": "Когда они халтурят", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Когда они тупят", "scores": {"narrative": "УБ"}},
                        "4": {"text": "Когда они скучные", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 8. Подарок
                    "text": "Какой подарок тебя порадует больше?",
                    "options": {
                        "1": {"text": "Дорогая вещь, статусная", "scores": {"narrative": "СБ"}},
                        "2": {"text": "Что-то полезное для дела", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Интеллектуальная игра, книга", "scores": {"narrative": "УБ"}},
                        "4": {"text": "Билет на концерт, впечатления", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 9. Страх
                    "text": "Чего ты боишься больше всего?",
                    "options": {
                        "1": {"text": "Потерять уважение, стать никем", "scores": {"narrative": "СБ"}},
                        "2": {"text": "Остаться без денег, без работы", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Показаться глупым", "scores": {"narrative": "УБ"}},
                        "4": {"text": "Стать незаметным, скучным", "scores": {"narrative": "ЧВ"}}
                    }
                }
            ]
        else:
            # Зрелые мужчины
            return [
                {  # Вопрос 2. Свободное время
                    "text": "Как ты предпочитаешь проводить свободное время?",
                    "options": {
                        "1": {"text": "С друзьями, шашлыки, баня", "scores": {"narrative": "СБ"}},
                        "2": {"text": "Дома, с семьёй, по хозяйству", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "За книгой, познавательное", "scores": {"narrative": "УБ"}},
                        "4": {"text": "Выезды, путешествия", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 3. Что ценишь в людях
                    "text": "Что для тебя главное в человеке?",
                    "options": {
                        "1": {"text": "Характер, стержень", "scores": {"narrative": "СБ"}},
                        "2": {"text": "Порядочность, надёжность", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Мудрость, опыт", "scores": {"narrative": "УБ"}},
                        "4": {"text": "Душевность, теплота", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 4. Комплимент
                    "text": "Какие слова для тебя самые дорогие?",
                    "options": {
                        "1": {"text": "«Ты добился всего сам»", "scores": {"narrative": "СБ"}},
                        "2": {"text": "«На тебя можно положиться»", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "«Ты мудрый, с тобой есть о чём поговорить»", "scores": {"narrative": "УБ"}},
                        "4": {"text": "«С тобой хорошо и спокойно»", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 5. Новая компания
                    "text": "В незнакомой компании ты...",
                    "options": {
                        "1": {"text": "Присматриваюсь, кто здесь главный", "scores": {"narrative": "СБ"}},
                        "2": {"text": "Ищу, с кем можно поговорить по делу", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Слушаю, что говорят, вникаю", "scores": {"narrative": "УБ"}},
                        "4": {"text": "Общаюсь со всеми, мне легко", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 6. Деньги
                    "text": "На что ты потратишь неожиданную премию?",
                    "options": {
                        "1": {"text": "На что-то для статуса (часы, машина)", "scores": {"narrative": "СБ"}},
                        "2": {"text": "Отложу, вложу", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "На обучение, саморазвитие", "scores": {"narrative": "УБ"}},
                        "4": {"text": "На путешествие, впечатления", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 7. Что бесит
                    "text": "Что тебя раздражает в других?",
                    "options": {
                        "1": {"text": "Неуважение, панибратство", "scores": {"narrative": "СБ"}},
                        "2": {"text": "Безответственность", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Глупость, нежелание думать", "scores": {"narrative": "УБ"}},
                        "4": {"text": "Пустота, с ними не о чем говорить", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 8. Подарок
                    "text": "Какой подарок тебя обрадует?",
                    "options": {
                        "1": {"text": "Дорогой, статусный", "scores": {"narrative": "СБ"}},
                        "2": {"text": "Полезный, нужный в хозяйстве", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Книга, редкое издание", "scores": {"narrative": "УБ"}},
                        "4": {"text": "Впечатление, путешествие", "scores": {"narrative": "ЧВ"}}
                    }
                },
                {  # Вопрос 9. Страх
                    "text": "Чего ты опасаешься в жизни?",
                    "options": {
                        "1": {"text": "Потерять уважение, статус", "scores": {"narrative": "СБ"}},
                        "2": {"text": "Остаться без средств", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Деградировать, отупеть", "scores": {"narrative": "УБ"}},
                        "4": {"text": "Одиночества", "scores": {"narrative": "ЧВ"}}
                    }
                }
            ]
    else:  # Женщины
        if age_group in ["YOUNG", "YOUNG_ADULT"]:
            # Молодые женщины
            return [
                {  # Вопрос 2. Свободное время
                    "text": "Как ты любишь проводить выходной?",
                    "options": {
                        "1": {"text": "С подругами, по магазинам, в кафе", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "Дома, с семьёй, готовлю, убираю", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Занимаюсь собой, спорт, уход", "scores": {"narrative": "СБ"}},
                        "4": {"text": "Читаю, смотрю познавательное", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 3. Что ценишь в людях
                    "text": "Что для тебя важно в человеке?",
                    "options": {
                        "1": {"text": "Чувство юмора, лёгкость", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "Надёжность, забота", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Уверенность, сила", "scores": {"narrative": "СБ"}},
                        "4": {"text": "Ум, интеллект", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 4. Комплимент
                    "text": "От какого комплимента тебе приятнее?",
                    "options": {
                        "1": {"text": "«Ты красивая, стильная»", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "«Ты заботливая, добрая»", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "«Ты сильная, с характером»", "scores": {"narrative": "СБ"}},
                        "4": {"text": "«С тобой интересно»", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 5. Новая компания
                    "text": "В новой компании ты...",
                    "options": {
                        "1": {"text": "Со всеми знакомлюсь, общаюсь", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "Присматриваюсь, слушаю", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Оцениваю, кто тут главный", "scores": {"narrative": "СБ"}},
                        "4": {"text": "Наблюдаю, анализирую", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 6. Деньги
                    "text": "На что потратишь неожиданную сумму?",
                    "options": {
                        "1": {"text": "На одежду, косметику", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "Отложу, на квартиру, на будущее", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "На что-то статусное (сумка, часы)", "scores": {"narrative": "СБ"}},
                        "4": {"text": "На курсы, обучение", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 7. Что бесит
                    "text": "Что тебя раздражает в других?",
                    "options": {
                        "1": {"text": "Скучные, с ними неинтересно", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "Безответственные", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Хамство, неуважение", "scores": {"narrative": "СБ"}},
                        "4": {"text": "Глупость, недалёкость", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 8. Подарок
                    "text": "Какой подарок тебя порадует?",
                    "options": {
                        "1": {"text": "Красивая вещь, украшение", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "Что-то нужное, полезное", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Что-то дорогое, статусное", "scores": {"narrative": "СБ"}},
                        "4": {"text": "Книга, курс, развитие", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 9. Страх
                    "text": "Чего ты боишься больше всего?",
                    "options": {
                        "1": {"text": "Одиночества", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "Бедности, нужды", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Потерять уважение, статус", "scores": {"narrative": "СБ"}},
                        "4": {"text": "Глупости, деградации", "scores": {"narrative": "УБ"}}
                    }
                }
            ]
        else:
            # Зрелые женщины
            return [
                {  # Вопрос 2. Свободное время
                    "text": "Как ты любишь проводить время?",
                    "options": {
                        "1": {"text": "С семьёй, с детьми/внуками", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "По дому, на даче", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "С подругами, встречи", "scores": {"narrative": "СБ"}},
                        "4": {"text": "Читаю, узнаю новое", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 3. Что ценишь в людях
                    "text": "Что для тебя главное в человеке?",
                    "options": {
                        "1": {"text": "Доброта, душевность", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "Надёжность, порядочность", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Характер, достоинство", "scores": {"narrative": "СБ"}},
                        "4": {"text": "Мудрость, опыт", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 4. Комплимент
                    "text": "Какие слова для тебя дороги?",
                    "options": {
                        "1": {"text": "«Ты замечательная мать/бабушка»", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "«На тебя можно положиться»", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "«Тебя уважают»", "scores": {"narrative": "СБ"}},
                        "4": {"text": "«Ты мудрая»", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 5. Новая компания
                    "text": "В незнакомой компании ты...",
                    "options": {
                        "1": {"text": "Общаюсь со всеми, мне легко", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "Присматриваюсь, не сразу открываюсь", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Оцениваю, кто здесь главный", "scores": {"narrative": "СБ"}},
                        "4": {"text": "Наблюдаю, слушаю", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 6. Деньги
                    "text": "На что потратишь неожиданную сумму?",
                    "options": {
                        "1": {"text": "На детей, внуков, семью", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "Отложу, на старость", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "На что-то статусное, дорогое", "scores": {"narrative": "СБ"}},
                        "4": {"text": "На путешествие, впечатления", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 7. Что бесит
                    "text": "Что тебя раздражает в людях?",
                    "options": {
                        "1": {"text": "Черствость, равнодушие", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "Безответственность", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Хамство, неуважение", "scores": {"narrative": "СБ"}},
                        "4": {"text": "Глупость, нежелание думать", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 8. Подарок
                    "text": "Какой подарок тебя порадует?",
                    "options": {
                        "1": {"text": "Внимание, забота, сюрприз", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "Что-то нужное, полезное", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Что-то дорогое, статусное", "scores": {"narrative": "СБ"}},
                        "4": {"text": "Книга, впечатления", "scores": {"narrative": "УБ"}}
                    }
                },
                {  # Вопрос 9. Страх
                    "text": "Чего ты опасаешься?",
                    "options": {
                        "1": {"text": "Одиночества", "scores": {"narrative": "ЧВ"}},
                        "2": {"text": "Бедности, немощи", "scores": {"narrative": "ТФ"}},
                        "3": {"text": "Потерять уважение", "scores": {"narrative": "СБ"}},
                        "4": {"text": "Деградации", "scores": {"narrative": "УБ"}}
                    }
                }
            ]

# ==================== БЛОК 2: РЕСУРСЫ (10 вопросов) ====================
COMMON_RESOURCES_QUESTIONS = [
    {  # Вопрос 10. Образование
        "text": "Какое у тебя образование?",
        "options": {
            "1": {"text": "Неполное среднее", "scores": {"education": 2, "edu_level": "LOW"}},
            "2": {"text": "Среднее (школа)", "scores": {"education": 4, "edu_level": "MEDIUM"}},
            "3": {"text": "Среднее специальное", "scores": {"education": 6, "edu_level": "MEDIUM"}},
            "4": {"text": "Высшее", "scores": {"education": 8, "edu_level": "HIGH"}},
            "5": {"text": "Два и более / учёная степень", "scores": {"education": 10, "edu_level": "VERY_HIGH"}}
        }
    },
    {  # Вопрос 11. Работа
        "text": "Кем ты работаешь?",
        "options": {
            "1": {"text": "Не работаю", "scores": {"job": "DEPENDENT", "income": 1}},
            "2": {"text": "Рабочий, персонал", "scores": {"job": "WORKER", "income": 3}},
            "3": {"text": "Офисный работник", "scores": {"job": "OFFICE", "income": 4}},
            "4": {"text": "Специалист (врач, учитель, инженер)", "scores": {"job": "PROFESSIONAL", "income": 5}},
            "5": {"text": "Руководитель, начальник", "scores": {"job": "MANAGER", "income": 7}},
            "6": {"text": "Свой бизнес", "scores": {"job": "BUSINESS", "income": 8}},
            "7": {"text": "Фрилансер", "scores": {"job": "FREELANCE", "income": 5}},
            "8": {"text": "Творческая профессия", "scores": {"job": "CREATIVE", "income": 4}}
        }
    },
    {  # Вопрос 12. Доход
        "text": "Как у тебя с деньгами?",
        "options": {
            "1": {"text": "Едва хватает на еду", "scores": {"money": 1}},
            "2": {"text": "Хватает на жизнь", "scores": {"money": 3}},
            "3": {"text": "Могу покупать крупные вещи", "scores": {"money": 5}},
            "4": {"text": "Обеспечен(а), есть накопления", "scores": {"money": 7}},
            "5": {"text": "Богат(а), деньги не проблема", "scores": {"money": 9}}
        }
    },
    {  # Вопрос 13. Жильё
        "text": "Где ты живёшь?",
        "options": {
            "1": {"text": "Снимаю угол/комнату", "scores": {"housing": 1}},
            "2": {"text": "С родителями/родственниками", "scores": {"housing": 2}},
            "3": {"text": "Снимаю квартиру", "scores": {"housing": 3}},
            "4": {"text": "Своя квартира/дом", "scores": {"housing": 5}},
            "5": {"text": "Несколько объектов", "scores": {"housing": 8}}
        }
    },
    {  # Вопрос 14. Рост
        "text": "Какой у тебя рост?",
        "options": {
            "1": {"text": "Ниже 160 см", "scores": {"height": 2}},
            "2": {"text": "160-170 см", "scores": {"height": 4}},
            "3": {"text": "170-180 см", "scores": {"height": 6}},
            "4": {"text": "180-190 см", "scores": {"height": 8}},
            "5": {"text": "Выше 190 см", "scores": {"height": 10}}
        }
    },
    {  # Вопрос 15. Внешность
        "text": "Как ты оцениваешь свою внешность?",
        "options": {
            "1": {"text": "Меня не замечают", "scores": {"looks": 2}},
            "2": {"text": "Обычная внешность", "scores": {"looks": 4}},
            "3": {"text": "Симпатичный(ая)", "scores": {"looks": 6}},
            "4": {"text": "Красивый(ая)", "scores": {"looks": 8}},
            "5": {"text": "Модельная внешность", "scores": {"looks": 10}}
        }
    },
    {  # Вопрос 16. Здоровье
        "text": "Как часто ты болеешь?",
        "options": {
            "1": {"text": "Постоянно", "scores": {"health": 2}},
            "2": {"text": "Несколько раз в год", "scores": {"health": 4}},
            "3": {"text": "Раз в год", "scores": {"health": 6}},
            "4": {"text": "Раз в несколько лет", "scores": {"health": 8}},
            "5": {"text": "Практически никогда", "scores": {"health": 10}}
        }
    },
    {  # Вопрос 17. Семейное положение
        "text": "Как у тебя с семьёй?",
        "options": {
            "1": {"text": "Никогда не был(а) в браке", "scores": {"marriage": 0, "marriages": 0}},
            "2": {"text": "В браке / в отношениях", "scores": {"marriage": 1, "marriages": 1}},
            "3": {"text": "Разведен(а)", "scores": {"marriage": 0, "marriages": 1}},
            "4": {"text": "Вдовец/вдова", "scores": {"marriage": 0, "marriages": 1}}
        }
    },
    {  # Вопрос 18. Дети
        "text": "Есть ли у тебя дети?",
        "options": {
            "1": {"text": "Нет детей", "scores": {"children": 0, "kids": 0}},
            "2": {"text": "Один ребёнок", "scores": {"children": 1, "kids": 1}},
            "3": {"text": "Двое детей", "scores": {"children": 2, "kids": 2}},
            "4": {"text": "Трое и больше", "scores": {"children": 3, "kids": 3}}
        }
    },
    {  # Вопрос 19. Друзья
        "text": "Сколько у тебя близких друзей?",
        "options": {
            "1": {"text": "Никого, я один(а)", "scores": {"friends": 1, "social": 1}},
            "2": {"text": "1-2 друга", "scores": {"friends": 3, "social": 3}},
            "3": {"text": "3-5 друзей", "scores": {"friends": 5, "social": 5}},
            "4": {"text": "5-10 человек", "scores": {"friends": 7, "social": 7}},
            "5": {"text": "Много друзей", "scores": {"friends": 9, "social": 9}}
        }
    }
]

# ==================== БЛОК 3: ДРЕВНИЕ ПРОГРАММЫ (7 вопросов) ====================
def get_ancient_program_questions(gender):
    """Возвращает вопросы для определения древней программы (F1-F6)"""
    
    # Общие для всех вопросы
    common = [
        {  # Вопрос 20. Спорт
            "text": "Каким спортом ты занимаешься?",
            "options": {
                "1": {"text": "Никаким, не люблю", "scores": {"ancient": "F2"}},
                "2": {"text": "Бег, плавание", "scores": {"ancient": "F2"}},
                "3": {"text": "Тренажерный зал", "scores": {"ancient": "F1"}},
                "4": {"text": "Единоборства, бокс", "scores": {"ancient": "F1"}},
                "5": {"text": "Йога, растяжка", "scores": {"ancient": "F3"}}
            }
        },
        {  # Вопрос 21. Конфликты
            "text": "Если кто-то лезет без очереди, ты...",
            "options": {
                "1": {"text": "Молчу, не хочу связываться", "scores": {"ancient": "F2"}},
                "2": {"text": "Смотрю в телефон, не замечаю", "scores": {"ancient": "F4"}},
                "3": {"text": "Жду, может кто-то другой скажет", "scores": {"ancient": "F3"}},
                "4": {"text": "Вежливо делаю замечание", "scores": {"ancient": "F5"}},
                "5": {"text": "Сразу высказываю", "scores": {"ancient": "F1"}}
            }
        },
        {  # Вопрос 22. Соцсети
            "text": "Как часто ты выкладываешь свои фото?",
            "options": {
                "1": {"text": "Никогда, не люблю", "scores": {"ancient": "F2"}},
                "2": {"text": "Только в сторис, на день", "scores": {"ancient": "F3"}},
                "3": {"text": "Раз в месяц, по настроению", "scores": {"ancient": "F6"}},
                "4": {"text": "Регулярно, веду страницу", "scores": {"ancient": "F5"}},
                "5": {"text": "Каждый день, блог", "scores": {"ancient": "F1"}}
            }
        },
        {  # Вопрос 23. Отношение к телу
            "text": "Как ты относишься к своему телу?",
            "options": {
                "1": {"text": "Стесняюсь, не нравится", "scores": {"ancient": "F2"}},
                "2": {"text": "Нормально, не задумываюсь", "scores": {"ancient": "F3"}},
                "3": {"text": "Принимаю, что есть", "scores": {"ancient": "F6"}},
                "4": {"text": "Забочусь, ухаживаю", "scores": {"ancient": "F5"}},
                "5": {"text": "Горжусь, показываю", "scores": {"ancient": "F1"}}
            }
        },
        {  # Вопрос 24. Сны
            "text": "Какие сны тебе чаще снятся?",
            "options": {
                "1": {"text": "Драки, погони, опасность", "scores": {"ancient": "F1"}},
                "2": {"text": "Что убегаю, прячусь", "scores": {"ancient": "F2"}},
                "3": {"text": "Зависаю, не могу пошевелиться", "scores": {"ancient": "F3"}},
                "4": {"text": "Странные, как в кино", "scores": {"ancient": "F4"}},
                "5": {"text": "Не помню, редко снятся", "scores": {"ancient": "F6"}}
            }
        }
    ]
    
    # Гендерно-специфичные вопросы
    if gender == "М":
        male_specific = [
            {  # Вопрос 25. Баня
                "text": "Как часто ты ходишь в баню?",
                "options": {
                    "1": {"text": "Никогда, не люблю", "scores": {"ancient": "F2"}},
                    "2": {"text": "Раз в год, с работы", "scores": {"ancient": "F5"}},
                    "3": {"text": "Иногда с друзьями", "scores": {"ancient": "F3"}},
                    "4": {"text": "Регулярно, раз в месяц", "scores": {"ancient": "F6"}},
                    "5": {"text": "Часто, своя баня", "scores": {"ancient": "F1"}}
                }
            },
            {  # Вопрос 26. Борода
                "text": "Как у тебя с бородой?",
                "options": {
                    "1": {"text": "Не растёт, гладко брею", "scores": {"ancient": "F6"}},
                    "2": {"text": "Щетина, немного", "scores": {"ancient": "F3"}},
                    "3": {"text": "Небольшая бородка", "scores": {"ancient": "F5"}},
                    "4": {"text": "Густая борода", "scores": {"ancient": "F1"}},
                    "5": {"text": "Очень густая", "scores": {"ancient": "F1"}}
                }
            },
            {  # Вопрос 27. Машина
                "text": "Какая у тебя машина?",
                "options": {
                    "1": {"text": "Нет, не нужна", "scores": {"ancient": "F2"}},
                    "2": {"text": "Эконом, чтобы ездила", "scores": {"ancient": "F3"}},
                    "3": {"text": "Надёжная, семейная", "scores": {"ancient": "F5"}},
                    "4": {"text": "Спортивная, быстрая", "scores": {"ancient": "F1"}},
                    "5": {"text": "Дорогая, статусная", "scores": {"ancient": "F1"}}
                }
            }
        ]
        return common + male_specific
    else:
        female_specific = [
            {  # Вопрос 25. Одежда
                "text": "Как ты одеваешься летом?",
                "options": {
                    "1": {"text": "Закрыто, не люблю открытое", "scores": {"ancient": "F2"}},
                    "2": {"text": "Как удобно, не задумываюсь", "scores": {"ancient": "F3"}},
                    "3": {"text": "Скромно, но аккуратно", "scores": {"ancient": "F5"}},
                    "4": {"text": "Открыто, нравится внимание", "scores": {"ancient": "F1"}},
                    "5": {"text": "Очень откровенно", "scores": {"ancient": "F1"}}
                }
            },
            {  # Вопрос 26. Отношения
                "text": "В отношениях с мужчиной ты чаще...",
                "options": {
                    "1": {"text": "Уступаю, чтобы не ссориться", "scores": {"ancient": "F5"}},
                    "2": {"text": "Молчу, терплю", "scores": {"ancient": "F3"}},
                    "3": {"text": "Ухожу, если что не так", "scores": {"ancient": "F2"}},
                    "4": {"text": "Договариваюсь, ищу компромисс", "scores": {"ancient": "F6"}},
                    "5": {"text": "Настаиваю на своём", "scores": {"ancient": "F1"}}
                }
            },
            {  # Вопрос 27. Интим
                "text": "В интимной близости тебе важнее...",
                "options": {
                    "1": {"text": "Чтобы партнёр был доволен", "scores": {"ancient": "F5"}},
                    "2": {"text": "Чтобы я была довольна", "scores": {"ancient": "F1"}},
                    "3": {"text": "Чтобы было комфортно", "scores": {"ancient": "F3"}},
                    "4": {"text": "Чтобы не было больно", "scores": {"ancient": "F2"}},
                    "5": {"text": "Мне всё равно", "scores": {"ancient": "F6"}}
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
    
    # База верификационных вопросов для разных комбинаций
    verification_db = {
        # ===== СБ + F1 (Силовой мир + Бей) =====
        ("СБ", "F1"): [
            {
                "text": "Вспомни случай из детства, когда тебя сильно обидели. Что ты сделал?",
                "options": {
                    "1": {"text": "Дал сдачи, даже если был слабее", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "Убежал и спрятался", "scores": {"verify": "ЧВ+F2"}},
                    "3": {"text": "Замер и терпел", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "Заплакал и пошёл жаловаться", "scores": {"verify": "ТФ+F5"}}
                }
            },
            {
                "text": "Кого ты больше уважаешь?",
                "options": {
                    "1": {"text": "Того, кто может постоять за себя", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "Того, кто избегает конфликтов", "scores": {"verify": "ЧВ+F2"}},
                    "3": {"text": "Того, кто всё просчитывает", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "Того, кто со всеми дружит", "scores": {"verify": "ТФ+F5"}}
                }
            },
            {
                "text": "Если бы ты был животным, каким?",
                "options": {
                    "1": {"text": "Лев, волк", "scores": {"verify": "СБ+F1"}},
                    "2": {"text": "Заяц, лань", "scores": {"verify": "ЧВ+F2"}},
                    "3": {"text": "Сова, лис", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "Собака (домашняя)", "scores": {"verify": "ТФ+F5"}}
                }
            }
        ],
        
        # ===== СБ + F5 (Силовой мир + Заискивай) =====
        ("СБ", "F5"): [
            {
                "text": "Как ты ведёшь себя с начальником?",
                "options": {
                    "1": {"text": "Стараюсь угодить, соглашаюсь", "scores": {"verify": "СБ+F5"}},
                    "2": {"text": "Могу поспорить, если не прав", "scores": {"verify": "УБ+F1"}},
                    "3": {"text": "Держусь независимо", "scores": {"verify": "ЧВ+F2"}},
                    "4": {"text": "Делаю вид, что не замечаю", "scores": {"verify": "ТФ+F3"}}
                }
            },
            {
                "text": "Что ты чувствуешь, когда тебя критикуют?",
                "options": {
                    "1": {"text": "Обиду и желание оправдаться", "scores": {"verify": "СБ+F5"}},
                    "2": {"text": "Злость, хочется ответить", "scores": {"verify": "УБ+F1"}},
                    "3": {"text": "Стыд, хочется провалиться", "scores": {"verify": "ЧВ+F2"}},
                    "4": {"text": "Мне всё равно", "scores": {"verify": "ТФ+F6"}}
                }
            }
        ],
        
        # ===== ЧВ + F2 (Мир внимания + Беги) =====
        ("ЧВ", "F2"): [
            {
                "text": "Как ты ведёшь себя на вечеринках?",
                "options": {
                    "1": {"text": "Стараюсь быть в центре", "scores": {"verify": "ЧВ+F1"}},
                    "2": {"text": "Держусь в стороне, наблюдаю", "scores": {"verify": "ЧВ+F2"}},
                    "3": {"text": "Общаюсь только со знакомыми", "scores": {"verify": "ТФ+F3"}},
                    "4": {"text": "Вообще не хожу", "scores": {"verify": "УБ+F2"}}
                }
            },
            {
                "text": "Что для тебя страшнее?",
                "options": {
                    "1": {"text": "Оказаться в центре внимания", "scores": {"verify": "ЧВ+F2"}},
                    "2": {"text": "Быть отвергнутым", "scores": {"verify": "ЧВ+F5"}},
                    "3": {"text": "Выглядеть глупо", "scores": {"verify": "УБ+F3"}},
                    "4": {"text": "Потерять контроль", "scores": {"verify": "СБ+F1"}}
                }
            }
        ],
        
        # ===== ТФ + F3 (Мир труда + Замри) =====
        ("ТФ", "F3"): [
            {
                "text": "Когда на работе аврал, ты...",
                "options": {
                    "1": {"text": "Теряюсь, не знаю за что хвататься", "scores": {"verify": "ТФ+F3"}},
                    "2": {"text": "Мобилизуюсь и работаю быстрее", "scores": {"verify": "ТФ+F1"}},
                    "3": {"text": "Ищу, кто поможет", "scores": {"verify": "ЧВ+F5"}},
                    "4": {"text": "Ухожу в себя, отключаюсь", "scores": {"verify": "УБ+F4"}}
                }
            },
            {
                "text": "Как ты принимаешь важные решения?",
                "options": {
                    "1": {"text": "Долго сомневаюсь, не решаюсь", "scores": {"verify": "ТФ+F3"}},
                    "2": {"text": "Быстро, интуитивно", "scores": {"verify": "СБ+F1"}},
                    "3": {"text": "Советуюсь с другими", "scores": {"verify": "ЧВ+F5"}},
                    "4": {"text": "Анализирую все варианты", "scores": {"verify": "УБ+F3"}}
                }
            }
        ],
        
        # ===== УБ + F4 (Мир знаний + Притворись мёртвым) =====
        ("УБ", "F4"): [
            {
                "text": "В стрессовой ситуации ты...",
                "options": {
                    "1": {"text": "Отключаюсь, как будто это не со мной", "scores": {"verify": "УБ+F4"}},
                    "2": {"text": "Начинаю суетиться", "scores": {"verify": "ЧВ+F2"}},
                    "3": {"text": "Застываю, не могу пошевелиться", "scores": {"verify": "ТФ+F3"}},
                    "4": {"text": "Действую агрессивно", "scores": {"verify": "СБ+F1"}}
                }
            },
            {
                "text": "Что говорят о тебе близкие?",
                "options": {
                    "1": {"text": "Что я витаю в облаках", "scores": {"verify": "УБ+F4"}},
                    "2": {"text": "Что я слишком эмоциональный", "scores": {"verify": "ЧВ+F2"}},
                    "3": {"text": "Что я надёжный", "scores": {"verify": "ТФ+F3"}},
                    "4": {"text": "Что я упрямый", "scores": {"verify": "СБ+F1"}}
                }
            }
        ]
    }
    
    # Ищем точное совпадение
    key = (narrative, program)
    if key in verification_db:
        return verification_db[key]
    
    # Если нет точного, возвращаем универсальные вопросы
    return [
        {
            "text": "Как ты обычно реагируешь на неожиданности?",
            "options": {
                "1": {"text": "Сразу действую", "scores": {"verify": "F1"}},
                "2": {"text": "Стараюсь уйти от ситуации", "scores": {"verify": "F2"}},
                "3": {"text": "Замираю, оцениваю", "scores": {"verify": "F3"}},
                "4": {"text": "Как будто не замечаю", "scores": {"verify": "F4"}}
            }
        },
        {
            "text": "Что важнее в жизни?",
            "options": {
                "1": {"text": "Быть уважаемым", "scores": {"verify": "СБ"}},
                "2": {"text": "Быть обеспеченным", "scores": {"verify": "ТФ"}},
                "3": {"text": "Быть умным", "scores": {"verify": "УБ"}},
                "4": {"text": "Быть любимым", "scores": {"verify": "ЧВ"}}
            }
        }
    ]

# ==================== ФУНКЦИИ ОПРЕДЕЛЕНИЯ ====================

def get_narrative_from_answers(answers):
    """Определяет нарратив на основе ответов на первые 8 вопросов"""
    scores = {"СБ": 0, "ТФ": 0, "УБ": 0, "ЧВ": 0}
    
    # Собираем все narrative из ответов
    for i in range(8):
        key = f'narrative_{i}'
        if key in answers:
            narr = answers[key]
            if narr in scores:
                scores[narr] += 1
    
    # Если нет данных - дефолт
    if sum(scores.values()) == 0:
        return "СБ", None, None
    
    # Сортируем
    sorted_narr = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    main = sorted_narr[0][0]
    second = sorted_narr[1][0] if len(sorted_narr) > 1 and sorted_narr[1][1] > 2 else None
    third = sorted_narr[2][0] if len(sorted_narr) > 2 and sorted_narr[2][1] > 1 else None
    
    logger.info(f"📊 Нарративы: main={main}, second={second}, third={third}, scores={dict(scores)}")
    
    return main, second, third

def get_ancient_program(answers):
    """Определяет доминирующую древнюю программу (F1-F6)"""
    scores = {"F1": 0, "F2": 0, "F3": 0, "F4": 0, "F5": 0, "F6": 0}
    
    # Собираем все ancient из ответов
    for i in range(8):  # максимум 8 вопросов о древних программах
        key = f'ancient_{i}'
        if key in answers:
            program = answers[key]
            if program in scores:
                scores[program] += 1
    
    logger.info(f"📊 Древние программы: {dict(scores)}")
    
    # Если нет данных - дефолт
    if sum(scores.values()) == 0:
        return "F3"
    
    return max(scores.items(), key=lambda x: x[1])[0]

def get_level(data, narrative):
    """Определяет уровень (1-6) на основе ресурсов"""
    base = 3
    
    # Бонусы
    if data.get('money', 0) > 7:
        base += 1
    if data.get('housing', 0) > 7:
        base += 1
    if data.get('education', 0) > 8:
        base += 1
    if data.get('looks', 0) > 8:
        base += 1
    if data.get('friends', 0) > 7:
        base += 1
    
    # Штрафы
    if data.get('money', 5) < 3:
        base -= 1
    if data.get('health', 5) < 3:
        base -= 1
    
    gender = data.get('gender', 'М')
    if gender == 'Ж':
        # Женские бонусы (будут собираться из вопросов)
        if data.get('breast', 0) > 7:
            base += 1
        if data.get('relationships', 0) > 7:
            base += 1
        if data.get('sex_work', 0) > 2:
            base += 1
    else:
        # Мужские бонусы
        if data.get('strength', 0) > 7:
            base += 1
        if data.get('testosterone', 0) > 7:
            base += 1
        if data.get('car', 0) > 3:
            base += 1
    
    return max(1, min(6, base))

def get_role_name(narrative, level, gender):
    """Название роли (для заголовка)"""
    roles_male = {
        "СБ": ["Бомж", "Шестёрка", "Смотрящий", "Вольный стрелок", "Разводящий", "Пахан"],
        "ТФ": ["Иждивенец", "Работяга", "Рантье", "Мастер", "Торгаш", "Хозяин"],
        "УБ": ["Пустышка", "Специалист", "Учитель", "Исследователь", "Продавец знаний", "Мыслитель"],
        "ЧВ": ["Зритель", "Помощник", "Лицо бренда", "Творец", "Организатор", "Владелец"]
    }
    roles_female = {
        "СБ": ["Бомжиха", "Шестёрка", "Смотрящая", "Вольная", "Разводящая", "Паханка"],
        "ТФ": ["Иждивенка", "Работяга", "Рантье", "Мастерица", "Торгашка", "Хозяйка"],
        "УБ": ["Пустышка", "Специалистка", "Учительница", "Исследовательница", "Продавщица знаний", "Мыслительница"],
        "ЧВ": ["Зрительница", "Помощница", "Лицо бренда", "Творица", "Организаторша", "Владелица"]
    }
    return (roles_female if gender == 'Ж' else roles_male)[narrative][level-1]

def verify_hypothesis(verification_answers, hypothesis):
    """
    Проверяет, подтверждается ли гипотеза
    Возвращает (успех, новая_гипотеза)
    """
    if not verification_answers:
        return False, hypothesis
    
    # Считаем подтверждения
    confirm_count = 0
    alternative_scores = {"СБ": 0, "ТФ": 0, "УБ": 0, "ЧВ": 0, 
                          "F1": 0, "F2": 0, "F3": 0, "F4": 0, "F5": 0, "F6": 0}
    
    for answer in verification_answers:
        if "+" in answer:  # Формат "СБ+F1"
            parts = answer.split("+")
            if len(parts) == 2:
                narr, prog = parts
                # Проверяем совпадение с гипотезой
                if narr == hypothesis["narrative"] and prog == hypothesis["program"]:
                    confirm_count += 1
                else:
                    # Учитываем альтернативы
                    if narr in alternative_scores:
                        alternative_scores[narr] += 1
                    if prog in alternative_scores:
                        alternative_scores[prog] += 1
        else:
            # Простой формат
            if answer == hypothesis["narrative"] or answer == hypothesis["program"]:
                confirm_count += 1
            else:
                if answer in alternative_scores:
                    alternative_scores[answer] += 1
    
    # Если большинство подтверждает - успех
    if confirm_count >= len(verification_answers) / 2:
        return True, hypothesis
    
    # Находим альтернативы
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
    """Начало гадания"""
    
    # Проверяем, есть ли сохранённые данные
    data = await state.get_data()
    if data and data.get('answers'):
        user_name = message.from_user.first_name or "путник"
        mystic = get_mystic_symbol()
        
        welcome_back = (
            f"{mystic} *Ты вернулся, {user_name}...* {mystic}\n\n"
            f"{get_separator()}\n\n"
            f"Я помню твою душу. Хочешь продолжить наше путешествие?\n\n"
            f"• 🔄 *Заново* — откроешь новые грани\n"
            f"• 👀 *Результаты* — заглянешь в уже открытое"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Пройти заново", callback_data="restart")
        builder.button(text="👀 Мои результаты", callback_data="show_results")
        builder.adjust(1)
        
        await message.answer(welcome_back, reply_markup=builder.as_markup())
        return
    
    # Новый пользователь
    user_name = message.from_user.first_name or "путник"
    mystic = get_mystic_symbol()
    
    intro = (
        f"{mystic} *Тайный шёпот* {mystic}\n\n"
        f"Здравствуй, {user_name}...\n\n"
        f"{get_separator()}\n\n"
        f"Я вижу твою душу сквозь время. Хочешь узнать, что скрыто от глаз?\n\n"
        f"За несколько вопросов я расскажу:\n"
        f"• 👶 *О том, что сформировало тебя*\n"
        f"• 🔍 *Кто ты есть на самом деле*\n"
        f"• 🔥 *О твоих тайных желаниях*\n"
        f"• ⏳ *Что ждёт тебя впереди*\n\n"
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
    """Объяснение"""
    await callback.answer()
    
    explanation = (
        f"🔮 *Немного правды* 🔮\n\n"
        f"{get_separator()}\n\n"
        f"Я не колдую — я *читаю тебя*.\n\n"
        f"Каждый твой ответ — ключ к твоей природе.\n"
        f"• 🧠 Как ты мыслишь\n"
        f"• 💓 Чего ты хочешь\n"
        f"• 🚀 Куда тебе двигаться\n\n"
        f"{get_separator()}\n\n"
        f"*Готов?*"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔮 Да", callback_data="start_test")
    builder.adjust(1)
    
    await callback.message.edit_text(explanation, reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data == "start_test")
async def start_test(callback: types.CallbackQuery, state: FSMContext):
    """Начало теста"""
    await callback.answer()
    
    # Очищаем состояние
    await state.clear()
    await state.update_data(
        answers={}, 
        last_message_id=None,
        verification_round=0,
        verification_answers=[]
    )
    await state.set_state(UserState.question_index)
    
    # Вступление
    mystic = get_mystic_symbol()
    await callback.message.edit_text(
        f"{mystic} *Сосредоточься...*\n\n"
        f"Я задам несколько вопросов. Отвечай честно.\n\n"
        f"*Первый вопрос...*"
    )
    await asyncio.sleep(2)
    
    # Вопрос о поле
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
        f"{get_mystic_symbol()} *Вопрос 1/27*\n\n"
        f"*{GENDER_QUESTION['text']}*",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(last_message_id=sent.message_id, question_index=0)

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
        f"{get_mystic_symbol()} *Вопрос 2/27*\n\n"
        f"*{AGE_QUESTION['text']}*",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(last_message_id=sent.message_id, question_index=1)

async def ask_question(user_id, index, state: FSMContext):
    """Задаёт обычный вопрос"""
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
    
    total_questions = 27
    
    # Определяем блок
    if index < 2:
        # Вопросы 0-1 уже обработаны отдельно
        return
    elif index < 10:  # 8 нарративных (2-9)
        narrative_q_idx = index - 2
        questions = get_narrative_questions(gender, age_group)
        q = questions[narrative_q_idx]
        block = "ПЕРВЫЙ КРУГ"
        q_num = index + 1
        prefix = "narrative"
    elif index < 20:  # 10 ресурсных (10-19)
        res_q_idx = index - 10
        q = COMMON_RESOURCES_QUESTIONS[res_q_idx]
        block = "ВТОРОЙ КРУГ"
        q_num = index + 1
        prefix = "res"
    else:  # 7 древних программ (20-26)
        ancient_q_idx = index - 20
        questions = get_ancient_program_questions(gender)
        q = questions[ancient_q_idx]
        block = "ТРЕТИЙ КРУГ"
        q_num = index + 1
        prefix = "ancient"
    
    progress = "█" * int((index + 1) / total_questions * 10) + "░" * (10 - int((index + 1) / total_questions * 10))
    
    builder = InlineKeyboardBuilder()
    for key, option in q["options"].items():
        # Для каждого вопроса сохраняем с правильным префиксом
        score_key = list(option["scores"].keys())[0]
        score_value = option["scores"][score_key]
        callback_data = f"ans_{index}_{key}_{prefix}_{score_key}_{score_value}"
        # Обрезаем если слишком длинный (макс 64 символа)
        if len(callback_data) > 64:
            # Используем сокращенный формат
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

async def ask_verification_question(user_id, state: FSMContext):
    """Задаёт верификационный вопрос"""
    data = await state.get_data()
    hypothesis = data.get('hypothesis')
    v_index = data.get('verification_index', 0)
    v_questions = data.get('verification_questions', [])
    
    if not v_questions or v_index >= len(v_questions):
        # Верификация завершена
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
        f"Я почти готов... Ещё один вопрос:\n\n"
        f"*{q['text']}*",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(
        last_message_id=sent.message_id,
        verification_index=v_index + 1
    )

async def finish_verification(user_id, state: FSMContext):
    """Завершение верификации и переход к финалу или новому кругу"""
    data = await state.get_data()
    hypothesis = data.get('hypothesis')
    verification_answers = data.get('verification_answers', [])
    round_num = data.get('verification_round', 1)
    
    # Проверяем гипотезу
    success, new_hypothesis = verify_hypothesis(verification_answers, hypothesis)
    
    if success or round_num >= 2:
        # Гипотеза подтверждена или закончились попытки
        await show_fortune(user_id, state, new_hypothesis)
    else:
        # Новый круг верификации
        new_questions = get_verification_questions(new_hypothesis)
        await state.update_data(
            hypothesis=new_hypothesis,
            verification_round=round_num + 1,
            verification_index=0,
            verification_answers=[],
            verification_questions=new_questions
        )
        
        # Сообщаем о новом круге
        mystic = get_mystic_symbol()
        await bot.send_message(
            user_id,
            f"{mystic} *Интересно...*\n\n"
            f"Твои ответы заставили меня задуматься. Позволь уточнить."
        )
        await asyncio.sleep(2)
        
        # Начинаем новый круг
        await ask_verification_question(user_id, state)

@dp.callback_query(lambda c: c.data.startswith('gender_'))
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    """Обработка пола"""
    await callback.answer()
    
    gender = callback.data.split('_')[1]
    
    data = await state.get_data()
    answers = data.get('answers', {})
    answers['gender'] = gender
    
    await state.update_data(answers=answers)
    
    # Удаляем сообщение
    try:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
    except:
        pass
    
    # Следующий вопрос - возраст
    await ask_age_question(callback.from_user.id, state)

@dp.callback_query(lambda c: c.data.startswith('age_'))
async def process_age(callback: types.CallbackQuery, state: FSMContext):
    """Обработка возраста"""
    await callback.answer()
    
    age_key = callback.data.split('_')[1]
    age_data = AGE_QUESTION["options"][age_key]["scores"]
    
    data = await state.get_data()
    answers = data.get('answers', {})
    answers['age'] = age_data['age']
    answers['age_group'] = age_data['age_group']
    
    await state.update_data(answers=answers)
    
    # Удаляем сообщение
    try:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
    except:
        pass
    
    # Первый нарративный вопрос (индекс 2)
    await ask_question(callback.from_user.id, 2, state)

@dp.callback_query(lambda c: c.data.startswith('ans_'))
async def process_answer(callback: types.CallbackQuery, state: FSMContext):
    """Обработка обычных ответов"""
    await callback.answer()
    
    parts = callback.data.split('_')
    idx = int(parts[1])
    key = parts[2]
    
    data = await state.get_data()
    answers = data.get('answers', {})
    gender = answers.get('gender', 'М')
    age_group = answers.get('age_group', 'ADULT')
    
    # Если есть дополнительные данные в callback
    if len(parts) > 5:
        prefix = parts[3]
        score_key = parts[4]
        score_value = parts[5]
    else:
        # Если нет, определяем из контекста
        if idx < 10:  # нарративные
            questions = get_narrative_questions(gender, age_group)
            q_idx = idx - 2
            q = questions[q_idx]
            score_key = list(q["options"][key]["scores"].keys())[0]
            score_value = q["options"][key]["scores"][score_key]
            prefix = "narrative"
        elif idx < 20:  # ресурсные
            q_idx = idx - 10
            q = COMMON_RESOURCES_QUESTIONS[q_idx]
            score_key = list(q["options"][key]["scores"].keys())[0]
            score_value = q["options"][key]["scores"][score_key]
            prefix = "res"
        else:  # древние программы
            questions = get_ancient_program_questions(gender)
            q_idx = idx - 20
            q = questions[q_idx]
            score_key = list(q["options"][key]["scores"].keys())[0]
            score_value = q["options"][key]["scores"][score_key]
            prefix = "ancient"
    
    # Сохраняем ответ
    if prefix == "narrative":
        answers[f'narrative_{idx-2}'] = score_value
    elif prefix == "res":
        answers[score_key] = int(score_value) if score_value.isdigit() else score_value
    elif prefix == "ancient":
        answers[f'ancient_{idx-20}'] = score_value
    
    await state.update_data(answers=answers)
    
    # Удаляем сообщение
    try:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
    except:
        pass
    
    # Проверяем, все ли вопросы заданы
    if idx + 1 >= 27:
        # Все основные вопросы отвечены - переходим к верификации
        await start_verification(callback.from_user.id, state)
    else:
        await ask_question(callback.from_user.id, idx + 1, state)

@dp.callback_query(lambda c: c.data.startswith('verif_'))
async def process_verification(callback: types.CallbackQuery, state: FSMContext):
    """Обработка верификационных ответов"""
    await callback.answer()
    
    parts = callback.data.split('_')
    v_idx = int(parts[1])
    score = parts[3]
    
    data = await state.get_data()
    verification_answers = data.get('verification_answers', [])
    verification_answers.append(score)
    
    await state.update_data(verification_answers=verification_answers)
    
    # Удаляем сообщение
    try:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
    except:
        pass
    
    # Следующий верификационный вопрос или завершение
    await ask_verification_question(callback.from_user.id, state)

@dp.callback_query(lambda c: c.data == "restart")
async def restart(callback: types.CallbackQuery, state: FSMContext):
    """Перезапуск"""
    await callback.answer()
    await state.clear()
    await cmd_start(callback.message, state)

@dp.callback_query(lambda c: c.data == "show_results")
async def show_results(callback: types.CallbackQuery, state: FSMContext):
    """Показать результаты (если есть)"""
    await callback.answer()
    data = await state.get_data()
    if data.get('answers'):
        # Используем последнюю гипотезу или формируем новую
        hypothesis = data.get('hypothesis')
        if hypothesis:
            await show_fortune(callback.from_user.id, state, hypothesis)
        else:
            # Формируем гипотезу из ответов
            answers = data.get('answers', {})
            narrative, second, third = get_narrative_from_answers(answers)
            program = get_ancient_program(answers)
            level = get_level(answers, narrative)
            hypothesis = {
                "narrative": narrative,
                "program": program,
                "level": level
            }
            await show_fortune(callback.from_user.id, state, hypothesis)
    else:
        await callback.message.answer("❌ Нет сохранённых результатов. Начни сначала /start")

async def start_verification(user_id, state: FSMContext):
    """Начинает верификацию после основных вопросов"""
    data = await state.get_data()
    answers = data.get('answers', {})
    
    # Формируем гипотезу
    narrative, second, third = get_narrative_from_answers(answers)
    program = get_ancient_program(answers)
    level = get_level(answers, narrative)
    
    hypothesis = {
        "narrative": narrative,
        "program": program,
        "level": level,
        "second": second,
        "third": third
    }
    
    logger.info(f"🔍 ГИПОТЕЗА: {hypothesis}")
    
    # Получаем верификационные вопросы
    v_questions = get_verification_questions(hypothesis)
    
    await state.update_data(
        hypothesis=hypothesis,
        verification_round=1,
        verification_index=0,
        verification_answers=[],
        verification_questions=v_questions
    )
    
    # Сообщаем о переходе к верификации
    mystic = get_mystic_symbol()
    await bot.send_message(
        user_id,
        f"{mystic} *Я почти вижу твою суть...*\n\n"
        f"Осталось уточнить несколько деталей."
    )
    await asyncio.sleep(2)
    
    # Начинаем верификацию
    await ask_verification_question(user_id, state)

async def show_fortune(user_id, state: FSMContext, hypothesis):
    """Показывает финальный результат"""
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
    third = hypothesis.get("third")
    
    # Получаем название роли для заголовка
    role = get_role_name(narrative, level, gender)
    
    # Удаляем последний вопрос
    last_id = data.get('last_message_id')
    if last_id:
        try:
            await bot.delete_message(user_id, last_id)
        except:
            pass
    
    logger.info(f"🔍 ФИНАЛ: нарратив={narrative}, программа={program}, уровень={level}, роль={role}")
    
    # Получаем интерпретацию
    interpretation = get_interpretation(
        gender=gender, 
        narrative=narrative, 
        level=level, 
        age=age,
        program=program,
        second_narrative=second, 
        third_narrative=third
    )
    
    # Формируем заголовок
    season = get_life_season(age)
    sep = get_separator()
    mystic = get_mystic_symbol()
    
    ancient_names = {
        "F1": "БЕЙ ⚔️",
        "F2": "БЕГИ 🏃",
        "F3": "ЗАМРИ 🧊",
        "F4": "ПРИТВОРИСЬ МЁРТВЫМ 💀",
        "F5": "ЗАИСКИВАЙ 🦊",
        "F6": "СДАЙСЯ 🏳️"
    }
    
    header = (
        f"{mystic} *Судьба {user_name}* {mystic}\n\n"
        f"{sep}\n"
        f"🌿 {season} — {age} лет\n"
        f"⚡ Твоя древняя программа: *{ancient_names.get(program, program)}*\n"
        f"📜 Твой мир: *{NARRATIVE_NAMES[narrative]}*\n"
        f"🎭 Твоя роль: *{role}*\n"
        f"{sep}\n\n"
    )
    
    # Отправляем
    await bot.send_chat_action(user_id, action="typing")
    await asyncio.sleep(2)
    
    # Разбиваем на части если длинное сообщение
    full_text = header + interpretation
    if len(full_text) > 4000:  # Лимит Telegram
        mid = len(full_text) // 2
        # Ищем место для разрыва (конец предложения)
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
    
    # Кнопка перезапуска
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
    """Запуск бота"""
    print("\n" + "="*50)
    print("🔮 ТАЙНЫЙ ШЁПОТ v3.0")
    print("="*50)
    print("🚀 Бот запущен и готов к работе...\n")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
