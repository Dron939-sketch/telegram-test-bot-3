#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ВИРТУАЛЬНЫЙ ПСИХОЛОГ - Матрица Поведений 4×6
ПОЛНАЯ ВЕРСИЯ с ИНТИМНЫМ ПРОФИЛЕМ, МЫСЛЯМИ ПСИХОЛОГА и ГОЛОСОВЫМИ ФУНКЦИЯМИ
+ КОНФАЙНМЕНТ-МОДЕЛИРОВАНИЕ (Мейстер А.Ю.)
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
import io
import struct
import wave
from typing import Optional, Dict, List, Any, Tuple
from statistics import mean
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime, timedelta
from collections import defaultdict
import math

# Импорты для конфайнмент-моделирования
from confinement_model import ConfinementModel9
from confinement_reporter import ConfinementReporter
from intervention_library import InterventionLibrary

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

# Хранилище данных пользователей
user_data: Dict[int, Dict[str, Any]] = {}
user_names: Dict[int, str] = {}  # Хранилище имен пользователей
user_contexts: Dict[int, 'UserContext'] = {}  # Хранилище контекстов

# Инициализация библиотеки интервенций
intervention_lib = InterventionLibrary()

# ─── Система уточняющих вопросов ───────────────────────────────────────────
CLARIFICATION_ZONES = [1.49, 2.00, 2.50, 3.00, 3.50]
CLARIFICATION_MARGIN = 0.12

# ══════════════════════════════════════════════
#  КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ
# ══════════════════════════════════════════════

