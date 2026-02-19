"""
Variatica Bot - Telegram бот для определения жизненной стратегии
Основан на теории Вариатики: 4 нарратива × 6 уровней = 24 архетипа
"""

import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Загружаем переменные окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# ==================== ДАННЫЕ ====================

# Блок 1: 8 вопросов для определения нарратива (метод исключения)
QUESTIONS_BLOCK1 = [
    {
        "text": "Что для тебя важнее в жизни?",
        "options": {
            "А": {"text": "Быть главным, чтобы меня уважали", "exclude": "ЧВ"},
            "Б": {"text": "Создать что-то полезное своими руками", "exclude": "СБ"},
            "В": {"text": "Понять, как устроен этот мир", "exclude": "ТФ"},
            "Г": {"text": "Быть в центре внимания", "exclude": "УБ"}
        }
    },
    {
        "text": "Чем ты любишь заниматься в свободное время?",
        "options": {
            "А": {"text": "Спорт, единоборства, активный отдых", "exclude": "ЧВ"},
            "Б": {"text": "Работать, мастерить, ремонтировать", "exclude": "СБ"},
            "В": {"text": "Читать, учиться, решать задачи", "exclude": "ТФ"},
            "Г": {"text": "Тусоваться, ходить на мероприятия", "exclude": "УБ"}
        }
    },
    {
        "text": "Какая фраза про тебя?",
        "options": {
            "А": {"text": "«Лучше быть сильным, чем правым»", "exclude": "ЧВ"},
            "Б": {"text": "«Без труда не выловишь и рыбку»", "exclude": "СБ"},
            "В": {"text": "«Век живи — век учись»", "exclude": "ТФ"},
            "Г": {"text": "«Главное, чтобы запомнили»", "exclude": "УБ"}
        }
    },
    {
        "text": "Что тебя бесит больше всего?",
        "options": {
            "А": {"text": "Когда меня не уважают, считают слабаком", "exclude": "ЧВ"},
            "Б": {"text": "Когда я работаю, а другие халявят", "exclude": "СБ"},
            "В": {"text": "Когда люди несут чушь и не слушают", "exclude": "ТФ"},
            "Г": {"text": "Когда меня игнорируют, не замечают", "exclude": "УБ"}
        }
    },
    {
        "text": "Кем ты восхищаешься?",
        "options": {
            "А": {"text": "Лидерами, которые умеют подчинять", "exclude": "ЧВ"},
            "Б": {"text": "Мастерами, которые создают шедевры", "exclude": "СБ"},
            "В": {"text": "Гениями, которые сделали открытия", "exclude": "ТФ"},
            "Г": {"text": "Звёздами, которых все знают", "exclude": "УБ"}
        }
    },
    {
        "text": "Куда бы потратил крупную сумму?",
        "options": {
            "А": {"text": "На крутую машину, часы, статусные вещи", "exclude": "ЧВ"},
            "Б": {"text": "На инструменты, оборудование, свой цех", "exclude": "СБ"},
            "В": {"text": "На обучение, книги, исследования", "exclude": "ТФ"},
            "Г": {"text": "На раскрутку имени, пиар, вечеринку", "exclude": "УБ"}
        }
    },
    {
        "text": "В компании незнакомых ты сразу...",
        "options": {
            "А": {"text": "Оцениваешь, кто тут главный", "exclude": "ЧВ"},
            "Б": {"text": "Ищешь, с кем можно по делу поговорить", "exclude": "СБ"},
            "В": {"text": "Слушаешь, кто говорит умные вещи", "exclude": "ТФ"},
            "Г": {"text": "Смотришь, кто в центре внимания", "exclude": "УБ"}
        }
    },
    {
        "text": "Чего ты боишься больше всего?",
        "options": {
            "А": {"text": "Потерять авторитет, стать никем", "exclude": "ЧВ"},
            "Б": {"text": "Остаться без работы, без денег", "exclude": "СБ"},
            "В": {"text": "Показаться глупым, некомпетентным", "exclude": "ТФ"},
            "Г": {"text": "Стать незаметным, скучным, серым", "exclude": "УБ"}
        }
    }
]

