"""
Модуль проверки реальности целей
Версия 1.0
"""

import logging
import re
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================
# ФУНКЦИИ ФОРМАТИРОВАНИЯ
# ============================================

def bold(text: str) -> str:
    """Жирный текст (HTML)"""
    return f"<b>{text}</b>"


# ============================================
# ПАРСИНГ ОТВЕТОВ ПОЛЬЗОВАТЕЛЯ
# ============================================

def parse_life_context_answers(text: str) -> Dict[str, Any]:
    """
    Парсит ответы на вопросы о жизненном контексте
    
    Args:
        text: текст ответа пользователя (обычно 10 строк)
    
    Returns:
        Dict с полями:
        - family_status: семейное положение
        - has_children: есть ли дети (bool)
        - children_info: информация о детях (строка)
        - work_schedule: график работы
        - job_title: должность
        - commute_time: время на дорогу
        - housing_type: тип жилья
        - has_private_space: есть ли отдельное пространство (bool)
        - has_car: есть ли машина (bool)
        - support_people: кто поддерживает
        - resistance_people: кто мешает
        - energy_level: уровень энергии (1-10)
    """
    lines = text.strip().split('\n')
    answers = []
    
    # Очищаем каждую строку от нумерации
    for line in lines:
        # Убираем цифры, эмодзи-цифры и лишние пробелы в начале
        clean = re.sub(r'^[\d️⃣🔟]*\s*', '', line.strip())
        if clean:  # добавляем только непустые строки
            answers.append(clean)
    
    result = {
        'family_status': 'не указано',
        'has_children': False,
        'children_info': '',
        'work_schedule': '',
        'job_title': '',
        'commute_time': '',
        'housing_type': '',
        'has_private_space': False,
        'has_car': False,
        'support_people': '',
        'resistance_people': '',
        'energy_level': 5  # значение по умолчанию
    }
    
    # Заполняем результат, если есть достаточно ответов
    if len(answers) >= 10:
        result['family_status'] = answers[0]
        result['children_info'] = answers[1]
        result['has_children'] = any(word in answers[1].lower() 
                                     for word in ['да', 'есть', 'двое', 'трое', 'ребенок', 'дочь', 'сын'])
        
        result['work_schedule'] = answers[2]
        result['job_title'] = answers[2]  # может быть уточнено позже
        
        result['commute_time'] = answers[3]
        
        result['housing_type'] = answers[4]
        
        result['has_private_space'] = any(word in answers[5].lower() 
                                          for word in ['да', 'есть', 'отдельная', 'своя'])
        
        result['has_car'] = any(word in answers[6].lower() 
                                for word in ['да', 'есть', 'машина'])
        
        result['support_people'] = answers[7] if len(answers) > 7 else ''
        result['resistance_people'] = answers[8] if len(answers) > 8 else ''
        
        # Парсим уровень энергии
        try:
            # Ищем число в строке
            energy_match = re.search(r'(\d+)', answers[9])
            if energy_match:
                result['energy_level'] = int(energy_match.group(1))
                # Ограничиваем диапазоном 1-10
                result['energy_level'] = max(1, min(10, result['energy_level']))
        except (ValueError, IndexError):
            result['energy_level'] = 5
    
    elif len(answers) >= 5:
        # Если ответов меньше, пытаемся извлечь хоть что-то
        for i, answer in enumerate(answers):
            if 'энерги' in answer.lower() or 'оцени' in answer.lower():
                try:
                    energy_match = re.search(r'(\d+)', answer)
                    if energy_match:
                        result['energy_level'] = int(energy_match.group(1))
                        result['energy_level'] = max(1, min(10, result['energy_level']))
                except:
                    pass
            
            if 'комнат' in answer.lower() or 'пространств' in answer.lower():
                result['has_private_space'] = any(word in answer.lower() 
                                                  for word in ['да', 'есть', 'отдельная'])
            
            if 'машин' in answer.lower():
                result['has_car'] = any(word in answer.lower() 
                                        for word in ['да', 'есть'])
    
    return result