class UserContext:
    """Полный контекст пользователя (город, погода, время, пол, возраст)"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.city = None
        self.timezone = "Europe/Moscow"  # По умолчанию
        self.timezone_offset = 3  # UTC+3 по умолчанию
        self.gender = None  # 'male', 'female'
        self.age = None
        self.last_context_update = None
        self.weather_cache = {}
        self.weather_cache_time = None
        
    def get_greeting(self, user_name: str = "") -> str:
        """Возвращает приветствие в зависимости от времени суток"""
        now = datetime.now()
        hour = now.hour
        
        greeting = ""
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
        """Возвращает контекст дня"""
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
    
    async def get_weather(self) -> dict:
        """Получает погоду для города пользователя"""
        if not self.city or not OPENWEATHER_API_KEY:
            return {}
        
        # Проверяем кэш (не старше 1 часа)
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
                        
                        # Переводим иконку в эмодзи
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
                            "wind": round(data['main']['wind']['speed']),
                            "icon": icon,
                            "pressure": data['main']['pressure']
                        }
                        self.weather_cache_time = datetime.now()
                        return self.weather_cache
        except Exception as e:
            logger.error(f"Ошибка получения погоды: {e}")
        return {}
    
    def get_weather_recommendation(self, weather: dict) -> str:
        """Дает рекомендацию по погоде"""
        if not weather:
            return ""
        
        temp = weather['temp']
        desc = weather['description']
        
        if temp < -20:
            return f"❄️ Морозно, {temp}°C. Сиди дома, пей чай, смотри кино. Мир подождет."
        elif temp < -10:
            return f"❄️ Холодно, {temp}°C. Одевайся теплее, не геройствуй."
        elif temp < 0:
            return f"☁️ Подморозило, {temp}°C. Шапку не забудь, простынешь - кто тебя лечить будет?"
        elif temp < 10:
            return f"🍂 Прохладно, {temp}°C. Самое время для уютного свитера и горячего какао."
        elif temp < 20:
            return f"🍃 Свежо, {temp}°C. Отличная погода для прогулки и разбора мыслей."
        elif temp < 30:
            return f"☀️ Теплынь, {temp}°C. Лови момент, гуляй, дыши, живи."
        else:
            return f"🔥 Жара, {temp}°C. Пей воду, ищи тень, не выгорай (в прямом смысле)."
    
    def get_age_stage(self) -> str:
        """Определяет жизненный этап по возрасту"""
        if not self.age:
            return ""
        
        if self.age < 18:
            return "Подростковый возраст — время поиска себя и первых серьезных выборов"
        elif self.age < 25:
            return "Молодость — время проб, ошибок и больших надежд"
        elif self.age < 35:
            return "Активная зрелость — строительство карьеры, отношений, семьи"
        elif self.age < 45:
            return "Расцвет — время реализации потенциала и передачи опыта"
        elif self.age < 55:
            return "Мудрая зрелость — время глубоких решений и осознанности"
        else:
            return "Возраст гармонии — время пожинать плоды и наслаждаться жизнью"
    
    def get_full_context(self, user_name: str) -> str:
        """Возвращает полный контекст для промпта"""
        day = self.get_day_context()
        context = []
        
        # Приветствие
        context.append(self.get_greeting(user_name))
        
        # День недели
        if day['is_weekend']:
            context.append(f"🎉 Сегодня {day['weekday']}, выходной — можно выдохнуть")
            if day['hour'] < 12:
                context.append("Можно поспать подольше, ты заслужил")
        else:
            context.append(f"💼 Сегодня {day['weekday']}, рабочий день")
            if day['hour'] < 9:
                context.append("Только начинается день, соберись с мыслями")
            elif day['hour'] > 18:
                context.append("День подходит к концу, пора подводить итоги")
        
        # Возраст
        age_stage = self.get_age_stage()
        if age_stage:
            context.append(f"📊 {age_stage}")
        
        # Город и погода
        if self.city:
            context.append(f"📍 Ты в {self.city}")
        
        return "\n".join(context)


# ══════════════════════════════════════════════
#  КОНСТАНТЫ ЭТАПОВ
# ══════════════════════════════════════════════

STAGE_ORDER = ["СБ", "ТФ", "УБ", "ЧВ"]

STAGE_INTROS = {
    "СБ": {
        "title": "ЭТАП 1 — РЕАКЦИЯ НА УГРОЗУ",
        "emoji": "🛡",
        "what": "Сейчас я исследую как вы реагируете когда на вас давят, угрожают или нарушают ваши границы.",
        "why": "Эта реакция определяет ваши отношения с начальством, партнёрами и миром в целом. Вы либо отстаиваете себя, либо терпите, либо уходите от конфликтов.",
        "what_you_learn": "Узнаете свой автоматизм под давлением и поймёте насколько он вам помогает или мешает.",
        "life_impact": "Эта реакция определяет ваши отношения с начальством, партнёрами и миром в целом. Вы либо отстаиваете себя, либо терпите, либо уходите от конфликтов.",
        "strategy_impact": "Ваш способ реагировать на давление становится вашей жизненной стратегией. Если вы замираете — вы упускаете возможности. Если атакуете — создаёте конфликты там где их можно избежать.",
        "trajectory": "От автоматических реакций (стопор, бегство) к осознанным (диалог, защита). Каждый следующий уровень даёт больше свободы выбора.",
        "questions_count": 8,
    },
    "ТФ": {
        "title": "ЭТАП 2 — ДОБЫЧА РЕСУРСОВ",
        "emoji": "💰",
        "what": "Сейчас я исследую как вы добываете деньги и материальные блага — вашу ресурсную стратегию.",
        "why": "Эта стратегия определяет не только доход, но и вашу реальную свободу. Нет ресурсов — нет выборов.",
        "what_you_learn": "Узнаете на каком уровне ваша стратегия и почему деньги ведут себя именно так.",
        "life_impact": "Ваша ресурсная стратегия определяет не только доход, но и вашу реальную свободу. Нет ресурсов — нет выборов.",
        "strategy_impact": "То как вы добываете ресурсы формирует всю вашу жизнь: от места жительства до отношений. Это базовая программа выживания.",
        "trajectory": "От зависимости и собирательства к управлению системами и созданию капитала.",
        "questions_count": 8,
    },
    "УБ": {
        "title": "ЭТАП 3 — ПОНИМАНИЕ МИРА",
        "emoji": "🔍",
        "what": "Сейчас я исследую как вы объясняете себе непонятное — кризисы, странное поведение людей, неудачи.",
        "why": "То как вы объясняете мир определяет что вы будете с ним делать. Разные объяснения — разные действия.",
        "what_you_learn": "Узнаете какая картина мира у вас в голове и даёт ли она вам контроль над ситуацией.",
        "life_impact": "Ваша картина мира определяет все ваши решения. Если мир враждебен — вы защищаетесь. Если мир случаен — вы ждёте.",
        "strategy_impact": "Объяснения становятся действиями. То как вы понимаете происходящее напрямую влияет на то, что вы делаете.",
        "trajectory": "От отрицания и магии к системному мышлению и построению моделей.",
        "questions_count": 8,
    },
    "ЧВ": {
        "title": "ЭТАП 4 — ОТНОШЕНИЯ С ЛЮДЬМИ",
        "emoji": "🤝",
        "what": "Последний этап. Исследую вашу стратегию в отношениях — как строите связи, просите, влияете.",
        "why": "Все ваши цели достигаются через людей или с людьми. Стратегия здесь решает многое.",
        "what_you_learn": "Узнаете ваш паттерн в отношениях и почему они складываются именно так.",
        "life_impact": "Все ваши цели достигаются через людей или с людьми. Отношения — это среда в которой вы живёте.",
        "strategy_impact": "Ваш способ строить связи определяет глубину отношений, ваше влияние и поддержку в трудные моменты.",
        "trajectory": "От зависимости и копирования к партнёрству и созданию сетей.",
        "questions_count": 8,
    },
}

STAGE_FEEDBACKS = {
    "СБ": {
        1: "Я вижу — в момент давления тело и разум как будто выключаются. Это не слабость. Это выученная реакция. И её можно изменить.",
        2: "Ваш ответ — уход. Вы умеете покидать неудобные ситуации. Вопрос: куда это вас приводит со временем?",
        3: "Вы соглашаетесь внешне — но внутри не согласны. Знакомо ощущение когда злость копится и потом взрывается?",
        4: "Вы умеете держать лицо. Это навык. Но есть цена — люди не знают настоящего вас.",
        5: "Вы умеете снижать напряжение. Это зрелая реакция. Есть только один вопрос — не гасите ли вы то что нужно было сказать?",
        6: "Вы умеете защищаться прямо. Редкий навык. Ключевой вопрос теперь — точность: когда это нужно, а когда достаточно диалога.",
    },
    "ТФ": {
        1: "Деньги пока приходят через других. Это честно. Давайте разберёмся что именно мешает изменить это.",
        2: "Вы умеете находить — но каждый раз заново. Нет системы которая работала бы без постоянного поиска.",
        3: "Вы умеете обменивать своё на чужое. Есть активность — но нет накопления. Начинаете каждый раз с нуля.",
        4: "Честный труд — надёжная база. Но вы — главный ресурс системы. Остановились — всё остановилось.",
        5: "У вас есть запас. Это даёт свободу говорить 'нет'. Следующий шаг — заставить запас работать.",
        6: "Вы выстраиваете системы. Это мощно. Риск один — потеря связи с реальностью. Системы нужно слышать снизу.",
    },
    "УБ": {
        1: "Непонятное игнорируется. Это даёт покой. Но то чего не понимаешь — начинает управлять тобой.",
        2: "Вы объясняете мир через судьбу и знаки. Это снижает тревогу. Но убирает вашу роль в происходящем.",
        3: "Вы доверяете экспертам. Это разумно. Риск: когда меняется эксперт — меняется вся ваша картина.",
        4: "Вы активно ищете объяснения. Энергии много. Но направлена она на поиск виноватых — не на решения.",
        5: "Вы проверяете сами. Это сила. Теперь важно из проверок делать обобщения — иначе данные есть, картины нет.",
        6: "Вы мыслите системами. Это редко. Проверяйте модели действиями — теория без практики остаётся теорией.",
    },
    "ЧВ": {
        1: "Несколько близких людей — это тепло и опора. Но если они исчезают — вы теряетесь. Это уязвимость.",
        2: "Вы хорошо подстраиваетесь. Люди принимают вас. Вопрос: кто вы когда не подстраиваетесь?",
        3: "Вас замечают. Это ценно. Но близость строится не на впечатлении — а на том что под ним.",
        4: "Вы хорошо понимаете людей — это редкий дар. Но используете его в одну сторону. Что если попробовать быть прямым?",
        5: "У вас есть настоящие партнёрства. Это основа. Теперь — масштаб. Мир больше вашего ближнего круга.",
        6: "Широкая сеть — сила. Но без нескольких глубоких точек опоры она рассыпается при первом испытании.",
    },
}

# ══════════════════════════════════════════════
#  ДАННЫЕ МАТРИЦЫ
# ══════════════════════════════════════════════

VECTORS = {
    "СБ": {
        "name": "Реакция на угрозу",
        "emoji": "🛡",
        "stimulus": "реакция когда на вас давят или угрожают",
        "levels": {
            1: {"name": "СТОПОР", "action": "замираешь", "desc": "Тело и разум отключаются при давлении"},
            2: {"name": "ИЗБЕГАНИЕ", "action": "убегаешь", "desc": "Уходишь от столкновения любым способом"},
            3: {"name": "КАПИТУЛЯЦИЯ", "action": "сдаёшься", "desc": "Соглашаешься лишь бы прекратить давление"},
            4: {"name": "МИМИКРИЯ", "action": "притворяешься", "desc": "Внешне спокоен, внутри скрываешь реакцию"},
            5: {"name": "УМИРОТВОРЕНИЕ", "action": "задабриваешь", "desc": "Ищешь компромисс, снижаешь напряжение"},
            6: {"name": "АТАКА", "action": "бьёшь в ответ", "desc": "Прямо защищаешь свои интересы"},
        }
    },
    "ТФ": {
        "name": "Добыча ресурсов",
        "emoji": "💰",
        "stimulus": "стратегия когда нужны деньги или материальные блага",
        "levels": {
            1: {"name": "ПАРАЗИТИЗМ", "action": "просишь", "desc": "Ждёшь что дадут, зависишь от чужой воли"},
            2: {"name": "СОБИРАТЕЛЬСТВО", "action": "ищешь готовое", "desc": "Берёшь что есть вокруг, ищешь удачу"},
            3: {"name": "ТОРГОВЛЯ", "action": "обмениваешь", "desc": "Меняешь своё на чужое, торгуешься"},
            4: {"name": "ТРУД", "action": "производишь", "desc": "Создаёшь сам, вкладываешь усилия"},
            5: {"name": "НАКОПЛЕНИЕ", "action": "копишь", "desc": "Создаёшь резерв, управляешь запасами"},
            6: {"name": "УПРАВЛЕНИЕ", "action": "организуешь", "desc": "Выстраиваешь системы, управляешь людьми"},
        }
    },
    "УБ": {
        "name": "Понимание мира",
        "emoji": "🔍",
        "stimulus": "ответ когда непонятно что происходит",
        "levels": {
            1: {"name": "ОТРИЦАНИЕ", "action": "игнорируешь", "desc": "Делаешь вид что непонятного нет"},
            2: {"name": "МАГИЯ", "action": "мистифицируешь", "desc": "Объясняешь судьбой, знаками, высшими силами"},
            3: {"name": "АВТОРИТЕТ", "action": "принимаешь", "desc": "Берёшь готовое объяснение от эксперта"},
            4: {"name": "ЗАГОВОР", "action": "ищешь умысел", "desc": "Ищешь кто виноват и зачем это делается"},
            5: {"name": "ЭМПИРИКА", "action": "проверяешь", "desc": "Собираешь данные, делаешь выводы сам"},
            6: {"name": "ТЕОРИЯ", "action": "систематизируешь", "desc": "Строишь модель, ищешь закономерности"},
        }
    },
    "ЧВ": {
        "name": "Отношения с людьми",
        "emoji": "🤝",
        "stimulus": "стратегия в отношении других людей",
        "levels": {
            1: {"name": "ЗАВИСИМОСТЬ", "action": "прилипаешь", "desc": "Не можешь без определённых людей"},
            2: {"name": "КОПИРОВАНИЕ", "action": "подражаешь", "desc": "Копируешь успешных, подстраиваешься под группу"},
            3: {"name": "ДЕМОНСТРАЦИЯ", "action": "показываешь себя", "desc": "Привлекаешь внимание, демонстрируешь себя"},
            4: {"name": "МАНИПУЛЯЦИЯ", "action": "используешь", "desc": "Добиваешься своего через влияние на других"},
            5: {"name": "ПАРТНЁРСТВО", "action": "сотрудничаешь", "desc": "Договариваешься, учитываешь интересы обоих"},
            6: {"name": "СЕТИ", "action": "строишь связи", "desc": "Создаёшь систему отношений, управляешь ею"},
        }
    }
}

# ══════════════════════════════════════════════
#  ВОПРОСЫ ТЕСТА
# ══════════════════════════════════════════════

QUESTIONS = {
    "СБ": [
        {
            "text": "Начальник кричит на вас несправедливо на совещании. Что происходит?",
            "options": [
                (1, "Теряюсь, слова не идут"),
                (2, "Придумываю причину уйти"),
                (3, "Киваю, но внутри кипит"),
                (4, "Спокойно говорю что думаю"),
            ]
        },
        # ... остальные вопросы СБ (все 8)
    ],

    "ТФ": [
        # ... все вопросы ТФ
    ],

    "УБ": [
        # ... все вопросы УБ
    ],

    "ЧВ": [
        # ... все вопросы ЧВ
    ]
}

# ══════════════════════════════════════════════
#  ЖИВЫЕ ПРОФИЛИ УРОВНЕЙ
# ══════════════════════════════════════════════

LEVEL_PROFILES = {
    "СБ": {
        1: {
            "archetype": "Замороженный",
            "archetype_desc": "Тот, у кого есть мнение — но нет голоса",
            "quote": "«Я открываю рот — и слова не идут. Потом дома думаю что надо было сказать. Уже поздно.»",
            "triggers": [
                "На тебя повысили голос — и ты буквально перестал думать. Мысли исчезли, тело застыло, слова не идут.",
                "После конфликта ты несколько часов прокручиваешь в голове что нужно было ответить. Злишься на себя.",
                "В момент давления плечи сами поднимаются к ушам, дыхание становится поверхностным, хочется стать меньше.",
                "Ты соглашаешься — хотя не согласен. И потом чувствуешь что предал сам себя.",
                "Совещание, конфликт, спор — и ты снова молчишь. Снова. Хотя знал что сказать.",
            ],
            "pain_origin": "Когда-то несогласие было опасным. Возражение приводило к боли — физической или эмоциональной. Тело запомнило намертво: молчи, это безопаснее. Теперь это работает автоматически — даже когда опасности давно нет.",
            "pain_costs": [
                "Тебя не слышат — потому что ты молчишь. Люди думают ты согласен и продолжают давить.",
                "Злость копится внутри и взрывается там где не надо — на близких, на случайных людей.",
                "Тебя воспринимают как человека которым можно управлять. Не из жестокости — просто потому что ты сам это транслируешь.",
            ],
            "immediate_tool": "Шаг 1. Поймай момент заморозки — когда чувствуешь что слова исчезли, отметь это телесно: где напряжение? Грудь? Горло? Плечи?\n\nШаг 2. Не пытайся сразу говорить. Скажи одно: «Подождите, мне нужна секунда». Это легально и это работает.\n\nШаг 3. Сделай один медленный выдох. Тело немного оттает.\n\nШаг 4. Спроси себя: «Что я хочу сказать?» Не надо говорить идеально — достаточно сказать что-то. Любое несогласие лучше молчания.\n\nШаг 5. После — запиши что хотел сказать. Это тренировка для следующего раза."
        },
        # ... остальные уровни СБ
    },
    "ТФ": {
        # ... все уровни ТФ
    },
    "УБ": {
        # ... все уровни УБ
    },
    "ЧВ": {
        # ... все уровни ЧВ
    },
}

# ══════════════════════════════════════════════
#  КОРРЕЛЯЦИИ
# ══════════════════════════════════════════════

CORRELATIONS = [
    {
        "condition": lambda s: s["ТФ"] <= 3 and s["СБ"] <= 3,
        "title": "Ресурсная ловушка → Пассивность перед угрозой",
        "explanation": "Нет ресурсов = нет реальных опций при угрозе. Невозможно сказать 'нет' начальнику если потеря работы — катастрофа. Невозможно выйти из токсичных отношений если финансово зависишь. Ваша реакция на угрозу не слабость характера — это рациональный ответ на реальное отсутствие выбора.",
        "solution": "Сначала ТФ. Ресурсный буфер на 3 месяца → реакция на угрозы изменится сама."
    },
    # ... остальные корреляции
]

# ══════════════════════════════════════════════
#  РЕКОМЕНДАЦИИ ПО УРОВНЯМ
# ══════════════════════════════════════════════

RECOMMENDATIONS = {
    "СБ": {
        1: [
            "Физические практики первичны: бокс, борьба, плавание.",
            "Тело должно знать что угроза переживаема.",
            "Начните с безопасных ситуаций: выскажите мнение там где нет реальных последствий.",
            "Работа с психологом по теме: диссоциация при стрессе.",
        ],
        # ... остальные уровни
    },
    # ... остальные вектора
}

# ─── Уточняющие вопросы для пограничных результатов ────────────────────────
CLARIFICATION_QUESTIONS = {
    "СБ": {
        "intro": (
            "⚡ *Один уточняющий вопрос*\n\n"
            "Ваши ответы по реакции на давление дали пограничный результат.\n\n"
            "Один вопрос — и картина станет точнее."
        ),
        "text": "Когда на вас давят — ваш первый внутренний импульс скорее:",
        "options": [
            (0, "Сжаться, исчезнуть, избежать"),
            (1, "Ответить, защититься, устоять"),
        ],
        "result": "✅ Картина прояснилась. Продолжаем."
    },
    # ... остальные вектора
}

# ══════════════════════════════════════════════
#  СТАТИСТИКА
# ══════════════════════════════════════════════

class Statistics:
    def __init__(self, stats_file="bot_stats.json"):
        self.stats_file = stats_file
        self.load()
    
    def load(self):
        """Загружает статистику из файла"""
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
        """Сохраняет статистику"""
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def register_start(self, user_id):
        """Регистрирует начало теста"""
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
        """Регистрирует завершение теста"""
        self.data["completed_tests"] += 1
        
        if str(user_id) in self.data["users"]:
            self.data["users"][str(user_id)]["completed"] = True
            self.data["users"][str(user_id)]["completed_at"] = datetime.now().isoformat()
            self.data["users"][str(user_id)]["scores"] = scores
            self.data["users"][str(user_id)]["levels"] = {k: level(v) for k, v in scores.items()}
        
        # По векторам
        for vector, score in scores.items():
            lvl = level(score)
            self.data["vectors"][vector][lvl] = self.data["vectors"][vector].get(lvl, 0) + 1
        
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.data["daily"]:
            self.data["daily"][today] = {"starts": 0, "completions": 0}
        self.data["daily"][today]["completions"] = self.data["daily"][today].get("completions", 0) + 1
        
        self.save()
    
    def get_stats_text(self):
        """Возвращает текст статистики для админа"""
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

# Инициализация статистики
stats = Statistics()

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

def get_profile_text(scores):
    """Формирует текст профиля без баров и цифр"""
    text = "📊 *ВАШ ПРОФИЛЬ*\n\n"
    
    for key, score in scores.items():
        vec = VECTORS[key]
        lvl = level(score)
        info = vec["levels"][lvl]
        
        text += f"{vec['emoji']} *{vec['name']}* — *{info['name']}*\n"
        text += f"└ {info['desc']}\n\n"
    
    return text

def get_priority_order(scores: dict) -> list:
    """Определяет порядок приоритетов"""
    tf = level(scores["ТФ"])
    if tf <= 2:
        rest = sorted([(k, v) for k, v in scores.items() if k != "ТФ"], key=lambda x: x[1])
        return ["ТФ"] + [r[0] for r in rest]
    else:
        return [k for k, _ in sorted(scores.items(), key=lambda x: x[1])]

def should_be_ironic(text: str) -> bool:
    """Определяет, стоит ли ответить с иронией"""
    ironic_markers = [
        "очевидно", "разумеется", "конечно", "естественно",
        "неужели", "серьёзно", "правда?", "интересно",
        "ха", "хм", "ну-ну", "ага"
    ]
    return any(marker in text.lower() for marker in ironic_markers)

# ══════════════════════════════════════════════
#  ФУНКЦИИ РАБОТЫ С DEEPGRAM API
# ══════════════════════════════════════════════

async def speech_to_text(voice_file_path: str) -> str:
    """
    Преобразует голосовое сообщение в текст через Deepgram STT API
    """
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
                    
                    if response.status in (400, 404):
                        logger.info("🔄 Пробуем альтернативную модель nova-2...")
                        params["model"] = "nova-2"
                        
                        async with session.post(
                            url,
                            params=params,
                            headers=headers,
                            data=audio_data,
                            timeout=timeout
                        ) as retry_response:
                            if retry_response.status == 200:
                                result = await retry_response.json()
                                try:
                                    transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
                                    logger.info(f"✅ Голос распознан (nova-2): {len(transcript)} символов")
                                    return transcript
                                except (KeyError, IndexError) as e:
                                    logger.error(f"❌ Ошибка парсинга ответа Deepgram: {e}")
                                    return ""
                    
                    return ""
                
                result = await response.json()
                
                try:
                    transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
                    logger.info(f"✅ Голос распознан: {len(transcript)} символов")
                    return transcript
                except (KeyError, IndexError) as e:
                    logger.error(f"❌ Ошибка парсинга ответа Deepgram: {e}")
                    return ""
                    
    except asyncio.TimeoutError:
        logger.error("⏰ Таймаут при обращении к Deepgram STT")
        return ""
    except aiohttp.ClientError as e:
        logger.error(f"🌐 Сетевая ошибка Deepgram: {e}")
        return ""
    except Exception as e:
        logger.error(f"💥 Неожиданная ошибка Deepgram STT: {e}")
        return ""

# ══════════════════════════════════════════════
#  ФУНКЦИИ РАБОТЫ С YANDEX SPEECHKIT
# ══════════════════════════════════════════════

async def text_to_speech(text: str, is_ironic: bool = False) -> bytes:
    """
    Преобразует текст в голос через Yandex SpeechKit
    с возможностью выбора ироничной интонации
    """
    YANDEX_API_KEY = os.environ.get("YANDEX_API_KEY", "")
    
    if not YANDEX_API_KEY:
        logger.error("❌ YANDEX_API_KEY не найден")
        return None
    
    if len(text) > 1000:
        text = text[:1000] + "..."
    
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
    }
    
    if is_ironic:
        voice = "filipp"  # эмоциональный, с иронией
        emotion = "good"  # для filipp доступна эмоция good
    else:
        voice = "oksana"  # заботливый женский голос для мотивации
        emotion = "neutral"
    
    data = {
        "text": text,
        "voice": voice,
        "emotion": emotion,
        "speed": 1.0,
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
                    
                    # Пробуем альтернативные голоса при ошибке
                    fallback_voices = [
                        {"voice": "oksana", "emotion": "neutral"},
                        {"voice": "alexandr", "emotion": "neutral"},
                        {"voice": "anton", "emotion": "neutral"},
                        {"voice": "ermil", "emotion": "good"},
                    ]
                    
                    for fallback in fallback_voices:
                        logger.info(f"🔄 Пробую запасной голос: {fallback['voice']}")
                        data["voice"] = fallback["voice"]
                        data["emotion"] = fallback["emotion"]
                        
                        async with session.post(
                            url,
                            headers=headers,
                            data=data,
                            timeout=timeout
                        ) as retry_response:
                            if retry_response.status == 200:
                                audio_data = await retry_response.read()
                                logger.info(f"✅ Аудио от {fallback['voice']} получено")
                                return audio_data
                    
                    return None
                    
    except Exception as e:
        logger.error(f"💥 Ошибка Yandex TTS: {e}")
        return None

# ══════════════════════════════════════════════
#  ФУНКЦИЯ call_deepseek
# ══════════════════════════════════════════════

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

def generate_smart_questions(scores):
    """Генерирует 4-5 вопросов на основе профиля"""
    questions = []
    
    tf = level(scores["ТФ"])
    sb = level(scores["СБ"])
    ub = level(scores["УБ"])
    cv = level(scores["ЧВ"])
    
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

def needs_clarification(avg: float) -> bool:
    """True если среднее в пограничной зоне ±0.12"""
    return any(abs(avg - b) <= CLARIFICATION_MARGIN for b in CLARIFICATION_ZONES)

def calc_synthetic_score(scores_list: list, target_avg: float) -> float:
    """Какой балл добавить для получения target_avg"""
    n = len(scores_list)
    synthetic = target_avg * (n + 1) - sum(scores_list)
    return max(1.0, min(4.0, synthetic))

def apply_clarification(avg: float, answer_val: int) -> float:
    """Сдвиг на ±0.15 в зависимости от ответа"""
    return round(avg - 0.15 if answer_val == 0 else avg + 0.15, 2)

def check_consistency(scores_list: list) -> bool:
    """Проверяет не хаотичны ли ответы. >1.3 = непоследовательны"""
    if len(scores_list) < 4:
        return True
    avg = mean(scores_list)
    variance = sum((x - avg) ** 2 for x in scores_list) / len(scores_list)
    std_dev = variance ** 0.5
    return std_dev <= 1.3

# ══════════════════════════════════════════════
#  ФУНКЦИИ ДЛЯ ТЕСТИРОВАНИЯ
# ══════════════════════════════════════════════

async def test_yandex_command(message: types.Message):
    """Тестирует Yandex TTS"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Только для администраторов")
        return
    
    test_text = "Привет! Это тестовое голосовое сообщение от Яндекс SpeechKit. Я буду отвечать на русском языке."
    status = await message.answer("🎧 Тестирую Yandex TTS...")
    
    audio = await text_to_speech(test_text)
    
    if audio:
        audio_file = BufferedInputFile(audio, filename="test.ogg")
        await message.answer_voice(
            audio_file,
            caption="✅ Yandex SpeechKit работает! Голос: Оксана"
        )
        await status.delete()
    else:
        await status.edit_text(
            "❌ Yandex SpeechKit не работает.\n"
            "Проверьте:\n"
            "1. Правильно ли указан YANDEX_API_KEY в .env\n"
            "2. Есть ли средства на аккаунте Яндекс Облака"
        )

