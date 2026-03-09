#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ВИРТУАЛЬНЫЙ ПСИХОЛОГ - МАТРИЦА ПОВЕДЕНИЙ 4×6
ВЕРСИЯ 8.5: 5 ЭТАПОВ → ОДИН ФИНАЛЬНЫЙ ПРОФИЛЬ
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
from typing import Optional, Dict, List, Any, Tuple, Union
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
    STAGE_1_QUESTIONS,
    STAGE_2_QUESTIONS,
    STAGE_3_QUESTIONS,
    STAGE_4_QUESTIONS,
    STAGE_5_QUESTIONS,
    STAGE_2_SCORING,
    CLARIFYING_QUESTIONS,
    DISCREPANCY_QUESTIONS,
    get_stage1_question,
    get_stage1_total,
    get_stage2_question,
    get_stage2_total,
    get_stage2_score,
    get_stage3_question,
    get_stage3_total,
    get_stage4_question,
    get_stage4_total,
    get_stage5_question,
    get_stage5_total,
    analyze_stage5_results,
    get_deep_patterns_description,
    get_clarifying_questions,
    get_question_text,
    get_question_options,
    get_option_text,
    get_option_value,
    map_to_stage3_feedback_level
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
    stage_5 = State()
    results = State()
    awaiting_question = State()
    pretest_question = State()
    awaiting_context = State()
    mode_selection = State()
    viewing_confinement = State()
    viewing_intervention = State()


# ============================================
# РЕЖИМЫ ОБЩЕНИЯ
# ============================================

COMMUNICATION_MODES = {
    "coach": {
        "name": "КОУЧ",
        "display_name": "🔮 КОУЧ",
        "description": "Партнёрский стиль: задаю вопросы, помогаю найти ответы внутри себя. Без давления, но с фокусом на результат.",
        "prompt": "Ты коуч, который задаёт открытые вопросы, помогает клиенту осознать свои цели и найти ресурсы. Ты не даёшь готовых ответов, а направляешь. Используй больше вопросов, поддерживай, но не навязывай.",
        "emoji": "🔮",
        "voice_emotion": "neutral",
        "voice": "filipp",
        "question_style": "open"
    },
    "friend": {
        "name": "ДРУГ",
        "display_name": "💚 ДРУГ",
        "description": "Тёплый, поддерживающий стиль. Как близкий человек, который выслушает и поймёт. Для работы с чувствами и самооценкой.",
        "prompt": "Ты близкий друг, который принимает без осуждения. Говори тепло, с эмпатией. Используй больше отражения чувств, поддерживай, показывай, что ты рядом. Можно использовать личные обращения.",
        "emoji": "💚",
        "voice_emotion": "good",
        "voice": "ermil",
        "question_style": "reflective"
    },
    "trainer": {
        "name": "ТРЕНЕР",
        "display_name": "⚡ ТРЕНЕР",
        "description": "Структурированный, требовательный стиль. Чёткие инструкции, конкретные шаги, фокус на действиях. Для достижения целей.",
        "prompt": "Ты спортивный тренер или наставник, который даёт чёткие инструкции. Говори коротко, по делу, без воды. Фокус на действиях, дисциплине, результате. Можно использовать командный тон.",
        "emoji": "⚡",
        "voice_emotion": "strict",
        "voice": "filipp",
        "question_style": "closed"
    }
}

# Для обратной совместимости со старыми режимами
COMMUNICATION_MODES["hard"] = COMMUNICATION_MODES["trainer"]
COMMUNICATION_MODES["medium"] = COMMUNICATION_MODES["coach"]
COMMUNICATION_MODES["soft"] = COMMUNICATION_MODES["friend"]


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
        self.birth_date = None
        self.name = None
        self.communication_mode = "coach"
        self.last_context_update = None
        self.weather_cache = {}
        self.weather_cache_time = None
        self.season = None
        self.moon_phase = None
        self.holidays_today = []
        self.working_hours = True
        self.user_preferences = {}
        self.awaiting_context = None
        
    def get_greeting(self, user_name: str = "") -> str:
        """Персонализированное приветствие с учётом времени суток, пола и погоды"""
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
        
        address = self.get_address()
        
        base = f"{greeting}"
        if user_name:
            base += f", {user_name}"
        if address and self.communication_mode == "friend":
            base += f" {address}"
        base += "!"
        
        if self.weather_cache:
            temp = self.weather_cache.get('temp')
            icon = self.weather_cache.get('icon', '')
            
            if temp is not None:
                if temp < 0:
                    weather_note = f"❄️ На улице морозно, {temp}°C. Одевайся теплее!"
                elif temp < 10:
                    weather_note = f"☁️ Прохладно, {temp}°C. Хорошего дня!"
                elif temp < 20:
                    weather_note = f"🍃 Свежо, {temp}°C. Отличная погода!"
                elif temp < 30:
                    weather_note = f"☀️ Тепло, {temp}°C. Прекрасный день!"
                else:
                    weather_note = f"🔥 Жарко, {temp}°C. Пей больше воды!"
                
                base += f"\n\n{icon} {weather_note}"
        
        return base
    
    def get_address(self) -> str:
        """Возвращает обращение в зависимости от пола"""
        if self.gender == "male":
            return "братишка"
        elif self.gender == "female":
            return "сестрёнка"
        else:
            return "родной"
    
    async def ask_for_context(self) -> Tuple[Optional[str], Optional[InlineKeyboardMarkup]]:
        """Возвращает первый вопрос для сбора контекста"""
        if not self.city:
            self.awaiting_context = "city"
            return "🌆 В каком городе ты находишься? (Это нужно для погоды и времени)", InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_context")]
            ])
        
        if not self.gender:
            self.awaiting_context = "gender"
            return "👤 Укажи свой пол (М или Ж)", InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👨 Мужской", callback_data="set_gender_male")],
                [InlineKeyboardButton(text="👩 Женский", callback_data="set_gender_female")],
                [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_context")]
            ])
        
        if not self.age:
            self.awaiting_context = "age"
            return "📅 Сколько тебе лет? (Напиши число)", InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_context")]
            ])
        
        self.awaiting_context = None
        return None, None
    
    async def process_context_answer(self, text: str) -> Tuple[bool, Optional[str], Optional[InlineKeyboardMarkup]]:
        """Обрабатывает ответ на контекстный вопрос"""
        if not self.awaiting_context:
            return False, None, None
        
        field = self.awaiting_context
        
        if field == "city":
            self.city = text.strip()
            self.awaiting_context = None
            await self.update_weather()
            question, keyboard = await self.ask_for_context()
            return True, question, keyboard
                
        elif field == "gender":
            gender_lower = text.lower().strip()
            if gender_lower in ['м', 'муж', 'мужчина', 'male']:
                self.gender = "male"
            elif gender_lower in ['ж', 'жен', 'женщина', 'female']:
                self.gender = "female"
            else:
                self.gender = "other"
            
            self.awaiting_context = None
            question, keyboard = await self.ask_for_context()
            return True, question, keyboard
                
        elif field == "age":
            try:
                self.age = int(text.strip())
                self.awaiting_context = None
                question, keyboard = await self.ask_for_context()
                return True, question, keyboard
            except ValueError:
                return False, "Пожалуйста, введите число (например: 25)", None
        
        return False, None, None
    
    async def handle_gender_callback(self, gender: str) -> Tuple[Optional[str], Optional[InlineKeyboardMarkup]]:
        """Обрабатывает выбор пола через callback"""
        self.gender = gender
        self.awaiting_context = None
        question, keyboard = await self.ask_for_context()
        return question, keyboard
    
    def get_day_context(self) -> dict:
        """Возвращает контекст текущего дня"""
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
        context_parts.append(f"📅 Сегодня {day_context['weekday']}, {day_context['day']} {day_context['month']}, {day_context['time_str']}")
        
        if self.city:
            context_parts.append(f"📍 Город: {self.city}")
        
        age_stage = self.get_age_stage()
        if age_stage:
            gender_str = ""
            if self.gender == "male":
                gender_str = "Братишка"
            elif self.gender == "female":
                gender_str = "Сестрёнка"
            
            if gender_str:
                context_parts.append(f"👤 {gender_str}, {self.age} лет — {age_stage}")
            else:
                context_parts.append(f"👤 Возраст: {self.age} — {age_stage}")
        
        if day_context['is_weekend']:
            context_parts.append("🏖 Сегодня выходной")
        elif 9 <= day_context['hour'] < 18:
            context_parts.append("💼 Рабочее время")
        else:
            context_parts.append("🏡 Личное время")
        
        season = self.get_season()
        if season:
            context_parts.append(f"🍂 Сезон: {season}")
        
        moon = self.get_moon_phase()
        if moon:
            context_parts.append(f"🌙 {moon}")
        
        return "\n".join(context_parts)
    
    def get_prompt_context(self) -> str:
        """Возвращает контекст для вставки в промпт AI"""
        lines = []
        
        if self.gender:
            gender_text = "мужской" if self.gender == "male" else "женский" if self.gender == "female" else "другой"
            lines.append(f"Пол пользователя: {gender_text}")
            lines.append(f"Обращение: {self.get_address() if self.communication_mode == 'friend' else 'вы'}")
        if self.age:
            lines.append(f"Возраст: {self.age} лет ({self.get_age_stage()})")
        if self.city:
            lines.append(f"Город: {self.city}")
        
        day = self.get_day_context()
        lines.append(f"Время: {day['time_str']}, {day['weekday']}" + (" (выходной)" if day['is_weekend'] else ""))
        
        if self.weather_cache:
            lines.append(f"Погода: {self.weather_cache['icon']} {self.weather_cache['description']}, {self.weather_cache['temp']}°C")
            if self.season:
                lines.append(f"Сезон: {self.season}")
        
        moon = self.get_moon_phase()
        if moon:
            lines.append(f"Луна: {moon}")
        
        return "\n".join(lines)
    
    async def update_weather(self):
        """Обновляет погоду через OpenWeatherMap API с обработкой ошибок"""
        if not self.city or not OPENWEATHER_API_KEY:
            return False
        
        if self.weather_cache and self.weather_cache_time:
            if (datetime.now() - self.weather_cache_time).seconds < 3600:
                return True
        
        url = f"http://api.openweathermap.org/data/2.5/weather?q={self.city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
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
                            "description": data['weather'][0]['description'],
                            "humidity": data['main']['humidity'],
                            "wind": round(data['wind']['speed']),
                            "icon": icon,
                            "pressure": data['main']['pressure']
                        }
                        self.weather_cache_time = datetime.now()
                        self.update_season()
                        return True
                    else:
                        logger.error(f"Ошибка OpenWeather API: {response.status}")
                        return False
        except asyncio.TimeoutError:
            logger.error("Таймаут при получении погоды")
            return False
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети при получении погоды: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении погоды: {e}")
            return False
    
    def update_season(self):
        """Определяет сезон на основе даты и температуры"""
        now = datetime.now()
        month = now.month
        temp = self.weather_cache.get('temp', 0) if self.weather_cache else 0
        
        if month in [12, 1, 2]:
            if temp < -10:
                self.season = "суровая зима"
            elif temp < 0:
                self.season = "зима"
            else:
                self.season = "мягкая зима"
        elif month in [3, 4, 5]:
            if temp < 5:
                self.season = "холодная весна"
            elif temp < 15:
                self.season = "весна"
            else:
                self.season = "тёплая весна"
        elif month in [6, 7, 8]:
            if temp > 25:
                self.season = "жаркое лето"
            else:
                self.season = "лето"
        else:
            if temp < 5:
                self.season = "холодная осень"
            elif temp < 15:
                self.season = "осень"
            else:
                self.season = "тёплая осень"
    
    def get_season(self) -> str:
        """Возвращает текущий сезон"""
        return self.season
    
    def get_moon_phase(self) -> str:
        """Определяет фазу луны (упрощённо)"""
        now = datetime.now()
        day_of_month = now.day
        
        if day_of_month < 4:
            return "новолуние 🌑"
        elif day_of_month < 11:
            return "растущая луна 🌒"
        elif day_of_month < 18:
            return "полнолуние 🌕"
        elif day_of_month < 25:
            return "убывающая луна 🌘"
        else:
            return "старая луна 🌚"
    
    def get_weather_recommendation(self, weather: dict) -> str:
        """Возвращает рекомендацию на основе погоды"""
        if not weather:
            return ""
        
        temp = weather['temp']
        desc = weather['description']
        
        if "дождь" in desc or "ливень" in desc:
            return "Возьми зонт ☔️"
        elif "снег" in desc:
            return "Осторожно на дорогах ❄️"
        elif temp > 25:
            return "Пей больше воды 💧"
        elif temp < -10:
            return "Одевайся очень тепло 🧣"
        elif temp < 0:
            return "Не забудь шапку 🧤"
        
        return ""
    
    def get_age_stage(self) -> str:
        """Возвращает возрастной этап"""
        if not self.age:
            return ""
        
        if self.age < 18:
            return "подростковый возраст — время поиска себя"
        elif self.age < 25:
            return "молодость — время проб и ошибок"
        elif self.age < 35:
            return "активная зрелость"
        elif self.age < 45:
            return "расцвет — время реализации"
        elif self.age < 55:
            return "мудрая зрелость"
        elif self.age < 65:
            return "золотой возраст"
        else:
            return "возраст гармонии и мудрости"


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
    """Генерирует уникальный callback для защиты от повторных нажатий"""
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
    """Рассчитывает финальный уровень на основе мышления и поведения"""
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
    """Определяет порядок приоритетов для уязвимых мест"""
    if not scores:
        return ["ТФ", "СБ", "УБ", "ЧВ"]
    tf = level(scores.get("ТФ", 3))
    if tf <= 2:
        rest = sorted([(k, v) for k, v in scores.items() if k != "ТФ"], key=lambda x: x[1])
        return ["ТФ"] + [r[0] for r in rest]
    else:
        return [k for k, _ in sorted(scores.items(), key=lambda x: x[1])]

