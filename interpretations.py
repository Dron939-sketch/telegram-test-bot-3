#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔮 ТАЙНЫЙ ШЁПОТ: Объединённые интерпретации v1.0
336 стратегий (168 мужских + 168 женских)
Формат: детство / идентичность / окружение (от 2-го лица)
"""

import logging
from male_interpretations import MALE_STRATEGIES
from female_interpretations import FEMALE_STRATEGIES

# ==================== НАЗВАНИЯ НАРРАТИВОВ ====================

NARRATIVE_NAMES = {
    "СБ": "СИЛЫ",
    "ТФ": "ТРУДА", 
    "УБ": "ЗНАНИЙ",
    "ЧВ": "ВНИМАНИЯ"
}

logger = logging.getLogger(__name__)

# Проверка загрузки
male_count = len(MALE_STRATEGIES)
female_count = len(FEMALE_STRATEGIES)
total_count = male_count + female_count

logger.info(f"✅ Загружено мужских стратегий: {male_count}")
logger.info(f"✅ Загружено женских стратегий: {female_count}")
logger.info(f"✅ ВСЕГО стратегий: {total_count}")

# ==================== ФУНКЦИИ ПОЛУЧЕНИЯ ИНТЕРПРЕТАЦИЙ ====================

def get_interpretation(gender, narrative, level, age, program, second_narrative=None, third_narrative=None):
    """
    Универсальная функция для получения интерпретации
    
    Параметры:
    - gender: "М" или "Ж"
    - narrative: основной нарратив (СБ, ТФ, УБ, ЧВ)
    - level: уровень 1-6
    - age: возраст (не используется в текущей версии)
    - program: древняя программа (F1-F6)
    - second_narrative: второй нарратив (если есть)
    - third_narrative: третий нарратив (если есть)
    
    Возвращает:
    - словарь с ключами: детство, идентичность, окружение
    """
    
    # Формируем ключ
    if second_narrative and third_narrative:
        # Тройной нарратив
        key = f"{narrative}-{second_narrative}-{third_narrative}_{level}_{program}"
    elif second_narrative:
        # Двойной нарратив
        key = f"{narrative}-{second_narrative}_{level}_{program}"
    else:
        # Чистый нарратив
        key = f"{narrative}_{level}_{program}"
    
    # Выбираем нужный словарь по полу
    if gender == "Ж":
        strategies = FEMALE_STRATEGIES
        gender_text = "женская"
    else:
        strategies = MALE_STRATEGIES
        gender_text = "мужская"
    
    # Ищем стратегию
    strategy = strategies.get(key)
    
    if strategy:
        logger.info(f"✅ Найдена {gender_text} стратегия: {key}")
        return strategy
    else:
        logger.warning(f"⚠️ {gender_text} стратегия не найдена: {key}")
        # Заглушка на случай отсутствия
        return {
            "детство": f"Твоя уникальность не вписывается в шаблоны. Ты сама создаёшь свой путь." if gender == "Ж" else "Твоя уникальность не вписывается в шаблоны. Ты сам создаёшь свой путь.",
            "идентичность": f"Ты — та, кто ищет себя за пределами готовых решений." if gender == "Ж" else "Ты — тот, кто ищет себя за пределами готовых решений.",
            "окружение": "Твой мир — там, где ты сама." if gender == "Ж" else "Твой мир — там, где ты сам."
        }

def get_male_interpretation(narrative, level, program, second_narrative=None, third_narrative=None):
    """Для обратной совместимости"""
    return get_interpretation(
        gender="М",
        narrative=narrative,
        level=level,
        age=0,
        program=program,
        second_narrative=second_narrative,
        third_narrative=third_narrative
    )

def get_female_interpretation(narrative, level, program, second_narrative=None, third_narrative=None):
    """Для удобного вызова женских интерпретаций"""
    return get_interpretation(
        gender="Ж",
        narrative=narrative,
        level=level,
        age=0,
        program=program,
        second_narrative=second_narrative,
        third_narrative=third_narrative
    )

# ==================== ЭКСПОРТ ====================

__all__ = [
    'NARRATIVE_NAMES', 
    'get_interpretation', 
    'get_male_interpretation', 
    'get_female_interpretation',
    'MALE_STRATEGIES', 
    'FEMALE_STRATEGIES'
]
