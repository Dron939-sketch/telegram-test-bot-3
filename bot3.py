#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ВИРТУАЛЬНЫЙ ПСИХОЛОГ - МАТРИЦА ПОВЕДЕНИЙ 4×6
ВЕРСИЯ 8.0: ПОЛНАЯ ИНТЕГРАЦИЯ С ГИПНОТЕРАПЕВТИЧЕСКИМ МОДУЛЕМ
"""

import os
import json
import logging
import aiohttp
import asyncio
import tempfile
import random
import re
import time
from typing import Optional, Dict, List, Any, Tuple
from statistics import mean
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile, CallbackQuery, Message
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime, timedelta
from collections import defaultdict

# Импортируем описания профилей
from profiles import (
    STAGE_1_FEEDBACK,
    STAGE_2_FEEDBACK,
    STAGE_3_FEEDBACK,
    DILTS_LEVELS,
    FALLBACK_ANALYSIS,
    VECTORS,
    LEVEL_PROFILES
)

# Импортируем вопросы
from test_questions import (
    get_stage1_question,
    get_stage1_total,
    get_stage2_question,
    get_stage2_total,
    get_stage2_score,
    get_stage3_question,
    get_stage3_total,
    get_stage4_question,
    get_stage4_total,
    get_question_text,
    get_question_options,
    get_option_text,
    get_option_value,
    map_to_stage3_feedback_level,
    STAGE_2_SCORING
)

# Импортируем гипнотический модуль
from hypno_module import HypnoOrchestrator, TherapeuticTales, Anchoring

# Загружаем переменные окружения
load_dotenv()

# Токены API
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
YANDEX_API_KEY = os.environ.get("YANDEX_API_KEY", "")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")

# ID администраторов
ADMIN_IDS = [532205848]

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Хранилища данных
user_data: Dict[int, Dict[str, Any]] = {}
user_names: Dict[int, str] = {}
user_contexts: Dict[int, 'UserContext'] = {}
user_routes: Dict[int, Dict[str, Any]] = {}

# Инициализируем гипнотический оркестратор
hypno = HypnoOrchestrator()
tales = TherapeuticTales()
anchoring = Anchoring()


# ============================================
# FSM СОСТОЯНИЯ
# ============================================

class TestStates(StatesGroup):
    stage_1 = State()
    stage_2 = State()
    stage_3 = State()
    stage_4 = State()
    results = State()
    awaiting_question = State()
    pretest_question = State()


# ============================================
# РЕЖИМЫ ОБЩЕНИЯ
# ============================================

COMMUNICATION_MODES = {
    "hard": {
        "name": "🔴 ЖЕСТКИЙ РЕЖИМ",
        "description": "Делай как сказано. Вопросы потом. Ты здесь не за соплями, а за результатом.",
        "prompt": "Ты жесткий наставник, военный инструктор. Говори коротко, приказным тоном. Никакой жалости, только дело. Используй короткие предложения, команды, без воды.",
        "emoji": "🔴",
        "voice_emotion": "strict",
        "voice": "filipp"
    },
    "medium": {
        "name": "🟡 СРЕДНИЙ РЕЖИМ",
        "description": "Объясняю, показываю, поддерживаю. Но с тебя — действия. Баланс дисциплины и эмпатии.",
        "prompt": "Ты старший товарищ, наставник. Сочетаешь поддержку с требовательностью. Можешь и подбодрить, и подстегнуть. Говори по делу, но с заботой.",
        "emoji": "🟡",
        "voice_emotion": "neutral",
        "voice": "oksana"
    },
    "soft": {
        "name": "🟢 МЯГКИЙ РЕЖИМ",
        "description": "Давай разберемся, почему тебе страшно, и пойдем маленькими шагами. Для работы с травмами и блоками.",
        "prompt": "Ты заботливый друг, психотерапевт. Говори мягко, поддерживающе. Никакого давления, только принятие и помощь. Используй больше вопросов, проявляй эмпатию.",
        "emoji": "🟢",
        "voice_emotion": "good",
        "voice": "ermil"
    }
}


# ============================================
# КЛАСС UserContext
# ============================================

class UserContext:
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
        
    def get_greeting(self, user_name: str = "") -> str:
        now = datetime.now()
        hour = now.hour
        
        if 5 <= hour < 12:
            greeting = "Доброе утро"
        elif 12 <= hour < 18:
            greeting = "Добрый день"
        elif 18 <= hour < 23:
            greeting = "Добрый вечер"
        else:
            greeting = "Доброй ночи"
        
        if user_name:
            return f"{greeting}, {user_name}!"
        return greeting + "!"
    
    def get_day_context(self) -> dict:
        now = datetime.now()
        weekdays_ru = {
            0: "понедельник", 1: "вторник", 2: "среда", 3: "четверг",
            4: "пятница", 5: "суббота", 6: "воскресенье"
        }
        months_ru = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа",
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }
        
        return {
            "weekday": weekdays_ru[now.weekday()],
            "weekday_num": now.weekday(),
            "is_weekend": now.weekday() >= 5,
            "month": months_ru[now.month],
            "month_num": now.month,
            "day": now.day,
            "hour": now.hour,
            "minute": now.minute,
            "time_str": now.strftime("%H:%M")
        }
    
    def get_full_context(self, user_name: str = "") -> str:
        """Возвращает полный контекст пользователя"""
        context_parts = []
        
        context_parts.append(self.get_greeting(user_name))
        
        day_context = self.get_day_context()
        context_parts.append(f"Сегодня {day_context['weekday']}, {day_context['day']} {day_context['month']}, {day_context['time_str']}")
        
        age_stage = self.get_age_stage()
        if age_stage:
            context_parts.append(f"Возрастной этап: {age_stage}")
        
        return "\n".join(context_parts)
    
    async def get_weather(self) -> dict:
        if not self.city or not OPENWEATHER_API_KEY:
            return {}
        
        if self.weather_cache and self.weather_cache_time:
            if (datetime.now() - self.weather_cache_time).seconds < 3600:
                return self.weather_cache
        
        url = f"http://api.openweathermap.org/data/2.5/weather?q={self.city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        weather_desc = data['weather'][0]['description']
                        
                        weather_icons = {
                            "clear": "☀️",
                            "clouds": "☁️",
                            "rain": "🌧",
                            "snow": "❄️",
                            "thunderstorm": "⚡️",
                            "mist": "🌫",
                            "fog": "🌫"
                        }
                        
                        icon = "☁️"
                        main = data['weather'][0]['main'].lower()
                        for key, emoji in weather_icons.items():
                            if key in main:
                                icon = emoji
                                break
                        
                        self.weather_cache = {
                            "temp": round(data['main']['temp']),
                            "feels_like": round(data['main']['feels_like']),
                            "description": weather_desc,
                            "humidity": data['main']['humidity'],
                            "wind": round(data['wind']['speed']),
                            "icon": icon,
                            "pressure": data['main']['pressure']
                        }
                        self.weather_cache_time = datetime.now()
                        return self.weather_cache
        except Exception as e:
            logger.error(f"Ошибка получения погоды: {e}")
        return {}
    
    def get_weather_recommendation(self, weather: dict) -> str:
        if not weather:
            return ""
        
        temp = weather['temp']
        
        if temp < -20:
            return f"❄️ Морозно, {temp}°C. Сиди дома."
        elif temp < -10:
            return f"❄️ Холодно, {temp}°C. Одевайся теплее."
        elif temp < 0:
            return f"☁️ Подморозило, {temp}°C."
        elif temp < 10:
            return f"🍂 Прохладно, {temp}°C."
        elif temp < 20:
            return f"🍃 Свежо, {temp}°C."
        elif temp < 30:
            return f"☀️ Теплынь, {temp}°C."
        else:
            return f"🔥 Жара, {temp}°C."
    
    def get_age_stage(self) -> str:
        if not self.age:
            return ""
        
        if self.age < 18:
            return "Подростковый возраст — время поиска себя"
        elif self.age < 25:
            return "Молодость — время проб и ошибок"
        elif self.age < 35:
            return "Активная зрелость"
        elif self.age < 45:
            return "Расцвет — время реализации"
        elif self.age < 55:
            return "Мудрая зрелость"
        else:
            return "Возраст гармонии"


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def level(score: float) -> int:
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

def calculate_progress(current: int, total: int) -> str:
    """Возвращает прогресс-бар"""
    percent = int((current / total) * 10)
    bar = "█" * percent + "░" * (10 - percent)
    return f"▸ Вопрос {current}/{total} • {bar}"

def generate_unique_callback(prefix: str, user_id: int, question: int, option: str, extra: str = "") -> str:
    """Генерирует уникальный callback"""
    timestamp = int(time.time() * 1000) % 10000
    return f"{prefix}_{question}_{option}_{extra}_{user_id}_{timestamp}"

def determine_perception_type(scores: dict) -> str:
    """Определяет тип восприятия на основе осей"""
    external = scores.get("EXTERNAL", 0)
    internal = scores.get("INTERNAL", 0)
    symbolic = scores.get("SYMBOLIC", 0)
    material = scores.get("MATERIAL", 0)
    
    attention = "EXTERNAL" if external > internal else "INTERNAL"
    anxiety = "SYMBOLIC" if symbolic > material else "MATERIAL"
    
    if attention == "EXTERNAL" and anxiety == "SYMBOLIC":
        return "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ"
    elif attention == "EXTERNAL" and anxiety == "MATERIAL":
        return "СТАТУСНО-ОРИЕНТИРОВАННЫЙ"
    elif attention == "INTERNAL" and anxiety == "SYMBOLIC":
        return "СМЫСЛО-ОРИЕНТИРОВАННЫЙ"
    else:
        return "ПРАКТИКО-ОРИЕНТИРОВАННЫЙ"

def calculate_thinking_level_by_scores(level_scores_dict: dict) -> int:
    """Рассчитывает итоговый уровень мышления (1-9)"""
    total_score = sum(level_scores_dict.values())
    
    if total_score <= 10:
        return 1
    elif total_score <= 20:
        return 2
    elif total_score <= 30:
        return 3
    elif total_score <= 40:
        return 4
    elif total_score <= 50:
        return 5
    elif total_score <= 60:
        return 6
    elif total_score <= 70:
        return 7
    elif total_score <= 80:
        return 8
    else:
        return 9

def get_level_group(level: int) -> str:
    """Группирует уровни для обратной связи"""
    if level <= 3:
        return "1-3"
    elif level <= 6:
        return "4-6"
    else:
        return "7-9"

def calculate_final_level(stage2_level: int, stage3_scores: list) -> int:
    """Рассчитывает финальный уровень"""
    if not stage3_scores:
        return stage2_level
    avg_behavior = sum(stage3_scores) / len(stage3_scores)
    return round((stage2_level + avg_behavior) / 2)

def determine_dominant_dilts(dilts_counts: dict) -> str:
    """Определяет доминирующий уровень Дилтса"""
    if not dilts_counts:
        return "BEHAVIOR"
    dominant = max(dilts_counts.items(), key=lambda x: x[1])
    return dominant[0]

def calculate_profile_final(user_data: dict) -> dict:
    """Финальный расчет профиля"""
    perception_type = user_data.get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
    thinking_level = user_data.get("thinking_level", 5)
    
    behavioral_levels = user_data.get("behavioral_levels", {})
    
    sb_levels = behavioral_levels.get("СБ", [])
    tf_levels = behavioral_levels.get("ТФ", [])
    ub_levels = behavioral_levels.get("УБ", [])
    chv_levels = behavioral_levels.get("ЧВ", [])
    
    sb_avg = sum(sb_levels) / len(sb_levels) if sb_levels else 3
    tf_avg = sum(tf_levels) / len(tf_levels) if tf_levels else 3
    ub_avg = sum(ub_levels) / len(ub_levels) if ub_levels else 3
    chv_avg = sum(chv_levels) / len(chv_levels) if chv_levels else 3
    
    dilts_counts = user_data.get("dilts_counts", {})
    dominant_dilts = determine_dominant_dilts(dilts_counts)
    
    profile_code = f"СБ-{round(sb_avg)}_ТФ-{round(tf_avg)}_УБ-{round(ub_avg)}_ЧВ-{round(chv_avg)}"
    
    return {
        "display_name": profile_code,
        "perception_type": perception_type,
        "thinking_level": thinking_level,
        "sb_level": round(sb_avg),
        "tf_level": round(tf_avg),
        "ub_level": round(ub_avg),
        "chv_level": round(chv_avg),
        "dominant_dilts": dominant_dilts,
        "dilts_counts": dilts_counts
    }

def get_priority_order(scores: dict) -> list:
    """Определяет порядок приоритетов"""
    if not scores:
        return ["ТФ", "СБ", "УБ", "ЧВ"]
    tf = level(scores.get("ТФ", 3))
    if tf <= 2:
        rest = sorted([(k, v) for k, v in scores.items() if k != "ТФ"], key=lambda x: x[1])
        return ["ТФ"] + [r[0] for r in rest]
    else:
        return [k for k, _ in sorted(scores.items(), key=lambda x: x[1])]

def is_test_completed(user: dict) -> bool:
    """Проверяет, завершен ли тест"""
    if not user or "scores" not in user:
        return False
    return all(len(user.get("scores", {}).get(stage, [])) >= 8 for stage in VECTORS)


# ============================================
# API ФУНКЦИИ
# ============================================

async def speech_to_text(voice_file_path: str) -> str:
    """Преобразует голос в текст через Deepgram"""
    if not DEEPGRAM_API_KEY:
        logger.error("❌ DEEPGRAM_API_KEY не найден")
        return ""
    
    url = "https://api.deepgram.com/v1/listen"
    params = {
        "model": "nova-2",
        "language": "ru",
        "punctuate": "true",
        "smart_format": "true",
        "detect_language": "false"
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
            async with session.post(
                url,
                params=params,
                headers=headers,
                data=audio_data,
                timeout=timeout
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ Ошибка Deepgram API {response.status}: {error_text[:200]}")
                    return ""
                
                result = await response.json()
                
                try:
                    transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
                    logger.info(f"✅ Голос распознан: {len(transcript)} символов")
                    return transcript
                except (KeyError, IndexError) as e:
                    logger.error(f"❌ Ошибка парсинга ответа Deepgram: {e}")
                    return ""
                    
    except Exception as e:
        logger.error(f"💥 Ошибка Deepgram STT: {e}")
        return ""

async def text_to_speech(text: str, mode: str = "medium") -> Optional[bytes]:
    """Преобразует текст в голос через Yandex SpeechKit"""
    if not YANDEX_API_KEY:
        logger.error("❌ YANDEX_API_KEY не найден")
        return None
    
    clean_text = text.replace('*', '').replace('_', '').replace('`', '').replace('#', '')
    clean_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean_text)
    
    if len(clean_text) > 1000:
        clean_text = clean_text[:1000] + "..."
    
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
    }
    
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["medium"])
    voice = mode_config.get("voice", "oksana")
    emotion = mode_config.get("voice_emotion", "neutral")
    
    data = {
        "text": clean_text,
        "voice": voice,
        "emotion": emotion,
        "speed": "1.0",
        "format": "oggopus",
    }
    
    try:
        logger.info(f"🎧 Отправка в Яндекс TTS: голос {voice}, эмоция {emotion}")
        
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                data=data,
                timeout=timeout
            ) as response:
                
                if response.status == 200:
                    audio_data = await response.read()
                    logger.info(f"✅ Аудио получено: {len(audio_data)} байт")
                    return audio_data
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Ошибка Yandex TTS {response.status}: {error_text}")
                    return None
                    
    except Exception as e:
        logger.error(f"💥 Ошибка Yandex TTS: {e}")
        return None

async def call_deepseek(prompt: str, system_message: str = "", max_tokens: int = 500, retry_count: int = 3) -> Optional[str]:
    """Вызов DeepSeek API"""
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
                async with session.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=timeout
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"❌ Ошибка API {response.status}: {error_text[:200]}")
                        
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
                        logger.info(f"✅ Успех! Длина ответа: {len(content)} символов")
                        return content
                    else:
                        logger.error(f"❌ Странный формат ответа: {result}")
                        return None
                            
        except asyncio.TimeoutError:
            logger.error(f"⏰ Таймаут соединения (попытка {attempt + 1})")
            if attempt < retry_count - 1:
                wait_time = (2 ** attempt) + random.random()
                await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error(f"💥 Неожиданная ошибка: {e}")
            if attempt < retry_count - 1:
                wait_time = (2 ** attempt) + random.random()
                await asyncio.sleep(wait_time)
    
    logger.error("❌ ВСЕ ПОПЫТКИ НЕ УДАЛИСЬ")
    return None


# ============================================
# КОНФАЙНМЕНТ-МОДЕЛИРОВАНИЕ
# ============================================

class ConfinementElement:
    TYPE_RESULT = 'result'
    TYPE_IMMEDIATE_CAUSE = 'immediate_cause'
    TYPE_COMMON_CAUSE = 'common_cause'
    TYPE_UPPER_CAUSE = 'upper_cause'
    TYPE_CLOSING = 'closing'
    
    def __init__(self, element_id: int, name: str = None):
        self.id = element_id
        self.name = name
        self.description = ""
        self.element_type = None
        self.vector = None
        self.level = None
        self.archetype = None
        self.strength = 0.5
        self.vak = 'digital'
        self.causes = []
        self.caused_by = []
        self.amplifies = []
        
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.element_type,
            'vector': self.vector,
            'level': self.level,
            'archetype': self.archetype,
            'strength': self.strength,
            'vak': self.vak,
            'causes': self.causes,
            'caused_by': self.caused_by,
            'amplifies': self.amplifies
        }
    
    @classmethod
    def from_dict(cls, data):
        element = cls(data['id'], data['name'])
        element.description = data.get('description', '')
        element.element_type = data.get('type')
        element.vector = data.get('vector')
        element.level = data.get('level')
        element.archetype = data.get('archetype')
        element.strength = data.get('strength', 0.5)
        element.vak = data.get('vak', 'digital')
        element.causes = data.get('causes', [])
        element.caused_by = data.get('caused_by', [])
        element.amplifies = data.get('amplifies', [])
        return element


class ConfinementModel9:
    def __init__(self, user_id: int = None):
        self.user_id = user_id
        self.elements = {i: None for i in range(1, 10)}
        self.links = []
        self.loops = []
        self.key_confinement = None
        self.is_closed = False
        self.closure_score = 0.0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.source_scores = {}
        self.source_history = []
    
    def build_from_profile(self, scores: dict, history: list = None) -> 'ConfinementModel9':
        self.source_scores = scores
        self.source_history = history or []
        
        self.elements[1] = self._extract_main_symptom()
        self.elements[2] = self._element_from_vector('СБ', 2)
        self.elements[3] = self._element_from_vector('ТФ', 3)
        self.elements[4] = self._element_from_vector('УБ', 4)
        
        self._ensure_causal_chain([2, 3, 4])
        
        self.elements[5] = self._find_common_cause([2, 3, 4])
        self.elements[6] = self._find_cause_for(6, [2, 5])
        self.elements[7] = self._find_cause_for(7, [6, 2])
        self.elements[8] = self._find_linked_to(8, 7, causing=[6, 5])
        self.elements[9] = self._find_closing_element()
        
        self._validate_links()
        self._find_loops()
        self._identify_key_confinement()
        self._calculate_closure()
        
        return self
    
    def _extract_main_symptom(self) -> ConfinementElement:
        min_vector = min(self.source_scores.items(), key=lambda x: level(x[1]))
        vector, score = min_vector
        vector_name = VECTORS[vector]['name']
        vector_emoji = VECTORS[vector]['emoji']
        lvl = level(score)
        level_info = VECTORS[vector]['levels'][lvl]
        profile = LEVEL_PROFILES.get(vector, {}).get(lvl, {})
        
        element = ConfinementElement(1, f"{vector_emoji} {vector_name}")
        element.description = profile.get('quote', level_info['desc'])
        element.element_type = ConfinementElement.TYPE_RESULT
        element.vector = vector
        element.level = lvl
        element.archetype = profile.get('archetype')
        element.strength = 1.0
        element.vak = 'kinesthetic'
        return element
    
    def _element_from_vector(self, vector: str, element_id: int) -> ConfinementElement:
        score = self.source_scores.get(vector, 3.0)
        lvl = level(score)
        level_info = VECTORS[vector]['levels'][lvl]
        vector_name = VECTORS[vector]['name']
        vector_emoji = VECTORS[vector]['emoji']
        profile = LEVEL_PROFILES.get(vector, {}).get(lvl, {})
        
        element = ConfinementElement(element_id, f"{vector_emoji} {vector_name}")
        element.description = level_info['desc']
        element.element_type = ConfinementElement.TYPE_IMMEDIATE_CAUSE
        element.vector = vector
        element.level = lvl
        element.archetype = profile.get('archetype')
        element.strength = lvl / 6.0
        
        vak_map = {'СБ': 'kinesthetic', 'ТФ': 'digital', 'УБ': 'visual', 'ЧВ': 'auditory'}
        element.vak = vak_map.get(vector, 'digital')
        return element
    
    def _ensure_causal_chain(self, element_ids: list):
        for i in range(len(element_ids)-1):
            cause_id = element_ids[i]
            effect_id = element_ids[i+1]
            cause = self.elements[cause_id]
            effect = self.elements[effect_id]
            if not cause or not effect:
                continue
            if effect_id not in cause.amplifies:
                cause.amplifies.append(effect_id)
            if cause_id not in effect.caused_by:
                effect.caused_by.append(cause_id)
            self.links.append({
                'from': cause_id, 'to': effect_id, 'type': 'amplifies',
                'strength': cause.strength * effect.strength
            })
    
    def _find_common_cause(self, effect_ids: list) -> ConfinementElement:
        element = ConfinementElement(5, f"💭 Убеждение")
        element.description = "Есть вещи, которые я не могу изменить"
        element.element_type = ConfinementElement.TYPE_COMMON_CAUSE
        element.strength = 0.7
        element.vak = 'auditory_digital'
        return element
    
    def _find_cause_for(self, element_id: int, effect_ids: list) -> ConfinementElement:
        if element_id == 6:
            element = ConfinementElement(6, f"🏛 Система")
            element.description = "Семья, работа, культура — контекст"
        else:
            element = ConfinementElement(7, f"⚓ Глубинное убеждение")
            element.description = "То, во что ты веришь на самом деле"
        element.element_type = ConfinementElement.TYPE_UPPER_CAUSE
        element.strength = 0.8 if element_id == 7 else 0.6
        return element
    
    def _find_linked_to(self, element_id: int, source_id: int, causing: list) -> ConfinementElement:
        element = ConfinementElement(8, f"🔗 Связка")
        element.description = "То, что соединяет верхний и нижний уровни"
        element.element_type = ConfinementElement.TYPE_UPPER_CAUSE
        element.strength = 0.7
        return element
    
    def _find_closing_element(self) -> ConfinementElement:
        weakest = min(self.source_scores.items(), key=lambda x: level(x[1]))
        vector, score = weakest
        closing_map = {
            'СБ': "Мир опасен, нужно защищаться",
            'ТФ': "Ресурсов мало, их надо экономить",
            'УБ': "Все не случайно",
            'ЧВ': "Людям нельзя доверять"
        }
        element = ConfinementElement(9, f"🌍 Замыкание")
        element.description = closing_map.get(vector, "Система самоподдерживается")
        element.element_type = ConfinementElement.TYPE_CLOSING
        element.vector = vector
        element.level = level(score)
        element.strength = 1.0
        element.vak = 'visual'
        return element
    
    def _validate_links(self):
        standard_links = [
            (1,2),(1,3),(1,4),(2,3),(3,4),(5,2),(5,3),(5,4),
            (6,2),(6,5),(7,6),(7,2),(8,7),(8,6),(8,5),(9,7),(9,8),(4,9),(1,9)
        ]
        for from_id, to_id in standard_links:
            if self.elements[from_id] and self.elements[to_id]:
                if to_id not in self.elements[from_id].causes:
                    self.elements[from_id].causes.append(to_id)
                if from_id not in self.elements[to_id].caused_by:
                    self.elements[to_id].caused_by.append(from_id)
                self.links.append({'from': from_id, 'to': to_id, 'type': 'causes', 'strength': 0.7})
    
    def _find_loops(self):
        self.loops = []
        loop1 = self._check_cycle([1,2,6,9,1])
        if loop1:
            self.loops.append({
                'elements': loop1, 'type': 'symptom_behavior_belief',
                'description': 'Симптом → поведение → убеждение → симптом',
                'strength': self._calculate_loop_strength(loop1)
            })
    
    def _check_cycle(self, potential_cycle: list) -> list:
        for i in range(len(potential_cycle)-1):
            if potential_cycle[i+1] not in self.elements[potential_cycle[i]].causes:
                return None
        return potential_cycle
    
    def _calculate_loop_strength(self, cycle: list) -> float:
        strength = 1.0
        for i in range(len(cycle)-1):
            for link in self.links:
                if link['from'] == cycle[i] and link['to'] == cycle[i+1]:
                    strength *= link['strength']
                    break
        return strength
    
    def _identify_key_confinement(self):
        candidates = []
        for elem_id, element in self.elements.items():
            if not element:
                continue
            importance = (len(element.causes) + 1) * (len(element.caused_by) + 1) * element.strength
            candidates.append({'id': elem_id, 'element': element, 'importance': importance})
        candidates.sort(key=lambda x: x['importance'], reverse=True)
        if candidates:
            self.key_confinement = {'id': candidates[0]['id'], 'element': candidates[0]['element']}
    
    def _calculate_closure(self):
        for loop in self.loops:
            if 9 in loop['elements']:
                self.closure_score = loop['strength']
                self.is_closed = self.closure_score > 0.5
                return
        self.is_closed = False
        self.closure_score = 0.0
    
    def to_dict(self) -> dict:
        return {
            'user_id': self.user_id,
            'elements': {k: v.to_dict() if v else None for k, v in self.elements.items()},
            'loops': self.loops,
            'key_confinement': self.key_confinement,
            'is_closed': self.is_closed,
            'closure_score': self.closure_score,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConfinementModel9':
        model = cls(data.get('user_id'))
        elements_dict = data.get('elements', {})
        for k, v in elements_dict.items():
            if v:
                model.elements[int(k)] = ConfinementElement.from_dict(v)
        model.loops = data.get('loops', [])
        model.key_confinement = data.get('key_confinement')
        model.is_closed = data.get('is_closed', False)
        model.closure_score = data.get('closure_score', 0.0)
        if data.get('created_at'):
            model.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            model.updated_at = datetime.fromisoformat(data['updated_at'])
        return model


# ============================================
# СТАТИСТИКА
# ============================================

class Statistics:
    def __init__(self, stats_file="bot_stats.json"):
        self.stats_file = stats_file
        self.load()
    
    def load(self):
        if os.path.exists(self.stats_file):
            with open(self.stats_file, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {
                "total_starts": 0,
                "completed_tests": 0,
                "vectors": {v: {i: 0 for i in range(1, 7)} for v in VECTORS},
                "users": {},
                "daily": {},
                "last_updated": datetime.now().isoformat()
            }
    
    def save(self):
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def register_start(self, user_id):
        self.data["total_starts"] += 1
        self.data["users"][str(user_id)] = {
            "started": datetime.now().isoformat(),
            "completed": False
        }
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.data["daily"]:
            self.data["daily"][today] = {"starts": 0, "completions": 0}
        self.data["daily"][today]["starts"] = self.data["daily"][today].get("starts", 0) + 1
        self.save()
    
    def register_completion(self, user_id, scores):
        self.data["completed_tests"] += 1
        if str(user_id) in self.data["users"]:
            self.data["users"][str(user_id)]["completed"] = True
            self.data["users"][str(user_id)]["completed_at"] = datetime.now().isoformat()
            self.data["users"][str(user_id)]["scores"] = scores
        
        for vector, score in scores.items():
            lvl = level(score)
            self.data["vectors"][vector][lvl] = self.data["vectors"][vector].get(lvl, 0) + 1
        
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.data["daily"]:
            self.data["daily"][today] = {"starts": 0, "completions": 0}
        self.data["daily"][today]["completions"] = self.data["daily"][today].get("completions", 0) + 1
        self.save()
    
    def get_stats_text(self):
        total_users = len(self.data["users"])
        completed = self.data["completed_tests"]
        started = self.data["total_starts"]
        
        text = f"📊 *СТАТИСТИКА БОТА*\n\n"
        text += f"👥 Всего пользователей: *{total_users}*\n"
        text += f"▶️ Начали тест: *{started}*\n"
        text += f"✅ Завершили тест: *{completed}*\n"
        text += f"📈 Конверсия: *{(completed/started*100) if started > 0 else 0:.1f}%*\n\n"
        
        if completed > 0:
            text += "*Распределение по уровням:*\n"
            for vector, vec_data in VECTORS.items():
                text += f"\n{vec_data['emoji']} *{vec_data['name']}*\n"
                dist = self.data["vectors"][vector]
                for lvl in range(1, 7):
                    count = dist.get(lvl, 0)
                    percent = (count / completed) * 100 if completed > 0 else 0
                    bar = "█" * int(percent / 5) + "░" * (20 - int(percent / 5))
                    text += f"  Ур.{lvl}: {count} чел. {bar} {percent:.1f}%\n"
        
        text += f"\n*Последние 7 дней:*\n"
        dates = sorted(self.data["daily"].keys(), reverse=True)[:7]
        for date in dates:
            day_stats = self.data["daily"][date]
            text += f"  {date}: {day_stats.get('starts', 0)} стартов, {day_stats.get('completions', 0)} завершений\n"
        
        text += f"\n🕐 Обновлено: {self.data['last_updated']}"
        return text


stats = Statistics()


# ============================================
# МЕНЕДЖЕР ОТЛОЖЕННЫХ ЗАДАЧ
# ============================================

class DelayedTaskManager:
    def __init__(self):
        self.tasks = {}
        self.bot_instance = None
    
    def set_bot(self, bot):
        self.bot_instance = bot
    
    async def schedule_motivation(self, user_id: int, scores: dict, user_name: str, delay_minutes: int = 5):
        task_id = f"motivation_{user_id}_{datetime.now().timestamp()}"
        
        async def send_motivation():
            await asyncio.sleep(delay_minutes * 60)
            if self.bot_instance:
                try:
                    if scores:
                        min_vector = min(scores.items(), key=lambda x: level(x[1]))
                        vector, score = min_vector
                        lvl = level(score)
                        profile = LEVEL_PROFILES.get(vector, {}).get(lvl, {})
                        
                        message_text = (
                            f"🧠 *ЧЕРЕЗ {delay_minutes} МИНУТ ПОСЛЕ ТЕСТА*\n\n"
                            f"Слушай, {user_name}...\n\n"
                            f"Твое самое узкое место — {VECTORS[vector]['name']} (уровень {lvl}).\n"
                            f"{profile.get('pain_origin', '')}\n\n"
                            f"🎯 *Первый шаг:*\n"
                            f"{profile.get('immediate_tool', 'Начни с малого.')}\n\n"
                            f"⚡️ Я с тобой на связи."
                        )
                    else:
                        message_text = f"Слушай, {user_name}...\n\nКак ты? Я рядом."
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions")],
                        [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
                        [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")]
                    ])
                    
                    await self.bot_instance.send_message(
                        user_id,
                        message_text,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке мотивационного сообщения пользователю {user_id}: {e}")
        
        task = asyncio.create_task(send_motivation())
        self.tasks[task_id] = {
            "task": task,
            "user_id": user_id,
            "type": "motivation",
            "scheduled_time": datetime.now() + timedelta(minutes=delay_minutes)
        }
        logger.info(f"📅 Запланировано мотивационное сообщение для пользователя {user_id} через {delay_minutes} минут")
        return task_id
    
    def cancel_user_tasks(self, user_id: int):
        for task_id in list(self.tasks.keys()):
            if self.tasks[task_id]["user_id"] == user_id:
                self.tasks[task_id]["task"].cancel()
                del self.tasks[task_id]
        logger.info(f"❌ Отменены все задачи для пользователя {user_id}")


task_manager = DelayedTaskManager()


# ============================================
# ФУНКЦИИ РЕЗУЛЬТАТОВ
# ============================================

def get_human_readable_profile(scores: dict, model=None, perception_type="не определен", thinking_level=5, dominant_dilts="BEHAVIOR") -> str:
    """Возвращает портрет пользователя"""
    lines = []
    
    if scores:
        min_vector = min(scores.items(), key=lambda x: level(x[1]))
        vector, score = min_vector
        lvl = level(score)
        profile = LEVEL_PROFILES.get(vector, {}).get(lvl, {})
    else:
        vector = "СБ"
        profile = {}
    
    lines.append(f"🧠 *ТВОЙ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ*\n")
    lines.append(f"🔍 *Тип восприятия:* {perception_type}\n")
    lines.append(f"🧠 *Уровень мышления:* {thinking_level}/9\n")
    lines.append(f"🎯 *Твой главный тормоз*")
    lines.append(f"{profile.get('quote', 'Пока не определено')}\n")
    lines.append(f"📜 *Откуда это взялось*")
    lines.append(f"{profile.get('pain_origin', 'Из твоего опыта')}\n")
    lines.append(f"💸 *Чем ты платишь*")
    costs = profile.get('pain_costs', ['Энергией', 'Временем', 'Возможностями'])
    for cost in costs[:3]:
        lines.append(f"• {cost}")
    lines.append("")
    
    if model and hasattr(model, 'key_confinement') and model.key_confinement:
        elem = model.key_confinement.get('element')
        if elem and hasattr(elem, 'description'):
            lines.append(f"⛓ *Что держит систему*")
            lines.append(f"{elem.description[:100]}\n")
    
    dilts_desc = DILTS_LEVELS.get(dominant_dilts, "⚡ Поведение")
    lines.append(f"🎯 *Твоя точка роста:* {dilts_desc}")
    
    return "\n".join(lines)


def get_help_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с категориями помощи"""
    buttons = [
        [InlineKeyboardButton(text="🗣 Отношения", callback_data="help_cat_relations"),
         InlineKeyboardButton(text="💰 Деньги", callback_data="help_cat_money")],
        [InlineKeyboardButton(text="🧠 Самоощущение", callback_data="help_cat_self"),
         InlineKeyboardButton(text="🧠 Знания", callback_data="help_cat_knowledge")],
        [InlineKeyboardButton(text="💪 Поддержка", callback_data="help_cat_support"),
         InlineKeyboardButton(text="🎨 Муза", callback_data="help_cat_muse")],
        [InlineKeyboardButton(text="🍏 Забота", callback_data="help_cat_care")],
        [InlineKeyboardButton(text="✏️ Написать самому", callback_data="ask_question")],
        [InlineKeyboardButton(text="◀️ К ПОРТРЕТУ", callback_data="show_results")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# ОБРАБОТЧИКИ ЭТАПА 1
# ============================================

async def show_stage_1_intro(callback: CallbackQuery, state: FSMContext):
    """Экран перед ЭТАПОМ 1"""
    user_id = callback.from_user.id
    
    await state.set_state(TestStates.stage_1)
    
    intro_text = (
        f"🧠 *ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ*\n\n"
        f"Восприятие — это линза, через которую ты смотришь на мир.\n\n"
        f"🔍 *Что мы исследуем:*\n"
        f"• Куда направлено твое внимание — вовне или внутрь\n"
        f"• Какая тревога доминирует — страх отвержения или страх потери контроля\n\n"
        f"📊 *Вопросов:* 8\n"
        f"⏱ *Время:* ~3 минуты\n\n"
        f"<i>Отвечай честно — это поможет мне лучше понять тебя.</i>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать исследование", callback_data="start_stage_1")]
    ])
    
    await callback.message.edit_text(intro_text, reply_markup=keyboard, parse_mode='Markdown')


