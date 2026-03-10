#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ВИРТУАЛЬНЫЙ ПСИХОЛОГ - МАТРИЦА ПОВЕДЕНИЙ 4×6
ВЕРСИЯ 9.1: ИСПРАВЛЕННАЯ (контекст, форматирование, мысли психолога)
"""

import os
import json
import logging
import asyncio
import tempfile
import random
import re
import time
from typing import Optional, Dict, List, Any, Tuple, Union
from statistics import mean
from datetime import datetime, timedelta
from collections import defaultdict

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile, CallbackQuery, Message
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Импорты из наших новых модулей
from config import (
    TELEGRAM_TOKEN, 
    ADMIN_IDS, 
    COMMUNICATION_MODES,
    DEEPSEEK_API_KEY,
    DEEPGRAM_API_KEY,
    YANDEX_API_KEY,
    OPENWEATHER_API_KEY
)
from models import (
    UserContext, ReminderManager, DestinationManager, Statistics,
    ConfinementModel9, level
)
from services import (
    speech_to_text, text_to_speech, call_deepseek,
    generate_response_with_full_context, generate_ai_profile,
    generate_psychologist_thought
)

# Импортируем описания профилей и вопросы
from profiles import (
    STAGE_1_FEEDBACK,
    STAGE_2_FEEDBACK,
    STAGE_3_FEEDBACK,
    DILTS_LEVELS,
    FALLBACK_ANALYSIS,
    VECTORS,
    LEVEL_PROFILES
)
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
from hypno_module import HypnoOrchestrator, TherapeuticTales, Anchoring

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальные хранилища
user_data: Dict[int, Dict[str, Any]] = {}
user_names: Dict[int, str] = {}
user_contexts: Dict[int, UserContext] = {}
user_routes: Dict[int, Dict[str, Any]] = {}

# Инициализируем менеджеры
reminder_manager = ReminderManager()
destination_manager = DestinationManager()
stats = Statistics()

# Инициализируем гипнотический оркестратор
hypno = HypnoOrchestrator()
tales = TherapeuticTales()
anchoring = Anchoring()


# ============================================
# ФУНКЦИИ ДЛЯ БЕЗОПАСНОГО ФОРМАТИРОВАНИЯ ТЕКСТА
# ============================================

def escape_markdown(text: str) -> str:
    """Экранирует специальные символы Markdown и исправляет незакрытые теги"""
    if not text:
        return text
    
    # Список опасных символов в Markdown
    dangerous_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    result = []
    in_bold = False
    in_italic = False
    
    i = 0
    while i < len(text):
        char = text[i]
        
        # Проверяем на двойные звездочки (жирный текст)
        if char == '*' and i + 1 < len(text) and text[i + 1] == '*':
            result.append('**')
            in_bold = not in_bold
            i += 2
            continue
        # Проверяем на подчеркивание (курсив)
        elif char == '_':
            result.append('_')
            in_italic = not in_italic
            i += 1
            continue
        # Экранируем опасные символы вне форматирования
        elif char in dangerous_chars and not in_bold and not in_italic:
            result.append('\\' + char)
        else:
            result.append(char)
        
        i += 1
    
    return ''.join(result)


def clean_markdown(text: str) -> str:
    """Полностью очищает текст от Markdown (для безопасной отправки)"""
    if not text:
        return text
    
    # Удаляем Markdown-форматирование
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # жирный
    text = re.sub(r'__(.*?)__', r'\1', text)      # жирный через __
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # курсив
    text = re.sub(r'_(.*?)_', r'\1', text)        # курсив через _
    text = re.sub(r'`(.*?)`', r'\1', text)        # код
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # ссылки
    text = re.sub(r'!\[(.*?)\]\(.*?\)', r'\1', text) # картинки
    text = re.sub(r'#{1,6}\s+', '', text)          # заголовки
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)  # списки
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)  # нумерованные списки
    
    return text


def format_text_safe(text: str, parse_mode: str = 'HTML') -> str:
    """Безопасно форматирует текст для отправки"""
    if parse_mode == 'HTML':
        # Экранируем HTML-символы
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        # Добавляем базовое HTML-форматирование
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)
        text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    elif parse_mode == 'Markdown':
        text = escape_markdown(text)
    
    return text


# ============================================
# FSM СОСТОЯНИЯ
# ============================================

class TestStates(StatesGroup):
    # Существующие состояния
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
    
    # Состояния коррекции
    profile_confirmation = State()
    clarifying_selection = State()
    clarifying_test = State()
    alternative_test = State()
    
    # Состояния для работы с моделью
    viewing_confinement = State()
    viewing_intervention = State()
    
    # НОВЫЕ состояния
    profile_generated = State()
    destination_selection = State()
    route_generation = State()
    route_active = State()
    route_step_active = State()


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

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
    """Определяет тип восприятия"""
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
    """Рассчитывает уровень мышления"""
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
    """Группирует уровни"""
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


def is_test_completed(user_data: dict) -> bool:
    """Проверяет, завершен ли тест"""
    required_fields = ["perception_type", "thinking_level", "behavioral_levels", "dilts_counts", "deep_patterns"]
    for field in required_fields:
        if field not in user_data:
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


def safe_get_profile_info(vector: str, level_num: int, key: str, default: str = "Информация уточняется") -> str:
    """Безопасно получает информацию из профиля"""
    try:
        profile = LEVEL_PROFILES.get(vector, {}).get(level_num, {})
        if isinstance(profile, dict):
            # Пробуем разные возможные ключи
            if key == 'quote':
                return profile.get('quote') or profile.get('description') or profile.get('block1') or default
            elif key == 'pain_origin':
                return profile.get('pain_origin') or profile.get('origin') or profile.get('block2') or default
            elif key == 'pain_costs':
                costs = profile.get('pain_costs') or profile.get('costs') or []
                if costs:
                    return costs
                return ["Энергией", "Временем", "Возможностями"]
        else:
            # Если профиль - строка, используем её как quote
            if key == 'quote':
                return str(profile)
            elif key == 'pain_origin':
                return "Из вашего опыта"
            elif key == 'pain_costs':
                return ["Энергией", "Временем", "Возможностями"]
    except Exception as e:
        logger.error(f"Ошибка при получении информации из профиля: {e}")
    
    return default


# ============================================
# ФУНКЦИИ ДЛЯ ПРОСТОГО ОПИСАНИЯ ПРОФИЛЯ
# ============================================

def convert_to_simple_language(scores: dict, perception_type: str, thinking_level: int, deep_patterns: dict = None) -> dict:
    """Конвертирует технические данные в простые описания"""
    
    result = {}
    
    # 1. Внимание (куда смотрит)
    if perception_type in ["СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ", "СТАТУСНО-ОРИЕНТИРОВАННЫЙ"]:
        result['attention'] = "ВЫ ОРИЕНТИРУЕТЕСЬ НА ЛЮДЕЙ"
        result['attention_desc'] = "Для вас важно, что думают другие, вы чутко считываете настроение и ожидания окружающих."
    else:
        result['attention'] = "ВЫ ОРИЕНТИРУЕТЕСЬ НА СЕБЯ"
        result['attention_desc'] = "Для вас важнее ваши внутренние ощущения и чувства, чем мнение других."
    
    # 2. Мышление
    if thinking_level <= 3:
        result['thinking'] = "ВЫ МЫСЛИТЕ КОНКРЕТНО"
        result['thinking_desc'] = "Вы хорошо видите отдельные ситуации, но не всегда замечаете общие закономерности."
    elif thinking_level <= 6:
        result['thinking'] = "ВЫ МЫСЛИТЕ СИСТЕМНО"
        result['thinking_desc'] = "Вы замечаете закономерности, но не всегда видите, к чему они приведут в будущем."
    else:
        result['thinking'] = "ВЫ МЫСЛИТЕ ГЛУБОКО"
        result['thinking_desc'] = "Вы видите общие законы и можете предсказывать развитие ситуаций."
    
    # 3. СБ (реакция на угрозу)
    sb_level = level(scores.get("СБ", 3))
    sb_profiles = {
        1: "Под давлением вы замираете и не можете слова сказать.",
        2: "Вы избегаете конфликтов — уходите, прячетесь, уворачиваетесь.",
        3: "Вы соглашаетесь внешне, но внутри всё кипит.",
        4: "Вы внешне спокойны, но внутри держите всё в себе.",
        5: "Вы пытаетесь сгладить конфликт, перевести в шутку.",
        6: "Вы умеете защищать себя, но можете и атаковать в ответ."
    }
    result['sb_desc'] = sb_profiles.get(sb_level, "Вы по-разному реагируете на давление.")
    
    # 4. ТФ (деньги)
    tf_level = level(scores.get("ТФ", 3))
    tf_profiles = {
        1: "Деньги приходят и уходят — как повезёт.",
        2: "Вы ищете возможности, но каждый раз как с нуля.",
        3: "Вы умеете зарабатывать своим трудом.",
        4: "Вы хорошо зарабатываете и можете копить.",
        5: "Вы создаёте системы дохода и управляете финансами.",
        6: "Вы управляете капиталом и создаёте финансовые структуры."
    }
    result['tf_desc'] = tf_profiles.get(tf_level, "У вас свои отношения с деньгами.")
    result['tf_strong'] = tf_level >= 5
    
    # 5. УБ (понимание мира)
    ub_level = level(scores.get("УБ", 3))
    ub_profiles = {
        1: "Вы стараетесь не думать о сложном — само как-то решится.",
        2: "Вы верите в знаки, судьбу, высшие силы.",
        3: "Вы доверяете экспертам и авторитетам.",
        4: "Вы ищете скрытые смыслы и заговоры.",
        5: "Вы анализируете факты и делаете выводы сами.",
        6: "Вы строите теории и ищете закономерности."
    }
    result['ub_desc'] = ub_profiles.get(ub_level, "Вы по-своему понимаете мир.")
    result['ub_weak'] = ub_level <= 2
    
    # 6. ЧВ (отношения)
    chv_level = level(scores.get("ЧВ", 3))
    chv_profiles = {
        1: "Вы сильно привязываетесь к людям, тяжело без них.",
        2: "Вы подстраиваетесь под других, теряя себя.",
        3: "Вы хотите нравиться, показываете себя с лучшей стороны.",
        4: "Вы умеете влиять на людей, добиваться своего.",
        5: "Вы строите равные партнёрские отношения.",
        6: "Вы создаёте сообщества и сети контактов."
    }
    result['chv_desc'] = chv_profiles.get(chv_level, "У вас свои паттерны в отношениях.")
    
    # 7. Точка роста
    growth_map = {
        "ENVIRONMENT": "Посмотрите вокруг — может, дело в обстоятельствах?",
        "BEHAVIOR": "Попробуйте делать хоть что-то по-другому — маленькие шаги многое меняют.",
        "CAPABILITIES": "Развивайте новые навыки — они откроют новые возможности.",
        "VALUES": "Поймите, что для вас действительно важно — это изменит всё.",
        "IDENTITY": "Ответьте себе на вопрос «кто я?» — в этом ключ к изменениям."
    }
    result['growth_point'] = growth_map.get(perception_type, "Начните с малого — и увидите, куда приведёт.")
    
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
        # Находим вектор с минимальным значением (самая проблемная зона)
        min_vector = min(scores.items(), key=lambda x: level(x[1]))
        vector, score = min_vector
        lvl = level(score)
        
        # Безопасно получаем информацию из профиля
        quote = safe_get_profile_info(vector, lvl, 'quote', 'Пока не определено')
        pain_origin = safe_get_profile_info(vector, lvl, 'pain_origin', 'Из вашего опыта')
        costs = safe_get_profile_info(vector, lvl, 'pain_costs', ["Энергией", "Временем", "Возможностями"])
    else:
        vector = "СБ"
        quote = "Пока не определено"
        pain_origin = "Из вашего опыта"
        costs = ["Энергией", "Временем", "Возможностями"]
    
    lines.append("<b>🧠 ВАШ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ</b>\n")
    lines.append(f"<b>🔍 Тип восприятия:</b> {perception_type}\n")
    lines.append(f"<b>🧠 Уровень мышления:</b> {thinking_level}/9\n")
    lines.append("<b>🎯 Главный тормоз</b>")
    lines.append(f"{quote}\n")
    lines.append("<b>📜 Откуда это взялось</b>")
    lines.append(f"{pain_origin}\n")
    lines.append("<b>💸 Чем вы платите</b>")
    for cost in costs[:3]:
        lines.append(f"• {cost}")
    lines.append("")
    
    if model and hasattr(model, 'key_confinement') and model.key_confinement:
        elem = model.key_confinement.get('element')
        if elem and hasattr(elem, 'description'):
            lines.append("<b>⛓ Что держит систему</b>")
            lines.append(f"{elem.description[:100]}\n")
    
    if model and hasattr(model, 'loops') and model.loops:
        strongest = max(model.loops, key=lambda x: x.get('strength', 0))
        lines.append("<b>🔄 Главная ловушка</b>")
        lines.append(f"{strongest.get('description', 'Не определено')}")
        lines.append(f"Сила: {strongest.get('strength', 0):.1%}\n")
    
    dilts_desc = DILTS_LEVELS.get(dominant_dilts, "⚡ Поведение")
    lines.append(f"<b>🎯 Ваша точка роста:</b> {dilts_desc}")
    
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
# НОВЫЕ ЭКРАНЫ ПРИВЕТСТВИЯ
# ============================================

async def cmd_start(message: Message, state: FSMContext):
    """Обновленный обработчик команды /start"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Пользователь"
    
    user_names[user_id] = user_name
    
    await state.clear()
    
    if user_id not in user_contexts:
        user_contexts[user_id] = UserContext(user_id)
        user_contexts[user_id].name = user_name
    
    stats.register_start(user_id)
    
    context = user_contexts[user_id]
    
    # Проверяем, есть ли уже профиль
    data = await state.get_data()
    if is_test_completed(data):
        profile_code = data.get("profile_data", {}).get('display_name', 'SA-5_INT')
        
        text = f"""
<b>🧠 ФРЕДИ: ВИРТУАЛЬНЫЙ ПСИХОЛОГ</b>

👋 <b>О, {user_name}, я вас помню!</b>
(У меня, в отличие от людей, с памятью всё отлично — спасибо базе данных)

<b>📊 ВАШ ПРОФИЛЬ:</b> <code>{profile_code}</code>
(Лежит у меня в архивах, пылится...)

━━━━━━━━━━━━━━━━━━━━
<b>❓ ЧТО ДЕЛАЕМ?</b>

Вы можете:
🔄 <b>Пройти тест заново</b> — вдруг вы изменились?
   (Хотя люди редко меняются, но вдруг...)

━━━━━━━━━━━━━━━━━━━━
⬇️ <b>ВЫБИРАЙТЕ:</b>
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 ПЕРЕПРОЙТИ ТЕСТ", callback_data="restart_test")],
            [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")]
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode='HTML')
        return
    
    # ИСПРАВЛЕНО: проверяем, заполнен ли контекст
    if not (context.city and context.gender and context.age):
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
            f"   ↳ Что сформировало вас как личность\n\n"
            f"⏱ <b>15 минут</b> — и я буду знать о вас больше, чем вы думаете.\n"
            f"🔮 И да, я обещаю не использовать это против вас.\n"
            f"   <i>(Ну, только если вы сами не попросите)</i>\n\n"
            f"🚀 Ну что, начнём наше знакомство?"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Давай, погнали!", callback_data="start_context")],
            [InlineKeyboardButton(text="🤨 А ты вообще кто такой?", callback_data="why_details")]
        ])
        
        await message.answer(welcome_text, reply_markup=keyboard, parse_mode='HTML')
        return
    
    # Если контекст уже заполнен, показываем меню
    await show_main_menu(message, context)


async def show_why_details(callback: CallbackQuery, state: FSMContext):
    """Показывает детальную информацию о боте"""
    
    text = """<b>🎭 Ну, вопрос хороший. Давайте по существу.</b>