async def test_voices_command(message: types.Message):
    """Тестирует разные голоса Yandex TTS"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Только для администраторов")
        return
    
    if not YANDEX_API_KEY:
        await message.answer("❌ YANDEX_API_KEY не настроен")
        return
    
    test_text = "Ну, допустим, вы действительно так считаете. Интересная мысль."
    status = await message.answer("🎧 Тестирую актуальные голоса Yandex...")
    
    voices_to_test = [
        ("oksana", "neutral", "Оксана (женский, заботливый)"),
        ("alena", "neutral", "Алена (женский, нейтральный)"),
        ("filipp", "good", "Филипп (мужской, ироничный)"),
        ("ermil", "good", "Эрмил (мужской, добрый)"),
        ("alexandr", "neutral", "Александр (мужской)"),
        ("anton", "neutral", "Антон (мужской, нейтральный)"),
    ]
    
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
    }
    
    results = []
    for voice, emotion, description in voices_to_test:
        data = {
            "text": test_text,
            "voice": voice,
            "emotion": emotion,
            "speed": 1.0,
            "format": "oggopus",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize",
                    headers=headers,
                    data=data,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        audio_file = BufferedInputFile(audio_data, filename=f"{voice}_{emotion}.ogg")
                        await message.answer_voice(
                            audio_file,
                            caption=f"🎙 *{description}*",
                            parse_mode='Markdown'
                        )
                        results.append(f"✅ {description}")
                        await asyncio.sleep(0.5)
                    else:
                        error = await response.text()
                        results.append(f"❌ {description}: {response.status}")
        except Exception as e:
            results.append(f"❌ {description}: {str(e)[:50]}")
    
    summary = "📊 *РЕЗУЛЬТАТЫ ТЕСТА ГОЛОСОВ*\n\n" + "\n".join(results)
    await message.answer(summary, parse_mode='Markdown')
    await status.delete()

# ══════════════════════════════════════════════
#  ФУНКЦИИ КОНТЕКСТА И МОТИВАЦИИ
# ══════════════════════════════════════════════

async def ask_for_context(callback: types.CallbackQuery):
    """Запрашивает у пользователя контекстные данные"""
    user_id = callback.from_user.id
    user_name = user_names.get(user_id, "друг")
    
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
    
    text = (
        f"🌍 *ДАВАЙ ПОЗНАКОМИМСЯ ПОБЛИЖЕ, {user_name.upper()}*\n\n"
        f"Чтобы я мог заботиться о тебе по-настоящему, расскажи немного о себе:\n\n"
        f"📍 *Город* — чтобы знать погоду и время\n"
        f"👤 *Пол* — чтобы правильно обращаться\n"
        f"🎂 *Возраст* — чтобы учитывать жизненный этап\n\n"
        f"_Напиши в формате:_\n"
        f"`Москва, м, 35`\n"
        f"или просто город, остальное заполним позже:\n\n"
        f"_(м/ж — мужской/женский)_"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Пропустить", callback_data="skip_context")],
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_menu")]
    ])
    
    if user_id in user_data:
        user_data[user_id]["awaiting"] = "context"
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def skip_context(callback: types.CallbackQuery):
    """Пропускает ввод контекста"""
    await callback.message.edit_text(
        "✅ Хорошо, продолжим без контекста. Если захочешь рассказать о себе позже — нажми кнопку в меню.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧠 К ТЕСТУ", callback_data="start_test")],
            [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="back_to_menu")]
        ])
    )

async def handle_context_input(message: types.Message):
    """Обрабатывает ввод контекстных данных"""
    user_id = message.from_user.id
    text = message.text.strip()
    user_name = user_names.get(user_id, "друг")
    
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
    
    context = user_contexts[user_id]
    
    # Парсим ввод
    parts = [p.strip() for p in text.split(',')]
    
    if len(parts) >= 1:
        context.city = parts[0]
    
    if len(parts) >= 2:
        gender = parts[1].lower()
        if gender in ['м', 'муж', 'мужской', 'male', 'm']:
            context.gender = 'male'
        elif gender in ['ж', 'жен', 'женский', 'female', 'f']:
            context.gender = 'female'
    
    if len(parts) >= 3:
        try:
            context.age = int(re.sub(r'[^0-9]', '', parts[2]))
        except:
            pass
    
    weather = await context.get_weather()
    
    response = f"✅ *Отлично, {user_name}! Я запомнил:*\n\n"
    response += f"📍 Город: {context.city or 'не указан'}\n"
    if context.gender:
        response += f"👤 Пол: {'Мужской' if context.gender == 'male' else 'Женский'}\n"
    if context.age:
        response += f"🎂 Возраст: {context.age}\n"
        response += f"📊 {context.get_age_stage()}\n"
    
    if weather:
        response += f"\n{context.get_weather_recommendation(weather)}\n"
        response += f"{weather['icon']} {weather['temp']}°C, {weather['description']}"
    
    day = context.get_day_context()
    response += f"\n\n📅 Сегодня {day['weekday']}, {day['day']} {day['month']}, {day['time_str']}"
    
    if day['is_weekend']:
        response += "\n🎉 Выходной — отдыхай!"
    else:
        response += "\n💼 Рабочий день — соберись!"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 К ТЕСТУ", callback_data="start_test")],
        [InlineKeyboardButton(text="🏠 В МЕНЮ", callback_data="back_to_menu")]
    ])
    
    await message.answer(response, parse_mode='Markdown', reply_markup=keyboard)
    
    if user_id in user_data:
        user_data[user_id]["awaiting"] = None

def generate_motivation_message(user_id: int, scores: dict, user_name: str = "друг") -> str:
    """Генерирует персонализированное мотивирующее сообщение"""
    
    tf_level = level(scores["ТФ"])
    sb_level = level(scores["СБ"])
    ub_level = level(scores["УБ"])
    cv_level = level(scores["ЧВ"])
    
    levels = {
        "ТФ": (tf_level, VECTORS["ТФ"]["name"], VECTORS["ТФ"]["emoji"]),
        "СБ": (sb_level, VECTORS["СБ"]["name"], VECTORS["СБ"]["emoji"]),
        "УБ": (ub_level, VECTORS["УБ"]["name"], VECTORS["УБ"]["emoji"]),
        "ЧВ": (cv_level, VECTORS["ЧВ"]["name"], VECTORS["ЧВ"]["emoji"]),
    }
    
    weakest = min(levels.items(), key=lambda x: x[1][0])
    weakest_key, (weakest_level, weakest_name, weakest_emoji) = weakest
    
    next_level = weakest_level + 1
    if next_level > 6:
        next_level = 6
    
    next_level_info = VECTORS[weakest_key]["levels"][next_level]
    current_level_info = VECTORS[weakest_key]["levels"][weakest_level]
    profile = LEVEL_PROFILES.get(weakest_key, {}).get(weakest_level, {})
    
    greetings = [
        f"Слушай, {user_name}...",
        f"Знаешь, {user_name}, что я подумал?",
        f"{user_name}, давай начистоту:",
        f"Эй, {user_name}, есть разговор:",
    ]
    
    main_texts = {
        "СБ": f"Твой главный тормоз — реакция на угрозу. Ты сейчас на уровне «{current_level_info['name']}».",
        "ТФ": f"Твоя ахиллесова пята — ресурсы. Ты на уровне «{current_level_info['name']}».",
        "УБ": f"Самое узкое место — как ты понимаешь мир. Уровень «{current_level_info['name']}».",
        "ЧВ": f"Больнее всего бьет по отношениям. Уровень «{current_level_info['name']}».",
    }
    
    tips = {
        "СБ": {
            1: "Начни с малого: в безопасной обстановке скажи 'нет' хотя бы один раз.",
            2: "В следующий раз, когда захочется уйти, останься на 2 минуты дольше.",
            3: "Вместо автоматического 'да' попробуй сказать 'мне нужно подумать'.",
            4: "Выбери одного человека, которому доверяешь, и скажи ему одну правду о своих чувствах.",
            5: "В следующий раз, когда будешь гасить конфликт, спроси себя: 'А может, этому конфликту нужно случиться?'",
            6: "Перед тем как атаковать, спроси себя: 'Что я хочу получить в итоге?'",
        },
        "ТФ": {
            1: "Найди один навык, который у тебя есть, и предложи его кому-то за деньги.",
            2: "Посмотри на свои подработки за последний год. Что повторялось?",
            3: "Открой отдельный счет и переведи туда 10% от следующего дохода.",
            4: "Напиши инструкцию для одной своей задачи.",
            5: "Раздели свои накопления на три части: запас, капитал, инвестиции.",
            6: "Раз в месяц общайся с теми, кто работает на нижних уровнях твоей системы.",
        },
        "УБ": {
            1: "Выбери одну тему, которую ты избегаешь, и удели ей 10 минут.",
            2: "Вспомни последнее 'знаковое' событие и объясни его без мистики.",
            3: "Возьми одно утверждение авторитета и проверь его сам.",
            4: "В следующий раз, когда найдешь виноватого, спроси себя: 'Что я могу сделать?'",
            5: "Найди три повторяющихся наблюдения и сформулируй принцип.",
            6: "Возьми одну свою теорию и проверь ее действием.",
        },
        "ЧВ": {
            1: "Сделай сегодня одно действие самостоятельно.",
            2: "В одном разговоре скажи мнение, которое расходится с собеседником.",
            3: "Выбери одного человека и проведи с ним час без телефона.",
            4: "Попроси о чем-то прямо, без манипуляций.",
            5: "Познакомься с одним новым человеком из другой сферы.",
            6: "Выбери трех ключевых людей и инвестируй в них время.",
        }
    }
    
    motivation_phrases = [
        f"Я не просто так тебя гружу — я вижу в тебе потенциал. Между «{current_level_info['name']}» и «{next_level_info['name']}» — не пропасть, а несколько конкретных шагов.",
        f"Ты уже прошел тест, а это значит, что готов что-то менять. Я в тебя верю, {user_name}.",
        f"Знаешь, в чем твоя суперсила? В том, что ты дошел до конца теста.",
        f"Слушай, {user_name}, я понимаю, что может быть страшно. Но страх проходит, а сделанное остается.",
    ]
    
    greeting = random.choice(greetings)
    main_text = main_texts[weakest_key]
    motivation_phrase = random.choice(motivation_phrases)
    tip = tips[weakest_key][weakest_level]
    
    text = (
        f"🧠 *ЧЕРЕЗ 5 МИНУТ ПОСЛЕ ТЕСТА*\n\n"
        f"{greeting}\n\n"
        f"{main_text} {weakest_level}/6 — это когда {current_level_info['desc'].lower()}.\n\n"
        f"🎯 *Цель:* уровень {next_level}/6 — «{next_level_info['name']}» — это когда {next_level_info['desc'].lower()}.\n\n"
        f"{motivation_phrase}\n\n"
        f"🛠 *Что делать прямо сейчас:*\n{tip}\n\n"
        f"⚡️ *Помни:* я с тобой на связи 24/7. Напиши, если что."
    )
    
    return text

# ══════════════════════════════════════════════
#  МЕНЕДЖЕР ОТЛОЖЕННЫХ ЗАДАЧ
# ══════════════════════════════════════════════

class DelayedTaskManager:
    """Управляет отложенными задачами"""
    
    def __init__(self):
        self.tasks = {}
        self.bot_instance = None
        self.running = False
    
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
                    message_text = generate_motivation_message(user_id, scores, user_name)
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions")],
                        [InlineKeyboardButton(text="🧠 К ПРОФИЛЮ", callback_data="show_results")],
                        [InlineKeyboardButton(text="📈 ЧТО ДАЛЬШЕ?", callback_data="more_info")]
                    ])
                    
                    await self.bot_instance.send_message(
                        user_id,
                        message_text,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                    
                    if YANDEX_API_KEY:
                        audio_data = await text_to_speech(message_text, is_ironic=False)
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
                        [InlineKeyboardButton(text="🧠 К ПРОФИЛЮ", callback_data="show_results")],
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

async def test_motivation_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Только для администраторов")
        return
    
    test_scores = {
        "СБ": 2.3,
        "ТФ": 3.1,
        "УБ": 2.8,
        "ЧВ": 3.5
    }
    
    mot_text = generate_motivation_message(ADMIN_IDS[0], test_scores, "Тестовый")
    
    await message.answer(mot_text, parse_mode='Markdown')
    
    audio_data = await text_to_speech(mot_text, is_ironic=False)
    if audio_data:
        audio_file = BufferedInputFile(audio_data, filename="motivation_test.ogg")
        await message.answer_voice(
            audio_file,
            caption="🎙 *Тестовое мотивационное сообщение*",
            parse_mode='Markdown'
        )

async def show_tasks_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Только для администраторов")
        return
    
    if not task_manager.tasks:
        await message.answer("📭 Нет запланированных задач")
        return
    
    text = "📋 *ЗАПЛАНИРОВАННЫЕ ЗАДАЧИ*\n\n"
    for task_id, task_info in task_manager.tasks.items():
        user_id = task_info["user_id"]
        task_type = task_info["type"]
        scheduled = task_info["scheduled_time"].strftime("%d.%m %H:%M")
        text += f"• {task_type} для {user_id} в {scheduled}\n"
    
    await message.answer(text, parse_mode='Markdown')

# ══════════════════════════════════════════════
#  ФУНКЦИИ ЭТАПОВ
# ══════════════════════════════════════════════

async def show_stage_intro(callback: types.CallbackQuery, stage_key: str):
    user_id = callback.from_user.id
    
    if user_id not in user_data:
        user_data[user_id] = {
            "stage": "menu",
            "scores": {k: [] for k in VECTORS},
            "current_stage": None,
            "current_question": 0,
            "profile_complete": False,
            "logged": False,
            "intimate_profile": None,
            "ai_analysis": None,
            "ai_recommendations": None,
            "history": [],
            "awaiting": None,
            "confinement_model": None,
            "confinement_history": []
        }
    
    user_data[user_id]["current_stage"] = stage_key
    user_data[user_id]["current_question"] = 0
    
    intro = STAGE_INTROS[stage_key]
    vec = VECTORS[stage_key]
    stage_num = STAGE_ORDER.index(stage_key) + 1
    
    text = (
        f"{vec['emoji']} *{intro['title']}*\n"
        f"{'━' * 18}\n\n"
        f"🔍 *Что я исследую:*\n"
        f"{intro['what']}\n\n"
        f"📝 *{intro['questions_count']} вопросов*\n\n"
        f"💭 _Выбирайте первый ответ который приходит в голову._"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"Начать этап {stage_num}", callback_data=f"begin_stage_{stage_key}"),
            InlineKeyboardButton(text="🔍 Детали", callback_data=f"stage_details_{stage_key}")
        ]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise

async def show_stage_details(callback: types.CallbackQuery, stage_key: str):
    intro = STAGE_INTROS[stage_key]
    vec = VECTORS[stage_key]
    
    text = (
        f"{vec['emoji']} *{intro['title']}*\n"
        f"{'━' * 18}\n\n"
        f"🔍 *Что я исследую:*\n"
        f"{intro['what']}\n\n"
        f"💫 *Как это влияет на жизнь:*\n"
        f"{intro['life_impact']}\n\n"
        f"🎯 *Влияние на стратегию:*\n"
        f"{intro['strategy_impact']}\n\n"
        f"📈 *Траектория развития:*\n"
        f"{intro['trajectory']}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад к этапу", callback_data=f"stage_intro_{stage_key}")]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise

async def show_stage_feedback(callback: types.CallbackQuery, stage_key: str):
    user_id = callback.from_user.id
    user = user_data[user_id]

    scores_list = user["scores"][stage_key]
    
    if not scores_list:
        await callback.message.edit_text(
            f"{VECTORS[stage_key]['emoji']} *Этап не пройден*\n\n"
            f"Похоже, вы не ответили ни на один вопрос. Попробуйте начать этап заново.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Начать заново", callback_data=f"begin_stage_{stage_key}")],
                [InlineKeyboardButton(text="◀️ В меню", callback_data="back_to_menu")]
            ]),
            parse_mode='Markdown'
        )
        return

    avg = round(mean(scores_list), 2)

    consistency_override = user.get(f"{stage_key}_consistency_override", False)
    if not consistency_override and not check_consistency(scores_list):
        await show_consistency_warning(callback, stage_key)
        return

    already_clarified = user.get(f"{stage_key}_clarified", False)
    if needs_clarification(avg) and not already_clarified:
        user[f"{stage_key}_pending_avg"] = avg
        await show_clarification_intro(callback, stage_key)
        return

    lvl = level(avg)
    vec = VECTORS[stage_key]
    level_info = vec["levels"][lvl]
    feedback = STAGE_FEEDBACKS[stage_key].get(lvl, "Анализирую ваши ответы...")
    
    profile = LEVEL_PROFILES.get(stage_key, {}).get(lvl, {})
    archetype_block = ""
    if profile:
        archetype_block = (
            f"🎭 *{profile['archetype']}*\n"
            f"_{profile['archetype_desc']}_\n\n"
            f"💬 {profile['quote']}\n"
        )
    
    stage_num = STAGE_ORDER.index(stage_key) + 1
    stages_done = "✅ " * stage_num + "⬜ " * (4 - stage_num)
    
    text = (
        f"{vec['emoji']} *ЭТАП {stage_num} ЗАВЕРШЁН*\n"
        f"{'━' * 18}\n\n"
        f"{stages_done}\n\n"
        f"*{vec['name']}*\n"
        f"Уровень: *{lvl}/6 — {level_info['name']}*\n"
        f"{archetype_block}"
        f"\n_{feedback}_\n\n"
    )
    
    next_stage_idx = STAGE_ORDER.index(stage_key) + 1
    
    if next_stage_idx < len(STAGE_ORDER):
        next_stage = STAGE_ORDER[next_stage_idx]
        next_intro = STAGE_INTROS[next_stage]
        text += f"Следующий этап: {next_intro['emoji']} *{next_intro['title']}*"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"Перейти к этапу {next_stage_idx + 1} →",
                callback_data=f"stage_intro_{next_stage}"
            )]
        ])
    else:
        text += "Все этапы пройдены. Формирую ваш профиль..."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🧠 Посмотреть мой профиль →",
                callback_data="show_results"
            )]
        ])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise

async def send_next_question(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = user_data[user_id]
    
    current_stage = user.get("current_stage")
    if not current_stage:
        await callback.message.edit_text(
            "⚠️ Ошибка: этап теста не определен. Начните заново.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔪 Начать тест", callback_data="start_test")]
            ])
        )
        return
    
    current_q_idx = user.get("current_question", 0)
    stage_questions = QUESTIONS.get(current_stage, [])
    
    if not stage_questions:
        await callback.message.edit_text(
            "⚠️ Ошибка: вопросы не найдены. Начните заново.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔪 Начать тест", callback_data="start_test")]
            ])
        )
        return
    
    total_in_stage = len(stage_questions)
    
    progress = current_q_idx
    progress_bar = "█" * progress + "░" * (total_in_stage - progress)
    
    vec = VECTORS[current_stage]
    
    if current_q_idx < total_in_stage:
        question = stage_questions[current_q_idx]
        
        keyboard = []
        for score, option_text in question["options"]:
            keyboard.append([InlineKeyboardButton(
                text=option_text[:65],
                callback_data=f"answer_{score}"
            )])
        
        text = (
            f"{vec['emoji']} *{vec['name'].upper()}*\n\n"
            f"*{question['text']}*\n"
            f"{'━' * 18}\n"
            f"▸ Вопрос {current_q_idx + 1}/{total_in_stage} • {progress_bar}"
        )
        
        try:
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode='Markdown'
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                logger.info(f"Ignored 'message not modified' error")
            else:
                raise
        
        user["current_question"] += 1
    else:
        await show_stage_feedback(callback, current_stage)

async def show_clarification_intro(callback: types.CallbackQuery, stage_key: str):
    cq = CLARIFICATION_QUESTIONS[stage_key]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Ответить →", callback_data=f"clarify_show_{stage_key}")
    ]])
    try:
        await callback.message.edit_text(cq["intro"], reply_markup=keyboard, parse_mode='Markdown')
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise

async def show_clarification_question(callback: types.CallbackQuery, stage_key: str):
    cq = CLARIFICATION_QUESTIONS[stage_key]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=f"clarify_answer_{stage_key}_{val}")]
        for val, text in cq["options"]
    ])
    try:
        await callback.message.edit_text(f"*{cq['text']}*", reply_markup=keyboard, parse_mode='Markdown')
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise

async def handle_clarification_answer(callback: types.CallbackQuery, stage_key: str, answer_val: int):
    user_id = callback.from_user.id
    user = user_data[user_id]
    
    pending_avg = user.get(f"{stage_key}_pending_avg", 2.0)
    corrected_avg = apply_clarification(pending_avg, answer_val)
    synthetic = calc_synthetic_score(user["scores"][stage_key], corrected_avg)
    
    user["scores"][stage_key].append(synthetic)
    user[f"{stage_key}_clarified"] = True
    
    cq = CLARIFICATION_QUESTIONS[stage_key]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Продолжить →", callback_data=f"after_clarification_{stage_key}")
    ]])
    try:
        await callback.message.edit_text(cq["result"], reply_markup=keyboard, parse_mode='Markdown')
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise

async def show_consistency_warning(callback: types.CallbackQuery, stage_key: str):
    vec = VECTORS[stage_key]
    stage_num = STAGE_ORDER.index(stage_key) + 1

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Пройти этап заново", callback_data=f"retry_stage_{stage_key}")],
        [InlineKeyboardButton(text="Продолжить как есть →", callback_data=f"force_stage_result_{stage_key}")]
    ])

    try:
        await callback.message.edit_text(
            f"{vec['emoji']} *Этап {stage_num} — нужно уточнение*\n\n"
            f"Ваши ответы в этом блоке сильно расходятся между собой.\n\n"
            f"Это нормально — иногда вопросы воспринимаются по-разному.\n\n"
            f"_Рекомендую пройти этап заново, отвечая на первый импульс._",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise

async def show_level_detail(callback: types.CallbackQuery, vector_key: str):
    user_id = callback.from_user.id
    scores = {k: round(mean(v), 1) for k, v in user_data[user_id]["scores"].items()}
    
    lvl = level(scores[vector_key])
    profile = LEVEL_PROFILES.get(vector_key, {}).get(lvl, {})
    vec = VECTORS[vector_key]
    
    if not profile:
        await callback.message.edit_text(
            "Профиль не найден.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_results")]
            ])
        )
        return
    
    triggers_text = "\n".join([f"• {t}" for t in profile.get("triggers", ["Узнаешь себя?"])])
    costs_text = "\n".join([f"• {c}" for c in profile.get("pain_costs", ["Это стоит тебе энергии"])])
    
    text = f"{vec['emoji']} **{vec['name']}** — уровень {lvl}/6\n\n"
    text += f"🎭 **{profile.get('archetype', '')}**\n"
    text += f"{profile.get('archetype_desc', '')}\n\n"
    text += f"💬 {profile.get('quote', '')}\n\n"
    text += f"**🔍 ЭТО ТЫ, ЕСЛИ...**\n"
    text += f"{triggers_text}\n\n"
    text += f"**⚠️ ОТКУДА ЭТО ВЗЯЛОСЬ**\n"
    text += f"{profile.get('pain_origin', '')}\n\n"
    text += f"**ЧЕМ ТЫ ПЛАТИШЬ**\n"
    text += f"{costs_text}\n\n"
    text += f"**🛠 ЧТО ДЕЛАТЬ ПРЯМО СЕЙЧАС**\n"
    
    tool_text = profile.get('immediate_tool', '')
    steps = tool_text.split('\n\n')
    for step in steps:
        if step.startswith('Шаг'):
            step_parts = step.split('.', 1)
            if len(step_parts) > 1:
                text += f"\n**{step_parts[0]}.**{step_parts[1]}\n"
            else:
                text += f"\n{step}\n"
        else:
            text += f"\n{step}\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад к профилю", callback_data="show_results")]
    ])
    
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for i, part in enumerate(parts):
            if i == 0:
                await callback.message.edit_text(part, parse_mode='Markdown')
            else:
                await callback.message.answer(part, parse_mode='Markdown')
        await callback.message.answer("Выберите действие:", reply_markup=keyboard)
    else:
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise

async def show_about_method(callback: types.CallbackQuery):
    text = (
        f"🔬 *ЧТО ЗА МЕТОД?*\n\n"
        f"В основе — пирамида Дилтса:\n\n"
        f"   🌍 Окружение → ГДЕ\n"
        f"   ⬇\n"
        f"   ⚡ Поведение → ЧТО\n"
        f"   ⬇\n"
        f"   🧠 Способности → КАК\n"
        f"   ⬇\n"
        f"   💭 Убеждения → ПОЧЕМУ\n"
        f"   ⬇\n"
        f"   🆔 Идентичность → КТО\n\n"
        f"──────────────────────\n\n"
        f"*Обычные тесты:*\n"
        f"«Вы тревожный. Идите, лечитесь».\n\n"
        f"*Мы:*\n"
        f"«Вы тревожный, потому что в 5 лет\n"
        f"вас ругали за громкий смех, теперь\n"
        f"вы замираете в конфликтах. Вот вам\n"
        f"три шага, че с этим делать»."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔪 Я готов, вскрывайте", callback_data="start_test")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="back_to_menu")]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise

async def show_results_examples(callback: types.CallbackQuery):
    text = (
        f"😱 *РЕЗУЛЬТ В ЛИЦАХ*\n\n"
        f"**СЛУЧАЙ 1. МЕНЕДЖЕР ОЛЕГ**\n\n"
        f"*Было:* «Начальник орёт — я немею».\n"
        f"*Стало:* «Начальник орёт — я предлагаю\n"
        f"        собрать метрики». Начальник офигел.\n\n"
        f"**СЛУЧАЙ 2. ДИЗАЙНЕР МАША**\n\n"
        f"*Было:* «Деньги приходят — деньги уходят».\n"
        f"*Стало:* «10% на счёт «Не трогать, убью».\n\n"
        f"**СЛУЧАЙ 3. ПРЕПОДАВАТЕЛЬ ДИМА**\n\n"
        f"*Было:* «Все козлы и специально меня бесят».\n"
        f"*Стало:* «А, это не заговор, это у людей\n"
        f"        просто свои тараканы»."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔪 ХОЧУ ТАК ЖЕ", callback_data="start_test")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="back_to_menu")]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise

def create_intimate_profile_prompt(scores):
    cv_level = level(scores["ЧВ"])
    sb_level = level(scores["СБ"])
    tf_level = level(scores["ТФ"])
    ub_level = level(scores["УБ"])
    
    cv_profile = LEVEL_PROFILES["ЧВ"].get(cv_level, {})
    sb_profile = LEVEL_PROFILES["СБ"].get(sb_level, {})
    
    prompt = f"""ТЫ — ПСИХОЛОГ-СЕКСОЛОГ. Напиши интимный профиль человека.

