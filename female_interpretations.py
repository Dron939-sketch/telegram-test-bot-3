"""
Женские интерпретации для системы "Тайный шёпот" v4.0
Временно использует мужские с заменой окончаний
"""

import logging
from male_interpretations import NARRATIVE_NAMES, get_male_interpretation

logger = logging.getLogger(__name__)

def get_female_interpretation(narrative, level, program, second_narrative=None, third_narrative=None):
    """
    Временная функция - использует мужские интерпретации
    """
    strategy = get_male_interpretation(
        narrative=narrative,
        level=level,
        program=program,
        second_narrative=second_narrative,
        third_narrative=third_narrative
    )
    
    if strategy:
        # Копируем и заменяем окончания (грубо, но для начала сойдёт)
        female_strategy = strategy.copy()
        female_strategy['роль'] = female_strategy['роль'].replace("ий", "ая").replace("ой", "ая").replace("ик", "ица")
        return female_strategy
    
    return None

__all__ = ['get_female_interpretation', 'NARRATIVE_NAMES']