Видите ли, дорогой человек, я — экспериментальная модель.
Андрей Мейстер однажды подумал: "А что, если я создам свою цифровую копию?
Пусть работает, пока я сплю, ем или просто ленюсь".

Так я и появился. 🧠

<b>🧐 Что я умею (помимо того, что шучу как он и временами бешу):</b>

• Вижу паттерны там, где вы видите просто день сурка
• Нахожу систему в ваших "случайных" решениях
• Понимаю, почему вы выбираете одних и тех же "не тех" людей
• И да — я реально беспристрастен. У меня нет плохого настроения,
  я не обижаюсь и не осуждаю. (Ну, почти. Иногда хочется, но алгоритмы не позволяют)

<b>🎯 Конкретно по тесту:</b>

1️⃣ <b>Восприятие</b> — поймём, какую линзу вы носите
2️⃣ <b>Мышление</b> — узнаем, как вы пережёвываете реальность
3️⃣ <b>Поведение</b> — посмотрим, что вы делаете "на автомате"
4️⃣ <b>Точка роста</b> — я скажу, куда вам двигаться (спойлер: не в стену)
5️⃣ <b>Глубинные паттерны</b> — заглянем в детство и подсознание

⏱ <b>15 минут.</b> Потом я составлю ваш профиль и мы поговорим по делу.

🔮 И да, я реально могу быть полезен.
   Просто доверьтесь цифровому психопа... психологу! 😉

<b>👌 Погнали?</b>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👌 Погнали!", callback_data="start_context")],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await callback.answer()


# ============================================
# НОВЫЕ ФУНКЦИИ ДЛЯ НАВИГАЦИИ
# ============================================

async def show_destinations(callback: CallbackQuery, state: FSMContext):
    """Показывает точки назначения после выбора режима"""
    
    user_id = callback.from_user.id
    data = await state.get_data()
    context = user_contexts.get(user_id)
    
    mode = data.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    profile_data = data.get("profile_data", {})
    profile_code = profile_data.get('display_name', 'SA-5_INT')
    
    # Получаем рекомендации
    recommended = destination_manager.recommend_by_profile(profile_code, mode)
    
    text = f"""
{mode_config['emoji']} <b>РЕЖИМ {mode_config['name']} АКТИВИРОВАН</b>

<b>🎯 ВЫБЕРИТЕ ТОЧКУ НАЗНАЧЕНИЯ</b>

Я вижу, что в вашем профиле сейчас наиболее актуально:

━━━━━━━━━━━━━━━━━━━━
👇 <b>Куда двинемся?</b>
"""
    
    # Строим клавиатуру с категориями
    keyboard = []
    destinations = destination_manager.get_destinations_for_mode(mode)
    
    for cat_id, category in destinations.items():
        keyboard.append([InlineKeyboardButton(
            text=f"━━━ {category['name']} ━━━",
            callback_data="ignore"
        )])
        
        row = []
        for i, dest in enumerate(category["destinations"]):
            prefix = "⭐ " if dest["id"] in recommended else ""
            button = InlineKeyboardButton(
                text=f"{prefix}{dest['name']}",
                callback_data=f"dest_{cat_id}_{dest['id']}"
            )
            row.append(button)
            
            if len(row) == 2 or i == len(category["destinations"]) - 1:
                keyboard.append(row)
                row = []
    
    keyboard.append([InlineKeyboardButton(
        text="✏️ Сформулирую сам", 
        callback_data="custom_destination"
    )])
    keyboard.append([InlineKeyboardButton(
        text="◀️ К выбору режима", 
        callback_data="show_mode_selection"
    )])
    
    await callback.message.edit_text(
        text, 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='HTML'
    )
    await state.set_state(TestStates.destination_selection)