# Блок 2: Вопросы для каждого нарратива
QUESTIONS_BLOCK2 = {
    "СБ": [  # Силовой
        {
            "text": "Как часто ты занимаешься спортом?",
            "options": {
                "1": {"text": "Вообще не занимаюсь", "scores": {"strength": 1}},
                "2": {"text": "Иногда, без фанатизма", "scores": {"strength": 3}},
                "3": {"text": "Регулярно 3-4 раза в неделю", "scores": {"strength": 7}},
                "4": {"text": "Живу спортом, соревнуюсь", "scores": {"strength": 10}}
            }
        },
        {
            "text": "Был ли ты в драке за последний год?",
            "options": {
                "1": {"text": "Нет, избегаю конфликтов", "scores": {"level": 1, "strength": 2}},
                "2": {"text": "Нет, но провоцировали — ушёл", "scores": {"level": 4, "strength": 4}},
                "3": {"text": "Был один раз, отстаивал себя", "scores": {"level": 5, "strength": 6}},
                "4": {"text": "Бывало, участвую в разборках", "scores": {"level": 6, "strength": 8}}
            }
        },
        {
            "text": "В компании друзей ты обычно...",
            "options": {
                "1": {"text": "Молчу, поддакиваю", "scores": {"status": 2}},
                "2": {"text": "Поддерживаю разговор", "scores": {"status": 4}},
                "3": {"text": "Предлагаю темы, меня слушают", "scores": {"status": 7}},
                "4": {"text": "Я главный, без меня не решают", "scores": {"status": 10}}
            }
        },
        {
            "text": "Если конфликт с незнакомцем, ты...",
            "options": {
                "1": {"text": "Извинюсь, даже если не прав", "scores": {"strategy": 1}},
                "2": {"text": "Попробую договориться", "scores": {"strategy": 2}},
                "3": {"text": "Замру, буду ждать", "scores": {"strategy": 3}},
                "4": {"text": "Уйду, чтобы не связываться", "scores": {"strategy": 4}},
                "5": {"text": "Позову друзей на помощь", "scores": {"strategy": 5}},
                "6": {"text": "Пойду в разборку", "scores": {"strategy": 6}}
            }
        },
        {
            "text": "Сколько людей, на которых ты можешь положиться?",
            "options": {
                "1": {"text": "Никого, я один", "scores": {"connections": 2}},
                "2": {"text": "1-2 близких друга", "scores": {"connections": 4}},
                "3": {"text": "Несколько человек плюс знакомые", "scores": {"connections": 7}},
                "4": {"text": "Целая команда, клан", "scores": {"connections": 10}}
            }
        },
        {
            "text": "Как часто носишь с собой что-то, что может быть оружием?",
            "options": {
                "1": {"text": "Никогда, не думал об этом", "scores": {"danger": 2}},
                "2": {"text": "Только в опасное место", "scores": {"danger": 4}},
                "3": {"text": "Часто, на всякий случай", "scores": {"danger": 7}},
                "4": {"text": "Всегда, это часть меня", "scores": {"danger": 10}}
            }
        }
    ],
    "ТФ": [  # Трудовой
        {
            "text": "Во сколько ты встаёшь в будни?",
            "options": {
                "1": {"text": "После 10, могу и позже", "scores": {"workaholic": 2}},
                "2": {"text": "В 8-9, как все", "scores": {"workaholic": 4}},
                "3": {"text": "В 6-7, чтобы успеть", "scores": {"workaholic": 7}},
                "4": {"text": "В 4-5, так каждый день", "scores": {"workaholic": 10}}
            }
        },
        {
            "text": "Что чувствуешь в воскресенье вечером?",
            "options": {
                "1": {"text": "Ужас, завтра на работу", "scores": {"attitude": 2}},
                "2": {"text": "Спокойно, работа есть работа", "scores": {"attitude": 4}},
                "3": {"text": "Тянет, соскучился по делу", "scores": {"attitude": 7}},
                "4": {"text": "Нет разницы, работаю и в выходные", "scores": {"attitude": 10}}
            }
        },
        {
            "text": "Сколько у тебя источников дохода?",
            "options": {
                "1": {"text": "Один — зарплата", "scores": {"level": 2}},
                "2": {"text": "Один, но я сам себе хозяин", "scores": {"level": 4}},
                "3": {"text": "Два-три, включая пассивные", "scores": {"level": 5}},
                "4": {"text": "Много, включая бизнес", "scores": {"level": 6}}
            }
        },
        {
            "text": "Ты когда-нибудь нанимал людей?",
            "options": {
                "1": {"text": "Нет, меня самого нанимают", "scores": {"level": 2}},
                "2": {"text": "Нет, работаю один", "scores": {"level": 4}},
                "3": {"text": "Да, иногда на разовые работы", "scores": {"level": 5}},
                "4": {"text": "Да, у меня постоянно работают", "scores": {"level": 6}}
            }
        },
        {
            "text": "Что купил в прошлом месяце самое дорогое?",
            "options": {
                "1": {"text": "Еду, мелочи", "scores": {"money": 2}},
                "2": {"text": "Одежду, технику", "scores": {"money": 4}},
                "3": {"text": "Инструмент для работы", "scores": {"money": 7}},
                "4": {"text": "Недвижимость, машину", "scores": {"money": 10}}
            }
        },
        {
            "text": "Если потеряешь работу, сколько продержишься?",
            "options": {
                "1": {"text": "Неделя, потом голод", "scores": {"savings": 2}},
                "2": {"text": "Месяц-два, есть заначка", "scores": {"savings": 4}},
                "3": {"text": "Полгода-год", "scores": {"savings": 7}},
                "4": {"text": "Мне не страшно, есть пассив", "scores": {"savings": 10}}
            }
        }
    ],
    "УБ": [  # Умственный
        {
            "text": "Сколько времени надо, чтобы собрать кубик Рубика?",
            "options": {
                "1": {"text": "Не умею", "scores": {"speed": 1}},
                "2": {"text": "Могу собрать одну сторону", "scores": {"speed": 3}},
                "3": {"text": "По инструкции за 5-10 минут", "scores": {"speed": 5}},
                "4": {"text": "Собираю сам без инструкции", "scores": {"speed": 7}},
                "5": {"text": "Меньше минуты, знаю алгоритмы", "scores": {"speed": 10}}
            }
        },
        {
            "text": "Какую книгу прочитал последней?",
            "options": {
                "1": {"text": "Не читаю книги", "scores": {"depth": 1}},
                "2": {"text": "Лёгкое чтиво, детектив", "scores": {"depth": 3}},
                "3": {"text": "Научно-популярная", "scores": {"depth": 6}},
                "4": {"text": "Серьёзная литература", "scores": {"depth": 8}},
                "5": {"text": "Научная, специализированная", "scores": {"depth": 10}}
            }
        },
        {
            "text": "Писал ли статьи длиннее 5000 знаков?",
            "options": {
                "1": {"text": "Нет", "scores": {"creativity": 1}},
                "2": {"text": "Посты в соцсетях", "scores": {"creativity": 3}},
                "3": {"text": "Статьи для работы", "scores": {"creativity": 5}},
                "4": {"text": "Научные статьи", "scores": {"creativity": 8}},
                "5": {"text": "Книги, исследования", "scores": {"creativity": 10}}
            }
        },
        {
            "text": "Сколько языков (иностранных/программирования) знаешь?",
            "options": {
                "1": {"text": "Ни одного или один", "scores": {"education": 2}},
                "2": {"text": "Один на базовом", "scores": {"education": 4}},
                "3": {"text": "Один-два свободно", "scores": {"education": 6}},
                "4": {"text": "Три-четыре", "scores": {"education": 8}},
                "5": {"text": "Много, я полиглот", "scores": {"education": 10}}
            }
        },
        {
            "text": "Как быстро засыпаешь над сложной задачей?",
            "options": {
                "1": {"text": "Сразу отключаюсь", "scores": {"thinking": 1}},
                "2": {"text": "Думаю немного", "scores": {"thinking": 3}},
                "3": {"text": "Могу час ворочаться", "scores": {"thinking": 6}},
                "4": {"text": "Часа два, пока не решу", "scores": {"thinking": 8}},
                "5": {"text": "Не усну, пока не найду решение", "scores": {"thinking": 10}}
            }
        },
        {
            "text": "Помнишь ли свой последний экзамен/тест?",
            "options": {
                "1": {"text": "С трудом помню вчера", "scores": {"memory": 1}},
                "2": {"text": "Помню примерно", "scores": {"memory": 3}},
                "3": {"text": "Помню основные вопросы", "scores": {"memory": 5}},
                "4": {"text": "Помню почти всё", "scores": {"memory": 7}},
                "5": {"text": "Помню даже одежду", "scores": {"memory": 10}}
            }
        }
    ],
    "ЧВ": [  # Артистический
        {
            "text": "Сколько у тебя подписчиков в соцсетях?",
            "options": {
                "1": {"text": "Нет аккаунтов", "scores": {"fame": 1}},
                "2": {"text": "До 500 — друзья", "scores": {"fame": 3}},
                "3": {"text": "500-5000", "scores": {"fame": 5}},
                "4": {"text": "5000-50000", "scores": {"fame": 7}},
                "5": {"text": "Более 50000", "scores": {"fame": 10}}
            }
        },
        {
            "text": "Как часто узнают на улице?",
            "options": {
                "1": {"text": "Никогда", "scores": {"recognition": 1}},
                "2": {"text": "Редко, раз в год", "scores": {"recognition": 3}},
                "3": {"text": "Пару раз в месяц", "scores": {"recognition": 5}},
                "4": {"text": "Пару раз в неделю", "scores": {"recognition": 7}},
                "5": {"text": "Каждый день", "scores": {"recognition": 10}}
            }
        },
        {
            "text": "Сколько мероприятий посетил за месяц?",
            "options": {
                "1": {"text": "0, я домосед", "scores": {"involvement": 1}},
                "2": {"text": "1-2", "scores": {"involvement": 3}},
                "3": {"text": "3-5", "scores": {"involvement": 5}},
                "4": {"text": "6-10", "scores": {"involvement": 7}},
                "5": {"text": "Более 10", "scores": {"involvement": 10}}
            }
        },
        {
            "text": "Сколько полезных людей в записной книжке?",
            "options": {
                "1": {"text": "Никого", "scores": {"connections": 1}},
                "2": {"text": "10-20 знакомых", "scores": {"connections": 3}},
                "3": {"text": "50-100", "scores": {"connections": 5}},
                "4": {"text": "100-500", "scores": {"connections": 7}},
                "5": {"text": "Более 500", "scores": {"connections": 10}}
            }
        },
        {
            "text": "Снимался ли в видео, давал интервью?",
            "options": {
                "1": {"text": "Нет, боюсь", "scores": {"level": 1}},
                "2": {"text": "Пару раз для галочки", "scores": {"level": 2}},
                "3": {"text": "Регулярно снимаю сторис", "scores": {"level": 3}},
                "4": {"text": "Веду блог, канал", "scores": {"level": 4}},
                "5": {"text": "Я медийное лицо", "scores": {"level": 5}}
            }
        },
        {
            "text": "Сколько времени в телефоне (не по работе)?",
            "options": {
                "1": {"text": "Меньше часа", "scores": {"consumption": 1}},
                "2": {"text": "1-3 часа", "scores": {"consumption": 3}},
                "3": {"text": "3-6 часов", "scores": {"consumption": 5}},
                "4": {"text": "6-9 часов", "scores": {"consumption": 7}},
                "5": {"text": "Более 9 часов", "scores": {"consumption": 10}}
            }
        }
    ]
}

