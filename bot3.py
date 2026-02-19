"""
Гадалка блять.. 🔮
Виртуальная бля..гадалка , которая расскажет о прошлом, настоящем и будущем
Включая самые сокровенные тайны, желания и интимные подробности
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
    question_index = State()        # Индекс текущего вопроса
    answers = State()               # Все ответы
    last_message_id = State()       # ID последнего сообщения для удаления

# ==================== ВОПРОСЫ ====================

# ОБЩИЕ ВОПРОСЫ ДЛЯ ВСЕХ (без гендерных пометок)
QUESTIONS = [
    {  # 0. Пол
        "text": "Скажи мне, кто ты...",
        "options": {
            "М": {"text": "👨 Мужчина", "scores": {"gender": "М"}},
            "Ж": {"text": "👩 Женщина", "scores": {"gender": "Ж"}}
        }
    },
    {  # 1. Возраст
        "text": "Сколько тебе лет?",
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
        "text": "Какое у тебя образование?",
        "options": {
            "1": {"text": "Неполное среднее", "scores": {"education": 2, "edu_level": "LOW"}},
            "2": {"text": "Среднее (школа)", "scores": {"education": 4, "edu_level": "MEDIUM"}},
            "3": {"text": "Среднее специальное", "scores": {"education": 6, "edu_level": "MEDIUM"}},
            "4": {"text": "Высшее", "scores": {"education": 8, "edu_level": "HIGH"}},
            "5": {"text": "Два и более / учёная степень", "scores": {"education": 10, "edu_level": "VERY_HIGH"}}
        }
    },
    {  # 3. Работа
        "text": "Кем ты работаешь?",
        "options": {
            "1": {"text": "Не работаю", "scores": {"job": "DEPENDENT", "income": 1}},
            "2": {"text": "Рабочий, обслуживающий персонал", "scores": {"job": "WORKER", "income": 3}},
            "3": {"text": "Офисный работник", "scores": {"job": "OFFICE", "income": 4}},
            "4": {"text": "Специалист (врач, учитель, инженер)", "scores": {"job": "PROFESSIONAL", "income": 5}},
            "5": {"text": "Руководитель, управленец", "scores": {"job": "MANAGER", "income": 7}},
            "6": {"text": "Бизнесмен, предприниматель", "scores": {"job": "BUSINESS", "income": 8}},
            "7": {"text": "Фрилансер, самозанятый", "scores": {"job": "FREELANCE", "income": 5}},
            "8": {"text": "Творческая профессия", "scores": {"job": "CREATIVE", "income": 4}}
        }
    },
    {  # 4. Доход
        "text": "Как у тебя с деньгами?",
        "options": {
            "1": {"text": "Едва хватает на еду", "scores": {"money": 1}},
            "2": {"text": "Хватает на жизнь, но без излишеств", "scores": {"money": 3}},
            "3": {"text": "Могу покупать крупные вещи", "scores": {"money": 5}},
            "4": {"text": "Обеспечен(а), есть накопления", "scores": {"money": 7}},
            "5": {"text": "Богат(а), деньги не проблема", "scores": {"money": 9}}
        }
    },
    {  # 5. Жильё
        "text": "Где ты живёшь?",
        "options": {
            "1": {"text": "Снимаю угол/комнату", "scores": {"housing": 1}},
            "2": {"text": "С родителями/родственниками", "scores": {"housing": 2}},
            "3": {"text": "Снимаю квартиру", "scores": {"housing": 3}},
            "4": {"text": "Своя квартира/дом", "scores": {"housing": 5}},
            "5": {"text": "Несколько объектов недвижимости", "scores": {"housing": 8}}
        }
    },
    {  # 6. Рост
        "text": "Какой у тебя рост?",
        "options": {
            "1": {"text": "Ниже 160 см", "scores": {"height": 2}},
            "2": {"text": "160-170 см", "scores": {"height": 4}},
            "3": {"text": "170-180 см", "scores": {"height": 6}},
            "4": {"text": "180-190 см", "scores": {"height": 8}},
            "5": {"text": "Выше 190 см", "scores": {"height": 10}}
        }
    },
    {  # 7. Внешность
        "text": "Как ты оцениваешь свою внешность?",
        "options": {
            "1": {"text": "Меня не замечают", "scores": {"looks": 2}},
            "2": {"text": "Обычная внешность", "scores": {"looks": 4}},
            "3": {"text": "Симпатичный(ая)", "scores": {"looks": 6}},
            "4": {"text": "Красивый(ая), привлекаю внимание", "scores": {"looks": 8}},
            "5": {"text": "Модельная внешность", "scores": {"looks": 10}}
        }
    },
    {  # 8. Здоровье
        "text": "Как часто ты болеешь?",
        "options": {
            "1": {"text": "Постоянно, каждый месяц", "scores": {"health": 2}},
            "2": {"text": "Несколько раз в год", "scores": {"health": 4}},
            "3": {"text": "Раз в год по сезону", "scores": {"health": 6}},
            "4": {"text": "Раз в несколько лет", "scores": {"health": 8}},
            "5": {"text": "Практически никогда", "scores": {"health": 10}}
        }
    },
    {  # 9. Семейное положение
        "text": "Какое у тебя семейное положение?",
        "options": {
            "1": {"text": "Никогда не был(а) в браке", "scores": {"marriage": 0, "marriages": 0}},
            "2": {"text": "В браке / в отношениях", "scores": {"marriage": 1, "marriages": 1}},
            "3": {"text": "Разведен(а) один раз", "scores": {"marriage": 0, "marriages": 1}},
            "4": {"text": "Разведен(а) дважды и более", "scores": {"marriage": 0, "marriages": 2}},
            "5": {"text": "Вдовец/вдова", "scores": {"marriage": 0, "marriages": 1}}
        }
    },
    {  # 10. Дети
        "text": "Есть ли у тебя дети?",
        "options": {
            "1": {"text": "Нет детей", "scores": {"children": 0, "kids": 0}},
            "2": {"text": "Один ребёнок", "scores": {"children": 1, "kids": 1}},
            "3": {"text": "Двое детей", "scores": {"children": 2, "kids": 2}},
            "4": {"text": "Трое и больше", "scores": {"children": 3, "kids": 3}}
        }
    },
    {  # 11. Друзья
        "text": "Сколько у тебя близких друзей?",
        "options": {
            "1": {"text": "Никого, я совсем один(а)", "scores": {"friends": 1, "social": 1}},
            "2": {"text": "1-2 друга", "scores": {"friends": 3, "social": 3}},
            "3": {"text": "3-5 друзей", "scores": {"friends": 5, "social": 5}},
            "4": {"text": "5-10 человек", "scores": {"friends": 7, "social": 7}},
            "5": {"text": "Целая команда, много друзей", "scores": {"friends": 9, "social": 9}}
        }
    }
]

# МУЖСКИЕ ВОПРОСЫ (без пометок о поле)
MALE_QUESTIONS = [
    {  # 12. Автомобиль
        "text": "Какой у тебя автомобиль?",
        "options": {
            "1": {"text": "Нет машины", "scores": {"car": 0, "car_type": "NONE", "status": 1}},
            "2": {"text": "Отечественный/старый", "scores": {"car": 1, "car_type": "OLD", "status": 2}},
            "3": {"text": "Бюджетный иномарка", "scores": {"car": 2, "car_type": "BUDGET", "status": 3}},
            "4": {"text": "Бизнес-класс", "scores": {"car": 3, "car_type": "BUSINESS", "status": 5}},
            "5": {"text": "Премиум/спортивный", "scores": {"car": 4, "car_type": "PREMIUM", "status": 7}},
            "6": {"text": "Внедорожник/большой джип", "scores": {"car": 4, "car_type": "SUV", "status": 6, "compensation": 1}}
        }
    },
    {  # 13. Баня
        "text": "Как часто ты ходишь в баню?",
        "options": {
            "1": {"text": "Никогда", "scores": {"banya": 1, "body_confidence": 2}},
            "2": {"text": "Раз в год по приглашению", "scores": {"banya": 3, "body_confidence": 4}},
            "3": {"text": "Иногда с друзьями", "scores": {"banya": 5, "body_confidence": 6}},
            "4": {"text": "Регулярно, это традиция", "scores": {"banya": 7, "body_confidence": 8}},
            "5": {"text": "У меня своя баня/сауна", "scores": {"banya": 9, "body_confidence": 7, "status": 5}}
        }
    },
    {  # 14. Отношение к верности
        "text": "Как ты относишься к верности?",
        "options": {
            "1": {"text": "Всегда верен, измены неприемлемы", "scores": {"cheating": 1, "loyalty": 9, "sex_drive": 3}},
            "2": {"text": "Было однажды, жалею", "scores": {"cheating": 3, "loyalty": 5, "sex_drive": 5}},
            "3": {"text": "Бывало, не вижу в этом проблемы", "scores": {"cheating": 5, "loyalty": 3, "sex_drive": 7}},
            "4": {"text": "Часто меняю женщин", "scores": {"cheating": 7, "loyalty": 1, "sex_drive": 9}},
            "5": {"text": "Не был в серьёзных отношениях", "scores": {"cheating": 2, "loyalty": 5, "sex_drive": 4}}
        }
    },
    {  # 15. Растительность на лице
        "text": "Как у тебя с растительностью на лице?",
        "options": {
            "1": {"text": "Растёт плохо", "scores": {"testosterone": 3, "masculinity": 3}},
            "2": {"text": "Нормально", "scores": {"testosterone": 5, "masculinity": 5}},
            "3": {"text": "Густая", "scores": {"testosterone": 7, "masculinity": 7}},
            "4": {"text": "Ношу бороду", "scores": {"testosterone": 8, "masculinity": 8}},
            "5": {"text": "Очень густая борода", "scores": {"testosterone": 9, "masculinity": 9}}
        }
    },
    {  # 16. Физическая сила
        "text": "Сколько раз можешь отжаться от пола?",
        "options": {
            "1": {"text": "0-5 раз", "scores": {"strength": 2, "fitness": 2}},
            "2": {"text": "5-15 раз", "scores": {"strength": 4, "fitness": 4}},
            "3": {"text": "15-30 раз", "scores": {"strength": 6, "fitness": 6}},
            "4": {"text": "30-50 раз", "scores": {"strength": 8, "fitness": 8}},
            "5": {"text": "Больше 50", "scores": {"strength": 10, "fitness": 10}}
        }
    },
    {  # 17. Телосложение
        "text": "Как ты оцениваешь своё телосложение?",
        "options": {
            "1": {"text": "Худощавое", "scores": {"body_type": "THIN", "size_confidence": 3}},
            "2": {"text": "Среднее", "scores": {"body_type": "AVERAGE", "size_confidence": 5}},
            "3": {"text": "Атлетичное", "scores": {"body_type": "ATHLETIC", "size_confidence": 7}},
            "4": {"text": "Крупное", "scores": {"body_type": "BIG", "size_confidence": 8}},
            "5": {"text": "Полное", "scores": {"body_type": "FULL", "size_confidence": 4}}
        }
    },
    {  # 18. Секретные фантазии
        "text": "Какие сны тебя будоражат?",
        "options": {
            "1": {"text": "О власти и деньгах", "scores": {"fantasy": "POWER", "kink": "DOMINANCE"}},
            "2": {"text": "О красивых женщинах", "scores": {"fantasy": "WOMEN", "kink": "HAREM"}},
            "3": {"text": "О приключениях и риске", "scores": {"fantasy": "ADVENTURE", "kink": "EXTREME"}},
            "4": {"text": "О признании и славе", "scores": {"fantasy": "FAME", "kink": "EXHIBITION"}},
            "5": {"text": "Не помню сны", "scores": {"fantasy": "NONE", "kink": "VANILLA"}}
        }
    }
]

# ЖЕНСКИЕ ВОПРОСЫ (без пометок о поле)
FEMALE_QUESTIONS = [
    {  # 12. Размер груди
        "text": "Какой у тебя размер груди?",
        "options": {
            "1": {"text": "0-1 размер (маленькая)", "scores": {"breast": 3, "fem_capital": 4, "body_confidence": 4}},
            "2": {"text": "2 размер", "scores": {"breast": 5, "fem_capital": 6, "body_confidence": 6}},
            "3": {"text": "3 размер", "scores": {"breast": 7, "fem_capital": 8, "body_confidence": 8}},
            "4": {"text": "4 размер и больше", "scores": {"breast": 9, "fem_capital": 9, "body_confidence": 7}},
            "5": {"text": "Не хочу отвечать", "scores": {"breast": 5, "fem_capital": 5, "body_confidence": 5}}
        }
    },
    {  # 13. Начало месячных
        "text": "Во сколько лет начались месячные?",
        "options": {
            "1": {"text": "До 11 лет (очень рано)", "scores": {"hormones": 8, "maturity": 8}},
            "2": {"text": "11-12 лет", "scores": {"hormones": 7, "maturity": 7}},
            "3": {"text": "12-14 лет", "scores": {"hormones": 6, "maturity": 6}},
            "4": {"text": "14-16 лет", "scores": {"hormones": 4, "maturity": 4}},
            "5": {"text": "После 16 лет", "scores": {"hormones": 3, "maturity": 3}}
        }
    },
    {  # 14. Выбор мужчин
        "text": "Какие мужчины тебе нравятся?",
        "options": {
            "1": {"text": "Сильные, доминантные, которые решают всё", "scores": {"mate": "ALPHA", "strategy": "DEPENDENT", "kink": "SUBMISSIVE"}},
            "2": {"text": "Уверенные, надёжные, с которыми спокойно", "scores": {"mate": "BETA", "strategy": "PARTNERSHIP", "kink": "VANILLA"}},
            "3": {"text": "Умные, интеллектуалы, с которыми интересно", "scores": {"mate": "GAMMA", "strategy": "INTELLECTUAL", "kink": "MENTAL"}},
            "4": {"text": "Богатые, статусные, которые могут обеспечить", "scores": {"mate": "DELTA", "strategy": "PROVIDER", "kink": "SUGAR"}},
            "5": {"text": "Красивые, харизматичные, с которыми не стыдно", "scores": {"mate": "OMEGA", "strategy": "STATUS", "kink": "EXHIBITION"}}
        }
    },
    {  # 15. Количество отношений
        "text": "Сколько у тебя было серьёзных отношений?",
        "options": {
            "1": {"text": "Ни одного", "scores": {"relationships": 0, "experience": 1}},
            "2": {"text": "Один", "scores": {"relationships": 1, "experience": 3}},
            "3": {"text": "2-3", "scores": {"relationships": 2, "experience": 5}},
            "4": {"text": "4-5", "scores": {"relationships": 3, "experience": 7}},
            "5": {"text": "Больше 5", "scores": {"relationships": 4, "experience": 9}}
        }
    },
    {  # 16. Интимный опыт за деньги
        "text": "Приходилось ли тебе зарабатывать, используя внешность?",
        "options": {
            "1": {"text": "Нет, никогда", "scores": {"sex_work": 0, "taboo": 1}},
            "2": {"text": "Были спонсоры, дорогие подарки", "scores": {"sex_work": 1, "taboo": 3}},
            "3": {"text": "Работала моделью/эскортом", "scores": {"sex_work": 2, "taboo": 5}},
            "4": {"text": "Был опыт в интимной индустрии", "scores": {"sex_work": 3, "taboo": 7}},
            "5": {"text": "Не хочу отвечать", "scores": {"sex_work": 1, "taboo": 4}}
        }
    },
    {  # 17. Любимая часть тела
        "text": "Что тебе нравится в своём теле больше всего?",
        "options": {
            "1": {"text": "Грудь", "scores": {"body_pride": "BREAST", "body_confidence": 6}},
            "2": {"text": "Попа", "scores": {"body_pride": "ASS", "body_confidence": 6}},
            "3": {"text": "Ноги", "scores": {"body_pride": "LEGS", "body_confidence": 6}},
            "4": {"text": "Глаза/лицо", "scores": {"body_pride": "FACE", "body_confidence": 6}},
            "5": {"text": "Ничего не нравится", "scores": {"body_pride": "NONE", "body_confidence": 2}}
        }
    },
    {  # 18. Интимные фантазии
        "text": "Какие сны тебя будоражат?",
        "options": {
            "1": {"text": "О сильном мужчине, который берёт контроль", "scores": {"fantasy": "ALPHA", "kink": "SUBMISSIVE"}},
            "2": {"text": "О богатстве и роскоши", "scores": {"fantasy": "WEALTH", "kink": "SUGAR"}},
            "3": {"text": "О страсти и диком сексе", "scores": {"fantasy": "PASSION", "kink": "WILD"}},
            "4": {"text": "О признании и славе", "scores": {"fantasy": "FAME", "kink": "EXHIBITION"}},
            "5": {"text": "Не помню сны", "scores": {"fantasy": "NONE", "kink": "VANILLA"}}
        }
    }
]

# ==================== ФУНКЦИИ ОПРЕДЕЛЕНИЯ НАРРАТИВА ====================

def get_narrative(data):
    """
    Определяем основной и второй нарратив с весовыми коэффициентами
    Возвращает (main_narrative, second_narrative, third_narrative)
    """
    scores = {"СБ": 0, "ТФ": 0, "УБ": 0, "ЧВ": 0}
    
    # ---- РАБОТА (вес 3) ----
    job = data.get('job', '')
    job_weights = {
        "DEPENDENT": {"ТФ": -2, "ЧВ": -1, "СБ": -1},
        "WORKER": {"ТФ": 4, "СБ": 2, "УБ": -1, "ЧВ": -1},
        "OFFICE": {"ТФ": 3, "УБ": 3, "ЧВ": 2, "СБ": 1},
        "PROFESSIONAL": {"УБ": 5, "ТФ": 3, "СБ": 2, "ЧВ": 2},
        "MANAGER": {"СБ": 4, "ТФ": 3, "ЧВ": 3, "УБ": 2},
        "BUSINESS": {"СБ": 5, "ТФ": 4, "ЧВ": 3, "УБ": 2},
        "FREELANCE": {"ТФ": 3, "ЧВ": 3, "УБ": 3, "СБ": 1},
        "CREATIVE": {"ЧВ": 5, "УБ": 3, "ТФ": 2, "СБ": 1}
    }
    if job in job_weights:
        for n, w in job_weights[job].items():
            scores[n] += w * 3
    
    # ---- ДОХОД (вес 2) ----
    money = data.get('money', 3)
    if money > 7:
        scores["СБ"] += 4
        scores["ТФ"] += 4
        scores["ЧВ"] += 2
    elif money > 4:
        scores["ТФ"] += 3
        scores["УБ"] += 2
        scores["СБ"] += 1
    else:
        scores["СБ"] -= 2
        scores["ТФ"] -= 1
        scores["ЧВ"] -= 1
    
    # ---- ЖИЛЬЁ (вес 2) ----
    housing = data.get('housing', 2)
    if housing > 5:
        scores["ТФ"] += 4
        scores["СБ"] += 3
    elif housing > 3:
        scores["ТФ"] += 2
        scores["УБ"] += 1
    
    # ---- ОБРАЗОВАНИЕ (вес 2) ----
    edu = data.get('education', 4)
    if edu > 7:
        scores["УБ"] += 6
        scores["ЧВ"] += 2
        scores["ТФ"] += 1
    elif edu > 4:
        scores["УБ"] += 3
        scores["ТФ"] += 2
        scores["ЧВ"] += 1
    else:
        scores["УБ"] -= 2
        scores["ТФ"] += 1
        scores["СБ"] += 1
    
    # ---- ВНЕШНОСТЬ (вес 2) ----
    looks = data.get('looks', 4)
    if looks > 7:
        scores["ЧВ"] += 6
        scores["СБ"] += 2
    elif looks < 3:
        scores["ЧВ"] -= 4
        scores["СБ"] -= 1
    
    # ---- ДРУЗЬЯ/СВЯЗИ (вес 1) ----
    friends = data.get('friends', 3)
    if friends > 7:
        scores["ЧВ"] += 3
        scores["СБ"] += 2
    elif friends < 3:
        scores["ЧВ"] -= 2
        scores["СБ"] -= 1
    
    # ---- СЕМЕЙНОЕ ПОЛОЖЕНИЕ (вес 1) ----
    marriages = data.get('marriages', 0)
    if marriages > 1:
        scores["ЧВ"] += 2
        scores["СБ"] += 1
    
    # ---- ДЕТИ (вес 1) ----
    kids = data.get('kids', 0)
    if kids > 0:
        scores["ТФ"] += 2
        scores["СБ"] += 1
    
    # ========== ГЕНДЕРНЫЕ ОСОБЕННОСТИ ==========
    gender = data.get('gender', 'М')
    
    if gender == 'Ж':
        # ЖЕНСКИЕ МАРКЕРЫ
        
        # Размер груди (вес 3)
        breast = data.get('breast', 5)
        if breast > 7:
            scores["ЧВ"] += 4
            scores["СБ"] += 2
        elif breast < 4:
            scores["ЧВ"] -= 2
            scores["СБ"] -= 1
        
        # Тип мужчин (вес 3)
        mate = data.get('mate', '')
        if mate == 'ALPHA':
            scores["СБ"] += 4
            scores["ЧВ"] -= 1
        elif mate == 'DELTA':
            scores["СБ"] += 3
            scores["ТФ"] += 3
        elif mate == 'GAMMA':
            scores["УБ"] += 4
        elif mate == 'OMEGA':
            scores["ЧВ"] += 4
        
        # Опыт интим-работы (вес 4)
        sex_work = data.get('sex_work', 0)
        if sex_work > 2:
            scores["ЧВ"] += 5
            scores["СБ"] += 3
        elif sex_work > 0:
            scores["ЧВ"] += 2
            scores["СБ"] += 1
        
        # Гормональный фон (вес 2)
        hormones = data.get('hormones', 5)
        if hormones > 7:
            scores["ЧВ"] += 3
            scores["СБ"] += 2
        elif hormones < 4:
            scores["ЧВ"] -= 2
            scores["СБ"] -= 1
        
        # Интимные фантазии (вес 2)
        kink = data.get('kink', '')
        if kink == 'SUBMISSIVE':
            scores["СБ"] += 3
        elif kink == 'SUGAR':
            scores["СБ"] += 2
            scores["ТФ"] += 2
        elif kink == 'WILD':
            scores["ЧВ"] += 3
        elif kink == 'MENTAL':
            scores["УБ"] += 3
        
    else:  # МУЖСКИЕ МАРКЕРЫ
        # Тестостерон (вес 3)
        testosterone = data.get('testosterone', 5)
        if testosterone > 7:
            scores["СБ"] += 5
            scores["ЧВ"] += 2
        elif testosterone < 4:
            scores["СБ"] -= 3
            scores["ЧВ"] -= 1
        
        # Автомобиль (вес 2)
        car = data.get('car_type', '')
        if car == 'PREMIUM':
            scores["СБ"] += 4
            scores["ЧВ"] += 4
        elif car == 'SUV':
            scores["СБ"] += 4
            scores["ТФ"] += 2
        elif car == 'BUSINESS':
            scores["ТФ"] += 3
            scores["СБ"] += 2
        elif car == 'NONE':
            scores["ТФ"] -= 1
            scores["ЧВ"] -= 1
        
        # Баня/телесная уверенность (вес 2)
        banya = data.get('banya', 3)
        if banya > 7:
            scores["СБ"] += 4
            scores["ТФ"] += 2
        elif banya < 3:
            scores["СБ"] -= 2
            scores["ЧВ"] -= 1
        
        # Физическая сила (вес 2)
        strength = data.get('strength', 4)
        if strength > 7:
            scores["СБ"] += 4
            scores["ТФ"] += 2
        elif strength < 3:
            scores["СБ"] -= 2
        
        # Измены/сексуальная активность (вес 2)
        cheating = data.get('cheating', 3)
        if cheating > 5:
            scores["ЧВ"] += 3
            scores["СБ"] += 2
        elif cheating < 2:
            scores["УБ"] += 1
            scores["ТФ"] += 1
        
        # Фантазии (вес 1)
        kink = data.get('kink', '')
        if kink == 'DOMINANCE':
            scores["СБ"] += 3
        elif kink == 'HAREM':
            scores["ЧВ"] += 3
        elif kink == 'EXTREME':
            scores["СБ"] += 2
            scores["ЧВ"] += 2
        elif kink == 'EXHIBITION':
            scores["ЧВ"] += 3
    
    # Нормализация (приводим к положительным значениям)
    min_score = min(scores.values())
    if min_score < 0:
        for n in scores:
            scores[n] -= min_score
    
    # Сортируем по убыванию
    sorted_narr = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    main = sorted_narr[0][0]
    second = sorted_narr[1][0] if len(sorted_narr) > 1 and sorted_narr[1][1] > sorted_narr[2][1] * 1.5 else None
    third = sorted_narr[2][0] if len(sorted_narr) > 2 and sorted_narr[2][1] > sorted_narr[3][1] * 2 else None
    
    return main, second, third


def get_level(data, narrative):
    """
    Определяем уровень в нарративе (1-6)
    """
    base = 3  # базовый уровень
    
    # Повышающие факторы
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
    
    # Гендерные факторы
    gender = data.get('gender', 'М')
    if gender == 'Ж':
        if data.get('breast', 0) > 7:
            base += 1
        if data.get('experience', 0) > 7:
            base += 1
        if data.get('sex_work', 0) > 2:
            base += 1
    else:
        if data.get('strength', 0) > 7:
            base += 1
        if data.get('testosterone', 0) > 7:
            base += 1
        if data.get('car', 0) > 3:
            base += 1
    
    # Корректировка по нарративу
    if narrative == "СБ":
        if data.get('strength', 0) < 3:
            base -= 1
        if data.get('body_confidence', 0) < 3:
            base -= 1
    elif narrative == "ТФ":
        if data.get('income', 0) < 3:
            base -= 1
        if data.get('job', '') in ['DEPENDENT']:
            base -= 2
    elif narrative == "УБ":
        if data.get('education', 0) < 4:
            base -= 1
    elif narrative == "ЧВ":
        if data.get('looks', 0) < 4:
            base -= 1
    
    return max(1, min(6, base))


def get_role_name(narrative, level, gender):
    """
    Получает название роли для отображения
    """
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
    roles = roles_female if gender == 'Ж' else roles_male
    return roles[narrative][level-1]

# ==================== ХЕНДЛЕРЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Начало гадания"""
    await state.clear()
    
    welcome = (
        "🔮 *Виртуальная гадалка* 🔮\n\n"
        "Я расскажу тебе о прошлом, настоящем и будущем.\n"
        "Никакой магии — только знание человеческой природы.\n"
        "Отвечай честно, и я увижу твою судьбу.\n\n"
        "Готова начать? Тогда первый вопрос..."
    )
    
    await message.answer(welcome)
    await state.set_state(UserState.gender)
    await state.update_data(answers={}, last_message_id=None)
    await ask_question(message.from_user.id, 0, state)