def parse_goal_context_answers(text: str) -> Dict[str, Any]:
    """
    Парсит ответы на вопросы о целевом контексте
    
    Args:
        text: текст ответа пользователя
    
    Returns:
        Dict с полями:
        - time_per_week: часов в неделю
        - budget: бюджет в рублях
        - raw_answers: сырые ответы
        - has_equipment: есть ли оборудование
        - equipment_needed: нужное оборудование
        - timeline_preference: предпочтения по срокам
    """
    result = {
        'time_per_week': 5,  # значение по умолчанию
        'budget': 0,
        'has_equipment': False,
        'equipment_needed': '',
        'timeline_preference': 'medium',  # fast/medium/slow
        'raw_answers': text
    }
    
    # Ищем время (часы в неделю)
    time_patterns = [
        r'(\d+)\s*часов',
        r'(\d+)\s*ч',
        r'(\d+)\s*час',
        r'(\d+)\s*в неделю'
    ]
    
    for pattern in time_patterns:
        time_match = re.search(pattern, text, re.IGNORECASE)
        if time_match:
            try:
                hours = int(time_match.group(1))
                # Реалистичные границы: 1-168 часов в неделю
                result['time_per_week'] = max(1, min(168, hours))
                break
            except:
                pass
    
    # Если не нашли по паттернам, ищем любое число, похожее на часы
    if result['time_per_week'] == 5:  # если не нашли
        numbers = re.findall(r'(\d+)', text)
        for num in numbers:
            try:
                val = int(num)
                if 1 <= val <= 168:
                    result['time_per_week'] = val
                    break
            except:
                pass
    
    # Ищем бюджет
    budget_patterns = [
        r'(\d+)\s*тыс',
        r'(\d+)\s*000',
        r'(\d+)\s*руб',
        r'(\d+)\s*₽'
    ]
    
    for pattern in budget_patterns:
        budget_match = re.search(pattern, text, re.IGNORECASE)
        if budget_match:
            try:
                amount = int(budget_match.group(1))
                if 'тыс' in pattern:
                    result['budget'] = amount * 1000
                else:
                    result['budget'] = amount
                break
            except:
                pass
    
    # Ищем упоминания оборудования
    equipment_keywords = ['нужн', 'оборуд', 'инструм', 'компьютер', 'ноутбук', 'программ']
    for keyword in equipment_keywords:
        if keyword in text.lower():
            result['has_equipment'] = True
            # Пробуем извлечь что именно нужно
            sentences = text.split('.')
            for sent in sentences:
                if keyword in sent.lower():
                    result['equipment_needed'] = sent.strip()
                    break
            break
    
    # Определяем предпочтения по срокам
    if any(word in text.lower() for word in ['быстр', 'срочн', 'скоре']):
        result['timeline_preference'] = 'fast'
    elif any(word in text.lower() for word in ['нетороп', 'постепен', 'долгосрочн']):
        result['timeline_preference'] = 'slow'
    else:
        result['timeline_preference'] = 'medium'
    
    return result


# ============================================
# ТЕОРЕТИЧЕСКИЕ ПУТИ К ЦЕЛЯМ
# ============================================