ДАННЫЕ:
ЧВ (Отношения): уровень {cv_level}/6, архетип {cv_profile.get('archetype', '')}
СБ (Реакция на угрозу): уровень {sb_level}/6, архетип {sb_profile.get('archetype', '')}
ТФ (Ресурсы): уровень {tf_level}/6
УБ (Понимание мира): уровень {ub_level}/6

НАПИШИ ПРОФИЛЬ ИЗ 5 БЛОКОВ:

1. ЗАГОЛОВОК: «{cv_level}ЧВ-{sb_level}СБ — {cv_profile.get('archetype', '')}»
2. КТО ТЫ В ПОСТЕЛИ (1 абзац)
3. ЧТО ТЕБЯ ЗАВОДИТ (4 пункта)
4. ЧТО ВЫКЛЮЧАЕТ (3 пункта)
5. ТВОЁ ГЛАВНОЕ (1 абзац)

СТИЛЬ: Телесный, конкретный, метафоричный. Пиши от второго лица («ты»)."""
    
    return prompt

async def show_intimate_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = user_data[user_id]
    
    if not all(len(v) >= 8 for v in user["scores"].values()):
        await callback.message.edit_text(
            "⚠️ Сначала завершите все этапы теста",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_results")]
            ])
        )
        return
    
    if user.get("intimate_profile"):
        await show_saved_intimate_profile(callback, user["intimate_profile"])
        return
    
    await callback.message.edit_text("🔥 *Составляю интимный профиль...*\n\n_Это займёт около 20 секунд_", parse_mode='Markdown')
    
    scores = {k: round(mean(v), 1) for k, v in user["scores"].items()}
    prompt = create_intimate_profile_prompt(scores)
    system_message = "Ты — психолог-сексолог. Пишешь глубокие, пронзительные психологические портреты."
    response = await call_deepseek(prompt, system_message, max_tokens=1500)
    
    if response:
        user["intimate_profile"] = response
        await show_saved_intimate_profile(callback, response)
    else:
        await callback.message.edit_text(
            "⚠️ Не удалось сгенерировать профиль. Попробуйте позже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_results")]
            ])
        )

async def show_saved_intimate_profile(callback: types.CallbackQuery, profile_text: str):
    def escape_markdown(text):
        text = text.replace('**', '‼BOLD‼')
        dangerous = '_[]()~`>#+=|{}!'
        for char in dangerous:
            text = text.replace(char, f'\\{char}')
        text = text.replace('*', '\\*')
        text = text.replace('‼BOLD‼', '**')
        return text
    
    formatted_text = profile_text
    formatted_text = formatted_text.replace("1. ЗАГОЛОВОК:", "**✨ Суть:**")
    formatted_text = formatted_text.replace("2. КТО ТЫ В ПОСТЕЛИ", "**🔥 Кто ты в постели**")
    formatted_text = formatted_text.replace("3. ЧТО ТЕБЯ ЗАВОДИТ", "**⚡ Что тебя заводит**")
    formatted_text = formatted_text.replace("4. ЧТО ВЫКЛЮЧАЕТ", "**❄️ Что выключает**")
    formatted_text = formatted_text.replace("5. ТВОЁ ГЛАВНОЕ", "**💫 Твоё главное**")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 МЫСЛИ ПСИХОЛОГА", callback_data="ai_analysis")],
        [InlineKeyboardButton(text="💡 ЧТО ДЕЛАТЬ", callback_data="ai_recommendations")],
        [InlineKeyboardButton(text="◀️ Назад к профилю", callback_data="show_results")]
    ])
    
    safe_text = escape_markdown(formatted_text)
    full_text = f"🔞 *ИНТИМНЫЙ ПРОФИЛЬ*\n\n{safe_text}"
    
    if len(full_text) > 4000:
        parts = [full_text[i:i+4000] for i in range(0, len(full_text), 4000)]
        await callback.message.edit_text(parts[0], parse_mode='Markdown', reply_markup=None)
        for part in parts[1:-1]:
            await callback.message.answer(part, parse_mode='Markdown')
        await callback.message.answer(parts[-1], parse_mode='Markdown', reply_markup=keyboard)
    else:
        await callback.message.edit_text(full_text, parse_mode='Markdown', reply_markup=keyboard)

def is_test_completed(user: dict) -> bool:
    return all(len(user.get("scores", {}).get(stage, [])) >= 8 for stage in STAGE_ORDER)

async def handle_voice_message(message: types.Message):
    user_id = message.from_user.id
    user = user_data.get(user_id)
    
    if not user:
        await message.answer("Начните с /start", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")]
        ]))
        return
    
    if not is_test_completed(user):
        await message.answer(
            "🎙 *Голосовые сообщения доступны только после завершения теста*\n\n"
            "Сначала пройдите все 4 этапа.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔪 Пройти тест", callback_data="start_test")],
                [InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")]
            ])
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
        
        await status_msg.edit_text(
            f"📝 *Вы сказали:*\n"
            f"_{recognized_text}_\n\n"
            f"🤔 *Думаю над ответом...*",
            parse_mode='Markdown'
        )
        
        scores = {k: round(mean(v), 1) for k, v in user["scores"].items()}
        context = user_contexts.get(user_id)
        user_name = user_names.get(user_id, message.from_user.first_name or "друг")
        
        profile_lines = []
        for k, v in scores.items():
            lvl = level(v)
            p = LEVEL_PROFILES.get(k, {}).get(lvl, {})
            profile_lines.append(f"{VECTORS[k]['name']}: {lvl}/6 — {p.get('archetype', '')}")
        profile_summary = "\n".join(profile_lines)
        
        context_text = ""
        if context:
            context_text = context.get_full_context(user_name)
            weather = await context.get_weather()
            if weather:
                context_text += f"\n{context.get_weather_recommendation(weather)}"
        
        history_text = ""
        if user.get("history"):
            recent = user["history"][-5:]
            for entry in recent:
                role = "Клиент" if entry["role"] == "user" else "Психолог"
                history_text += f"{role}: {entry['text']}\n"
        
        system_prompt = f"""Ты - друг, брат, наставник.

