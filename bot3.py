"""
Гадалка 🔮
Виртуальная гадалка, которая расскажет о прошлом, настоящем и будущем
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

# ==================== ВОПРОСЫ ====================

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
        "text": "Как у тебя с деньгами?",
        "options": {
            "1": {"text": "Едва хватает на еду", "scores": {"money": 1}},
            "2": {"text": "Хватает на жизнь", "scores": {"money": 3}},
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
            "5": {"text": "Несколько объектов", "scores": {"housing": 8}}
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
        "text": "Как ты выглядишь?",
        "options": {
            "1": {"text": "Меня не замечают", "scores": {"looks": 2}},
            "2": {"text": "Обычная внешность", "scores": {"looks": 4}},
            "3": {"text": "Симпатичный(ая)", "scores": {"looks": 6}},
            "4": {"text": "Красивый(ая)", "scores": {"looks": 8}},
            "5": {"text": "Модельная внешность", "scores": {"looks": 10}}
        }
    },
    {  # 8. Здоровье
        "text": "Как часто ты болеешь?",
        "options": {
            "1": {"text": "Постоянно", "scores": {"health": 2}},
            "2": {"text": "Несколько раз в год", "scores": {"health": 4}},
            "3": {"text": "Раз в год", "scores": {"health": 6}},
            "4": {"text": "Раз в несколько лет", "scores": {"health": 8}},
            "5": {"text": "Практически никогда", "scores": {"health": 10}}
        }
    },
    {  # 9. Семейное положение
        "text": "Какое у тебя семейное положение?",
        "options": {
            "1": {"text": "Никогда не был(а) в браке", "scores": {"marriage": 0, "marriages": 0}},
            "2": {"text": "В браке / отношениях", "scores": {"marriage": 1, "marriages": 1}},
            "3": {"text": "Разведен(а) один раз", "scores": {"marriage": 0, "marriages": 1}},
            "4": {"text": "Разведен(а) дважды", "scores": {"marriage": 0, "marriages": 2}},
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
            "1": {"text": "Никого, я один(а)", "scores": {"friends": 1, "social": 1}},
            "2": {"text": "1-2 друга", "scores": {"friends": 3, "social": 3}},
            "3": {"text": "3-5 друзей", "scores": {"friends": 5, "social": 5}},
            "4": {"text": "5-10 человек", "scores": {"friends": 7, "social": 7}},
            "5": {"text": "Много друзей", "scores": {"friends": 9, "social": 9}}
        }
    }
]

# Мужские вопросы
MALE_QUESTIONS = [
    {  # 12. Автомобиль
        "text": "Какой у тебя автомобиль?",
        "options": {
            "1": {"text": "Нет машины", "scores": {"car": 0, "car_type": "NONE", "status": 1}},
            "2": {"text": "Отечественный/старый", "scores": {"car": 1, "car_type": "OLD", "status": 2}},
            "3": {"text": "Бюджетный иномарка", "scores": {"car": 2, "car_type": "BUDGET", "status": 3}},
            "4": {"text": "Бизнес-класс", "scores": {"car": 3, "car_type": "BUSINESS", "status": 5}},
            "5": {"text": "Премиум/спортивный", "scores": {"car": 4, "car_type": "PREMIUM", "status": 7}},
            "6": {"text": "Внедорожник/джип", "scores": {"car": 4, "car_type": "SUV", "status": 6, "compensation": 1}}
        }
    },
    {  # 13. Баня
        "text": "Как часто ты ходишь в баню?",
        "options": {
            "1": {"text": "Никогда", "scores": {"banya": 1, "body_confidence": 2}},
            "2": {"text": "Раз в год по приглашению", "scores": {"banya": 3, "body_confidence": 4}},
            "3": {"text": "Иногда с друзьями", "scores": {"banya": 5, "body_confidence": 6}},
            "4": {"text": "Регулярно, традиция", "scores": {"banya": 7, "body_confidence": 8}},
            "5": {"text": "У меня своя баня", "scores": {"banya": 9, "body_confidence": 7, "status": 5}}
        }
    },
    {  # 14. Измены
        "text": "Как ты относишься к верности?",
        "options": {
            "1": {"text": "Всегда верен", "scores": {"cheating": 1, "loyalty": 9, "sex_drive": 3}},
            "2": {"text": "Было однажды", "scores": {"cheating": 3, "loyalty": 5, "sex_drive": 5}},
            "3": {"text": "Бывало, не вижу проблемы", "scores": {"cheating": 5, "loyalty": 3, "sex_drive": 7}},
            "4": {"text": "Часто меняю женщин", "scores": {"cheating": 7, "loyalty": 1, "sex_drive": 9}},
            "5": {"text": "Не был в отношениях", "scores": {"cheating": 2, "loyalty": 5, "sex_drive": 4}}
        }
    },
    {  # 15. Растительность
        "text": "Как у тебя с растительностью на лице?",
        "options": {
            "1": {"text": "Растёт плохо", "scores": {"testosterone": 3, "masculinity": 3}},
            "2": {"text": "Нормально, бреюсь через день", "scores": {"testosterone": 5, "masculinity": 5}},
            "3": {"text": "Густая, бреюсь каждый день", "scores": {"testosterone": 7, "masculinity": 7}},
            "4": {"text": "Ношу бороду", "scores": {"testosterone": 8, "masculinity": 8}},
            "5": {"text": "Очень густая борода", "scores": {"testosterone": 9, "masculinity": 9}}
        }
    },
    {  # 16. Сила
        "text": "Сколько отжимаешься?",
        "options": {
            "1": {"text": "0-5 раз", "scores": {"strength": 2, "fitness": 2}},
            "2": {"text": "5-15 раз", "scores": {"strength": 4, "fitness": 4}},
            "3": {"text": "15-30 раз", "scores": {"strength": 6, "fitness": 6}},
            "4": {"text": "30-50 раз", "scores": {"strength": 8, "fitness": 8}},
            "5": {"text": "Больше 50", "scores": {"strength": 10, "fitness": 10}}
        }
    },
    {  # 17. Размер (деликатно)
        "text": "Как ты оцениваешь своё телосложение?",
        "options": {
            "1": {"text": "Худощавое", "scores": {"body_type": "THIN", "size_confidence": 3}},
            "2": {"text": "Среднее", "scores": {"body_type": "AVERAGE", "size_confidence": 5}},
            "3": {"text": "Атлетичное", "scores": {"body_type": "ATHLETIC", "size_confidence": 7}},
            "4": {"text": "Крупное, мощное", "scores": {"body_type": "BIG", "size_confidence": 8}},
            "5": {"text": "Полное", "scores": {"body_type": "FULL", "size_confidence": 4}}
        }
    },
    {  # 18. Фантазии
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

# Женские вопросы
FEMALE_QUESTIONS = [
    {  # 12. Размер груди
        "text": "Какой у тебя размер груди?",
        "options": {
            "1": {"text": "0-1 размер", "scores": {"breast": 3, "fem_capital": 4, "body_confidence": 4}},
            "2": {"text": "2 размер", "scores": {"breast": 5, "fem_capital": 6, "body_confidence": 6}},
            "3": {"text": "3 размер", "scores": {"breast": 7, "fem_capital": 8, "body_confidence": 8}},
            "4": {"text": "4 размер и больше", "scores": {"breast": 9, "fem_capital": 9, "body_confidence": 7}},
            "5": {"text": "Не хочу отвечать", "scores": {"breast": 5, "fem_capital": 5, "body_confidence": 5}}
        }
    },
    {  # 13. Месячные
        "text": "Во сколько лет начались месячные?",
        "options": {
            "1": {"text": "До 11 лет", "scores": {"hormones": 8, "maturity": 8}},
            "2": {"text": "11-12 лет", "scores": {"hormones": 7, "maturity": 7}},
            "3": {"text": "12-14 лет", "scores": {"hormones": 6, "maturity": 6}},
            "4": {"text": "14-16 лет", "scores": {"hormones": 4, "maturity": 4}},
            "5": {"text": "После 16", "scores": {"hormones": 3, "maturity": 3}}
        }
    },
    {  # 14. Выбор мужчин
        "text": "Какие мужчины тебе нравятся?",
        "options": {
            "1": {"text": "Сильные, доминантные", "scores": {"mate": "ALPHA", "strategy": "DEPENDENT", "kink": "SUBMISSIVE"}},
            "2": {"text": "Уверенные, надёжные", "scores": {"mate": "BETA", "strategy": "PARTNERSHIP", "kink": "VANILLA"}},
            "3": {"text": "Умные, интеллектуалы", "scores": {"mate": "GAMMA", "strategy": "INTELLECTUAL", "kink": "MENTAL"}},
            "4": {"text": "Богатые, статусные", "scores": {"mate": "DELTA", "strategy": "PROVIDER", "kink": "SUGAR"}},
            "5": {"text": "Красивые, харизматичные", "scores": {"mate": "OMEGA", "strategy": "STATUS", "kink": "EXHIBITION"}}
        }
    },
    {  # 15. Отношения
        "text": "Сколько у тебя было серьёзных отношений?",
        "options": {
            "1": {"text": "Ни одного", "scores": {"relationships": 0, "experience": 1}},
            "2": {"text": "Один", "scores": {"relationships": 1, "experience": 3}},
            "3": {"text": "2-3", "scores": {"relationships": 2, "experience": 5}},
            "4": {"text": "4-5", "scores": {"relationships": 3, "experience": 7}},
            "5": {"text": "Больше 5", "scores": {"relationships": 4, "experience": 9}}
        }
    },
    {  # 16. Интим-работа
        "text": "Приходилось ли зарабатывать внешностью?",
        "options": {
            "1": {"text": "Нет, никогда", "scores": {"sex_work": 0, "taboo": 1}},
            "2": {"text": "Были спонсоры/подарки", "scores": {"sex_work": 1, "taboo": 3}},
            "3": {"text": "Работала моделью/эскортом", "scores": {"sex_work": 2, "taboo": 5}},
            "4": {"text": "Был опыт в интимной сфере", "scores": {"sex_work": 3, "taboo": 7}},
            "5": {"text": "Не хочу отвечать", "scores": {"sex_work": 1, "taboo": 4}}
        }
    },
    {  # 17. Тело
        "text": "Что тебе нравится в своём теле?",
        "options": {
            "1": {"text": "Грудь", "scores": {"body_pride": "BREAST", "body_confidence": 6}},
            "2": {"text": "Попа", "scores": {"body_pride": "ASS", "body_confidence": 6}},
            "3": {"text": "Ноги", "scores": {"body_pride": "LEGS", "body_confidence": 6}},
            "4": {"text": "Глаза/лицо", "scores": {"body_pride": "FACE", "body_confidence": 6}},
            "5": {"text": "Ничего не нравится", "scores": {"body_pride": "NONE", "body_confidence": 2}}
        }
    },
    {  # 18. Фантазии
        "text": "Какие сны тебя будоражат?",
        "options": {
            "1": {"text": "О сильном мужчине", "scores": {"fantasy": "ALPHA", "kink": "SUBMISSIVE"}},
            "2": {"text": "О богатстве и роскоши", "scores": {"fantasy": "WEALTH", "kink": "SUGAR"}},
            "3": {"text": "О страсти и сексе", "scores": {"fantasy": "PASSION", "kink": "WILD"}},
            "4": {"text": "О признании и славе", "scores": {"fantasy": "FAME", "kink": "EXHIBITION"}},
            "5": {"text": "Не помню сны", "scores": {"fantasy": "NONE", "kink": "VANILLA"}}
        }
    }
]

# ==================== ФУНКЦИИ ГАДАНИЯ ====================

def get_narrative(data):
    """Определяем доминирующий нарратив"""
    scores = {"СБ": 0, "ТФ": 0, "УБ": 0, "ЧВ": 0}
    
    job = data.get('job', '')
    if job in ['MANAGER', 'BUSINESS']:
        scores["СБ"] += 2
    elif job in ['WORKER', 'OFFICE']:
        scores["ТФ"] += 2
    elif job in ['PROFESSIONAL']:
        scores["УБ"] += 2
    elif job in ['CREATIVE']:
        scores["ЧВ"] += 2
    
    if data.get('money', 0) > 5:
        scores["СБ"] += 1
    if data.get('housing', 0) > 5:
        scores["ТФ"] += 1
    if data.get('education', 0) > 7:
        scores["УБ"] += 2
    if data.get('looks', 0) > 7:
        scores["ЧВ"] += 2
    
    gender = data.get('gender', 'М')
    if gender == 'Ж':
        if data.get('breast', 0) > 6:
            scores["ЧВ"] += 1
        if data.get('mate', '') in ['ALPHA', 'DELTA']:
            scores["СБ"] += 1
    else:
        if data.get('testosterone', 0) > 7:
            scores["СБ"] += 1
        if data.get('car_type', '') in ['PREMIUM', 'SUV']:
            scores["ЧВ"] += 1
    
    max_score = max(scores.values())
    top_narratives = [n for n, s in scores.items() if s == max_score]
    
    main = top_narratives[0]
    second = top_narratives[1] if len(top_narratives) > 1 else None
    
    return main, second

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
    if data.get('friends', 0) > 7:
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
    """Получаем название роли"""
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
    await state.update_data(answers={})
    await ask_question(message.from_user.id, 0, state)

async def ask_question(user_id, index, state: FSMContext):
    """Задаёт вопрос по индексу"""
    data = await state.get_data()
    answers = data.get('answers', {})
    gender = answers.get('gender', 'М')
    
    if index < len(QUESTIONS):
        q = QUESTIONS[index]
    elif gender == 'М':
        if index - len(QUESTIONS) < len(MALE_QUESTIONS):
            q = MALE_QUESTIONS[index - len(QUESTIONS)]
        else:
            await show_fortune(user_id, state)
            return
    else:
        if index - len(QUESTIONS) < len(FEMALE_QUESTIONS):
            q = FEMALE_QUESTIONS[index - len(QUESTIONS)]
        else:
            await show_fortune(user_id, state)
            return
    
    builder = InlineKeyboardBuilder()
    for key, option in q["options"].items():
        builder.button(text=option["text"], callback_data=f"ans_{index}_{key}")
    builder.adjust(1)
    
    await bot.send_message(
        user_id,
        f"*Вопрос {index+1}*: {q['text']}",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(lambda c: c.data.startswith('ans_'))
async def process_answer(callback: types.CallbackQuery, state: FSMContext):
    """Обработка ответа"""
    await callback.answer()
    
    _, index_str, answer_key = callback.data.split('_')
    index = int(index_str)
    
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
    
    scores = q["options"][answer_key]["scores"]
    for key, value in scores.items():
        answers[key] = value
    
    await state.update_data(answers=answers)
    await ask_question(callback.from_user.id, index + 1, state)

async def show_fortune(user_id, state: FSMContext):
    """Показывает гадание"""
    data = await state.get_data()
    answers = data.get('answers', {})
    
    gender = answers.get('gender', 'М')
    age = answers.get('age', 30)
    
    narrative, second_narrative = get_narrative(answers)
    level = get_level(answers, narrative)
    role = get_role_name(narrative, level, gender)
    
    base_interpretation = get_interpretation(gender, narrative, level, second_narrative)
    
    # Добавляем возрастные прогнозы
    age_1 = age + 1
    age_5 = age + 5
    age_10 = age + 10
    
    fortune = f"🔮 *Твоя судьба* 🔮\n\n"
    fortune += f"Твой мир — *{NARRATIVE_NAMES[narrative]}*\n"
    fortune += f"Твоя роль — *{role}*\n\n"
    fortune += base_interpretation
    
    # Добавляем возрастные прогнозы
    fortune += f"\n\n*Твой возраст: {age} лет*\n\n"
    fortune += f"*Через год, в {age_1} лет:*\n"
    fortune += f"Ты будешь там же, где и сейчас, если не начнёшь что-то менять. Год пролетит незаметно, а оглянешься — и ничего не изменилось.\n\n"
    fortune += f"*Через 5 лет, в {age_5} лет:*\n"
    fortune += f"Это рубеж. Ты либо закрепишься в своей роли, либо начнёшь скатываться. Всё зависит от решений, которые примешь сейчас.\n\n"
    fortune += f"*Через 10 лет, в {age_10} лет:*\n"
    fortune += f"Ты оглянешься назад и поймёшь, что главные возможности были упущены. Или наоборот — что ты всё сделала правильно. Выбор за тобой.\n\n"
    
    fortune += f"— *Виртуальная гадалка*"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Погадать ещё", callback_data="restart")
    builder.adjust(1)
    
    await bot.send_message(user_id, fortune, reply_markup=builder.as_markup())
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