async def show_destination_route(callback: CallbackQuery, state: FSMContext):
    """Показывает маршрут к выбранной точке"""
    
    data_parts = callback.data.split('_')
    if len(data_parts) < 3:
        return
    
    cat_id = data_parts[1]
    dest_id = data_parts[2]
    
    user_id = callback.from_user.id
    state_data = await state.get_data()
    mode = state_data.get("communication_mode", "coach")
    
    # Находим выбранную точку
    dest_info = None
    destinations = destination_manager.get_destinations_for_mode(mode)
    
    if cat_id in destinations:
        for dest in destinations[cat_id]["destinations"]:
            if dest["id"] == dest_id:
                dest_info = dest
                break
    
    if not dest_info:
        await callback.answer("Точка не найдена")
        return
    
    # Сохраняем выбранную точку
    await state.update_data(
        current_destination=dest_info,
        destination_category=cat_id,
        route_step=1,
        route_progress=[]
    )
    
    await callback.message.edit_text(
        "<b>🧠 Строю оптимальный маршрут...</b>\n\n"
        "Это займёт несколько секунд.",
        parse_mode='HTML'
    )
    
    # Генерируем маршрут через ИИ
    from services import generate_route_ai
    route = await generate_route_ai(user_id, state_data, dest_info)
    
    if route:
        await state.update_data(current_route=route)
        await show_route_step(callback, state, 1, route)
    else:
        await show_fallback_route(callback, state, dest_info)


async def show_route_step(callback: CallbackQuery, state: FSMContext, step: int, route: Dict):
    """Показывает текущий шаг маршрута"""
    
    data = await state.get_data()
    destination = data.get("current_destination", {})
    mode = data.get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    text = f"""
{mode_config['emoji']} <b>МАРШРУТ К ЦЕЛИ</b>

<b>🎯 Точка назначения:</b> {destination['name']}
<b>⏱ Ориентировочное время:</b> {destination['time']}

━━━━━━━━━━━━━━━━━━━━
{route.get('full_text', 'Маршрут строится...')}

━━━━━━━━━━━━━━━━━━━━
👇 <b>Отмечайте выполнение, когда готовы</b>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ВЫПОЛНИЛ ЭТАП", callback_data="route_step_done")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions")],
        [InlineKeyboardButton(text="◀️ К ЦЕЛЯМ", callback_data="show_destinations")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(TestStates.route_active)
    
    await reminder_manager.schedule_motivation_sequence(callback.from_user.id, destination)


async def route_step_done(callback: CallbackQuery, state: FSMContext):
    """Отмечает выполнение этапа"""
    
    data = await state.get_data()
    step = data.get("route_step", 1)
    route_progress = data.get("route_progress", [])
    
    route_progress.append(step)
    next_step = step + 1
    
    await state.update_data(
        route_step=next_step,
        route_progress=route_progress
    )
    
    if next_step > 3:
        await show_route_complete(callback, state)
    else:
        await callback.message.edit_text(
            f"<b>✅ Этап {step} выполнен!</b>\n\nПереходим к этапу {next_step}...",
            parse_mode='HTML'
        )
        await asyncio.sleep(1)
        
        route = data.get("current_route", {})
        await show_route_step(callback, state, next_step, route)


async def show_route_complete(callback: CallbackQuery, state: FSMContext):
    """Показывает завершение маршрута"""
    
    data = await state.get_data()
    destination = data.get("current_destination", {})
    
    text = f"""
<b>🎉 МАРШРУТ ЗАВЕРШЕН!</b>

Поздравляю! Вы достигли цели: <b>{destination['name']}</b>

━━━━━━━━━━━━━━━━━━━━
<b>💪 ГОРДИТЕСЬ СОБОЙ</b>