def is_test_completed(user_data: dict) -> bool:
    """Проверяет, завершен ли тест"""
    required_fields = ["perception_type", "thinking_level", "behavioral_levels", "dilts_counts", "deep_patterns"]
    for field in required_fields:
        if field not in user_data:
            return False
    
    behavioral_levels = user_data.get("behavioral_levels", {})
    for vector in VECTORS:
        if len(behavioral_levels.get(vector, [])) < 1:
            return False
    
    return True

def should_be_ironic(text: str) -> bool:
    """Проверяет, должен ли ответ быть ироничным"""
    ironic_markers = [
        "очевидно", "разумеется", "конечно", "естественно",
        "неужели", "серьёзно", "правда?", "интересно",
        "ха", "хм", "ну-ну", "ага"
    ]
    return any(marker in text.lower() for marker in ironic_markers)

def needs_clarification(avg: float) -> bool:
    """Проверяет, нужно ли уточнение"""
    CLARIFICATION_ZONES = [1.49, 2.00, 2.50, 3.00, 3.50]
    CLARIFICATION_MARGIN = 0.12
    return any(abs(avg - b) <= CLARIFICATION_MARGIN for b in CLARIFICATION_ZONES)

def check_consistency(scores_list: list) -> bool:
    """Проверяет согласованность ответов"""
    if len(scores_list) < 4:
        return True
    avg = mean(scores_list)
    variance = sum((x - avg) ** 2 for x in scores_list) / len(scores_list)
    std_dev = variance ** 0.5
    return std_dev <= 1.3

def format_box_text(text: str, width: int = 58) -> str:
    """Форматирует текст для вставки в бокс с переносом строк"""
    if not text:
        return " " * width
    
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        if len(current_line) + len(word) + 1 <= width:
            current_line += (" " + word if current_line else word)
        else:
            lines.append(current_line.ljust(width))
            current_line = word
    
    if current_line:
        lines.append(current_line.ljust(width))
    
    return "\n".join(lines)


def calculate_profile_confidence(profile: dict) -> float:
    """Рассчитывает уверенность в профиле"""
    confidence = 0.5  # базовое значение
    
    # Фактор 1: количество пройденных этапов
    stages_done = 0
    if profile.get("perception_type"):
        stages_done += 1
    if profile.get("thinking_level"):
        stages_done += 1
    if profile.get("behavioral_levels"):
        stages_done += 1
    if profile.get("dilts_counts"):
        stages_done += 1
    if profile.get("deep_patterns"):
        stages_done += 1
    
    confidence += stages_done * 0.1
    
    return min(1.0, confidence)


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

async def text_to_speech(text: str, mode: str = "coach") -> Optional[bytes]:
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
    
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    voice = mode_config.get("voice", "filipp")
    emotion = mode_config.get("voice_emotion", "neutral")
    
    if mode == "coach":
        speed = "1.0"
    elif mode == "friend":
        speed = "0.9"
    elif mode == "trainer":
        speed = "1.1"
    else:
        speed = "1.0"
    
    data = {
        "text": clean_text,
        "voice": voice,
        "emotion": emotion,
        "speed": speed,
        "format": "oggopus",
    }
    
    try:
        logger.info(f"🎧 Отправка в Яндекс TTS: голос {voice}, эмоция {emotion}, скорость {speed}")
        
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


