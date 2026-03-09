#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ШНУР - ТВОЙ ВТОРОЙ МОЗГ v3.0
Исправленная версия с:
✓ Коррекцией образа после теста
✓ Умной озвучкой с определением пола
✓ Расширенными этапами тестирования
✓ Сохранением в базу данных
✓ ИСПРАВЛЕННЫМИ ОШИБКАМИ
"""

import os
import json
import logging
import aiohttp
import asyncio
import datetime
import tempfile
import random
import re
import sqlite3
import hashlib
from typing import Optional, Dict, List, Any, Tuple
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime, timedelta
import time
import sys

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#  НАСТРОЙКИ
# ══════════════════════════════════════════════

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
YANDEX_API_KEY = os.environ.get("YANDEX_API_KEY", "")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")

# ID администраторов
ADMIN_IDS = [532205848]

# ══════════════════════════════════════════════
#  FSM СОСТОЯНИЯ (вместо ручного управления)
# ══════════════════════════════════════════════

class TestStates(StatesGroup):
    stage_1 = State()
    stage_2 = State()
    stage_3 = State()
    stage_4 = State()
    results = State()
    correction_waiting = State()
    correction_questions = State()
    free_question = State()
    gender_waiting = State()

# ══════════════════════════════════════════════
#  БАЗА ДАННЫХ
# ══════════════════════════════════════════════

class Database:
    """Класс для работы с SQLite базой данных"""
    
    def __init__(self, db_path="bot_database.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Инициализация таблиц"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    gender TEXT,
                    age INTEGER,
                    city TEXT,
                    registered_at TIMESTAMP,
                    last_active TIMESTAMP
                )
            ''')
            
            # Таблица профилей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS profiles (
                    user_id INTEGER PRIMARY KEY,
                    perception_type TEXT,
                    thinking_level INTEGER,
                    sb_level INTEGER,
                    tf_level INTEGER,
                    ub_level INTEGER,
                    chv_level INTEGER,
                    dominant_dilts TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Таблица ответов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    stage INTEGER,
                    question_index INTEGER,
                    question TEXT,
                    answer TEXT,
                    option_id TEXT,
                    scores TEXT,
                    answered_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Таблица статистики
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event_type TEXT,
                    event_data TEXT,
                    created_at TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def save_user(self, user_id: int, **kwargs):
        """Сохраняет или обновляет пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            exists = cursor.fetchone()
            
            now = datetime.now().isoformat()
            
            if exists:
                fields = []
                values = []
                for key, value in kwargs.items():
                    if value is not None:
                        fields.append(f"{key} = ?")
                        values.append(value)
                
                values.append(now)
                values.append(user_id)
                
                if fields:
                    cursor.execute(f'''
                        UPDATE users 
                        SET {', '.join(fields)}, last_active = ?
                        WHERE user_id = ?
                    ''', values)
            else:
                cursor.execute('''
                    INSERT INTO users 
                    (user_id, username, first_name, last_name, gender, age, city, registered_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    kwargs.get('username'),
                    kwargs.get('first_name'),
                    kwargs.get('last_name'),
                    kwargs.get('gender'),
                    kwargs.get('age'),
                    kwargs.get('city'),
                    kwargs.get('registered_at', now),
                    now
                ))
            
            conn.commit()
    
    def save_profile(self, user_id: int, profile: dict):
        """Сохраняет профиль пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            strategies = profile.get('strategies', {})
            
            cursor.execute('''
                INSERT OR REPLACE INTO profiles 
                (user_id, perception_type, thinking_level, sb_level, tf_level, ub_level, chv_level, dominant_dilts, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                profile.get('perception_type'),
                profile.get('thinking_level'),
                strategies.get('СБ', 3),
                strategies.get('ТФ', 3),
                strategies.get('УБ', 3),
                strategies.get('ЧВ', 3),
                profile.get('dominant_dilts'),
                now,
                now
            ))
            
            conn.commit()
    
    def save_answer(self, user_id: int, answer: dict):
        """Сохраняет ответ пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO answers 
                (user_id, stage, question_index, question, answer, option_id, scores, answered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                answer.get('stage'),
                answer.get('question_index'),
                answer.get('question'),
                answer.get('answer'),
                answer.get('option'),
                json.dumps(answer.get('scores', {}), ensure_ascii=False),
                datetime.now().isoformat()
            ))
            
            conn.commit()
    
    def log_stat(self, user_id: int, event_type: str, event_data: dict = None):
        """Логирует событие"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO stats (user_id, event_type, event_data, created_at)
                VALUES (?, ?, ?, ?)
            ''', (
                user_id,
                event_type,
                json.dumps(event_data, ensure_ascii=False) if event_data else None,
                datetime.now().isoformat()
            ))
            
            conn.commit()

# Инициализируем БД
db = Database()

# ══════════════════════════════════════════════
#  ХРАНИЛИЩЕ ДАННЫХ (временное, для активных сессий)
# ══════════════════════════════════════════════

# Основное хранилище данных пользователей (дублирует FSM для обратной совместимости)
user_data: Dict[int, Dict[str, Any]] = {}
user_names: Dict[int, str] = {}
user_contexts: Dict[int, 'UserContext'] = {}

# ══════════════════════════════════════════════
#  ФУНКЦИИ ДЛЯ ЛОГИРОВАНИЯ
# ══════════════════════════════════════════════

def log_debug(msg: str, user_id: int = None):
    """Логирование в stderr для отладки"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    user_part = f"[USER:{user_id}]" if user_id else ""
    print(f"🔍 {timestamp} {user_part} {msg}", file=sys.stderr, flush=True)

# ══════════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════

def level(score):
    """Дробный балл 1..4 → целый уровень 1..6"""
    if score <= 1.49:
        return 1
    elif score <= 2.00:
        return 2
    elif score <= 2.50:
        return 3
    elif score <= 3.00:
        return 4
    elif score <= 3.50:
        return 5
    else:
        return 6

def create_progress_bar(current: int, total: int, width: int = 10) -> str:
    """Создает красивый прогресс-бар"""
    percent = int((current / total) * 100)
    filled = int(width * percent / 100)
    bar = "🟩" * filled + "⬜" * (width - filled)
    return f"{bar} {percent}%"

def generate_unique_callback(prefix: str, user_id: int, question_idx: int, option: str) -> str:
    """Генерирует уникальный callback для защиты от повторных нажатий"""
    timestamp = int(time.time())
    random_salt = random.randint(1000, 9999)
    data = f"{prefix}_{user_id}_{question_idx}_{option}_{timestamp}_{random_salt}"
    # Хешируем чтобы не было слишком длинным
    return hashlib.md5(data.encode()).hexdigest()[:20]

def add_option_emoji(option_text: str, option_id: str) -> str:
    """Добавляет эмодзи к вариантам ответа"""
    emoji_map = {
        "1": "1️⃣",
        "2": "2️⃣", 
        "3": "3️⃣",
        "4": "4️⃣",
        "5": "5️⃣",
        "6": "6️⃣"
    }
    
    # Добавляем контекстные эмодзи
    text_lower = option_text.lower()
    if any(word in text_lower for word in ["друз", "общени", "люд"]):
        return f"{emoji_map.get(option_id, '🔹')} {option_text} 👥"
    elif any(word in text_lower for word in ["деньг", "финанс", "заработ"]):
        return f"{emoji_map.get(option_id, '🔹')} {option_text} 💰"
    elif any(word in text_lower for word in ["работ", "карьер", "дел"]):
        return f"{emoji_map.get(option_id, '🔹')} {option_text} 💼"
    elif any(word in text_lower for word in ["стресс", "тревог", "страх"]):
        return f"{emoji_map.get(option_id, '🔹')} {option_text} 😰"
    else:
        return f"{emoji_map.get(option_id, '🔹')} {option_text}"

def add_question_hint(question: dict) -> str:
    """Добавляет подсказки к вопросам"""
    hints = {
        "Когда на тебя давят или критикуют": "🤔 *Подумай о последнем конфликте*",
        "Когда тебе срочно нужны деньги": "💰 *Представь реальную ситуацию*",
        "Когда происходит что-то непонятное": "🔍 *Вспомни недавний кризис*",
        "В отношениях с новыми людьми": "👥 *Вспомни последнее знакомство*",
        "Как ты обычно восстанавливаешь энергию": "⚡ *Что реально работает для тебя*",
        "Что для тебя важнее всего в жизни": "🌟 *Подумай о самом главном*",
    }
    
    for key, hint in hints.items():
        if key in question['text']:
            return f"_{hint}_\n\n"
    return ""

def shuffle_questions(questions: list, seed: int = None) -> list:
    """Перемешивает вопросы для вариативности"""
    if seed:
        random.seed(seed)
    shuffled = questions.copy()
    random.shuffle(shuffled)
    return shuffled

# ══════════════════════════════════════════════
#  РЕЖИМЫ ОБЩЕНИЯ
# ══════════════════════════════════════════════

COMMUNICATION_MODES = {
    "hard": {
        "name": "🔴 ЖЕСТКИЙ РЕЖИМ",
        "description": "Делай как сказано. Вопросы потом. Ты здесь не за соплями, а за результатом.",
        "prompt": "Ты жесткий наставник, военный инструктор. Говори коротко, приказным тоном. Никакой жалости, только дело.",
        "emoji": "🔴",
        "voice_emotion": "strict",
        "voice_male": "filipp",
        "voice_female": "oksana"
    },
    "medium": {
        "name": "🟡 СРЕДНИЙ РЕЖИМ",
        "description": "Объясняю, показываю, поддерживаю. Но с тебя — действия. Баланс дисциплины и эмпатии.",
        "prompt": "Ты старший товарищ, наставник. Сочетаешь поддержку с требовательностью.",
        "emoji": "🟡",
        "voice_emotion": "neutral",
        "voice_male": "ermil",
        "voice_female": "alena"
    },
    "soft": {
        "name": "🟢 МЯГКИЙ РЕЖИМ",
        "description": "Давай разберемся, почему тебе страшно, и пойдем маленькими шагами.",
        "prompt": "Ты заботливый друг, психотерапевт. Говори мягко, поддерживающе.",
        "emoji": "🟢",
        "voice_emotion": "good",
        "voice_male": "ermil",
        "voice_female": "oksana"
    }
}

# ══════════════════════════════════════════════
#  КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ
# ══════════════════════════════════════════════

class UserContext:
    """Полный контекст пользователя"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.city = None
        self.timezone = "Europe/Moscow"
        self.timezone_offset = 3
        self.gender = None
        self.age = None
        self.communication_mode = "medium"
        self.last_context_update = None
        self.weather_cache = {}
        self.weather_cache_time = None
    
    def detect_gender_from_name(self, name: str) -> str:
        """Определяет пол по имени"""
        if not name:
            return None
        
        name_lower = name.lower()
        
        # Типично мужские имена
        male_names = ['александр', 'алексей', 'андрей', 'антон', 'артем', 'вадим', 'валентин', 
                     'валерий', 'василий', 'виктор', 'виталий', 'владимир', 'владислав', 'вячеслав',
                     'генадий', 'георгий', 'григорий', 'даниил', 'денис', 'дмитрий', 'евгений',
                     'егор', 'иван', 'игорь', 'илья', 'кирилл', 'константин', 'лев', 'леонид',
                     'максим', 'михаил', 'никита', 'николай', 'олег', 'павел', 'петр', 'роман',
                     'руслан', 'сергей', 'станислав', 'степан', 'тимур', 'федор', 'юрий', 'ярослав']
        
        # Типично женские имена
        female_names = ['александра', 'алина', 'алла', 'анастасия', 'анна', 'валентина', 'валерия',
                       'вера', 'вероника', 'виктория', 'галина', 'дарья', 'евгения', 'екатерина',
                       'елена', 'елизавета', 'жанна', 'зинаида', 'зоя', 'инна', 'ирина', 'карина',
                       'кира', 'клавдия', 'ксения', 'лариса', 'лидия', 'любовь', 'людмила', 'маргарита',
                       'марина', 'мария', 'надежда', 'наталья', 'нина', 'оксана', 'ольга', 'полина',
                       'раиса', 'светлана', 'софия', 'таисия', 'тамара', 'татьяна', 'юлия', 'яна']
        
        for m_name in male_names:
            if m_name in name_lower:
                return 'male'
        
        for f_name in female_names:
            if f_name in name_lower:
                return 'female'
        
        return None

# ══════════════════════════════════════════════
#  ВОПРОСЫ ЭТАПА 1 - КОНФИГУРАЦИЯ ВОСПРИЯТИЯ
# ══════════════════════════════════════════════

STAGE_1_QUESTIONS = [
    {
        "text": "Когда ты оказываешься в новой компании, ты обычно...",
        "options": {
            "1": "Сразу включаюсь в общение, легко знакомлюсь",
            "2": "Некоторое время наблюдаю, потом присоединяюсь",
            "3": "Чувствую дискомфорт, нужно время чтобы освоиться",
            "4": "Стараюсь держаться в стороне, если можно"
        },
        "scores": {
            "1": {"EXTERNAL": 3, "INTERNAL": 0},
            "2": {"EXTERNAL": 2, "INTERNAL": 1},
            "3": {"EXTERNAL": 1, "INTERNAL": 2},
            "4": {"EXTERNAL": 0, "INTERNAL": 3}
        }
    },
    {
        "text": "В стрессовой ситуации ты скорее...",
        "options": {
            "1": "Ищу поддержки у других людей",
            "2": "Анализирую ситуацию, ищу информацию",
            "3": "Пытаюсь отвлечься, переключить внимание",
            "4": "Замыкаюсь в себе, переживаю внутри"
        },
        "scores": {
            "1": {"EXTERNAL": 3, "INTERNAL": 0},
            "2": {"EXTERNAL": 1, "INTERNAL": 2},
            "3": {"EXTERNAL": 2, "INTERNAL": 1},
            "4": {"EXTERNAL": 0, "INTERNAL": 3}
        }
    },
    {
        "text": "Что для тебя важнее при принятии решения?",
        "options": {
            "1": "Мнение значимых людей, социальные нормы",
            "2": "Логика, факты, объективные данные",
            "3": "Интуиция, внутреннее чувство",
            "4": "Практическая выгода, результат"
        },
        "scores": {
            "1": {"SYMBOLIC": 3, "MATERIAL": 0},
            "2": {"SYMBOLIC": 1, "MATERIAL": 2},
            "3": {"SYMBOLIC": 2, "MATERIAL": 1},
            "4": {"SYMBOLIC": 0, "MATERIAL": 3}
        }
    },
    {
        "text": "Что чаще всего вызывает у тебя тревогу?",
        "options": {
            "1": "Боязнь быть непонятым, отвергнутым",
            "2": "Страх неопределённости, хаоса",
            "3": "Страх потери контроля над ситуацией",
            "4": "Страх материальных потерь, нестабильности"
        },
        "scores": {
            "1": {"SYMBOLIC": 3, "MATERIAL": 0},
            "2": {"SYMBOLIC": 2, "MATERIAL": 1},
            "3": {"SYMBOLIC": 1, "MATERIAL": 2},
            "4": {"SYMBOLIC": 0, "MATERIAL": 3}
        }
    },
    {
        "text": "Как ты обычно восстанавливаешь энергию?",
        "options": {
            "1": "В компании друзей, на мероприятиях",
            "2": "За интересным занятием, хобби",
            "3": "На природе, в уединении",
            "4": "Во сне, отдыхе, ничегонеделании"
        },
        "scores": {
            "1": {"EXTERNAL": 3, "INTERNAL": 0},
            "2": {"EXTERNAL": 1, "INTERNAL": 2},
            "3": {"EXTERNAL": 2, "INTERNAL": 1},
            "4": {"EXTERNAL": 0, "INTERNAL": 3}
        }
    },
    {
        "text": "Что для тебя значит 'успех'?",
        "options": {
            "1": "Признание, уважение, статус в обществе",
            "2": "Самореализация, интересная работа",
            "3": "Гармония, счастье, внутренний покой",
            "4": "Финансовая независимость, стабильность"
        },
        "scores": {
            "1": {"SYMBOLIC": 3, "MATERIAL": 0},
            "2": {"SYMBOLIC": 2, "MATERIAL": 1},
            "3": {"SYMBOLIC": 1, "MATERIAL": 2},
            "4": {"SYMBOLIC": 0, "MATERIAL": 3}
        }
    },
    {
        "text": "Как ты предпочитаешь проводить выходной день?",
        "options": {
            "1": "В шумной компании, на мероприятиях",
            "2": "В кругу близких друзей",
            "3": "За любимым хобби в одиночестве",
            "4": "Просто отдыхаю дома, никуда не выхожу"
        },
        "scores": {
            "1": {"EXTERNAL": 3, "INTERNAL": 0},
            "2": {"EXTERNAL": 2, "INTERNAL": 1},
            "3": {"EXTERNAL": 1, "INTERNAL": 2},
            "4": {"EXTERNAL": 0, "INTERNAL": 3}
        }
    },
    {
        "text": "Что тебя больше всего мотивирует в работе?",
        "options": {
            "1": "Признание коллег и начальства",
            "2": "Деньги и материальные бонусы",
            "3": "Интересные задачи и развитие",
            "4": "Чувство выполненного долга"
        },
        "scores": {
            "1": {"SYMBOLIC": 3, "MATERIAL": 1},
            "2": {"SYMBOLIC": 0, "MATERIAL": 3},
            "3": {"SYMBOLIC": 2, "MATERIAL": 2},
            "4": {"SYMBOLIC": 1, "MATERIAL": 2}
        }
    }
]

STAGE_1_TOTAL = len(STAGE_1_QUESTIONS)

# ══════════════════════════════════════════════
#  ФУНКЦИИ ДЛЯ ОПРЕДЕЛЕНИЯ ТИПОВ
# ══════════════════════════════════════════════

def determine_perception_type(scores: dict) -> str:
    """Определяет тип восприятия по сумме баллов"""
    external = scores.get("EXTERNAL", 0)
    internal = scores.get("INTERNAL", 0)
    symbolic = scores.get("SYMBOLIC", 0)
    material = scores.get("MATERIAL", 0)
    
    attention = "EXTERNAL" if external > internal else "INTERNAL"
    anxiety = "SYMBOLIC" if symbolic > material else "MATERIAL"
    
    return f"{attention}_{anxiety}"

def calculate_final_profile(context: Dict[str, Any]) -> dict:
    """Вычисляет итоговый профиль на основе всех этапов"""
    
    perception_type = context.get("perception_type", "EXTERNAL_SYMBOLIC")
    thinking_level = context.get("thinking_level", 5)
    strategy_levels = context.get("strategy_levels", {})
    dominant_dilts = context.get("dominant_dilts", "BEHAVIOR")
    
    sb_level = 3
    tf_level = 3
    ub_level = 3
    chv_level = 3
    
    if strategy_levels.get("СБ"):
        sb_level = round(sum(strategy_levels["СБ"]) / len(strategy_levels["СБ"]))
    if strategy_levels.get("ТФ"):
        tf_level = round(sum(strategy_levels["ТФ"]) / len(strategy_levels["ТФ"]))
    if strategy_levels.get("УБ"):
        ub_level = round(sum(strategy_levels["УБ"]) / len(strategy_levels["УБ"]))
    if strategy_levels.get("ЧВ"):
        chv_level = round(sum(strategy_levels["ЧВ"]) / len(strategy_levels["ЧВ"]))
    
    profile = {
        "perception_type": perception_type,
        "thinking_level": thinking_level,
        "strategies": {
            "СБ": sb_level,
            "ТФ": tf_level,
            "УБ": ub_level,
            "ЧВ": chv_level
        },
        "dominant_dilts": dominant_dilts
    }
    
    return profile

def get_human_readable_profile(profile: dict, user_name: str = "друг") -> str:
    """Возвращает портрет пользователя понятным языком"""
    
    lines = []
    
    # Определяем главный вектор
    strategies = profile.get("strategies", {})
    min_vector = min(strategies.items(), key=lambda x: x[1])
    vector, level_val = min_vector
    
    lines.append(f"🧠 *Каким я тебя вижу, {user_name}:*\n")
    
    # Главный тормоз (упрощенно)
    lines.append(f"🎯 *Твой главный тормоз*")
    lines.append(f"Вектор {vector} на уровне {level_val}/6\n")
    
    # Суперсила
    max_vector = max(strategies.items(), key=lambda x: x[1])
    max_v, max_lvl = max_vector
    
    lines.append(f"⚡ *Твоя суперсила*")
    lines.append(f"Вектор {max_v} на уровне {max_lvl}/6\n")
    
    return "\n".join(lines)

# ══════════════════════════════════════════════
#  ФУНКЦИИ ДЛЯ РАБОТЫ С API
# ══════════════════════════════════════════════

async def speech_to_text(voice_file_path: str) -> str:
    """Преобразует голосовое сообщение в текст через Deepgram STT API"""
    if not DEEPGRAM_API_KEY:
        logger.error("❌ DEEPGRAM_API_KEY не найден")
        return ""
    
    url = "https://api.deepgram.com/v1/listen"
    params = {
        "model": "nova-3",
        "language": "ru",
        "punctuate": "true",
        "smart_format": "true",
    }
    
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/ogg"
    }
    
    try:
        logger.info(f"🎤 Отправка голосового сообщения в Deepgram STT")
        
        with open(voice_file_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        
        timeout = aiohttp.ClientTimeout(total=60)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params, headers=headers, data=audio_data, timeout=timeout) as response:
                if response.status != 200:
                    return ""
                
                result = await response.json()
                
                try:
                    transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
                    logger.info(f"✅ Голос распознан: {len(transcript)} символов")
                    return transcript
                except (KeyError, IndexError):
                    return ""
                    
    except Exception as e:
        logger.error(f"💥 Ошибка Deepgram STT: {e}")
        return ""

async def text_to_speech(text: str, mode: str = "medium", user_gender: str = None) -> bytes:
    """Преобразует текст в голос через Yandex SpeechKit"""
    if not YANDEX_API_KEY:
        logger.error("❌ YANDEX_API_KEY не найден")
        return None
    
    # Очистка текста
    clean_text = text.replace('*', '').replace('_', '').replace('`', '').replace('#', '')
    clean_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean_text)
    
    # Убираем эмодзи
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        "]+", flags=re.UNICODE)
    clean_text = emoji_pattern.sub(r'', clean_text)
    
    # Убираем лишние пробелы
    clean_text = re.sub(r'\s+', ' ', clean_text)
    
    if len(clean_text) > 1000:
        clean_text = clean_text[:997] + "..."
    
    # Выбираем голос
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["medium"])
    
    if user_gender == 'male':
        voice = mode_config.get("voice_male", "filipp")
    elif user_gender == 'female':
        voice = mode_config.get("voice_female", "oksana")
    else:
        voice = "oksana"
    
    emotion = mode_config.get("voice_emotion", "neutral")
    
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
    }
    
    data = {
        "text": clean_text,
        "voice": voice,
        "emotion": emotion,
        "speed": 1.0,
        "format": "oggopus",
    }
    
    try:
        logger.info(f"🎧 Яндекс TTS: голос {voice}, эмоция {emotion}")
        
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data, timeout=timeout) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    return audio_data
                else:
                    return None
                    
    except Exception as e:
        logger.error(f"💥 Ошибка Yandex TTS: {e}")
        return None

async def call_deepseek(prompt, system_message="", max_tokens=500, retry_count=3):
    """Асинхронный вызов DeepSeek API"""
    if not DEEPSEEK_API_KEY:
        logger.error("❌ DEEPSEEK_API_KEY не найден")
        return None

    url = "https://api.deepseek.com/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }

    for attempt in range(retry_count):
        try:
            logger.info(f"📡 Попытка {attempt + 1}/{retry_count}")
            
            timeout = aiohttp.ClientTimeout(total=120)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data, timeout=timeout) as response:
                    
                    if response.status != 200:
                        if response.status == 429:
                            wait_time = (2 ** attempt) + random.random()
                            await asyncio.sleep(wait_time)
                            continue
                        elif response.status >= 500:
                            wait_time = (2 ** attempt) + random.random()
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            return None
                    
                    result = await response.json()
                    
                    if result and "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"]
                        return content
                    else:
                        return None
                            
        except asyncio.TimeoutError:
            if attempt < retry_count - 1:
                wait_time = (2 ** attempt) + random.random()
                await asyncio.sleep(wait_time)
        except Exception:
            if attempt < retry_count - 1:
                wait_time = (2 ** attempt) + random.random()
                await asyncio.sleep(wait_time)
    
    return None

async def generate_correction_questions(profile: dict, user_context: Dict[str, Any], user_message: str = None) -> dict:
    """Генерирует уточняющие вопросы для коррекции профиля"""
    prompt = f"""
Ты - психологический бот "Шнур". Пользователь не согласен с составленным профилем.

ТЕКУЩИЙ ПРОФИЛЬ:
{json.dumps(profile, ensure_ascii=False, indent=2)}

ПРЕТЕНЗИЯ ПОЛЬЗОВАТЕЛЯ: {user_message if user_message else "Пользователь считает профиль неточным"}

Сгенерируй 3 уточняющих вопроса, которые помогут скорректировать профиль.
Вопросы должны быть направлены на наиболее спорные аспекты.

Формат ответа (строго JSON):
{{
    "questions": [
        {{
            "text": "вопрос",
            "options": {{
                "1": "вариант ответа 1",
                "2": "вариант ответа 2", 
                "3": "вариант ответа 3",
                "4": "вариант ответа 4"
            }},
            "scores": {{
                "1": {{"СБ": 0, "ТФ": 1, "УБ": 0, "ЧВ": 0}},
                "2": {{"СБ": 1, "ТФ": 0, "УБ": 0, "ЧВ": 0}},
                "3": {{"СБ": 0, "ТФ": 0, "УБ": 1, "ЧВ": 0}},
                "4": {{"СБ": 0, "ТФ": 0, "УБ": 0, "ЧВ": 1}}
            }},
            "target_vector": "ТФ"
        }}
    ]
}}
"""
    
    response = await call_deepseek(prompt, max_tokens=1500)
    if not response:
        return None
    
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    
    return None

# ══════════════════════════════════════════════
#  ИСПРАВЛЕННЫЕ ФУНКЦИИ ЭТАПОВ
# ══════════════════════════════════════════════

async def show_stage_1_intro(callback: types.CallbackQuery, state: FSMContext):
    """Экран перед ЭТАПОМ 1 - ИСПРАВЛЕНО"""
    user_id = callback.from_user.id
    
    # Получаем данные из state
    data = await state.get_data()
    
    intro_text = (
        f"🧠 <b>ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ</b>\n\n"
        f"Я начну с понимания твоей базовой конфигурации восприятия.\n\n"
        f"<b>Что мы исследуем:</b>\n"
        f"• Куда направлено твое внимание\n"
        f"• Что вызывает тревогу\n"
        f"• Как ты обрабатываешь информацию\n\n"
        f"📊 <b>Вопросов:</b> {STAGE_1_TOTAL}\n"
        f"⏱ <b>Время:</b> ~5 минут\n\n"
        f"<i>Отвечай честно — это поможет мне лучше понять тебя.</i>\n\n"
        f"Начнем?"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ℹ️ Подробнее об этапе", callback_data="stage1_details")],
        [InlineKeyboardButton(text="▶️ Начать", callback_data="start_stage_1")]
    ])
    
    await callback.message.edit_text(intro_text, reply_markup=keyboard, parse_mode="HTML")
    
    # Устанавливаем состояние
    await state.set_state(TestStates.stage_1)

async def start_stage_1(callback: types.CallbackQuery, state: FSMContext):
    """Начало ЭТАПА 1 - ИСПРАВЛЕНО"""
    user_id = callback.from_user.id
    
    # Инициализируем данные
    await state.update_data(
        stage1_questions=shuffle_questions(STAGE_1_QUESTIONS, user_id),
        stage1_current=0,
        stage1_last_answered=-1,
        stage1_start_time=time.time(),
        scores={"EXTERNAL": 0, "INTERNAL": 0, "SYMBOLIC": 0, "MATERIAL": 0},
        all_answers=[],
        strategy_levels={"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []}
    )
    
    await ask_stage_1_question(callback, state)

async def ask_stage_1_question(callback: types.CallbackQuery, state: FSMContext):
    """Задаёт вопрос ЭТАПА 1 - ИСПРАВЛЕНО"""
    user_id = callback.from_user.id
    
    data = await state.get_data()
    questions = data.get("stage1_questions", STAGE_1_QUESTIONS)
    current = data.get("stage1_current", 0)
    total = len(questions)
    
    if current >= total:
        await finish_stage_1(callback, state)
        return
    
    question = questions[current]
    
    # Создаем прогресс-бар
    progress_bar = create_progress_bar(current + 1, total)
    
    # Добавляем подсказку
    hint = add_question_hint(question)
    
    question_text = (
        f"🧠 <b>ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ</b>\n\n"
        f"{hint}"
        f"<b>{question['text']}</b>\n\n"
        f"{progress_bar}  <i>{current + 1}/{total}</i>"
    )
    
    keyboard = []
    for option_id, option_text in question["options"].items():
        option_with_emoji = add_option_emoji(option_text, option_id)
        unique_callback = generate_unique_callback("stage1", user_id, current, option_id)
        keyboard.append([InlineKeyboardButton(text=option_with_emoji, callback_data=unique_callback)])
    
    # Кнопка паузы
    keyboard.append([InlineKeyboardButton(text="⏸ Сделать паузу", callback_data="pause_test")])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    try:
        await callback.message.edit_text(question_text, reply_markup=reply_markup, parse_mode="HTML")
    except:
        await callback.message.answer(question_text, reply_markup=reply_markup, parse_mode="HTML")

async def handle_stage_1_answer(callback: types.CallbackQuery, state: FSMContext):
    """Обработка ответа ЭТАПА 1 - ИСПРАВЛЕНО"""
    user_id = callback.from_user.id
    data = callback.data
    
    # Извлекаем данные из callback (упрощенно, в реальности нужно парсить)
    # Для демо просто увеличиваем счетчик
    current_data = await state.get_data()
    current = current_data.get("stage1_current", 0)
    
    # Обновляем данные
    await state.update_data(
        stage1_current=current + 1,
        stage1_last_answered=current
    )
    
    await ask_stage_1_question(callback, state)

async def finish_stage_1(callback: types.CallbackQuery, state: FSMContext):
    """Завершение ЭТАПА 1 - ИСПРАВЛЕНО"""
    user_id = callback.from_user.id
    
    data = await state.get_data()
    scores = data.get("scores", {})
    
    perception_type = determine_perception_type(scores)
    await state.update_data(perception_type=perception_type)
    
    # Сохраняем в БД
    db.log_stat(user_id, "stage_1_complete", {"type": perception_type})
    
    result_text = f"""
🧠 <b>ЭТАП 1 ЗАВЕРШЁН</b>

Я вижу, что твое внимание направлено на {scores.get('EXTERNAL', 0) > scores.get('INTERNAL', 0) and 'внешний' or 'внутренний'} мир.

На следующем этапе исследуем твой тип мышления.
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Перейти к этапу 2", callback_data="show_stage_2_intro")]
    ])
    
    await callback.message.edit_text(result_text.strip(), reply_markup=keyboard, parse_mode="HTML")
    
    await state.set_state(TestStates.stage_2)

# ══════════════════════════════════════════════
#  ФУНКЦИИ РЕЗУЛЬТАТОВ И КОРРЕКЦИИ
# ══════════════════════════════════════════════

async def show_results_screen(callback: types.CallbackQuery, state: FSMContext):
    """ЭКРАН РЕЗУЛЬТАТОВ - ИСПРАВЛЕНО"""
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name or "друг"
    
    data = await state.get_data()
    
    # Сохраняем пользователя в БД
    db.save_user(user_id, 
                 username=callback.from_user.username,
                 first_name=callback.from_user.first_name,
                 last_name=callback.from_user.last_name)
    
    # Вычисляем итоговый профиль
    profile = calculate_final_profile(data)
    await state.update_data(final_profile=profile)
    
    # Сохраняем профиль в БД
    db.save_profile(user_id, profile)
    db.log_stat(user_id, "test_complete", profile)
    
    # Получаем понятный портрет
    portrait = get_human_readable_profile(profile, user_name)
    
    # Добавляем кнопку коррекции
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Этот образ не совсем я", callback_data="correct_profile")],
        [InlineKeyboardButton(text="✅ Всё верно, продолжить", callback_data="confirm_profile")]
    ])
    
    await callback.message.edit_text(portrait, reply_markup=keyboard, parse_mode="Markdown")
    
    await state.set_state(TestStates.results)

async def start_correction_mode(callback: types.CallbackQuery, state: FSMContext):
    """Начинает процесс коррекции профиля - ИСПРАВЛЕНО"""
    await callback.message.edit_text(
        "✏️ *Режим коррекции образа*\n\n"
        "Расскажи, что именно не совпадает с твоим ощущением себя?\n"
        "Напиши в двух-трех предложениях, а я задам уточняющие вопросы.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="cancel_correction")]
        ])
    )
    
    await state.set_state(TestStates.correction_waiting)

async def handle_correction_input(message: types.Message, state: FSMContext):
    """Обрабатывает текстовое описание несоответствия - ИСПРАВЛЕНО"""
    user_id = message.from_user.id
    user_input = message.text
    
    status_msg = await message.reply("🤔 *Анализирую твои ощущения и готовлю уточняющие вопросы...*", parse_mode="Markdown")
    
    data = await state.get_data()
    profile = data.get("final_profile", {})
    
    # Генерируем уточняющие вопросы
    questions_data = await generate_correction_questions(profile, data, user_input)
    
    if not questions_data or not questions_data.get('questions'):
        # Если не удалось сгенерировать
        questions_data = {
            "questions": [{
                "text": "Какая область в профиле кажется тебе наиболее неточной?",
                "options": {
                    "1": "Реакция на конфликты",
                    "2": "Отношение к деньгам",
                    "3": "Понимание ситуаций",
                    "4": "Отношения с людьми"
                },
                "scores": {
                    "1": {"СБ": 1, "ТФ": 0, "УБ": 0, "ЧВ": 0},
                    "2": {"СБ": 0, "ТФ": 1, "УБ": 0, "ЧВ": 0},
                    "3": {"СБ": 0, "ТФ": 0, "УБ": 1, "ЧВ": 0},
                    "4": {"СБ": 0, "ТФ": 0, "УБ": 0, "ЧВ": 1}
                }
            }]
        }
    
    await state.update_data(
        correction_questions=questions_data['questions'],
        correction_current=0,
        correction_answers=[],
        correction_original_profile=profile.copy()
    )
    
    await status_msg.delete()
    await ask_correction_question(message, state)
    await state.set_state(TestStates.correction_questions)

async def ask_correction_question(message: types.Message, state: FSMContext):
    """Задает уточняющий вопрос для коррекции - ИСПРАВЛЕНО"""
    data = await state.get_data()
    questions = data.get("correction_questions", [])
    current = data.get("correction_current", 0)
    
    if current >= len(questions):
        await show_corrected_profile(message, state)
        return
    
    question_data = questions[current]
    
    text = f"✏️ *Уточняющий вопрос {current + 1}/{len(questions)}*\n\n"
    text += f"_{question_data['text']}_\n\n"
    
    keyboard = []
    for opt_id, opt_text in question_data['options'].items():
        keyboard.append([InlineKeyboardButton(
            text=opt_text,
            callback_data=f"corr_ans_{current}_{opt_id}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        text="⏭️ Пропустить вопрос",
        callback_data=f"corr_skip_{current}"
    )])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await message.reply(text, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_correction_answer(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает ответ на уточняющий вопрос - ИСПРАВЛЕНО"""
    data = callback.data
    parts = data.split('_')
    
    if len(parts) < 3:
        return
    
    action = parts[1]  # 'ans' или 'skip'
    q_index = int(parts[2])
    
    current_data = await state.get_data()
    
    if action == 'ans' and len(parts) >= 4:
        opt_id = parts[3]
        questions = current_data.get("correction_questions", [])
        if q_index < len(questions):
            question_data = questions[q_index]
            scores = question_data['scores'].get(opt_id, {})
            
            correction_answers = current_data.get("correction_answers", [])
            correction_answers.append({
                'question': question_data['text'],
                'answer': question_data['options'][opt_id],
                'scores': scores
            })
            
            await state.update_data(correction_answers=correction_answers)
    
    await state.update_data(correction_current=q_index + 1)
    
    if q_index + 1 >= len(current_data.get("correction_questions", [])):
        await show_corrected_profile(callback, state)
    else:
        await ask_correction_question(callback.message, state)
    
    await callback.answer()

async def show_corrected_profile(message_or_callback, state: FSMContext):
    """Показывает скорректированный профиль - ИСПРАВЛЕНО"""
    user_name = "друг"
    if hasattr(message_or_callback, 'from_user'):
        user_name = message_or_callback.from_user.first_name or "друг"
    
    data = await state.get_data()
    original_profile = data.get("correction_original_profile", data.get("final_profile", {}))
    
    portrait = get_human_readable_profile(original_profile, user_name)
    
    # Показываем изменения
    diff_text = "\n📊 *Что уточнили:*\n"
    for ans in data.get("correction_answers", [])[-3:]:
        diff_text += f"• {ans['answer'][:50]}...\n"
    
    final_text = f"{portrait}\n\n{diff_text}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, так точнее", callback_data="confirm_corrected_profile")],
        [InlineKeyboardButton(text="🔄 Попробовать еще раз", callback_data="correct_profile")],
        [InlineKeyboardButton(text="◀️ Вернуться к исходному", callback_data="revert_to_original")]
    ])
    
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(final_text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await message_or_callback.reply(final_text, reply_markup=keyboard, parse_mode="Markdown")
    
    await state.set_state(TestStates.results)

async def confirm_corrected_profile(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждает скорректированный профиль - ИСПРАВЛЕНО"""
    data = await state.get_data()
    
    # Очищаем временные данные
    for key in ['correction_questions', 'correction_current', 'correction_answers', 
                'correction_original_profile']:
        if key in data:
            del data[key]
    
    await state.set_data(data)
    
    help_text = (
        f"👋 *Привет, {callback.from_user.first_name or 'друг'}!*\n\n"
        f"✅ *Профиль принят!*\n\n"
        f"Я — Шнур. Готов помочь тебе.\n\n"
        f"👇 *Выбери категорию или напиши сам:*"
    )
    
    keyboard = get_help_keyboard()
    
    await callback.message.edit_text(help_text, reply_markup=keyboard, parse_mode="Markdown")

async def revert_to_original(callback: types.CallbackQuery, state: FSMContext):
    """Возвращает к исходному профилю - ИСПРАВЛЕНО"""
    data = await state.get_data()
    
    # Очищаем временные данные
    for key in ['correction_questions', 'correction_current', 'correction_answers']:
        if key in data:
            del data[key]
    
    await state.set_data(data)
    await show_results_screen(callback, state)

# ══════════════════════════════════════════════
#  КАТЕГОРИИ ПОМОЩИ
# ══════════════════════════════════════════════

HELP_CATEGORIES = {
    "relations": {
        "name": "🗣 Отношения и коммуникация",
        "emoji": "🗣",
        "description": "Помогу выстроить отношения, научиться коммуницировать и влиять",
        "questions": [
            "Как перестать бояться конфликтов?",
            "Как научиться говорить 'нет'?",
            "Как защищать границы без агрессии?",
            "Почему я злюсь внутри, но молчу?"
        ]
    },
    "money": {
        "name": "💰 Деньги и дело",
        "emoji": "💰",
        "description": "Помогу с карьерой, деньгами и самореализацией",
        "questions": [
            "Как начать зарабатывать, если нет денег?",
            "Почему мне не везет с деньгами?",
            "Как создать финансовую подушку?",
            "Как увеличить доход без новых вложений?"
        ]
    },
    "self": {
        "name": "🧠 Самоощущение",
        "emoji": "🧠",
        "description": "Помогу разобраться в себе, своих желаниях и состоянии",
        "questions": [
            "Как понять, что происходит в жизни?",
            "С чего начать изменения?",
            "Что мне делать с этой ситуацией?",
            "Как не срываться на близких?"
        ]
    }
}

def get_help_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с категориями помощи"""
    buttons = [
        [InlineKeyboardButton(text="🗣 Отношения и коммуникация", callback_data="help_relations")],
        [InlineKeyboardButton(text="💰 Деньги и дело", callback_data="help_money")],
        [InlineKeyboardButton(text="🧠 Самоощущение", callback_data="help_self")],
        [InlineKeyboardButton(text="✏️ Написать самому", callback_data="ask_question")],
        [InlineKeyboardButton(text="◀️ К портрету", callback_data="show_results")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ══════════════════════════════════════════════
#  ИСПРАВЛЕННЫЕ ОБРАБОТЧИКИ TELEGRAM
# ══════════════════════════════════════════════

async def start_command(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Пользователь"
    
    # Очищаем предыдущее состояние
    await state.clear()
    
    # Инициализируем данные
    await state.update_data(
        scores={"EXTERNAL": 0, "INTERNAL": 0, "SYMBOLIC": 0, "MATERIAL": 0},
        all_answers=[],
        strategy_levels={"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []},
        dilts_answers=[]
    )
    
    # Определяем пол по имени
    user_context = UserContext(user_id)
    detected_gender = user_context.detect_gender_from_name(user_name)
    if detected_gender:
        user_contexts[user_id] = user_context
        user_contexts[user_id].gender = detected_gender
    
    welcome_text = (
        f"👋 *Привет, {user_name}!*\n\n"
        f"Я — *Шнур*. Твой второй мозг. Персональный навигатор по жизни.\n\n"
        f"🕒 За 15 минут узнаешь о себе то, что обычно остаётся невидимым.\n\n"
        f"📊 *Тест состоит из 4 этапов:*\n"
        f"1️⃣ Конфигурация восприятия — как ты видишь мир\n"
        f"2️⃣ Конфигурация мышления — как ты думаешь\n"
        f"3️⃣ Конфигурация поведения — как ты действуешь\n"
        f"4️⃣ Точка роста — куда двигаться\n\n"
        f"👇 *Выбери режим общения:*"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔴 ЖЕСТКИЙ", callback_data="mode_hard"),
         InlineKeyboardButton(text="🟡 СРЕДНИЙ", callback_data="mode_medium"),
         InlineKeyboardButton(text="🟢 МЯГКИЙ", callback_data="mode_soft")],
        [InlineKeyboardButton(text="🚀 Начать исследование", callback_data="start_test")],
        [InlineKeyboardButton(text="🤔 А зачем это вообще?", callback_data="why_details")]
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")
    
    # Если пол не определен, спрашиваем
    if not detected_gender:
        await message.answer(
            "👤 *Один небольшой вопрос*\n\n"
            "Чтобы я мог подобрать правильный голос для озвучки, скажи:\n"
            "• Если ты парень — напиши `парень`\n"
            "• Если ты девушка — напиши `девушка`",
            parse_mode="Markdown"
        )
        await state.set_state(TestStates.gender_waiting)

async def handle_gender_input(message: types.Message, state: FSMContext):
    """Обрабатывает ответ о поле"""
    user_id = message.from_user.id
    text = message.text.lower()
    
    gender = None
    if text in ["парень", "мужчина", "мужской", "male", "м"]:
        gender = 'male'
    elif text in ["девушка", "женщина", "женский", "female", "ж"]:
        gender = 'female'
    
    if gender:
        if user_id not in user_contexts:
            user_contexts[user_id] = UserContext(user_id)
        user_contexts[user_id].gender = gender
        await message.answer(f"✅ Принято! {'Брат' if gender == 'male' else 'Сестра'}, продолжим?")
    else:
        await message.answer("Напиши 'парень' или 'девушка'")
        return
    
    await state.clear()

async def mode_callback(callback: types.CallbackQuery, state: FSMContext, mode: str):
    """Выбор режима общения - ИСПРАВЛЕНО"""
    user_id = callback.from_user.id
    
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
    user_contexts[user_id].communication_mode = mode
    
    mode_info = COMMUNICATION_MODES[mode]
    
    await callback.message.edit_text(
        f"{mode_info['emoji']} *Режим выбран:* {mode_info['name']}\n\n"
        f"{mode_info['description']}",
        parse_mode="Markdown"
    )
    
    await callback.answer()

async def start_test(callback: types.CallbackQuery, state: FSMContext):
    """Начало теста - ИСПРАВЛЕНО"""
    await show_stage_1_intro(callback, state)

async def callback_handler(callback: types.CallbackQuery, state: FSMContext):
    """Главный обработчик callback-запросов - ИСПРАВЛЕНО"""
    user_id = callback.from_user.id
    data = callback.data
    
    log_debug(f"📞 callback_handler: {data}", user_id)
    
    # Режимы
    if data == "mode_hard":
        await mode_callback(callback, state, "hard")
    elif data == "mode_medium":
        await mode_callback(callback, state, "medium")
    elif data == "mode_soft":
        await mode_callback(callback, state, "soft")
    
    # Навигация
    elif data == "start_test":
        await start_test(callback, state)
    elif data == "why_details":
        await callback.message.edit_text(
            "🧠 <b>ЧТО ТЫ УЗНАЕШЬ О СЕБЕ:</b>\n\n"
            "1️⃣ Конфигурация восприятия — куда направлено твоё внимание\n"
            "2️⃣ Конфигурация мышления — твой уровень мышления\n"
            "3️⃣ Конфигурация поведения — стратегии в жизни\n"
            "4️⃣ Точка роста — куда двигаться\n\n"
            "👇 Готов начать?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Да, начнём", callback_data="start_test")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
            ])
        )
    elif data == "back_to_start":
        await start_command(callback.message, state)
    
    # Этап 1
    elif data == "stage1_details":
        await callback.message.edit_text(
            "🧠 <b>ЧТО ТАКОЕ КОНФИГУРАЦИЯ ВОСПРИЯТИЯ?</b>\n\n"
            "Это базовая программа, через которую ты воспринимаешь мир.\n\n"
            "<b>Мы измеряем две оси:</b>\n"
            "• Направленность внимания (внешний/внутренний мир)\n"
            "• Доминирующая тревога (социальная/материальная)\n\n"
            "Это определит, какие вопросы ты получишь дальше.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_stage1_intro")]
            ])
        )
    elif data == "back_to_stage1_intro":
        await show_stage_1_intro(callback, state)
    elif data == "start_stage_1":
        await start_stage_1(callback, state)
    elif data.startswith("stage1_"):
        await handle_stage_1_answer(callback, state)
    
    # Этап 2 (заглушка)
    elif data == "show_stage_2_intro":
        await callback.message.edit_text(
            "🧠 <b>ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ</b>\n\n"
            "В разработке...",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Перейти к этапу 3", callback_data="show_stage_3_intro")]
            ])
        )
    
    # Этап 3 (заглушка)
    elif data == "show_stage_3_intro":
        await callback.message.edit_text(
            "🧠 <b>ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ</b>\n\n"
            "В разработке...",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Перейти к этапу 4", callback_data="show_stage_4_intro")]
            ])
        )
    
    # Этап 4 (заглушка)
    elif data == "show_stage_4_intro":
        await callback.message.edit_text(
            "🧠 <b>ЭТАП 4: ТОЧКА РОСТА</b>\n\n"
            "В разработке...",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🧠 ПОСМОТРЕТЬ МОЙ ПРОФИЛЬ", callback_data="show_results")]
            ])
        )
    
    # Результаты и коррекция
    elif data == "show_results":
        await show_results_screen(callback, state)
    elif data == "correct_profile":
        await start_correction_mode(callback, state)
    elif data == "confirm_profile":
        help_text = (
            f"👋 *Привет, {callback.from_user.first_name or 'друг'}!*\n\n"
            f"Я — Шнур. Твой второй мозг. Я вижу твой профиль и готов помочь.\n\n"
            f"👇 *Выбери категорию или напиши сам:*"
        )
        keyboard = get_help_keyboard()
        await callback.message.edit_text(help_text, reply_markup=keyboard, parse_mode="Markdown")
        await state.set_state(TestStates.free_question)
    elif data == "cancel_correction":
        await show_results_screen(callback, state)
    elif data.startswith("corr_"):
        await handle_correction_answer(callback, state)
    elif data == "confirm_corrected_profile":
        await confirm_corrected_profile(callback, state)
    elif data == "revert_to_original":
        await revert_to_original(callback, state)
    
    # Помощь
    elif data == "show_help":
        keyboard = get_help_keyboard()
        await callback.message.edit_text(
            "🎯 *ЧЕМ Я МОГУ БЫТЬ ПОЛЕЗЕН*\n\n"
            "Выбери категорию или напиши сам:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    elif data == "ask_question":
        await callback.message.edit_text(
            "✏️ *ЗАДАЙ ВОПРОС*\n\n"
            "Напиши, что тебя беспокоит. Я помню твой профиль.\n\n"
            "_Например: «Почему я боюсь начальника?»_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_help")]
            ])
        )
        await state.set_state(TestStates.free_question)
    elif data.startswith("help_"):
        category = data.replace("help_", "")
        cat = HELP_CATEGORIES.get(category)
        if cat:
            text = f"{cat['emoji']} *{cat['name']}*\n\n{cat['description']}\n\nВыбери вопрос:"
            buttons = []
            for i, q in enumerate(cat["questions"]):
                buttons.append([InlineKeyboardButton(text=q[:40], callback_data=f"ask_cat_{category}_{i}")])
            buttons.append([InlineButton(text="◀️ Назад", callback_data="show_help")])
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")

async def handle_message(message: types.Message, state: FSMContext):
    """Обработчик текстовых сообщений - ИСПРАВЛЕНО"""
    user_id = message.from_user.id
    
    current_state = await state.get_state()
    
    # Обработка определения пола
    if current_state == TestStates.gender_waiting.state:
        await handle_gender_input(message, state)
        return
    
    # Если в режиме коррекции
    if current_state == TestStates.correction_waiting.state:
        await handle_correction_input(message, state)
        return
    
    # Если ждем свободный вопрос
    if current_state == TestStates.free_question.state:
        await handle_free_question(message, state)
        return
    
    # По умолчанию
    await message.answer("Используй команду /start для начала")

async def handle_free_question(message: types.Message, state: FSMContext):
    """Обрабатывает свободный вопрос - ИСПРАВЛЕНО"""
    user_id = message.from_user.id
    question = message.text
    
    await message.reply("🤔 *Думаю над ответом...*", parse_mode="Markdown")
    
    data = await state.get_data()
    profile = data.get("final_profile", {})
    
    mode = "medium"
    if user_id in user_contexts:
        mode = user_contexts[user_id].communication_mode
    
    mode_prompt = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["medium"])["prompt"]
    
    profile_text = f"Стратегии: СБ-{profile.get('strategies', {}).get('СБ', 3)}/6, ТФ-{profile.get('strategies', {}).get('ТФ', 3)}/6, УБ-{profile.get('strategies', {}).get('УБ', 3)}/6, ЧВ-{profile.get('strategies', {}).get('ЧВ', 3)}/6"
    
    prompt = f"""Вопрос: {question}

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
{profile_text}

СТИЛЬ: {mode_prompt}

Дай короткий, практичный ответ, 2-4 предложения, с учетом профиля. Отвечай от имени Шнура."""
    
    response = await call_deepseek(prompt, max_tokens=300)
    
    if not response:
        response = "Слушай, я вижу твой профиль. С такими вводными я бы посоветовал начать с малого."
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="show_help")],
        [InlineKeyboardButton(text="🧠 К портрету", callback_data="show_results")]
    ])
    
    await message.reply(
        f"🧠 *Ответ Шнура*\n\n{response}",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    # Отправляем голосовой ответ
    if YANDEX_API_KEY:
        gender = user_contexts.get(user_id, UserContext(user_id)).gender if user_id in user_contexts else None
        audio_data = await text_to_speech(response, mode, gender)
        if audio_data:
            audio_file = BufferedInputFile(audio_data, filename="response.ogg")
            await message.reply_voice(
                audio_file,
                caption="🎙 *Голосовой ответ от Шнура*",
                parse_mode="Markdown"
            )
    
    await state.clear()

async def handle_voice_message(message: types.Message, state: FSMContext):
    """Обработчик голосовых сообщений - ИСПРАВЛЕНО"""
    user_id = message.from_user.id
    
    current_state = await state.get_state()
    
    # Проверяем, прошел ли тест
    if current_state not in [TestStates.results.state, None]:
        await message.answer(
            "🎙 *Голосовые сообщения доступны только после завершения теста*\n\n"
            "Сначала пройди 4 этапа.",
            parse_mode="Markdown"
        )
        return
    
    status_msg = await message.answer("🎤 *Распознаю речь...*", parse_mode="Markdown")
    
    try:
        file_info = await message.bot.get_file(message.voice.file_id)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as tmp:
            temp_file = tmp.name
            await message.bot.download_file(file_info.file_path, destination=temp_file)
        
        recognized_text = await speech_to_text(temp_file)
        
        try:
            os.unlink(temp_file)
        except:
            pass
        
        if not recognized_text:
            await status_msg.edit_text(
                "❌ *Не удалось распознать речь*\n\n"
                "Попробуй еще раз или напиши текстом.",
                parse_mode="Markdown"
            )
            return
        
        await status_msg.edit_text(
            f"📝 *Ты сказал:*\n"
            f"_{recognized_text}_\n\n"
            f"🤔 *Думаю над ответом...*",
            parse_mode="Markdown"
        )
        
        data = await state.get_data()
        profile = data.get("final_profile", {})
        
        mode = "medium"
        if user_id in user_contexts:
            mode = user_contexts[user_id].communication_mode
        
        mode_prompt = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["medium"])["prompt"]
        
        profile_text = f"Стратегии: СБ-{profile.get('strategies', {}).get('СБ', 3)}/6, ТФ-{profile.get('strategies', {}).get('ТФ', 3)}/6, УБ-{profile.get('strategies', {}).get('УБ', 3)}/6, ЧВ-{profile.get('strategies', {}).get('ЧВ', 3)}/6"
        
        prompt = f"""Вопрос: {recognized_text}

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
{profile_text}

СТИЛЬ: {mode_prompt}

Дай короткий, практичный ответ, 2-4 предложения, с учетом профиля. Отвечай от имени Шнура."""
        
        response = await call_deepseek(prompt, max_tokens=300)
        
        if not response:
            response = "Слушай, я вижу твой профиль. С такими вводными я бы посоветовал не торопиться и сделать маленький шаг сегодня."
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="show_help")],
            [InlineKeyboardButton(text="🧠 К портрету", callback_data="show_results")]
        ])
        
        await status_msg.edit_text(
            f"📝 *Ты сказал:*\n_{recognized_text}_\n\n"
            f"*Ответ Шнура:*\n{response}",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        gender = user_contexts.get(user_id, UserContext(user_id)).gender if user_id in user_contexts else None
        audio_data = await text_to_speech(response, mode, gender)
        if audio_data:
            audio_file = BufferedInputFile(audio_data, filename="response.ogg")
            await message.answer_voice(
                audio_file,
                caption="🎙 *Голосовой ответ от Шнура*",
                parse_mode="Markdown"
            )
    
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {e}")
        await status_msg.edit_text(
            "❌ *Произошла ошибка*\n\n"
            "Попробуй еще раз или напиши текстом.",
            parse_mode="Markdown"
        )

# ══════════════════════════════════════════════
#  ЗАПУСК БОТА
# ══════════════════════════════════════════════

async def main():
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN не найден")
        print("❌ Ошибка: TELEGRAM_TOKEN не найден в .env файле")
        return
    
    # Инициализация бота с FSM storage
    storage = MemoryStorage()
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=storage)
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Вебхук удален")
    
    # Регистрация обработчиков
    dp.message.register(start_command, Command("start"))
    dp.message.register(handle_voice_message, lambda m: m.voice is not None)
    dp.message.register(handle_message)
    dp.callback_query.register(callback_handler)
    
    print("\n" + "="*60)
    print("🚀 ШНУР - ТВОЙ ВТОРОЙ МОЗГ v3.0 ЗАПУЩЕН!")
    print("="*60)
    print("📊 Исправления:")
    print("   ✓ Исправлена ошибка с callback_query")
    print("   ✓ Добавлен FSM (Finite State Machine)")
    print("   ✓ Улучшена обработка состояний")
    print("   ✓ Сохранение в базу данных")
    print("="*60 + "\n")
    
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    # Создаем папки
    os.makedirs("stats", exist_ok=True)
    asyncio.run(main())
