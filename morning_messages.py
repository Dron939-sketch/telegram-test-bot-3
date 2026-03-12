"""
Модуль для утренних вдохновляющих сообщений (3 дня)
С ИИ-генерацией для Дней 2 и 3
"""

import asyncio
import logging
import random
import re
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any

import pytz
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from profiles import VECTORS, LEVEL_PROFILES
from services import call_deepseek

logger = logging.getLogger(__name__)


class MorningMessageManager:
    """Менеджер утренних сообщений с ИИ-генерацией"""
    
    def __init__(self):
        self.scheduled_tasks = {}  # {user_id: {day: task}}
        self.bot = None
        self.user_contexts = None
        self.user_data = None
    
    def set_bot(self, bot):
        """Устанавливает экземпляр бота"""
        self.bot = bot
    
    def set_contexts(self, user_contexts, user_data):
        """Устанавливает ссылки на глобальные хранилища"""
        self.user_contexts = user_contexts
        self.user_data = user_data
    
    async def schedule_morning_message(self, user_id: int, user_name: str, scores: dict, profile_data: dict):
        """
        Планирует серию из 3 утренних сообщений
        День 1: завтра в 9:00 (сценарий)
        День 2: послезавтра в 9:00 (ИИ)
        День 3: через 2 дня в 9:00 (ИИ)
        """
        # Отменяем все предыдущие задачи для этого пользователя
        self.cancel_all_user_tasks(user_id)
        
        # Получаем часовой пояс пользователя
        context = self.user_contexts.get(user_id) if self.user_contexts else None
        timezone = self._get_user_timezone(context)
        
        # Текущее время
        now_utc = datetime.now(pytz.UTC)
        now_local = now_utc.astimezone(timezone)
        
        # Планируем на 3 дня
        for day in range(1, 4):
            # Целевая дата (сегодня + day дней)
            target_local = now_local.replace(hour=9, minute=0, second=0, microsecond=0)
            target_local = target_local + timedelta(days=day)
            
            # Если сегодня уже после 9:00, то начинаем с завтра
            if day == 1 and now_local.hour >= 9:
                target_local = target_local + timedelta(days=1)
            
            target_utc = target_local.astimezone(pytz.UTC)
            seconds_until_target = (target_utc - now_utc).total_seconds()
            
            if seconds_until_target < 0:
                seconds_until_target = 60
            
            logger.info(
                f"📅 День {day} для пользователя {user_id}\n"
                f"   Отправка: {target_local.strftime('%Y-%m-%d %H:%M')}\n"
                f"   Через: {seconds_until_target/3600:.1f} часов"
            )
            
            # Создаем задачу
            task = asyncio.create_task(
                self._send_daily_message(
                    user_id, user_name, scores, profile_data,
                    seconds_until_target, timezone, day
                )
            )
            
            if user_id not in self.scheduled_tasks:
                self.scheduled_tasks[user_id] = {}
            
            self.scheduled_tasks[user_id][day] = task
    
    def _get_user_timezone(self, context) -> pytz.timezone:
        """Определяет часовой пояс пользователя"""
        if context and hasattr(context, 'timezone') and context.timezone:
            try:
                return pytz.timezone(context.timezone)
            except Exception as e:
                logger.warning(f"⚠️ Ошибка часового пояса {context.timezone}: {e}")
        
        return pytz.timezone("Europe/Moscow")
    
    async def _send_daily_message(self, user_id: int, user_name: str, scores: dict,
                                   profile_data: dict, delay_seconds: float,
                                   timezone: pytz.timezone, day: int):
        """Отправляет ежедневное сообщение"""
        try:
            await asyncio.sleep(delay_seconds)
            
            if not self.bot:
                logger.error(f"❌ Бот не инициализирован")
                return
            
            # Получаем актуальные данные
            context = self.user_contexts.get(user_id) if self.user_contexts else None
            mode = context.communication_mode if context else "coach"
            
            if context:
                await context.update_weather()
            
            # Генерируем текст для этого дня
            if day == 1:
                # День 1 - по сценарию (как в текущем коде)
                text = await self._generate_day1_text(
                    user_id, user_name, scores, profile_data, context, timezone
                )
            else:
                # Дни 2 и 3 - через ИИ
                text = await self._generate_ai_text(
                    user_id, user_name, scores, profile_data, context, timezone, day
                )
            
            clean_text = self._clean_text_for_voice(text)
            
            # Клавиатура для дня
            keyboard = self._get_keyboard_for_day(day)
            
            # Отправляем текст
            await self.bot.send_message(
                user_id,
                text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
            
            # Отправляем голос
            try:
                from services import text_to_speech
                audio_data = await text_to_speech(clean_text, mode)
                if audio_data:
                    audio_file = BufferedInputFile(audio_data, filename=f"day{day}.ogg")
                    await self.bot.send_voice(
                        user_id,
                        audio_file,
                        caption=f"🎙 День {day}"
                    )
            except Exception as e:
                logger.error(f"❌ Ошибка голоса: {e}")
            
            logger.info(f"✅ День {day} отправлен пользователю {user_id}")
            
        except asyncio.CancelledError:
            logger.info(f"⏰ День {day} для {user_id} отменён")
        except Exception as e:
            logger.error(f"❌ Ошибка дня {day} для {user_id}: {e}")
    
    def _get_keyboard_for_day(self, day: int) -> InlineKeyboardMarkup:
        """Возвращает клавиатуру для конкретного дня"""
        if day == 1:
            return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ ПРИНИМАЮ", callback_data="accept_myself")],
                [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")]
            ])
        elif day == 2:
            return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚡ СДЕЛАЛ", callback_data="did_action")],
                [InlineKeyboardButton(text="🎯 ЦЕЛЬ НА СЕГОДНЯ", callback_data="show_dynamic_destinations")]
            ])
        else:  # day 3
            return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌟 ПРОДОЛЖАТЬ", callback_data="continue_journey")],
                [InlineKeyboardButton(text="📊 МОЙ ПРОГРЕСС", callback_data="show_progress")]
            ])
    
    async def _generate_day1_text(self, user_id: int, user_name: str, scores: dict,
                                    profile_data: dict, context, timezone: pytz.timezone) -> str:
        """
        Генерирует текст для Дня 1 (по сценарию, как в текущем коде)
        """
        now_local = datetime.now(timezone)
        hour = now_local.hour
        
        # Приветствие
        greeting = self._get_greeting(hour, user_name, context)
        
        # Погода
        weather_text = self._get_weather_text(context, hour)
        
        # Вдохновение на основе профиля
        inspiration = self._get_profile_inspiration(scores)
        
        # Совет на день
        daily_tip = self._get_daily_tip(scores)
        
        text = f"""
🌅 <b>{greeting}!</b>

{weather_text}

{inspiration}

💡 <b>Совет на сегодня:</b>
{daily_tip}

✨ Хорошего дня!
"""
        return text.strip()
    
    async def _generate_ai_text(self, user_id: int, user_name: str, scores: dict,
                                  profile_data: dict, context, timezone: pytz.timezone,
                                  day: int) -> str:
        """
        Генерирует текст через DeepSeek для Дней 2 и 3
        """
        now_local = datetime.now(timezone)
        hour = now_local.hour
        weekday = now_local.weekday()
        
        # Определяем основной вектор (самый слабый)
        min_vector = min(scores.items(), key=lambda x: x[1])
        main_vector = min_vector[0]
        level = self._level(min_vector[1])
        
        # Описание вектора
        vector_names = {
            "СБ": "страх конфликтов и защиту границ",
            "ТФ": "отношения с деньгами и ресурсами",
            "УБ": "понимание мира и поиск смыслов",
            "ЧВ": "отношения с людьми и эмоциональные связи"
        }
        vector_desc = vector_names.get(main_vector, "психологический профиль")
        
        # Дни недели
        weekdays = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
        weekday_name = weekdays[weekday]
        
        # Тема дня
        day_themes = {
            2: "маленькие действия и эксперименты",
            3: "интеграция опыта и взгляд в будущее"
        }
        theme = day_themes.get(day, "продолжение пути")
        
        # Пол для обращения
        gender = context.gender if context else "other"
        address = "друг"
        if gender == "male":
            address = "брат"
        elif gender == "female":
            address = "сестрёнка"
        
        # Погода для контекста
        weather_context = ""
        if context and context.weather_cache:
            weather = context.weather_cache
            temp = weather.get('temp', 0)
            desc = weather.get('description', '')
            icon = weather.get('icon', '☁️')
            weather_context = f"Погода: {icon} {desc}, {temp}°C. "
        
        # Формируем промпт для ИИ
        prompt = f"""
Ты - психолог Фреди. Напиши утреннее мотивационное сообщение для пользователя.

ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ:
- Имя: {user_name}
- Обращение: {address}
- Пол: {gender}
- Основной вектор: {main_vector} ({vector_desc})
- Уровень по этому вектору: {level}/6
- День недели: {weekday_name}
- Время суток: {hour} часов
- {weather_context}

КОНТЕКСТ СООБЩЕНИЯ:
- Это ДЕНЬ {day} из 3-дневной серии
- Тема дня: {theme}
- День 1 уже был (он был о принятии себя)
- Сегодня нужно вдохновить на {theme}

ТРЕБОВАНИЯ К СООБЩЕНИЮ:
1. Тёплое, поддерживающее, без нравоучений
2. Учитывай профиль пользователя (вектор и уровень)
3. Используй обращение "{address}" в тексте
4. Добавь 1-2 риторических вопроса
5. Закончи ободряющей фразой
6. Длина: 3-5 абзацев
7. НЕ ИСПОЛЬЗУЙ звёздочки, решётки, markdown
8. Только текст, готовый для голосового озвучивания

Напиши сообщение:
"""
        
        try:
            response = await call_deepseek(prompt, max_tokens=800)
            if response:
                # Добавляем эмодзи и форматирование для чата
                formatted = self._format_ai_response(response, day, address)
                return formatted
        except Exception as e:
            logger.error(f"❌ Ошибка генерации ИИ: {e}")
        
        # Запасной вариант, если ИИ не ответил
        return await self._generate_fallback_text(day, user_name, address)
    
    def _format_ai_response(self, text: str, day: int, address: str) -> str:
        """Форматирует ответ ИИ для чата (добавляет эмодзи и структуру)"""
        # Убираем возможные markdown
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'__(.*?)__', r'\1', text)
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
        
        # Добавляем заголовок в зависимости от дня
        if day == 2:
            header = f"⚡ <b>Доброе утро, {address}!</b>\n\n"
        else:
            header = f"🌟 <b>Доброе утро, {address}!</b>\n\n"
        
        # Разбиваем на абзацы для читаемости
        paragraphs = text.split('\n\n')
        formatted_paragraphs = []
        for p in paragraphs:
            p = p.strip()
            if p:
                formatted_paragraphs.append(p)
        
        body = '\n\n'.join(formatted_paragraphs)
        
        return header + body
    
    async def _generate_fallback_text(self, day: int, user_name: str, address: str) -> str:
        """Запасной текст, если ИИ недоступен"""
        if day == 2:
            return f"""
🌅 <b>Доброе утро, {address}!</b>

Сегодня день маленьких шагов. Не надо геройства, просто одно маленькое действие в сторону того, что для тебя важно.

Помни: большие перемены начинаются с малого.

✨ Хорошего дня!
"""
        else:
            return f"""
🌅 <b>Доброе утро, {address}!</b>

Третий день нашей работы. Ты уже прошёл большой путь за это время.

Посмотри назад — ты изменился. Пусть немного, но это начало новой привычки — быть на своей стороне.

✨ Я рядом и всегда поддержу.
"""
    
    def _get_greeting(self, hour: int, user_name: str, context) -> str:
        """Возвращает приветствие"""
        if 5 <= hour < 12:
            greeting = "Доброе утро"
        elif 12 <= hour < 18:
            greeting = "Добрый день"
        elif 18 <= hour < 23:
            greeting = "Добрый вечер"
        else:
            greeting = "Доброй ночи"
        
        address = context.get_address() if context and hasattr(context, 'get_address') else ""
        
        if address:
            return f"{greeting}, {address}"
        else:
            return f"{greeting}, {user_name}"
    
    def _get_weather_text(self, context, hour: int) -> str:
        """Формирует текст о погоде (как в текущем коде)"""
        if not context or not hasattr(context, 'weather_cache') or not context.weather_cache:
            return "За окном новый день, полный возможностей."
        
        weather = context.weather_cache
        temp = weather.get('temp', 0)
        desc = weather.get('description', '')
        icon = weather.get('icon', '☁️')
        
        if 5 <= hour < 12:
            time_word = "утро"
        elif 12 <= hour < 18:
            time_word = "день"
        elif 18 <= hour < 23:
            time_word = "вечер"
        else:
            time_word = "ночь"
        
        if temp < -15:
            return f"{icon} Морозное {time_word}, {temp}°C. Даже в самый холод можно найти тепло внутри себя."
        elif temp < 0:
            return f"{icon} {desc}, {temp}°C. Холодно, но твоя внутренняя искра уже согревает."
        elif temp < 10:
            return f"{icon} Прохладное {time_word}, {temp}°C. Самое время для уютных мыслей и планов."
        elif temp < 20:
            return f"{icon} Свежее {time_word}, {temp}°C. Природа просыпается — как и твои новые возможности."
        elif temp < 30:
            return f"{icon} Теплое {time_word}, {temp}°C. Энергия так и плещет — лови момент!"
        else:
            return f"{icon} Жаркое {time_word}, {temp}°C. Даже солнце сегодня хочет тебя вдохновить."
    
    def _get_profile_inspiration(self, scores: dict) -> str:
        """Вдохновение на основе профиля (как в текущем коде)"""
        # ... существующий код ...
        return "Каждый день — это новая страница твоей истории."
    
    def _get_daily_tip(self, scores: dict) -> str:
        """Совет на день на основе профиля (как в текущем коде)"""
        # ... существующий код ...
        return "Найди 5 минут для себя и просто подыши."
    
    def _clean_text_for_voice(self, text: str) -> str:
        """Очищает текст для синтеза речи"""
        if not text:
            return text
        
        # Убираем HTML-теги
        text = re.sub(r'<[^>]+>', '', text)
        
        # Убираем эмодзи
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"
            u"\U0001F300-\U0001F5FF"
            u"\U0001F680-\U0001F6FF"
            u"\U0001F1E0-\U0001F1FF"
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            u"\U0001F900-\U0001F9FF"
            "]+", flags=re.UNICODE)
        text = emoji_pattern.sub(r'', text)
        
        # Убираем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _level(self, score: float) -> int:
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
    
    def cancel_all_user_tasks(self, user_id: int):
        """Отменяет все задачи пользователя"""
        if user_id in self.scheduled_tasks:
            for day, task in self.scheduled_tasks[user_id].items():
                task.cancel()
                logger.info(f"⏰ Отменён день {day} для пользователя {user_id}")
            del self.scheduled_tasks[user_id]