ТЕКУЩИЙ КОНТЕКСТ:
{context_text if context_text else ""}

ПСИХОЛОГИЧЕСКИЙ ПРОФИЛЬ:
{profile_summary}

ИСТОРИЯ ОБЩЕНИЯ:
{history_text if history_text else "Это наш первый разговор"}

Отвечай коротко, 2-4 предложения, по делу. Используй местоимение "ты". 
Обращайся к человеку по имени ({user_name}), если это уместно.
Будь заботливым, внимательным, с юмором."""
        
        response = await call_deepseek(recognized_text, system_prompt, max_tokens=300)
        
        if not response:
            bottleneck_key = get_priority_order(scores)[0]
            bottleneck_lvl = level(scores[bottleneck_key])
            response = FALLBACK_ANALYSIS[bottleneck_key][bottleneck_lvl]
        
        if "history" not in user:
            user["history"] = []
        
        user["history"].append({
            "role": "user", 
            "text": recognized_text, 
            "timestamp": datetime.now().isoformat()
        })
        user["history"].append({
            "role": "assistant", 
            "text": response, 
            "timestamp": datetime.now().isoformat()
        })
        
        if len(user["history"]) > 10:
            user["history"] = user["history"][-10:]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="smart_questions")],
            [InlineKeyboardButton(text="🧠 К профилю", callback_data="show_results")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")]
        ])
        
        await status_msg.edit_text(
            f"📝 *Вы сказали:*\n_{recognized_text}_\n\n"
            f"*Ответ:*\n{response}",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        ironic = should_be_ironic(response)
        audio_data = await text_to_speech(response, ironic)
        
        if audio_data:
            audio_file = BufferedInputFile(audio_data, filename="response.ogg")
            await message.answer_voice(
                audio_file,
                caption="🎙 *Голосовой ответ*",
                parse_mode='Markdown'
            )
    
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {e}", exc_info=True)
        await status_msg.edit_text(
            "❌ *Произошла ошибка*\n\n"
            "Попробуйте еще раз или напишите текстом.",
            parse_mode='Markdown'
        )

FALLBACK_ANALYSIS = {
    "СБ": {
        1: "Ты в стопоре под давлением. Это защитный механизм. Начни с малого: скажи 'нет' в безопасной ситуации.",
        2: "Ты избегаешь конфликтов. Попробуй в следующем конфликте остаться на 2 минуты дольше.",
        3: "Ты соглашаешься внешне, но внутри кипишь. Вместо 'да' говори 'мне нужно подумать'.",
        4: "Ты носишь маску. Выбери одного доверенного человека и скажи ему правду о своих чувствах.",
        5: "Ты гасишь конфликты. Попробуй раз в неделю не вмешиваться в чужой спор.",
        6: "Ты умеешь защищаться. Перед атакой спроси себя: 'Что я хочу получить в итоге?'"
    },
    "ТФ": {
        1: "Твои деньги зависят от других. Найди один навык и предложи его за деньги.",
        2: "Ты находишь, но не создаёшь. Посмотри на повторяющиеся подработки — сделай это системой.",
        3: "Ты зарабатываешь, но не копишь. Открой счет и переводи туда 10% от дохода.",
        4: "Ты много работаешь. Напиши инструкцию для одной задачи и отдай её кому-то.",
        5: "У тебя есть накопления. Раздели их на 3 части и начни инвестировать.",
        6: "Ты строишь системы. Раз в месяц общайся с теми, кто на нижнем уровне."
    },
    "УБ": {
        1: "Ты игнорируешь непонятное. Выбери одну тему и удели ей 10 минут.",
        2: "Ты объясняешь всё знаками. Вспомни последнее событие и объясни без мистики.",
        3: "Ты доверяешь экспертам. Возьми одно утверждение и проверь его сам.",
        4: "Ты ищешь заговоры. Спроси себя: 'Что я могу сделать, независимо от виноватых?'",
        5: "Ты проверяешь факты. Найди три повторяющихся наблюдения и сформулируй принцип.",
        6: "Ты строишь теории. Сделай предсказание и проверь его через 2 недели."
    },
    "ЧВ": {
        1: "Ты зависишь от близких. Сделай сегодня одно действие самостоятельно.",
        2: "Ты подстраиваешься под всех. Скажи мнение, которое расходится с собеседником.",
        3: "Вас знают многие. Выбери одного человека и проведи с ним час без 'программы'.",
        4: "Ты понимаешь людей. Попробуй один раз попросить прямо, без манипуляций.",
        5: "У тебя есть партнёрства. Познакомься с одним новым человеком из другой сферы.",
        6: "У тебя широкая сеть. Выбери 3 ключевых людей и инвестируй в них время."
    }
}

async def show_ai_analysis(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = user_data[user_id]
    
    test_completed = all(len(user["scores"][stage]) >= 8 for stage in STAGE_ORDER)
    
    if not test_completed:
        await callback.message.edit_text(
            "⚠️ Сначала завершите все этапы теста!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ К тесту", callback_data="start_test")]
            ])
        )
        return
    
    if user.get("ai_analysis"):
        await show_saved_ai_analysis(callback, user["ai_analysis"])
        return
    
    await callback.message.edit_text(
        "🧠 *Анализирую ваш профиль...*\n\n"
        "_Это займёт около 20 секунд_",
        parse_mode='Markdown'
    )
    
    scores = {k: round(mean(v), 1) for k, v in user["scores"].items()}
    bottleneck_key = get_priority_order(scores)[0]
    bottleneck_lvl = level(scores[bottleneck_key])
    bottleneck_profile = LEVEL_PROFILES.get(bottleneck_key, {}).get(bottleneck_lvl, {})
    bottleneck_vec = VECTORS[bottleneck_key]
    
    prompt = f"""ТЫ — ПСИХОЛОГ. Напиши психологический портрет человека.

УЗКОЕ МЕСТО:
- Вектор: {bottleneck_vec['name']}
- Уровень: {bottleneck_lvl}/6
- Архетип: {bottleneck_profile.get('archetype', '')}
- Описание: {bottleneck_profile.get('archetype_desc', '')}

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
        user["ai_analysis"] = response
        await show_saved_ai_analysis(callback, response)
    else:
        fallback_text = FALLBACK_ANALYSIS[bottleneck_key][bottleneck_lvl]
        await callback.message.edit_text(
            f"🧠 *МЫСЛИ ПСИХОЛОГА*\n\n{fallback_text}",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

async def show_saved_ai_analysis(callback: types.CallbackQuery, analysis_text: str):
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
    
    if len(full_text) > 4000:
        parts = [full_text[i:i+4000] for i in range(0, len(full_text), 4000)]
        await callback.message.edit_text(parts[0], parse_mode='Markdown', reply_markup=None)
        for part in parts[1:-1]:
            await callback.message.answer(part, parse_mode='Markdown')
        await callback.message.answer(parts[-1], parse_mode='Markdown', reply_markup=keyboard)
    else:
        await callback.message.edit_text(full_text, parse_mode='Markdown', reply_markup=keyboard)

async def show_ai_recommendations(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = user_data[user_id]
    
    test_completed = all(len(user["scores"][stage]) >= 8 for stage in STAGE_ORDER)
    
    if not test_completed:
        await callback.message.edit_text(
            "⚠️ Сначала завершите все этапы теста!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ К тесту", callback_data="start_test")]
            ])
        )
        return
    
    if user.get("ai_recommendations"):
        await show_saved_recommendations(callback, user["ai_recommendations"])
        return
    
    await callback.message.edit_text(
        "💡 *Подбираю рекомендации...*\n\n"
        "_Это займёт около 15-20 секунд_",
        parse_mode='Markdown'
    )
    
    scores = {k: round(mean(v), 1) for k, v in user["scores"].items()}
    bottleneck_key = get_priority_order(scores)[0]
    bottleneck_lvl = level(scores[bottleneck_key])
    bottleneck_vec = VECTORS[bottleneck_key]
    
    vectors_context = []
    for key in STAGE_ORDER:
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
        user["ai_recommendations"] = response
        await show_saved_recommendations(callback, response)
    else:
        fallback_text = get_fallback_recommendations(bottleneck_key, bottleneck_lvl, bottleneck_vec['name'])
        await callback.message.edit_text(
            f"💡 *ПЛАН ДЕЙСТВИЙ*\n\n{fallback_text}",
            parse_mode='Markdown',
            reply_markup=keyboard
        )