Хотите выбрать новую цель или закрепить результат?
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 НОВАЯ ЦЕЛЬ", callback_data="show_destinations")],
        [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await state.update_data(route_step=None, current_destination=None)
    
    reminder_manager.cancel_user_reminders(callback.from_user.id)


async def show_fallback_route(callback: CallbackQuery, state: FSMContext, destination: dict):
    """Резервный маршрут, если ИИ не отвечает"""
    
    mode = (await state.get_data()).get("communication_mode", "coach")
    mode_config = COMMUNICATION_MODES.get(mode, COMMUNICATION_MODES["coach"])
    
    text = f"""
{mode_config['emoji']} <b>МАРШРУТ К ЦЕЛИ</b>

<b>🎯 Точка назначения:</b> {destination['name']}
<b>⏱ Ориентировочное время:</b> {destination['time']}

━━━━━━━━━━━━━━━━━━━━
📍 <b>ЭТАП 1: ДИАГНОСТИКА</b>
   • Что делаем: анализируем текущую ситуацию
   • Домашнее задание: записываем всё, что связано с целью
   • Критерий: есть список наблюдений

📍 <b>ЭТАП 2: ПЛАНИРОВАНИЕ</b>
   • Что делаем: составляем пошаговый план
   • Домашнее задание: разбиваем цель на микро-шаги
   • Критерий: есть конкретный план

📍 <b>ЭТАП 3: ДЕЙСТВИЕ</b>
   • Что делаем: начинаем с первого микро-шага
   • Домашнее задание: каждый день делать хотя бы одно действие
   • Критерий: первый шаг сделан

━━━━━━━━━━━━━━━━━━━━
👇 <b>Начинаем?</b>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ НАЧАТЬ", callback_data="route_step_done")],
        [InlineKeyboardButton(text="◀️ К ЦЕЛЯМ", callback_data="show_destinations")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(TestStates.route_active)


# ============================================
# ОБНОВЛЕННЫЙ show_final_profile
# ============================================

async def show_final_profile(callback: CallbackQuery, state: FSMContext):
    """Показывает финальный профиль после всех этапов"""
    
    user_id = callback.from_user.id
    data = await state.get_data()
    
    if data.get("ai_generated_profile"):
        await show_ai_generated_profile(callback, state, data["ai_generated_profile"])
        return
    
    status_msg = await callback.message.answer(
        "<b>🧠 Анализирую данные...</b>\n\n"
        "Собираю воедино результаты 5 этапов тестирования.\n"
        "Это займёт около 20-30 секунд.\n\n"
        "<i>Формирую ваш точный психологический портрет...</i>",
        parse_mode='HTML'
    )
    
    ai_profile = await generate_ai_profile(user_id, data)
    
    await status_msg.delete()
    
    if ai_profile:
        await state.update_data(ai_generated_profile=ai_profile)
        await show_ai_generated_profile(callback, state, ai_profile)
    else:
        await show_old_final_profile(callback, state)


async def show_ai_generated_profile(callback: CallbackQuery, state: FSMContext, ai_profile: str):
    """Показывает профиль, сгенерированный ИИ"""
    
    # Очищаем от Markdown и форматируем для HTML
    clean_text = clean_markdown(ai_profile)
    
    text = f"""
<b>🧠 ВАШ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ</b>

{clean_text}

━━━━━━━━━━━━━━━━━━━━
👇 <b>Что дальше?</b>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 МЫСЛИ ПСИХОЛОГА", callback_data="psychologist_thought")],
        [InlineKeyboardButton(text="🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_destinations")],
        [InlineKeyboardButton(text="⚙️ ВЫБРАТЬ РЕЖИМ", callback_data="show_mode_selection")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(TestStates.profile_generated)


async def show_old_final_profile(callback: CallbackQuery, state: FSMContext):
    """Старая версия финального профиля (резерв)"""
    data = await state.get_data()
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    perception_type = data.get("perception_type", "не определен")
    thinking_level = data.get("thinking_level", 5)
    dilts_counts = data.get("dilts_counts", {})
    dominant_dilts = determine_dominant_dilts(dilts_counts)
    
    profile_text = get_human_readable_profile(
        scores, 
        model=None,
        perception_type=perception_type,
        thinking_level=thinking_level,
        dominant_dilts=dominant_dilts
    )
    
    text = f"{profile_text}\n\n━━━━━━━━━━━━━━━━━━━━\n👇 <b>Что дальше?</b>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 МЫСЛИ ПСИХОЛОГА", callback_data="psychologist_thought")],
        [InlineKeyboardButton(text="🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_destinations")],
        [InlineKeyboardButton(text="⚙️ ВЫБРАТЬ РЕЖИМ", callback_data="show_mode_selection")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(TestStates.profile_generated)


# ============================================
# ОБРАБОТЧИКИ ЭТАПА 1
# ============================================

async def show_stage_1_intro(callback: CallbackQuery, state: FSMContext):
    """Экран перед ЭТАПОМ 1"""
    user_id = callback.from_user.id
    
    await state.set_state(TestStates.stage_1)
    
    intro_text = (
        f"<b>🧠 ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ</b>\n\n"
        f"Восприятие — это линза, через которую вы смотрите на мир.\n\n"
        f"Она сформирована культурой, нормами, ценностями и опытом, который вас строил. Это определило, что вы замечаете автоматически, а что остаётся за кадром.\n\n"
        f"<b>🔍 Что мы исследуем:</b>\n"
        f"• Куда направлено ваше внимание — вовне или внутрь\n"
        f"• Какая тревога доминирует — страх отвержения или страх потери контроля\n\n"
        f"<b>📊 Вопросов:</b> 8\n"
        f"<b>⏱ Время:</b> ~3 минуты\n\n"
        f"<i>Отвечайте честно — это поможет мне лучше понять вас.</i>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать исследование", callback_data="start_stage_1")]
    ])
    
    await callback.message.edit_text(intro_text, reply_markup=keyboard, parse_mode='HTML')


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
        f"<b>🧠 ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ</b>\n\n"
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
        
        if not parts[1].isdigit():
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
    
    # Очищаем от Markdown и форматируем для HTML
    result_text = clean_markdown(result_text)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Перейти к этапу 2", callback_data="show_stage_2_intro")]
    ])
    
    await callback.message.edit_text(result_text, reply_markup=keyboard, parse_mode='HTML')
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
        f"<b>🧠 ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ</b>\n\n"
        f"Восприятие определяет, что вы видите. Мышление — как вы это понимаете.\n\n"
        f"Конфигурация мышления определяется задачами: как вы обрабатываете информацию, какие связи видите, какой объём можете удержать.\n\n"
        f"<b>🎯 Самое важное:</b>\n"
        f"Конфигурация мышления — это траектория с чётким пунктом назначения: результат, к которому вы придёте. Если ничего не менять — вы попадёте именно туда.\n\n"
        f"<b>📊 Вопросов:</b> {total_questions}\n"
        f"<b>⏱ Время:</b> ~3-4 минуты\n\n"
        f"<i>Продолжим исследование?</i>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать исследование", callback_data="start_stage_2")]
    ])
    
    await callback.message.edit_text(intro_text, reply_markup=keyboard, parse_mode='HTML')


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
        f"<b>🧠 ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ</b>\n\n"
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
        
        if not parts[1].isdigit():
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
    
    # Очищаем от Markdown
    result_text = clean_markdown(result_text)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Перейти к этапу 3", callback_data="show_stage_3_intro")]
    ])
    
    await callback.message.edit_text(result_text, reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(TestStates.stage_3)


# ============================================
# ОБРАБОТЧИКИ ЭТАПА 3
# ============================================

async def show_stage_3_intro(callback: CallbackQuery, state: FSMContext):
    """Экран перед ЭТАПОМ 3"""
    user_id = callback.from_user.id
    
    intro_text = (
        f"<b>🧠 ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ</b>\n\n"
        f"Восприятие определяет, что вы видите.\n"
        f"Мышление — как вы это понимаете.\n\n"
        f"Конфигурация поведения — это то, как вы на это реагируете.\n\n"
        f"В ней уже встроены стереотипы, роли и паттерны, которые вы когда-то переняли у других.\n\n"
        f"<b>🔍 Здесь мы исследуем:</b>\n"
        f"• Ваши автоматические реакции\n"
        f"• Как вы действуете в разных ситуациях\n"
        f"• Какие стратегии поведения закреплены\n\n"
        f"<b>📊 Вопросов:</b> 8\n"
        f"<b>⏱ Время:</b> ~3 минуты\n\n"
        f"<i>Продолжим?</i>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать исследование", callback_data="start_stage_3")]
    ])
    
    await callback.message.edit_text(intro_text, reply_markup=keyboard, parse_mode='HTML')


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
        f"<b>🧠 ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ</b>\n\n"
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
        
        if not parts[1].isdigit():
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
    
    # Очищаем от Markdown
    result_text = clean_markdown(result_text)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Перейти к этапу 4", callback_data="show_stage_4_intro")]
    ])
    
    await callback.message.edit_text(result_text, reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(TestStates.stage_4)


# ============================================
# ОБРАБОТЧИКИ ЭТАПА 4
# ============================================

async def show_stage_4_intro(callback: CallbackQuery, state: FSMContext):
    """Экран перед ЭТАПОМ 4"""
    user_id = callback.from_user.id
    
    intro_text = (
        f"<b>🧠 ЭТАП 4: ТОЧКА РОСТА</b>\n\n"
        f"Восприятие — что вы видите.\n"
        f"Мышление — как понимаете.\n"
        f"Поведение — как реагируете.\n"
        f"Всё это — ваша внутренняя система.\n\n"
        f"🌍 Но она живёт внутри внешней системы — общества, которое постоянно меняется.\n\n"
        f"⚡ Когда одна система меняется, а другая — нет, возникает напряжение.\n\n"
        f"<b>🔍 Здесь мы найдём, где именно находится рычаг — место, где минимальное усилие даёт максимальные изменения.</b>\n\n"
        f"<b>📊 Вопросов:</b> 8\n"
        f"<b>⏱ Время:</b> ~3 минуты\n\n"
        f"<i>Готовы найти свою точку роста?</i>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать исследование", callback_data="start_stage_4")]
    ])
    
    await callback.message.edit_text(intro_text, reply_markup=keyboard, parse_mode='HTML')


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
        f"<b>🧠 ЭТАП 4: ТОЧКА РОСТА</b>\n\n"
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
        
        if not parts[1].isdigit():
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
    model.build_from_profile(scores, data.get('history', []))
    await state.update_data(confinement_model=model.to_dict())
    
    logger.info(f"✅ User {user_id}: Stage 4 complete, profile={profile_data.get('display_name', 'unknown')}")
    
    # Показываем предварительный профиль
    await show_preliminary_profile(callback, state)


# ============================================
# НОВЫЕ ФУНКЦИИ: ПОКАЗ ПРЕДВАРИТЕЛЬНОГО ПРОФИЛЯ
# ============================================

async def show_preliminary_profile(callback: CallbackQuery, state: FSMContext):
    """Показывает предварительный портрет простым языком"""
    
    data = await state.get_data()
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    
    scores = {}
    for k in VECTORS:
        levels = data.get("behavioral_levels", {}).get(k, [])
        scores[k] = sum(levels) / len(levels) if levels else 3.0
    
    perception_type = data.get("perception_type", "unknown")
    thinking_level = data.get("thinking_level", 5)
    
    simple_profile = convert_to_simple_language(
        scores, perception_type, thinking_level
    )
    
    confidence = calculate_profile_confidence(data)
    confidence_bar = "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
    
    text = f"""
<b>🧠 ПРЕДВАРИТЕЛЬНЫЙ ПОРТРЕТ</b>

{simple_profile['attention_desc']}

{simple_profile['thinking_desc']}

<b>📊 ТВОИ ВЕКТОРЫ:</b>
• Реакция на давление: {simple_profile['sb_desc']}
• Отношение к деньгам: {simple_profile['tf_desc']}
• Понимание мира: {simple_profile['ub_desc']}
• Отношения с людьми: {simple_profile['chv_desc']}

<b>🎯 Точка роста:</b> {simple_profile['growth_point']}

<b>📊 Уверенность:</b> {confidence_bar} {int(confidence*100)}%

👇 <b>ЭТО ПОХОЖЕ НА ВАС?</b>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ДА", callback_data="profile_confirm")],
        [InlineKeyboardButton(text="❓ ЕСТЬ СОМНЕНИЯ", callback_data="profile_doubt")],
        [InlineKeyboardButton(text="🔄 НЕТ", callback_data="profile_reject")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(TestStates.profile_confirmation)


def calculate_profile_confidence(profile: dict) -> float:
    """Рассчитывает уверенность в профиле"""
    confidence = 0.5
    
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
    
    clarification_count = profile.get("clarification_iteration", 0)
    confidence += clarification_count * 0.05
    
    return min(1.0, confidence)


# ============================================
# НОВЫЕ ФУНКЦИИ: ОБРАБОТКА ПОДТВЕРЖДЕНИЯ ПРОФИЛЯ
# ============================================

async def profile_confirm(callback: CallbackQuery, state: FSMContext):
    """Пользователь подтвердил профиль"""
    
    await callback.answer("✅ Отлично! Тогда исследуем глубину...")
    
    # Показываем 5-й этап
    await show_stage_5_intro(callback, state)


async def profile_doubt(callback: CallbackQuery, state: FSMContext):
    """Пользователь сомневается"""
    
    data = await state.get_data()
    
    current_levels = {}
    for vector in VECTORS:
        levels = data.get("behavioral_levels", {}).get(vector, [])
        current_levels[vector] = sum(levels) / len(levels) if levels else 3
    
    await ask_whats_wrong(callback, state, current_levels)


async def profile_reject(callback: CallbackQuery, state: FSMContext):
    """Пользователь полностью не согласен"""
    
    await callback.answer("🔄 Хорошо, попробуем иначе...")
    
    await state.clear()
    await back_to_intro(callback)


async def ask_whats_wrong(callback: CallbackQuery, state: FSMContext, current_levels: dict):
    """Спрашивает, что именно не так"""
    
    text = """
<b>🔍 ДАВАЙ УТОЧНИМ</b>

Что именно вам не подходит?
(можно выбрать несколько)

🎭 Про людей — я не так сильно завишу от чужого мнения
💰 Про деньги — у меня с ними по-другому
🔍 Про знаки — я вполне себе анализирую
🤝 Про отношения — я знаю, чего хочу
🛡 Про давление — я реагирую иначе