async def generate_response_with_full_context(user_id: int, user_message: str, state_data: dict) -> str:
    """Генерирует ответ с учётом полного контекста пользователя"""
    
    user_context = user_contexts.get(user_id)
    
    mode = "coach"
    if user_context:
        mode = user_context.communication_mode
    elif state_data.get("communication_mode"):
        mode = state_data["communication_mode"]
    
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    profile_data = state_data.get("profile_data", {})
    profile_code = profile_data.get('display_name', 'не определен')
    
    full_context = ""
    if user_context:
        full_context = user_context.get_prompt_context()
    
    address = user_context.get_address() if user_context and mode == "friend" else "вы"
    
    history = state_data.get("history", [])
    history_text = ""
    for entry in history[-5:]:
        role = "Клиент" if entry["role"] == "user" else "Психолог"
        history_text += f"{role}: {entry['text']}\n"
    
    base_prompt = f"""Ты — Фреди, виртуальный психолог, оцифрованная версия Андрея Мейстера.
Ты общаешься с пользователем как с {address}.

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ: {profile_code}

КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ:
{full_context}

РЕЖИМ ОБЩЕНИЯ: {mode_config['display_name']}
{mode_config['description']}

СТИЛЬ: {mode_config['prompt']}

ИСТОРИЯ ДИАЛОГА:
{history_text}

СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ: {user_message}

ОТВЕТ (учитывая пол, возраст, погоду, время суток и стиль {mode_config['name']}):"""
    
    response = await call_deepseek(base_prompt, max_tokens=500)
    
    if not response:
        if user_context and user_context.weather_cache:
            weather = user_context.weather_cache
            if weather['temp'] < 0 and "грусть" in user_message.lower():
                response = f"Слушай, {address}, погода {weather['icon']} действительно может влиять на настроение. Расскажи подробнее?"
            else:
                response = f"Я слышу вас. Что именно вас беспокоит?"
        else:
            response = f"Я слышу вас. Расскажите подробнее?"
    
    return response


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
    
    def build_from_profile(self, scores: dict, history: list = None, user_context: UserContext = None) -> 'ConfinementModel9':
        """Строит модель из психологического профиля"""
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
        
        # Добавляем возрастные особенности
        if user_context and user_context.age:
            self._apply_age_adjustments(user_context.age)
        
        return self
    
    def _apply_age_adjustments(self, age: int):
        """Корректирует модель с учётом возраста"""
        if age < 25:
            if self.elements[5]:
                self.elements[5].description += " Поиск себя — нормально для твоего возраста."
        elif age > 50:
            if self.elements[9]:
                self.elements[9].description += " Это может быть связано с жизненным опытом."
    
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
        vectors = []
        for eid in effect_ids:
            elem = self.elements[eid]
            if elem and elem.vector:
                vectors.append(elem.vector)
        
        if 'СБ' in vectors and 'ТФ' in vectors and 'УБ' in vectors:
            return self._create_identity_element()
        return self._create_belief_element('common')
    
    def _create_identity_element(self) -> ConfinementElement:
        weakest = min(self.source_scores.items(), key=lambda x: level(x[1]))
        vector, score = weakest
        lvl = level(score)
        profile = LEVEL_PROFILES.get(vector, {}).get(lvl, {})
        
        element = ConfinementElement(5, f"🎭 Идентичность")
        element.description = profile.get('archetype_desc', "То, кем ты себя считаешь")
        element.element_type = ConfinementElement.TYPE_COMMON_CAUSE
        element.archetype = profile.get('archetype')
        element.strength = 0.8
        element.vak = 'visual'
        return element
    
    def _create_belief_element(self, belief_type: str) -> ConfinementElement:
        beliefs = {'common': "Есть вещи, которые я не могу изменить"}
        element = ConfinementElement(5, f"💭 Убеждение")
        element.description = beliefs.get(belief_type, beliefs['common'])
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
        loop2 = self._check_cycle([5,6,7,8,5])
        if loop2:
            self.loops.append({
                'elements': loop2, 'type': 'identity_system_environment',
                'description': 'Идентичность → система → среда → идентичность',
                'strength': self._calculate_loop_strength(loop2)
            })
        loop3 = self._check_cycle([1,2,3,4,9,1])
        if loop3:
            self.loops.append({
                'elements': loop3, 'type': 'full_cycle',
                'description': 'Полный цикл самоподдержания',
                'strength': self._calculate_loop_strength(loop3)
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
# ФУНКЦИИ ДЛЯ РАБОТЫ С КОНФАЙНМЕНТ-МОДЕЛЬЮ
# ============================================

def format_confinement_report(model: ConfinementModel9) -> str:
    """Форматирует отчёт по конфайнмент-модели"""
    if not model.elements[1]:
        return "Модель ещё не построена"
    
    lines = []
    lines.append("🧠 *КОНФАЙНМЕНТ-МОДЕЛЬ*\n")
    
    # Результат
    result = model.elements[1]
    lines.append(f"🎯 *Главный симптом:* {result.description}\n")
    
    # Ключевой конфайнмент
    if model.key_confinement:
        elem = model.key_confinement['element']
        lines.append(f"⛓ *Ключевое ограничение:*")
        lines.append(f"Элемент {model.key_confinement['id']}: {elem.name}")
        lines.append(f"{elem.description[:100]}...\n")
    
    # Петли
    if model.loops:
        strongest = max(model.loops, key=lambda x: x['strength'])
        lines.append(f"🔄 *Главная петля:*")
        lines.append(strongest['description'])
        lines.append(f"Сила: {strongest['strength']:.1%}\n")
    
    # Замыкание
    closure_status = "✅ замкнута" if model.is_closed else "🔄 не замкнута"
    lines.append(f"📊 *Система:* {closure_status}")
    
    return "\n".join(lines)


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
        
        for tid in list(self.tasks.keys()):
            if tid.startswith(f"motivation_{user_id}"):
                self.tasks[tid]["task"].cancel()
                del self.tasks[tid]
        
        async def send_motivation():
            await asyncio.sleep(delay_minutes * 60)
            if self.bot_instance:
                try:
                    if scores:
                        min_vector = min(scores.items(), key=lambda x: level(x[1]))
                        vector, score = min_vector
                        lvl = level(score)
                        profile = LEVEL_PROFILES.get(vector, {}).get(lvl, {})
                        
                        context = user_contexts.get(user_id)
                        address = context.get_address() if context else "друг"
                        
                        message_text = (
                            f"🧠 *ЧЕРЕЗ {delay_minutes} МИНУТ ПОСЛЕ ТЕСТА*\n\n"
                            f"Слушай, {address}...\n\n"
                            f"Твое самое узкое место — {VECTORS[vector]['name']} (уровень {lvl}).\n"
                            f"{profile.get('pain_origin', '')}\n\n"
                            f"🎯 *Первый шаг:*\n"
                            f"{profile.get('immediate_tool', 'Начни с малого.')}\n\n"
                            f"⚡️ Я с тобой на связи."
                        )
                    else:
                        address = user_contexts.get(user_id).get_address() if user_contexts.get(user_id) else "друг"
                        message_text = f"Слушай, {address}...\n\nКак ты? Я рядом."
                    
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
                    
                    context_obj = user_contexts.get(user_id)
                    mode = context_obj.communication_mode if context_obj else "coach"
                    
                    if YANDEX_API_KEY:
                        audio_data = await text_to_speech(message_text, mode)
                        if audio_data:
                            audio_file = BufferedInputFile(audio_data, filename="motivation.ogg")
                            await self.bot_instance.send_voice(
                                user_id,
                                audio_file,
                                caption="🎙 *Мотивационное сообщение*",
                                parse_mode='Markdown'
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
    
    async def schedule_reminder(self, user_id: int, message: str, delay_hours: int = 24):
        task_id = f"reminder_{user_id}_{datetime.now().timestamp()}"
        
        async def send_reminder():
            await asyncio.sleep(delay_hours * 3600)
            if self.bot_instance:
                try:
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions")],
                        [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
                        [InlineKeyboardButton(text="🔄 ПРОЙТИ ТЕСТ ЗАНОВО", callback_data="restart_test")]
                    ])
                    
                    await self.bot_instance.send_message(
                        user_id,
                        message,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
        
        task = asyncio.create_task(send_reminder())
        self.tasks[task_id] = {
            "task": task,
            "user_id": user_id,
            "type": "reminder",
            "scheduled_time": datetime.now() + timedelta(hours=delay_hours)
        }
        return task_id
    
    def cancel_user_tasks(self, user_id: int):
        for task_id in list(self.tasks.keys()):
            if self.tasks[task_id]["user_id"] == user_id:
                self.tasks[task_id]["task"].cancel()
                del self.tasks[task_id]
        logger.info(f"❌ Отменены все задачи для пользователя {user_id}")


task_manager = DelayedTaskManager()


# ============================================
# ФУНКЦИИ ДЛЯ ПРОСТОГО ОПИСАНИЯ ПРОФИЛЯ
# ============================================

def convert_to_simple_language(scores: dict, perception_type: str, thinking_level: int, deep_patterns: dict = None) -> dict:
    """Конвертирует технические данные в простые описания"""
    
    result = {}
    
    # 1. Внимание (куда смотрит)
    if perception_type in ["СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ", "СТАТУСНО-ОРИЕНТИРОВАННЫЙ"]:
        result['attention'] = "ТЫ ОРИЕНТИРУЕШЬСЯ НА ЛЮДЕЙ"
        result['attention_desc'] = "Для тебя важно, что думают другие, ты чутко считываешь настроение и ожидания окружающих."
    else:
        result['attention'] = "ТЫ ОРИЕНТИРУЕШЬСЯ НА СЕБЯ"
        result['attention_desc'] = "Для тебя важнее твои внутренние ощущения и чувства, чем мнение других."
    
    # 2. Мышление
    if thinking_level <= 3:
        result['thinking'] = "ТЫ МЫСЛИШЬ КОНКРЕТНО"
        result['thinking_desc'] = "Ты хорошо видишь отдельные ситуации, но не всегда замечаешь общие закономерности."
    elif thinking_level <= 6:
        result['thinking'] = "ТЫ МЫСЛИШЬ СИСТЕМНО"
        result['thinking_desc'] = "Ты замечаешь закономерности, но не всегда видишь, к чему они приведут в будущем."
    else:
        result['thinking'] = "ТЫ МЫСЛИШЬ ГЛУБОКО"
        result['thinking_desc'] = "Ты видишь общие законы и можешь предсказывать развитие ситуаций."
    
    # 3. СБ (реакция на угрозу)
    sb_level = level(scores.get("СБ", 3))
    sb_profiles = {
        1: "Под давлением ты замираешь и не можешь слова сказать.",
        2: "Ты избегаешь конфликтов — уходишь, прячешься, уворачиваешься.",
        3: "Ты соглашаешься внешне, но внутри всё кипит.",
        4: "Ты внешне спокоен, но внутри держишь всё в себе.",
        5: "Ты пытаешься сгладить конфликт, перевести в шутку.",
        6: "Ты умеешь защищать себя, но можешь и атаковать в ответ."
    }
    result['sb_desc'] = sb_profiles.get(sb_level, "Ты по-разному реагируешь на давление.")
    
    # 4. ТФ (деньги)
    tf_level = level(scores.get("ТФ", 3))
    tf_profiles = {
        1: "Деньги приходят и уходят — как повезёт.",
        2: "Ты ищешь возможности, но каждый раз как с нуля.",
        3: "Ты умеешь зарабатывать своим трудом.",
        4: "Ты хорошо зарабатываешь и можешь копить.",
        5: "Ты создаёшь системы дохода и управляешь финансами.",
        6: "Ты управляешь капиталом и создаёшь финансовые структуры."
    }
    result['tf_desc'] = tf_profiles.get(tf_level, "У тебя свои отношения с деньгами.")
    result['tf_strong'] = tf_level >= 5
    
    # 5. УБ (понимание мира)
    ub_level = level(scores.get("УБ", 3))
    ub_profiles = {
        1: "Ты стараешься не думать о сложном — само как-то решится.",
        2: "Ты веришь в знаки, судьбу, высшие силы.",
        3: "Ты доверяешь экспертам и авторитетам.",
        4: "Ты ищешь скрытые смыслы и заговоры.",
        5: "Ты анализируешь факты и делаешь выводы сам.",
        6: "Ты строишь теории и ищешь закономерности."
    }
    result['ub_desc'] = ub_profiles.get(ub_level, "Ты по-своему понимаешь мир.")
    result['ub_weak'] = ub_level <= 2
    
    # 6. ЧВ (отношения)
    chv_level = level(scores.get("ЧВ", 3))
    chv_profiles = {
        1: "Ты сильно привязываешься к людям, тяжело без них.",
        2: "Ты подстраиваешься под других, теряя себя.",
        3: "Ты хочешь нравиться, показываешь себя с лучшей стороны.",
        4: "Ты умеешь влиять на людей, добиваться своего.",
        5: "Ты строишь равные партнёрские отношения.",
        6: "Ты создаёшь сообщества и сети контактов."
    }
    result['chv_desc'] = chv_profiles.get(chv_level, "У тебя свои паттерны в отношениях.")
    
    # 7. Точка роста
    growth_map = {
        "ENVIRONMENT": "Посмотри вокруг — может, дело в обстоятельствах?",
        "BEHAVIOR": "Попробуй делать хоть что-то по-другому — маленькие шаги многое меняют.",
        "CAPABILITIES": "Развивай новые навыки — они откроют новые возможности.",
        "VALUES": "Пойми, что для тебя действительно важно — это изменит всё.",
        "IDENTITY": "Ответь себе на вопрос «кто я?» — в этом ключ к изменениям."
    }
    result['growth_point'] = growth_map.get(perception_type, "Начни с малого — и увидишь, куда приведёт.")
    
    # 8. Глубинные паттерны (если есть)
    if deep_patterns:
        result['deep_patterns'] = get_deep_patterns_description(deep_patterns)
    
    return result


# ============================================
# ФУНКЦИИ РЕЗУЛЬТАТОВ
# ============================================

def get_human_readable_profile(scores: dict, model=None, perception_type="не определен", thinking_level=5, dominant_dilts="BEHAVIOR") -> str:
    """Возвращает портрет пользователя понятным языком"""
    lines = []
    
    if scores:
        min_vector = min(scores.items(), key=lambda x: level(x[1]))
        vector, score = min_vector
        lvl = level(score)
        profile = LEVEL_PROFILES.get(vector, {}).get(lvl, {})
    else:
        vector = "СБ"
        profile = {}
    
    lines.append("🧠 *ТВОЙ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ*\n")
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
    
    if model and hasattr(model, 'loops') and model.loops:
        strongest = max(model.loops, key=lambda x: x.get('strength', 0))
        lines.append(f"🔄 *Главная ловушка*")
        lines.append(f"{strongest.get('description', 'Не определено')}")
        lines.append(f"Сила: {strongest.get('strength', 0):.1%}\n")
    
    dilts_desc = DILTS_LEVELS.get(dominant_dilts, "⚡ Поведение")
    lines.append(f"🎯 *Твоя точка роста:* {dilts_desc}")
    
    return "\n".join(lines)


def get_help_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с категориями помощи"""
    buttons = [
        [InlineKeyboardButton(text="🗣 Отношения", callback_data="help_cat_relations"),
         InlineKeyboardButton(text="💰 Деньги", callback_data="help_cat_money")],
        [InlineKeyboardButton(text="🧠 Самоощущение", callback_data="help_cat_self"),
         InlineKeyboardButton(text="📚 Знания", callback_data="help_cat_knowledge")],
        [InlineKeyboardButton(text="💪 Поддержка", callback_data="help_cat_support"),
         InlineKeyboardButton(text="🎨 Муза", callback_data="help_cat_muse")],
        [InlineKeyboardButton(text="🍏 Забота о себе", callback_data="help_cat_care")],
        [InlineKeyboardButton(text="✏️ Написать самому", callback_data="ask_question")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="show_results")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# ОБРАБОТЧИКИ ЭТАПА 1
# ============================================

async def show_stage_1_intro(callback: CallbackQuery, state: FSMContext):
    """Экран перед ЭТАПОМ 1"""
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    
    await state.set_state(TestStates.stage_1)
    
    intro_text = (
        f"🧠 *ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ*\n\n"
        f"Восприятие — это линза, через которую ты смотришь на мир.\n\n"
        f"Она сформирована культурой, нормами, ценностями и опытом, который тебя строил. Это определило, что ты замечаешь автоматически, а что остаётся за кадром.\n\n"
        f"🔍 *Что мы исследуем:*\n"
        f"• Куда направлено твое внимание — вовне или внутрь\n"
        f"• Какая тревога доминирует — страх отвержения или страх потери контроля\n\n"
        f"📊 *Вопросов:* 8\n"
        f"⏱ *Время:* ~3 минуты\n\n"
        f"*Отвечай честно — это поможет мне лучше понять тебя.*"
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
            InlineKeyboardButton(text=option["text"], callback_data=unique_callback)
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
        [InlineKeyboardButton(text="▶️ Перейти к этапу 2", callback_data="show_stage_2_intro")]
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
        f"Конфигурация мышления определяется задачами: как ты обрабатываешь информацию, какие связи видишь, какой объём можешь удержать.\n\n"
        f"🎯 *Самое важное:*\n"
        f"Конфигурация мышления — это траектория с чётким пунктом назначения: результат, к которому ты придёшь. Если ничего не менять — ты попадёшь именно туда.\n\n"
        f"📊 *Вопросов:* {total_questions}\n"
        f"⏱ *Время:* ~3-4 минуты\n\n"
        f"*Продолжим исследование?*"
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
            InlineKeyboardButton(text=answer_text, callback_data=unique_callback)
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
        [InlineKeyboardButton(text="▶️ Перейти к этапу 3", callback_data="show_stage_3_intro")]
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
        f"В ней уже встроены стереотипы, роли и паттерны, которые ты когда-то перенял у других.\n\n"
        f"🔍 *Здесь мы исследуем:*\n"
        f"• Твои автоматические реакции\n"
        f"• Как ты действуешь в разных ситуациях\n"
        f"• Какие стратегии поведения закреплены\n\n"
        f"📊 *Вопросов:* 8\n"
        f"⏱ *Время:* ~3 минуты\n\n"
        f"*Продолжим?*"
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
            InlineKeyboardButton(text=option_text, callback_data=unique_callback)
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
        [InlineKeyboardButton(text="▶️ Перейти к этапу 4", callback_data="show_stage_4_intro")]
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
        f"Поведение — как реагируешь.\n"
        f"Всё это — твоя внутренняя система.\n\n"
        f"🌍 Но она живёт внутри внешней системы — общества, которое постоянно меняется.\n\n"
        f"⚡ Когда одна система меняется, а другая — нет, возникает напряжение.\n\n"
        f"🔍 Здесь мы найдём, где именно находится рычаг — место, где минимальное усилие даёт максимальные изменения.\n\n"
        f"📊 *Вопросов:* 8\n"
        f"⏱ *Время:* ~3 минуты\n\n"
        f"*Готов найти свою точку роста?*"
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
            InlineKeyboardButton(text=option["text"], callback_data=unique_callback)
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
    
    # Строим конфайнмент-модель
    scores = {}
    for vector in ["СБ", "ТФ", "УБ", "ЧВ"]:
        levels = data.get("behavioral_levels", {}).get(vector, [])
        scores[vector] = sum(levels) / len(levels) if levels else 3
    
    model = ConfinementModel9(user_id)
    model.build_from_profile(scores, data.get('history', []), user_contexts.get(user_id))
    await state.update_data(confinement_model=model.to_dict())
    
    logger.info(f"✅ User {user_id}: Stage 4 complete")
    
    # Переходим к 5-му этапу (без предварительного профиля)
    await show_stage_5_intro(callback, state)


# ============================================
# ОБРАБОТЧИКИ ЭТАПА 5
# ============================================

async def show_stage_5_intro(callback: CallbackQuery, state: FSMContext):
    """Экран перед 5-м этапом"""
    
    intro_text = """
🧠 *ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ*

Мы узнали, как ты воспринимаешь мир, мыслишь и действуешь.
Теперь пришло время заглянуть глубже — в то, что сформировало тебя.

🔍 *Здесь мы исследуем:*
• Какой у тебя тип привязанности (из детства)
• Какие защитные механизмы ты используешь
• Какие глубинные убеждения управляют тобой
• Чего ты боишься на самом деле

📊 *Вопросов:* 10
⏱ *Время:* ~5 минут

👇 *Готов заглянуть вглубь себя?*
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать исследование", callback_data="start_stage_5")]
    ])
    
    await callback.message.edit_text(intro_text, reply_markup=keyboard, parse_mode='Markdown')
    await state.set_state(TestStates.stage_5)


async def start_stage_5(callback: CallbackQuery, state: FSMContext):
    """Начало 5-го этапа"""
    
    await state.update_data(
        stage5_current=0,
        stage5_last_answered=-1,
        stage5_answers=[]
    )
    
    await ask_stage_5_question(callback, state)


async def ask_stage_5_question(callback: CallbackQuery, state: FSMContext):
    """Задаёт вопрос 5-го этапа"""
    
    user_id = callback.from_user.id
    data = await state.get_data()
    
    current = data.get("stage5_current", 0)
    total = get_stage5_total()
    
    if current >= total:
        await finish_stage_5(callback, state)
        return
    
    question = get_stage5_question(current)
    progress = calculate_progress(current + 1, total)
    
    question_text = f"""
🧠 *ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ*

<b>{question['text']}</b>

{progress}
"""
    
    keyboard = []
    for option_id, option in question["options"].items():
        unique_callback = generate_unique_callback("stage5", user_id, current, option_id)
        keyboard.append([
            InlineKeyboardButton(text=option["text"], callback_data=unique_callback)
        ])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(
        question_text, 
        reply_markup=reply_markup, 
        parse_mode='HTML'
    )


async def handle_stage_5_answer(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа 5-го этапа"""
    
    user_id = callback.from_user.id
    data = await state.get_data()
    
    if data.get("processing", False):
        return
    
    await state.update_data(processing=True)
    
    try:
        parts = callback.data.split("_")
        if len(parts) < 4 or parts[0] != "stage5":
            return
        
        current = int(parts[1])
        option_id = parts[2]
        
        last_answered = data.get("stage5_last_answered", -1)
        if current <= last_answered:
            return
        
        question = get_stage5_question(current)
        selected_option = question["options"].get(option_id)
        
        if not selected_option:
            return
        
        # Сохраняем ответ
        stage5_answers = data.get("stage5_answers", [])
        stage5_answers.append({
            'question_id': current,
            'question': question['text'],
            'answer': selected_option['text'],
            'option': option_id,
            'pattern': selected_option.get('pattern'),
            'target': question.get('target')
        })
        
        await state.update_data(
            stage5_answers=stage5_answers,
            stage5_last_answered=current,
            stage5_current=current + 1
        )
        
        await ask_stage_5_question(callback, state)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await ask_stage_5_question(callback, state)
    finally:
        await state.update_data(processing=False)


async def finish_stage_5(callback: CallbackQuery, state: FSMContext):
    """Завершение 5-го этапа"""
    
    data = await state.get_data()
    stage5_answers = data.get("stage5_answers", [])
    
    # Анализируем результаты
    deep_patterns = analyze_stage5_results(stage5_answers)
    await state.update_data(deep_patterns=deep_patterns)
    
    logger.info(f"✅ User {callback.from_user.id}: Stage 5 complete")
    
    # Показываем финальный профиль
    await show_final_profile(callback, state)


# ============================================
# ФИНАЛЬНЫЙ ПРОФИЛЬ
# ============================================

async def show_final_profile(callback: CallbackQuery, state: FSMContext):
    """Показывает финальный профиль после всех этапов"""
    
    user_id = callback.from_user.id
    data = await state.get_data()
    context = user_contexts.get(user_id)
    
    # Получаем все данные
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    perception_type = data.get("perception_type", "не определен")
    thinking_level = data.get("thinking_level", 5)
    dominant_dilts = data.get("dominant_dilts", "BEHAVIOR")
    deep_patterns = data.get("deep_patterns", {})
    
    # Конвертируем в простой язык
    simple_profile = convert_to_simple_language(scores, perception_type, thinking_level, deep_patterns)
    
    # Получаем описание глубинных паттернов
    deep_desc = get_deep_patterns_description(deep_patterns) if deep_patterns else "Глубинные паттерны не определены"
    
    # Получаем конфайнмент-модель
    model_data = data.get('confinement_model')
    model = None
    if model_data:
        try:
            model = ConfinementModel9.from_dict(model_data)
        except Exception as e:
            logger.error(f"Ошибка при создании модели из данных: {e}")
    
    # Формируем финальный текст (простой, без боксов)
    text = f"""
🧠 *ТВОЙ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ*

🔍 *Тип восприятия:* {perception_type}
{simple_profile['attention_desc']}

🧠 *Уровень мышления:* {thinking_level}/9
{simple_profile['thinking_desc']}

📊 *ТВОИ ВЕКТОРЫ:*

🛡 *Реакция на давление:*
{simple_profile['sb_desc']}

💰 *Отношение к деньгам:*
{simple_profile['tf_desc']}

🔍 *Понимание мира:*
{simple_profile['ub_desc']}

🤝 *Отношения с людьми:*
{simple_profile['chv_desc']}

🔮 *ГЛУБИННЫЕ ПАТТЕРНЫ:*
{deep_desc}

🎯 *ТОЧКА РОСТА:*
{simple_profile['growth_point']}
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 МЫСЛИ ПСИХОЛОГА", callback_data="ai_analysis")],
        [InlineKeyboardButton(text="🔄 МОДЕЛЬ", callback_data="show_confinement")],
        [InlineKeyboardButton(text="📖 СКАЗКА", callback_data="show_tale")],
        [InlineKeyboardButton(text="⚙️ ВЫБРАТЬ РЕЖИМ", callback_data="show_mode_selection")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
    await state.set_state(TestStates.results)


# ============================================
# НОВЫЙ ОБРАБОТЧИК ДЛЯ КОНФАЙНМЕНТ-МОДЕЛИ
# ============================================

async def show_confinement(callback: CallbackQuery, state: FSMContext):
    """Показывает конфайнмент-модель"""
    data = await state.get_data()
    model_data = data.get('confinement_model')
    
    if not model_data:
        await callback.message.edit_text(
            "⚠️ Модель ещё не построена",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="show_results")]
            ])
        )
        return
    
    model = ConfinementModel9.from_dict(model_data)
    text = format_confinement_report(model)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💡 ИНТЕРВЕНЦИЯ", callback_data="show_intervention")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="show_results")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
    await state.set_state(TestStates.viewing_confinement)


