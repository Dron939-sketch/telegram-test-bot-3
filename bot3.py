#!/usr/bin/env python3
"""
🧠 ПСИХОЛОГИЧЕСКИЙ ПРОФАЙЛЕР v6.0
Матрица 4×6: что реально работало в вашей жизни
Основано на оперантном обусловливании и теории подкрепления
"""

import os
import logging
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
from typing import Dict, List, Tuple, Optional

# Загружаем токен
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ Токен не найден! Проверьте файл .env")

# ==================== НАСТРОЙКА ЛОГИРОВАНИЯ ====================
logging.basicConfig(
    level=logging.INFO,
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

class ProfileState(StatesGroup):
    # Физические данные
    height = State()
    strength = State()
    looks = State()
    health = State()
    reaction = State()
    
    # Окружение в детстве
    area = State()
    family = State()
    peers = State()
    school = State()
    money = State()
    
    # Что работало (оперантное обусловливание)
    sb_q1 = State()  # СБ - давать сдачи
    sb_q2 = State()  # СБ - избегать
    sb_q3 = State()  # СБ - замирать
    sb_q4 = State()  # СБ - заискивать
    sb_q5 = State()  # СБ - подчиняться
    
    tf_q1 = State()  # ТФ - просить
    tf_q2 = State()  # ТФ - искать
    tf_q3 = State()  # ТФ - обменивать
    tf_q4 = State()  # ТФ - работать
    tf_q5 = State()  # ТФ - копить
    tf_q6 = State()  # ТФ - организовывать
    
    ub_q1 = State()  # УБ - игнорировать
    ub_q2 = State()  # УБ - мистика
    ub_q3 = State()  # УБ - заговор
    ub_q4 = State()  # УБ - догма
    ub_q5 = State()  # УБ - эмпирика
    ub_q6 = State()  # УБ - теория
    
    chv_q1 = State()  # ЧВ - прилипать
    chv_q2 = State()  # ЧВ - копировать
    chv_q3 = State()  # ЧВ - привлекать
    chv_q4 = State()  # ЧВ - использовать
    chv_q5 = State()  # ЧВ - сотрудничать
    chv_q6 = State()  # ЧВ - создавать связи
    
    last_message_id = State()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Прогресс-бар"""
    filled = int((current / total) * length)
    return "█" * filled + "░" * (length - filled)

# ==================== ВОПРОСЫ ====================

# БЛОК 1: ФИЗИЧЕСКИЕ ДАННЫЕ
PHYSICAL_QUESTIONS = [
    {
        "id": "height",
        "text": "Какой у вас рост?",
        "options": {
            "1": "📏 Ниже 160 см",
            "2": "📏 160-170 см",
            "3": "📏 170-180 см",
            "4": "📏 180-190 см",
            "5": "📏 Выше 190 см"
        }
    },
    {
        "id": "strength",
        "text": "Как вы оцениваете свою физическую силу?",
        "options": {
            "1": "🦴 Слабый(ая), меня легко обидеть",
            "2": "🦵 Средняя, как у большинства",
            "3": "💪 Сильнее среднего",
            "4": "🦍 Очень сильный(ая)",
            "5": "🏋️ Профессиональный спортсмен"
        }
    },
    {
        "id": "looks",
        "text": "Как вы оцениваете свою внешность?",
        "options": {
            "1": "👤 Меня не замечают",
            "2": "👤 Обычная внешность",
            "3": "✨ Симпатичный(ая)",
            "4": "🌟 Красивый(ая)",
            "5": "💫 Модельная внешность"
        }
    },
    {
        "id": "health",
        "text": "Как часто вы болеете?",
        "options": {
            "1": "🏥 Постоянно",
            "2": "🤧 Несколько раз в год",
            "3": "😷 Раз в год",
            "4": "💪 Раз в несколько лет",
            "5": "🦸 Практически никогда"
        }
    },
    {
        "id": "reaction",
        "text": "Как у вас со скоростью реакции?",
        "options": {
            "1": "🐢 Медленная, не успеваю",
            "2": "🚶 Средняя",
            "3": "🏃 Быстрее среднего",
            "4": "⚡ Очень быстрая",
            "5": "🎯 Профессиональная (спортсмен, водитель)"
        }
    }
]

# БЛОК 2: ОКРУЖЕНИЕ В ДЕТСТВЕ
ENVIRONMENT_QUESTIONS = [
    {
        "id": "area",
        "text": "Где вы росли?",
        "options": {
            "1": "🏚️ В опасном районе, где часто дрались",
            "2": "🏘️ В обычном спальном районе",
            "3": "🏡 В тихом, спокойном месте",
            "4": "🌳 В пригороде, на природе",
            "5": "🏙️ В центре большого города"
        }
    },
    {
        "id": "family",
        "text": "Какие были отношения в семье?",
        "options": {
            "1": "⚔️ Частые скандалы, драки",
            "2": "😐 Холодные, отстранённые",
            "3": "🤝 Обычные, как у всех",
            "4": "😊 Тёплые, поддерживающие",
            "5": "👑 Меня баловали, всё позволяли"
        }
    },
    {
        "id": "peers",
        "text": "Как к вам относились сверстники в школе?",
        "options": {
            "1": "👊 Часто обижали, били",
            "2": "😶 Не замечали, игнорировали",
            "3": "👥 Были друзья, но и враги тоже",
            "4": "🤝 Хорошо относились, уважали",
            "5": "👑 Я был(а) лидером, все слушались"
        }
    },
    {
        "id": "school",
        "text": "Как вы учились в школе?",
        "options": {
            "1": "📉 Плохо, меня считали глупым",
            "2": "📊 Средне, как все",
            "3": "📈 Хорошо, но без фанатизма",
            "4": "📚 Отлично, был(а) умницей",
            "5": "🏆 Круглый отличник, олимпиады"
        }
    },
    {
        "id": "money",
        "text": "Какое было материальное положение семьи?",
        "options": {
            "1": "🍞 Едва хватало на еду",
            "2": "💰 Жили скромно, но хватало",
            "3": "💳 Средний достаток",
            "4": "🏦 Обеспеченная семья",
            "5": "💎 Богатые, ни в чём не нуждались"
        }
    }
]

# БЛОК 3: ЧТО РАБОТАЛО (ОПЕРАНТНОЕ ОБУСЛОВЛИВАНИЕ)
REINFORCEMENT_QUESTIONS = [
    # ===== СБ (НАПАДАЙ) =====
    {
        "id": "sb_q1",
        "category": "СБ",
        "text": "В детстве, когда я давал сдачи обидчикам...",
        "options": {
            "1": "😨 Меня ещё сильнее били",
            "2": "😐 Ничего не менялось",
            "3": "😶 Меня наказывали взрослые",
            "4": "👍 Иногда помогало",
            "5": "✅ Часто помогало, меня начинали уважать",
            "6": "🏆 Всегда работало, я стал лидером"
        }
    },
    {
        "id": "sb_q2",
        "category": "СБ",
        "text": "Когда я пытался избежать конфликта, уйти...",
        "options": {
            "1": "😨 Меня догоняли и били ещё сильнее",
            "2": "😐 Ничего не менялось",
            "3": "😶 Называли трусом",
            "4": "👍 Иногда удавалось спастись",
            "5": "✅ Часто это спасало",
            "6": "🏆 Всегда так делал и был в безопасности"
        }
    },
    {
        "id": "sb_q3",
        "category": "СБ",
        "text": "Когда я замирал и делал вид, что меня нет...",
        "options": {
            "1": "😨 Всё равно замечали и били",
            "2": "😐 Ничего не менялось",
            "3": "😶 Надо мной смеялись",
            "4": "👍 Иногда проносило",
            "5": "✅ Часто меня не замечали",
            "6": "🏆 Всегда это спасало"
        }
    },
    {
        "id": "sb_q4",
        "category": "СБ",
        "text": "Когда я пытался подружиться с обидчиками, угождал им...",
        "options": {
            "1": "😨 Они издевались ещё больше",
            "2": "😐 Ничего не менялось",
            "3": "😶 Считали подлизой",
            "4": "👍 Иногда отставали",
            "5": "✅ Часто принимали в компанию",
            "6": "🏆 Всегда так делал и был в безопасности"
        }
    },
    {
        "id": "sb_q5",
        "category": "СБ",
        "text": "Когда я полностью подчинялся, делал что велят...",
        "options": {
            "1": "😨 Требовали всё больше",
            "2": "😐 Ничего не менялось",
            "3": "😶 Не уважали",
            "4": "👍 Иногда оставляли в покое",
            "5": "✅ Часто это работало",
            "6": "🏆 Всегда так выживал"
        }
    },
    
    # ===== ТФ (ЕШЬ) =====
    {
        "id": "tf_q1",
        "category": "ТФ",
        "text": "Когда я просил у родителей то, что хочу...",
        "options": {
            "1": "😨 Ругали и ничего не давали",
            "2": "😐 Игнорировали",
            "3": "😶 Говорили, что я нахал(ка)",
            "4": "👍 Иногда давали",
            "5": "✅ Часто давали",
            "6": "🏆 Всегда давали, что попрошу"
        }
    },
    {
        "id": "tf_q2",
        "category": "ТФ",
        "text": "Когда я сам искал, где найти или заработать...",
        "options": {
            "1": "😨 Ничего не находил, только проблемы",
            "2": "😐 Ничего не получалось",
            "3": "😶 Считали странным",
            "4": "👍 Иногда находил",
            "5": "✅ Часто получалось",
            "6": "🏆 Всегда находил способ"
        }
    },
    {
        "id": "tf_q3",
        "category": "ТФ",
        "text": "Когда я менялся с другими, обменивался...",
        "options": {
            "1": "😨 Меня обманывали",
            "2": "😐 Ничего не выходило",
            "3": "😶 Считали жадным",
            "4": "👍 Иногда получалось выгодно",
            "5": "✅ Часто получал то, что хочу",
            "6": "🏆 Всегда умел выменять"
        }
    },
    {
        "id": "tf_q4",
        "category": "ТФ",
        "text": "Когда я сам работал, что-то делал своими руками...",
        "options": {
            "1": "😨 Ругали, что плохо",
            "2": "😐 Никто не замечал",
            "3": "😶 Считали, что это странно",
            "4": "👍 Иногда хвалили",
            "5": "✅ Часто получалось хорошо",
            "6": "🏆 Гордились мной"
        }
    },
    {
        "id": "tf_q5",
        "category": "ТФ",
        "text": "Когда я копил, откладывал на что-то...",
        "options": {
            "1": "😨 Деньги отбирали или терял",
            "2": "😐 Ничего не получалось накопить",
            "3": "😶 Считали жадным",
            "4": "👍 Иногда получалось купить",
            "5": "✅ Часто достигал цели",
            "6": "🏆 Всегда мог накопить на что хочу"
        }
    },
    {
        "id": "tf_q6",
        "category": "ТФ",
        "text": "Когда я организовывал других, распределял задачи...",
        "options": {
            "1": "😨 Никто не слушался, смеялись",
            "2": "😐 Ничего не получалось",
            "3": "😶 Считали выскочкой",
            "4": "👍 Иногда слушались",
            "5": "✅ Часто получалось организовать",
            "6": "🏆 Меня слушались всегда"
        }
    },
    
    # ===== УБ (ДУМАЙ) =====
    {
        "id": "ub_q1",
        "category": "УБ",
        "text": "Когда я сталкивался с чем-то непонятным и игнорировал это...",
        "options": {
            "1": "😨 Проблемы только росли",
            "2": "😐 Ничего не менялось",
            "3": "😶 Считали глупым",
            "4": "👍 Иногда само рассасывалось",
            "5": "✅ Часто проходило мимо",
            "6": "🏆 Всегда так и жил — без проблем"
        }
    },
    {
        "id": "ub_q2",
        "category": "УБ",
        "text": "Когда я объяснял непонятное приметами, знаками, магией...",
        "options": {
            "1": "😨 Надо мной смеялись",
            "2": "😐 Никто не верил",
            "3": "😶 Считали странным",
            "4": "👍 Иногда совпадало",
            "5": "✅ Часто сбывалось",
            "6": "🏆 Я всегда знал, что это знаки"
        }
    },
    {
        "id": "ub_q3",
        "category": "УБ",
        "text": "Когда я искал скрытый смысл, заговор, тайный умысел...",
        "options": {
            "1": "😨 Меня считали параноиком",
            "2": "😐 Никто не слушал",
            "3": "😶 Отмахивались",
            "4": "👍 Иногда оказывался прав",
            "5": "✅ Часто мои догадки подтверждались",
            "6": "🏆 Я всегда вижу то, что скрыто"
        }
    },
    {
        "id": "ub_q4",
        "category": "УБ",
        "text": "Когда я верил авторитетам, учителям, старшим...",
        "options": {
            "1": "😨 Они меня обманывали",
            "2": "😐 Ничего не давало",
            "3": "😶 Считали наивным",
            "4": "👍 Иногда помогали",
            "5": "✅ Часто их советы работали",
            "6": "🏆 Всегда следовал советам и это спасало"
        }
    },
    {
        "id": "ub_q5",
        "category": "УБ",
        "text": "Когда я проверял всё сам, экспериментировал...",
        "options": {
            "1": "😨 Попадал в неприятности",
            "2": "😐 Ничего не выходило",
            "3": "😶 Считали занудой",
            "4": "👍 Иногда находил ответ",
            "5": "✅ Часто понимал, как всё устроено",
            "6": "🏆 Всегда доходил до истины"
        }
    },
    {
        "id": "ub_q6",
        "category": "УБ",
        "text": "Когда я искал закономерности, строил системы...",
        "options": {
            "1": "😨 Ничего не понимал",
            "2": "😐 Путался ещё больше",
            "3": "😶 Считали заумным",
            "4": "👍 Иногда находил логику",
            "5": "✅ Часто видел систему там, где другие — хаос",
            "6": "🏆 Я всегда вижу, как всё устроено на самом деле"
        }
    },
    
    # ===== ЧВ (СПАРИВАЙСЯ) =====
    {
        "id": "chv_q1",
        "category": "ЧВ",
        "text": "Когда я сильно привязывался к кому-то, не отпускал...",
        "options": {
            "1": "😨 Меня отвергали",
            "2": "😐 Ничего не получалось",
            "3": "😶 Считали навязчивым",
            "4": "👍 Иногда оставались со мной",
            "5": "✅ Часто удавалось удержать",
            "6": "🏆 Всегда так и жил — с кем-то рядом"
        }
    },
    {
        "id": "chv_q2",
        "category": "ЧВ",
        "text": "Когда я копировал других, делал как они...",
        "options": {
            "1": "😨 Надо мной смеялись",
            "2": "😐 Никто не замечал",
            "3": "😶 Считали обезьянкой",
            "4": "👍 Иногда принимали",
            "5": "✅ Часто становился своим",
            "6": "🏆 Всегда мог быть как все"
        }
    },
    {
        "id": "chv_q3",
        "category": "ЧВ",
        "text": "Когда я привлекал внимание, показывал себя...",
        "options": {
            "1": "😨 Меня игнорировали",
            "2": "😐 Ничего не менялось",
            "3": "😶 Считали выскочкой",
            "4": "👍 Иногда замечали",
            "5": "✅ Часто нравился людям",
            "6": "🏆 Всегда был в центре внимания"
        }
    },
    {
        "id": "chv_q4",
        "category": "ЧВ",
        "text": "Когда я использовал других для своих целей...",
        "options": {
            "1": "😨 Меня раскусили и наказали",
            "2": "😐 Ничего не выходило",
            "3": "😶 Считали манипулятором",
            "4": "👍 Иногда получалось",
            "5": "✅ Часто добивался своего",
            "6": "🏆 Всегда умел использовать людей"
        }
    },
    {
        "id": "chv_q5",
        "category": "ЧВ",
        "text": "Когда я сотрудничал, договаривался на равных...",
        "options": {
            "1": "😨 Меня обманывали",
            "2": "😐 Ничего не выходило",
            "3": "😶 Считали слабым",
            "4": "👍 Иногда получалось договориться",
            "5": "✅ Часто находил общий язык",
            "6": "🏆 Всегда умел договариваться"
        }
    },
    {
        "id": "chv_q6",
        "category": "ЧВ",
        "text": "Когда я создавал связи, знакомил людей...",
        "options": {
            "1": "😨 Все ссорились",
            "2": "😐 Никто не сближался",
            "3": "😶 Считали странным",
            "4": "👍 Иногда получалось объединить",
            "5": "✅ Часто люди через меня знакомились",
            "6": "🏆 Я всегда в центре сети контактов"
        }
    }
]

# ==================== ФУНКЦИИ РАСЧЁТА ====================

def calculate_profile(data: Dict) -> Dict:
    """Рассчитывает профиль на основе ответов"""
    
    # Считаем средние по каждому поведению
    categories = {
        "СБ": ["sb_q1", "sb_q2", "sb_q3", "sb_q4", "sb_q5"],
        "ТФ": ["tf_q1", "tf_q2", "tf_q3", "tf_q4", "tf_q5", "tf_q6"],
        "УБ": ["ub_q1", "ub_q2", "ub_q3", "ub_q4", "ub_q5", "ub_q6"],
        "ЧВ": ["chv_q1", "chv_q2", "chv_q3", "chv_q4", "chv_q5", "chv_q6"]
    }
    
    scores = {}
    for cat, questions in categories.items():
        values = []
        for q in questions:
            val = data.get(q)
            if val is None:
                logger.warning(f"⚠️ Отсутствует ответ на вопрос {q}, использую 3")
                values.append(3)
            else:
                try:
                    values.append(int(val))
                except ValueError:
                    logger.warning(f"⚠️ Неверное значение {val} для {q}, использую 3")
                    values.append(3)
        
        scores[cat] = round(sum(values) / len(values), 1)
    
    # Сортируем по убыванию
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    # Определяем доминанту и второстепенные
    dominant = sorted_scores[0][0]
    secondary = sorted_scores[1][0]
    tertiary = sorted_scores[2][0]
    quaternary = sorted_scores[3][0]
    
    # Собираем физические данные
    physical = {
        "height": int(data.get("height", 3)),
        "strength": int(data.get("strength", 3)),
        "looks": int(data.get("looks", 3)),
        "health": int(data.get("health", 3)),
        "reaction": int(data.get("reaction", 3))
    }
    
    # Собираем окружение
    environment = {
        "area": int(data.get("area", 3)),
        "family": int(data.get("family", 3)),
        "peers": int(data.get("peers", 3)),
        "school": int(data.get("school", 3)),
        "money": int(data.get("money", 3))
    }
    
    return {
        "scores": scores,
        "dominant": dominant,
        "secondary": secondary,
        "tertiary": tertiary,
        "quaternary": quaternary,
        "physical": physical,
        "environment": environment
    }

# ==================== ОПИСАНИЯ ПРОФИЛЕЙ ====================

def get_profile_description(profile: Dict) -> str:
    """Возвращает текстовое описание профиля"""
    
    dominant = profile["dominant"]
    secondary = profile["secondary"]
    scores = profile["scores"]
    physical = profile["physical"]
    env = profile["environment"]
    
    # Базовая характеристика по доминанте
    descriptions = {
        "СБ": (
            "⚔️ <b>Силовой тип</b>\n"
            "В вашей жизни работала сила и агрессия. Когда вы давали сдачи, защищались, "
            "нападали — это приносило результат. Мир воспринимается как арена, "
            "где нужно отстаивать своё место."
        ),
        "ТФ": (
            "🔧 <b>Трудовой тип</b>\n"
            "В вашей жизни работал труд, накопление, обмен. Когда вы работали, копили, "
            "организовывали — это приносило результат. Мир воспринимается как источник "
            "ресурсов, которые можно добыть и сохранить."
        ),
        "УБ": (
            "📚 <b>Мыслительный тип</b>\n"
            "В вашей жизни работало понимание, анализ, познание. Когда вы разбирались, "
            "искали закономерности, строили теории — это приносило результат. "
            "Мир воспринимается как загадка, которую нужно разгадать."
        ),
        "ЧВ": (
            "🤝 <b>Социальный тип</b>\n"
            "В вашей жизни работали связи, общение, отношения. Когда вы общались, "
            "привлекали внимание, создавали связи — это приносило результат. "
            "Мир воспринимается как сеть людей, где главное — быть своим."
        )
    }
    
    # Вторичная характеристика
    secondary_desc = {
        "СБ": "⚔️ Вы также умеете применять силу, когда нужно.",
        "ТФ": "🔧 Вы также умеете работать и добывать ресурсы.",
        "УБ": "📚 Вы также умеете анализировать и понимать.",
        "ЧВ": "🤝 Вы также умеете общаться и строить связи."
    }
    
    # Характеристика по физическим данным
    physical_desc = []
    if physical["strength"] >= 4:
        physical_desc.append("• Физически сильный — это ваше преимущество")
    if physical["looks"] >= 4:
        physical_desc.append("• Привлекательная внешность — вам легче в социальных контактах")
    if physical["health"] <= 2:
        physical_desc.append("• Слабое здоровье — приходится экономить силы")
    if physical["reaction"] >= 4:
        physical_desc.append("• Быстрая реакция — успеваете в опасных ситуациях")
    
    # Характеристика по окружению
    env_desc = []
    if env["area"] <= 2:
        env_desc.append("• Росли в опасной среде — это закалило")
    if env["family"] >= 4:
        env_desc.append("• Поддерживающая семья — дала уверенность")
    if env["peers"] <= 2:
        env_desc.append("• В школе не принимали — пришлось искать свои пути")
    if env["peers"] >= 4:
        env_desc.append("• В школе уважали — социальные навыки развиты")
    if env["school"] >= 4:
        env_desc.append("• Хорошо учились — интеллектуальные способности выше среднего")
    if env["money"] <= 2:
        env_desc.append("• Росли в бедности — научились ценить ресурсы")
    
    # Собираем описание
    text = f"""
🧠 <b>ВАШ ПРОФИЛЬ</b>

{descriptions[dominant]}

📊 <b>Ваши стратегии (что работало):</b>
• ⚔️ СБ (сила): {scores['СБ']}/6
• 🔧 ТФ (труд): {scores['ТФ']}/6
• 📚 УБ (мышление): {scores['УБ']}/6
• 🤝 ЧВ (общение): {scores['ЧВ']}/6

<b>Доминирует:</b> {dominant}
<b>Вторичная стратегия:</b> {secondary} {secondary_desc[secondary]}

<b>Что дано от природы:</b>
"""

    # Добавляем физические характеристики безопасно
    height_desc = ["низкий", "ниже среднего", "средний", "выше среднего", "высокий"]
    strength_desc = ["слабый", "ниже среднего", "средняя", "выше среднего", "очень сильный"]
    looks_desc = ["незаметная", "обычная", "симпатичная", "красивая", "модельная"]

    text += f"<i>Рост:</i> {height_desc[physical['height']-1]}\n"
    text += f"<i>Сила:</i> {strength_desc[physical['strength']-1]}\n"
    text += f"<i>Внешность:</i> {looks_desc[physical['looks']-1]}\n"

    if physical_desc:
        text += "\n<b>Заметки по физическим данным:</b>\n" + "\n".join(physical_desc) + "\n"

    if env_desc:
        text += "\n<b>Как повлияло окружение:</b>\n" + "\n".join(env_desc) + "\n"

    # Рекомендации отдельно (не в f-строке из-за эмодзи)
    text += "\n💡 <b>Рекомендации:</b>\n"
    text += f"• Развивайте {secondary} — это ваша вторая по эффективности стратегия\n"
    text += f"• {get_recommendation(dominant, scores, secondary)}\n"
    text += "• Учитывайте свои физические данные — они дают преимущества и ограничения\n"
    text += "• Окружение можно менять — то, что работало в детстве, может не работать сейчас\n"
    
    return text

def get_recommendation(dominant: str, scores: Dict, secondary: str = None) -> str:
    """Возвращает рекомендацию по развитию"""
    
    if dominant == "СБ":
        if scores["СБ"] > 5:
            base = "Ваша сила — в силе. Но помните, что не все проблемы решаются напором."
        else:
            base = "Учитесь отстаивать свои границы, но без лишней агрессии."
    
    elif dominant == "ТФ":
        if scores["ТФ"] > 5:
            base = "Вы умеете добывать ресурсы. Не забывайте, что отдых тоже важен."
        else:
            base = "Развивайте навыки планирования и накопления."
    
    elif dominant == "УБ":
        if scores["УБ"] > 5:
            base = "Ваш ум — главный инструмент. Не забывайте про практику."
        else:
            base = "Учитесь анализировать ситуации, ищите закономерности."
    
    else:  # ЧВ
        if scores["ЧВ"] > 5:
            base = "Вы прекрасно строите связи. Не забывайте про искренность."
        else:
            base = "Развивайте коммуникативные навыки, учитесь знакомиться."
    
    # Добавляем рекомендацию по вторичной стратегии, если она передана
    if secondary:
        secondary_rec = {
            "СБ": " Развивайте умение отстаивать границы, но без агрессии.",
            "ТФ": " Учитесь планировать и накапливать ресурсы.",
            "УБ": " Анализируйте ситуации, ищите закономерности.",
            "ЧВ": " Учитесь знакомиться и строить искренние отношения."
        }
        base += secondary_rec.get(secondary, "")
    
    return base

# ==================== ХЕНДЛЕРЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Начало тестирования"""
    
    await state.clear()
    
    intro = (
        f"🧠 <b>Психологический профайлер v6.0</b>\n\n"
        f"Здравствуйте, {message.from_user.first_name or 'пользователь'}!\n\n"
        f"Этот тест определит, какие стратегии поведения <b>реально работали</b> в вашей жизни.\n\n"
        f"• 5 вопросов о физических данных\n"
        f"• 5 вопросов об окружении в детстве\n"
        f"• 23 вопроса о том, что приносило результат\n\n"
        f"<i>Всего 33 вопроса. Отвечайте честно — это только для вас.</i>\n\n"
        f"<b>Начинаем?</b>"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Начать тест", callback_data="start_test")
    builder.adjust(1)
    
    await message.answer(intro, reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data.startswith('ans_'))
async def process_answer(callback: types.CallbackQuery, state: FSMContext):
    """Обработка ответа"""
    await callback.answer()
    
    # Парсим callback data
    # Формат: ans_sb_q1_1  или ans_height_3
    parts = callback.data.split('_')
    
    if len(parts) < 3:
        logger.error(f"❌ Неверный формат callback: {callback.data}")
        await callback.message.answer("❌ Ошибка. Начните заново: /start")
        return
    
    # Собираем ID вопроса (может быть составным: "sb_q1" или простым: "height")
    if len(parts) == 3:
        # Простой формат: ans_height_3
        q_id = parts[1]  # "height"
        value = parts[2]  # "3"
    elif len(parts) == 4:
        # Сложный формат: ans_sb_q1_1
        q_id = f"{parts[1]}_{parts[2]}"  # "sb_q1"
        value = parts[3]  # "1"
    else:
        logger.error(f"❌ Неверный формат callback: {callback.data}")
        await callback.message.answer("❌ Ошибка. Начните заново: /start")
        return
    
    logger.info(f"📝 Получен ответ: {q_id} = {value}")
    
    # Сохраняем ответ
    data = await state.get_data()
    data[q_id] = value
    await state.update_data(data)
    
    # Удаляем сообщение с вопросом (игнорируем ошибку, если сообщение уже удалено)
    try:
        await bot.delete_message(callback.from_user.id, callback.message.message_id)
    except Exception as e:
        logger.debug(f"Не удалось удалить сообщение: {e}")
    
    # Определяем следующий вопрос
    all_questions = PHYSICAL_QUESTIONS + ENVIRONMENT_QUESTIONS + REINFORCEMENT_QUESTIONS
    
    # Находим индекс текущего вопроса
    current_index = -1
    for i, q in enumerate(all_questions):
        if q["id"] == q_id:
            current_index = i
            break
    
    if current_index == -1:
        logger.error(f"❌ Вопрос {q_id} не найден")
        await callback.message.answer("❌ Ошибка. Начните заново: /start")
        return
    
    # Если есть следующий вопрос
    if current_index + 1 < len(all_questions):
        next_q = all_questions[current_index + 1]
        
        # Устанавливаем соответствующее состояние
        state_map = {
            "height": ProfileState.height,
            "strength": ProfileState.strength,
            "looks": ProfileState.looks,
            "health": ProfileState.health,
            "reaction": ProfileState.reaction,
            "area": ProfileState.area,
            "family": ProfileState.family,
            "peers": ProfileState.peers,
            "school": ProfileState.school,
            "money": ProfileState.money,
            "sb_q1": ProfileState.sb_q1,
            "sb_q2": ProfileState.sb_q2,
            "sb_q3": ProfileState.sb_q3,
            "sb_q4": ProfileState.sb_q4,
            "sb_q5": ProfileState.sb_q5,
            "tf_q1": ProfileState.tf_q1,
            "tf_q2": ProfileState.tf_q2,
            "tf_q3": ProfileState.tf_q3,
            "tf_q4": ProfileState.tf_q4,
            "tf_q5": ProfileState.tf_q5,
            "tf_q6": ProfileState.tf_q6,
            "ub_q1": ProfileState.ub_q1,
            "ub_q2": ProfileState.ub_q2,
            "ub_q3": ProfileState.ub_q3,
            "ub_q4": ProfileState.ub_q4,
            "ub_q5": ProfileState.ub_q5,
            "ub_q6": ProfileState.ub_q6,
            "chv_q1": ProfileState.chv_q1,
            "chv_q2": ProfileState.chv_q2,
            "chv_q3": ProfileState.chv_q3,
            "chv_q4": ProfileState.chv_q4,
            "chv_q5": ProfileState.chv_q5,
            "chv_q6": ProfileState.chv_q6,
        }
        
        if next_q["id"] in state_map:
            await state.set_state(state_map[next_q["id"]])
        else:
            logger.error(f"❌ Нет состояния для вопроса {next_q['id']}")
            await callback.message.answer("❌ Ошибка. Начните заново: /start")
            return
        
        await ask_question(callback.from_user.id, state, next_q)
        
    else:
        # Тест завершён
        await show_result(callback.from_user.id, state)

async def show_result(user_id: int, state: FSMContext):
    """Показывает результат"""
    
    data = await state.get_data()
    
    # Удаляем последнее сообщение
    last_id = data.get('last_message_id')
    if last_id:
        try:
            await bot.delete_message(user_id, last_id)
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение: {e}")
    
    # Рассчитываем профиль
    profile = calculate_profile(data)
    
    # Получаем описание
    description = get_profile_description(profile)
    
    # Отправляем результат
    await bot.send_chat_action(user_id, action="typing")
    await asyncio.sleep(1)
    
    await bot.send_message(user_id, description)
    
    # Кнопка для повторного прохождения
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Пройти заново", callback_data="restart")
    builder.adjust(1)
    
    await bot.send_message(
        user_id,
        f"📋 <b>Что дальше?</b>\n\n"
        f"Хотите пройти тест ещё раз?",
        reply_markup=builder.as_markup()
    )
    
    await state.clear()

@dp.callback_query(lambda c: c.data == "restart")
async def restart(callback: types.CallbackQuery, state: FSMContext):
    """Перезапуск теста"""
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
        f"<b>О тесте:</b>\n"
        f"33 вопроса о том, что реально работало в вашей жизни.\n"
        f"Основано на теории оперантного обусловливания.\n\n"
        f"<i>Все ответы анонимны и используются только для расчёта профиля.</i>"
    )
    
    await message.answer(help_text)

# ==================== ЗАПУСК ====================

async def main():
    """Запуск бота"""
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Вебхук сброшен")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось сбросить вебхук: {e}")
    
    print("\n" + "="*60)
    print("🧠 ПСИХОЛОГИЧЕСКИЙ ПРОФАЙЛЕР v6.0")
    print("="*60)
    print("🚀 Бот запущен")
    print("📊 Матрица 4×6: 1296 базовых профилей")
    print("📊 С учётом данных: 32 400 уникальных профилей")
    print("="*60 + "\n")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