def get_theoretical_path(goal_id: str, mode: str) -> Dict[str, Any]:
    """
    Возвращает теоретический путь к цели
    
    Args:
        goal_id: идентификатор цели
        mode: режим (coach/psychologist/trainer)
    
    Returns:
        Dict с полями:
        - time_total: общее время в часах
        - time_per_week: часов в неделю
        - duration_weeks: длительность в неделях
        - energy_required: требуемый уровень энергии (1-10)
        - space_required: требуется ли отдельное пространство
        - budget: бюджет в рублях (0 если бесплатно)
        - support_required: требуется ли поддержка
        - steps: список шагов с описанием
        - formatted_text: отформатированный текст для вывода
    """
    paths = {
        # ДЕНЬГИ
        "income_growth": {
            "coach": {
                "time_total": 340,
                "time_per_week": 13,
                "duration_weeks": 26,
                "energy_required": 7,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущей ситуации и ресурсов",
                    "Постановка конкретных финансовых целей",
                    "Поиск точек роста и возможностей",
                    "Создание плана действий",
                    "Еженедельные сессии для сверки и корректировки"
                ]
            },
            "psychologist": {
                "time_total": 200,
                "time_per_week": 8,
                "duration_weeks": 26,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование денежных убеждений и сценариев",
                    "Проработка страхов и блоков",
                    "Анализ семейных денежных паттернов",
                    "Работа с чувством собственной ценности",
                    "Интеграция нового отношения к деньгам"
                ]
            },
            "trainer": {
                "time_total": 400,
                "time_per_week": 15,
                "duration_weeks": 26,
                "energy_required": 8,
                "space_required": True,
                "budget": 0,
                "support_required": True,
                "steps": [
                    "Освоение конкретного навыка (обучение 120ч)",
                    "Практика и отработка (80ч)",
                    "Создание продукта/услуги (60ч)",
                    "Маркетинг и поиск клиентов (80ч)",
                    "Анализ и масштабирование (60ч)"
                ]
            }
        },
        
        "money_blocks": {
            "coach": {
                "time_total": 200,
                "time_per_week": 8,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Выявление основных ограничений",
                    "Поиск альтернативных путей",
                    "Развитие новых финансовых привычек",
                    "Планирование бюджета",
                    "Регулярная ревизия прогресса"
                ]
            },
            "psychologist": {
                "time_total": 250,
                "time_per_week": 10,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Поиск корней денежных блоков",
                    "Проработка семейных сценариев",
                    "Работа с чувством вины и стыда",
                    "Формирование новой денежной идентичности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Ведение финансового дневника",
                    "Освоение базовых финансовых инструментов",
                    "Создание финансовой подушки",
                    "Автоматизация накоплений",
                    "Анализ расходов"
                ]
            }
        },
        
        # ОТНОШЕНИЯ
        "relations": {
            "coach": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущей ситуации и желаний",
                    "Прояснение критериев и ценностей",
                    "Поиск мест знакомств",
                    "Развитие навыков общения",
                    "Анализ опыта и корректировка"
                ]
            },
            "psychologist": {
                "time_total": 180,
                "time_per_week": 7,
                "duration_weeks": 26,
                "energy_required": 7,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование типа привязанности",
                    "Проработка прошлых травм",
                    "Анализ повторяющихся сценариев",
                    "Работа со страхом близости",
                    "Формирование здоровых моделей"
                ]
            },
            "trainer": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 5000,
                "support_required": False,
                "steps": [
                    "Навыки знакомства и самопрезентации",
                    "Развитие эмпатии и активного слушания",
                    "Навыки ведения свиданий",
                    "Коммуникация в отношениях",
                    "Разрешение конфликтов"
                ]
            }
        },
        
        # ТРЕВОГА
        "anxiety_reduce": {
            "coach": {
                "time_total": 80,
                "time_per_week": 3,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Определение триггеров тревоги",
                    "Поиск ресурсных состояний",
                    "Постановка маленьких целей",
                    "Отслеживание прогресса",
                    "Закрепление новых состояний"
                ]
            },
            "psychologist": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Поиск корневых причин тревоги",
                    "Проработка детских травм",
                    "Работа с защитными механизмами",
                    "Интеграция теневых частей",
                    "Формирование базового чувства безопасности"
                ]
            },
            "trainer": {
                "time_total": 60,
                "time_per_week": 2.5,
                "duration_weeks": 24,
                "energy_required": 4,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Ежедневные дыхательные практики (15 мин)",
                    "Техники заземления",
                    "Когнитивные упражнения",
                    "Телесные практики",
                    "Ведение дневника состояний"
                ]
            }
        },
        
        # ЭНЕРГИЯ
        "energy_boost": {
            "coach": {
                "time_total": 60,
                "time_per_week": 2.5,
                "duration_weeks": 24,
                "energy_required": 4,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ текущего образа жизни",
                    "Определение точек утечки энергии",
                    "Поиск ресурсных активностей",
                    "Планирование изменений",
                    "Отслеживание динамики"
                ]
            },
            "psychologist": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование психосоматических связей",
                    "Проработка подавленных эмоций",
                    "Работа с внутренними конфликтами",
                    "Выявление вторичных выгод упадка сил",
                    "Интеграция новой энергии"
                ]
            },
            "trainer": {
                "time_total": 50,
                "time_per_week": 2,
                "duration_weeks": 24,
                "energy_required": 3,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Режим сна (настройка)",
                    "Коррекция питания",
                    "Физическая активность 3 раза в неделю",
                    "Энергетические практики 15 мин в день",
                    "Отслеживание показателей"
                ]
            }
        },
        
        # САМОПОЗНАНИЕ
        "purpose": {
            "coach": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование ценностей и интересов",
                    "Анализ прошлого опыта",
                    "Поиск точек вдохновения",
                    "Формулировка гипотез",
                    "Тестирование и корректировка"
                ]
            },
            "psychologist": {
                "time_total": 200,
                "time_per_week": 8,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Исследование детских мечтаний",
                    "Анализ запретов и долженствований",
                    "Работа с самооценкой",
                    "Поиск уникальности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Тестирование разных активностей",
                    "Ведение дневника",
                    "Обучение новым навыкам",
                    "Нетворкинг",
                    "Создание проекта"
                ]
            }
        },
        
        # ДОПОЛНИТЕЛЬНЫЕ ЦЕЛИ
        "boundaries": {
            "coach": {
                "time_total": 80,
                "time_per_week": 3,
                "duration_weeks": 26,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Осознание своих границ",
                    "Определение личных прав",
                    "Практика маленьких отказов",
                    "Анализ реакций окружающих",
                    "Закрепление новых паттернов"
                ]
            },
            "psychologist": {
                "time_total": 120,
                "time_per_week": 5,
                "duration_weeks": 24,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Поиск причин размытых границ",
                    "Проработка страха отвержения",
                    "Работа с чувством вины",
                    "Восстановление целостности",
                    "Интеграция"
                ]
            },
            "trainer": {
                "time_total": 60,
                "time_per_week": 2.5,
                "duration_weeks": 24,
                "energy_required": 4,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Техники твердого 'нет'",
                    "Я-высказывания",
                    "Управление дистанцией",
                    "Телесные практики границ",
                    "Ролевые игры"
                ]
            }
        },
        
        "self_esteem": {
            "coach": {
                "time_total": 100,
                "time_per_week": 4,
                "duration_weeks": 25,
                "energy_required": 5,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Анализ сильных сторон",
                    "Постановка достижимых целей",
                    "Фиксация успехов",
                    "Работа с внутренним критиком",
                    "Развитие самопринятия"
                ]
            },
            "psychologist": {
                "time_total": 150,
                "time_per_week": 6,
                "duration_weeks": 25,
                "energy_required": 6,
                "space_required": False,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Поиск корней низкой самооценки",
                    "Проработка детских посланий",
                    "Интеграция теневых частей",
                    "Формирование новой идентичности",
                    "Закрепление"
                ]
            },
            "trainer": {
                "time_total": 80,
                "time_per_week": 3,
                "duration_weeks": 26,
                "energy_required": 4,
                "space_required": True,
                "budget": 0,
                "support_required": False,
                "steps": [
                    "Ежедневные аффирмации",
                    "Практики самопрезентации",
                    "Ведение дневника достижений",
                    "Телесные практики уверенности",
                    "Публичные выступления"
                ]
            }
        }
    }
    
    # Защита от отсутствия цели
    if goal_id not in paths:
        logger.warning(f"Цель {goal_id} не найдена, возвращаю заглушку")
        return {
            "time_total": 200,
            "time_per_week": 8,
            "duration_weeks": 25,
            "energy_required": 6,
            "space_required": False,
            "budget": 0,
            "support_required": False,
            "steps": ["Информация уточняется"],
            "formatted_text": "Маршрут в разработке"
        }
    
    if mode not in paths[goal_id]:
        logger.warning(f"Режим {mode} не найден для цели {goal_id}, использую coach")
        mode = "coach"
    
    path = paths[goal_id][mode].copy()
    
    # Форматируем текст для вывода
    formatted_text = f"""
⏱ {bold('ВРЕМЯ:')} {path['time_total']} часов всего = {path['time_per_week']} ч/нед, {path['duration_weeks']} недель
⚡ {bold('ЭНЕРГИЯ:')} уровень {path['energy_required']}/10
🏠 {bold('ПРОСТРАНСТВО:')} {'✅ нужно отдельное' if path['space_required'] else 'не обязательно'}
💰 {bold('БЮДЖЕТ:')} {path['budget']}₽
👥 {bold('ПОДДЕРЖКА:')} {'✅ нужна' if path['support_required'] else 'опционально'}

{bold('ЭТАПЫ:')}
"""
    for i, step in enumerate(path['steps'], 1):
        formatted_text += f"{i}. {step}\n"
    
    path['formatted_text'] = formatted_text
    return path


