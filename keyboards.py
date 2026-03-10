"""
Вспомогательные функции
"""
import re
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


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


def is_test_completed(user_data: dict) -> bool:
    """Проверяет, завершен ли тест"""
    required_fields = ["perception_type", "thinking_level", "behavioral_levels", "dilts_counts", "deep_patterns"]
    for field in required_fields:
        if field not in user_data:
            return False
    return True


def safe_get_profile_info(vector: str, level_num: int, key: str, default: str = "Информация уточняется") -> str:
    """Безопасно получает информацию из профиля"""
    try:
        profile = LEVEL_PROFILES.get(vector, {}).get(level_num, {})
        if isinstance(profile, dict):
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
            if key == 'quote':
                return str(profile)
            elif key == 'pain_origin':
                return "Из вашего опыта"
            elif key == 'pain_costs':
                return ["Энергией", "Временем", "Возможностями"]
    except Exception as e:
        logger.error(f"Ошибка при получении информации из профиля: {e}")
    
    return default


def convert_to_simple_language(scores: dict, perception_type: str, thinking_level: int, deep_patterns: dict = None) -> dict:
    """Конвертирует технические данные в простые описания"""
    
    result = {}
    
    if perception_type in ["СОЦИАЛЬНО-ОРИЕНТИРОВАННЫЙ", "СТАТУСНО-ОРИЕНТИРОВАННЫЙ"]:
        result['attention'] = "ВЫ ОРИЕНТИРУЕТЕСЬ НА ЛЮДЕЙ"
        result['attention_desc'] = "Для вас важно, что думают другие, вы чутко считываете настроение и ожидания окружающих."
    else:
        result['attention'] = "ВЫ ОРИЕНТИРУЕТЕСЬ НА СЕБЯ"
        result['attention_desc'] = "Для вас важнее ваши внутренние ощущения и чувства, чем мнение других."
    
    if thinking_level <= 3:
        result['thinking'] = "ВЫ МЫСЛИТЕ КОНКРЕТНО"
        result['thinking_desc'] = "Вы хорошо видите отдельные ситуации, но не всегда замечаете общие закономерности."
    elif thinking_level <= 6:
        result['thinking'] = "ВЫ МЫСЛИТЕ СИСТЕМНО"
        result['thinking_desc'] = "Вы замечаете закономерности, но не всегда видите, к чему они приведут в будущем."
    else:
        result['thinking'] = "ВЫ МЫСЛИТЕ ГЛУБОКО"
        result['thinking_desc'] = "Вы видите общие законы и можете предсказывать развитие ситуаций."
    
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
    
    growth_map = {
        "ENVIRONMENT": "Посмотрите вокруг — может, дело в обстоятельствах?",
        "BEHAVIOR": "Попробуйте делать хоть что-то по-другому — маленькие шаги многое меняют.",
        "CAPABILITIES": "Развивайте новые навыки — они откроют новые возможности.",
        "VALUES": "Поймите, что для вас действительно важно — это изменит всё.",
        "IDENTITY": "Ответьте себе на вопрос «кто я?» — в этом ключ к изменениям."
    }
    result['growth_point'] = growth_map.get(perception_type, "Начните с малого — и увидите, куда приведёт.")
    
    if deep_patterns:
        result['deep_patterns'] = get_deep_patterns_description(deep_patterns)
    
    return result


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


def get_human_readable_profile(scores: dict, model=None, perception_type="не определен", thinking_level=5, dominant_dilts="BEHAVIOR") -> str:
    """Возвращает портрет пользователя понятным языком"""
    from formatters import bold
    
    lines = []
    
    if scores:
        min_vector = min(scores.items(), key=lambda x: level(x[1]))
        vector, score = min_vector
        lvl = level(score)
        
        quote = safe_get_profile_info(vector, lvl, 'quote', 'Пока не определено')
        pain_origin = safe_get_profile_info(vector, lvl, 'pain_origin', 'Из вашего опыта')
        costs = safe_get_profile_info(vector, lvl, 'pain_costs', ["Энергией", "Временем", "Возможностями"])
    else:
        vector = "СБ"
        quote = "Пока не определено"
        pain_origin = "Из вашего опыта"
        costs = ["Энергией", "Временем", "Возможностями"]
    
    lines.append(f"🧠 {bold('ВАШ ПСИХОЛОГИЧЕСКИЙ ПОРТРЕТ')}")
    lines.append("")
    lines.append(f"🔍 {bold('Тип восприятия:')} {perception_type}")
    lines.append(f"🧠 {bold('Уровень мышления:')} {thinking_level}/9")
    lines.append("")
    lines.append(f"🔑 {bold('КЛЮЧЕВАЯ ХАРАКТЕРИСТИКА')}")
    lines.append(quote)
    lines.append("")
    lines.append(f"💪 {bold('СИЛЬНЫЕ СТОРОНЫ')}")
    lines.append("• Высокоразвитые социальные навыки")
    lines.append("• Системное мышление")
    lines.append("• Устойчивость к стрессу")
    lines.append("• Прагматизм")
    lines.append("")
    lines.append(f"🎯 {bold('ЗОНЫ РОСТА')}")
    lines.append(f"• {pain_origin}")
    for cost in costs[:3]:
        lines.append(f"• {cost}")
    lines.append("")
    lines.append(f"⚠️ {bold('ГЛАВНАЯ ЛОВУШКА')}")
    dilts_desc = DILTS_LEVELS.get(dominant_dilts, "Поведение")
    lines.append(f"• {dilts_desc}")
    
    return "\n".join(lines)