👇 <b>Выберите и нажмите ДАЛЬШЕ</b>
"""
    
    await state.update_data(clarifying_levels=current_levels)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎭 Про людей", callback_data="discrepancy_people")],
        [InlineKeyboardButton(text="💰 Про деньги", callback_data="discrepancy_money")],
        [InlineKeyboardButton(text="🔍 Про знаки", callback_data="discrepancy_signs")],
        [InlineKeyboardButton(text="🤝 Про отношения", callback_data="discrepancy_relations")],
        [InlineKeyboardButton(text="🛡 Про давление", callback_data="discrepancy_sb")],
        [InlineKeyboardButton(text="➡️ ДАЛЬШЕ", callback_data="clarify_next")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(TestStates.clarifying_selection)
    
    await state.update_data(discrepancies=[])


async def handle_discrepancy(callback: CallbackQuery, state: FSMContext, discrepancy: str):
    """Обрабатывает выбор расхождения"""
    
    data = await state.get_data()
    discrepancies = data.get("discrepancies", [])
    
    if discrepancy not in discrepancies:
        discrepancies.append(discrepancy)
        await state.update_data(discrepancies=discrepancies)
        await callback.answer(f"✅ Добавлено")
    else:
        discrepancies.remove(discrepancy)
        await state.update_data(discrepancies=discrepancies)
        await callback.answer(f"❌ Убрано")


async def clarify_next(callback: CallbackQuery, state: FSMContext):
    """Переходит к уточняющим вопросам"""
    
    data = await state.get_data()
    discrepancies = data.get("discrepancies", [])
    current_levels = data.get("clarifying_levels", {})
    
    if not discrepancies:
        await callback.answer("Выберите хотя бы одно расхождение!")
        return
    
    questions = get_clarifying_questions(discrepancies, current_levels)
    
    if not questions:
        await callback.answer("Зададим общие уточняющие вопросы")
        return
    
    await state.update_data(
        clarifying_questions=questions,
        clarifying_current=0,
        clarifying_answers=[]
    )
    
    await ask_clarifying_question(callback, state)


async def ask_clarifying_question(callback: CallbackQuery, state: FSMContext):
    """Задаёт уточняющий вопрос"""
    
    data = await state.get_data()
    questions = data.get("clarifying_questions", [])
    current = data.get("clarifying_current", 0)
    
    if current >= len(questions):
        await update_profile_with_clarifications(callback, state)
        return
    
    question = questions[current]
    
    question_text = f"""
<b>🔍 УТОЧНЯЮЩИЙ ВОПРОС {current + 1}/{len(questions)}</b>

{question['text']}
"""
    
    keyboard = []
    options = question.get('options', {})
    for opt_key, opt_text in options.items():
        callback_data = f"clarify_answer_{current}_{opt_key}"
        keyboard.append([InlineKeyboardButton(text=opt_text, callback_data=callback_data)])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await callback.message.edit_text(question_text, reply_markup=reply_markup, parse_mode='HTML')


async def handle_clarifying_answer(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает ответ на уточняющий вопрос"""
    
    data = await state.get_data()
    parts = callback.data.split("_")
    if len(parts) < 4:
        return
    
    if not parts[2].isdigit():
        return
    current = int(parts[2])
    answer_key = parts[3]
    
    questions = data.get("clarifying_questions", [])
    if current >= len(questions):
        return
    
    question = questions[current]
    
    answers = data.get("clarifying_answers", [])
    answers.append({
        "question": question['text'],
        "answer_key": answer_key,
        "answer_text": question['options'].get(answer_key, ""),
        "type": question.get('type'),
        "target": question.get('target') or question.get('vector')
    })
    
    await state.update_data(
        clarifying_answers=answers,
        clarifying_current=current + 1
    )
    
    await ask_clarifying_question(callback, state)


async def update_profile_with_clarifications(callback: CallbackQuery, state: FSMContext):
    """Обновляет профиль с учётом уточнений"""
    
    data = await state.get_data()
    answers = data.get("clarifying_answers", [])
    
    iteration = data.get("clarification_iteration", 0) + 1
    await state.update_data(clarification_iteration=iteration)
    
    await show_preliminary_profile(callback, state)


# ============================================
# НОВЫЕ ФУНКЦИИ: 5-Й ЭТАП
# ============================================

async def show_stage_5_intro(callback: CallbackQuery, state: FSMContext):
    """Экран перед 5-м этапом"""
    
    intro_text = """
<b>🧠 ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ</b>

Мы узнали, как вы воспринимаете мир, мыслите и действуете.
Теперь пришло время заглянуть глубже — в то, что сформировало вас.

<b>🔍 Здесь мы исследуем:</b>
• Какой у вас тип привязанности (из детства)
• Какие защитные механизмы вы используете
• Какие глубинные убеждения управляют вами
• Чего вы боитесь на самом деле

<b>📊 Вопросов:</b> 10
<b>⏱ Время:</b> ~5 минут

👇 <b>Готовы заглянуть вглубь себя?</b>
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать исследование", callback_data="start_stage_5")]
    ])
    
    await callback.message.edit_text(intro_text, reply_markup=keyboard, parse_mode='HTML')
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
<b>🧠 ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ</b>

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
        
        if not parts[1].isdigit():
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
    
    deep_patterns = analyze_stage5_results(stage5_answers)
    await state.update_data(deep_patterns=deep_patterns)
    
    logger.info(f"✅ User {callback.from_user.id}: Stage 5 complete")
    
    await show_final_profile(callback, state)


# ============================================
# AI АНАЛИЗ (ИСПРАВЛЕНО!)
# ============================================

async def show_ai_analysis(callback: CallbackQuery, state: FSMContext):
    """Показывает мысли психолога"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    if data.get("psychologist_thought"):
        await show_saved_psychologist_thought(callback, data["psychologist_thought"])
        return
    
    # Отправляем новое сообщение о начале анализа
    status_msg = await callback.message.answer(
        "<b>🧠 Анализирую через конфайнмент-модель...</b>\n\n"
        "<i>Это займёт около 15-20 секунд</i>",
        parse_mode='HTML'
    )
    
    thought = await generate_psychologist_thought(user_id, data)
    
    # Удаляем статусное сообщение
    await status_msg.delete()
    
    if thought:
        await state.update_data(psychologist_thought=thought)
        await show_saved_psychologist_thought(callback, thought)
    else:
        # Отправляем сообщение об ошибке
        await callback.message.answer(
            "❌ Не удалось сгенерировать анализ",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="show_results")]
            ])
        )


async def show_saved_psychologist_thought(callback: CallbackQuery, thought: str):
    """Показывает сохраненные мысли психолога"""
    
    # Очищаем текст от Markdown
    clean_thought = clean_markdown(thought)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 ВЫБРАТЬ ЦЕЛЬ", callback_data="show_destinations")],
        [InlineKeyboardButton(text="◀️ К ПОРТРЕТУ", callback_data="show_results")]
    ])
    
    # Отправляем новым сообщением
    await callback.message.answer(
        f"<b>🧠 МЫСЛИ ПСИХОЛОГА</b>\n\n{clean_thought}",
        reply_markup=keyboard,
        parse_mode='HTML'
    )


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
        header = f"{mode_config['emoji']} <b>ЗАДАЙТЕ ВОПРОС (КОУЧ)</b>\n\nЯ буду задавать открытые вопросы, помогая вам найти ответы внутри себя.\n\n"
    elif mode == "friend":
        header = f"{mode_config['emoji']} <b>РАССКАЖИТЕ МНЕ (ДРУГ)</b>\n\nЯ здесь, чтобы выслушать и поддержать. Что у вас на душе?\n\n"
    elif mode == "trainer":
        header = f"{mode_config['emoji']} <b>ПОСТАВЬТЕ ЗАДАЧУ (ТРЕНЕР)</b>\n\nЧётко сформулируйте, что хотите решить. Я дам конкретные шаги.\n\n"
    else:
        header = "<b>❓ ЗАДАЙТЕ ВОПРОС</b>\n\n"
    
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
        parse_mode='HTML'
    )


async def handle_smart_question(callback: CallbackQuery, state: FSMContext, question: str):
    """Обрабатывает выбранный умный вопрос"""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    await callback.message.edit_text(
        "<b>🤔 Думаю над ответом...</b>\n\n"
        "<i>Это займёт около 10-15 секунд</i>",
        parse_mode='HTML'
    )
    
    response = await generate_response_with_full_context(user_id, question, data, user_contexts)
    
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
    
    # Очищаем ответ от Markdown
    clean_response = clean_markdown(response)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="smart_questions")],
        [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
        [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")]
    ])
    
    await callback.message.edit_text(
        f"<b>❓ {question}</b>\n\n{clean_response}",
        parse_mode='HTML',
        reply_markup=keyboard
    )
    
    audio_data = await text_to_speech(response, mode)
    if audio_data:
        audio_file = BufferedInputFile(audio_data, filename="response.ogg")
        await callback.message.answer_voice(
            audio_file,
            caption="<b>🎙 Голосовой ответ</b>",
            parse_mode='HTML'
        )


# ============================================
# ОБРАБОТЧИКИ ПОМОЩИ
# ============================================

async def show_help(callback: CallbackQuery, state: FSMContext):
    """Показывает меню помощи"""
    keyboard = get_help_keyboard()
    await callback.message.edit_text(
        "<b>🎯 ЧЕМ Я МОГУ БЫТЬ ПОЛЕЗЕН</b>\n\n"
        "Выберите категорию или напишите сами:",
        reply_markup=keyboard,
        parse_mode='HTML'
    )