# ============================================
# ГЕНЕРАЦИЯ ВОПРОСОВ ДЛЯ КОНТЕКСТА
# ============================================

def generate_life_context_questions() -> str:
    """Генерирует вопросы для сбора базового жизненного контекста"""
    return """
1️⃣ Семейное положение? (один/пара/семья/с родителями)
2️⃣ Есть дети? Если да, сколько и сколько лет?
3️⃣ Работаешь? Кем и какой график? (5/2, 2/2, свободный)
4️⃣ Сколько времени уходит на дорогу в день? (в минутах)
5️⃣ Есть своё жильё или съёмное? Ипотека?
6️⃣ Есть отдельная комната для дел?
7️⃣ Есть машина?
8️⃣ Кто из близких реально поддержит?
9️⃣ Кто будет мешать или обесценивать?
🔟 Оцени энергию от 1 до 10 в среднем
"""


def generate_goal_context_questions(goal_id: str, profile: Dict, mode: str, goal_name: str = "") -> str:
    """
    Генерирует вопросы под конкретную цель, профиль и режим
    
    Args:
        goal_id: идентификатор цели
        profile: данные профиля (векторы)
        mode: режим
        goal_name: название цели для контекста
    
    Returns:
        Строка с вопросами
    """
    
    # Получаем значения векторов с защитой от отсутствия данных
    try:
        behavioral = profile.get("behavioral_levels", {})
        sb = behavioral.get("СБ", [3])[0] if behavioral.get("СБ") else 3
        tf = behavioral.get("ТФ", [3])[0] if behavioral.get("ТФ") else 3
        ub = behavioral.get("УБ", [3])[0] if behavioral.get("УБ") else 3
        chv = behavioral.get("ЧВ", [3])[0] if behavioral.get("ЧВ") else 3
    except (IndexError, TypeError, KeyError):
        sb = tf = ub = chv = 3
    
    questions = []
    
    # Базовые вопросы для всех
    if "income" in goal_id or "money" in goal_id:
        questions.append("1️⃣ Какой навык будешь развивать? (коротко)")
        questions.append("2️⃣ Сколько часов в неделю реально можешь уделять?")
        questions.append("3️⃣ Нужны ли внешние инструменты/оборудование? (да/нет, какие)")
        
        # Вопросы от режима
        if mode == "coach":
            questions.append("4️⃣ Что для тебя идеальный результат?")
        elif mode == "psychologist":
            questions.append("4️⃣ Что самое страшное в увеличении дохода?")
            if sb >= 4:
                questions.append("5️⃣ Есть ли финансовая подушка? (да/нет)")
            if ub >= 4:
                questions.append("6️⃣ Доверяешь ли ты новым способам заработка?")
        elif mode == "trainer":
            questions.append("4️⃣ Готов ли вставать на час раньше ради цели?")
            if tf >= 4:
                questions.append("5️⃣ Какой результат хочешь получить через месяц?")
    
    elif "relations" in goal_id:
        questions.append("1️⃣ Сколько времени готов уделять знакомствам/встречам?")
        questions.append("2️⃣ Нужны ли внешние изменения? (гардероб/имидж)")
        questions.append("3️⃣ Готов ли ходить к психологу, если потребуется?")
        
        if mode == "psychologist":
            if chv >= 4:
                questions.append("4️⃣ Боишься остаться один?")
            if sb >= 4:
                questions.append("5️⃣ Что страшнее — отвержение или сближение?")
    
    elif "anxiety" in goal_id or "energy" in goal_id or "calm" in goal_id:
        questions.append("1️⃣ Сколько часов спишь в среднем?")
        questions.append("2️⃣ Есть ли хронические заболевания?")
        questions.append("3️⃣ Принимаешь ли какие-то препараты?")
        
        if mode == "psychologist":
            questions.append("4️⃣ Когда началось? С чем связано?")
        elif mode == "trainer":
            questions.append("4️⃣ Готов ли делать практики ежедневно?")
    
    elif "purpose" in goal_id or "meaning" in goal_id:
        questions.append("1️⃣ Сколько времени в неделю готов посвящать поиску?")
        questions.append("2️⃣ Есть ли идеи или гипотезы?")
        questions.append("3️⃣ Нужен ли наставник/психолог?")
        
        if mode == "psychologist":
            questions.append("4️⃣ Что запрещали в детстве?")
        elif mode == "trainer":
            questions.append("4️⃣ Готов тестировать разные активности?")
    
    else:
        # Общие вопросы для других целей
        questions.append("1️⃣ Сколько часов в неделю можешь уделять?")
        questions.append("2️⃣ Нужны ли внешние ресурсы?")
        questions.append("3️⃣ Кто может поддержать?")
    
    # Добавляем вопросы по профилю для всех целей
    if sb >= 4:
        questions.append("❓ Что обычно вызывает у тебя тревогу? (коротко)")
    if tf >= 4:
        questions.append("❓ Важен ли быстрый результат?")
    if ub >= 4:
        questions.append("❓ Доверяешь ли ты себе в этом вопросе?")
    if chv >= 4:
        questions.append("❓ Чьё мнение для тебя важно в этом?")
    
    return "\n".join(questions)