# Матрица ролей (24 стратегии)
ROLES_MATRIX = {
    "СБ": {
        1: "БОМЖ",
        2: "ШНЫРЬ",
        3: "СМОТРЯЩИЙ",
        4: "ВОЛЬНЫЙ СТРЕЛОК",
        5: "РАЗВОДЯЩИЙ",
        6: "ПАХАН"
    },
    "ТФ": {
        1: "ИЖДИВЕНЕЦ",
        2: "НАЁМНЫЙ РАБОЧИЙ",
        3: "АРЕНДОДАТЕЛЬ",
        4: "САМОЗАНЯТЫЙ",
        5: "СЕЛЛЕР",
        6: "ПРОИЗВОДИТЕЛЬ"
    },
    "УБ": {
        1: "ЛЖЕЭКСПЕРТ",
        2: "НАЁМНЫЙ СПЕЦИАЛИСТ",
        3: "НАСТАВНИК",
        4: "ИССЛЕДОВАТЕЛЬ",
        5: "ПРОДАВЕЦ ЗНАНИЙ",
        6: "ТЕОРЕТИК"
    },
    "ЧВ": {
        1: "ТУСОВЩИК",
        2: "ПРОЕКТНЫЙ",
        3: "АМБАССАДОР",
        4: "АРТИСТ",
        5: "АГЕНТ",
        6: "МЕДИАМАГНАТ"
    }
}

