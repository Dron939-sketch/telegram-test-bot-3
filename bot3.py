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
            "🔱": {"text": "Быть главным, чтобы меня уважали", "exclude": "ЧВ"},
            "🔨": {"text": "Создать что-то полезное своими руками", "exclude": "СБ"},
            "📚": {"text": "Понять, как устроен этот мир", "exclude": "ТФ"},
            "🎭": {"text": "Быть в центре внимания", "exclude": "УБ"}
        }
    },
    {
        "text": "Чем ты любишь заниматься в свободное время?",
        "options": {
            "🥊": {"text": "Спорт, единоборства, активный отдых", "exclude": "ЧВ"},
            "🛠️": {"text": "Работать, мастерить, ремонтировать", "exclude": "СБ"},
            "📖": {"text": "Читать, учиться, решать задачи", "exclude": "ТФ"},
            "🎉": {"text": "Тусоваться, ходить на мероприятия", "exclude": "УБ"}
        }
    },
    {
        "text": "Какая фраза про тебя?",
        "options": {
            "⚔️": {"text": "«Лучше быть сильным, чем правым»", "exclude": "ЧВ"},
            "⚙️": {"text": "«Без труда не выловишь и рыбку»", "exclude": "СБ"},
            "🔬": {"text": "«Век живи — век учись»", "exclude": "ТФ"},
            "🎪": {"text": "«Главное, чтобы запомнили»", "exclude": "УБ"}
        }
    },
    {
        "text": "Что тебя бесит больше всего?",
        "options": {
            "👑": {"text": "Когда меня не уважают, считают слабаком", "exclude": "ЧВ"},
            "⏰": {"text": "Когда я работаю, а другие халявят", "exclude": "СБ"},
            "🤯": {"text": "Когда люди несут чушь и не слушают", "exclude": "ТФ"},
            "👻": {"text": "Когда меня игнорируют, не замечают", "exclude": "УБ"}
        }
    },
    {
        "text": "Кем ты восхищаешься?",
        "options": {
            "🏛️": {"text": "Лидерами, которые умеют подчинять", "exclude": "ЧВ"},
            "🏗️": {"text": "Мастерами, которые создают шедевры", "exclude": "СБ"},
            "🧠": {"text": "Гениями, которые сделали открытия", "exclude": "ТФ"},
            "🌟": {"text": "Звёздами, которых все знают", "exclude": "УБ"}
        }
    },
    {
        "text": "Куда бы ты потратил крупную сумму?",
        "options": {
            "💎": {"text": "На крутую машину, часы, статусные вещи", "exclude": "ЧВ"},
            "🏭": {"text": "На инструменты, оборудование, свой цех", "exclude": "СБ"},
            "📚": {"text": "На обучение, книги, исследования", "exclude": "ТФ"},
            "📢": {"text": "На раскрутку имени, пиар, вечеринку", "exclude": "УБ"}
        }
    },
    {
        "text": "В компании незнакомых ты сразу...",
        "options": {
            "🦁": {"text": "Оцениваешь, кто тут главный", "exclude": "ЧВ"},
            "🐜": {"text": "Ищешь, с кем можно по делу поговорить", "exclude": "СБ"},
            "🦉": {"text": "Слушаешь, кто говорит умные вещи", "exclude": "ТФ"},
            "🦚": {"text": "Смотришь, кто в центре внимания", "exclude": "УБ"}
        }
    },
    {
        "text": "Чего ты боишься больше всего?",
        "options": {
            "📉": {"text": "Потерять авторитет, стать никем", "exclude": "ЧВ"},
            "💸": {"text": "Остаться без работы, без денег", "exclude": "СБ"},
            "🤦": {"text": "Показаться глупым, некомпетентным", "exclude": "ТФ"},
            "👀": {"text": "Стать незаметным, скучным, серым", "exclude": "УБ"}
        }
    }
]