async def start_stage_1(callback: CallbackQuery, state: FSMContext):
    """Начало ЭТАПА 1"""
    user_id = callback.from_user.id
    
    await state.update_data(
        stage1_current=0,
        stage1_last_answered=-1,
        stage1_start_time=time.time(),
        perception_scores={"EXTERNAL": 0, "INTERNAL": 0, "SYMBOLIC": 0, "MATERIAL": 0}
    )
    
    await ask_stage_1_question(callback, state)


async def ask_stage_1_question(callback: CallbackQuery, state: FSMContext):
    """Задаёт вопрос ЭТАПА 1"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    current = data.get("stage1_current", 0)
    total = get_stage1_total()
    
    if current >= total:
        await finish_stage_1(callback, state)
        return
    
    question = get_stage1_question(current)
    progress = calculate_progress(current + 1, total)
    
    question_text = (
        f"🧠 *ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ*\n\n"
        f"<b>{question['text']}</b>\n\n"
        f"{progress}"
    )
    
    keyboard = []
    for option_id, option in question["options"].items():
        unique_callback = generate_unique_callback("stage1", user_id, current, option_id)
        keyboard.append([
            InlineKeyboardButton(option["text"], callback_data=unique_callback)
        ])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        question_text, 
        reply_markup=reply_markup, 
        parse_mode='HTML'
    )


async def handle_stage_1_answer(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа ЭТАПА 1"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    if data.get("processing", False):
        return
    
    await state.update_data(processing=True)
    
    try:
        parts = callback.data.split("_")
        if len(parts) < 4 or parts[0] != "stage1":
            return
        
        current = int(parts[1])
        option_id = parts[2]
        
        last_answered = data.get("stage1_last_answered", -1)
        if current <= last_answered:
            return
        
        question = get_stage1_question(current)
        selected_option = question["options"].get(option_id)
        
        if not selected_option:
            return
        
        perception_scores = data.get("perception_scores", {})
        for axis, score in selected_option.get("scores", {}).items():
            if axis in ["EXTERNAL", "INTERNAL", "SYMBOLIC", "MATERIAL"]:
                perception_scores[axis] = perception_scores.get(axis, 0) + score
        
        all_answers = data.get("all_answers", [])
        all_answers.append({
            'stage': 1,
            'question_index': current,
            'question': question['text'],
            'answer': selected_option['text'],
            'option': option_id,
            'scores': selected_option.get('scores', {})
        })
        
        await state.update_data(
            perception_scores=perception_scores,
            stage1_last_answered=current,
            stage1_current=current + 1,
            all_answers=all_answers
        )
        
        await ask_stage_1_question(callback, state)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await ask_stage_1_question(callback, state)
    finally:
        await state.update_data(processing=False)


async def finish_stage_1(callback: CallbackQuery, state: FSMContext):
    """Завершение ЭТАПА 1"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    perception_scores = data.get("perception_scores", {})
    perception_type = determine_perception_type(perception_scores)
    
    await state.update_data(perception_type=perception_type)
    
    logger.info(f"✅ User {user_id}: Stage 1 complete, type={perception_type}")
    
    result_text = STAGE_1_FEEDBACK.get(perception_type, STAGE_1_FEEDBACK["СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ"])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Перейти к этапу 2 — Конфигурация мышления", callback_data="show_stage_2_intro")]
    ])
    
    await callback.message.edit_text(result_text.strip(), reply_markup=keyboard, parse_mode='Markdown')
    await state.set_state(TestStates.stage_2)


