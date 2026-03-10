"""
Модуль для утренних вдохновляющих сообщений
Отправляются на следующее утро после теста в 9:00
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from config import COMMUNICATION_MODES
from profiles import VECTORS, LEVEL_PROFILES

logger = logging.getLogger(__name__)

class MorningMessageManager:
    """Менеджер утренних сообщений"""
    
    def __init__(self):
        self.scheduled_tasks = {}  # {user_id: task}
        self.bot = None
        self.user_contexts = None
        self.user_data = None
    
    def set_bot(self, bot):
        self.bot = bot
    
    def set_contexts(self, user_contexts, user_data):
        """Устанавливает ссылки на глобальные хранилища"""
        self.user_contexts = user_contexts
        self.user_data = user_data
    
    async def schedule_morning_message(self, user_id: int, user_name: str, scores: dict, profile_data: dict):
        """
        Планирует отправку утреннего сообщения на следующий день в 9:00
        """
        # Отменяем предыдущую задачу для этого пользователя
        if user_id in self.scheduled_tasks:
            self.scheduled_tasks[user_id].cancel()
        
        # Рассчитываем время до следующего утра 9:00
        now = datetime.now()
        tomorrow_9am = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        # Если сейчас уже после 9:00, то добавляем еще один день
        if now.hour >= 9:
            tomorrow_9am = tomorrow_9am + timedelta(days=1)
        
        seconds_until_9am = (tomorrow_9am - now).total_seconds()
        
        logger.info(f"📅 Запланировано утреннее сообщение для пользователя {user_id} на {tomorrow_9am.strftime('%Y-%m-%d %H:%M')} (через {seconds_until_9am/3600:.1f} часов)")
        
        # Создаем задачу
        task = asyncio.create_task(
            self._send_morning_message(user_id, user_name, scores, profile_data, seconds_until_9am)
        )
        
        self.scheduled_tasks[user_id] = task
        return task
    
    async def _send_morning_message(self, user_id: int, user_name: str, scores: dict, profile_data: dict, delay_seconds: float):
        """Отправляет утреннее сообщение после задержки"""
        try:
            await asyncio.sleep(delay_seconds)
            
            if not self.bot:
                logger.error(f"❌ Бот не инициализирован для отправки утреннего сообщения пользователю {user_id}")
                return
            
            # Получаем актуальные данные
            context = self.user_contexts.get(user_id) if self.user_contexts else None
            mode = context.communication_mode if context else "coach"
            
            # Обновляем погоду
            if context:
                await context.update_weather()
            
            # Генерируем текст сообщения
            text = await self._generate_morning_text(user_id, user_name, scores, profile_data, context)
            
            # Создаем клавиатуру
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="☕ Доброе утро!", callback_data="morning_greeting")],
                [InlineKeyboardButton(text="🎯 ЦЕЛЬ НА СЕГОДНЯ", callback_data="show_dynamic_destinations")],
                [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")]
            ])
            
            # Отправляем текстовое сообщение
            await self.bot.send_message(
                user_id,
                text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
            
            # Отправляем голосовое сообщение
            from services import text_to_speech
            audio_data = await text_to_speech(text, mode)
            if audio_data:
                audio_file = BufferedInputFile(audio_data, filename="morning.ogg")
                await self.bot.send_voice(
                    user_id,
                    audio_file,
                    caption="🎙 Доброе утро!"
                )
            
            logger.info(f"✅ Утреннее сообщение отправлено пользователю {user_id}")
            
        except asyncio.CancelledError:
            logger.info(f"⏰ Утреннее сообщение для пользователя {user_id} отменено")
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке утреннего сообщения пользователю {user_id}: {e}")
    
    async def _generate_morning_text(self, user_id: int, user_name: str, scores: dict, profile_data: dict, context) -> str:
        """Генерирует текст утреннего сообщения"""
        
        # Обращение
        greeting = self._get_morning_greeting()
        address = context.get_address() if context and context.communication_mode == "friend" else ""
        
        if address:
            greeting = f"{greeting}, {address}"
        else:
            greeting = f"{greeting}, {user_name}"
        
        # Погода
        weather_text = ""
        if context and context.weather_cache:
            weather = context.weather_cache
            weather_text = self._get_weather_inspiration(weather)
        
        # Вдохновение на основе профиля
        inspiration = self._get_profile_inspiration(scores, profile_data)
        
        # Совет на день
        daily_tip = self._get_daily_tip(scores)
        
        # Собираем всё вместе
        text = f"""
🌅 <b>{greeting}!</b>

{weather_text}

{inspiration}

💡 <b>Совет на сегодня:</b>
{daily_tip}