# Описания стратегий (короткие, для Telegram)
DESCRIPTIONS = {
    "СБ": {
        1: "Ты вне иерархии. Тебя нет в раскладе. Ты просто существуешь, ни на что не влияя. Твоя стратегия — быть незаметным, потому что любое внимание к тебе может быть опасным.",
        2: "Ты обслуживаешь тех, кто сильнее. Твоя роль — быть полезным, бегать по поручениям, выполнять приказы. Ты не принимаешь решений, но ты в безопасности, пока нужен.",
        3: "Ты следишь за порядком на своей территории. У тебя есть зона ответственности, где ты главный. Ты не лезешь наверх, но контролируешь то, что доверено.",
        4: "Ты сам по себе. Ты ничей. Ты не строишься в иерархию и не подчиняешься. Тебя уважают, потому что ты опасен, но ты один — и это твоя сила и слабость.",
        5: "Ты решаешь вопросы за процент. Ты знаешь нужных людей и умеешь их сводить. Ты не применяешь силу — ты торгуешь связями. Ты — мост между теми, у кого есть власть, и теми, кому она нужна.",
        6: "Ты наверху. Ты устанавливаешь правила. Твоё слово — закон. Ты прошёл все круги и знаешь цену людям. Ты — авторитет, пахан, хозяин положения."
    },
    "ТФ": {
        1: "Ты живёшь за счёт других. Государство, родители, партнёр — кто-то обеспечивает твоё существование. Твоя стратегия — быть, а не делать. Вопрос только в том, как долго это продлится.",
        2: "Ты продаёшь своё время и руки за зарплату. Ты приходишь, делаешь, получаешь, уходишь. Твоя задача — не высовываться и не брать лишнего. Ты — надёжный винтик в большой машине.",
        3: "Ты не работаешь руками — ты работаешь имуществом. Квартиры, инструменты, оборудование — ты сдаёшь то, чем владеешь. Твой доход идёт к тебе без твоего участия.",
        4: "Ты работаешь на себя. Фриланс, шабашки, ИП без сотрудников. Ты сам ищешь заказы, сам делаешь, сам отвечаешь. Свобода для тебя важнее стабильности.",
        5: "Ты продаёшь чужой товар. Маркетплейсы, перекупы, дистрибуция. Ты не производишь — ты находишь того, кто произвёл, и того, кто купит. Твоя магия — убеждение.",
        6: "Ты организовал производство. У тебя есть люди, станки, цеха. Ты даёшь работу другим. Ты создаёшь продукт, который покупают. Ты — хозяин, работодатель, создатель."
    },
    "УБ": {
        1: "Ты продаёшь воздух. Ты говоришь красиво и уверенно, но за этим ничего нет. Ты научился создавать видимость понимания. Главное — чтобы не задавали правильных вопросов.",
        2: "Ты продаёшь свои знания за зарплату. Ты компетентен, но не создаёшь нового — ты применяешь готовое. Ты — надёжный специалист, но не творец.",
        3: "Ты передаёшь знания другим. Учитель, наставник, преподаватель. Ты не создаёшь нового, но помогаешь другим понять старое. Твоя сила — в терпении и умении объяснять.",
        4: "Ты создаёшь новое. Ты исследователь, который идёт туда, куда никто не ходил. Ты независим, но твоя свобода — это ответственность. Никто не оценит твой труд, пока ты не покажешь результат.",
        5: "Ты продаёшь чужие знания. Издатель, популяризатор, организатор курсов. Ты упаковываешь идеи в красивые обёртки и находишь для них покупателей.",
        6: "Ты создал систему. Твои работы цитируют, по твоим книгам учат. Ты оставил след в мире знаний. Ты — теоретик, академик, создатель парадигмы."
    },
    "ЧВ": {
        1: "Ты всегда там, где движуха. Ты ходишь на тусовки, знаешь всех в лицо, но тебя никто не знает. Ты — вечный гость, но не хозяин. Ты потребляешь чужое внимание, не создавая своего.",
        2: "Ты работаешь в чужих проектах. Ты талантлив, но твой талант работает на других. Ты — невидимый герой, чьё имя не в титрах.",
        3: "Ты — лицо бренда. Твоё имя работает на других. Ты популярен, но ты не свободен — ты должен соответствовать. Ты — посол, а не создатель.",
        4: "Ты создаёшь своё имя. Блогер, артист, творец. Ты сам проект. Ты свободен, но твоя свобода — это бесконечная работа. Ты зависишь от внимания, как от воздуха.",
        5: "Ты создаёшь тех, кто создаёт контент. Продюсер, агент, менеджер. Ты не на сцене, но без тебя сцены бы не было. Ты — закулисный игрок.",
        6: "Ты владеешь платформой. У тебя канал, студия, СМИ. Ты даёшь другим возможность быть услышанными. Ты — хозяин эфира, медиамагнат."
    }
}