# ============================================
# РАСЧЁТ ДОСТИЖИМОСТИ
# ============================================

def calculate_feasibility(
    goal_path: Dict,
    life_context: Dict,
    goal_context: Dict,
    profile: Dict
) -> Dict[str, Any]:
    """
    Рассчитывает достижимость цели на основе всех данных
    
    Args:
        goal_path: теоретический путь к цели
        life_context: жизненный контекст пользователя
        goal_context: контекст под цель
        profile: профиль пользователя
    
    Returns:
        Dict с полями:
        - deficit: общий дефицит ресурсов в %
        - time_deficit: дефицит времени в %
        - energy_deficit: дефицит энергии в %
        - space_deficit: есть ли пространство (100% если нет)
        - support_deficit: есть ли поддержка (100% если нет)
        - budget_deficit: дефицит бюджета в %
        - requirements_text: что требуется
        - available_text: что есть
        - recommendation: рекомендация
        - status: цветовой статус (🟢/🟡/🔴)
        - status_text: текстовый статус
    """
    
    # Защита от отсутствия данных
    if not goal_path:
        goal_path = {}
    if not life_context:
        life_context = {}
    if not goal_context:
        goal_context = {}
    
    # Извлекаем данные с защитой
    required_time = goal_path.get("time_per_week", 10)
    if required_time <= 0:
        required_time = 10  # избегаем деления на ноль
    
    required_energy = goal_path.get("energy_required", 6)
    if required_energy <= 0:
        required_energy = 6
    
    required_space = goal_path.get("space_required", False)
    required_budget = goal_path.get("budget", 0)
    if required_budget < 0:
        required_budget = 0
    
    required_support = goal_path.get("support_required", False)
    
    # Данные пользователя с защитой
    available_time = float(goal_context.get("time_per_week", 0) or 0)
    if available_time < 0:
        available_time = 0
    
    available_energy = life_context.get("energy_level", 5)
    if available_energy <= 0:
        available_energy = 5
    
    available_space = life_context.get("has_private_space", False)
    available_budget = float(goal_context.get("budget", 0) or 0)
    if available_budget < 0:
        available_budget = 0
    
    available_support = bool(life_context.get("support_people"))
    
    # Считаем дефициты
    time_deficit = max(0, (required_time - available_time) / required_time * 100) if required_time > 0 else 0
    energy_deficit = max(0, (required_energy - available_energy) / required_energy * 100) if required_energy > 0 else 0
    space_deficit = 100 if required_space and not available_space else 0
    support_deficit = 100 if required_support and not available_support else 0
    budget_deficit = max(0, (required_budget - available_budget) / required_budget * 100) if required_budget > 0 else 0
    
    # Общий дефицит (среднее, но пространство и поддержка имеют больший вес)
    deficits = [time_deficit, energy_deficit, space_deficit, support_deficit, budget_deficit]
    weights = [1, 1, 2, 1.5, 1]  # пространство и поддержка важнее
    
    weighted_sum = sum(d * w for d, w in zip(deficits, weights))
    total_weight = sum(weights)
    total_deficit = weighted_sum / total_weight if total_weight > 0 else 0
    
    # Ограничиваем дефицит диапазоном 0-100
    total_deficit = max(0, min(100, total_deficit))
    
    # Определяем статус
    if total_deficit <= 20:
        status = "🟢"
        status_text = "ЦЕЛЬ ДОСТИЖИМА"
    elif total_deficit <= 50:
        status = "🟡"
        status_text = "ТРЕБУЕТ КОРРЕКТИРОВКИ"
    else:
        status = "🔴"
        status_text = "ЦЕЛЬ НЕДОСТИЖИМА"
    
    # Формируем тексты
    requirements_text = f"""
⏱ {bold('ВРЕМЯ:')} {required_time} ч/нед
⚡ {bold('ЭНЕРГИЯ:')} уровень {required_energy}/10
🏠 {bold('ПРОСТРАНСТВО:')} {'✅ нужно' if required_space else 'не обязательно'}
💰 {bold('БЮДЖЕТ:')} {required_budget}₽
👥 {bold('ПОДДЕРЖКА:')} {'✅ нужна' if required_support else 'опционально'}
"""
    
    available_text = f"""
⏱ {bold('ВРЕМЯ:')} {available_time} ч/нед
⚡ {bold('ЭНЕРГИЯ:')} уровень {available_energy}/10
🏠 {bold('ПРОСТРАНСТВО:')} {'✅ есть' if available_space else '❌ нет'}
💰 {bold('БЮДЖЕТ:')} {available_budget}₽
👥 {bold('ПОДДЕРЖКА:')} {'✅ есть' if available_support else '❌ нет'}
"""
    
    # Формируем рекомендацию
    if total_deficit <= 20:
        recommendation = "Отличные условия! Можно начинать по плану."
    elif total_deficit <= 50:
        recommendation = "Есть дефициты, которые стоит учесть:\n"
        if time_deficit > 20:
            recommendation += "• Не хватает времени — увеличь срок или найди окна\n"
        if energy_deficit > 20:
            recommendation += "• Энергия ниже требуемой — начни с восстановления\n"
        if space_deficit > 0:
            recommendation += "• Нет отдельного пространства — найди место (кафе, коворкинг)\n"
        if support_deficit > 0:
            recommendation += "• Нет поддержки — найди единомышленников или наставника\n"
        if budget_deficit > 0:
            recommendation += f"• Не хватает {int(budget_deficit)}% бюджета — пересмотри расходы\n"
    else:
        recommendation = "Цель требует серьёзной подготовки:\n"
        recommendation += "• Увеличь срок в 2 раза\n"
        recommendation += "• Сначала создай условия (время, пространство, энергия)\n"
        recommendation += "• Или выбери более реалистичную цель"
    
    return {
        "deficit": round(total_deficit, 1),
        "time_deficit": round(time_deficit, 1),
        "energy_deficit": round(energy_deficit, 1),
        "space_deficit": round(space_deficit, 1),
        "support_deficit": round(support_deficit, 1),
        "budget_deficit": round(budget_deficit, 1),
        "requirements_text": requirements_text,
        "available_text": available_text,
        "recommendation": recommendation,
        "status": status,
        "status_text": status_text
    }