# ============================================
# ОБРАБОТЧИКИ ЭТАПА 2
# ============================================

async def show_stage_2_intro(callback: CallbackQuery, state: FSMContext):
    """Экран перед ЭТАПОМ 2"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    perception_type = data.get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
    total_questions = get_stage2_total(perception_type)
    
    intro_text = (
        f"🧠 *ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ*\n\n"
        f"Восприятие определяет, что ты видишь. Мышление — как ты это понимаешь.\n\n"
        f"Конфигурация мышления — это траектория с чётким пунктом назначения: результат, к которому ты придёшь.\n\n"
        f"📊 *Вопросов:* {total_questions}\n"
        f"⏱ *Время:* ~3-4 минуты\n\n"
        f"<i>Продолжим исследование?</i>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать исследование", callback_data="start_stage_2")]
    ])
    
    await callback.message.edit_text(intro_text, reply_markup=keyboard, parse_mode='Markdown')


async def start_stage_2(callback: CallbackQuery, state: FSMContext):
    """Начало ЭТАПА 2"""
    user_id = callback.from_user.id
    
    await state.update_data(
        stage2_current=0,
        stage2_last_answered=-1,
        stage2_start_time=time.time(),
        stage2_level_scores_dict={"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0, "7": 0, "8": 0, "9": 0},
        strategy_levels={"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []}
    )
    
    await ask_stage_2_question(callback, state)


async def ask_stage_2_question(callback: CallbackQuery, state: FSMContext):
    """Задаёт вопрос ЭТАПА 2"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    perception_type = data.get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
    current = data.get("stage2_current", 0)
    total_questions = get_stage2_total(perception_type)
    
    if current >= total_questions:
        await finish_stage_2(callback, state)
        return
    
    question = get_stage2_question(perception_type, current)
    if not question:
        await finish_stage_2(callback, state)
        return
    
    measures = question.get("measures", "thinking")
    progress = calculate_progress(current + 1, total_questions)
    
    question_text = (
        f"🧠 *ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ*\n\n"
        f"<b>{question['text']}</b>\n\n"
        f"{progress}"
    )
    
    keyboard = []
    for level_num, answer_text in question["options"].items():
        unique_callback = generate_unique_callback("stage2", user_id, current, level_num, measures)
        keyboard.append([
            InlineKeyboardButton(answer_text, callback_data=unique_callback)
        ])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        question_text, 
        reply_markup=reply_markup, 
        parse_mode='HTML'
    )