async def ask_question(user_id, index, state: FSMContext):
    """Задаёт вопрос по индексу, удаляя предыдущее сообщение"""
    data = await state.get_data()
    answers = data.get('answers', {})
    gender = answers.get('gender', 'М')
    
    # Удаляем предыдущее сообщение, если оно есть
    last_message_id = data.get('last_message_id')
    if last_message_id:
        try:
            await bot.delete_message(user_id, last_message_id)
        except:
            pass  # Если не удалось удалить (например, сообщение слишком старое)
    
    # Определяем общее количество вопросов
    total_questions = len(QUESTIONS) + (len(MALE_QUESTIONS) if gender == 'М' else len(FEMALE_QUESTIONS))
    
    if index >= total_questions:
        await show_fortune(user_id, state)
        return
    
    # Выбираем вопрос из соответствующего массива
    if index < len(QUESTIONS):
        q = QUESTIONS[index]
    elif gender == 'М':
        q = MALE_QUESTIONS[index - len(QUESTIONS)]
    else:
        q = FEMALE_QUESTIONS[index - len(QUESTIONS)]
    
    # Строим клавиатуру
    builder = InlineKeyboardBuilder()
    for key, option in q["options"].items():
        builder.button(text=option["text"], callback_data=f"ans_{index}_{key}")
    builder.adjust(1)  # вертикальное расположение
    
    # Отправляем новое сообщение и сохраняем его ID
    sent_message = await bot.send_message(
        user_id,
        f"*Вопрос {index+1}*: {q['text']}",
        reply_markup=builder.as_markup()
    )
    
    # Сохраняем ID последнего сообщения в состоянии
    await state.update_data(last_message_id=sent_message.message_id)