# Блок 2: 15 универсальных вопросов про ресурсы
QUESTIONS_BLOCK2 = [
    {  # 1. Рост
        "text": "Какой у тебя рост?",
        "type": "physical",
        "options": {
            "1": {"text": "Ниже 165 см", "scores": {"height": 2}},
            "2": {"text": "165-175 см", "scores": {"height": 4}},
            "3": {"text": "175-185 см", "scores": {"height": 6}},
            "4": {"text": "185-195 см", "scores": {"height": 8}},
            "5": {"text": "Выше 195 см", "scores": {"height": 10}}
        }
    },
    {  # 2. Телосложение в 15 лет
        "text": "Каким ты был в 15 лет?",
        "type": "physical",
        "options": {
            "1": {"text": "Очень худым, слабым", "scores": {"build": 2}},
            "2": {"text": "Худощавым", "scores": {"build": 4}},
            "3": {"text": "Нормальным, средним", "scores": {"build": 6}},
            "4": {"text": "Плотным, крепким", "scores": {"build": 8}},
            "5": {"text": "Сильным, меня боялись", "scores": {"build": 10}}
        }
    },
    {  # 3. Здоровье
        "text": "Как часто ты болеешь?",
        "type": "physical",
        "options": {
            "1": {"text": "Постоянно, каждый месяц", "scores": {"health": 2}},
            "2": {"text": "Несколько раз в год", "scores": {"health": 4}},
            "3": {"text": "Раз в год по сезону", "scores": {"health": 6}},
            "4": {"text": "Раз в несколько лет", "scores": {"health": 8}},
            "5": {"text": "Практически никогда", "scores": {"health": 10}}
        }
    },
    {  # 4. Внешность
        "text": "Как ты выглядишь?",
        "type": "physical",
        "options": {
            "1": {"text": "Меня не замечают", "scores": {"attractiveness": 2}},
            "2": {"text": "Обычная внешность", "scores": {"attractiveness": 4}},
            "3": {"text": "Симпатичный, приятный", "scores": {"attractiveness": 6}},
            "4": {"text": "Красивый, привлекаю внимание", "scores": {"attractiveness": 8}},
            "5": {"text": "Модельная внешность", "scores": {"attractiveness": 10}}
        }
    },
    {  # 5. Сила
        "text": "Сколько ты можешь отжаться от пола?",
        "type": "physical",
        "options": {
            "1": {"text": "0-5 раз", "scores": {"strength": 2}},
            "2": {"text": "5-15 раз", "scores": {"strength": 4}},
            "3": {"text": "15-30 раз", "scores": {"strength": 6}},
            "4": {"text": "30-50 раз", "scores": {"strength": 8}},
            "5": {"text": "Больше 50", "scores": {"strength": 10}}
        }
    },
    {  # 6. Школьная успеваемость
        "text": "В школе ты учился...",
        "type": "intellectual",
        "options": {
            "1": {"text": "Еле тянул, двойки", "scores": {"intelligence": 2}},
            "2": {"text": "Тройки, кое-как", "scores": {"intelligence": 4}},
            "3": {"text": "Хорошист, твердая 4", "scores": {"intelligence": 6}},
            "4": {"text": "Отличник, легко давалось", "scores": {"intelligence": 8}},
            "5": {"text": "Гений, олимпиады, скучал", "scores": {"intelligence": 10}}
        }
    },
    {  # 7. Скорость обучения
        "text": "Сколько времени нужно, чтобы выучить 50 иностранных слов?",
        "type": "intellectual",
        "options": {
            "1": {"text": "Неделя и больше", "scores": {"learning_speed": 2}},
            "2": {"text": "Несколько дней", "scores": {"learning_speed": 4}},
            "3": {"text": "Один день", "scores": {"learning_speed": 6}},
            "4": {"text": "Несколько часов", "scores": {"learning_speed": 8}},
            "5": {"text": "Час или меньше", "scores": {"learning_speed": 10}}
        }
    },
    {  # 8. Память на лица
        "text": "Ты хорошо запоминаешь лица и имена?",
        "type": "intellectual",
        "options": {
            "1": {"text": "Постоянно путаю, забываю", "scores": {"memory": 2}},
            "2": {"text": "Запоминаю только близких", "scores": {"memory": 4}},
            "3": {"text": "Запоминаю тех, кто важен", "scores": {"memory": 6}},
            "4": {"text": "Запоминаю большинство", "scores": {"memory": 8}},
            "5": {"text": "Фотографическая память", "scores": {"memory": 10}}
        }
    },
    {  # 9. Креативность
        "text": "Если сломается бытовая техника, ты...",
        "type": "intellectual",
        "options": {
            "1": {"text": "Выброшу и куплю новую", "scores": {"creativity": 2}},
            "2": {"text": "Позову мастера", "scores": {"creativity": 4}},
            "3": {"text": "Попробую починить по инструкции", "scores": {"creativity": 6}},
            "4": {"text": "Разберусь сам и починю", "scores": {"creativity": 8}},
            "5": {"text": "Улучшу, сделаю лучше чем было", "scores": {"creativity": 10}}
        }
    },
    {  # 10. Семья (стартовый капитал)
        "text": "Кем работали твои родители?",
        "type": "social",
        "options": {
            "1": {"text": "Безработные, алкоголики", "scores": {"family": 2}},
            "2": {"text": "Рабочие, низкий квалификация", "scores": {"family": 4}},
            "3": {"text": "Служащие, специалисты", "scores": {"family": 6}},
            "4": {"text": "Бизнесмены, руководители", "scores": {"family": 8}},
            "5": {"text": "Элита, чиновники высокого уровня", "scores": {"family": 10}}
        }
    },
    {  # 11. Близкие друзья
        "text": "Сколько у тебя близких друзей, на которых реально можно положиться?",
        "type": "social",
        "options": {
            "1": {"text": "Никого, я совсем один", "scores": {"friends": 2}},
            "2": {"text": "1-2 друга", "scores": {"friends": 4}},
            "3": {"text": "3-5 друзей", "scores": {"friends": 6}},
            "4": {"text": "5-10 человек", "scores": {"friends": 8}},
            "5": {"text": "Целая команда, много друзей", "scores": {"friends": 10}}
        }
    },
    {  # 12. Финансовая подушка
        "text": "Если срочно понадобится крупная сумма (как месячная зарплата), ты...",
        "type": "social",
        "options": {
            "1": {"text": "Негде взять, катастрофа", "scores": {"money": 2}},
            "2": {"text": "Занять у друзей/родных", "scores": {"money": 4}},
            "3": {"text": "Взять кредит", "scores": {"money": 6}},
            "4": {"text": "У меня есть накопления", "scores": {"money": 8}},
            "5": {"text": "Для меня это мелочь", "scores": {"money": 10}}
        }
    },
    {  # 13. Полезные связи
        "text": "Сколько у тебя знакомых, которые могут помочь с работой/вопросом?",
        "type": "social",
        "options": {
            "1": {"text": "Никого", "scores": {"connections": 2}},
            "2": {"text": "1-2 человека", "scores": {"connections": 4}},
            "3": {"text": "Несколько знакомых", "scores": {"connections": 6}},
            "4": {"text": "Много полезных контактов", "scores": {"connections": 8}},
            "5": {"text": "Я знаю всех, кого нужно", "scores": {"connections": 10}}
        }
    },
    {  # 14. Реакция на стресс (биохимия)
        "text": "В детстве, когда на тебя кричали, твое лицо...",
        "type": "biochemical",
        "options": {
            "1": {"text": "Краснело", "scores": {"stress_response": "FIGHT"}},
            "2": {"text": "Бледнело", "scores": {"stress_response": "FLIGHT"}},
            "3": {"text": "Каменело, застывало", "scores": {"stress_response": "FREEZE"}},
            "4": {"text": "Становилось тряпичным, обмякало", "scores": {"stress_response": "PLAY_DEAD"}},
            "5": {"text": "Расплывалось в улыбке", "scores": {"stress_response": "FAWN"}},
            "6": {"text": "Становилось пустым, безразличным", "scores": {"stress_response": "SURRENDER"}}
        }
    },
    {  # 15. Сон (тип нервной системы)
        "text": "Как ты засыпаешь после тяжелого дня?",
        "type": "biochemical",
        "options": {
            "1": {"text": "Мгновенно, как выключили", "scores": {"nervous_system": "strong", "sleep": 10}},
            "2": {"text": "Долго ворочаюсь, мысли в голове", "scores": {"nervous_system": "anxious", "sleep": 4}},
            "3": {"text": "Засыпаю, но просыпаюсь ночью", "scores": {"nervous_system": "unstable", "sleep": 3}},
            "4": {"text": "Не могу уснуть без таблеток/алкоголя", "scores": {"nervous_system": "exhausted", "sleep": 1}},
            "5": {"text": "Засыпаю, но снятся кошмары", "scores": {"nervous_system": "stressed", "sleep": 5}}
        }
    }
]

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

