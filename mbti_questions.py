"""
🧠 Модуль MBTI: Научно-обоснованные вопросы для определения типа личности
Версия 1.0
"""

import logging
logger = logging.getLogger(__name__)

# Шкала ответов для MBTI
MBTI_SCALE = {
    "1": {"text": "❌ Совершенно не согласен", "value": 1},
    "2": {"text": "⚠️ Скорее не согласен", "value": 2},
    "3": {"text": "⚪ Нейтрально", "value": 3},
    "4": {"text": "✅ Скорее согласен", "value": 4},
    "5": {"text": "👍 Полностью согласен", "value": 5}
}

# Названия типов MBTI
MBTI_TYPE_NAMES = {
    "ISTJ": "Инспектор",
    "ISFJ": "Защитник",
    "INFJ": "Адвокат",
    "INTJ": "Стратег",
    "ISTP": "Виртуоз",
    "ISFP": "Художник",
    "INFP": "Посредник",
    "INTP": "Логик",
    "ESTP": "Делец",
    "ESFP": "Развлекатель",
    "ENFP": "Борец",
    "ENTP": "Полемист",
    "ESTJ": "Менеджер",
    "ESFJ": "Консул",
    "ENFJ": "Тренер",
    "ENTJ": "Командир"
}

def get_mbti_questions(gender):
    """
    Возвращает полный список вопросов MBTI (81 вопрос)
    Сбалансированы по шкалам, включают прямые и обратные вопросы
    """
    
    # ========== Шкала E/I (Экстраверсия - Интроверсия) ==========
    ei_questions = [
        {
            "text": "После напряжённой рабочей недели я предпочитаю провести выходные с друзьями на мероприятии, а не в одиночестве дома.",
            "dimension": "EI",
            "direction": "E",
            "reverse": False
        },
        {
            "text": "В новой компании я обычно жду, пока другие начнут разговор, прежде чем активно включиться.",
            "dimension": "EI",
            "direction": "I",
            "reverse": True
        },
        {
            "text": "Я чувствую прилив энергии после нескольких часов общения с большой группой людей.",
            "dimension": "EI",
            "direction": "E",
            "reverse": False
        },
        {
            "text": "Мне нужно время в одиночестве, чтобы «перезарядиться» после социальных взаимодействий.",
            "dimension": "EI",
            "direction": "I",
            "reverse": True
        },
        {
            "text": "На вечеринке я скорее буду перемещаться между группами, знакомясь с новыми людьми, чем глубоко беседовать с одним-двумя знакомыми.",
            "dimension": "EI",
            "direction": "E",
            "reverse": False
        },
        {
            "text": "Я предпочитаю обдумывать свои мысли внутренне, прежде чем высказывать их вслух.",
            "dimension": "EI",
            "direction": "I",
            "reverse": True
        },
        {
            "text": "Работа в открытом офисе с постоянным общением меня стимулирует больше, чем утомляет.",
            "dimension": "EI",
            "direction": "E",
            "reverse": False
        },
        {
            "text": "Я часто думаю вслух, формулируя идеи в процессе разговора.",
            "dimension": "EI",
            "direction": "E",
            "reverse": False
        },
        {
            "text": "Длительное пребывание в одиночестве вызывает у меня чувство беспокойства или скуки.",
            "dimension": "EI",
            "direction": "E",
            "reverse": False
        },
        {
            "text": "Я предпочитаю письменное общение (сообщения, email) устным разговорам или звонкам.",
            "dimension": "EI",
            "direction": "I",
            "reverse": True
        },
        {
            "text": "Когда я сталкиваюсь с проблемой, я предпочитаю обсудить её с кем-то, чтобы прояснить свои мысли.",
            "dimension": "EI",
            "direction": "E",
            "reverse": False
        },
        {
            "text": "Я чувствую себя истощённым после целого дня встреч и общения с людьми.",
            "dimension": "EI",
            "direction": "I",
            "reverse": True
        },
        {
            "text": "В учебной или рабочей группе я естественно беру на себя роль координатора общения.",
            "dimension": "EI",
            "direction": "E",
            "reverse": False
        },
        {
            "text": "Я предпочитаю наблюдать за ситуацией со стороны, прежде чем в неё включиться.",
            "dimension": "EI",
            "direction": "I",
            "reverse": True
        },
        {
            "text": "Молчание в разговоре вызывает у меня желание его заполнить.",
            "dimension": "EI",
            "direction": "E",
            "reverse": False
        },
        {
            "text": "Я легко знакомлюсь с новыми людьми в незнакомой обстановке.",
            "dimension": "EI",
            "direction": "E",
            "reverse": False
        },
        {
            "text": "После активного общения мне нужно побыть одному, чтобы прийти в себя.",
            "dimension": "EI",
            "direction": "I",
            "reverse": True
        },
        {
            "text": "Я люблю быть в центре внимания и получать отклик от окружающих.",
            "dimension": "EI",
            "direction": "E",
            "reverse": False
        },
        {
            "text": "Я часто оказываюсь слушателем, а не рассказчиком в компании.",
            "dimension": "EI",
            "direction": "I",
            "reverse": True
        },
        {
            "text": "Я предпочитаю работать в команде, а не в одиночку.",
            "dimension": "EI",
            "direction": "E",
            "reverse": False
        }
    ]

    # ========== Шкала S/N (Сенсорика - Интуиция) ==========
    sn_questions = [
        {
            "text": "При планировании отпуска я сосредотачиваюсь на конкретных деталях: бронировании, маршрутах, бюджете.",
            "dimension": "SN",
            "direction": "S",
            "reverse": False
        },
        {
            "text": "Меня больше вдохновляют абстрактные концепции и теории, чем практические примеры.",
            "dimension": "SN",
            "direction": "N",
            "reverse": True
        },
        {
            "text": "Я предпочитаю следовать проверенным методам работы, а не экспериментировать с новыми подходами.",
            "dimension": "SN",
            "direction": "S",
            "reverse": False
        },
        {
            "text": "Я часто вижу скрытые связи и паттерны там, где другие видят отдельные факты.",
            "dimension": "SN",
            "direction": "N",
            "reverse": True
        },
        {
            "text": "При описании события я фокусируюсь на конкретных фактах: кто, что, где, когда.",
            "dimension": "SN",
            "direction": "S",
            "reverse": False
        },
        {
            "text": "Меня привлекают метафоры, символы и возможность интерпретировать смыслы.",
            "dimension": "SN",
            "direction": "N",
            "reverse": True
        },
        {
            "text": "Я доверяю своему непосредственному опыту больше, чем теоретическим предположениям.",
            "dimension": "SN",
            "direction": "S",
            "reverse": False
        },
        {
            "text": "При решении проблемы я сначала представляю общую картину, а потом перехожу к деталям.",
            "dimension": "SN",
            "direction": "N",
            "reverse": True
        },
        {
            "text": "Я предпочитаю пошаговые инструкции абстрактным принципам.",
            "dimension": "SN",
            "direction": "S",
            "reverse": False
        },
        {
            "text": "Меня больше интересует, каким что-то может стать в будущем, чем каково оно сейчас.",
            "dimension": "SN",
            "direction": "N",
            "reverse": True
        },
        {
            "text": "При чтении инструкции я следую каждому шагу последовательно.",
            "dimension": "SN",
            "direction": "S",
            "reverse": False
        },
        {
            "text": "Я часто задумываюсь о глобальных вопросах и философских концепциях.",
            "dimension": "SN",
            "direction": "N",
            "reverse": True
        },
        {
            "text": "Я замечаю мелкие детали в окружающей обстановке, которые другие упускают.",
            "dimension": "SN",
            "direction": "S",
            "reverse": False
        },
        {
            "text": "Меня больше интересуют инновации и новые возможности, чем совершенствование существующего.",
            "dimension": "SN",
            "direction": "N",
            "reverse": True
        },
        {
            "text": "Я предпочитаю работать с конкретными данными и фактами, а не с абстрактными идеями.",
            "dimension": "SN",
            "direction": "S",
            "reverse": False
        },
        {
            "text": "Я легко представляю себе будущие сценарии и альтернативные реальности.",
            "dimension": "SN",
            "direction": "N",
            "reverse": True
        },
        {
            "text": "Я доверяю проверенным традициям и методам больше, чем непроверенным новшествам.",
            "dimension": "SN",
            "direction": "S",
            "reverse": False
        },
        {
            "text": "Я часто ловлю себя на том, что строю догадки и предположения о том, что будет дальше.",
            "dimension": "SN",
            "direction": "N",
            "reverse": True
        },
        {
            "text": "Для меня важны практические, осязаемые результаты работы.",
            "dimension": "SN",
            "direction": "S",
            "reverse": False
        },
        {
            "text": "Я люблю размышлять о том, «что было бы, если...».",
            "dimension": "SN",
            "direction": "N",
            "reverse": True
        }
    ]

    # ========== Шкала T/F (Мышление - Чувство) ==========
    tf_questions = [
        {
            "text": "При принятии решения я в первую очередь анализирую логические последствия, а не влияние на людей.",
            "dimension": "TF",
            "direction": "T",
            "reverse": False
        },
        {
            "text": "Я считаю, что поддержание гармонии в отношениях важнее, чем отстаивание объективной правды.",
            "dimension": "TF",
            "direction": "F",
            "reverse": True
        },
        {
            "text": "Меня раздражает, когда эмоции мешают рациональному обсуждению.",
            "dimension": "TF",
            "direction": "T",
            "reverse": False
        },
        {
            "text": "При конфликте я стараюсь понять чувства всех сторон, прежде чем выносить суждение.",
            "dimension": "TF",
            "direction": "F",
            "reverse": True
        },
        {
            "text": "Я ценю справедливость и последовательность правил больше, чем индивидуальный подход к каждой ситуации.",
            "dimension": "TF",
            "direction": "T",
            "reverse": False
        },
        {
            "text": "Критика воспринимается мной как личное отношение, а не просто обратная связь о работе.",
            "dimension": "TF",
            "direction": "F",
            "reverse": True
        },
        {
            "text": "Я легко могу указать на ошибки в чужой аргументации, даже если это может обидеть человека.",
            "dimension": "TF",
            "direction": "T",
            "reverse": False
        },
        {
            "text": "При принятии решения я учитываю, как оно повлияет на благополучие окружающих.",
            "dimension": "TF",
            "direction": "F",
            "reverse": True
        },
        {
            "text": "Я считаю комплименты и выражение признательности менее важными, чем конкретные результаты работы.",
            "dimension": "TF",
            "direction": "T",
            "reverse": False
        },
        {
            "text": "Мне естественно выражать эмпатию и эмоциональную поддержку другим людям.",
            "dimension": "TF",
            "direction": "F",
            "reverse": True
        },
        {
            "text": "Когда друг делится проблемой, я сначала предлагаю практические решения.",
            "dimension": "TF",
            "direction": "T",
            "reverse": False
        },
        {
            "text": "Я считаю важным сохранить чьи-то чувства, даже если это требует смягчить правду.",
            "dimension": "TF",
            "direction": "F",
            "reverse": True
        },
        {
            "text": "Я легко отделяю личное отношение к человеку от оценки его работы или идей.",
            "dimension": "TF",
            "direction": "T",
            "reverse": False
        },
        {
            "text": "Атмосфера и эмоциональный климат в коллективе для меня так же важны, как и результаты работы.",
            "dimension": "TF",
            "direction": "F",
            "reverse": True
        },
        {
            "text": "Я считаю, что объективный анализ всегда предпочтительнее субъективных переживаний.",
            "dimension": "TF",
            "direction": "T",
            "reverse": False
        },
        {
            "text": "Я принимаю решения, основываясь на том, что кажется правильным с человеческой точки зрения.",
            "dimension": "TF",
            "direction": "F",
            "reverse": True
        },
        {
            "text": "Мне легче дать конструктивную критику, чем похвалу.",
            "dimension": "TF",
            "direction": "T",
            "reverse": False
        },
        {
            "text": "Я часто ставлю потребности других людей выше своих собственных.",
            "dimension": "TF",
            "direction": "F",
            "reverse": True
        },
        {
            "text": "Я верю, что правда важнее, чем чьи-то чувства.",
            "dimension": "TF",
            "direction": "T",
            "reverse": False
        },
        {
            "text": "Я очень чувствителен(на) к тону и настроению разговора.",
            "dimension": "TF",
            "direction": "F",
            "reverse": True
        }
    ]

    # ========== Шкала J/P (Суждение - Восприятие) ==========
    jp_questions = [
        {
            "text": "Я предпочитаю планировать свой день заранее и следовать этому плану.",
            "dimension": "JP",
            "direction": "J",
            "reverse": False
        },
        {
            "text": "Мне комфортно оставлять варианты открытыми и принимать решения спонтанно.",
            "dimension": "JP",
            "direction": "P",
            "reverse": True
        },
        {
            "text": "Незавершённые дела и открытые вопросы вызывают у меня дискомфорт.",
            "dimension": "JP",
            "direction": "J",
            "reverse": False
        },
        {
            "text": "Я часто начинаю новые проекты, не завершив предыдущие.",
            "dimension": "JP",
            "direction": "P",
            "reverse": True
        },
        {
            "text": "Я предпочитаю иметь чёткие дедлайны и структуру в работе.",
            "dimension": "JP",
            "direction": "J",
            "reverse": False
        },
        {
            "text": "Я лучше работаю под давлением приближающегося срока, чем с большим запасом времени.",
            "dimension": "JP",
            "direction": "P",
            "reverse": True
        },
        {
            "text": "Моё рабочее пространство обычно организовано и упорядочено.",
            "dimension": "JP",
            "direction": "J",
            "reverse": False
        },
        {
            "text": "Я легко адаптируюсь к изменениям планов и неожиданным обстоятельствам.",
            "dimension": "JP",
            "direction": "P",
            "reverse": True
        },
        {
            "text": "Я предпочитаю принять решение и двигаться дальше, чем долго собирать дополнительную информацию.",
            "dimension": "JP",
            "direction": "J",
            "reverse": False
        },
        {
            "text": "Мне нравится исследовать разные возможности, даже если это задерживает окончательное решение.",
            "dimension": "JP",
            "direction": "P",
            "reverse": True
        },
        {
            "text": "Я составляю списки дел и получаю удовлетворение от вычёркивания выполненных задач.",
            "dimension": "JP",
            "direction": "J",
            "reverse": False
        },
        {
            "text": "Я предпочитаю гибкий график работы жёсткому распорядку.",
            "dimension": "JP",
            "direction": "P",
            "reverse": True
        },
        {
            "text": "Я чувствую себя некомфортно, когда не знаю, что буду делать завтра.",
            "dimension": "JP",
            "direction": "J",
            "reverse": False
        },
        {
            "text": "Мне нравится оставлять решения открытыми на случай появления новой информации.",
            "dimension": "JP",
            "direction": "P",
            "reverse": True
        },
        {
            "text": "Я предпочитаю закончить один проект, прежде чем начинать следующий.",
            "dimension": "JP",
            "direction": "J",
            "reverse": False
        },
        {
            "text": "Я часто откладываю дела до последнего момента и работаю наиболее продуктивно перед дедлайном.",
            "dimension": "JP",
            "direction": "P",
            "reverse": True
        },
        {
            "text": "Мне важно, чтобы всё было на своих местах и организовано определённым образом.",
            "dimension": "JP",
            "direction": "J",
            "reverse": False
        },
        {
            "text": "Я легко переключаюсь между задачами в зависимости от настроения или обстоятельств.",
            "dimension": "JP",
            "direction": "P",
            "reverse": True
        },
        {
            "text": "Я предпочитаю иметь чёткий план действий перед началом проекта.",
            "dimension": "JP",
            "direction": "J",
            "reverse": False
        },
        {
            "text": "Мне комфортно действовать по ситуации, без заранее определённого плана.",
            "dimension": "JP",
            "direction": "P",
            "reverse": True
        }
    ]

    # ========== Контрольные вопросы (честность и согласованность) ==========
    control_questions = [
        {
            "text": "Я всегда говорю только правду, даже в мелочах.",
            "dimension": "CONTROL",
            "direction": "SD",
            "reverse": False,
            "control_type": "social_desirability"
        },
        {
            "text": "Я никогда не опаздываю на встречи.",
            "dimension": "CONTROL",
            "direction": "SD",
            "reverse": False,
            "control_type": "social_desirability"
        },
        {
            "text": "Я никогда не испытываю негативных эмоций по отношению к другим людям.",
            "dimension": "CONTROL",
            "direction": "SD",
            "reverse": False,
            "control_type": "social_desirability"
        },
        {
            "text": "Я чувствую прилив энергии после общения с большой группой людей.",
            "dimension": "EI",
            "direction": "E",
            "reverse": False,
            "control_type": "consistency",
            "duplicate_of": 2
        },
        {
            "text": "При решении проблемы я сначала вижу общую картину, а потом детали.",
            "dimension": "SN",
            "direction": "N",
            "reverse": True,
            "control_type": "consistency",
            "duplicate_of": 7
        }
    ]

    # Объединяем все вопросы
    all_questions = ei_questions + sn_questions + tf_questions + jp_questions + control_questions
    
    # Добавляем индексы для удобства
    for i, q in enumerate(all_questions):
        q["index"] = i
    
    logger.info(f"📊 MBTI: загружено {len(all_questions)} вопросов")
    return all_questions