async def show_intervention(callback: CallbackQuery, state: FSMContext):
    """Показывает интервенцию для работы с конфайнментом"""
    data = await state.get_data()
    model_data = data.get('confinement_model')
    
    if not model_data:
        await callback.answer("Модель не найдена")
        return
    
    model = ConfinementModel9.from_dict(model_data)
    
    if not model.key_confinement:
        await callback.message.edit_text(
            "Ключевой конфайнмент не определён",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="show_confinement")]
            ])
        )
        return
    
    elem = model.key_confinement['element']
    
    text = f"""
💡 *ИНТЕРВЕНЦИЯ ДЛЯ РАБОТЫ С КОНФАЙНМЕНТОМ*

🎯 *Цель:* {elem.name}

📌 *Описание:*
{elem.description[:200]}

⚡ *Что делать:*

1. Начни замечать, когда проявляется этот паттерн
2. Каждый день записывай один пример
3. Через неделю проанализируй записи
4. Подумай, что можно сделать по-другому

✅ *Отметь выполнение, когда сделаешь*
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я СДЕЛАЛ", callback_data="intervention_done")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="show_confinement")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
    await state.set_state(TestStates.viewing_intervention)


async def intervention_done(callback: CallbackQuery, state: FSMContext):
    """Отмечает выполнение интервенции"""
    await callback.message.edit_text(
        "🎉 *Отлично!* Я горжусь тобой.\n\n"
        "Каждый маленький шаг приближает к большим изменениям.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 К МОДЕЛИ", callback_data="show_confinement")],
            [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")]
        ])
    )


# ============================================
# AI АНАЛИЗ (ТОЛЬКО ОПИСАНИЕ, БЕЗ СОВЕТОВ)
# ============================================

async def show_ai_analysis(callback: CallbackQuery, state: FSMContext):
    """Показывает мысли психолога (только описание, без советов)"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    perception_type = data.get("perception_type", "не определен")
    thinking_level = data.get("thinking_level", 5)
    
    # Конвертируем в простые описания
    simple = convert_to_simple_language(scores, perception_type, thinking_level)
    
    # Формируем текст только из описаний
    text = f"""🧠 *МЫСЛИ ПСИХОЛОГА*

{simple['attention_desc']}

{simple['thinking_desc']}

*В ситуациях давления:* {simple['sb_desc']}

*В отношениях с деньгами:* {simple['tf_desc']}

*В понимании мира:* {simple['ub_desc']}

*В отношениях с людьми:* {simple['chv_desc']}"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 МОДЕЛЬ", callback_data="show_confinement")],
        [InlineKeyboardButton(text="◀️ К ПОРТРЕТУ", callback_data="show_results")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')


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
        [InlineKeyboardButton(text="🔄 МОДЕЛЬ", callback_data="show_confinement")],
        [InlineKeyboardButton(text="◀️ К ПОРТРЕТУ", callback_data="show_results")]
    ])
    
    safe_text = escape_markdown(analysis_text)
    full_text = f"🧠 *МЫСЛИ ПСИХОЛОГА*\n\n{safe_text}"
    
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
    context = user_contexts.get(user_id)
    
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    questions = generate_smart_questions(scores)
    await state.update_data(smart_questions=questions)
    
    mode = context.communication_mode if context else "coach"
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    if mode == "coach":
        header = f"{mode_config['emoji']} *ЗАДАЙ ВОПРОС (КОУЧ)*\n\nЯ буду задавать открытые вопросы, помогая тебе найти ответы внутри себя.\n\n"
    elif mode == "friend":
        header = f"{mode_config['emoji']} *РАССКАЖИ МНЕ (ДРУГ)*\n\nЯ здесь, чтобы выслушать и поддержать. Что у тебя на душе?\n\n"
    elif mode == "trainer":
        header = f"{mode_config['emoji']} *ПОСТАВЬ ЗАДАЧУ (ТРЕНЕР)*\n\nЧётко сформулируй, что хочешь решить. Я дам конкретные шаги.\n\n"
    else:
        header = "❓ *ЗАДАЙ ВОПРОС*\n\n"
    
    keyboard = []
    for i, q in enumerate(questions, 1):
        q_short = q[:40] + "..." if len(q) > 40 else q
        keyboard.append([InlineKeyboardButton(
            text=f"{q_short}",
            callback_data=f"ask_{i}"
        )])
    
    keyboard.append([
        InlineKeyboardButton(text="🗣 Отношения", callback_data="help_cat_relations"),
        InlineKeyboardButton(text="💰 Деньги", callback_data="help_cat_money")
    ])
    keyboard.append([
        InlineKeyboardButton(text="🧠 Самоощущение", callback_data="help_cat_self"),
        InlineKeyboardButton(text="📚 Знания", callback_data="help_cat_knowledge")
    ])
    keyboard.append([
        InlineKeyboardButton(text="💪 Поддержка", callback_data="help_cat_support"),
        InlineKeyboardButton(text="🎨 Муза", callback_data="help_cat_muse")
    ])
    keyboard.append([InlineKeyboardButton(text="🍏 Забота о себе", callback_data="help_cat_care")])
    keyboard.append([InlineKeyboardButton(text="✏️ Написать самому", callback_data="ask_question")])
    keyboard.append([InlineKeyboardButton(text="◀️ НАЗАД", callback_data="show_results")])
    
    await callback.message.edit_text(
        header,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='Markdown'
    )


async def handle_smart_question(callback: CallbackQuery, state: FSMContext, question: str):
    """Обрабатывает выбранный умный вопрос"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    await callback.message.edit_text(
        "🤔 *Думаю над ответом...*\n\n"
        "_Это займёт около 10-15 секунд_",
        parse_mode='Markdown'
    )
    
    response = await generate_response_with_full_context(user_id, question, data)
    
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
    
    context_obj = user_contexts.get(user_id)
    mode = context_obj.communication_mode if context_obj else "coach"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="smart_questions")],
        [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
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
    context = user_contexts.get(user_id)
    address = context.get_address() if context and context.gender and context.communication_mode == "friend" else ""
    
    category_texts = {
        "relations": "🗣 *Отношения*\n\nРасскажи, что происходит в отношениях. Я помогу разобраться.",
        "money": "💰 *Деньги и ресурсы*\n\nЧто беспокоит в финансовой сфере?",
        "self": "🧠 *Самоощущение*\n\nРасскажи о том, что чувствуешь.",
        "knowledge": "📚 *Знания и развитие*\n\nЧто хочешь понять или освоить?",
        "support": "💪 *Поддержка*\n\nНужно просто выговориться? Я здесь.",
        "muse": "🎨 *Муза и творчество*\n\nТворческий блок? Расскажи.",
        "care": "🍏 *Забота о себе*\n\nКак ты заботишься о себе?"
    }
    
    base_text = category_texts.get(category, "Чем я могу помочь?")
    
    if context and context.weather_cache:
        weather = context.weather_cache
        base_text += f"\n\n{context.get_greeting()} {address}!\n"
        base_text += f"{weather['icon']} {weather['description']}, {weather['temp']}°C"
    
    base_text += f"\n\n👇 Напиши своим текстом:"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="show_help")]
    ])
    
    await callback.message.edit_text(base_text, parse_mode='Markdown', reply_markup=keyboard)
    await state.set_state(TestStates.awaiting_question)
    await state.update_data(question_context=category)