# Соответствие биохимии и уровня
BIOCHEMICAL_TO_LEVEL = {
    "FIGHT": 6,
    "FLIGHT": 4,
    "FREEZE": 3,
    "PLAY_DEAD": 2,
    "FAWN": 5,
    "SURRENDER": 1
}

# ==================== СОСТОЯНИЯ ====================

class UserState(StatesGroup):
    block1_question = State()  # Индекс текущего вопроса блока 1
    block1_excludes = State()  # Список исключённых нарративов
    narrative = State()        # Определённый нарратив
    second_narrative = State() # Второй нарратив (если есть)
    block2_question = State()  # Индекс текущего вопроса блока 2
    block2_resources = State() # Собранные ресурсы
    block2_answers = State()   # Количество отвеченных вопросов

# ==================== ХЕНДЛЕРЫ ====================

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    """Приветствие и начало теста"""
    await message.answer(
        "🧠 *Вариатика: твоя жизненная стратегия*\n\n"
        "Я задам 8 вопросов, чтобы понять, в каком мире ты живёшь.\n"
        "Потом ещё 15 — чтобы узнать твои ресурсы.\n\n"
        "Готов? Поехали!",
        parse_mode="Markdown"
    )
    
    # Инициализация состояний
    await UserState.block1_question.set()
    await state.update_data(block1_question=0, block1_excludes=[])
    
    # Задаём первый вопрос
    await ask_block1_question(message.from_user.id, 0, state)