async def show_saved_recommendations(callback: types.CallbackQuery, recommendations_text: str):
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

def get_fallback_recommendations(key: str, lvl: int, vector_name: str) -> str:
    recommendations = {
        "СБ": {
            1: "⚡ *СЕГОДНЯ*\n• Заметь момент заморозки\n• Скажи «нет» в мелочи\n• Сделай паузу\n\n📌 *НА НЕДЕЛЮ*\n• Практикуй «стоп-слова»\n• Оставайся в конфликте на 2 минуты\n\n🔥 *В МЕСЯЦ*\n• Создай ресурсный буфер",
            2: "⚡ *СЕГОДНЯ*\n• Останься в разговоре на 2 минуты\n• Не уходи сразу\n• Заметь, что мир не рухнул",
            3: "⚡ *СЕГОДНЯ*\n• Вместо «да» скажи «подумаю»\n• Запиши одну ситуацию\n• Сделай паузу",
            4: "⚡ *СЕГОДНЯ*\n• Сними маску с одним человеком\n• Скажи правду о чувствах\n• Заметь реакцию",
            5: "⚡ *СЕГОДНЯ*\n• Не вмешайся в чужой спор\n• Добавь свою позицию\n• Заметь, где гасишь себя",
            6: "⚡ *СЕГОДНЯ*\n• Перед атакой спроси цель\n• Выбери дипломатию\n• Сделай паузу"
        },
        "ТФ": {
            1: "⚡ *СЕГОДНЯ*\n• Найди один навык\n• Сделай действие к доходу\n• Отдели свои действия от чужих",
            2: "⚡ *СЕГОДНЯ*\n• Открой счёт «Подушка»\n• Переведи 10%\n• Запиши доходы",
            3: "⚡ *СЕГОДНЯ*\n• Открой накопительный счёт\n• Переведи 10%\n• Запиши источники",
            4: "⚡ *СЕГОДНЯ*\n• Напиши инструкцию\n• Посчитай стоимость часа\n• Выбери задачу",
            5: "⚡ *СЕГОДНЯ*\n• Раздели накопления\n• Выбери инструмент\n• Изучи вариант",
            6: "⚡ *СЕГОДНЯ*\n• Проверь обратную связь\n• Поговори с людьми\n• Найди слабое место"
        },
        "УБ": {
            1: "⚡ *СЕГОДНЯ*\n• Выбери одну тему\n• Удели ей 10 минут\n• Спроси «почему?»",
            2: "⚡ *СЕГОДНЯ*\n• Вспомни «знаковое» событие\n• Объясни без мистики\n• Найди причины",
            3: "⚡ *СЕГОДНЯ*\n• Возьми утверждение\n• Проверь сам\n• Найди контраргумент",
            4: "⚡ *СЕГОДНЯ*\n• Найди объяснение без заговора\n• Спроси «что я могу сделать?»\n• Переключись",
            5: "⚡ *СЕГОДНЯ*\n• Найди 3 наблюдения\n• Сформулируй принцип\n• Проверь",
            6: "⚡ *СЕГОДНЯ*\n• Проверь модель действием\n• Сделай предсказание\n• Запиши результат"
        },
        "ЧВ": {
            1: "⚡ *СЕГОДНЯ*\n• Проведи час один\n• Сделай решение без оглядки\n• Скажи «я занят»",
            2: "⚡ *СЕГОДНЯ*\n• Выскажи другое мнение\n• Заметь реакцию\n• Спроси «чего хочу я?»",
            3: "⚡ *СЕГОДНЯ*\n• Сними маску с близким\n• Скажи правду о чувствах\n• Заметь",
            4: "⚡ *СЕГОДНЯ*\n• Попроси прямо\n• Скажи чего хочешь\n• Уважай право отказа",
            5: "⚡ *СЕГОДНЯ*\n• Новый контакт\n• Найди общие интересы\n• Предложи пользу",
            6: "⚡ *СЕГОДНЯ*\n• Выбери 3 ключевых людей\n• Инвестируй время\n• Скажи личное"
        }
    }
    
    text = f"⚡ *ПЛАН ПО {vector_name.upper()}*\n\n"
    text += recommendations.get(key, {}).get(lvl, "• Работай над собой каждый день")
    return text

async def show_smart_questions(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = user_data[user_id]
    
    test_completed = all(len(user["scores"][stage]) >= 8 for stage in STAGE_ORDER)
    
    if not test_completed:
        await callback.message.edit_text(
            "⚠️ Сначала завершите все этапы теста!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ К тесту", callback_data="start_test")]
            ])
        )
        return
    
    scores = {k: round(mean(v), 1) for k, v in user["scores"].items()}
    questions = generate_smart_questions(scores)
    user["smart_questions"] = questions
    
    voice_info = ""
    if is_test_completed(user):
        voice_info = "🎙 *Голосовой режим активен*\n"
    
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
        text="◀️ Назад к профилю", 
        callback_data="show_results"
    )])
    
    await callback.message.edit_text(
        f"❓ *ЧТО ТЕБЯ БЕСПОКОИТ?*\n\n"
        f"{voice_info}"
        f"Выбери вопрос или задай свой. Я помню твой профиль.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='Markdown'
    )

async def show_more_info(callback: types.CallbackQuery):
    text = (
        f"🧠 *ВИРТУАЛЬНЫЙ ПСИХОЛОГ 3.0*\n\n"
        f"⚡ *В ЭТОЙ ВЕРСИИ:*\n"
        f"• 🔞 Интимный профиль\n"
        f"• 🧠 4 вектора × 6 уровней\n"
        f"• 💡 Персональные рекомендации\n"
        f"• ❓ Умные вопросы с учетом профиля\n"
        f"• 🎙 Голосовые сообщения\n"
        f"• 🌍 Контекст (город, погода, время)\n"
        f"• 🤝 Роль друга и наставника\n"
        f"• 🔄 Конфайнмент-моделирование\n\n"
        f"💬 *ОДНАЖДЫ ТЫ ПРОСТО ПЕРЕСТАНЕШЬ БЫТЬ ПРОБЛЕМОЙ ДЛЯ САМОГО СЕБЯ.*"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 СВЯЗАТЬСЯ С ПСИХОЛОГОМ", url="https://t.me/meysternlp")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="show_results")]
    ])
    
    try:
        await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=keyboard)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise

async def handle_smart_question(callback: types.CallbackQuery, question: str):
    user_id = callback.from_user.id
    user = user_data[user_id]
    scores = {k: round(mean(v), 1) for k, v in user["scores"].items()}
    
    await callback.message.edit_text(
        "🤔 *Думаю над ответом...*\n\n"
        "_Это займёт около 10-15 секунд_",
        parse_mode='Markdown'
    )
    
    context = user_contexts.get(user_id)
    user_name = user_names.get(user_id, callback.from_user.first_name or "друг")
    
    profile_lines = []
    for k, v in scores.items():
        lvl = level(v)
        p = LEVEL_PROFILES.get(k, {}).get(lvl, {})
        profile_lines.append(f"{VECTORS[k]['name']}: {lvl}/6 — {p.get('archetype', '')}")
    profile_summary = "\n".join(profile_lines)
    
    context_text = ""
    if context:
        context_text = context.get_full_context(user_name)
        weather = await context.get_weather()
        if weather:
            context_text += f"\n{context.get_weather_recommendation(weather)}"
    
    history_text = ""
    if user.get("history"):
        recent = user["history"][-5:]
        for entry in recent:
            role = "Клиент" if entry["role"] == "user" else "Психолог"
            history_text += f"{role}: {entry['text']}\n"
    
    system_prompt = f"""Ты - друг, брат, наставник.

КОНТЕКСТ:
{context_text if context_text else ""}

ПРОФИЛЬ:
{profile_summary}

ИСТОРИЯ:
{history_text if history_text else ""}

Ответь на вопрос коротко, 2-4 предложения, по делу. Будь заботливым, с юмором если уместно."""
    
    prompt = f"Вопрос: {question}"
    response = await call_deepseek(prompt, system_prompt, max_tokens=300)
    
    if not response:
        bottleneck_key = get_priority_order(scores)[0]
        bottleneck_lvl = level(scores[bottleneck_key])
        response = FALLBACK_ANALYSIS[bottleneck_key][bottleneck_lvl]
    
    if "history" not in user:
        user["history"] = []
    
    user["history"].append({
        "role": "user", 
        "text": question, 
        "timestamp": datetime.now().isoformat()
    })
    user["history"].append({
        "role": "assistant", 
        "text": response, 
        "timestamp": datetime.now().isoformat()
    })
    
    if len(user["history"]) > 10:
        user["history"] = user["history"][-10:]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="smart_questions")],
        [InlineKeyboardButton(text="🧠 К профилю", callback_data="show_results")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")]
    ])
    
    await callback.message.edit_text(
        f"❓ *{question}*\n\n{response}",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    
    if is_test_completed(user):
        ironic = should_be_ironic(response)
        audio_data = await text_to_speech(response, ironic)
        
        if audio_data:
            audio_file = BufferedInputFile(audio_data, filename="response.ogg")
            await callback.message.answer_voice(
                audio_file,
                caption="🎙 *Голосовой ответ*",
                parse_mode='Markdown'
            )

# ══════════════════════════════════════════════
#  НОВЫЕ ОБРАБОТЧИКИ ДЛЯ КОНФАЙНМЕНТ-МОДЕЛИ
# ══════════════════════════════════════════════

async def show_confinement(callback: types.CallbackQuery):
    """Показывает конфайнмент-модель пользователя"""
    user_id = callback.from_user.id
    user = user_data.get(user_id, {})
    
    if not user.get('confinement_model'):
        await callback.message.edit_text(
            "⚠️ *Модель еще не построена*\n\n"
            "Сначала пройди тест, чтобы я мог проанализировать твою психологическую систему.\n\n"
            "Тест занимает всего 2-3 минуты.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 ПРОЙТИ ТЕСТ", callback_data="start_test")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_results")]
            ]),
            parse_mode='Markdown'
        )
        return
    
    # Восстанавливаем модель
    try:
        model_data = user['confinement_model']
        model = ConfinementModel9.from_dict(model_data)
        name = user_names.get(user_id, "друг")
        
        # Создаем отчет
        reporter = ConfinementReporter(model, name)
        
        # Показываем меню
        text = "🧠 *КОНФАЙНМЕНТ-МОДЕЛЬ*\n\n"
        text += "Что ты хочешь узнать о своей психологической системе?\n\n"
        
        # Добавляем краткую информацию
        if model.key_confinement:
            elem_id = model.key_confinement.get('id')
            if elem_id:
                text += f"⭐ *Ключевое ограничение:* элемент {elem_id}\n"
        
        if model.is_closed:
            text += f"🔒 *Система замкнута* (степень {model.closure_score:.0%})\n"
        else:
            text += f"🔓 *Система разомкнута* (степень {model.closure_score:.0%})\n"
        
        text += f"🔄 *Найдено петель:* {len(reporter.loops)}\n"
        
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        text = "⚠️ *Ошибка загрузки модели*\n\nПопробуй пройти тест заново."
    
    # Клавиатура
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Краткий обзор", callback_data="confinement_summary"),
         InlineKeyboardButton(text="📈 Детальный отчет", callback_data="confinement_detailed")],
        [InlineKeyboardButton(text="💡 Совет дня", callback_data="confinement_advice"),
         InlineKeyboardButton(text="🎯 Интервенция", callback_data="confinement_intervention")],
        [InlineKeyboardButton(text="🗺️ Схема", callback_data="confinement_map"),
         InlineKeyboardButton(text="📅 Неделя", callback_data="confinement_week")],
        [InlineKeyboardButton(text="🔊 Голосовое", callback_data="confinement_voice")],
        [InlineKeyboardButton(text="◀️ К профилю", callback_data="show_results")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')


async def confinement_summary(callback: types.CallbackQuery):
    """Показывает краткую сводку модели"""
    user_id = callback.from_user.id
    user = user_data.get(user_id, {})
    
    model_data = user.get('confinement_model')
    if not model_data:
        await callback.answer("Модель не найдена")
        return
    
    try:
        model = ConfinementModel9.from_dict(model_data)
        name = user_names.get(user_id, "друг")
        reporter = ConfinementReporter(model, name)
        
        text = reporter.get_summary()
        
        await callback.message.edit_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📈 Подробнее", callback_data="confinement_detailed"),
                 InlineKeyboardButton(text="💡 Совет", callback_data="confinement_advice")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_confinement")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in summary: {e}")
        await callback.message.edit_text(
            "⚠️ Ошибка формирования отчета",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_confinement")]
            ])
        )


async def confinement_detailed(callback: types.CallbackQuery):
    """Показывает детальный отчет"""
    user_id = callback.from_user.id
    user = user_data.get(user_id, {})
    
    model_data = user.get('confinement_model')
    if not model_data:
        await callback.answer("Модель не найдена")
        return
    
    try:
        model = ConfinementModel9.from_dict(model_data)
        name = user_names.get(user_id, "друг")
        reporter = ConfinementReporter(model, name)
        
        text = reporter.get_detailed_report()
        
        # Разбиваем на части если слишком длинно
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            
            # Отправляем первую часть
            await callback.message.edit_text(parts[0], parse_mode='Markdown')
            
            # Отправляем остальные части
            for part in parts[1:-1]:
                await callback.message.answer(part, parse_mode='Markdown')
            
            # Последняя часть с кнопкой
            await callback.message.answer(
                parts[-1], 
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="show_confinement")]
                ])
            )
        else:
            await callback.message.edit_text(
                text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="show_confinement")]
                ])
            )
    except Exception as e:
        logger.error(f"Error in detailed report: {e}")
        await callback.message.edit_text(
            "⚠️ Ошибка формирования детального отчета",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_confinement")]
            ])
        )