@dp.callback_query(lambda c: c.data.startswith('ans_'))
async def process_answer(callback: types.CallbackQuery, state: FSMContext):
    """Обработка ответа"""
    await callback.answer()
    
    # Парсим ответ
    _, index_str, answer_key = callback.data.split('_')
    index = int(index_str)
    
    # Получаем данные
    data = await state.get_data()
    answers = data.get('answers', {})
    gender = answers.get('gender', 'М')
    
    # Определяем вопрос
    if index < len(QUESTIONS):
        q = QUESTIONS[index]
    elif gender == 'М':
        q = MALE_QUESTIONS[index - len(QUESTIONS)]
    else:
        q = FEMALE_QUESTIONS[index - len(QUESTIONS)]
    
    # Сохраняем ответ
    scores = q["options"][answer_key]["scores"]
    for key, value in scores.items():
        answers[key] = value
    
    await state.update_data(answers=answers)
    
    # Удаляем сообщение с кнопками, на которое нажали
    try:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
    except:
        pass  # Если не удалось удалить
    
    # Переходим к следующему вопросу
    await ask_question(callback.from_user.id, index + 1, state)


async def show_fortune(user_id, state: FSMContext):
    """Показывает гадание с разбивкой на несколько сообщений"""
    data = await state.get_data()
    answers = data.get('answers', {})
    
    # Удаляем последний вопрос, если он есть
    last_message_id = data.get('last_message_id')
    if last_message_id:
        try:
            await bot.delete_message(user_id, last_message_id)
        except:
            pass
    
    gender = answers.get('gender', 'М')
    age = answers.get('age', 30)
    
    # Определяем нарративы
    narrative, second_narrative, third_narrative = get_narrative(answers)
    level = get_level(answers, narrative)
    role = get_role_name(narrative, level, gender)
    
    # Получаем интерпретацию
    interpretation = get_interpretation(
        gender=gender,
        narrative=narrative,
        level=level,
        age=age,
        second_narrative=second_narrative,
        third_narrative=third_narrative
    )
    
    # Формируем заголовок
    header = f"🔮 *Твоя судьба* 🔮\n\n"
    header += f"Твой мир — *{NARRATIVE_NAMES[narrative]}*\n"
    header += f"Твоя роль — *{role}*\n\n"
    
    # Разбиваем интерпретацию на части по 3500 символов
    max_len = 3500
    full_text = interpretation
    
    # Первое сообщение с заголовком
    first_part = header + full_text[:max_len]
    await bot.send_message(user_id, first_part)
    
    # Отправляем остальные части
    remaining = full_text[max_len:]
    part_num = 2
    
    while remaining:
        # Берем следующий кусок
        next_part = remaining[:max_len]
        remaining = remaining[max_len:]
        
        # Добавляем индикатор части
        next_part += f"\n\n*— часть {part_num} —*"
        
        await bot.send_message(user_id, next_part)
        part_num += 1
        await asyncio.sleep(1)  # небольшая задержка между сообщениями
    
    # Кнопка перезапуска
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Погадать ещё", callback_data="restart")
    builder.adjust(1)
    
    await bot.send_message(user_id, "✨ *Что дальше?* ✨\n\nХочешь узнать свою судьбу ещё раз?", 
                          reply_markup=builder.as_markup())
    
    await state.clear()


@dp.callback_query(lambda c: c.data == 'restart')
async def restart(callback: types.CallbackQuery, state: FSMContext):
    """Перезапуск"""
    await callback.answer()
    await cmd_start(callback.message, state)


async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
