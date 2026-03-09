# models.py
"""
Классы-менеджеры и модели данных
"""
import os
import json
import logging
import aiohttp
import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from collections import defaultdict

# ВАЖНО: добавляем все необходимые импорты из aiogram
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from config import OPENWEATHER_API_KEY, COMMUNICATION_MODES, DESTINATIONS

logger = logging.getLogger(__name__)


# ============================================
# Вспомогательная функция level (ПЕРЕНЕСЕНА В НАЧАЛО)
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
        
        address = self.get_address() if self.communication_mode == "friend" else ""
        
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
                    weather_note = f"❄️ На улице морозно, {temp}°C. Одевайтесь теплее!"
                elif temp < 10:
                    weather_note = f"☁️ Прохладно, {temp}°C. Хорошего дня!"
                elif temp < 20:
                    weather_note = f"🍃 Свежо, {temp}°C. Отличная погода!"
                elif temp < 30:
                    weather_note = f"☀️ Тепло, {temp}°C. Прекрасный день!"
                else:
                    weather_note = f"🔥 Жарко, {temp}°C. Пейте больше воды!"
                
                base += f"\n\n{icon} {weather_note}"
        
        return base
    
    def get_address(self) -> str:
        """Возвращает обращение в зависимости от пола (только для режима ДРУГ)"""
        if self.gender == "male":
            return "братишка"
        elif self.gender == "female":
            return "сестрёнка"
        return ""
    
    async def ask_for_context(self) -> Tuple[Optional[str], Optional[InlineKeyboardMarkup]]:
        """Возвращает первый вопрос для сбора контекста"""
        if not self.city:
            self.awaiting_context = "city"
            return "🌆 В каком городе вы находитесь? (Это нужно для погоды)", InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_context")]
            ])
        
        if not self.gender:
            self.awaiting_context = "gender"
            return "👤 Укажите ваш пол", InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👨 Мужской", callback_data="set_gender_male")],
                [InlineKeyboardButton(text="👩 Женский", callback_data="set_gender_female")],
                [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_context")]
            ])
        
        if not self.age:
            self.awaiting_context = "age"
            return "📅 Сколько вам лет?", InlineKeyboardMarkup(inline_keyboard=[
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
                return False, "Пожалуйста, введите число", None
        
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
    
    def get_prompt_context(self) -> str:
        """Возвращает контекст для вставки в промпт AI"""
        lines = []
        
        if self.gender:
            gender_text = "мужской" if self.gender == "male" else "женский" if self.gender == "female" else "другой"
            lines.append(f"Пол пользователя: {gender_text}")
            if self.communication_mode == "friend":
                lines.append(f"Обращение: {self.get_address()}")
        if self.age:
            lines.append(f"Возраст: {self.age} лет")
        if self.city:
            lines.append(f"Город: {self.city}")
        
        day = self.get_day_context()
        lines.append(f"Время: {day['time_str']}, {day['weekday']}" + (" (выходной)" if day['is_weekend'] else ""))
        
        if self.weather_cache:
            lines.append(f"Погода: {self.weather_cache['icon']} {self.weather_cache['description']}, {self.weather_cache['temp']}°C")
        
        return "\n".join(lines)
    
    async def update_weather(self):
        """Обновляет погоду через OpenWeatherMap API"""
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
                        return True
        except Exception as e:
            logger.error(f"Ошибка получения погоды: {e}")
        return False
    
    def get_age_stage(self) -> str:
        """Возвращает возрастной этап"""
        if not self.age:
            return ""
        
        if self.age < 18:
            return "подростковый возраст"
        elif self.age < 25:
            return "молодость"
        elif self.age < 35:
            return "активная зрелость"
        elif self.age < 45:
            return "расцвет"
        elif self.age < 55:
            return "мудрая зрелость"
        elif self.age < 65:
            return "золотой возраст"
        else:
            return "возраст мудрости"


# ============================================
# КЛАСС ReminderManager
# ============================================

class ReminderManager:
    """Управляет напоминаниями для активных маршрутов"""
    
    def __init__(self):
        self.reminders = {}  # {user_id: [reminder1, reminder2, ...]}
        self.bot = None
    
    def set_bot(self, bot):
        self.bot = bot
    
    async def schedule_reminder(self, user_id: int, reminder_type: str, delay_minutes: int, data: dict = None):
        """
        Планирует напоминание
        reminder_type: 'motivation' | 'checkin' | 'deadline'
        """
        if not self.bot:
            return None
            
        task_id = f"{reminder_type}_{user_id}_{int(time.time())}"
        
        async def send_reminder():
            await asyncio.sleep(delay_minutes * 60)
            
            # Импортируем здесь, чтобы избежать циклического импорта
            from main import user_contexts
            
            user_context = user_contexts.get(user_id)
            address = user_context.get_address() if user_context and user_context.communication_mode == "friend" else ""
            
            # Текст зависит от типа напоминания
            if reminder_type == 'motivation':
                text = f"🧠 *Напоминание*\n\nКак продвигается ваш план? Нужна помощь?"
            elif reminder_type == 'checkin':
                text = f"👋 *Проверка связи*\n\nРасскажите, что получилось за это время?"
            elif reminder_type == 'deadline':
                hours = data.get('hours_left', 24) if data else 24
                text = f"⏰ *Дедлайн приближается*\n\nОсталось {hours} часов. Успеваете?"
            else:
                text = f"🔔 *Напоминание*"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ ВЫПОЛНИЛ", callback_data="route_step_done")],
                [InlineKeyboardButton(text="❓ НУЖНА ПОМОЩЬ", callback_data="smart_questions")],
                [InlineKeyboardButton(text="⏭️ ОТЛОЖИТЬ", callback_data="reminder_snooze")]
            ])
            
            await self.bot.send_message(user_id, text, reply_markup=keyboard)
        
        task = asyncio.create_task(send_reminder())
        
        if user_id not in self.reminders:
            self.reminders[user_id] = []
        
        self.reminders[user_id].append({
            'id': task_id,
            'type': reminder_type,
            'task': task,
            'scheduled_time': datetime.now() + timedelta(minutes=delay_minutes)
        })
        
        return task_id
    
    async def schedule_motivation_sequence(self, user_id: int, route_data: dict):
        """Планирует последовательность напоминаний для маршрута"""
        # Через 5 минут после начала
        await self.schedule_reminder(
            user_id=user_id,
            reminder_type='motivation',
            delay_minutes=5,
            data={'step': 1}
        )
        
        # Через 24 часа
        await self.schedule_reminder(
            user_id=user_id,
            reminder_type='checkin',
            delay_minutes=24*60,
            data={'step': 1}
        )
    
    def cancel_user_reminders(self, user_id: int):
        """Отменяет все напоминания пользователя"""
        if user_id in self.reminders:
            for reminder in self.reminders[user_id]:
                reminder['task'].cancel()
            del self.reminders[user_id]