async def confinement_advice(callback: types.CallbackQuery):
    """Показывает совет на основе модели"""
    user_id = callback.from_user.id
    user = user_data.get(user_id, {})
    
    model_data = user.get('confinement_model')
    if not model_data:
        await callback.answer("Модель не найдена")
        return
    
    try:
        model = ConfinementModel9.from_dict(model_data)
        name = user_names.get(user_id, "друг")
        reporter = ConfinementReporter(model, name)
        
        advice = reporter.get_simple_advice()
        
        await callback.message.edit_text(
            advice,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Выполнил", callback_data="confinement_done"),
                 InlineKeyboardButton(text="🎯 Интервенция", callback_data="confinement_intervention")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_confinement")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in advice: {e}")
        await callback.message.edit_text(
            "⚠️ Ошибка формирования совета",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_confinement")]
            ])
        )


async def confinement_intervention(callback: types.CallbackQuery):
    """Показывает интервенцию для работы с конфайнментом"""
    user_id = callback.from_user.id
    user = user_data.get(user_id, {})
    
    model_data = user.get('confinement_model')
    if not model_data:
        await callback.answer("Модель не найдена")
        return
    
    try:
        model = ConfinementModel9.from_dict(model_data)
        name = user_names.get(user_id, "друг")
        reporter = ConfinementReporter(model, name)
        
        intervention = reporter.get_intervention()
        
        if not intervention:
            await callback.answer("Интервенция не найдена")
            return
        
        # Получаем персонализированную интервенцию из библиотеки
        if reporter.loops:
            loop_type = reporter.loops[0].get('type', 'universal')
            profile = {
                'vector': intervention.get('vector'),
                'level': intervention.get('level')
            }
            personalized = intervention_lib.get_personalized(loop_type, profile)
            if personalized and personalized.get('quote'):
                quote = f"\n\n💬 *Цитата дня:* {personalized['quote']}"
            else:
                quote = ""
        else:
            quote = ""
        
        text = f"🎯 *ИНТЕРВЕНЦИЯ*\n\n"
        text += f"**{intervention.get('approach', 'Работа с ограничением')}**\n\n"
        text += f"📌 *Метод:* {intervention.get('method', 'Не указан')}\n"
        text += f"⏱ *Длительность:* {intervention.get('duration', '7-14 дней')}\n"
        text += f"📊 *Сложность:* {intervention.get('difficulty', 'Средняя')}\n\n"
        text += f"⚡ *Упражнение:*\n_{intervention.get('exercise', 'Нет упражнения')}_\n"
        text += f"\n🎯 *Цель:* {intervention.get('target', 'Изменение системы')}"
        text += quote
        
        await callback.message.edit_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Я сделал это", callback_data="confinement_done")],
                [InlineKeyboardButton(text="📅 На неделю", callback_data="confinement_week")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="confinement_advice")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in intervention: {e}")
        await callback.message.edit_text(
            "⚠️ Ошибка формирования интервенции",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_confinement")]
            ])
        )


async def confinement_map(callback: types.CallbackQuery):
    """Показывает ASCII-схему модели"""
    user_id = callback.from_user.id
    user = user_data.get(user_id, {})
    
    model_data = user.get('confinement_model')
    if not model_data:
        await callback.answer("Модель не найдена")
        return
    
    try:
        model = ConfinementModel9.from_dict(model_data)
        name = user_names.get(user_id, "друг")
        reporter = ConfinementReporter(model, name)
        
        map_text = reporter.get_confinement_map()
        
        await callback.message.edit_text(
            map_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 Кратко", callback_data="confinement_summary"),
                 InlineKeyboardButton(text="📈 Подробно", callback_data="confinement_detailed")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_confinement")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in map: {e}")
        await callback.message.edit_text(
            "⚠️ Ошибка формирования схемы",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_confinement")]
            ])
        )


async def confinement_voice(callback: types.CallbackQuery):
    """Показывает текст для голосового сообщения"""
    user_id = callback.from_user.id
    user = user_data.get(user_id, {})
    
    model_data = user.get('confinement_model')
    if not model_data:
        await callback.answer("Модель не найдена")
        return
    
    try:
        model = ConfinementModel9.from_dict(model_data)
        name = user_names.get(user_id, "друг")
        reporter = ConfinementReporter(model, name)
        
        voice_text = reporter.get_voice_message_text()
        
        await callback.message.edit_text(
            f"🔊 *Голосовое сообщение*\n\n{voice_text}\n\n_Скопируй этот текст в голосовой ввод, если хочешь прослушать_",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_confinement")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in voice: {e}")
        await callback.message.edit_text(
            "⚠️ Ошибка формирования текста",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_confinement")]
            ])
        )


async def confinement_week(callback: types.CallbackQuery):
    """Показывает программу на неделю"""
    user_id = callback.from_user.id
    user = user_data.get(user_id, {})
    
    model_data = user.get('confinement_model')
    if not model_data:
        await callback.answer("Модель не найдена")
        return
    
    try:
        model = ConfinementModel9.from_dict(model_data)
        
        # Определяем ключевой элемент
        key_id = None
        if model.key_confinement:
            key_id = model.key_confinement.get('id')
        
        if not key_id:
            key_id = 5  # По умолчанию
        
        # Получаем программу на неделю
        week_program = intervention_lib.get_program_for_week(key_id)
        
        text = f"📅 *ПРОГРАММА НА НЕДЕЛЮ*\n\n"
        text += f"Работа с элементом {key_id}\n\n"
        
        for day in week_program:
            text += f"*{day['day']}:* {day['title']}\n"
            text += f"└ {day['task']} ({day['duration']})\n\n"
        
        # Добавляем бонусное упражнение
        daily = intervention_lib.get_daily_practice(key_id)
        text += f"🎯 *Бонус:* {daily['title']}\n"
        text += f"└ {daily['practice']}\n"
        
        await callback.message.edit_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Я выполнил день", callback_data="confinement_done")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_confinement")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in week program: {e}")
        await callback.message.edit_text(
            "⚠️ Ошибка формирования программы",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_confinement")]
            ])
        )


async def confinement_done(callback: types.CallbackQuery):
    """Отмечает выполнение интервенции"""
    user_id = callback.from_user.id
    user = user_data.get(user_id, {})
    
    # Добавляем запись о выполнении в статистику
    if 'completed_interventions' not in user:
        user['completed_interventions'] = []
    
    user['completed_interventions'].append({
        'date': datetime.now().isoformat(),
        'type': 'intervention'
    })
    
    # Получаем случайную цитату
    import random
    quote = random.choice(intervention_lib.quotes['action'])
    
    text = f"🎉 *Отлично!*\n\n"
    text += f"{quote}\n\n"
    text += f"Ты сделал важный шаг. Каждое маленькое действие приближает к большим изменениям.\n\n"
    text += f"*Выполнено интервенций:* {len(user['completed_interventions'])}"
    
    await callback.message.edit_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 К модели", callback_data="show_confinement")],
            [InlineKeyboardButton(text="🧠 К профилю", callback_data="show_results")]
        ])
    )


# ══════════════════════════════════════════════
#  ОБНОВЛЕННАЯ ФУНКЦИЯ show_results
# ══════════════════════════════════════════════

async def show_results(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = user_data.get(user_id, {})
    
    if not user or 'scores' not in user:
        await callback.message.edit_text(
            "⚠️ Сначала нужно ответить на вопросы.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 НАЧАТЬ ТЕСТ", callback_data="start_test")]
            ])
        )
        return
    
    # Проверяем завершенность теста
    for stage in STAGE_ORDER:
        if len(user["scores"].get(stage, [])) < 8:
            await callback.message.edit_text(
                "⚠️ Сначала завершите все этапы теста!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ К тесту", callback_data="start_test")]
                ])
            )
            return
    
    # Вычисляем средние баллы
    scores = {k: round(mean(v), 1) for k, v in user["scores"].items()}
    
    # Строим конфайнмент-модель
    try:
        logger.info(f"Building confinement model for user {user_id}")
        model = ConfinementModel9(user_id)
        history = user.get('history', [])
        model.build_from_profile(scores, history)
        
        # Сохраняем модель
        user['confinement_model'] = model.to_dict()
        
        # Сохраняем в историю моделей
        if 'confinement_history' not in user:
            user['confinement_history'] = []
        user['confinement_history'].append({
            'date': datetime.now().isoformat(),
            'model': model.to_dict()
        })
        
        logger.info(f"Model saved for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error building model for user {user_id}: {e}")
        # Продолжаем без модели
    
    # Регистрируем завершение (только один раз)
    if not user.get("logged", False):
        stats.register_completion(user_id, scores)
        user["logged"] = True
        user["profile_complete"] = True
        
        # Отменяем старые задачи и создаем новые
        task_manager.cancel_user_tasks(user_id)
        user_name = user_names.get(user_id, callback.from_user.first_name or "друг")
        
        # Планируем мотивационное сообщение через 5 минут
        asyncio.create_task(task_manager.schedule_motivation(user_id, scores, user_name, delay_minutes=5))
        
        # Планируем напоминание через 24 часа
        reminder_text = (
            f"🧠 *ПРОШЕЛ ДЕНЬ ПОСЛЕ ТЕСТА*\n\n"
            f"Привет, {user_name}! Как успехи? Удалось сделать хоть один шаг?\n\n"
            f"Если застрял — просто напиши мне."
        )
        asyncio.create_task(task_manager.schedule_reminder(user_id, reminder_text, delay_hours=24))
    
    # Формируем текст профиля
    text = f"🧠 *ТВОЙ ПРОФИЛЬ*\n\n"
    
    for key in STAGE_ORDER:
        vec = VECTORS[key]
        lvl = level(scores[key])
        info = vec["levels"][lvl]
        profile = LEVEL_PROFILES.get(key, {}).get(lvl, {})
        
        text += f"{vec['emoji']} **{vec['name']}** — *{info['name']}* ({key}-{lvl})\n"
        if profile.get('quote'):
            text += f"   {profile['quote']}\n"
        text += f"\n"
    
    bottleneck_key = get_priority_order(scores)[0]
    bottleneck_lvl = level(scores[bottleneck_key])
    bottleneck_vec = VECTORS[bottleneck_key]
    
    text += f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
    text += f"🎯 **УЗКОЕ МЕСТО:**\n"
    text += f"   {bottleneck_vec['name']} ({bottleneck_key}-{bottleneck_lvl})\n\n"
    
    # Добавляем краткую сводку модели, если она есть
    if user.get('confinement_model'):
        try:
            model_data = user['confinement_model']
            model = ConfinementModel9.from_dict(model_data)
            name = user_names.get(user_id, "друг")
            reporter = ConfinementReporter(model, name)
            text += reporter.get_summary()
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
    
    # Обновленная клавиатура с кнопкой конфайнмент-модели
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 МЫСЛИ ПСИХОЛОГА", callback_data="ai_analysis")],
        [InlineKeyboardButton(text="🔞 ИНТИМНЫЙ ПРОФИЛЬ", callback_data="intimate_profile")],
        [InlineKeyboardButton(text="🔄 КОНФАЙНМЕНТ", callback_data="show_confinement")],  # НОВАЯ
        [InlineKeyboardButton(text="❓ ВОПРОСЫ", callback_data="smart_questions")],
        [InlineKeyboardButton(text="💡 ЧТО ДЕЛАТЬ", callback_data="ai_recommendations")],
        [InlineKeyboardButton(text="🌍 РАССКАЗАТЬ О СЕБЕ", callback_data="ask_context")],
        [InlineKeyboardButton(text="✨ ЕЩЁ", callback_data="more_info")]
    ])
    
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        await callback.message.edit_text(parts[0], parse_mode='Markdown', reply_markup=None)
        for part in parts[1:-1]:
            await callback.message.answer(part, parse_mode='Markdown')
        await callback.message.answer(parts[-1], parse_mode='Markdown', reply_markup=keyboard)
    else:
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise


# ══════════════════════════════════════════════
#  ОБРАБОТЧИКИ TELEGRAM
# ══════════════════════════════════════════════

