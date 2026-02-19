#!/usr/bin/env python3
"""
🔮 ТАЙНЫЙ ШЁПОТ: Виртуальная гадалка
Раскроет тайны прошлого, настоящего и будущего
Никакой магии — только знание человеческой природы
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
    gender = State()               # Пол
    question_index = State()        # Индекс текущего вопроса
    answers = State()               # Все ответы
    last_message_id = State()       # ID последнего сообщения

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

# ==================== ВОПРОСЫ ====================

# ОБЩИЕ ВОПРОСЫ
QUESTIONS = [
    {  # 0. Пол
        "text": "Кто ты в этом мире?",
        "options": {
            "М": {"text": "👨 Мужчина", "scores": {"gender": "М"}},
            "Ж": {"text": "👩 Женщина", "scores": {"gender": "Ж"}}
        }
    },
    {  # 1. Возраст
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
    },
    {  # 2. Образование
        "text": "Какие знания ты нёс через годы?",
        "options": {
            "1": {"text": "Неполное среднее", "scores": {"education": 2, "edu_level": "LOW"}},
            "2": {"text": "Среднее (школа)", "scores": {"education": 4, "edu_level": "MEDIUM"}},
            "3": {"text": "Среднее специальное", "scores": {"education": 6, "edu_level": "MEDIUM"}},
            "4": {"text": "Высшее", "scores": {"education": 8, "edu_level": "HIGH"}},
            "5": {"text": "Два и более / учёная степень", "scores": {"education": 10, "edu_level": "VERY_HIGH"}}
        }
    },
    {  # 3. Работа
        "text": "Чем ты наполняешь свои дни?",
        "options": {
            "1": {"text": "Не работаю", "scores": {"job": "DEPENDENT", "income": 1}},
            "2": {"text": "Рабочий, персонал", "scores": {"job": "WORKER", "income": 3}},
            "3": {"text": "Офисный работник", "scores": {"job": "OFFICE", "income": 4}},
            "4": {"text": "Специалист (врач, учитель)", "scores": {"job": "PROFESSIONAL", "income": 5}},
            "5": {"text": "Руководитель", "scores": {"job": "MANAGER", "income": 7}},
            "6": {"text": "Бизнесмен", "scores": {"job": "BUSINESS", "income": 8}},
            "7": {"text": "Фрилансер", "scores": {"job": "FREELANCE", "income": 5}},
            "8": {"text": "Творческая профессия", "scores": {"job": "CREATIVE", "income": 4}}
        }
    },
    {  # 4. Доход
        "text": "Как щедра к тебе судьба в монетах?",
        "options": {
            "1": {"text": "Едва хватает на еду", "scores": {"money": 1}},
            "2": {"text": "Хватает на жизнь", "scores": {"money": 3}},
            "3": {"text": "Могу покупать крупные вещи", "scores": {"money": 5}},
            "4": {"text": "Обеспечен(а), есть накопления", "scores": {"money": 7}},
            "5": {"text": "Богат(а), деньги не проблема", "scores": {"money": 9}}
        }
    },
    {  # 5. Жильё
        "text": "Где приютилась твоя душа?",
        "options": {
            "1": {"text": "Снимаю угол/комнату", "scores": {"housing": 1}},
            "2": {"text": "С родителями/родственниками", "scores": {"housing": 2}},
            "3": {"text": "Снимаю квартиру", "scores": {"housing": 3}},
            "4": {"text": "Своя квартира/дом", "scores": {"housing": 5}},
            "5": {"text": "Несколько объектов", "scores": {"housing": 8}}
        }
    },
    {  # 6. Рост
        "text": "Как высоко ты над землёй?",
        "options": {
            "1": {"text": "Ниже 160 см", "scores": {"height": 2}},
            "2": {"text": "160-170 см", "scores": {"height": 4}},
            "3": {"text": "170-180 см", "scores": {"height": 6}},
            "4": {"text": "180-190 см", "scores": {"height": 8}},
            "5": {"text": "Выше 190 см", "scores": {"height": 10}}
        }
    },
    {  # 7. Внешность
        "text": "Как оценивают твой облик прохожие?",
        "options": {
            "1": {"text": "Меня не замечают", "scores": {"looks": 2}},
            "2": {"text": "Обычная внешность", "scores": {"looks": 4}},
            "3": {"text": "Симпатичный(ая)", "scores": {"looks": 6}},
            "4": {"text": "Красивый(ая)", "scores": {"looks": 8}},
            "5": {"text": "Модельная внешность", "scores": {"looks": 10}}
        }
    },
    {  # 8. Здоровье
        "text": "Как часто тело напоминает о себе?",
        "options": {
            "1": {"text": "Постоянно", "scores": {"health": 2}},
            "2": {"text": "Несколько раз в год", "scores": {"health": 4}},
            "3": {"text": "Раз в год", "scores": {"health": 6}},
            "4": {"text": "Раз в несколько лет", "scores": {"health": 8}},
            "5": {"text": "Практически никогда", "scores": {"health": 10}}
        }
    },
    {  # 9. Семейное положение
        "text": "Кого согреваешь теплом своим?",
        "options": {
            "1": {"text": "Никогда не был(а) в браке", "scores": {"marriage": 0, "marriages": 0}},
            "2": {"text": "В браке / в отношениях", "scores": {"marriage": 1, "marriages": 1}},
            "3": {"text": "Разведен(а) один раз", "scores": {"marriage": 0, "marriages": 1}},
            "4": {"text": "Разведен(а) дважды", "scores": {"marriage": 0, "marriages": 2}},
            "5": {"text": "Вдовец/вдова", "scores": {"marriage": 0, "marriages": 1}}
        }
    },
    {  # 10. Дети
        "text": "Оставил(а) ли след в потомках?",
        "options": {
            "1": {"text": "Нет детей", "scores": {"children": 0, "kids": 0}},
            "2": {"text": "Один ребёнок", "scores": {"children": 1, "kids": 1}},
            "3": {"text": "Двое детей", "scores": {"children": 2, "kids": 2}},
            "4": {"text": "Трое и больше", "scores": {"children": 3, "kids": 3}}
        }
    },
    {  # 11. Друзья
        "text": "Сколько душ готовы прийти на зов?",
        "options": {
            "1": {"text": "Никого, я один(а)", "scores": {"friends": 1, "social": 1}},
            "2": {"text": "1-2 друга", "scores": {"friends": 3, "social": 3}},
            "3": {"text": "3-5 друзей", "scores": {"friends": 5, "social": 5}},
            "4": {"text": "5-10 человек", "scores": {"friends": 7, "social": 7}},
            "5": {"text": "Много друзей", "scores": {"friends": 9, "social": 9}}
        }
    }
]

# МУЖСКИЕ ВОПРОСЫ
MALE_QUESTIONS = [
    {  # 12. Автомобиль
        "text": "Какое железное сердце служит тебе?",
        "options": {
            "1": {"text": "Нет машины", "scores": {"car": 0, "car_type": "NONE", "status": 1}},
            "2": {"text": "Отечественный/старый", "scores": {"car": 1, "car_type": "OLD", "status": 2}},
            "3": {"text": "Бюджетный иномарка", "scores": {"car": 2, "car_type": "BUDGET", "status": 3}},
            "4": {"text": "Бизнес-класс", "scores": {"car": 3, "car_type": "BUSINESS", "status": 5}},
            "5": {"text": "Премиум/спортивный", "scores": {"car": 4, "car_type": "PREMIUM", "status": 7}},
            "6": {"text": "Внедорожник/джип", "scores": {"car": 4, "car_type": "SUV", "status": 6}}
        }
    },
    {  # 13. Баня
        "text": "Как часто очищаешь тело и дух в бане?",
        "options": {
            "1": {"text": "Никогда", "scores": {"banya": 1, "body_confidence": 2}},
            "2": {"text": "Раз в год", "scores": {"banya": 3, "body_confidence": 4}},
            "3": {"text": "Иногда с друзьями", "scores": {"banya": 5, "body_confidence": 6}},
            "4": {"text": "Регулярно", "scores": {"banya": 7, "body_confidence": 8}},
            "5": {"text": "У меня своя баня", "scores": {"banya": 9, "body_confidence": 7}}
        }
    },
    {  # 14. Верность
        "text": "Что для тебя значит верность?",
        "options": {
            "1": {"text": "Святое, никогда не изменял", "scores": {"cheating": 1, "loyalty": 9, "sex_drive": 3}},
            "2": {"text": "Было однажды, жалею", "scores": {"cheating": 3, "loyalty": 5, "sex_drive": 5}},
            "3": {"text": "Бывало, не вижу проблемы", "scores": {"cheating": 5, "loyalty": 3, "sex_drive": 7}},
            "4": {"text": "Часто меняю женщин", "scores": {"cheating": 7, "loyalty": 1, "sex_drive": 9}},
            "5": {"text": "Не был в отношениях", "scores": {"cheating": 2, "loyalty": 5, "sex_drive": 4}}
        }
    },
    {  # 15. Растительность
        "text": "Как щедра природа на лице?",
        "options": {
            "1": {"text": "Растёт плохо", "scores": {"testosterone": 3, "masculinity": 3}},
            "2": {"text": "Нормально", "scores": {"testosterone": 5, "masculinity": 5}},
            "3": {"text": "Густая", "scores": {"testosterone": 7, "masculinity": 7}},
            "4": {"text": "Ношу бороду", "scores": {"testosterone": 8, "masculinity": 8}},
            "5": {"text": "Очень густая борода", "scores": {"testosterone": 9, "masculinity": 9}}
        }
    },
    {  # 16. Сила
        "text": "Сколько раз можешь оторвать себя от земли?",
        "options": {
            "1": {"text": "0-5 раз", "scores": {"strength": 2, "fitness": 2}},
            "2": {"text": "5-15 раз", "scores": {"strength": 4, "fitness": 4}},
            "3": {"text": "15-30 раз", "scores": {"strength": 6, "fitness": 6}},
            "4": {"text": "30-50 раз", "scores": {"strength": 8, "fitness": 8}},
            "5": {"text": "Больше 50", "scores": {"strength": 10, "fitness": 10}}
        }
    },
    {  # 17. Телосложение
        "text": "Какова твоя телесная форма?",
        "options": {
            "1": {"text": "Худощавое", "scores": {"body_type": "THIN", "size_confidence": 3}},
            "2": {"text": "Среднее", "scores": {"body_type": "AVERAGE", "size_confidence": 5}},
            "3": {"text": "Атлетичное", "scores": {"body_type": "ATHLETIC", "size_confidence": 7}},
            "4": {"text": "Крупное", "scores": {"body_type": "BIG", "size_confidence": 8}},
            "5": {"text": "Полное", "scores": {"body_type": "FULL", "size_confidence": 4}}
        }
    },
    {  # 18. Фантазии
        "text": "Какие тайные желания будоражат ночами?",
        "options": {
            "1": {"text": "О власти и деньгах", "scores": {"fantasy": "POWER", "kink": "DOMINANCE"}},
            "2": {"text": "О красивых женщинах", "scores": {"fantasy": "WOMEN", "kink": "HAREM"}},
            "3": {"text": "О приключениях", "scores": {"fantasy": "ADVENTURE", "kink": "EXTREME"}},
            "4": {"text": "О признании и славе", "scores": {"fantasy": "FAME", "kink": "EXHIBITION"}},
            "5": {"text": "Не помню сны", "scores": {"fantasy": "NONE", "kink": "VANILLA"}}
        }
    }
]

# ЖЕНСКИЕ ВОПРОСЫ
FEMALE_QUESTIONS = [
    {  # 12. Размер груди
        "text": "Каков твой знак женственности?",
        "options": {
            "1": {"text": "0-1 размер", "scores": {"breast": 3, "fem_capital": 4, "body_confidence": 4}},
            "2": {"text": "2 размер", "scores": {"breast": 5, "fem_capital": 6, "body_confidence": 6}},
            "3": {"text": "3 размер", "scores": {"breast": 7, "fem_capital": 8, "body_confidence": 8}},
            "4": {"text": "4 размер и больше", "scores": {"breast": 9, "fem_capital": 9, "body_confidence": 7}},
            "5": {"text": "Не хочу отвечать", "scores": {"breast": 5, "fem_capital": 5, "body_confidence": 5}}
        }
    },
    {  # 13. Месячные
        "text": "Когда природа впервые заявила о себе?",
        "options": {
            "1": {"text": "До 11 лет", "scores": {"hormones": 8, "maturity": 8}},
            "2": {"text": "11-12 лет", "scores": {"hormones": 7, "maturity": 7}},
            "3": {"text": "12-14 лет", "scores": {"hormones": 6, "maturity": 6}},
            "4": {"text": "14-16 лет", "scores": {"hormones": 4, "maturity": 4}},
            "5": {"text": "После 16 лет", "scores": {"hormones": 3, "maturity": 3}}
        }
    },
    {  # 14. Выбор мужчин
        "text": "К какому типу мужчин тянется душа?",
        "options": {
            "1": {"text": "Сильные, доминантные", "scores": {"mate": "ALPHA", "strategy": "DEPENDENT", "kink": "SUBMISSIVE"}},
            "2": {"text": "Уверенные, надёжные", "scores": {"mate": "BETA", "strategy": "PARTNERSHIP", "kink": "VANILLA"}},
            "3": {"text": "Умные, интеллектуалы", "scores": {"mate": "GAMMA", "strategy": "INTELLECTUAL", "kink": "MENTAL"}},
            "4": {"text": "Богатые, статусные", "scores": {"mate": "DELTA", "strategy": "PROVIDER", "kink": "SUGAR"}},
            "5": {"text": "Красивые, харизматичные", "scores": {"mate": "OMEGA", "strategy": "STATUS", "kink": "EXHIBITION"}}
        }
    },
    {  # 15. Количество отношений
        "text": "Скольким дарила своё сердце?",
        "options": {
            "1": {"text": "Ни одного", "scores": {"relationships": 0, "experience": 1}},
            "2": {"text": "Один", "scores": {"relationships": 1, "experience": 3}},
            "3": {"text": "2-3", "scores": {"relationships": 2, "experience": 5}},
            "4": {"text": "4-5", "scores": {"relationships": 3, "experience": 7}},
            "5": {"text": "Больше 5", "scores": {"relationships": 4, "experience": 9}}
        }
    },
    {  # 16. Интимный опыт
        "text": "Приходилось ли платить телом за блага?",
        "options": {
            "1": {"text": "Нет, никогда", "scores": {"sex_work": 0, "taboo": 1}},
            "2": {"text": "Были спонсоры", "scores": {"sex_work": 1, "taboo": 3}},
            "3": {"text": "Работала моделью/эскортом", "scores": {"sex_work": 2, "taboo": 5}},
            "4": {"text": "Был опыт", "scores": {"sex_work": 3, "taboo": 7}},
            "5": {"text": "Не хочу отвечать", "scores": {"sex_work": 1, "taboo": 4}}
        }
    },
    {  # 17. Любимая часть тела
        "text": "Что в себе ты любишь больше всего?",
        "options": {
            "1": {"text": "Грудь", "scores": {"body_pride": "BREAST", "body_confidence": 6}},
            "2": {"text": "Попа", "scores": {"body_pride": "ASS", "body_confidence": 6}},
            "3": {"text": "Ноги", "scores": {"body_pride": "LEGS", "body_confidence": 6}},
            "4": {"text": "Глаза/лицо", "scores": {"body_pride": "FACE", "body_confidence": 6}},
            "5": {"text": "Ничего не нравится", "scores": {"body_pride": "NONE", "body_confidence": 2}}
        }
    },
    {  # 18. Фантазии
        "text": "Какие тайные желания будоражат ночами?",
        "options": {
            "1": {"text": "О сильном мужчине", "scores": {"fantasy": "ALPHA", "kink": "SUBMISSIVE"}},
            "2": {"text": "О богатстве", "scores": {"fantasy": "WEALTH", "kink": "SUGAR"}},
            "3": {"text": "О страсти", "scores": {"fantasy": "PASSION", "kink": "WILD"}},
            "4": {"text": "О славе", "scores": {"fantasy": "FAME", "kink": "EXHIBITION"}},
            "5": {"text": "Не помню сны", "scores": {"fantasy": "NONE", "kink": "VANILLA"}}
        }
    }
]

# ==================== ФУНКЦИИ ОПРЕДЕЛЕНИЯ ====================

def get_narrative(data):
    """Определяем нарративы"""
    scores = {"СБ": 0, "ТФ": 0, "УБ": 0, "ЧВ": 0}
    
    job = data.get('job', '')
    job_weights = {
        "WORKER": {"ТФ": 4, "СБ": 2},
        "OFFICE": {"ТФ": 3, "УБ": 3, "ЧВ": 2},
        "PROFESSIONAL": {"УБ": 5, "ТФ": 3},
        "MANAGER": {"СБ": 4, "ТФ": 3, "ЧВ": 3},
        "BUSINESS": {"СБ": 5, "ТФ": 4, "ЧВ": 3},
        "FREELANCE": {"ТФ": 3, "ЧВ": 3, "УБ": 3},
        "CREATIVE": {"ЧВ": 5, "УБ": 3}
    }
    if job in job_weights:
        for n, w in job_weights[job].items():
            scores[n] += w * 3
    
    money = data.get('money', 3)
    if money > 7:
        scores["СБ"] += 4
        scores["ТФ"] += 4
    elif money > 4:
        scores["ТФ"] += 3
        scores["УБ"] += 2
        scores["СБ"] += 1
    
    edu = data.get('education', 4)
    if edu > 7:
        scores["УБ"] += 6
    elif edu > 4:
        scores["УБ"] += 3
        scores["ТФ"] += 2
    
    looks = data.get('looks', 4)
    if looks > 7:
        scores["ЧВ"] += 6
        scores["СБ"] += 2
    
    gender = data.get('gender', 'М')
    if gender == 'Ж':
        breast = data.get('breast', 5)
        if breast > 7:
            scores["ЧВ"] += 4
            scores["СБ"] += 2
        mate = data.get('mate', '')
        if mate == 'ALPHA':
            scores["СБ"] += 4
        elif mate == 'DELTA':
            scores["СБ"] += 3
            scores["ТФ"] += 3
        elif mate == 'GAMMA':
            scores["УБ"] += 4
    else:
        testosterone = data.get('testosterone', 5)
        if testosterone > 7:
            scores["СБ"] += 5
            scores["ЧВ"] += 2
        strength = data.get('strength', 4)
        if strength > 7:
            scores["СБ"] += 4
            scores["ТФ"] += 2
    
    sorted_narr = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    main = sorted_narr[0][0]
    second = sorted_narr[1][0] if sorted_narr[1][1] > sorted_narr[2][1] * 1.5 else None
    third = sorted_narr[2][0] if len(sorted_narr) > 2 and sorted_narr[2][1] > sorted_narr[3][1] * 2 else None
    
    return main, second, third

def get_level(data, narrative):
    """Определяем уровень"""
    base = 3
    
    if data.get('money', 0) > 7:
        base += 1
    if data.get('housing', 0) > 7:
        base += 1
    if data.get('education', 0) > 8:
        base += 1
    if data.get('looks', 0) > 8:
        base += 1
    
    gender = data.get('gender', 'М')
    if gender == 'Ж':
        if data.get('breast', 0) > 7:
            base += 1
        if data.get('experience', 0) > 7:
            base += 1
    else:
        if data.get('strength', 0) > 7:
            base += 1
        if data.get('testosterone', 0) > 7:
            base += 1
    
    return max(1, min(6, base))

def get_role_name(narrative, level, gender):
    """Название роли"""
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

# ==================== ХЕНДЛЕРЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Начало гадания — с интригой и атмосферой"""
    
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
    
    # Новый пользователь — создаём атмосферу
    user_name = message.from_user.first_name or "путник"
    mystic = get_mystic_symbol()
    
    intro = (
        f"{mystic} *Тайный шёпот* {mystic}\n\n"
        f"Здравствуй, {user_name}...\n\n"
        f"{get_separator()}\n\n"
        f"Я вижу твою душу сквозь время. Хочешь узнать, что скрыто от глаз?\n\n"
        f"За те несколько вопросов, что я задам, я расскажу:\n"
        f"• 👶 *О том, что сформировало тебя*\n"
        f"• 🔍 *Кто ты есть на самом деле*\n"
        f"• 🔥 *О твоих тайных желаниях*\n"
        f"• ⏳ *Что ждёт тебя впереди*\n\n"
        f"{get_separator()}\n\n"
        f"*Готов заглянуть за завесу?*"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔮 Начать гадание", callback_data="start_test")
    builder.button(text="❓ Что это за магия?", callback_data="why_details")
    builder.adjust(1)
    
    await message.answer(intro, reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data == "why_details")
async def why_details(callback: types.CallbackQuery, state: FSMContext):
    """Объяснение магии"""
    await callback.answer()
    
    explanation = (
        f"🔮 *Немного правды о магии* 🔮\n\n"
        f"{get_separator()}\n\n"
        f"Я не колдую — я *читаю тебя*.\n\n"
        f"Каждый твой ответ — это ключ к твоей природе.\n"
        f"Я вижу:\n"
        f"• 🧠 Как ты мыслишь\n"
        f"• 💓 Чего ты хочешь на самом деле\n"
        f"• 🚀 Куда тебе двигаться\n\n"
        f"Это не магия — это *знание человеческой души*.\n\n"
        f"{get_separator()}\n\n"
        f"*Готов узнать себя настоящего?*"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔮 Да, я готов", callback_data="start_test")
    builder.adjust(1)
    
    await callback.message.edit_text(explanation, reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data == "start_test")
async def start_test(callback: types.CallbackQuery, state: FSMContext):
    """Начало теста"""
    await callback.answer()
    
    # Очищаем состояние, но сохраняем важное
    data = await state.get_data()
    saved_invites = data.get('sexual_invites', [])
    
    await state.clear()
    await state.update_data(answers={}, last_message_id=None, sexual_invites=saved_invites)
    await state.set_state(UserState.gender)
    
    # Мистическое вступление
    mystic = get_mystic_symbol()
    await callback.message.edit_text(
        f"{mystic} *Сосредоточься...*\n\n"
        f"Я задам несколько вопросов. Отвечай честно — иначе звёзды солгут.\n\n"
        f"*Первый вопрос...*"
    )
    await asyncio.sleep(2)
    
    await ask_question(callback.from_user.id, 0, state)

async def ask_question(user_id, index, state: FSMContext):
    """Задаёт вопрос, удаляя предыдущий"""
    data = await state.get_data()
    answers = data.get('answers', {})
    gender = answers.get('gender', 'М')
    
    # Удаляем предыдущее сообщение
    last_id = data.get('last_message_id')
    if last_id:
        try:
            await bot.delete_message(user_id, last_id)
        except:
            pass
    
    # Определяем общее количество вопросов
    total = len(QUESTIONS) + (len(MALE_QUESTIONS) if gender == 'М' else len(FEMALE_QUESTIONS))
    
    if index >= total:
        await show_fortune(user_id, state)
        return
    
    # Выбираем вопрос
    if index < len(QUESTIONS):
        q = QUESTIONS[index]
    elif gender == 'М':
        q = MALE_QUESTIONS[index - len(QUESTIONS)]
    else:
        q = FEMALE_QUESTIONS[index - len(QUESTIONS)]
    
    # Прогресс
    progress = "░" * 10
    filled = int(index / total * 10)
    progress = "█" * filled + "░" * (10 - filled)
    
    # Клавиатура
    builder = InlineKeyboardBuilder()
    for key, option in q["options"].items():
        builder.button(text=option["text"], callback_data=f"ans_{index}_{key}")
    builder.adjust(1)
    
    # Отправляем вопрос
    sent = await bot.send_message(
        user_id,
        f"{get_mystic_symbol()} *Вопрос {index+1}/{total}*\n"
        f"`{progress}`\n\n"
        f"*{q['text']}*",
        reply_markup=builder.as_markup()
    )
    
    await state.update_data(last_message_id=sent.message_id)

@dp.callback_query(lambda c: c.data.startswith('ans_'))
async def process_answer(callback: types.CallbackQuery, state: FSMContext):
    """Обработка ответа"""
    await callback.answer()
    
    _, idx_str, key = callback.data.split('_')
    idx = int(idx_str)
    
    data = await state.get_data()
    answers = data.get('answers', {})
    gender = answers.get('gender', 'М')
    
    # Определяем вопрос
    if idx < len(QUESTIONS):
        q = QUESTIONS[idx]
    elif gender == 'М':
        q = MALE_QUESTIONS[idx - len(QUESTIONS)]
    else:
        q = FEMALE_QUESTIONS[idx - len(QUESTIONS)]
    
    # Сохраняем ответ
    for k, v in q["options"][key]["scores"].items():
        answers[k] = v
    
    await state.update_data(answers=answers)
    
    # Удаляем сообщение с кнопками
    try:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
    except:
        pass
    
    await ask_question(callback.from_user.id, idx + 1, state)

async def show_fortune(user_id, state: FSMContext):
    """Показывает гадание — красиво и без дублей"""
    data = await state.get_data()
    answers = data.get('answers', {})
    
    # Удаляем последний вопрос
    last_id = data.get('last_message_id')
    if last_id:
        try:
            await bot.delete_message(user_id, last_id)
        except:
            pass
    
    gender = answers.get('gender', 'М')
    age = answers.get('age', 30)
    user = await bot.get_chat(user_id)
    user_name = user.first_name or "путник"
    
    # Определяем нарративы
    narrative, second, third = get_narrative(answers)
    level = get_level(answers, narrative)
    role = get_role_name(narrative, level, gender)
    
    # Получаем интерпретацию
    interpretation = get_interpretation(
        gender=gender, narrative=narrative, level=level, age=age,
        second_narrative=second, third_narrative=third
    )
    
    # Убираем дублирующиеся заголовки
    lines = interpretation.split('\n')
    if len(lines) > 2 and ('ТВОЙ МИР:' in lines[0] or 'ТВОЯ РОЛЬ:' in lines[0]):
        interpretation = '\n'.join(lines[2:])
    
    # Красивый заголовок
    season = get_life_season(age)
    sep = get_separator()
    mystic = get_mystic_symbol()
    
    header = (
        f"{mystic} *Судьба {user_name}* {mystic}\n\n"
        f"{sep}\n"
        f"🌿 {season} — {age} лет\n"
        f"📜 Твой мир: *{NARRATIVE_NAMES[narrative]}*\n"
        f"🎭 Твоя роль: *{role}*\n"
        f"{sep}\n\n"
    )
    
    # Сила
    secret_powers = {
        "СБ": "💪 *Твоя сила:* выживать там, где другие ломаются.",
        "ТФ": "🔨 *Твоя сила:* создавать порядок из хаоса.",
        "УБ": "🧠 *Твоя сила:* видеть скрытое от других.",
        "ЧВ": "✨ *Твоя сила:* очаровывать, даже когда молчишь."
    }
    secret_power = secret_powers.get(narrative, "🌟 *Твоя сила:* быть собой.")
    
    # Предсказание
    daily = [
        "🌟 *Знак свыше:* жди неожиданную встречу.",
        "🌙 *Знак свыше:* прислушайся к снам.",
        "⭐ *Знак свыше:* маленькая радость уже близко.",
        "🕊️ *Знак свыше:* избегай конфликтов сегодня.",
        "💫 *Знак свыше:* удача в делах."
    ]
    
    # Разбиваем на 2 части максимум
    parts = []
    max_len = 3500
    
    # Первая часть: заголовок + первая половина интерпретации
    first_half = interpretation[:len(interpretation)//2]
    parts.append(header + first_half)
    
    # Вторая часть: вторая половина + сила + предсказание
    second_half = interpretation[len(interpretation)//2:]
    second_part = second_half + f"\n\n{sep}\n\n{secret_power}\n\n{random.choice(daily)}"
    parts.append(second_part)
    
    # Отправляем с эффектом печати
    await bot.send_chat_action(user_id, action="typing")
    await asyncio.sleep(2)
    await bot.send_message(user_id, parts[0])
    
    await bot.send_chat_action(user_id, action="typing")
    await asyncio.sleep(2)
    await bot.send_message(user_id, parts[1])
    
    # Кнопки
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

@dp.callback_query(lambda c: c.data == "restart")
async def restart(callback: types.CallbackQuery, state: FSMContext):
    """Перезапуск"""
    await callback.answer()
    await state.clear()
    await cmd_start(callback.message, state)

@dp.callback_query(lambda c: c.data == "show_results")
async def show_results(callback: types.CallbackQuery, state: FSMContext):
    """Показать сохранённые результаты"""
    await callback.answer()
    await show_fortune(callback.from_user.id, state)

# ==================== ЗАПУСК ====================

async def main():
    """Запуск бота"""
    print("\n" + "="*50)
    print("🔮 ТАЙНЫЙ ШЁПОТ — Виртуальная гадалка")
    print("="*50)
    print("🚀 Бот запущен и готов к работе...\n")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
