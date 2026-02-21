"""
Вопросы для теста "Сексуальный профайл"
3 блока по 8 вопросов = 24 вопроса
"""

SEXUAL_QUESTIONS = [
    # БЛОК 1: ТЕМПЕРАМЕНТ (вопросы 0-7)
    {
        "id": "s1_1",
        "text": "В сексе вы скорее...",
        "block": "temperament",
        "options": {
            "a": {"text": "Активный и напористый", "scores": {"PREDATOR": 2}},
            "b": {"text": "Чувственный и медленный", "scores": {"ARTIST": 2}},
            "c": {"text": "Наблюдающий и изучающий", "scores": {"OBSERVER": 2}},
            "d": {"text": "Игривый и разнообразный", "scores": {"PLAYER": 2}}
        }
    },
    {
        "id": "s1_2",
        "text": "Что вас заводит сильнее?",
        "block": "temperament",
        "options": {
            "a": {"text": "Охота и соблазнение", "scores": {"PREDATOR": 2}},
            "b": {"text": "Атмосфера и эстетика", "scores": {"ARTIST": 2}},
            "c": {"text": "Наблюдение за партнёром", "scores": {"OBSERVER": 2}},
            "d": {"text": "Эксперименты и новизна", "scores": {"PLAYER": 2}}
        }
    },
    {
        "id": "s1_3",
        "text": "Ваш любимый темп в сексе:",
        "block": "temperament",
        "options": {
            "a": {"text": "Быстрый и интенсивный", "scores": {"PREDATOR": 2}},
            "b": {"text": "Медленный, тягучий", "scores": {"ARTIST": 2}},
            "c": {"text": "Разный, подстраиваюсь", "scores": {"OBSERVER": 1, "PLAYER": 1}},
            "d": {"text": "Меняю по настроению", "scores": {"PLAYER": 2}}
        }
    },
    {
        "id": "s1_4",
        "text": "После секса вы чаще:",
        "block": "temperament",
        "options": {
            "a": {"text": "Чувствую удовлетворённую усталость", "scores": {"PREDATOR": 1}},
            "b": {"text": "Хочу обниматься и говорить", "scores": {"ARTIST": 2}},
            "c": {"text": "Анализирую, что понравилось", "scores": {"OBSERVER": 2}},
            "d": {"text": "Уже думаю, что попробовать в следующий раз", "scores": {"PLAYER": 2}}
        }
    },
    {
        "id": "s1_5",
        "text": "В постели вы чаще:",
        "block": "temperament",
        "options": {
            "a": {"text": "Беру инициативу", "scores": {"PREDATOR": 2}},
            "b": {"text": "Создаю атмосферу", "scores": {"ARTIST": 2}},
            "c": {"text": "Следую за партнёром", "scores": {"OBSERVER": 1}},
            "d": {"text": "Предлагаю поиграть", "scores": {"PLAYER": 2}}
        }
    },
    {
        "id": "s1_6",
        "text": "Что для вас важнее?",
        "block": "temperament",
        "options": {
            "a": {"text": "Достичь цели (оргазма)", "scores": {"PREDATOR": 2}},
            "b": {"text": "Прожить процесс", "scores": {"ARTIST": 2}},
            "c": {"text": "Понять партнёра", "scores": {"OBSERVER": 2}},
            "d": {"text": "Получить удовольствие", "scores": {"PLAYER": 1}}
        }
    },
    {
        "id": "s1_7",
        "text": "Как вы относитесь к импровизации?",
        "block": "temperament",
        "options": {
            "a": {"text": "Люблю, когда всё по плану", "scores": {"PREDATOR": 1}},
            "b": {"text": "Люблю творить на ходу", "scores": {"ARTIST": 2}},
            "c": {"text": "Наблюдаю и подхватываю", "scores": {"OBSERVER": 2}},
            "d": {"text": "Импровизация — моё всё", "scores": {"PLAYER": 2}}
        }
    },
    {
        "id": "s1_8",
        "text": "Ваш сексуальный девиз:",
        "block": "temperament",
        "options": {
            "a": {"text": "«Лучший секс — тот, где я веду»", "scores": {"PREDATOR": 2}},
            "b": {"text": "«Главное — красота момента»", "scores": {"ARTIST": 2}},
            "c": {"text": "«Важно чувствовать партнёра»", "scores": {"OBSERVER": 2}},
            "d": {"text": "«Каждый раз как в первый»", "scores": {"PLAYER": 2}}
        }
    },

    # БЛОК 2: ФЕТИШИ (вопросы 8-15)
    {
        "id": "s2_1",
        "text": "Что вас неожиданно заводит?",
        "block": "fetishes",
        "options": {
            "a": {"text": "Запахи (пот, духи, тело)", "scores": {"SMELL": 2}},
            "b": {"text": "Материалы (кожа, шёлк, латекс)", "scores": {"MATERIALS": 2}},
            "c": {"text": "Части тела (шея, ступни, руки)", "scores": {"BODY_PARTS": 2}},
            "d": {"text": "Ситуации (риск, место, роль)", "scores": {"SITUATIONS": 2}}
        }
    },
    {
        "id": "s2_2",
        "text": "В порно вы чаще обращаете внимание на:",
        "block": "fetishes",
        "options": {
            "a": {"text": "Звуки и стоны", "scores": {"SMELL": 1, "SOUNDS": 1}},
            "b": {"text": "Одежду и фактуры", "scores": {"MATERIALS": 2}},
            "c": {"text": "Крупные планы частей тела", "scores": {"BODY_PARTS": 2}},
            "d": {"text": "Сюжет и обстановку", "scores": {"SITUATIONS": 2}}
        }
    },
    {
        "id": "s2_3",
        "text": "Что запоминается после секса?",
        "block": "fetishes",
        "options": {
            "a": {"text": "Его/её запах на коже", "scores": {"SMELL": 2}},
            "b": {"text": "Ощущение ткани на теле", "scores": {"MATERIALS": 2}},
            "c": {"text": "Как выглядело тело партнёра", "scores": {"BODY_PARTS": 2}},
            "d": {"text": "Где и как это было", "scores": {"SITUATIONS": 2}}
        }
    },
    {
        "id": "s2_4",
        "text": "Ваши фантазии чаще связаны с:",
        "block": "fetishes",
        "options": {
            "a": {"text": "Конкретным человеком и его запахом", "scores": {"SMELL": 2}},
            "b": {"text": "Определённой одеждой/формой", "scores": {"MATERIALS": 2}},
            "c": {"text": "Особенностями тела", "scores": {"BODY_PARTS": 2}},
            "d": {"text": "Местом или ролью", "scores": {"SITUATIONS": 2}}
        }
    },
    {
        "id": "s2_5",
        "text": "Что вы замечаете в первую очередь в человеке?",
        "block": "fetishes",
        "options": {
            "a": {"text": "Как пахнет", "scores": {"SMELL": 2}},
            "b": {"text": "Во что одет", "scores": {"MATERIALS": 2}},
            "c": {"text": "Его/её шею, губы, руки", "scores": {"BODY_PARTS": 2}},
            "d": {"text": "Как себя ведёт", "scores": {"SITUATIONS": 2}}
        }
    },
    {
        "id": "s2_6",
        "text": "Что для вас эротичнее?",
        "block": "fetishes",
        "options": {
            "a": {"text": "Запах пота после тренировки", "scores": {"SMELL": 2}},
            "b": {"text": "Кожаная куртка или шёлковое бельё", "scores": {"MATERIALS": 2}},
            "c": {"text": "Обнажённая шея или ключицы", "scores": {"BODY_PARTS": 2}},
            "d": {"text": "Сценарий «незнакомцы в лифте»", "scores": {"SITUATIONS": 2}}
        }
    },
    {
        "id": "s2_7",
        "text": "Если бы снимали кино о ваших фантазиях, там было бы много:",
        "block": "fetishes",
        "options": {
            "a": {"text": "Крупных планов нюхающих что-то лиц", "scores": {"SMELL": 2}},
            "b": {"text": "Разных текстур и тканей", "scores": {"MATERIALS": 2}},
            "c": {"text": "Красивых тел и их частей", "scores": {"BODY_PARTS": 2}},
            "d": {"text": "Интригующих локаций и ролей", "scores": {"SITUATIONS": 2}}
        }
    },
    {
        "id": "s2_8",
        "text": "Вам нравится, когда партнёр:",
        "block": "fetishes",
        "options": {
            "a": {"text": "Позволяет вдыхать его/её запах", "scores": {"SMELL": 2}},
            "b": {"text": "Носит что-то особенное", "scores": {"MATERIALS": 2}},
            "c": {"text": "Акцентирует внимание на теле", "scores": {"BODY_PARTS": 2}},
            "d": {"text": "Играет роль или создаёт ситуацию", "scores": {"SITUATIONS": 2}}
        }
    },

    # БЛОК 3: ФОРМАТЫ (вопросы 16-23)
    {
        "id": "s3_1",
        "text": "Как вы относитесь к идее секса с двумя партнёрами?",
        "block": "formats",
        "options": {
            "a": {"text": "Мечтаю об этом", "scores": {"MFM": 3, "FMF": 3}},
            "b": {"text": "Интересно, но страшно", "scores": {"MFM": 2, "FMF": 2}},
            "c": {"text": "Только с любимым человеком", "scores": {"MONO": 2}},
            "d": {"text": "Категорически нет", "scores": {"TRADITIONAL": 2}}
        }
    },
    {
        "id": "s3_2",
        "text": "Что думаете о свинг-вечеринках?",
        "block": "formats",
        "options": {
            "a": {"text": "Хочу попробовать", "scores": {"SWING": 3}},
            "b": {"text": "Посмотреть бы со стороны", "scores": {"VOYEURISM": 2}},
            "c": {"text": "Не моё, но не осуждаю", "scores": {"MONO": 1}},
            "d": {"text": "Противно даже думать", "scores": {"TRADITIONAL": 2}}
        }
    },
    {
        "id": "s3_3",
        "text": "Хотели бы вы попробовать BDSM-практики?",
        "block": "formats",
        "options": {
            "a": {"text": "Да, хочу быть доминантом", "scores": {"BDSM_DOM": 2}},
            "b": {"text": "Да, хочу быть подчинённым", "scores": {"BDSM_SUB": 2}},
            "c": {"text": "Лёгкие игры интересуют", "scores": {"BDSM_LIGHT": 2}},
            "d": {"text": "Не интересно", "scores": {"TRADITIONAL": 1}}
        }
    },
    {
        "id": "s3_4",
        "text": "Как вы относитесь к ролевым играм?",
        "block": "formats",
        "options": {
            "a": {"text": "Обожаю, много сценариев", "scores": {"ROLES": 2}},
            "b": {"text": "Иногда можно", "scores": {"ROLES": 1}},
            "c": {"text": "Только если партнёр хочет", "scores": {"ADAPTIVE": 1}},
            "d": {"text": "Не понимаю этого", "scores": {"TRADITIONAL": 2}}
        }
    },
    {
        "id": "s3_5",
        "text": "Что скажете о сексе в публичных местах (риск)?",
        "block": "formats",
        "options": {
            "a": {"text": "Уже пробовал(а)", "scores": {"RISK": 2}},
            "b": {"text": "Хочу попробовать", "scores": {"RISK": 2}},
            "c": {"text": "Страшно, но интересно", "scores": {"RISK": 1}},
            "d": {"text": "Не нужно, спасибо", "scores": {"TRADITIONAL": 1}}
        }
    },
    {
        "id": "s3_6",
        "text": "Ваше отношение к секс-игрушкам в паре?",
        "block": "formats",
        "options": {
            "a": {"text": "У нас целая коллекция", "scores": {"TOYS": 2}},
            "b": {"text": "Используем иногда", "scores": {"TOYS": 1}},
            "c": {"text": "Хотели бы попробовать", "scores": {"TOYS": 1}},
            "d": {"text": "Нам и так хорошо", "scores": {"TRADITIONAL": 1}}
        }
    },
    {
        "id": "s3_7",
        "text": "Хотели бы вы снимать секс на видео?",
        "block": "formats",
        "options": {
            "a": {"text": "Да, это заводит", "scores": {"VIDEO": 2}},
            "b": {"text": "Можно попробовать", "scores": {"VIDEO": 1}},
            "c": {"text": "Только для себя", "scores": {"VIDEO": 1}},
            "d": {"text": "Ни в коем случае", "scores": {"TRADITIONAL": 2}}
        }
    },
    {
        "id": "s3_8",
        "text": "Как вы относитесь к виртуальному сексу (чат, камеры)?",
        "block": "formats",
        "options": {
            "a": {"text": "Возбуждает", "scores": {"VIRTUAL": 2}},
            "b": {"text": "Иногда практикую", "scores": {"VIRTUAL": 1}},
            "c": {"text": "Не заменяет реальность", "scores": {"TRADITIONAL": 1}},
            "d": {"text": "Не моё", "scores": {"TRADITIONAL": 1}}
        }
    }
]