async def handle_help_category(callback: CallbackQuery, state: FSMContext, category: str):
    """Обработчик категорий помощи"""
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    
    category_texts = {
        "relations": "🗣 <b>Отношения</b>\n\nРасскажите, что происходит в отношениях. Я помогу разобраться.",
        "money": "💰 <b>Деньги и ресурсы</b>\n\nЧто беспокоит в финансовой сфере?",
        "self": "🧠 <b>Самоощущение</b>\n\nРасскажите о том, что чувствуете.",
        "knowledge": "📚 <b>Знания и развитие</b>\n\nЧто хотите понять или освоить?",
        "support": "💪 <b>Поддержка</b>\n\nНужно просто выговориться? Я здесь.",
        "muse": "🎨 <b>Муза и творчество</b>\n\nТворческий блок? Расскажите.",
        "care": "🍏 <b>Забота о себе</b>\n\nКак вы заботитесь о себе?"
    }
    
    base_text = category_texts.get(category, "Чем я могу помочь?")
    
    if context and context.weather_cache:
        weather = context.weather_cache
        base_text += f"\n\n{context.get_greeting()}\n"
        base_text += f"{weather['icon']} {weather['description']}, {weather['temp']}°C"
    
    base_text += f"\n\n👇 Напишите своим текстом:"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="show_help")]
    ])
    
    await callback.message.edit_text(base_text, parse_mode='HTML', reply_markup=keyboard)
    await state.set_state(TestStates.awaiting_question)
    await state.update_data(question_context=category)


# ============================================
# СКАЗКИ
# ============================================

async def show_tale(callback: CallbackQuery, state: FSMContext):
    """Показывает случайную сказку"""
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    
    tale = tales.get_tale_for_issue("рост")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 ЕЩЁ СКАЗКУ", callback_data="show_tale")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="show_results")]
    ])
    
    intro = f"<b>📖 {tale['title']}</b>\n\n"
    
    # Очищаем текст сказки от Markdown
    clean_tale_text = clean_markdown(tale['text'])
    
    await callback.message.edit_text(
        intro + clean_tale_text[:4000],
        parse_mode='HTML',
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
    
    # Принудительный сброс (чтобы точно спросило)
    context.city = None
    context.gender = None
    context.age = None
    
    question, keyboard = await context.ask_for_context()
    
    if question:
        await callback.message.answer(
            f"<b>📝 Давайте познакомимся</b>\n\n{question}",
            reply_markup=keyboard,
            parse_mode='HTML'
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
    
    await callback.message.edit_text(
        f"⏭ Хорошо, будем общаться без привязки к месту и времени.\n\n"
        "Но помните: с контекстом советы точнее 😉\n"
        "Можете в любой момент рассказать о себе — просто напишите /context",
        parse_mode='HTML'
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
            await callback.message.edit_text(
                f"<b>📝 Давайте познакомимся</b>\n\n{question}",
                reply_markup=keyboard,
                parse_mode='HTML'
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
            await callback.message.edit_text(
                f"<b>📝 Давайте познакомимся</b>\n\n{question}",
                reply_markup=keyboard,
                parse_mode='HTML'
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
            await message.answer(
                f"<b>📝 Давайте познакомимся</b>\n\n{next_question}",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        else:
            await show_context_complete(message, state, context)
    else:
        await message.answer(next_question or "Пожалуйста, ответьте корректно.")
    
    return True


async def show_context_complete(message_or_callback, state: FSMContext, context: UserContext):
    """Показывает итоговый экран после сбора контекста"""
    
    await context.update_weather()
    
    summary = f"<b>✅ Отлично! Теперь я знаю о вас:</b>\n\n"
    
    if context.city:
        summary += f"📍 Город: {context.city}\n"
    if context.gender:
        gender_str = "Мужчина" if context.gender == "male" else "Женщина" if context.gender == "female" else "Другое"
        summary += f"👤 Пол: {gender_str}\n"
    if context.age:
        summary += f"📅 Возраст: {context.age}\n"
    if context.weather_cache:
        summary += f"{context.weather_cache['icon']} Погода: {context.weather_cache['description']}, {context.weather_cache['temp']}°C\n"
    
    summary += f"\n🎯 Теперь я буду учитывать это в наших разговорах!\n\n"
    summary += "━━━━━━━━━━━━━━━━━━━━\n"
    summary += "<b>🧠 ЧТО ДАЛЬШЕ?</b>\n\n"
    summary += "Чтобы я мог помочь по-настоящему, нужно пройти тест (15 минут).\n"
    summary += "Он определит ваш психологический профиль по 4 векторам и глубинным паттернам.\n\n"
    summary += "━━━━━━━━━━━━━━━━━━━━\n"
    summary += "👇 <b>Начинаем?</b>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 НАЧАТЬ ТЕСТ", callback_data="show_stage_1_intro")],
        [InlineKeyboardButton(text="📖 ЧТО ДАЕТ ТЕСТ", callback_data="show_benefits")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="ask_pretest")]
    ])
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(summary, reply_markup=keyboard, parse_mode='HTML')
    else:
        # Отправляем новое сообщение
        await message_or_callback.message.answer(summary, reply_markup=keyboard, parse_mode='HTML')
    
    await state.clear()


# ============================================
# СТАРТ И НАВИГАЦИЯ
# ============================================

async def show_main_menu(message: Message, context: UserContext):
    """Показывает главное меню до теста"""
    
    await context.update_weather()
    
    day_context = context.get_day_context()
    
    welcome_text = f"{context.get_greeting(context.name)}\n\n"
    
    if context.weather_cache:
        weather = context.weather_cache
        welcome_text += f"{weather['icon']} {weather['description']}, {weather['temp']}°C\n"
    
    if day_context['is_weekend']:
        welcome_text += f"🏖 Сегодня выходной! Как настроение?\n\n"
    elif 9 <= day_context['hour'] < 18:
        welcome_text += f"💼 Рабочее время. Чем займёмся?\n\n"
    else:
        welcome_text += f"🏡 Личное время. Есть что обсудить?\n\n"
    
    welcome_text += f"👇 <b>Выберите действие:</b>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔴 ЖЕСТКИЙ", callback_data="mode_hard"),
            InlineKeyboardButton(text="🟡 СРЕДНИЙ", callback_data="mode_medium"),
            InlineKeyboardButton(text="🟢 МЯГКИЙ", callback_data="mode_soft")
        ],
        [InlineKeyboardButton(text="📖 ЧТО ДАЕТ ТЕСТ", callback_data="show_benefits")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="ask_pretest")]
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode='HTML')


async def show_main_menu_after_mode(message: Message, context: UserContext):
    """Показывает главное меню после выбора режима"""
    mode_config = COMMUNICATION_MODES.get(context.communication_mode, COMMUNICATION_MODES["coach"])
    
    await context.update_weather()
    day_context = context.get_day_context()
    
    text = f"{mode_config['emoji']} <b>РЕЖИМ {mode_config['display_name']}</b>\n\n"
    text += context.get_greeting(context.name) + "\n"
    text += f"📅 Сегодня {day_context['weekday']}, {day_context['day']} {day_context['month']}, {day_context['time_str']}\n"
    
    if context.weather_cache:
        weather = context.weather_cache
        text += f"{weather['icon']} {weather['description']}, {weather['temp']}°C\n\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += "<b>🧠 ЧЕМ ЗАЙМЁМСЯ?</b>\n\n"
    
    if context.communication_mode == "coach":
        text += "• Задать вопрос — я помогу найти ответ внутри себя\n"
    elif context.communication_mode == "friend":
        text += "• Расскажите, что у вас на душе — я рядом\n"
    elif context.communication_mode == "trainer":
        text += "• Поставьте задачу — я дам конкретные шаги\n"
    
    text += "• Выбрать тему — отношения, деньги, самоощущение\n"
    text += "• Послушать сказку — для глубокой работы\n"
    text += "• Посмотреть портрет — напомнить себе, кто вы"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 МЫСЛИ ПСИХОЛОГА", callback_data="ai_analysis")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions")],
        [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")],
        [
            InlineKeyboardButton(text="📖 СКАЗКА", callback_data="show_tale"),
            InlineKeyboardButton(text="⚙️ СМЕНИТЬ РЕЖИМ", callback_data="show_mode_selection")
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode='HTML')


async def show_benefits(callback: CallbackQuery):
    """Показывает преимущества теста"""
    text = (
        "<b>🔍 ЧТО ВЫ УЗНАЕТЕ О СЕБЕ:</b>\n\n"
        "<b>🧠 ЭТАП 1: КОНФИГУРАЦИЯ ВОСПРИЯТИЯ</b>\n"
        "Линза, через которую вы смотрите на мир.\n\n"
        "<b>🧠 ЭТАП 2: КОНФИГУРАЦИЯ МЫШЛЕНИЯ</b>\n"
        "Как вы обрабатываете информацию.\n\n"
        "<b>🧠 ЭТАП 3: КОНФИГУРАЦИЯ ПОВЕДЕНИЯ</b>\n"
        "Ваши автоматические реакции.\n\n"
        "<b>🧠 ЭТАП 4: ТОЧКА РОСТА</b>\n"
        "Где находится рычаг изменений.\n\n"
        "<b>🧠 ЭТАП 5: ГЛУБИННЫЕ ПАТТЕРНЫ</b>\n"
        "Тип привязанности, защитные механизмы, базовые убеждения.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>⚡ ПОСЛЕ ТЕСТА ВЫ ПОЛУЧИТЕ:</b>\n\n"
        "✅ Полный психологический портрет\n"
        "✅ Глубинный анализ подсознательных паттернов\n"
        "✅ Выбор стиля общения: 🔮 КОУЧ | 💚 ДРУГ | ⚡ ТРЕНЕР\n"
        "✅ Индивидуальный навигатор по целям\n"
        "✅ Напоминания и поддержка на пути\n\n"
        "<b>⏱ Всего 15 минут</b>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 НАЧАТЬ ТЕСТ", callback_data="show_stage_1_intro")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="back_to_intro")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')