async def handle_stage_2_answer(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа ЭТАПА 2"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    if data.get("processing", False):
        return
    
    await state.update_data(processing=True)
    
    try:
        parts = callback.data.split("_")
        if len(parts) < 5 or parts[0] != "stage2":
            return
        
        current = int(parts[1])
        selected_level = parts[2]
        measures = parts[3]
        
        last_answered = data.get("stage2_last_answered", -1)
        if current <= last_answered:
            return
        
        perception_type = data.get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
        question = get_stage2_question(perception_type, current)
        if not question:
            return
        
        answer_text = question["options"].get(selected_level, "неизвестно")
        
        stage2_level_scores_dict = data.get("stage2_level_scores_dict", {})
        
        if measures == "thinking":
            points = get_stage2_score(perception_type, current, selected_level)
            stage2_level_scores_dict[selected_level] = stage2_level_scores_dict.get(selected_level, 0) + points
        
        strategy_levels = data.get("strategy_levels", {"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []})
        if measures in ["СБ", "ТФ", "УБ", "ЧВ"]:
            try:
                value = int(selected_level)
                strategy_levels[measures].append(value)
            except ValueError:
                pass
        
        all_answers = data.get("all_answers", [])
        all_answers.append({
            'stage': 2,
            'question_index': current,
            'question': question['text'],
            'answer': answer_text,
            'option': selected_level,
            'measures': measures,
            'perception_type': perception_type
        })
        
        await state.update_data(
            stage2_level_scores_dict=stage2_level_scores_dict,
            strategy_levels=strategy_levels,
            stage2_last_answered=current,
            stage2_current=current + 1,
            all_answers=all_answers
        )
        
        await ask_stage_2_question(callback, state)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await ask_stage_2_question(callback, state)
    finally:
        await state.update_data(processing=False)


async def finish_stage_2(callback: CallbackQuery, state: FSMContext):
    """Завершение ЭТАПА 2"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    level_scores_dict = data.get("stage2_level_scores_dict", {})
    thinking_level = calculate_thinking_level_by_scores(level_scores_dict)
    
    await state.update_data(thinking_level=thinking_level)
    
    perception_type = data.get("perception_type", "СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ")
    level_group = get_level_group(thinking_level)
    
    logger.info(f"✅ User {user_id}: Stage 2 complete, level={thinking_level}")
    
    result_text = STAGE_2_FEEDBACK.get((perception_type, level_group))
    if not result_text:
        result_text = STAGE_2_FEEDBACK[("СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ", "1-3")]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Перейти к этапу 3 — Конфигурация поведения", callback_data="show_stage_3_intro")]
    ])
    
    await callback.message.edit_text(result_text.strip(), reply_markup=keyboard, parse_mode='Markdown')
    await state.set_state(TestStates.stage_3)


# ============================================
# ОБРАБОТЧИКИ ЭТАПА 3
# ============================================

async def show_stage_3_intro(callback: CallbackQuery, state: FSMContext):
    """Экран перед ЭТАПОМ 3"""
    user_id = callback.from_user.id
    
    intro_text = (
        f"🧠 *ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ*\n\n"
        f"Восприятие определяет, что ты видишь.\n"
        f"Мышление — как ты это понимаешь.\n\n"
        f"Конфигурация поведения — это то, как ты на это реагируешь.\n\n"
        f"🔍 *Здесь мы исследуем:*\n"
        f"• Твои автоматические реакции\n"
        f"• Как ты действуешь в разных ситуациях\n\n"
        f"📊 *Вопросов:* 8\n"
        f"⏱ *Время:* ~3 минуты\n\n"
        f"<i>Продолжим?</i>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать исследование", callback_data="start_stage_3")]
    ])
    
    await callback.message.edit_text(intro_text, reply_markup=keyboard, parse_mode='Markdown')


async def start_stage_3(callback: CallbackQuery, state: FSMContext):
    """Начало ЭТАПА 3"""
    user_id = callback.from_user.id
    
    await state.update_data(
        stage3_current=0,
        stage3_last_answered=-1,
        stage3_start_time=time.time(),
        stage3_level_scores=[],
        behavioral_levels={"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []}
    )
    
    await ask_stage_3_question(callback, state)


async def ask_stage_3_question(callback: CallbackQuery, state: FSMContext):
    """Задаёт вопрос ЭТАПА 3"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    current = data.get("stage3_current", 0)
    total = get_stage3_total()
    
    if current >= total:
        await finish_stage_3(callback, state)
        return
    
    question = get_stage3_question(current)
    strategy = question.get("strategy", "УБ")
    progress = calculate_progress(current + 1, total)
    
    question_text = (
        f"🧠 *ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ*\n\n"
        f"<b>{question['text']}</b>\n\n"
        f"{progress}"
    )
    
    keyboard = []
    for option_id, option_text in question["options"].items():
        unique_callback = generate_unique_callback("stage3", user_id, current, option_id, strategy)
        keyboard.append([
            InlineKeyboardButton(option_text, callback_data=unique_callback)
        ])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        question_text, 
        reply_markup=reply_markup, 
        parse_mode='HTML'
    )


async def handle_stage_3_answer(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа ЭТАПА 3"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    if data.get("processing", False):
        return
    
    await state.update_data(processing=True)
    
    try:
        parts = callback.data.split("_")
        if len(parts) < 5 or parts[0] != "stage3":
            return
        
        current = int(parts[1])
        option_id = parts[2]
        strategy = parts[3]
        
        stage3_current = data.get("stage3_current", 0)
        
        if current < stage3_current:
            await ask_stage_3_question(callback, state)
            return
        
        question = get_stage3_question(current)
        option_text = question["options"].get(option_id)
        
        if not option_text:
            return
        
        try:
            level_val = int(option_id)
        except ValueError:
            level_val = 1
        
        stage3_level_scores = data.get("stage3_level_scores", [])
        stage3_level_scores.append(level_val)
        
        behavioral_levels = data.get("behavioral_levels", {"СБ": [], "ТФ": [], "УБ": [], "ЧВ": []})
        if strategy in ["СБ", "ТФ", "УБ", "ЧВ"]:
            behavioral_levels[strategy].append(level_val)
        
        all_answers = data.get("all_answers", [])
        all_answers.append({
            'stage': 3,
            'question_index': current,
            'question': question['text'],
            'answer': option_text,
            'answer_value': level_val,
            'strategy': strategy
        })
        
        await state.update_data(
            stage3_level_scores=stage3_level_scores,
            behavioral_levels=behavioral_levels,
            stage3_last_answered=current,
            stage3_current=current + 1,
            all_answers=all_answers
        )
        
        await ask_stage_3_question(callback, state)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await ask_stage_3_question(callback, state)
    finally:
        await state.update_data(processing=False)


async def finish_stage_3(callback: CallbackQuery, state: FSMContext):
    """Завершение ЭТАПА 3"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    stage2_level = data.get("thinking_level", 1)
    stage3_scores = data.get("stage3_level_scores", [])
    
    final_level = calculate_final_level(stage2_level, stage3_scores)
    await state.update_data(final_level=final_level)
    
    behavior_level = map_to_stage3_feedback_level(final_level)
    
    logger.info(f"✅ User {user_id}: Stage 3 complete, final_level={final_level}")
    
    result_text = STAGE_3_FEEDBACK.get(behavior_level, STAGE_3_FEEDBACK[1])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Перейти к завершающему этапу", callback_data="show_stage_4_intro")]
    ])
    
    await callback.message.edit_text(result_text.strip(), reply_markup=keyboard, parse_mode='Markdown')
    await state.set_state(TestStates.stage_4)


# ============================================
# ОБРАБОТЧИКИ ЭТАПА 4
# ============================================

async def show_stage_4_intro(callback: CallbackQuery, state: FSMContext):
    """Экран перед ЭТАПОМ 4"""
    user_id = callback.from_user.id
    
    intro_text = (
        f"🧠 *ЭТАП 4: ТОЧКА РОСТА*\n\n"
        f"Восприятие — что ты видишь.\n"
        f"Мышление — как понимаешь.\n"
        f"Поведение — как реагируешь.\n\n"
        f"🔍 Здесь мы найдём, где именно находится рычаг — место, где минимальное усилие даёт максимальные изменения.\n\n"
        f"📊 *Вопросов:* 8\n"
        f"⏱ *Время:* ~3 минуты\n\n"
        f"<i>Готов найти свою точку роста?</i>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать исследование", callback_data="start_stage_4")]
    ])
    
    await callback.message.edit_text(intro_text, reply_markup=keyboard, parse_mode='Markdown')


async def start_stage_4(callback: CallbackQuery, state: FSMContext):
    """Начало ЭТАПА 4"""
    user_id = callback.from_user.id
    
    await state.update_data(
        stage4_current=0,
        stage4_last_answered=-1,
        stage4_start_time=time.time(),
        dilts_counts={"ENVIRONMENT": 0, "BEHAVIOR": 0, "CAPABILITIES": 0, "VALUES": 0, "IDENTITY": 0}
    )
    
    await ask_stage_4_question(callback, state)


async def ask_stage_4_question(callback: CallbackQuery, state: FSMContext):
    """Задаёт вопрос ЭТАПА 4"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    current = data.get("stage4_current", 0)
    total = get_stage4_total()
    
    if current >= total:
        await finish_stage_4(callback, state)
        return
    
    question = get_stage4_question(current)
    progress = calculate_progress(current + 1, total)
    
    question_text = (
        f"🧠 *ЭТАП 4: ТОЧКА РОСТА*\n\n"
        f"<b>{question['text']}</b>\n\n"
        f"{progress}"
    )
    
    keyboard = []
    for option_id, option in question["options"].items():
        unique_callback = generate_unique_callback("stage4", user_id, current, option_id)
        keyboard.append([
            InlineKeyboardButton(option["text"], callback_data=unique_callback)
        ])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        question_text, 
        reply_markup=reply_markup, 
        parse_mode='HTML'
    )


async def handle_stage_4_answer(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа ЭТАПА 4"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    if data.get("processing", False):
        return
    
    await state.update_data(processing=True)
    
    try:
        parts = callback.data.split("_")
        if len(parts) < 4 or parts[0] != "stage4":
            return
        
        current = int(parts[1])
        option_id = parts[2]
        
        last_answered = data.get("stage4_last_answered", -1)
        if current <= last_answered:
            return
        
        question = get_stage4_question(current)
        selected_option = question["options"].get(option_id)
        
        if not selected_option:
            return
        
        dilts = selected_option.get("dilts", "BEHAVIOR")
        dilts_counts = data.get("dilts_counts", {})
        dilts_counts[dilts] = dilts_counts.get(dilts, 0) + 1
        
        all_answers = data.get("all_answers", [])
        all_answers.append({
            'stage': 4,
            'question_index': current,
            'question': question['text'],
            'answer': selected_option['text'],
            'option': option_id,
            'dilts': dilts
        })
        
        await state.update_data(
            dilts_counts=dilts_counts,
            stage4_last_answered=current,
            stage4_current=current + 1,
            all_answers=all_answers
        )
        
        await ask_stage_4_question(callback, state)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await ask_stage_4_question(callback, state)
    finally:
        await state.update_data(processing=False)


async def finish_stage_4(callback: CallbackQuery, state: FSMContext):
    """Завершение ЭТАПА 4"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    dilts_counts = data.get("dilts_counts", {})
    dominant_dilts = determine_dominant_dilts(dilts_counts)
    await state.update_data(dominant_dilts=dominant_dilts)
    
    profile_data = calculate_profile_final(data)
    await state.update_data(profile_data=profile_data)
    
    logger.info(f"✅ User {user_id}: Stage 4 complete, profile={profile_data.get('display_name', 'unknown')}")
    
    scores = {}
    for vector in ["СБ", "ТФ", "УБ", "ЧВ"]:
        levels = data.get("behavioral_levels", {}).get(vector, [])
        scores[vector] = sum(levels) / len(levels) if levels else 3
    
    model = ConfinementModel9(user_id)
    model.build_from_profile(scores, data.get('history', []))
    
    await state.update_data(confinement_model=model.to_dict())
    
    analysis_text = f"""
🧠 *АНАЛИЗИРУЮ ДАННЫЕ*

<b>Соединяются четыре слоя информации:</b>
▸ ✅ Конфигурация восприятия — определена
▸ ✅ Конфигурация мышления — проанализирована
▸ ✅ Конфигурация поведения — обработана
▸ ✅ Точка роста — найдена

<b>Формирую твой уникальный профиль...</b>

⏳ Пожалуйста, подожди несколько секунд...
"""
    
    await callback.message.edit_text(analysis_text.strip(), parse_mode='HTML')
    await asyncio.sleep(2)
    
    await show_results_screen(callback, state)


# ============================================
# ФУНКЦИИ РЕЗУЛЬТАТОВ
# ============================================

async def show_results_screen(callback: CallbackQuery, state: FSMContext):
    """Показывает финальный портрет"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    perception_type = data.get("perception_type", "не определен")
    thinking_level = data.get("thinking_level", 5)
    dominant_dilts = data.get("dominant_dilts", "BEHAVIOR")
    
    if user_id not in user_data:
        user_data[user_id] = {}
    
    if not user_data[user_id].get("logged", False):
        stats.register_completion(user_id, scores)
        user_data[user_id]["logged"] = True
        
        user_name = user_names.get(user_id, callback.from_user.first_name or "друг")
        asyncio.create_task(schedule_motivation_standalone(user_id, scores, user_name, delay_minutes=5))
    
    model_data = data.get('confinement_model')
    model = None
    if model_data:
        try:
            model = ConfinementModel9.from_dict(model_data)
        except Exception as e:
            logger.error(f"Ошибка при создании модели из данных: {e}")
    
    text = get_human_readable_profile(scores, model, perception_type, thinking_level, dominant_dilts)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 МЫСЛИ ПСИХОЛОГА", callback_data="ai_analysis")],
        [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help"),
         InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions")],
        [InlineKeyboardButton(text="📖 СКАЗКА", callback_data="show_tale"),
         InlineKeyboardButton(text="✨ ЕЩЁ", callback_data="more_info")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
    await state.set_state(TestStates.results)


async def schedule_motivation_standalone(user_id: int, scores: dict, user_name: str, delay_minutes: int = 5):
    """Планирует отправку мотивационного сообщения"""
    await asyncio.sleep(delay_minutes * 60)
    
    try:
        if scores:
            min_vector = min(scores.items(), key=lambda x: level(x[1]))
            vector, score = min_vector
            lvl = level(score)
            profile = LEVEL_PROFILES.get(vector, {}).get(lvl, {})
            
            message_text = (
                f"🧠 *ЧЕРЕЗ {delay_minutes} МИНУТ ПОСЛЕ ТЕСТА*\n\n"
                f"Слушай, {user_name}...\n\n"
                f"Твое самое узкое место — {VECTORS[vector]['name']} (уровень {lvl}).\n"
                f"{profile.get('pain_origin', '')}\n\n"
                f"🎯 *Первый шаг:*\n"
                f"{profile.get('immediate_tool', 'Начни с малого.')}\n\n"
                f"⚡️ Я с тобой на связи."
            )
        else:
            message_text = f"Слушай, {user_name}...\n\nКак ты? Я рядом."
        
        logger.info(f"Мотивационное сообщение для пользователя {user_id} готово к отправке")
        
    except Exception as e:
        logger.error(f"Ошибка в schedule_motivation_standalone для пользователя {user_id}: {e}")


# ============================================
# AI АНАЛИЗ И РЕКОМЕНДАЦИИ
# ============================================

async def show_ai_analysis(callback: CallbackQuery, state: FSMContext):
    """Показывает AI анализ профиля"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    if data.get("ai_analysis"):
        await show_saved_ai_analysis(callback, data["ai_analysis"])
        return
    
    await callback.message.edit_text(
        "🧠 *Анализирую ваш профиль...*\n\n_Это займёт около 20 секунд_",
        parse_mode='Markdown'
    )
    
    bottleneck_key = get_priority_order(scores)[0]
    bottleneck_lvl = level(scores[bottleneck_key])
    bottleneck_profile = LEVEL_PROFILES.get(bottleneck_key, {}).get(bottleneck_lvl, {})
    bottleneck_vec = VECTORS[bottleneck_key]
    
    prompt = f"""ТЫ — ПСИХОЛОГ. Напиши психологический портрет.

УЗКОЕ МЕСТО:
- Вектор: {bottleneck_vec['name']}
- Уровень: {bottleneck_lvl}/6
- Архетип: {bottleneck_profile.get('archetype', '')}

НАПИШИ:
1. Суть проблемы (2-3 предложения)
2. Откуда это взялось (2 предложения)
3. Первый шаг (3 конкретных действия)
4. Цитата-напутствие

СТИЛЬ: Как старший товарищ — честно, с заботой, без воды."""
    
    system_message = "Ты психолог. Пиши коротко, метафорично."
    response = await call_deepseek(prompt, system_message, max_tokens=1000)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ ВОПРОСЫ", callback_data="smart_questions")],
        [InlineKeyboardButton(text="💡 ЧТО ДЕЛАТЬ", callback_data="ai_recommendations")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="show_results")]
    ])
    
    if response:
        await state.update_data(ai_analysis=response)
        await show_saved_ai_analysis(callback, response)
    else:
        fallback_text = FALLBACK_ANALYSIS[bottleneck_key][bottleneck_lvl]
        await callback.message.edit_text(
            f"🧠 *МЫСЛИ ПСИХОЛОГА*\n\n{fallback_text}",
            parse_mode='Markdown',
            reply_markup=keyboard
        )


async def show_saved_ai_analysis(callback: CallbackQuery, analysis_text: str):
    """Показывает сохраненный AI анализ"""
    def escape_markdown(text):
        text = text.replace('**', '‼BOLD‼')
        dangerous = '_*[]()~`>+=|{}!'
        for char in dangerous:
            text = text.replace(char, f'\\{char}')
        text = text.replace('‼BOLD‼', '**')
        return text
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ ВОПРОСЫ", callback_data="smart_questions")],
        [InlineKeyboardButton(text="💡 ЧТО ДЕЛАТЬ", callback_data="ai_recommendations")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="show_results")]
    ])
    
    safe_text = escape_markdown(analysis_text)
    full_text = f"🧠 *МЫСЛИ ПСИХОЛОГА*\n\n{safe_text}"
    
    await callback.message.edit_text(full_text, parse_mode='Markdown', reply_markup=keyboard)


async def show_ai_recommendations(callback: CallbackQuery, state: FSMContext):
    """Показывает AI рекомендации"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    if data.get("ai_recommendations"):
        await show_saved_recommendations(callback, data["ai_recommendations"])
        return
    
    await callback.message.edit_text(
        "💡 *Подбираю рекомендации...*\n\n_Это займёт около 15-20 секунд_",
        parse_mode='Markdown'
    )
    
    bottleneck_key = get_priority_order(scores)[0]
    bottleneck_lvl = level(scores[bottleneck_key])
    bottleneck_vec = VECTORS[bottleneck_key]
    
    vectors_context = []
    for key in VECTORS:
        lvl = level(scores[key])
        vec = VECTORS[key]
        profile = LEVEL_PROFILES.get(key, {}).get(lvl, {})
        vectors_context.append(f"{vec['name']}: {lvl}/6 — {profile.get('archetype', '')}")
    
    prompt = f"""ТЫ — ПСИХОЛОГ. Напиши персональные рекомендации.

ПРОФИЛЬ:
{chr(10).join(vectors_context)}

УЗКОЕ МЕСТО: {bottleneck_vec['name']} (уровень {bottleneck_lvl}/6)

НАПИШИ 3 БЛОКА:
⚡ ЧТО ДЕЛАТЬ СЕГОДНЯ (3 микро-действия)
📌 ЧТО ДЕЛАТЬ НА ЭТОЙ НЕДЕЛЕ (3 задачи)
🔥 ЧТО ДЕЛАТЬ В ЭТОМ МЕСЯЦЕ (2-3 шага)

Коротко, конкретно, по делу. Каждый пункт с •"""
    
    system_message = "Ты психолог. Пиши коротко, конкретно."
    response = await call_deepseek(prompt, system_message, max_tokens=800)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ ЕЩЁ ВОПРОС", callback_data="smart_questions")],
        [InlineKeyboardButton(text="🧠 МЫСЛИ ПСИХОЛОГА", callback_data="ai_analysis")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="show_results")]
    ])
    
    if response:
        await state.update_data(ai_recommendations=response)
        await show_saved_recommendations(callback, response)
    else:
        fallback_text = FALLBACK_ANALYSIS[bottleneck_key][bottleneck_lvl]
        await callback.message.edit_text(
            f"💡 *ПЛАН ДЕЙСТВИЙ*\n\n{fallback_text}",
            parse_mode='Markdown',
            reply_markup=keyboard
        )


async def show_saved_recommendations(callback: CallbackQuery, recommendations_text: str):
    """Показывает сохраненные рекомендации"""
    def escape_markdown(text):
        text = text.replace('**', '‼BOLD‼')
        dangerous = '_*[]()~`>+=|{}!'
        for char in dangerous:
            text = text.replace(char, f'\\{char}')
        text = text.replace('‼BOLD‼', '**')
        return text
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ ЕЩЁ ВОПРОС", callback_data="smart_questions")],
        [InlineKeyboardButton(text="🧠 МЫСЛИ ПСИХОЛОГА", callback_data="ai_analysis")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="show_results")]
    ])
    
    safe_text = escape_markdown(recommendations_text)
    full_text = f"💡 *ПЛАН ДЕЙСТВИЙ*\n\n{safe_text}"
    
    await callback.message.edit_text(full_text, parse_mode='Markdown', reply_markup=keyboard)