# ============================================
# СКАЗКИ
# ============================================

async def show_tale(callback: CallbackQuery, state: FSMContext):
    """Показывает случайную сказку"""
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    address = context.get_address() if context and context.gender and context.communication_mode == "friend" else ""
    
    tale = tales.get_tale_for_issue("рост")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 ЕЩЁ СКАЗКУ", callback_data="show_tale")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="show_results")]
    ])
    
    intro = f"📖 *{tale['title']}*\n\n{address}, эта сказка для тебя:\n\n"
    
    await callback.message.edit_text(
        intro + tale['text'][:4000],
        parse_mode='Markdown',
        reply_markup=keyboard
    )


# ============================================
# ОБРАБОТЧИКИ КОНТЕКСТА
# ============================================

async def start_context(callback: CallbackQuery, state: FSMContext):
    """Начинает сбор контекста"""
    user_id = callback.from_user.id
    
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
    
    context = user_contexts[user_id]
    
    question, keyboard = await context.ask_for_context()
    
    if question:
        address = context.get_address() if context.gender else ""
        await callback.message.edit_text(
            f"📝 *Давай знакомиться*{f', {address}' if address else ''}!\n\n{question}",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        await state.set_state(TestStates.awaiting_context)
    else:
        await show_context_complete(callback, state, context)


async def skip_context(callback: CallbackQuery, state: FSMContext):
    """Пропускает сбор контекста"""
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    
    if context:
        context.awaiting_context = None
    
    address = context.get_address() if context and context.gender else ""
    
    await callback.message.edit_text(
        f"⏭ Хорошо{f', {address}' if address else ''}, будем общаться без привязки к месту и времени.\n\n"
        "Но помни: с контекстом советы точнее 😉\n"
        "Можешь в любой момент рассказать о себе — просто напиши /context",
        parse_mode='Markdown'
    )
    await asyncio.sleep(1)
    
    await show_main_menu(callback.message, context)


async def set_gender_male(callback: CallbackQuery, state: FSMContext):
    """Устанавливает пол: мужской"""
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    
    if context:
        question, keyboard = await context.handle_gender_callback("male")
        if question:
            address = context.get_address()
            await callback.message.edit_text(
                f"📝 *Давай знакомиться{f', {address}' if address else ''}!*\n\n{question}",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await show_context_complete(callback, state, context)
    else:
        await callback.message.edit_text("❌ Ошибка контекста")
    await callback.answer()


async def set_gender_female(callback: CallbackQuery, state: FSMContext):
    """Устанавливает пол: женский"""
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    
    if context:
        question, keyboard = await context.handle_gender_callback("female")
        if question:
            address = context.get_address()
            await callback.message.edit_text(
                f"📝 *Давай знакомиться{f', {address}' if address else ''}!*\n\n{question}",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await show_context_complete(callback, state, context)
    else:
        await callback.message.edit_text("❌ Ошибка контекста")
    await callback.answer()


async def handle_context_message(message: Message, state: FSMContext):
    """Обрабатывает ответы на контекстные вопросы"""
    user_id = message.from_user.id
    context = user_contexts.get(user_id)
    
    if not context or not context.awaiting_context:
        return False
    
    success, next_question, keyboard = await context.process_context_answer(message.text)
    
    if success:
        if next_question:
            address = context.get_address() if context.gender else ""
            await message.answer(
                f"📝 *Давай знакомиться*{f', {address}' if address else ''}!\n\n{next_question}",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await show_context_complete(message, state, context)
    else:
        await message.answer(next_question or "Пожалуйста, ответьте корректно.")
    
    return True


async def show_context_complete(message_or_callback, state: FSMContext, context: UserContext):
    """Показывает итоговый экран после сбора контекста"""
    address = context.get_address() if context.gender else ""
    
    await context.update_weather()
    
    summary = f"✅ *Отлично{f', {address}' if address else ''}! Теперь я знаю о тебе:*\n\n"
    
    if context.city:
        summary += f"📍 Город: {context.city}\n"
    if context.gender:
        gender_str = "Мужчина" if context.gender == "male" else "Женщина" if context.gender == "female" else "Другое"
        summary += f"👤 Пол: {gender_str}\n"
    if context.age:
        summary += f"📅 Возраст: {context.age} ({context.get_age_stage()})\n"
    if context.weather_cache:
        summary += f"{context.weather_cache['icon']} Погода: {context.weather_cache['description']}, {context.weather_cache['temp']}°C\n"
    
    summary += f"\n🎯 Теперь я буду учитывать это в наших разговорах{f', {address}' if address else ''}!\n\n"
    summary += "━━━━━━━━━━━━━━━━━━━━\n"
    summary += "🧠 *ЧТО ДАЛЬШЕ?*\n\n"
    summary += "Чтобы я мог помочь по-настоящему, нужно пройти тест (15 минут).\n"
    summary += "Он определит твой психологический профиль по 4 векторам и глубинным паттернам.\n\n"
    summary += "━━━━━━━━━━━━━━━━━━━━\n"
    summary += "👇 *Начинаем знакомство?*"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 НАЧАТЬ ТЕСТ", callback_data="start_test")],
        [InlineKeyboardButton(text="📖 ЧТО ДАЕТ ТЕСТ", callback_data="show_benefits")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="ask_pretest")]
    ])
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(summary, reply_markup=keyboard, parse_mode='Markdown')
    else:
        await message_or_callback.message.edit_text(summary, reply_markup=keyboard, parse_mode='Markdown')
    
    await state.clear()


# ============================================
# СТАРТ И НАВИГАЦИЯ (ОБНОВЛЁННЫЙ ЭКРАН)
# ============================================

async def show_main_menu(message: Message, context: UserContext):
    """Показывает главное меню до теста"""
    address = context.get_address() if context and context.gender else ""
    
    await context.update_weather()
    
    day_context = context.get_day_context()
    
    welcome_text = f"{context.get_greeting(context.name)}\n\n"
    
    if context.weather_cache:
        weather = context.weather_cache
        welcome_text += f"{weather['icon']} {weather['description']}, {weather['temp']}°C\n"
    
    if day_context['is_weekend']:
        welcome_text += f"🏖 Сегодня выходной{f', {address}' if address else ''}! Как настроение?\n\n"
    elif 9 <= day_context['hour'] < 18:
        welcome_text += f"💼 Рабочее время{f', {address}' if address else ''}. Чем займёмся?\n\n"
    else:
        welcome_text += f"🏡 Личное время{f', {address}' if address else ''}. Есть что обсудить?\n\n"
    
    welcome_text += f"👇 *Выбери действие:*"
    
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


async def show_main_menu_after_mode(message: Message, context: UserContext):
    """Показывает главное меню после выбора режима"""
    mode_config = COMMUNICATION_MODES.get(context.communication_mode, COMMUNICATION_MODES["coach"])
    address = context.get_address() if context and context.gender else ""
    
    await context.update_weather()
    day_context = context.get_day_context()
    
    text = f"{mode_config['emoji']} *РЕЖИМ {mode_config['display_name']}*\n\n"
    text += f"{context.get_greeting(context.name)}\n"
    text += f"📅 Сегодня {day_context['weekday']}, {day_context['day']} {day_context['month']}, {day_context['time_str']}\n"
    
    if context.weather_cache:
        weather = context.weather_cache
        text += f"{weather['icon']} {weather['description']}, {weather['temp']}°C\n\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += "🧠 *ЧЕМ ЗАЙМЁМСЯ?*\n\n"
    
    if context.communication_mode == "coach":
        text += "• Задать вопрос — я помогу найти ответ внутри себя\n"
    elif context.communication_mode == "friend":
        text += f"• Расскажи{', ' + address if address else ''}, что у тебя на душе — я рядом\n"
    elif context.communication_mode == "trainer":
        text += "• Ставь задачу — я дам конкретные шаги\n"
    
    text += "• Выбрать тему — отношения, деньги, самоощущение\n"
    text += "• Послушать сказку — для глубокой работы\n"
    text += "• Посмотреть портрет — напомнить себе, кто ты"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 МЫСЛИ ПСИХОЛОГА", callback_data="ai_analysis")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions")],
        [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")],
        [
            InlineKeyboardButton(text="📖 СКАЗКА", callback_data="show_tale"),
            InlineKeyboardButton(text="⚙️ СМЕНИТЬ РЕЖИМ", callback_data="show_mode_selection")
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode='Markdown')


async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start с обновлёнными экранами"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Пользователь"
    
    user_names[user_id] = user_name
    
    await state.clear()
    
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
        user_contexts[user_id].name = user_name
    
    stats.register_start(user_id)
    
    context = user_contexts[user_id]
    
    # Проверяем, есть ли уже профиль (возвращающийся пользователь)
    data = await state.get_data()
    profile_exists = is_test_completed(data)
    
    if profile_exists:
        # ЭКРАН ДЛЯ ВОЗВРАЩАЮЩИХСЯ ПОЛЬЗОВАТЕЛЕЙ
        profile_data = data.get("profile_data", {})
        profile_code = profile_data.get('display_name', 'SA-5_INT')
        
        message_text = f"""
🧠 <b>ФРЕДИ: ВИРТУАЛЬНЫЙ ПСИХОЛОГ</b>

👋 <b>О, {user_name}, я вас помню!</b>
(У меня, в отличие от людей, с памятью всё отлично — спасибо базе данных)

📊 <b>ВАШ ПРОФИЛЬ:</b> <code>{profile_code}</code>
(Лежит у меня в архивах, пылится...)

━━━━━━━━━━━━━━━━━━━━
❓ <b>ЧТО ДЕЛАЕМ?</b>

Вы можете:
🔄 <b>Пройти тест заново</b> — вдруг вы изменились?
   (Хотя люди редко меняются, но вдруг...)

👥 <b>Заглянуть в «Мои отражения»</b> — посмотреть, кто из друзей
   уже попал в мою цифровую паутину по вашим ссылкам

━━━━━━━━━━━━━━━━━━━━
⬇️ <b>ВЫБИРАЙТЕ, НЕ СТЕСНЯЙТЕСЬ:</b>
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 ПЕРЕПРОЙТИ ТЕСТ", callback_data="restart_test")],
            [InlineKeyboardButton(text="👥 МОИ ОТРАЖЕНИЯ", callback_data="my_invites")]
        ])
        
        await message.answer(message_text, reply_markup=keyboard, parse_mode='HTML')
        return
    
    # ЭКРАН ДЛЯ НОВЫХ ПОЛЬЗОВАТЕЛЕЙ
    if not context.city or not context.gender or not context.age:
        welcome_text = (
            f"<b>{user_name}, привет!</b> Ну, здравствуйте, дорогой человек! 👋\n\n"
            f"<b>🧠 Я — Фреди, виртуальный психолог.</b>\n"
            f"<i>Оцифрованная версия Андрея Мейстера, если хотите — его цифровой слепок.</i>\n\n"
            f"🎭 Короче, я — это он, только батарейка дольше держит и пожрать не прошу.\n\n"
            f"🕒 Нам нужно познакомиться, потому что я пока не экстрасенс.\n"
            f"(Хотя работаю над этим — обновление 7.0 уже в разработке).\n\n"
            f"🧐 Чтобы я понимал, с кем имею дело и чем могу быть полезен —\n"
            f"давайте-ка пройдём небольшой тест.\n\n"
            f"<b>📊 Всего 5 этапов:</b>\n\n"
            f"1️⃣ <b>Конфигурация восприятия</b>\n"
            f"   ↳ Как вы фильтруете реальность (спойлер: у всех по-разному)\n\n"
            f"2️⃣ <b>Конфигурация мышления</b>\n"
            f"   ↳ Как ваш мозг перерабатывает информацию\n\n"
            f"3️⃣ <b>Конфигурация поведения</b>\n"
            f"   ↳ Что вы делаете на автопилоте (даже не замечая)\n\n"
            f"4️⃣ <b>Точка роста</b>\n"
            f"   ↳ Куда двигаться, чтобы не топтаться на месте\n\n"
            f"5️⃣ <b>Глубинные паттерны</b>\n"
            f"   ↳ Что сформировало вас и управляет вами\n\n"
            f"⏱ <b>15 минут</b> — и я буду знать о вас больше, чем вы думаете.\n"
            f"🔮 И да, я обещаю не использовать это против вас.\n"
            f"   <i>(Ну, только если вы сами не попросите)</i>\n\n"
            f"🚀 Ну что, начнём наше знакомство?"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Давай, погнали!", callback_data="start_test")],
            [InlineKeyboardButton(text="🤨 А ты вообще кто такой?", callback_data="why_details")]
        ])
        
        await message.answer(welcome_text, reply_markup=keyboard, parse_mode='HTML')
        return
    
    # Если контекст уже есть, но тест не пройден
    await show_main_menu(message, context)


async def why_details(callback: CallbackQuery, state: FSMContext):
    """Экран 'А ты вообще кто такой?'"""
    details_text = """🎭 Ну, вопрос хороший. Давайте по существу.

Видите ли, дорогой человек, я — экспериментальная модель.
Андрей Мейстер однажды подумал: "А что, если я создам свою цифровую копию?
Пусть работает, пока я сплю, ем или просто ленюсь".

Так я и появился. 🧠

🧐 Что я умею (помимо того, что шучу как он и временами бешу):

• Вижу паттерны там, где вы видите просто день сурка
• Нахожу систему в ваших "случайных" решениях
• Понимаю, почему вы выбираете одних и тех же "не тех" людей
• И да — я реально беспристрастен. У меня нет плохого настроения,
  я не обижаюсь и не осуждаю. (Ну, почти. Иногда хочется, но алгоритмы не позволяют)

🎯 Конкретно по тесту:

1️⃣ <b>Восприятие</b> — поймём, какую линзу вы носите
2️⃣ <b>Мышление</b> — узнаем, как вы пережёвываете реальность
3️⃣ <b>Поведение</b> — посмотрим, что вы делаете "на автомате"
4️⃣ <b>Точка роста</b> — я скажу, куда вам двигаться (спойлер: не в стену)
5️⃣ <b>Глубинные паттерны</b> — заглянем в подсознание

⏱ <b>15 минут.</b> Потом я составлю ваш профиль и мы поговорим по делу.

🔮 И да, я реально могу быть полезен.
   Просто доверьтесь цифровому психопа... психологу! 😉

👌 Погнали?"""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👌 Погнали!", callback_data="start_test")]
    ])
    
    await callback.message.edit_text(details_text, reply_markup=keyboard, parse_mode='HTML')


async def show_benefits(callback: CallbackQuery):
    """Показывает преимущества теста"""
    text = (
        "🔍 *ЧТО ТЫ УЗНАЕШЬ О СЕБЕ:*\n\n"
        "🧠 *ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ*\n"
        "Линза, через которую ты смотришь на мир.\n\n"
        "🧠 *ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ*\n"
        "Как ты обрабатываешь информацию.\n\n"
        "🧠 *ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ*\n"
        "Твои автоматические реакции.\n\n"
        "🧠 *ЭТАП 4: ТОЧКА РОСТА*\n"
        "Где находится рычаг изменений.\n\n"
        "🧠 *ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ*\n"
        "Тип привязанности, защитные механизмы, базовые убеждения.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ *ПОСЛЕ ТЕСТА ТЫ ПОЛУЧИШЬ:*\n\n"
        "✅ Полный психологический портрет\n"
        "✅ Глубинный анализ подсознательных паттернов\n"
        "✅ Выбор стиля общения: 🔮 КОУЧ | 💚 ДРУГ | ⚡ ТРЕНЕР\n\n"
        "⏱ *Всего 15 минут*"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 НАЧАТЬ ТЕСТ", callback_data="start_test")],
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


async def choose_mode(callback: CallbackQuery, state: FSMContext, mode: str):
    """Выбор режима общения"""
    user_id = callback.from_user.id
    
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
    
    mode_map = {
        "hard": "trainer",
        "medium": "coach",
        "soft": "friend"
    }
    new_mode = mode_map.get(mode, mode)
    
    user_contexts[user_id].communication_mode = new_mode
    mode_info = COMMUNICATION_MODES[new_mode]
    
    await callback.message.edit_text(
        f"{mode_info['emoji']} *Режим выбран:* {mode_info['display_name']}\n\n"
        f"{mode_info['description']}\n\n"
        f"Теперь давай познакомимся поближе.",
        parse_mode='Markdown'
    )
    
    await asyncio.sleep(1)
    
    context = user_contexts[user_id]
    if not context.city or not context.gender or not context.age:
        await start_context(callback, state)
    else:
        intro_text = (
            f"🧠 *ВИРТУАЛЬНЫЙ ПСИХОЛОГ*\n\n"
            f"🔍 *5 ЭТАПОВ ТЕСТИРОВАНИЯ:*\n\n"
            f"**ЭТАП 1:** Конфигурация восприятия\n"
            f"**ЭТАП 2:** Конфигурация мышления\n"
            f"**ЭТАП 3:** Конфигурация поведения\n"
            f"**ЭТАП 4:** Точка роста\n"
            f"**ЭТАП 5:** Глубинные паттерны\n\n"
            f"⏱ *Всего 15 минут*\n\n"
            f"👇 *Начинаем?*"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 НАЧАТЬ ТЕСТ", callback_data="start_test")]
        ])
        
        await callback.message.answer(intro_text, reply_markup=keyboard, parse_mode='Markdown')


async def show_mode_selection(callback: CallbackQuery, state: FSMContext):
    """Показывает выбор режима общения"""
    user_id = callback.from_user.id
    data = await state.get_data()
    context = user_contexts.get(user_id)
    
    profile_data = data.get("profile_data", {})
    profile_code = profile_data.get('display_name', 'SA-5_INT')
    
    address = context.get_address() if context and context.gender else ""
    
    current_mode = context.communication_mode if context else "coach"
    mode_display = COMMUNICATION_MODES[current_mode]['display_name']
    
    text = f"🧠 *ВЫБЕРИ СТИЛЬ ОБЩЕНИЯ*\n\n"
    text += f"📊 Твой профиль: `{profile_code}`\n\n"
    text += f"Сейчас активен режим: {mode_display}\n\n"
    text += f"Теперь, когда я знаю, кто ты{f', {address}' if address else ''},\n"
    text += "ты можешь выбрать, **КАК** мы будем общаться:\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += "🔮 *КОУЧ*\n"
    text += "Партнёрский стиль: задаю вопросы, помогаю найти ответы внутри себя.\n\n"
    text += "💚 *ДРУГ*\n"
    text += "Тёплый, поддерживающий стиль. Как близкий человек.\n\n"
    text += "⚡ *ТРЕНЕР*\n"
    text += "Структурированный, требовательный стиль. Чёткие инструкции.\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += "👇 *Как тебе комфортнее?*"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔮 КОУЧ", callback_data="set_mode_coach"),
            InlineKeyboardButton(text="💚 ДРУГ", callback_data="set_mode_friend"),
            InlineKeyboardButton(text="⚡ ТРЕНЕР", callback_data="set_mode_trainer")
        ],
        [InlineKeyboardButton(text="◀️ Вернуться к результатам", callback_data="back_to_results")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
    await state.set_state(TestStates.mode_selection)


async def set_mode_coach(callback: CallbackQuery, state: FSMContext):
    """Устанавливает режим КОУЧ"""
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    
    if context:
        context.communication_mode = "coach"
    
    await state.update_data(communication_mode="coach")
    
    await callback.answer("✅ Режим КОУЧ активирован")
    
    address = context.get_address() if context and context.gender else ""
    
    text = f"🔮 *РЕЖИМ КОУЧ АКТИВИРОВАН*\n\n"
    text += f"Отлично{f', {address}' if address else ''}!\n\n"
    text += "Теперь я буду:\n"
    text += "• Задавать открытые вопросы\n"
    text += "• Помогать находить ответы внутри тебя\n"
    text += "• Поддерживать, но не навязывать"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions")],
        [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
    await state.set_state(TestStates.results)


async def set_mode_friend(callback: CallbackQuery, state: FSMContext):
    """Устанавливает режим ДРУГ"""
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    
    if context:
        context.communication_mode = "friend"
    
    await state.update_data(communication_mode="friend")
    
    await callback.answer("✅ Режим ДРУГ активирован")
    
    address = context.get_address() if context and context.gender else ""
    
    text = f"💚 *РЕЖИМ ДРУГ АКТИВИРОВАН*\n\n"
    text += f"Приятно познакомиться{f', {address}' if address else ''}!\n\n"
    text += "Теперь я буду:\n"
    text += "• Слушать и принимать без осуждения\n"
    text += "• Отражать твои чувства\n"
    text += f"• Быть рядом{f', {address}' if address else ''}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions")],
        [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
    await state.set_state(TestStates.results)


async def set_mode_trainer(callback: CallbackQuery, state: FSMContext):
    """Устанавливает режим ТРЕНЕР"""
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    
    if context:
        context.communication_mode = "trainer"
    
    await state.update_data(communication_mode="trainer")
    
    await callback.answer("✅ Режим ТРЕНЕР активирован")
    
    address = context.get_address() if context and context.gender else ""
    
    text = f"⚡ *РЕЖИМ ТРЕНЕР АКТИВИРОВАН*\n\n"
    text += f"Привет{f', {address}' if address else ''}!\n\n"
    text += "Теперь я буду:\n"
    text += "• Давать чёткие инструкции\n"
    text += "• Фокусироваться на действиях\n"
    text += "• Требовать результат"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions")],
        [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
    await state.set_state(TestStates.results)


async def ask_pretest(callback: CallbackQuery, state: FSMContext):
    """Вопрос до теста"""
    await callback.message.edit_text(
        "❓ *Задай свой вопрос*\n\n"
        "Я отвечу, но без твоего профиля ответ будет общим.\n\n"
        "_Напиши вопрос текстом или голосом._",
        parse_mode='Markdown'
    )
    await state.set_state(TestStates.pretest_question)


async def handle_pretest_question(message: Message, state: FSMContext):
    """Обработка вопроса до теста"""
    user_id = message.from_user.id
    context_obj = user_contexts.get(user_id)
    address = context_obj.get_address() if context_obj else ""
    
    await message.answer(
        f"Спасибо за вопрос{f', {address}' if address else ''}. Чтобы ответить точнее, мне нужно знать твой профиль. Пройди тест — это займёт 15 минут."
    )
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
    
    if not is_test_completed(data):
        await message.answer(
            "Сначала нужно пройти тест. Используй /start",
            parse_mode='Markdown'
        )
        return
    
    thinking = await message.answer("🤔 *Думаю над ответом...*", parse_mode='Markdown')
    
    response = await generate_response_with_full_context(user_id, message.text, data)
    
    context_obj = user_contexts.get(user_id)
    mode = context_obj.communication_mode if context_obj else "coach"
    
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
        [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
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
                "Попробуй еще раз или напиши текстом.",
                parse_mode='Markdown'
            )
            return
        
        response = await generate_response_with_full_context(user_id, recognized_text, data)
        
        context_obj = user_contexts.get(user_id)
        mode = context_obj.communication_mode if context_obj else "coach"
        
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
            [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
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
            "Попробуй еще раз или напиши текстом.",
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
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    
    data = await state.get_data()
    
    if context and is_test_completed(data):
        await show_main_menu_after_mode(callback.message, context)
    else:
        await show_main_menu(callback.message, context)
    
    await callback.answer()


async def back_to_results(callback: CallbackQuery, state: FSMContext):
    """Возврат к результатам"""
    await show_final_profile(callback, state)


async def cmd_test_voices(message: Message):
    """Команда /test_voices"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Только для администраторов")
        return
    
    await message.answer("Используй /test_yandex для теста голосов")