async def back_to_intro(callback: CallbackQuery):
    """Возврат к начальному экрану"""
    user_id = callback.from_user.id
    user_name = user_names.get(user_id, callback.from_user.first_name or "друг")
    
    welcome_text = (
        f"👋 <b>Привет, {user_name}!</b>\n\n"
        f"👇 <b>Выберите, с какой интонацией будем общаться:</b>"
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
    
    await callback.message.edit_text(welcome_text, reply_markup=keyboard, parse_mode='HTML')


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
        f"{mode_info['emoji']} <b>Режим выбран:</b> {mode_info['display_name']}\n\n"
        f"{mode_info['responsibility']}\n\n"
        f"Теперь давайте познакомимся поближе.",
        parse_mode='HTML'
    )
    
    await asyncio.sleep(1)
    
    context = user_contexts[user_id]
    if not (context.city and context.gender and context.age):
        await start_context(callback, state)
    else:
        intro_text = (
            f"<b>🧠 ВИРТУАЛЬНЫЙ ПСИХОЛОГ</b>\n\n"
            f"<b>🔍 5 ЭТАПОВ ТЕСТИРОВАНИЯ:</b>\n\n"
            f"<b>ЭТАП 1:</b> Конфигурация восприятия\n"
            f"<b>ЭТАП 2:</b> Конфигурация мышления\n"
            f"<b>ЭТАП 3:</b> Конфигурация поведения\n"
            f"<b>ЭТАП 4:</b> Точка роста\n"
            f"<b>ЭТАП 5:</b> Глубинные паттерны\n\n"
            f"<b>⏱ Всего 15 минут</b>\n\n"
            f"👇 <b>Начинаем?</b>"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 НАЧАТЬ ТЕСТ", callback_data="show_stage_1_intro")]
        ])
        
        await callback.message.answer(intro_text, reply_markup=keyboard, parse_mode='HTML')


async def show_mode_selection(callback: CallbackQuery, state: FSMContext):
    """Показывает выбор режима общения"""
    user_id = callback.from_user.id
    data = await state.get_data()
    context = user_contexts.get(user_id)
    
    profile_data = data.get("profile_data", {})
    profile_code = profile_data.get('display_name', 'SA-5_INT')
    
    current_mode = context.communication_mode if context else "coach"
    mode_display = COMMUNICATION_MODES[current_mode]['display_name']
    
    text = f"<b>🧠 ВЫБЕРИТЕ СТИЛЬ ОБЩЕНИЯ</b>\n\n"
    text += f"<b>📊 Ваш профиль:</b> <code>{profile_code}</code>\n\n"
    text += f"Сейчас активен режим: {mode_display}\n\n"
    text += "Теперь, когда я знаю, кто вы,\n"
    text += "вы можете выбрать, <b>КАК</b> мы будем общаться:\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += "<b>🔮 КОУЧ</b>\n"
    text += "Партнёрский стиль: задаю вопросы, помогаю найти ответы внутри себя.\n\n"
    text += "<b>💚 ДРУГ</b>\n"
    text += "Тёплый, поддерживающий стиль. Как близкий человек.\n\n"
    text += "<b>⚡ ТРЕНЕР</b>\n"
    text += "Структурированный, требовательный стиль. Чёткие инструкции.\n\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += "👇 <b>Как вам комфортнее?</b>"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔮 КОУЧ", callback_data="set_mode_coach"),
            InlineKeyboardButton(text="💚 ДРУГ", callback_data="set_mode_friend"),
            InlineKeyboardButton(text="⚡ ТРЕНЕР", callback_data="set_mode_trainer")
        ],
        [InlineKeyboardButton(text="◀️ Вернуться к результатам", callback_data="back_to_results")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(TestStates.mode_selection)


async def set_mode_coach(callback: CallbackQuery, state: FSMContext):
    """Устанавливает режим КОУЧ"""
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    
    if context:
        context.communication_mode = "coach"
    
    await state.update_data(communication_mode="coach")
    
    await callback.answer("✅ Режим КОУЧ активирован")
    
    text = f"<b>🔮 РЕЖИМ КОУЧ АКТИВИРОВАН</b>\n\n"
    text += f"Отлично!\n\n"
    text += "Теперь я буду:\n"
    text += "• Задавать открытые вопросы\n"
    text += "• Помогать находить ответы внутри вас\n"
    text += "• Поддерживать, но не навязывать"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions")],
        [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(TestStates.results)


async def set_mode_friend(callback: CallbackQuery, state: FSMContext):
    """Устанавливает режим ДРУГ"""
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    
    if context:
        context.communication_mode = "friend"
    
    await state.update_data(communication_mode="friend")
    
    await callback.answer("✅ Режим ДРУГ активирован")
    
    text = f"<b>💚 РЕЖИМ ДРУГ АКТИВИРОВАН</b>\n\n"
    text += f"Приятно познакомиться!\n\n"
    text += "Теперь я буду:\n"
    text += "• Слушать и принимать без осуждения\n"
    text += "• Отражать ваши чувства\n"
    text += "• Быть рядом"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions")],
        [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(TestStates.results)


async def set_mode_trainer(callback: CallbackQuery, state: FSMContext):
    """Устанавливает режим ТРЕНЕР"""
    user_id = callback.from_user.id
    context = user_contexts.get(user_id)
    
    if context:
        context.communication_mode = "trainer"
    
    await state.update_data(communication_mode="trainer")
    
    await callback.answer("✅ Режим ТРЕНЕР активирован")
    
    text = f"<b>⚡ РЕЖИМ ТРЕНЕР АКТИВИРОВАН</b>\n\n"
    text += f"Привет!\n\n"
    text += "Теперь я буду:\n"
    text += "• Давать чёткие инструкции\n"
    text += "• Фокусироваться на действиях\n"
    text += "• Требовать результат"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions")],
        [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(TestStates.results)


async def ask_pretest(callback: CallbackQuery, state: FSMContext):
    """Вопрос до теста"""
    await callback.message.edit_text(
        "<b>❓ Задайте свой вопрос</b>\n\n"
        "Я отвечу, но без вашего профиля ответ будет общим.\n\n"
        "<i>Напишите вопрос текстом или голосом.</i>",
        parse_mode='HTML'
    )
    await state.set_state(TestStates.pretest_question)


async def handle_pretest_question(message: Message, state: FSMContext):
    """Обработка вопроса до теста"""
    user_id = message.from_user.id
    context_obj = user_contexts.get(user_id)
    
    await message.answer(
        f"Спасибо за вопрос. Чтобы ответить точнее, мне нужно знать ваш профиль. Пройдите тест — это займёт 15 минут."
    )
    await state.clear()


async def handle_ask_question(callback: CallbackQuery, state: FSMContext):
    """Обработка запроса на вопрос после теста"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="show_results")]
    ])
    await callback.message.edit_text(
        "<b>✏️ ЗАДАЙТЕ ВОПРОС</b>\n\n"
        "Напишите, что вас беспокоит. Я помню ваш профиль.",
        parse_mode='HTML',
        reply_markup=keyboard
    )
    await state.set_state(TestStates.awaiting_question)


async def handle_question_message(message: Message, state: FSMContext):
    """Обработка вопроса после теста"""
    user_id = message.from_user.id
    data = await state.get_data()
    
    if not is_test_completed(data):
        await message.answer(
            "Сначала нужно пройти тест. Используйте /start",
            parse_mode='HTML'
        )
        return
    
    thinking = await message.answer("<b>🤔 Думаю над ответом...</b>", parse_mode='HTML')
    
    response = await generate_response_with_full_context(user_id, message.text, data, user_contexts)
    
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
    
    # Очищаем ответ от Markdown
    clean_response = clean_markdown(response)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="smart_questions")],
        [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
        [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")]
    ])
    
    await message.answer(
        f"<b>🧠 Ответ</b>\n\n{clean_response}",
        parse_mode='HTML',
        reply_markup=keyboard
    )
    
    audio_data = await text_to_speech(response, mode)
    if audio_data:
        audio_file = BufferedInputFile(audio_data, filename="response.ogg")
        await message.answer_voice(
            audio_file,
            caption="<b>🎙 Голосовой ответ</b>",
            parse_mode='HTML'
        )
    
    await state.set_state(TestStates.results)


async def handle_voice_message(message: Message, state: FSMContext):
    """Обработка голосового сообщения"""
    user_id = message.from_user.id
    data = await state.get_data()
    
    if not is_test_completed(data):
        await message.answer(
            "<b>🎙 Голосовые сообщения доступны только после завершения теста</b>",
            parse_mode='HTML'
        )
        return
    
    status_msg = await message.answer("<b>🎤 Распознаю речь...</b>", parse_mode='HTML')
    
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
                "❌ <b>Не удалось распознать речь</b>\n\n"
                "Попробуйте еще раз или напишите текстом.",
                parse_mode='HTML'
            )
            return
        
        response = await generate_response_with_full_context(user_id, recognized_text, data, user_contexts)
        
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
        
        # Очищаем ответ от Markdown
        clean_response = clean_markdown(response)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="smart_questions")],
            [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
            [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")]
        ])
        
        await status_msg.edit_text(
            f"<b>📝 Вы сказали:</b>\n<i>{recognized_text}</i>\n\n"
            f"<b>Ответ:</b>\n{clean_response}",
            parse_mode='HTML',
            reply_markup=keyboard
        )
        
        audio_data = await text_to_speech(response, mode)
        if audio_data:
            audio_file = BufferedInputFile(audio_data, filename="response.ogg")
            await message.answer_voice(
                audio_file,
                caption="<b>🎙 Голосовой ответ</b>",
                parse_mode='HTML'
            )
    
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {e}")
        await status_msg.edit_text(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Попробуйте еще раз или напишите текстом.",
            parse_mode='HTML'
        )


async def handle_unknown_message(message: Message):
    """Обработка неизвестных сообщений"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 К ПОРТРЕТУ", callback_data="show_results")],
        [InlineKeyboardButton(text="🎯 ЧЕМ ПОМОЧЬ", callback_data="show_help")],
        [InlineKeyboardButton(text="❓ ЗАДАТЬ ВОПРОС", callback_data="smart_questions")]
    ])
    await message.answer(
        "Используйте кнопки для навигации:",
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
    
    await message.answer("Используйте /test_yandex для теста голосов")


# ============================================
# CALLBACK ХЕНДЛЕР
# ============================================

async def callback_handler(callback: CallbackQuery, state: FSMContext):
    """Основной обработчик callback'ов"""
    
    # ВАЖНО: сразу отвечаем, чтобы избежать таймаута
    await callback.answer()
    
    data = callback.data
    
    try:
        # Новые экраны
        if data == "why_details":
            await show_why_details(callback, state)
            return
        
        # Навигация по точкам
        elif data == "show_destinations":
            await show_destinations(callback, state)
        
        elif data.startswith("dest_"):
            await show_destination_route(callback, state)
        
        elif data == "custom_destination":
            await callback.message.edit_text(
                "<b>✏️ СФОРМУЛИРУЙТЕ ЦЕЛЬ</b>\n\n"
                "Напишите своим текстом, чего хотите достичь.\n"
                "Я помогу построить маршрут.",
                parse_mode='HTML'
            )
            await state.set_state(TestStates.awaiting_question)
            await state.update_data(awaiting_custom_destination=True)
        
        elif data == "route_step_done":
            await route_step_done(callback, state)
        
        elif data == "reminder_snooze":
            await callback.message.edit_text(
                "<b>⏭️ Напоминание отложено на 24 часа</b>",
                parse_mode='HTML'
            )
            await reminder_manager.schedule_reminder(
                callback.from_user.id,
                'checkin',
                24*60
            )
        
        # ИСПРАВЛЕНО: обработка мысли психолога
        elif data == "psychologist_thought":
            await show_ai_analysis(callback, state)
        
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
        elif data == "show_stage_1_intro":
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
        
        # Подтверждение профиля
        elif data == "profile_confirm":
            await profile_confirm(callback, state)
        elif data == "profile_doubt":
            await profile_doubt(callback, state)
        elif data == "profile_reject":
            await profile_reject(callback, state)
        
        # Расхождения
        elif data.startswith("discrepancy_"):
            disc = data.replace("discrepancy_", "")
            await handle_discrepancy(callback, state, disc)
        elif data == "clarify_next":
            await clarify_next(callback, state)
        elif data.startswith("clarify_answer_"):
            await handle_clarifying_answer(callback, state)
        
        # Результаты и конфайнмент
        elif data == "show_results":
            await show_final_profile(callback, state)
        elif data == "ai_analysis":
            await show_ai_analysis(callback, state)
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
        
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            logger.info("Ignored 'message not modified' error")
        elif "can't parse entities" in str(e).lower() or "parse entities" in str(e).lower():
            logger.warning(f"HTML parsing error, retrying without HTML: {e}")
            try:
                if callback.message and callback.message.text:
                    # Удаляем все HTML-теги
                    clean_text = re.sub(r'<[^>]+>', '', callback.message.text)
                    await callback.message.edit_text(clean_text, reply_markup=callback.message.reply_markup)
                else:
                    await callback.answer("❌ Ошибка форматирования")
            except Exception as e2:
                logger.error(f"Failed to recover from HTML error: {e2}")
                await callback.answer("❌ Произошла ошибка")
        else:
            logger.error(f"TelegramBadRequest: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in callback_handler: {e}")


# ============================================
# КОМАНДЫ АДМИНИСТРАТОРОВ
# ============================================

async def cmd_stats(message: Message):
    """Команда /stats"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещен")
        return
    
    await message.answer(stats.get_stats_text(), parse_mode='HTML')


async def cmd_apistatus(message: Message):
    """Команда /apistatus"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещен")
        return
    
    from config import DEEPSEEK_API_KEY, DEEPGRAM_API_KEY, YANDEX_API_KEY, OPENWEATHER_API_KEY
    
    deepseek_status = "✅ работает" if DEEPSEEK_API_KEY else "❌ не настроен"
    deepgram_status = "✅ работает" if DEEPGRAM_API_KEY else "❌ не настроен"
    yandex_status = "✅ работает" if YANDEX_API_KEY else "❌ не настроен"
    weather_status = "✅ работает" if OPENWEATHER_API_KEY else "❌ не настроен"
    
    text = f"<b>📊 Статус API:</b>\n\n"
    text += f"• DeepSeek: {deepseek_status}\n"
    text += f"• Deepgram: {deepgram_status}\n"
    text += f"• Yandex TTS: {yandex_status}\n"
    text += f"• OpenWeather: {weather_status}\n\n"
    
    if OPENWEATHER_API_KEY:
        text += f"🌍 Погода будет автоматически подгружаться для пользователей\n"
    
    if YANDEX_API_KEY:
        text += f"🎙 Голоса: Филипп (коуч/тренер), Эрмил (друг)\n"
    
    await message.answer(text, parse_mode='HTML')


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
                parse_mode='HTML'
            )
            results.append(f"✅ {COMMUNICATION_MODES[mode]['display_name']}")
        else:
            results.append(f"❌ {COMMUNICATION_MODES[mode]['display_name']}")
        await asyncio.sleep(0.5)
    
    await status.delete()
    await message.answer("<b>📊 Результаты:</b>\n" + "\n".join(results), parse_mode='HTML')