# Названия нарративов
NARRATIVE_NAMES = {
    "СБ": "СИЛЫ",
    "ТФ": "ТРУДА",
    "УБ": "ЗНАНИЙ",
    "ЧВ": "ВНИМАНИЯ"
}

# ==================== СОСТОЯНИЯ ====================

class UserState(StatesGroup):
    block1_question = State()  # Какой вопрос из блока 1 сейчас
    block1_answers = State()   # Список исключённых нарративов
    narrative = State()        # Определённый нарратив
    block2_question = State()  # Какой вопрос из блока 2
    block2_data = State()      # Собранные данные (уровень, ресурсы)
    block2_answers = State()   # Счётчик ответов

# ==================== ХЕНДЛЕРЫ ====================

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    """Приветствие и начало теста"""
    await message.answer(
        "🧠 *Вариатика: твоя жизненная стратегия*\n\n"
        "Я задам 8 вопросов, чтобы понять, в каком мире ты живёшь.\n"
        "Потом ещё несколько — чтобы определить твою роль.\n\n"
        "Готов? Поехали!",
        parse_mode="Markdown"
    )
    
    # Инициализация состояний
    await UserState.block1_question.set()
    await UserState.block1_answers.set(0)  # Счётчик вопросов
    
    # Задаём первый вопрос
    await ask_block1_question(message.from_user.id, 0)