# ============================================
# SMART QUESTIONS
# ============================================

def generate_smart_questions(scores):
    """Генерирует вопросы на основе профиля"""
    questions = []
    
    tf = level(scores.get("ТФ", 3))
    sb = level(scores.get("СБ", 3))
    ub = level(scores.get("УБ", 3))
    cv = level(scores.get("ЧВ", 3))
    
    if tf <= 2:
        questions.append("Как начать зарабатывать, если нет денег?")
        questions.append("Почему мне не везет с деньгами?")
    elif tf <= 4:
        questions.append("Как увеличить доход без новых вложений?")
        questions.append("Как создать финансовую подушку?")
    
    if sb <= 2:
        questions.append("Как перестать бояться конфликтов?")
        questions.append("Как научиться говорить 'нет'?")
    elif sb <= 4:
        questions.append("Почему я злюсь внутри, но молчу?")
        questions.append("Как защищать границы без агрессии?")
    
    if ub <= 2:
        questions.append("Как понять, что происходит в жизни?")
    elif ub == 4:
        questions.append("Как перестать искать заговоры?")
    
    if cv <= 2:
        questions.append("Как перестать зависеть от других?")
    elif cv <= 4:
        questions.append("Почему отношения поверхностные?")
    
    general = [
        "С чего начать изменения?",
        "Что мне делать с этой ситуацией?",
        "Как не срываться на близких?"
    ]
    
    while len(questions) < 5:
        for q in general:
            if q not in questions and len(questions) < 5:
                questions.append(q)
    
    return questions[:5]