async def cmd_test_weather(message: Message):
    """Команда /test_weather - тест погоды"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Только для администраторов")
        return
    
    from config import OPENWEATHER_API_KEY
    
    if not OPENWEATHER_API_KEY:
        await message.answer("❌ OPENWEATHER_API_KEY не настроен")
        return
    
    test_city = "Москва"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={test_city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
    
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    temp = data['main']['temp']
                    feels_like = data['main']['feels_like']
                    desc = data['weather'][0]['description']
                    humidity = data['main']['humidity']
                    wind = data['wind']['speed']
                    
                    text = f"<b>✅ Погода работает!</b>\n\n"
                    text += f"📍 Город: {test_city}\n"
                    text += f"🌡 Температура: {temp}°C (ощущается как {feels_like}°C)\n"
                    text += f"☁️ Описание: {desc}\n"
                    text += f"💧 Влажность: {humidity}%\n"
                    text += f"💨 Ветер: {wind} м/с"
                    
                    await message.answer(text, parse_mode='HTML')
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
        # Очищаем текст сказки от Markdown
        clean_tale_text = clean_markdown(tale['text'])
        await message.answer(
            f"<b>📖 {tale['title']}</b>\n\n{clean_tale_text[:4000]}",
            parse_mode='HTML'
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
    
    await message.answer("<b>🔄 Давайте обновим ваш контекст</b>", parse_mode='HTML')
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
    from config import DEEPSEEK_API_KEY, OPENWEATHER_API_KEY
    
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
    
    reminder_manager.set_bot(bot)
    
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
    
    from config import DEEPSEEK_API_KEY
    if DEEPSEEK_API_KEY:
        logger.info("✅ DeepSeek API ключ найден")
        asyncio.create_task(check_api_on_startup())
    else:
        logger.warning("❌ DeepSeek API ключ не найден")
    
    logger.info("Бот запущен...")
    print("\n" + "="*80)
    print("🚀 ВИРТУАЛЬНЫЙ ПСИХОЛОГ - МАТРИЦА ПОВЕДЕНИЙ 4×6 v9.1")
    print("="*80)
    print(f"👤 Ваш Telegram ID: {ADMIN_IDS[0] if ADMIN_IDS else 'не указан'}")
    print("📊 Команды: /stats, /apistatus, /test_yandex, /test_voices, /test_weather, /tale, /context")
    print("🎙 Распознавание: " + ("✅ Deepgram" if DEEPGRAM_API_KEY else "❌ нет"))
    print("🎙 Синтез речи: " + ("✅ Yandex" if YANDEX_API_KEY else "❌ нет"))
    print("🌍 Погода: " + ("✅ OpenWeather" if OPENWEATHER_API_KEY else "❌ нет"))
    print("🔄 Конфайнмент-моделирование: ✅")
    print("🧠 5 этапов тестирования: ✅")
    print("🧠 Динамическая генерация профиля: ✅")
    print("🎭 Режимы: 🔮 КОУЧ | 💚 ДРУГ | ⚡ ТРЕНЕР")
    print("🧭 Навигатор по целям: ✅")
    print("📅 Напоминания: ✅")
    print("="*80 + "\n")
    
    await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    os.makedirs("stats", exist_ok=True)
    asyncio.run(main())