✨ Хорошего дня!
"""
        
        return text.strip()
    
    def _get_morning_greeting(self) -> str:
        """Возвращает утреннее приветствие"""
        greetings = [
            "Доброе утро",
            "С добрым утром",
            "Утро доброе",
            "Прекрасного утра",
            "Солнечного утра"
        ]
        import random
        return random.choice(greetings)
    
    def _get_weather_inspiration(self, weather: dict) -> str:
        """Вдохновение на основе погоды"""
        temp = weather.get('temp', 0)
        desc = weather.get('description', '')
        icon = weather.get('icon', '☁️')
        
        if temp < -10:
            return f"{icon} Морозно, {temp}°C. Отличный день, чтобы завернуться в плед и помечтать о тепле."
        elif temp < 0:
            return f"{icon} За окном {desc}, {temp}°C. Холодно, но внутри тебя уже теплеет."
        elif temp < 10:
            return f"{icon} Прохладно, {temp}°C. Самое время для чашечки горячего чая и планов."
        elif temp < 20:
            return f"{icon} Свежо, {temp}°C. Природа просыпается — как и твои новые возможности."
        elif temp < 30:
            return f"{icon} Тепло, {temp}°C. Энергия так и плещет — лови момент!"
        else:
            return f"{icon} Жарко, {temp}°C. Даже солнце сегодня хочет тебя вдохновить."
    
    def _get_profile_inspiration(self, scores: dict, profile_data: dict) -> str:
        """Вдохновение на основе профиля"""
        if not scores:
            return "Каждый день — это новая страница твоей истории."
        
        # Находим сильные и слабые стороны
        sorted_vectors = sorted(scores.items(), key=lambda x: x[1])
        weakest = sorted_vectors[0] if sorted_vectors else ("СБ", 3)
        strongest = sorted_vectors[-1] if sorted_vectors else ("ЧВ", 3)
        
        weak_vector, weak_score = weakest
        strong_vector, strong_score = strongest
        
        weak_lvl = level(weak_score)
        strong_lvl = level(strong_score)
        
        # Вдохновение для слабой стороны
        weak_inspirations = {
            "СБ": [
                f"Твоя сила не в отсутствии страха, а в умении действовать несмотря на него.",
                f"Каждый раз, когда ты встречаешь вызов, ты становишься сильнее.",
                f"Ты уже справился со многими бурями — справишься и с этой."
            ],
            "ТФ": [
                f"Деньги — это просто энергия, и ты учишься ей управлять.",
                f"Твоя ценность не в кошельке, а в том, какой ты человек.",
                f"Изобилие начинается с благодарности за то, что уже есть."
            ],
            "УБ": [
                f"Мир полон загадок, и каждая разгаданная делает тебя мудрее.",
                f"Ты не обязан всё понимать сразу — просто наблюдай.",
                f"В хаосе всегда есть порядок, просто он пока не виден."
            ],
            "ЧВ": [
                f"Самые важные отношения — это отношения с собой.",
                f"Ты достоин любви просто потому, что ты есть.",
                f"Каждая встреча — это урок, который делает тебя ближе к себе."
            ]
        }
        
        # Вдохновение для сильной стороны
        strong_inspirations = {
            "СБ": "Твоя устойчивость — это твой суперсила. Используй её, чтобы защищать не только себя, но и свои мечты.",
            "ТФ": "Твой талант управлять ресурсами может изменить не только твою жизнь, но и жизнь вокруг.",
            "УБ": "Твоя способность видеть закономерности — дар. Доверяй своей интуиции.",
            "ЧВ": "Твоя эмпатия — это мост к другим людям. Не бойся открываться."
        }
        
        # Выбираем случайное вдохновение
        import random
        weak_text = random.choice(weak_inspirations.get(weak_vector, ["Сегодня — день новых возможностей."]))
        strong_text = strong_inspirations.get(strong_vector, "")
        
        return f"{weak_text}\n\n{strong_text}"
    
    def _get_daily_tip(self, scores: dict) -> str:
        """Совет на день на основе профиля"""
        if not scores:
            return "Найди 5 минут для себя и просто подыши."
        
        # Находим самое слабое место
        min_vector = min(scores.items(), key=lambda x: x[1])
        vector, score = min_vector
        lvl = level(score)
        
        tips = {
            "СБ": {
                1: "Сделай одно маленькое дело, которое откладывал.",
                2: "Скажи 'нет' тому, что тебе не нужно.",
                3: "Позволь себе не согласиться с кем-то сегодня.",
                4: "Выдохни и отпусти контроль над одной ситуацией.",
                5: "Защити не себя, а того, кто слабее.",
                6: "Используй свою силу, чтобы созидать, а не обороняться."
            },
            "ТФ": {
                1: "Запиши одну идею заработка, которая пришла в голову.",
                2: "Посмотри на свои расходы и найди одну статью для оптимизации.",
                3: "Поблагодари себя за то, что уже имеешь.",
                4: "Подумай, на что ты потратишь неожиданный доход.",
                5: "Сделай маленький шаг к финансовой цели.",
                6: "Поделись ресурсом с тем, кому он нужнее."
            },
            "УБ": {
                1: "Прочитай одну статью на новую тему.",
                2: "Задай вопрос 'почему' три раза подряд.",
                3: "Найди закономерность в своей неделе.",
                4: "Попробуй посмотреть на ситуацию глазами другого.",
                5: "Запиши одну мысль, которая кажется важной.",
                6: "Поделись своим пониманием с кем-то."
            },
            "ЧВ": {
                1: "Напиши близкому человеку просто так.",
                2: "Скажи комплимент незнакомцу.",
                3: "Выслушай кого-то, не перебивая.",
                4: "Попроси о помощи, если она нужна.",
                5: "Поблагодари того, кто это заслужил.",
                6: "Обними того, кто рядом."
            }
        }
        
        vector_tips = tips.get(vector, {})
        tip = vector_tips.get(lvl, "Сделай что-то хорошее для себя сегодня.")
        
        return tip


# Вспомогательная функция (дублируется из models.py для независимости)
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