# ============================================
# КЛАСС DestinationManager
# ============================================

class DestinationManager:
    """Управляет точками назначения и маршрутами"""
    
    def __init__(self):
        self.destinations = DESTINATIONS
    
    def get_destinations_for_mode(self, mode: str) -> dict:
        """Возвращает доступные точки для режима"""
        return self.destinations.get(mode, self.destinations["coach"])
    
    def recommend_by_profile(self, profile_code: str, mode: str) -> List[str]:
        """Рекомендует точки на основе профиля"""
        # Парсим профиль (СБ-2_ТФ-5_УБ-3_ЧВ-4)
        parts = profile_code.split('_')
        scores = {}
        for part in parts:
            if '-' in part:
                vec, val = part.split('-')
                scores[vec] = int(val)
        
        if not scores:
            return []
        
        # Находим самое слабое место
        weakest = min(scores.items(), key=lambda x: x[1])
        weak_vector = weakest[0]
        
        # Маппинг векторов на категории в зависимости от режима
        mapping = {
            "coach": {
                "СБ": ["blocks", "doubts"],
                "ТФ": ["values", "purpose"],
                "УБ": ["values", "purpose"],
                "ЧВ": ["choice", "priorities"]
            },
            "friend": {
                "СБ": ["fear", "anxiety"],
                "ТФ": ["self_love", "confidence"],
                "УБ": ["loneliness", "connect"],
                "ЧВ": ["connect", "friends", "boundaries"]
            },
            "trainer": {
                "СБ": ["stress", "anger"],
                "ТФ": ["budget", "savings", "invest"],
                "УБ": ["skills", "new_job"],
                "ЧВ": ["team", "promotion"]
            }
        }
        
        return mapping.get(mode, {}).get(weak_vector, [])


# ============================================
# КЛАСС Statistics
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
                "vectors": {"СБ": {}, "ТФ": {}, "УБ": {}, "ЧВ": {}},
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
            if lvl not in self.data["vectors"][vector]:
                self.data["vectors"][vector][lvl] = 0
            self.data["vectors"][vector][lvl] += 1
        
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
            for vector, vec_data in {"СБ": "Реакция на угрозу", "ТФ": "Деньги", "УБ": "Понимание мира", "ЧВ": "Отношения"}.items():
                text += f"\n*{vec_data}*\n"
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


# ============================================
# КЛАСС DelayedTaskManager
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
                    from main import user_contexts
                    from profiles import VECTORS, LEVEL_PROFILES
                    
                    if scores:
                        min_vector = min(scores.items(), key=lambda x: level(x[1]))
                        vector, score = min_vector
                        lvl = level(score)
                        profile = LEVEL_PROFILES.get(vector, {}).get(lvl, {})
                        
                        context = user_contexts.get(user_id)
                        address = context.get_address() if context and context.communication_mode == "friend" else ""
                        
                        message_text = (
                            f"🧠 *ЧЕРЕЗ {delay_minutes} МИНУТ ПОСЛЕ ТЕСТА*\n\n"
                            f"Слушайте{', ' + address if address else ''}...\n\n"
                            f"Ваше самое узкое место — {VECTORS[vector]['name']} (уровень {lvl}).\n"
                            f"{profile.get('pain_origin', '')}\n\n"
                            f"🎯 *Первый шаг:*\n"
                            f"{profile.get('immediate_tool', 'Начните с малого.')}\n\n"
                            f"⚡️ Я с вами на связи."
                        )
                    else:
                        context = user_contexts.get(user_id)
                        address = context.get_address() if context and context.communication_mode == "friend" else ""
                        message_text = f"Слушайте{', ' + address if address else ''}...\n\nКак вы? Я рядом."
                    
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
                    
                    from config import YANDEX_API_KEY
                    from services import text_to_speech
                    
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


# ============================================
# КЛАСС ConfinementModel9
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
        from profiles import VECTORS, LEVEL_PROFILES
        
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
        from profiles import VECTORS, LEVEL_PROFILES
        
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
        from profiles import VECTORS, LEVEL_PROFILES
        
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
        from profiles import LEVEL_PROFILES
        
        vectors = []
        for eid in effect_ids:
            elem = self.elements[eid]
            if elem and elem.vector:
                vectors.append(elem.vector)
        
        if 'СБ' in vectors and 'ТФ' in vectors and 'УБ' in vectors:
            return self._create_identity_element()
        return self._create_belief_element('common')
    
    def _create_identity_element(self) -> ConfinementElement:
        from profiles import LEVEL_PROFILES
        
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
        from profiles import LEVEL_PROFILES
        
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