def calculate_mbti_type(answers):
    """
    Рассчитывает MBTI тип на основе ответов
    answers: словарь с ответами вида {"mbti_0": 4, "mbti_1": 2, ...}
    """
    scores = {
        "E": 0, "I": 0,
        "S": 0, "N": 0,
        "T": 0, "F": 0,
        "J": 0, "P": 0
    }
    
    control_scores = {
        "social_desirability": [],
        "consistency": {}
    }
    
    # Получаем все вопросы для проверки дубликатов
    all_questions = get_mbti_questions("М")
    
    for key, value in answers.items():
        if not key.startswith("mbti_"):
            continue
        
        idx = int(key.split("_")[1])
        if idx >= len(all_questions):
            continue
            
        q = all_questions[idx]
        
        # Для контрольных вопросов
        if q.get("control_type") == "social_desirability":
            control_scores["social_desirability"].append(value)
            continue
        
        # Для дубликатов сохраняем для проверки согласованности
        if q.get("control_type") == "consistency":
            original_idx = q.get("duplicate_of")
            if original_idx is not None:
                control_scores["consistency"][idx] = value
        
        # Инвертируем если обратный вопрос
        if q.get("reverse", False):
            score = 6 - value  # 1->5, 2->4, 3->3, 4->2, 5->1
        else:
            score = value
        
        # Добавляем к соответствующей шкале
        scores[q["direction"]] += score
    
    # Проверка валидности
    validation = {
        "valid": True,
        "warnings": []
    }
    
    # Проверка социальной желательности
    if control_scores["social_desirability"]:
        avg_sd = sum(control_scores["social_desirability"]) / len(control_scores["social_desirability"])
        if avg_sd > 4.0:
            validation["warnings"].append("⚠️ Возможно, вы старались выглядеть лучше, чем есть на самом деле")
            validation["valid"] = False
    
    # Проверка согласованности
    for dup_idx, dup_value in control_scores["consistency"].items():
        q = all_questions[dup_idx]
        original_idx = q.get("duplicate_of")
        original_key = f"mbti_{original_idx}"
        
        if original_key in answers:
            original_value = answers[original_key]
            
            # Инвертируем для обратных вопросов
            if all_questions[original_idx].get("reverse", False):
                original_score = 6 - original_value
            else:
                original_score = original_value
            
            if all_questions[dup_idx].get("reverse", False):
                dup_score = 6 - dup_value
            else:
                dup_score = dup_value
            
            if abs(original_score - dup_score) > 2:
                validation["warnings"].append("⚠️ Обнаружены противоречия в ответах")
                validation["valid"] = False
    
    # Определяем тип
    mbti_type = ""
    mbti_type += "E" if scores["E"] > scores["I"] else "I"
    mbti_type += "S" if scores["S"] > scores["N"] else "N"
    mbti_type += "T" if scores["T"] > scores["F"] else "F"
    mbti_type += "J" if scores["J"] > scores["P"] else "P"
    
    # Рассчитываем выраженность (нормализуем к диапазону -20..20)
    preferences = {
        "EI": max(-20, min(20, scores["E"] - scores["I"])),
        "SN": max(-20, min(20, scores["S"] - scores["N"])),
        "TF": max(-20, min(20, scores["T"] - scores["F"])),
        "JP": max(-20, min(20, scores["J"] - scores["P"]))
    }
    
    return {
        "type": mbti_type,
        "type_name": MBTI_TYPE_NAMES.get(mbti_type, "Неизвестный тип"),
        "scores": scores,
        "preferences": preferences,
        "validation": validation
    }