async def ask_block1_question(user_id, question_index, state: FSMContext):
    """Задать вопрос из блока 1"""
    q = QUESTIONS_BLOCK1[question_index]
    
    # Создаём клавиатуру
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for emoji, option in q["options"].items():
        keyboard.add(types.InlineKeyboardButton(
            text=f"{emoji} {option['text']}",
            callback_data=f"b1_{question_index}_{emoji}"
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
    _, q_index_str, emoji = callback.data.split('_')
    q_index = int(q_index_str)
    
    # Получаем данные состояния
    data = await state.get_data()
    excludes = data.get('block1_excludes', [])
    
    # Получаем исключаемый нарратив
    excluded = QUESTIONS_BLOCK1[q_index]["options"][emoji]["exclude"]
    excludes.append(excluded)
    await state.update_data(block1_excludes=excludes)
    
    # Следующий вопрос или переход к блоку 2
    if q_index + 1 < len(QUESTIONS_BLOCK1):
        # Ещё есть вопросы
        await ask_block1_question(callback.from_user.id, q_index + 1, state)
    else:
        # Вопросы кончились - определяем нарратив
        await determine_narrative(callback.from_user.id, state)

async def determine_narrative(user_id, state: FSMContext):
    """Определение нарратива методом исключения"""
    data = await state.get_data()
    excludes = data.get('block1_excludes', [])
    
    # Считаем, сколько раз исключали каждый нарратив
    counts = {"СБ": 0, "ТФ": 0, "УБ": 0, "ЧВ": 0}
    for ex in excludes:
        counts[ex] += 1
    
    # Находим наименее исключаемый (или не исключаемый)
    # Сортируем по возрастанию исключений
    sorted_narratives = sorted(counts.items(), key=lambda x: x[1])
    
    narrative = sorted_narratives[0][0]
    second_narrative = None
    
    # Если второй тоже мало исключался
    if sorted_narratives[1][1] - sorted_narratives[0][1] <= 1:
        second_narrative = sorted_narratives[1][0]
    
    # Сохраняем нарратив
    await state.update_data(
        narrative=narrative,
        second_narrative=second_narrative,
        block2_question=0,
        block2_resources={},
        block2_answers=0
    )
    
    # Переходим к блоку 2
    await UserState.block2_question.set()
    
    await bot.send_message(
        user_id,
        f"🎯 *Определено:* твой мир — *{NARRATIVE_NAMES[narrative]}*.\n\n"
        f"Теперь 15 вопросов о твоих ресурсах. Отвечай честно — это важно для точного попадания.",
        parse_mode="Markdown"
    )
    
    # Задаём первый вопрос блока 2
    await ask_block2_question(user_id, 0, state)

async def ask_block2_question(user_id, question_index, state: FSMContext):
    """Задать вопрос из блока 2"""
    q = QUESTIONS_BLOCK2[question_index]
    
    # Создаём клавиатуру
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for key, option in q["options"].items():
        # Укорачиваем текст для кнопок
        btn_text = option['text']
        if len(btn_text) > 30:
            btn_text = btn_text[:28] + ".."
        keyboard.add(types.InlineKeyboardButton(
            text=btn_text,
            callback_data=f"b2_{question_index}_{key}"
        ))
    
    await bot.send_message(
        user_id,
        f"*Вопрос {question_index+1}/15:*\n{q['text']}",
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
    resources = data.get('block2_resources', {})
    answers_count = data.get('block2_answers', 0)
    
    # Получаем баллы за ответ
    q = QUESTIONS_BLOCK2[q_index]
    scores = q["options"][answer_key]["scores"]
    
    # Обновляем ресурсы
    for key, value in scores.items():
        resources[key] = value
    
    await state.update_data(
        block2_resources=resources,
        block2_answers=answers_count + 1
    )
    
    # Следующий вопрос или результат
    if q_index + 1 < len(QUESTIONS_BLOCK2):
        # Ещё есть вопросы
        await ask_block2_question(callback.from_user.id, q_index + 1, state)
    else:
        # Вопросы кончились - показываем результат
        await show_result(callback.from_user.id, state)

async def show_result(user_id, state: FSMContext):
    """Показывает финальный фокус"""
    data = await state.get_data()
    narrative = data.get('narrative')
    second_narrative = data.get('second_narrative')
    resources = data.get('block2_resources', {})
    
    # Определяем уровень
    level = 3  # По умолчанию
    
    # Если есть прямая биохимическая реакция
    if 'stress_response' in resources:
        level = BIOCHEMICAL_TO_LEVEL.get(resources['stress_response'], 3)
    
    # Корректировка по физическим ресурсам
    physical_avg = 0
    physical_count = 0
    for key in ['strength', 'height', 'build', 'health']:
        if key in resources:
            physical_avg += resources[key]
            physical_count += 1
    
    if physical_count > 0:
        physical_avg /= physical_count
        if physical_avg > 7:
            level = min(6, level + 1)
        elif physical_avg < 3:
            level = max(1, level - 1)
    
    # Корректировка по интеллектуальным
    intel_avg = 0
    intel_count = 0
    for key in ['intelligence', 'learning_speed', 'memory', 'creativity']:
        if key in resources:
            intel_avg += resources[key]
            intel_count += 1
    
    if intel_count > 0:
        intel_avg /= intel_count
        if intel_avg > 8 and narrative == "УБ":
            level = min(6, level + 1)
    
    # Корректировка по социальным
    social_avg = 0
    social_count = 0
    for key in ['family', 'friends', 'money', 'connections']:
        if key in resources:
            social_avg += resources[key]
            social_count += 1
    
    if social_count > 0:
        social_avg /= social_count
        if social_avg > 8:
            if narrative == "ТФ":
                level = 6  # ПРОИЗВОДИТЕЛЬ
            elif narrative == "СБ":
                level = 6  # ПАХАН
            elif narrative == "ЧВ":
                level = 6  # МЕДИАМАГНАТ
    
    role = ROLES_MATRIX[narrative][level]
    description = DESCRIPTIONS[narrative][level]
    
    # Формируем результат
    result = f"🎯 *Твой фокус:*\n\n"
    result += f"Ты — *{role}* в мире *{NARRATIVE_NAMES[narrative]}*.\n\n"
    result += f"_{description}_\n\n"
    
    if second_narrative:
        result += f"*При этом* ты используешь мир *{NARRATIVE_NAMES[second_narrative]}* как средство.\n\n"
    
    # Добавляем немного персонализации по ресурсам
    if 'stress_response' in resources:
        stress_map = {
            "FIGHT": "Твоя реакция на стресс — атаковать. Ты краснеешь в конфликте.",
            "FLIGHT": "Твоя реакция на стресс — убегать. Ты бледнеешь в конфликте.",
            "FREEZE": "Твоя реакция на стресс — замирать. Ты каменеешь в конфликте.",
            "PLAY_DEAD": "Твоя реакция на стресс — притворяться мертвым. Ты обмякаешь в конфликте.",
            "FAWN": "Твоя реакция на стресс — заискивать. Ты улыбаешься в конфликте.",
            "SURRENDER": "Твоя реакция на стресс — сдаваться. Ты пустеешь в конфликте."
        }
        result += f"{stress_map.get(resources['stress_response'], '')}\n\n"
    
    # Следующий уровень
    if level < 6:
        next_role = ROLES_MATRIX[narrative][level + 1]
        result += f"*Если хочешь расти:* твой следующий уровень — *{next_role}*.\n"
    else:
        result += f"*Ты на вершине* своего мира. Дальше только смена нарратива.\n"
    
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