async def ask_block1_question(user_id, question_index):
    """Задать вопрос из блока 1"""
    state = dp.current_state(user=user_id)
    
    q = QUESTIONS_BLOCK1[question_index]
    
    # Создаём клавиатуру
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for key, value in q["options"].items():
        keyboard.add(types.InlineKeyboardButton(
            text=f"{key}. {value['text'][:30]}...",
            callback_data=f"b1_{question_index}_{key}"
        ))
    
    await bot.send_message(
        user_id,
        f"*Вопрос {question_index+1}/8:*\n{q['text']}",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data.startswith('b1_'), state=UserState.block1_question)
async def process_block1_answer(callback: types.CallbackQuery, state: FSMContext):
    """Обработка ответа на вопрос из блока 1"""
    await callback.answer()
    
    # Парсим callback_data
    _, q_index_str, answer_key = callback.data.split('_')
    q_index = int(q_index_str)
    
    # Получаем данные состояния
    data = await state.get_data()
    answers_count = data.get('block1_answers', 0)
    
    # Получаем исключаемый нарратив
    excluded = QUESTIONS_BLOCK1[q_index]["options"][answer_key]["exclude"]
    
    # Сохраняем исключение (можно в массив)
    excludes = data.get('excludes', [])
    excludes.append(excluded)
    await state.update_data(excludes=excludes)
    
    # Следующий вопрос или переход к блоку 2
    if q_index + 1 < len(QUESTIONS_BLOCK1):
        # Ещё есть вопросы
        await ask_block1_question(callback.from_user.id, q_index + 1)
    else:
        # Вопросы кончились - определяем нарратив
        await determine_narrative(callback.from_user.id, state)