def get_mbti_interpretation(mbti_result, gender="М", age=30):
    """
    Возвращает интерпретацию MBTI типа
    """
    mbti_type = mbti_result["type"]
    preferences = mbti_result["preferences"]
    type_name = MBTI_TYPE_NAMES.get(mbti_type, "Неизвестный тип")
    
    # Описание выраженности
    strength_desc = {}
    for dim, score in preferences.items():
        if abs(score) < 5:
            strength_desc[dim] = "Сбалансированность"
        elif abs(score) < 10:
            strength_desc[dim] = "Умеренное предпочтение"
        else:
            strength_desc[dim] = "Выраженное предпочтение"
    
    # База описаний типов
    descriptions = {
        "ISTJ": {
            "strengths": "Исключительная надежность, систематический подход, внимание к деталям, уважение к традициям, практичность",
            "weaknesses": "Гибкость в изменяющихся ситуациях, открытость новому, выражение эмоций",
            "career": "Бухгалтер, аудитор, юрист, инженер, военный, администратор",
            "relationships": "Цените стабильность, проявляете заботу через действия, верны партнеру"
        },
        "ISFJ": {
            "strengths": "Глубокая эмпатия, внимание к потребностям других, надежность, практическая помощь",
            "weaknesses": "Личные границы, принятие изменений, выражение собственных потребностей",
            "career": "Медсестра, учитель, социальный работник, HR-специалист, библиотекарь",
            "relationships": "Чрезвычайно заботливы, создаете уют, нуждаетесь в признании"
        },
        "INFJ": {
            "strengths": "Глубокое понимание людей, идеализм, креативность, способность видеть потенциал",
            "weaknesses": "Реалистичность ожиданий, практические аспекты, принятие несовершенства",
            "career": "Психолог, писатель, учитель, консультант, некоммерческий сектор",
            "relationships": "Ищете глубокие связи, интуитивно понимаете партнера, преданы"
        },
        "INTJ": {
            "strengths": "Стратегическое мышление, независимость, высокие стандарты, решительность",
            "weaknesses": "Терпимость к ошибкам, эмоциональная экспрессия, гибкость",
            "career": "Ученый, программист, стратег, архитектор, аналитик",
            "relationships": "Цените интеллектуальное партнерство, нуждаетесь в пространстве"
        },
        "ISTP": {
            "strengths": "Практические навыки, быстрая реакция, логический анализ, независимость",
            "weaknesses": "Долгосрочное планирование, выражение эмоций, завершение проектов",
            "career": "Механик, инженер, хирург, программист, спортсмен",
            "relationships": "Проявляете любовь через действия, нуждаетесь в свободе"
        },
        "ISFP": {
            "strengths": "Художественная чувствительность, эмпатия, гибкость, аутентичность",
            "weaknesses": "Ассертивность, долгосрочное планирование, структурированность",
            "career": "Художник, дизайнер, музыкант, ветеринар, фотограф",
            "relationships": "Романтичны, внимательны к деталям, избегаете конфликтов"
        },
        "INFP": {
            "strengths": "Глубокие ценности, креативность, эмпатия, аутентичность",
            "weaknesses": "Практичность, принятие решений, завершение проектов",
            "career": "Писатель, психолог, художник, учитель, социальный работник",
            "relationships": "Ищете душевную связь, идеализируете партнера, преданы"
        },
        "INTP": {
            "strengths": "Аналитическое мышление, способность к абстракциям, независимость, любознательность",
            "weaknesses": "Практическая реализация, эмоциональная экспрессия, организованность",
            "career": "Ученый, программист, философ, математик, аналитик",
            "relationships": "Цените интеллектуальную стимуляцию, нуждаетесь в независимости"
        },
        "ESTP": {
            "strengths": "Энергичность, быстрая оценка ситуаций, практичность, харизма",
            "weaknesses": "Долгосрочное планирование, чувствительность к эмоциям, терпение",
            "career": "Предприниматель, продавец, маркетолог, спортсмен",
            "relationships": "Спонтанны, ориентированы на действия, привносите азарт"
        },
        "ESFP": {
            "strengths": "Энтузиазм, способность развлекать, спонтанность, эмпатия",
            "weaknesses": "Долгосрочное планирование, финансовая дисциплина, глубокая рефлексия",
            "career": "Актер, ведущий, учитель, продавец, стилист",
            "relationships": "Щедры, создаете веселую атмосферу, живете настоящим"
        },
        "ENFP": {
            "strengths": "Энтузиазм, креативность, способность видеть потенциал, эмпатия",
            "weaknesses": "Завершение начатого, практичность, реалистичность ожиданий",
            "career": "Психолог, журналист, учитель, маркетолог, консультант",
            "relationships": "Страстны, ищете глубокую связь, спонтанны"
        },
        "ENTP": {
            "strengths": "Быстрое мышление, способность видеть возможности, инновационность, умение дебатировать",
            "weaknesses": "Чувствительность к эмоциям, завершение проектов, рутинные обязанности",
            "career": "Предприниматель, изобретатель, юрист, консультант",
            "relationships": "Интеллектуально стимулируете, нуждаетесь в независимости"
        },
        "ESTJ": {
            "strengths": "Организаторские способности, эффективность, ответственность, прямота",
            "weaknesses": "Гибкость, эмпатия, открытость новым идеям",
            "career": "Менеджер, военный, судья, администратор, банкир",
            "relationships": "Берете ответственность, цените традиционные роли"
        },
        "ESFJ": {
            "strengths": "Забота о других, гостеприимство, организация событий, лояльность",
            "weaknesses": "Личные границы, принятие критики, гибкость",
            "career": "Учитель, медсестра, администратор, HR-менеджер",
            "relationships": "Чрезвычайно заботливы, создаете традиции"
        },
        "ENFJ": {
            "strengths": "Харизма, понимание людей, организация для общей цели, эмпатия",
            "weaknesses": "Забота о себе, реалистичность ожиданий, принятие критики",
            "career": "Учитель, психолог, HR-директор, политик, тренер",
            "relationships": "Глубоко преданы, интуитивно понимаете потребности"
        },
        "ENTJ": {
            "strengths": "Лидерство, стратегическое мышление, эффективность, уверенность",
            "weaknesses": "Терпение, эмоциональная чувствительность, слушание других",
            "career": "CEO, предприниматель, юрист, менеджер проектов",
            "relationships": "Берете лидерство, цените интеллект партнера"
        }
    }
    
    desc = descriptions.get(mbti_type, {
        "strengths": "Уникальное сочетание качеств",
        "weaknesses": "Индивидуальные особенности",
        "career": "Множество вариантов",
        "relationships": "Индивидуальный подход"
    })
    
    # Формируем интерпретацию
    interpretation = f"""*📊 Выраженность предпочтений:*
• E/I: {preferences['EI']} ({strength_desc['EI']})
• S/N: {preferences['SN']} ({strength_desc['SN']})
• T/F: {preferences['TF']} ({strength_desc['TF']})
• J/P: {preferences['JP']} ({strength_desc['JP']})

*⚡ Сильные стороны:*
{desc['strengths']}

*🌱 Зоны развития:*
{desc['weaknesses']}

*💼 Карьерные рекомендации:*
{desc['career']}

*❤️ В отношениях:*
{desc['relationships']}"""
    
    return interpretation
