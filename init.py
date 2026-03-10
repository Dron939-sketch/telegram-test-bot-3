# modes/__init__.py
from typing import Dict, Any, Optional
from .coach import CoachMode
from .psychologist import PsychologistMode
from .trainer import TrainerMode

_mode_classes = {
    "coach": CoachMode,
    "psychologist": PsychologistMode,  # бывший friend
    "trainer": TrainerMode
}

def get_mode(mode_name: str, user_id: int, user_data: Dict[str, Any], context=None):
    """
    Фабрика для создания экземпляра режима
    """
    mode_class = _mode_classes.get(mode_name)
    if not mode_class:
        mode_class = CoachMode  # по умолчанию
    
    return mode_class(user_id, user_data, context)

def get_available_modes() -> Dict[str, str]:
    """
    Возвращает список доступных режимов с описаниями
    """
    return {
        "coach": "🔮 КОУЧ - помогаю найти ответы внутри себя через вопросы",
        "psychologist": "🧠 ПСИХОЛОГ - работаю с глубинными паттернами и гипнозом",
        "trainer": "⚡ ТРЕНЕР - даю чёткие инструкции и требую результат"
    }

def get_mode_description(mode_name: str) -> str:
    """
    Возвращает подробное описание режима
    """
    descriptions = {
        "coach": """
🔮 *Режим КОУЧ*

*Как работает:* Задаёт открытые вопросы, помогает найти ответы внутри себя.
*Когда выбирать:* Когда хотите разобраться в себе, но не нуждаетесь в советах.
*Что получите:* Осознание своих паттернов, новые перспективы.
""",
        "psychologist": """
🧠 *Режим ПСИХОЛОГ*

*Как работает:* Анализирует глубинные паттерны, работает с защитами, использует гипнотические техники.
*Когда выбирать:* Когда есть повторяющиеся проблемы, травмы, сложные эмоции.
*Что получите:* Понимание причин, доступ к бессознательному, терапевтические метафоры.
""",
        "trainer": """
⚡ *Режим ТРЕНЕР*

*Как работает:* Даёт конкретные задания, ставит дедлайны, мотивирует через вызов.
*Когда выбирать:* Когда нужен пинок, чёткий план и контроль.
*Что получите:* Конкретные действия, прогресс, результат.
"""
    }
    return descriptions.get(mode_name, descriptions["coach"])