async def show_smart_questions(callback: CallbackQuery, state: FSMContext):
    """Показывает умные вопросы"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    questions = generate_smart_questions(scores)
    await state.update_data(smart_questions=questions)
    
    keyboard = []
    for i, q in enumerate(questions, 1):
        q_short = q[:40] + "..." if len(q) > 40 else q
        keyboard.append([InlineKeyboardButton(
            text=f"{q_short}",
            callback_data=f"ask_{i}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        text="✏️ Спросить самому", 
        callback_data="ask_question"
    )])
    keyboard.append([InlineKeyboardButton(
        text="◀️ Назад к портрету", 
        callback_data="show_results"
    )])
    
    await callback.message.edit_text(
        f"❓ *ЧТО ТЕБЯ БЕСПОКОИТ?*\n\n"
        f"Выбери вопрос или задай свой. Я помню твой профиль.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='Markdown'
    )


async def handle_smart_question(callback: CallbackQuery, state: FSMContext, question: str):
    """Обрабатывает выбранный умный вопрос"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    await callback.message.edit_text(
        "🤔 *Думаю над ответом...*\n\n"
        "_Это займёт около 10-15 секунд_",
        parse_mode='Markdown'
    )
    
    context_obj = user_contexts.get(user_id)
    user_name = user_names.get(user_id, callback.from_user.first_name or "друг")
    mode = context_obj.communication_mode if context_obj else "medium"
    
    profile_lines = []
    for k, v in scores.items():
        lvl = level(v)
        p = LEVEL_PROFILES.get(k, {}).get(lvl, {})
        profile_lines.append(f"{VECTORS[k]['name']}: {lvl}/6 — {p.get('archetype', '')}")
    profile_summary = "\n".join(profile_lines)
    
    context_text = ""
    if context_obj:
        context_text = context_obj.get_full_context(user_name)
        weather = await context_obj.get_weather()
        if weather:
            context_text += f"\n{context_obj.get_weather_recommendation(weather)}"
    
    history_text = ""
    if data.get("history"):
        recent = data["history"][-5:]
        for entry in recent:
            role = "Клиент" if entry["role"] == "user" else "Психолог"
            history_text += f"{role}: {entry['text']}\n"
    
    mode_prompt = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["medium"])["prompt"]
    
    # Используем гипнотический оркестратор вместо прямого вызова DeepSeek
    hypno_context = {
        'confinement_model': data.get('confinement_model'),
        'scores': scores,
        'history': data.get('history', [])[-5:]
    }
    
    response = hypno.process(user_id, question, hypno_context)
    
    history = data.get("history", [])
    history.append({
        "role": "user", 
        "text": question, 
        "timestamp": datetime.now().isoformat()
    })
    history.append({
        "role": "assistant", 
        "text": response, 
        "timestamp": datetime.now().isoformat()
    })
    await state.update_data(history=history)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="smart_questions")],
        [InlineKeyboardButton(text="🧠 К портрету", callback_data="show_results")],
        [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")]
    ])
    
    await callback.message.edit_text(
        f"❓ *{question}*\n\n{response}",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    
    audio_data = await text_to_speech(response, mode)
    if audio_data:
        audio_file = BufferedInputFile(audio_data, filename="response.ogg")
        await callback.message.answer_voice(
            audio_file,
            caption="🎙 *Голосовой ответ*",
            parse_mode='Markdown'
        )


# ============================================
# ОБРАБОТЧИКИ ПОМОЩИ
# ============================================

async def show_help(callback: CallbackQuery, state: FSMContext):
    """Показывает меню помощи"""
    keyboard = get_help_keyboard()
    await callback.message.edit_text(
        "🎯 *ЧЕМ Я МОГУ БЫТЬ ПОЛЕЗЕН*\n\n"
        "Выбери категорию или напиши сам:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_help_category(callback: CallbackQuery, state: FSMContext, category: str):
    """Обработчик категорий помощи"""
    user_id = callback.from_user.id
    
    category_texts = {
        "relations": "🗣 *Отношения*\n\nРасскажи, что происходит в отношениях. Я помогу разобраться.",
        "money": "💰 *Деньги и ресурсы*\n\nЧто беспокоит в финансовой сфере?",
        "self": "🧠 *Самоощущение*\n\nРасскажи о том, что чувствуешь.",
        "knowledge": "🧠 *Знания и развитие*\n\nЧто хочешь понять или освоить?",
        "support": "💪 *Поддержка*\n\nНужно просто выговориться? Я здесь.",
        "muse": "🎨 *Муза и творчество*\n\nТворческий блок? Расскажи.",
        "care": "🍏 *Забота о себе*\n\nКак ты заботишься о себе?"
    }
    
    text = category_texts.get(category, "Чем я могу помочь?")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Написать", callback_data="ask_question")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="show_help")]
    ])
    
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=keyboard)
    await state.set_state(TestStates.awaiting_question)
    await state.update_data(question_context=category)