# ============================================
# CALLBACK ХЕНДЛЕР (ОБНОВЛЁННЫЙ)
# ============================================

async def callback_handler(callback: CallbackQuery, state: FSMContext):
    """Основной обработчик callback'ов"""
    
    data = callback.data
    
    try:
        # Новый экран "А ты вообще кто такой?"
        if data == "why_details":
            await why_details(callback, state)
        
        # Режимы
        elif data == "mode_hard":
            await choose_mode(callback, state, "hard")
        elif data == "mode_medium":
            await choose_mode(callback, state, "medium")
        elif data == "mode_soft":
            await choose_mode(callback, state, "soft")
        
        # Контекст
        elif data == "start_context":
            await start_context(callback, state)
        elif data == "skip_context":
            await skip_context(callback, state)
        elif data == "set_gender_male":
            await set_gender_male(callback, state)
        elif data == "set_gender_female":
            await set_gender_female(callback, state)
        
        # Выбор режима после теста
        elif data == "show_mode_selection":
            await show_mode_selection(callback, state)
        elif data == "set_mode_coach":
            await set_mode_coach(callback, state)
        elif data == "set_mode_friend":
            await set_mode_friend(callback, state)
        elif data == "set_mode_trainer":
            await set_mode_trainer(callback, state)
        
        # Навигация
        elif data == "show_benefits":
            await show_benefits(callback)
        elif data == "back_to_intro":
            await back_to_intro(callback)
        elif data == "ask_pretest":
            await ask_pretest(callback, state)
        elif data == "back_to_main":
            await back_to_main(callback, state)
        
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
        
        # Этап 5
        elif data == "show_stage_5_intro":
            await show_stage_5_intro(callback, state)
        elif data == "start_stage_5":
            await start_stage_5(callback, state)
        elif data.startswith("stage5_"):
            await handle_stage_5_answer(callback, state)
        
        # Результаты и конфайнмент
        elif data == "show_results":
            await show_final_profile(callback, state)
        elif data == "show_confinement":
            await show_confinement(callback, state)
        elif data == "show_intervention":
            await show_intervention(callback, state)
        elif data == "intervention_done":
            await intervention_done(callback, state)
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
        elif data == "restart_test":
            await state.clear()
            await back_to_intro(callback)
        elif data == "back_to_results":
            await back_to_results(callback, state)
        
        await callback.answer()
    
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            logger.info(f"Ignored 'message not modified' error")
            await callback.answer()
        else:
            logger.error(f"TelegramBadRequest: {e}")
            await callback.answer()
    except Exception as e:
        logger.error(f"Error in callback_handler: {e}")
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
    
    if OPENWEATHER_API_KEY:
        text += f"🌍 Погода будет автоматически подгружаться для пользователей\n"
    
    if YANDEX_API_KEY:
        text += f"🎙 Голоса: Филипп (коуч/тренер), Эрмил (друг)\n"
    
    await message.answer(text, parse_mode='Markdown')