# ============================================
# ФУНКЦИИ ДЛЯ СОХРАНЕНИЯ РЕЗУЛЬТАТОВ
# ============================================

def save_feasibility_result(user_id: int, goal_id: str, result: Dict) -> None:
    """
    Сохраняет результат проверки реальности
    
    Args:
        user_id: ID пользователя
        goal_id: ID цели
        result: результат проверки
    """
    # Здесь можно добавить сохранение в базу данных или файл
    # Например, в JSON-файл
    try:
        import json
        import os
        from datetime import datetime
        
        # Создаем папку для результатов, если её нет
        os.makedirs("feasibility_results", exist_ok=True)
        
        # Формируем имя файла
        filename = f"feasibility_results/user_{user_id}_{datetime.now().strftime('%Y%m%d')}.json"
        
        # Загружаем существующие результаты
        data = []
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except:
                    data = []
        
        # Добавляем новый результат
        data.append({
            "user_id": user_id,
            "goal_id": goal_id,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
        # Сохраняем
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logger.error(f"Ошибка при сохранении результата: {e}")


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def get_goal_difficulty(goal_id: str, mode: str) -> str:
    """
    Возвращает сложность цели
    
    Args:
        goal_id: ID цели
        mode: режим
    
    Returns:
        "easy", "medium" или "hard"
    """
    difficulties = {
        "income_growth": {"coach": "hard", "psychologist": "medium", "trainer": "hard"},
        "money_blocks": {"coach": "medium", "psychologist": "medium", "trainer": "easy"},
        "relations": {"coach": "medium", "psychologist": "hard", "trainer": "medium"},
        "anxiety_reduce": {"coach": "medium", "psychologist": "hard", "trainer": "easy"},
        "energy_boost": {"coach": "easy", "psychologist": "medium", "trainer": "easy"},
        "purpose": {"coach": "hard", "psychologist": "hard", "trainer": "medium"},
        "boundaries": {"coach": "medium", "psychologist": "hard", "trainer": "easy"},
        "self_esteem": {"coach": "medium", "psychologist": "hard", "trainer": "easy"}
    }
    
    if goal_id in difficulties and mode in difficulties[goal_id]:
        return difficulties[goal_id][mode]
    return "medium"


def get_goal_time_estimate(goal_id: str, mode: str) -> str:
    """
    Возвращает оценку времени для цели
    
    Args:
        goal_id: ID цели
        mode: режим
    
    Returns:
        Строка с оценкой времени
    """
    estimates = {
        "income_growth": {"coach": "6 месяцев", "psychologist": "6 месяцев", "trainer": "6 месяцев"},
        "money_blocks": {"coach": "4-6 недель", "psychologist": "6-8 недель", "trainer": "4-6 недель"},
        "relations": {"coach": "4-6 месяцев", "psychologist": "6-8 месяцев", "trainer": "4-6 месяцев"},
        "anxiety_reduce": {"coach": "6 месяцев", "psychologist": "6-8 месяцев", "trainer": "4-6 месяцев"},
        "energy_boost": {"coach": "4-6 месяцев", "psychologist": "6 месяцев", "trainer": "4-6 месяцев"},
        "purpose": {"coach": "6-8 месяцев", "psychologist": "6-8 месяцев", "trainer": "4-6 месяцев"},
        "boundaries": {"coach": "4-6 месяцев", "psychologist": "6 месяцев", "trainer": "4-6 месяцев"},
        "self_esteem": {"coach": "4-6 месяцев", "psychologist": "6 месяцев", "trainer": "4-6 месяцев"}
    }
    
    if goal_id in estimates and mode in estimates[goal_id]:
        return estimates[goal_id][mode]
    return "3-6 месяцев"