async def start_command(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Пользователь"
    
    user_names[user_id] = user_name
    
    # Обновленная структура данных с полями для конфайнмент-модели
    user_data[user_id] = {
        "stage": "menu",
        "scores": {k: [] for k in VECTORS},
        "current_stage": None,
        "current_question": 0,
        "profile_complete": False,
        "logged": False,
        "intimate_profile": None,
        "ai_analysis": None,
        "ai_recommendations": None,
        "history": [],
        "awaiting": None,
        "confinement_model": None,
        "confinement_history": []
    }
    
    stats.register_start(user_id)
    
    text = (
        f"🧠 *ВИРТУАЛЬНЫЙ ПСИХОЛОГ*\n\n"
        f"👋 *Привет, {user_name}!*\n\n"
        f"Я твой друг, брат, наставник. Буду с тобой честен, поддержу, когда надо, и пну, если потребуется.\n\n"
        f"🔹 **ШАГ 1 — Пройди тест** (12 минут)\n"
        f"🔹 **ШАГ 2 — Изучи профиль**\n"
        f"🔹 **ШАГ 3 — Задавай вопросы** (текст или голос)\n\n"
        f"🎙 Голос автоматически включится после теста.\n"
        f"🌍 Расскажешь свой город — буду знать погоду и время."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔪 ДЕЛАЕМ ВСКРЫТИЕ!", callback_data="start_test")],
        [InlineKeyboardButton(text="📖 ЧТО ЗА МЕТОД", callback_data="about_method")],
        [InlineKeyboardButton(text="🌍 РАССКАЗАТЬ О СЕБЕ", callback_data="ask_context")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode='Markdown')

async def stats_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещен")
        return
    
    await message.answer(stats.get_stats_text(), parse_mode='Markdown')

async def apistatus_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещен")
        return
    
    status_msg = await message.answer("🔄 Проверяю API...")
    
    deepseek_status = "✅ работает" if DEEPSEEK_API_KEY else "❌ не настроен"
    deepgram_status = "✅ работает" if DEEPGRAM_API_KEY else "❌ не настроен"
    yandex_status = "✅ работает" if YANDEX_API_KEY else "❌ не настроен"
    weather_status = "✅ работает" if OPENWEATHER_API_KEY else "❌ не настроен"
    
    text = f"📊 **Статус API:**\n\n"
    text += f"• DeepSeek: {deepseek_status}\n"
    text += f"• Deepgram: {deepgram_status}\n"
    text += f"• Yandex TTS: {yandex_status}\n"
    text += f"• OpenWeather: {weather_status}\n\n"
    
    if YANDEX_API_KEY:
        text += f"🎙 Голоса: Оксана (забота), Филипп (ирония)\n"
    
    await status_msg.edit_text(text, parse_mode='Markdown')

async def callback_handler(callback: types.CallbackQuery):
    await callback.answer()
    
    user_id = callback.from_user.id
    data = callback.data
    
    if user_id not in user_data:
        user_data[user_id] = {
            "stage": "menu",
            "scores": {k: [] for k in VECTORS},
            "current_stage": None,
            "current_question": 0,
            "profile_complete": False,
            "logged": False,
            "intimate_profile": None,
            "ai_analysis": None,
            "ai_recommendations": None,
            "history": [],
            "awaiting": None,
            "confinement_model": None,
            "confinement_history": []
        }
    
    try:
        if data == "start_test":
            user_data[user_id]["stage"] = "testing"
            user_data[user_id]["scores"] = {k: [] for k in VECTORS}
            user_data[user_id]["current_stage"] = STAGE_ORDER[0]
            user_data[user_id]["current_question"] = 0
            user_data[user_id]["profile_complete"] = False
            await show_stage_intro(callback, STAGE_ORDER[0])
        
        elif data == "about_method":
            await show_about_method(callback)
        
        elif data == "results_examples":
            await show_results_examples(callback)
        
        elif data == "ask_context":
            await ask_for_context(callback)
        
        elif data == "skip_context":
            await skip_context(callback)
        
        elif data == "back_to_menu":
            user = user_data.get(user_id, {})
            test_completed = is_test_completed(user)
            
            keyboard_buttons = [
                [InlineKeyboardButton(text="🔪 ДЕЛАЕМ ВСКРЫТИЕ!", callback_data="start_test")],
                [InlineKeyboardButton(text="📖 ЧТО ЗА МЕТОД", callback_data="about_method")],
                [InlineKeyboardButton(text="🌍 РАССКАЗАТЬ О СЕБЕ", callback_data="ask_context")],
            ]
            
            if test_completed:
                keyboard_buttons.insert(1, [InlineKeyboardButton(text="🧠 МОЙ ПРОФИЛЬ", callback_data="show_results")])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            menu_text = "🧠 *ВИРТУАЛЬНЫЙ ПСИХОЛОГ*\n\nЧем займемся?"
            if test_completed:
                menu_text += "\n\n✅ Тест пройден! Доступны голосовые сообщения."
            
            await callback.message.edit_text(
                menu_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        
        elif data.startswith("stage_details_"):
            stage_key = data.replace("stage_details_", "")
            await show_stage_details(callback, stage_key)
        
        elif data.startswith("stage_intro_"):
            stage_key = data.replace("stage_intro_", "")
            user_data[user_id]["current_stage"] = stage_key
            user_data[user_id]["current_question"] = 0
            await show_stage_intro(callback, stage_key)
        
        elif data.startswith("begin_stage_"):
            stage_key = data.replace("begin_stage_", "")
            user = user_data[user_id]
            user["current_stage"] = stage_key
            user["current_question"] = 0
            if stage_key not in user["scores"]:
                user["scores"][stage_key] = []
            await send_next_question(callback)
        
        elif data.startswith("clarify_show_"):
            stage_key = data.replace("clarify_show_", "")
            await show_clarification_question(callback, stage_key)

        elif data.startswith("clarify_answer_"):
            parts = data.split("_")
            stage_key = parts[2]
            answer_val = int(parts[3])
            await handle_clarification_answer(callback, stage_key, answer_val)

        elif data.startswith("after_clarification_"):
            stage_key = data.replace("after_clarification_", "")
            await show_stage_feedback(callback, stage_key)

        elif data.startswith("retry_stage_"):
            stage_key = data.replace("retry_stage_", "")
            user_data[user_id]["scores"][stage_key] = []
            user_data[user_id]["current_stage"] = stage_key
            user_data[user_id]["current_question"] = 0
            user_data[user_id].pop(f"{stage_key}_clarified", None)
            user_data[user_id].pop(f"{stage_key}_pending_avg", None)
            await send_next_question(callback)

        elif data.startswith("force_stage_result_"):
            stage_key = data.replace("force_stage_result_", "")
            user_data[user_id][f"{stage_key}_consistency_override"] = True
            await show_stage_feedback(callback, stage_key)
        
        elif data.startswith("answer_"):
            if user_data[user_id].get("processing", False):
                return
            user_data[user_id]["processing"] = True
            try:
                score = int(data.split("_")[1])
                user = user_data[user_id]
                
                current_stage = user.get("current_stage")
                if not current_stage:
                    await callback.message.edit_text(
                        "⚠️ Ошибка: тест не активен. Начните заново.",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🔪 Начать тест", callback_data="start_test")]
                        ])
                    )
                    return
                
                if current_stage not in user["scores"]:
                    user["scores"][current_stage] = []
                
                user["scores"][current_stage].append(score)
                await send_next_question(callback)
                
            except Exception as e:
                logger.error(f"Ошибка при обработке ответа: {e}")
                await callback.message.edit_text(
                    "❌ Произошла ошибка. Попробуйте начать заново.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")]
                    ])
                )
            finally:
                user_data[user_id]["processing"] = False
        
        elif data.startswith("detail_"):
            vector_key = data.replace("detail_", "")
            await show_level_detail(callback, vector_key)
        
        elif data == "show_results":
            await show_results(callback)
        
        elif data == "ai_analysis":
            await show_ai_analysis(callback)
        
        elif data == "ai_recommendations":
            await show_ai_recommendations(callback)
        
        elif data == "intimate_profile":
            await show_intimate_profile(callback)
        
        elif data == "smart_questions":
            await show_smart_questions(callback)
        
        elif data == "more_info":
            await show_more_info(callback)
        
        elif data == "ask_question":
            user_data[user_id]["stage"] = "awaiting_question"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="show_results")]
            ])
            await callback.message.edit_text(
                "✏️ *ЗАДАЙ ВОПРОС*\n\n"
                "Напиши, что тебя беспокоит. Я помню твой профиль.",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        elif data == "restart_test":
            old_history = user_data[user_id].get("history", [])
            
            user_data[user_id] = {
                "stage": "menu",
                "scores": {k: [] for k in VECTORS},
                "current_stage": None,
                "current_question": 0,
                "profile_complete": False,
                "logged": False,
                "intimate_profile": None,
                "ai_analysis": None,
                "ai_recommendations": None,
                "history": old_history[-10:] if old_history else [],
                "awaiting": None,
                "confinement_model": None,
                "confinement_history": []
            }
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔪 ДЕЛАЕМ ВСКРЫТИЕ!", callback_data="start_test")],
                [InlineKeyboardButton(text="📖 ЧТО ЗА МЕТОД", callback_data="about_method")],
                [InlineKeyboardButton(text="🌍 РАССКАЗАТЬ О СЕБЕ", callback_data="ask_context")]
            ])
            await callback.message.edit_text(
                "🧠 *ВИРТУАЛЬНЫЙ ПСИХОЛОГ*\n\nГотовы к вскрытию?",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        
        elif data.startswith("ask_"):
            idx = int(data.split("_")[1]) - 1
            questions = user_data[user_id].get("smart_questions", [])
            if 0 <= idx < len(questions):
                user_data[user_id]["stage"] = "answering_question"
                await handle_smart_question(callback, questions[idx])
        
        # Новые обработчики для конфайнмент-модели
        elif data == "show_confinement":
            await show_confinement(callback)
        
        elif data == "confinement_summary":
            await confinement_summary(callback)
        
        elif data == "confinement_detailed":
            await confinement_detailed(callback)
        
        elif data == "confinement_advice":
            await confinement_advice(callback)
        
        elif data == "confinement_intervention":
            await confinement_intervention(callback)
        
        elif data == "confinement_map":
            await confinement_map(callback)
        
        elif data == "confinement_voice":
            await confinement_voice(callback)
        
        elif data == "confinement_week":
            await confinement_week(callback)
        
        elif data == "confinement_done":
            await confinement_done(callback)
    
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            logger.info(f"Ignored 'message not modified' error")
        else:
            raise

async def handle_message(message: types.Message):
    user_id = message.from_user.id
    
    if user_id not in user_data:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")]
        ])
        await message.answer("Начните с /start", reply_markup=keyboard)
        return
    
    user = user_data[user_id]
    
    if user.get("awaiting") == "context":
        await handle_context_input(message)
        return
    
    if user.get("stage") == "awaiting_question":
        pass
    elif user.get("stage") == "testing":
        await message.answer("Пожалуйста, используйте кнопки для ответов на вопросы теста.")
        return
    else:
        await message.answer("Используйте кнопки для навигации")
        return
    
    if not all(len(v) > 0 for v in user["scores"].values()):
        await message.answer("Сначала пройдите тест через /start")
        return
    
    scores = {k: round(mean(v), 1) for k, v in user["scores"].items()}
    thinking = await message.answer(
        "🤔 *Думаю над ответом...*",
        parse_mode='Markdown'
    )
    
    context = user_contexts.get(user_id)
    user_name = user_names.get(user_id, message.from_user.first_name or "друг")
    
    profile_lines = []
    for k, v in scores.items():
        lvl = level(v)
        p = LEVEL_PROFILES.get(k, {}).get(lvl, {})
        profile_lines.append(f"{VECTORS[k]['name']}: {lvl}/6 — {p.get('archetype', '')}")
    profile_summary = "\n".join(profile_lines)
    
    context_text = ""
    if context:
        context_text = context.get_full_context(user_name)
        weather = await context.get_weather()
        if weather:
            context_text += f"\n{context.get_weather_recommendation(weather)}"
    
    history_text = ""
    if user.get("history"):
        recent = user["history"][-5:]
        for entry in recent:
            role = "Клиент" if entry["role"] == "user" else "Психолог"
            history_text += f"{role}: {entry['text']}\n"
    
    system_prompt = f"""Ты - друг, брат, наставник.

КОНТЕКСТ:
{context_text if context_text else ""}

ПРОФИЛЬ:
{profile_summary}

ИСТОРИЯ:
{history_text if history_text else ""}

Ответь на вопрос коротко, 2-4 предложения, по делу. Будь заботливым."""
    
    response = await call_deepseek(f"Вопрос: {message.text}", system_prompt, max_tokens=300)
    
    if not response:
        bottleneck_key = get_priority_order(scores)[0]
        bottleneck_lvl = level(scores[bottleneck_key])
        response = FALLBACK_ANALYSIS[bottleneck_key][bottleneck_lvl]
    
    if "history" not in user:
        user["history"] = []
    
    user["history"].append({
        "role": "user", 
        "text": message.text, 
        "timestamp": datetime.now().isoformat()
    })
    user["history"].append({
        "role": "assistant", 
        "text": response, 
        "timestamp": datetime.now().isoformat()
    })
    
    if len(user["history"]) > 10:
        user["history"] = user["history"][-10:]
    
    await thinking.delete()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="smart_questions")],
        [InlineKeyboardButton(text="🧠 К профилю", callback_data="show_results")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")]
    ])
    
    await message.answer(
        f"🧠 *Ответ*\n\n{response}",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    
    if is_test_completed(user):
        ironic = should_be_ironic(response)
        audio_data = await text_to_speech(response, ironic)
        
        if audio_data:
            audio_file = BufferedInputFile(audio_data, filename="response.ogg")
            await message.answer_voice(
                audio_file,
                caption="🎙 *Голосовой ответ*",
                parse_mode='Markdown'
            )
    
    user["stage"] = "menu"

# ══════════════════════════════════════════════
#  ЗАПУСК БОТА
# ══════════════════════════════════════════════

async def check_api_on_startup():
    logger.info("Проверяю DeepSeek API...")
    response = await call_deepseek("Ответь 'OK' одним словом", max_tokens=10)
    if response:
        logger.info("✅ DeepSeek API работает")
    else:
        logger.warning("❌ DeepSeek API не отвечает")

async def main():
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN не найден")
        print("❌ Ошибка: TELEGRAM_TOKEN не найден в .env файле")
        return
    
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher()
    
    task_manager.set_bot(bot)
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Вебхук удален")
    
    dp.message.register(start_command, Command("start"))
    dp.message.register(stats_command, Command("stats"))
    dp.message.register(apistatus_command, Command("apistatus"))
    dp.message.register(test_yandex_command, Command("test_yandex"))
    dp.message.register(test_voices_command, Command("test_voices"))
    dp.message.register(test_motivation_command, Command("test_mot"))
    dp.message.register(show_tasks_command, Command("tasks"))
    dp.callback_query.register(callback_handler)
    dp.message.register(handle_voice_message, lambda m: m.voice is not None)
    dp.message.register(handle_message)
    
    if DEEPSEEK_API_KEY:
        logger.info("DeepSeek API ключ найден")
        asyncio.create_task(check_api_on_startup())
    else:
        logger.warning("DeepSeek API ключ не найден")
    
    logger.info("Бот запущен...")
    print("\n" + "="*60)
    print("🚀 ВИРТУАЛЬНЫЙ ПСИХОЛОГ ЗАПУЩЕН!")
    print("="*60)
    print(f"👤 Ваш Telegram ID: {ADMIN_IDS[0] if ADMIN_IDS else 'не указан'}")
    print("📊 Команды: /stats, /apistatus, /test_yandex, /test_voices, /test_mot, /tasks")
    print("🎙 Распознавание: " + ("✅ Deepgram" if DEEPGRAM_API_KEY else "❌ нет"))
    print("🎙 Синтез речи: " + ("✅ Yandex" if YANDEX_API_KEY else "❌ нет"))
    print("🌍 Погода: " + ("✅ OpenWeather" if OPENWEATHER_API_KEY else "❌ нет"))
    print("🧠 Конфайнмент-моделирование: ✅ ДА")
    print("📅 Мотивация: через 5 мин и 24 часа")
    print("="*60 + "\n")
    
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    os.makedirs("stats", exist_ok=True)
    asyncio.run(main())