async def determine_narrative(user_id, state: FSMContext):
    """Определение нарратива методом исключения"""
    data = await state.get_data()
    excludes = data.get('excludes', [])
    
    # Считаем, сколько раз исключали каждый нарратив
    counts = {"СБ": 0, "ТФ": 0, "УБ": 0, "ЧВ": 0}
    for ex in excludes:
        counts[ex] += 1
    
    # Находим наименее исключаемый (или не исключаемый)
    # Сортируем по возрастанию исключений
    sorted_narratives = sorted(counts.items(), key=lambda x: x[1])
    
    if sorted_narratives[0][1] < sorted_narratives[1][1]:
        # Чёткий лидер
        narrative = sorted_narratives[0][0]
        second_narrative = None
    else:
        # Возможно два с одинаковым счётом
        # Берём первый и второй, но первый как основной
        narrative = sorted_narratives[0][0]
        second_narrative = sorted_narratives[1][0]
    
    # Сохраняем нарратив
    await state.update_data(
        narrative=narrative,
        second_narrative=second_narrative,
        block2_question=0,
        block2_answers=[],
        resources={}
    )
    
    # Переходим к блоку 2
    await UserState.block2_question.set()
    
    await bot.send_message(
        user_id,
        f"*Определено:* твой мир — *{NARRATIVE_NAMES[narrative]}*.\n\n"
        f"Теперь {len(QUESTIONS_BLOCK2[narrative])} вопросов, чтобы понять твою роль.",
        parse_mode="Markdown"
    )
    
    # Задаём первый вопрос блока 2
    await ask_block2_question(user_id, 0, narrative, state)