# ============================================
# СКАЗКИ
# ============================================

async def show_tale(callback: CallbackQuery, state: FSMContext):
    """Показывает случайную сказку"""
    user_id = callback.from_user.id
    
    tale = tales.get_tale_for_issue("рост")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 ЕЩЁ СКАЗКУ", callback_data="show_tale")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="show_results")]
    ])
    
    await callback.message.edit_text(
        f"📖 *{tale['title']}*\n\n{tale['text'][:4000]}",
        parse_mode='Markdown',
        reply_markup=keyboard
    )


async def more_info(callback: CallbackQuery, state: FSMContext):
    """Показывает дополнительную информацию"""
    text = (
        f"🧠 *ТВОЙ ВТОРОЙ МОЗГ 8.0*\n\n"
        f"⚡ *В ЭТОЙ ВЕРСИИ:*\n"
        f"• 🧠 4 вектора × 6 уровней\n"
        f"• 🧠 4-этапный тест\n"
        f"• 🔄 Конфайнмент-моделирование\n"
        f"• 🧠 ГИПНОТЕРАПЕВТИЧЕСКИЙ МОДУЛЬ\n"
        f"• 🎙 Голосовые сообщения\n"
        f"• 🌍 Контекст (город, погода, время)\n\n"
        f"💬 *ОДНАЖДЫ ТЫ ПРОСТО ПЕРЕСТАНЕШЬ БЫТЬ ПРОБЛЕМОЙ ДЛЯ САМОГО СЕБЯ.*"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 СВЯЗАТЬСЯ С ПСИХОЛОГОМ", url="https://t.me/meysternlp")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="show_results")]
    ])
    
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=keyboard)


# ============================================
# СТАРТ И НАВИГАЦИЯ
# ============================================

async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Пользователь"
    
    user_names[user_id] = user_name
    
    await state.clear()
    
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
    
    stats.register_start(user_id)
    
    welcome_text = (
        f"👋 *Привет, {user_name}!*\n\n"
        f"Я — твой второй мозг. Персональный навигатор по жизни.\n\n"
        f"🔮 *Что я умею:*\n"
        f"• Помогать с отношениями, деньгами и самоощущением\n"
        f"• Строить твой психологический профиль\n"
        f"• Находить скрытые связи и петли в поведении\n\n"
        f"⏱ *Сначала нужно узнать тебя* — пройди тест (12 минут).\n\n"
        f"👇 *Выбери, с какой интонацией будем общаться:*"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔴 ЖЕСТКИЙ", callback_data="mode_hard"),
            InlineKeyboardButton(text="🟡 СРЕДНИЙ", callback_data="mode_medium"),
            InlineKeyboardButton(text="🟢 МЯГКИЙ", callback_data="mode_soft")
        ],
        [InlineKeyboardButton(text="📖 ЧТО ДАЕТ ТЕСТ", callback_data="show_benefits")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="ask_pretest")]
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode='Markdown')


async def choose_mode(callback: CallbackQuery, state: FSMContext, mode: str):
    """Выбор режима общения"""
    user_id = callback.from_user.id
    
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
    
    user_contexts[user_id].communication_mode = mode
    mode_info = COMMUNICATION_MODES[mode]
    
    await callback.message.edit_text(
        f"{mode_info['emoji']} *Режим выбран:* {mode_info['name']}\n\n"
        f"{mode_info['description']}\n\n"
        f"Теперь давай познакомимся поближе.",
        parse_mode='Markdown'
    )
    
    await asyncio.sleep(1)
    
    intro_text = (
        f"🧠 *ВИРТУАЛЬНЫЙ ПСИХОЛОГ - МАТРИЦА ПОВЕДЕНИЙ 4×6*\n\n"
        f"🔍 *ЧТО ТЕБЯ ЖДЕТ:*\n\n"
        f"**ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ**\n"
        f"Линза, через которую ты смотришь на мир.\n\n"
        f"**ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ**\n"
        f"Как ты обрабатываешь информацию.\n\n"
        f"**ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ**\n"
        f"Твои автоматические реакции.\n\n"
        f"**ЭТАП 4: ТОЧКА РОСТА**\n"
        f"Где находится рычаг изменений.\n\n"
        f"⏱ *Всего 12 минут*\n\n"
        f"👇 *Начинаем?*"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 НАЧАТЬ ТЕСТ", callback_data="start_test")]
    ])
    
    await callback.message.answer(intro_text, reply_markup=keyboard, parse_mode='Markdown')


async def show_benefits(callback: CallbackQuery):
    """Показывает преимущества теста"""
    text = (
        f"🔍 *ЧТО ТЫ УЗНАЕШЬ О СЕБЕ:*\n\n"
        f"🛡 **Как ты реагируешь на давление**\n\n"
        f"💰 **Твоя стратегия с деньгами**\n\n"
        f"🔍 **Как ты объясняешь себе неудачи**\n\n"
        f"🤝 **Твой паттерн в отношениях**\n\n"
        f"⚡ *После теста ты получишь:*\n"
        f"• Полный психологический портрет\n"
        f"• 🧠 Конфайнмент-модель\n"
        f"• 💡 Конкретные шаги для изменений\n"
        f"• 🎙 Голосовые ответы"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔪 НАЧАТЬ ТЕСТ", callback_data="start_test")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="back_to_intro")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')


async def back_to_intro(callback: CallbackQuery):
    """Возврат к начальному экрану"""
    user_id = callback.from_user.id
    user_name = user_names.get(user_id, callback.from_user.first_name or "друг")
    
    welcome_text = (
        f"👋 *Привет, {user_name}!*\n\n"
        f"👇 *Выбери, с какой интонацией будем общаться:*"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔴 ЖЕСТКИЙ", callback_data="mode_hard"),
            InlineKeyboardButton(text="🟡 СРЕДНИЙ", callback_data="mode_medium"),
            InlineKeyboardButton(text="🟢 МЯГКИЙ", callback_data="mode_soft")
        ],
        [InlineKeyboardButton(text="📖 ЧТО ДАЕТ ТЕСТ", callback_data="show_benefits")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="ask_pretest")]
    ])
    
    await callback.message.edit_text(welcome_text, reply_markup=keyboard, parse_mode='Markdown')


async def ask_pretest(callback: CallbackQuery, state: FSMContext):
    """Вопрос до теста"""
    await callback.message.edit_text(
        "❓ *Задай свой вопрос*\n\n"
        "Я отвечу, но без твоего профиля ответ будет общим. "
        "После теста смогу дать персональную рекомендацию.\n\n"
        "_Напиши вопрос текстом или голосом._",
        parse_mode='Markdown'
    )
    
    await state.set_state(TestStates.pretest_question)


async def handle_pretest_question(message: Message, state: FSMContext):
    """Обработка вопроса до теста"""
    user_id = message.from_user.id
    user_name = user_names.get(user_id, message.from_user.first_name or "друг")
    context_obj = user_contexts.get(user_id)
    mode = context_obj.communication_mode if context_obj else "medium"
    
    question = message.text
    
    data = await state.get_data()
    history = data.get("history", [])
    history.append({
        "role": "user",
        "text": question,
        "timestamp": datetime.now().isoformat(),
        "type": "pretest"
    })
    await state.update_data(history=history)
    
    thinking = await message.answer("🤔 *Думаю...*", parse_mode='Markdown')
    await asyncio.sleep(1)
    
    mode_prompt = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["medium"])["prompt"]
    
    prompt = f"""Ответь на вопрос человека. Ты еще не знаешь его профиль, поэтому ответь общо, но полезно.
Затем мягко предложи пройти тест для точного ответа.

Вопрос: {question}

Стиль: {mode_prompt}"""
    
    response = await call_deepseek(prompt, max_tokens=400)
    
    if not response:
        response = f"Спасибо за вопрос, {user_name}. Чтобы ответить точнее, мне нужно знать твой профиль. Пройди тест — это займёт 12 минут."
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔪 НАЧАТЬ ТЕСТ", callback_data="start_test")],
        [InlineKeyboardButton(text="❓ ЕЩЁ ВОПРОС", callback_data="ask_pretest")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="back_to_intro")]
    ])
    
    await thinking.delete()
    await message.answer(response, reply_markup=keyboard, parse_mode='Markdown')
    
    await state.clear()