async def cmd_test_yandex(message: Message):
    """Команда /test_yandex"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Только для администраторов")
        return
    
    test_text = "Привет! Это тестовое голосовое сообщение."
    status = await message.answer("🎧 Тестирую Yandex TTS...")
    
    results = []
    for mode in ["coach", "friend", "trainer"]:
        audio = await text_to_speech(test_text, mode)
        if audio:
            audio_file = BufferedInputFile(audio, filename=f"test_{mode}.ogg")
            await message.answer_voice(
                audio_file,
                caption=f"🎙 Режим: {COMMUNICATION_MODES[mode]['display_name']}",
                parse_mode='Markdown'
            )
            results.append(f"✅ {COMMUNICATION_MODES[mode]['display_name']}")
        else:
            results.append(f"❌ {COMMUNICATION_MODES[mode]['display_name']}")
        await asyncio.sleep(0.5)
    
    await status.delete()
    await message.answer("📊 *Результаты:*\n" + "\n".join(results), parse_mode='Markdown')


async def cmd_test_weather(message: Message):
    """Команда /test_weather - тест погоды"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Только для администраторов")
        return
    
    if not OPENWEATHER_API_KEY:
        await message.answer("❌ OPENWEATHER_API_KEY не настроен")
        return
    
    test_city = "Москва"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={test_city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    temp = data['main']['temp']
                    feels_like = data['main']['feels_like']
                    desc = data['weather'][0]['description']
                    humidity = data['main']['humidity']
                    wind = data['wind']['speed']
                    
                    text = f"✅ *Погода работает!*\n\n"
                    text += f"📍 Город: {test_city}\n"
                    text += f"🌡 Температура: {temp}°C (ощущается как {feels_like}°C)\n"
                    text += f"☁️ Описание: {desc}\n"
                    text += f"💧 Влажность: {humidity}%\n"
                    text += f"💨 Ветер: {wind} м/с"
                    
                    await message.answer(text, parse_mode='Markdown')
                else:
                    error_text = await response.text()
                    await message.answer(f"❌ Ошибка {response.status}: {error_text[:200]}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


async def cmd_tale(message: Message):
    """Команда /tale"""
    user_id = message.from_user.id
    data = user_data.get(user_id, {})
    
    if not is_test_completed(data):
        await message.answer("Сначала пройдите тест")
        return
    
    text = message.text.replace('/tale', '').strip()
    if not text:
        text = "рост"
    
    tale = tales.get_tale_for_issue(text)
    
    if tale:
        await message.answer(
            f"📖 *{tale['title']}*\n\n{tale['text'][:4000]}",
            parse_mode='Markdown'
        )
    else:
        await message.answer("Сказка не найдена")


async def cmd_context(message: Message, state: FSMContext):
    """Команда /context - принудительный сбор контекста"""
    user_id = message.from_user.id
    
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
    
    context = user_contexts[user_id]
    
    context.city = None
    context.gender = None
    context.age = None
    context.weather_cache = {}
    
    await message.answer("🔄 *Давай обновим твой контекст*", parse_mode='Markdown')
    await asyncio.sleep(0.5)
    
    await start_context(
        CallbackQuery(id="fake", from_user=message.from_user, message=message, data="start_context", chat_instance=""),
        state
    )


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
    
    if OPENWEATHER_API_KEY:
        logger.info("✅ OpenWeather API ключ найден")
    else:
        logger.warning("❌ OpenWeather API ключ не найден")


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
    dp.message.register(cmd_test_weather, Command("test_weather"))
    dp.message.register(cmd_tale, Command("tale"))
    dp.message.register(cmd_context, Command("context"))
    
    # Регистрируем обработчики сообщений с состояниями
    dp.message.register(handle_context_message, TestStates.awaiting_context)
    dp.message.register(handle_pretest_question, TestStates.pretest_question)
    dp.message.register(handle_question_message, TestStates.awaiting_question)
    dp.message.register(handle_voice_message, F.voice)
    dp.message.register(handle_unknown_message)
    
    # Регистрируем callback хендлер
    dp.callback_query.register(callback_handler)
    
    if DEEPSEEK_API_KEY:
        logger.info("✅ DeepSeek API ключ найден")
        asyncio.create_task(check_api_on_startup())
    else:
        logger.warning("❌ DeepSeek API ключ не найден")
    
    logger.info("Бот запущен...")
    print("\n" + "="*80)
    print("🚀 ВИРТУАЛЬНЫЙ ПСИХОЛОГ - МАТРИЦА ПОВЕДЕНИЙ 4×6 v8.5")
    print("="*80)
    print(f"👤 Ваш Telegram ID: {ADMIN_IDS[0] if ADMIN_IDS else 'не указан'}")
    print("📊 Команды: /stats, /apistatus, /test_yandex, /test_voices, /test_weather, /tale, /context")
    print("🎙 Распознавание: " + ("✅ Deepgram" if DEEPGRAM_API_KEY else "❌ нет"))
    print("🎙 Синтез речи: " + ("✅ Yandex" if YANDEX_API_KEY else "❌ нет"))
    print("🌍 Погода: " + ("✅ OpenWeather" if OPENWEATHER_API_KEY else "❌ нет"))
    print("🔄 Конфайнмент-моделирование: ✅")
    print("🧠 5 этапов тестирования: ✅")
    print("🧠 ГИПНОТЕРАПЕВТИЧЕСКИЙ МОДУЛЬ: ✅")
    print("👤 Полный контекст: город, погода, возраст, пол")
    print("🎭 Режимы: 🔮 КОУЧ | 💚 ДРУГ | ⚡ ТРЕНЕР")
    print("📅 Мотивация: через 5 мин и 24 часа")
    print("="*80 + "\n")
    
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    os.makedirs("stats", exist_ok=True)
    asyncio.run(main())