async def ask_block2_question(user_id, q_index, narrative, state):
    """Задать вопрос из блока 2"""
    q = QUESTIONS_BLOCK2[narrative][q_index]
    
    # Создаём клавиатуру
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for key, value in q["options"].items():
        # Укорачиваем текст для кнопок
        btn_text = value['text']
        if len(btn_text) > 30:
            btn_text = btn_text[:28] + ".."
        keyboard.add(types.InlineKeyboardButton(
            text=btn_text,
            callback_data=f"b2_{q_index}_{key}"
        ))
    
    await bot.send_message(
        user_id,
        f"*Вопрос {q_index+1}/{len(QUESTIONS_BLOCK2[narrative])}:*\n{q['text']}",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data.startswith('b2_'), state=UserState.block2_question)
async def process_block2_answer(callback: types.CallbackQuery, state: FSMContext):
    """Обработка ответа на вопрос из блока 2"""
    await callback.answer()
    
    # Парсим callback_data
    _, q_index_str, answer_key = callback.data.split('_')
    q_index = int(q_index_str)
    
    # Получаем данные состояния
    data = await state.get_data()
    narrative = data.get('narrative')
    
    # Получаем баллы за ответ
    q = QUESTIONS_BLOCK2[narrative][q_index]
    scores = q["options"][answer_key]["scores"]
    
    # Сохраняем ответ
    answers = data.get('block2_answers', [])
    answers.append({
        "q_index": q_index,
        "answer": answer_key,
        "scores": scores
    })
    
    # Обновляем ресурсы
    resources = data.get('resources', {})
    for key, value in scores.items():
        if key in resources:
            resources[key] = (resources[key] + value) / 2  # Среднее
        else:
            resources[key] = value
    
    await state.update_data(block2_answers=answers, resources=resources)
    
    # Следующий вопрос или результат
    if q_index + 1 < len(QUESTIONS_BLOCK2[narrative]):
        # Ещё есть вопросы
        await ask_block2_question(callback.from_user.id, q_index + 1, narrative, state)
    else:
        # Вопросы кончились - показываем результат
        await show_result(callback.from_user.id, state)

async def show_result(user_id, state: FSMContext):
    """Показывает финальный фокус"""
    data = await state.get_data()
    narrative = data.get('narrative')
    second_narrative = data.get('second_narrative')
    resources = data.get('resources', {})
    answers = data.get('block2_answers', [])
    
    # Определяем уровень
    # Ищем прямые указания уровня в ответах
    level_from_answers = None
    for ans in answers:
        if 'level' in ans['scores']:
            level_from_answers = ans['scores']['level']
            break
    
    if level_from_answers:
        level = level_from_answers
    else:
        # Вычисляем средний уровень по ресурсам
        # По умолчанию 3
        level = 3
    
    # Корректировка по ресурсам (упрощённо)
    if 'strength' in resources and resources['strength'] > 8:
        level = min(6, level + 1)
    if 'money' in resources and resources['money'] > 8:
        level = min(6, level + 1)
    if 'fame' in resources and resources['fame'] > 8:
        level = min(6, level + 1)
    
    role = ROLES_MATRIX[narrative][level]
    description = DESCRIPTIONS[narrative][level]
    
    # Формируем результат
    result = f"🎯 *Твой фокус:*\n\n"
    result += f"Ты — *{role}* в мире *{NARRATIVE_NAMES[narrative]}*.\n\n"
    result += f"{description}\n\n"
    
    if second_narrative:
        result += f"*При этом* ты используешь мир *{NARRATIVE_NAMES[second_narrative]}* как средство.\n\n"
    
    # Следующий уровень
    if level < 6:
        next_role = ROLES_MATRIX[narrative][level + 1]
        result += f"*Если хочешь расти:* твой следующий уровень — *{next_role}*.\n"
    
    # Кнопка для перезапуска
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔄 Пройти заново", callback_data="restart"))
    
    await bot.send_message(
        user_id,
        result,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    
    # Сброс состояния
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'restart')
async def restart_test(callback: types.CallbackQuery):
    """Перезапуск теста"""
    await callback.answer()
    await cmd_start(callback.message)

# ==================== ЗАПУСК ====================

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