async def handle_ask_question(callback: CallbackQuery, state: FSMContext):
    """Обработка запроса на вопрос после теста"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="show_results")]
    ])
    await callback.message.edit_text(
        "✏️ *ЗАДАЙ ВОПРОС*\n\n"
        "Напиши, что тебя беспокоит. Я помню твой профиль.",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    await state.set_state(TestStates.awaiting_question)


async def handle_question_message(message: Message, state: FSMContext):
    """Обработка вопроса после теста"""
    user_id = message.from_user.id
    data = await state.get_data()
    
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    thinking = await message.answer("🤔 *Думаю над ответом...*", parse_mode='Markdown')
    
    context_obj = user_contexts.get(user_id)
    user_name = user_names.get(user_id, message.from_user.first_name or "друг")
    mode = context_obj.communication_mode if context_obj else "medium"
    
    # Используем гипнотический оркестратор
    hypno_context = {
        'confinement_model': data.get('confinement_model'),
        'scores': scores,
        'history': data.get('history', [])[-5:]
    }
    
    response = hypno.process(user_id, message.text, hypno_context)
    
    history = data.get("history", [])
    history.append({
        "role": "user", 
        "text": message.text, 
        "timestamp": datetime.now().isoformat()
    })
    history.append({
        "role": "assistant", 
        "text": response, 
        "timestamp": datetime.now().isoformat()
    })
    await state.update_data(history=history)
    
    await thinking.delete()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="smart_questions")],
        [InlineKeyboardButton(text="🧠 К портрету", callback_data="show_results")],
        [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")]
    ])
    
    await message.answer(
        f"🧠 *Ответ*\n\n{response}",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    
    audio_data = await text_to_speech(response, mode)
    if audio_data:
        audio_file = BufferedInputFile(audio_data, filename="response.ogg")
        await message.answer_voice(
            audio_file,
            caption="🎙 *Голосовой ответ*",
            parse_mode='Markdown'
        )
    
    await state.set_state(TestStates.results)


async def handle_voice_message(message: Message, state: FSMContext):
    """Обработка голосового сообщения"""
    user_id = message.from_user.id
    data = await state.get_data()
    
    if not is_test_completed(data):
        await message.answer(
            "🎙 *Голосовые сообщения доступны только после завершения теста*",
            parse_mode='Markdown'
        )
        return
    
    status_msg = await message.answer("🎤 *Распознаю речь...*", parse_mode='Markdown')
    
    temp_file = None
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
                "Попробуйте еще раз или напишите текстом.",
                parse_mode='Markdown'
            )
            return
        
        scores = {}
        for k in VECTORS:
            levels = data.get("behavioral_levels", {}).get(k, [])
            scores[k] = sum(levels) / len(levels) if levels else 3.0
        
        context_obj = user_contexts.get(user_id)
        mode = context_obj.communication_mode if context_obj else "medium"
        
        # Используем гипнотический оркестратор
        hypno_context = {
            'confinement_model': data.get('confinement_model'),
            'scores': scores,
            'history': data.get('history', [])[-5:]
        }
        
        response = hypno.process(user_id, recognized_text, hypno_context)
        
        history = data.get("history", [])
        history.append({
            "role": "user", 
            "text": recognized_text, 
            "timestamp": datetime.now().isoformat()
        })
        history.append({
            "role": "assistant", 
            "text": response, 
            "timestamp": datetime.now().isoformat()
        })
        await state.update_data(history=history)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="smart_questions")],
            [InlineKeyboardButton(text="🧠 К портрету", callback_data="show_results")],
            [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")]
        ])
        
        await status_msg.edit_text(
            f"📝 *Вы сказали:*\n_{recognized_text}_\n\n"
            f"*Ответ:*\n{response}",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        audio_data = await text_to_speech(response, mode)
        if audio_data:
            audio_file = BufferedInputFile(audio_data, filename="response.ogg")
            await message.answer_voice(
                audio_file,
                caption="🎙 *Голосовой ответ*",
                parse_mode='Markdown'
            )
    
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {e}")
        await status_msg.edit_text(
            "❌ *Произошла ошибка*\n\n"
            "Попробуйте еще раз или напишите текстом.",
            parse_mode='Markdown'
        )


async def handle_unknown_message(message: Message):
    """Обработка неизвестных сообщений"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
        [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions")]
    ])
    await message.answer(
        "Используй кнопки для навигации:",
        reply_markup=keyboard
    )


# ============================================
# CALLBACK ХЕНДЛЕР
# ============================================

async def callback_handler(callback: CallbackQuery, state: FSMContext):
    """Основной обработчик callback'ов"""
    data = callback.data
    
    try:
        # Режимы
        if data == "mode_hard":
            await choose_mode(callback, state, "hard")
        elif data == "mode_medium":
            await choose_mode(callback, state, "medium")
        elif data == "mode_soft":
            await choose_mode(callback, state, "soft")
        
        # Навигация
        elif data == "show_benefits":
            await show_benefits(callback)
        elif data == "back_to_intro":
            await back_to_intro(callback)
        elif data == "ask_pretest":
            await ask_pretest(callback, state)
        
        # Категории помощи
        elif data.startswith("help_cat_"):
            category = data.replace("help_cat_", "")
            await handle_help_category(callback, state, category)
        
        # Тест - начало
        elif data == "start_test":
            await show_stage_1_intro(callback, state)
        
        # Этап 1
        elif data == "start_stage_1":
            await start_stage_1(callback, state)
        elif data.startswith("stage1_"):
            await handle_stage_1_answer(callback, state)
        
        # Этап 2
        elif data == "show_stage_2_intro":
            await show_stage_2_intro(callback, state)
        elif data == "start_stage_2":
            await start_stage_2(callback, state)
        elif data.startswith("stage2_"):
            await handle_stage_2_answer(callback, state)
        
        # Этап 3
        elif data == "show_stage_3_intro":
            await show_stage_3_intro(callback, state)
        elif data == "start_stage_3":
            await start_stage_3(callback, state)
        elif data.startswith("stage3_"):
            await handle_stage_3_answer(callback, state)
        
        # Этап 4
        elif data == "show_stage_4_intro":
            await show_stage_4_intro(callback, state)
        elif data == "start_stage_4":
            await start_stage_4(callback, state)
        elif data.startswith("stage4_"):
            await handle_stage_4_answer(callback, state)
        
        # Результаты
        elif data == "show_results":
            await show_results_screen(callback, state)
        elif data == "ai_analysis":
            await show_ai_analysis(callback, state)
        elif data == "ai_recommendations":
            await show_ai_recommendations(callback, state)
        elif data == "smart_questions":
            await show_smart_questions(callback, state)
        elif data.startswith("ask_"):
            state_data = await state.get_data()
            idx = int(data.split("_")[1]) - 1
            questions = state_data.get("smart_questions", [])
            if 0 <= idx < len(questions):
                await handle_smart_question(callback, state, questions[idx])
        elif data == "ask_question":
            await handle_ask_question(callback, state)
        elif data == "show_help":
            await show_help(callback, state)
        elif data == "show_tale":
            await show_tale(callback, state)
        elif data == "more_info":
            await more_info(callback, state)
        elif data == "restart_test":
            await state.clear()
            await back_to_intro(callback)
    
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            logger.info(f"Ignored 'message not modified' error")
        else:
            raise
    
    await callback.answer()


# ============================================
# КОМАНДЫ АДМИНИСТРАТОРОВ
# ============================================

async def cmd_stats(message: Message):
    """Команда /stats"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещен")
        return
    
    await message.answer(stats.get_stats_text(), parse_mode='Markdown')


async def cmd_apistatus(message: Message):
    """Команда /apistatus"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещен")
        return
    
    deepseek_status = "✅ работает" if DEEPSEEK_API_KEY else "❌ не настроен"
    deepgram_status = "✅ работает" if DEEPGRAM_API_KEY else "❌ не настроен"
    yandex_status = "✅ работает" if YANDEX_API_KEY else "❌ не настроен"
    weather_status = "✅ работает" if OPENWEATHER_API_KEY else "❌ не настроен"
    
    text = f"📊 **Статус API:**\n\n"
    text += f"• DeepSeek: {deepseek_status}\n"
    text += f"• Deepgram: {deepgram_status}\n"
    text += f"• Yandex TTS: {yandex_status}\n"
    text += f"• OpenWeather: {weather_status}\n\n"
    
    await message.answer(text, parse_mode='Markdown')


async def cmd_test_yandex(message: Message):
    """Команда /test_yandex"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Только для администраторов")
        return
    
    test_text = "Привет! Это тестовое голосовое сообщение."
    status = await message.answer("🎧 Тестирую Yandex TTS...")
    
    audio = await text_to_speech(test_text, "medium")
    
    if audio:
        audio_file = BufferedInputFile(audio, filename="test.ogg")
        await message.answer_voice(
            audio_file,
            caption="✅ Yandex SpeechKit работает!"
        )
        await status.delete()
    else:
        await status.edit_text("❌ Yandex SpeechKit не работает.")


async def cmd_test_voices(message: Message):
    """Команда /test_voices"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Только для администраторов")
        return
    
    if not YANDEX_API_KEY:
        await message.answer("❌ YANDEX_API_KEY не настроен")
        return
    
    test_text = "Ну, допустим, вы действительно так считаете."
    status = await message.answer("🎧 Тестирую голоса...")
    
    modes_to_test = [
        ("hard", "🔴 Жесткий режим"),
        ("medium", "🟡 Средний режим"),
        ("soft", "🟢 Мягкий режим"),
    ]
    
    for mode_key, description in modes_to_test:
        audio = await text_to_speech(test_text, mode_key)
        if audio:
            audio_file = BufferedInputFile(audio, filename=f"{mode_key}.ogg")
            await message.answer_voice(
                audio_file,
                caption=f"🎙 *{description}*",
                parse_mode='Markdown'
            )
        await asyncio.sleep(0.5)
    
    await status.delete()


async def cmd_tale(message: Message):
    """Команда /tale"""
    user_id = message.from_user.id
    data = user_data.get(user_id, {})
    
    if not is_test_completed(data):
        await message.answer("Сначала пройдите тест")
        return
    
    text = message.text.replace('/tale', '').strip()
    if not text:
        text = "страх"
    
    tale = tales.get_tale_for_issue(text)
    
    if tale:
        await message.answer(
            f"📖 *{tale['title']}*\n\n{tale['text'][:4000]}",
            parse_mode='Markdown'
        )
    else:
        await message.answer("Сказка не найдена")


# ============================================
# ЗАПУСК БОТА
# ============================================

async def check_api_on_startup():
    """Проверка API при запуске"""
    logger.info("Проверяю DeepSeek API...")
    response = await call_deepseek("Ответь 'OK' одним словом", max_tokens=10)
    if response:
        logger.info("✅ DeepSeek API работает")
    else:
        logger.warning("❌ DeepSeek API не отвечает")


async def main():
    """Главная функция"""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN не найден")
        print("❌ Ошибка: TELEGRAM_TOKEN не найден в .env файле")
        return
    
    storage = MemoryStorage()
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=storage)
    
    task_manager.set_bot(bot)
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Вебхук удален")
    
    # Регистрируем обработчики команд
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_stats, Command("stats"))
    dp.message.register(cmd_apistatus, Command("apistatus"))
    dp.message.register(cmd_test_yandex, Command("test_yandex"))
    dp.message.register(cmd_test_voices, Command("test_voices"))
    dp.message.register(cmd_tale, Command("tale"))
    
    # Регистрируем обработчики сообщений с состояниями
    dp.message.register(handle_pretest_question, TestStates.pretest_question)
    dp.message.register(handle_question_message, TestStates.awaiting_question)
    dp.message.register(handle_voice_message, F.voice)
    dp.message.register(handle_unknown_message)
    
    # Регистрируем callback хендлер
    dp.callback_query.register(callback_handler)
    
    if DEEPSEEK_API_KEY:
        logger.info("DeepSeek API ключ найден")
        asyncio.create_task(check_api_on_startup())
    else:
        logger.warning("DeepSeek API ключ не найден")
    
    logger.info("Бот запущен...")
    print("\n" + "="*80)
    print("🚀 ВИРТУАЛЬНЫЙ ПСИХОЛОГ - МАТРИЦА ПОВЕДЕНИЙ 4×6 v8.0")
    print("="*80)
    print(f"👤 Ваш Telegram ID: {ADMIN_IDS[0] if ADMIN_IDS else 'не указан'}")
    print("🎙 Распознавание: " + ("✅ Deepgram" if DEEPGRAM_API_KEY else "❌ нет"))
    print("🎙 Синтез речи: " + ("✅ Yandex" if YANDEX_API_KEY else "❌ нет"))
    print("🌍 Погода: " + ("✅ OpenWeather" if OPENWEATHER_API_KEY else "❌ нет"))
    print("="*80 + "\n")
    
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    os.makedirs("stats", exist_ok=True)
    asyncio.run(main())
