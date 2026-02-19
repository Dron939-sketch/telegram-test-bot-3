"""
Variatica Bot - для aiogram 3.x (совместим с Python 3.13)
"""

import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Проверь переменные окружения")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==================== ДАННЫЕ ====================

# Блок 1: 8 вопросов для определения нарратива
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

# Блок 2: 15 вопросов про ресурсы
QUESTIONS_BLOCK2 = [
    {
        "text": "Какой у тебя рост?",
        "options": {
            "1": {"text": "Ниже 165 см", "scores": {"height": 2}},
            "2": {"text": "165-175 см", "scores": {"height": 4}},
            "3": {"text": "175-185 см", "scores": {"height": 6}},
            "4": {"text": "185-195 см", "scores": {"height": 8}},
            "5": {"text": "Выше 195 см", "scores": {"height": 10}}
        }
    },
    {
        "text": "Каким ты был в 15 лет?",
        "options": {
            "1": {"text": "Очень худым, слабым", "scores": {"build": 2}},
            "2": {"text": "Худощавым", "scores": {"build": 4}},
            "3": {"text": "Нормальным, средним", "scores": {"build": 6}},
            "4": {"text": "Плотным, крепким", "scores": {"build": 8}},
            "5": {"text": "Сильным, меня боялись", "scores": {"build": 10}}
        }
    },
    {
        "text": "Как часто ты болеешь?",
        "options": {
            "1": {"text": "Постоянно, каждый месяц", "scores": {"health": 2}},
            "2": {"text": "Несколько раз в год", "scores": {"health": 4}},
            "3": {"text": "Раз в год по сезону", "scores": {"health": 6}},
            "4": {"text": "Раз в несколько лет", "scores": {"health": 8}},
            "5": {"text": "Практически никогда", "scores": {"health": 10}}
        }
    },
    {
        "text": "Как ты выглядишь?",
        "options": {
            "1": {"text": "Меня не замечают", "scores": {"attractiveness": 2}},
            "2": {"text": "Обычная внешность", "scores": {"attractiveness": 4}},
            "3": {"text": "Симпатичный, приятный", "scores": {"attractiveness": 6}},
            "4": {"text": "Красивый, привлекаю внимание", "scores": {"attractiveness": 8}},
            "5": {"text": "Модельная внешность", "scores": {"attractiveness": 10}}
        }
    },
    {
        "text": "Сколько ты можешь отжаться от пола?",
        "options": {
            "1": {"text": "0-5 раз", "scores": {"strength": 2}},
            "2": {"text": "5-15 раз", "scores": {"strength": 4}},
            "3": {"text": "15-30 раз", "scores": {"strength": 6}},
            "4": {"text": "30-50 раз", "scores": {"strength": 8}},
            "5": {"text": "Больше 50", "scores": {"strength": 10}}
        }
    },
    {
        "text": "В школе ты учился...",
        "options": {
            "1": {"text": "Еле тянул, двойки", "scores": {"intelligence": 2}},
            "2": {"text": "Тройки, кое-как", "scores": {"intelligence": 4}},
            "3": {"text": "Хорошист, твердая 4", "scores": {"intelligence": 6}},
            "4": {"text": "Отличник, легко давалось", "scores": {"intelligence": 8}},
            "5": {"text": "Гений, олимпиады, скучал", "scores": {"intelligence": 10}}
        }
    },
    {
        "text": "Сколько времени нужно, чтобы выучить 50 иностранных слов?",
        "options": {
            "1": {"text": "Неделя и больше", "scores": {"learning_speed": 2}},
            "2": {"text": "Несколько дней", "scores": {"learning_speed": 4}},
            "3": {"text": "Один день", "scores": {"learning_speed": 6}},
            "4": {"text": "Несколько часов", "scores": {"learning_speed": 8}},
            "5": {"text": "Час или меньше", "scores": {"learning_speed": 10}}
        }
    },
    {
        "text": "Ты хорошо запоминаешь лица и имена?",
        "options": {
            "1": {"text": "Постоянно путаю, забываю", "scores": {"memory": 2}},
            "2": {"text": "Запоминаю только близких", "scores": {"memory": 4}},
            "3": {"text": "Запоминаю тех, кто важен", "scores": {"memory": 6}},
            "4": {"text": "Запоминаю большинство", "scores": {"memory": 8}},
            "5": {"text": "Фотографическая память", "scores": {"memory": 10}}
        }
    },
    {
        "text": "Если сломается бытовая техника, ты...",
        "options": {
            "1": {"text": "Выброшу и куплю новую", "scores": {"creativity": 2}},
            "2": {"text": "Позову мастера", "scores": {"creativity": 4}},
            "3": {"text": "Попробую починить по инструкции", "scores": {"creativity": 6}},
            "4": {"text": "Разберусь сам и починю", "scores": {"creativity": 8}},
            "5": {"text": "Улучшу, сделаю лучше чем было", "scores": {"creativity": 10}}
        }
    },
    {
        "text": "Кем работали твои родители?",
        "options": {
            "1": {"text": "Безработные, алкоголики", "scores": {"family": 2}},
            "2": {"text": "Рабочие, низкая квалификация", "scores": {"family": 4}},
            "3": {"text": "Служащие, специалисты", "scores": {"family": 6}},
            "4": {"text": "Бизнесмены, руководители", "scores": {"family": 8}},
            "5": {"text": "Элита, чиновники высокого уровня", "scores": {"family": 10}}
        }
    },
    {
        "text": "Сколько у тебя близких друзей, на которых реально можно положиться?",
        "options": {
            "1": {"text": "Никого, я совсем один", "scores": {"friends": 2}},
            "2": {"text": "1-2 друга", "scores": {"friends": 4}},
            "3": {"text": "3-5 друзей", "scores": {"friends": 6}},
            "4": {"text": "5-10 человек", "scores": {"friends": 8}},
            "5": {"text": "Целая команда, много друзей", "scores": {"friends": 10}}
        }
    },
    {
        "text": "Если срочно понадобится крупная сумма (как месячная зарплата), ты...",
        "options": {
            "1": {"text": "Негде взять, катастрофа", "scores": {"money": 2}},
            "2": {"text": "Занять у друзей/родных", "scores": {"money": 4}},
            "3": {"text": "Взять кредит", "scores": {"money": 6}},
            "4": {"text": "У меня есть накопления", "scores": {"money": 8}},
            "5": {"text": "Для меня это мелочь", "scores": {"money": 10}}
        }
    },
    {
        "text": "Сколько у тебя знакомых, которые могут помочь с работой/вопросом?",
        "options": {
            "1": {"text": "Никого", "scores": {"connections": 2}},
            "2": {"text": "1-2 человека", "scores": {"connections": 4}},
            "3": {"text": "Несколько знакомых", "scores": {"connections": 6}},
            "4": {"text": "Много полезных контактов", "scores": {"connections": 8}},
            "5": {"text": "Я знаю всех, кого нужно", "scores": {"connections": 10}}
        }
    },
    {
        "text": "В детстве, когда на тебя кричали, твое лицо...",
        "options": {
            "1": {"text": "Краснело", "scores": {"stress_response": "FIGHT"}},
            "2": {"text": "Бледнело", "scores": {"stress_response": "FLIGHT"}},
            "3": {"text": "Каменело, застывало", "scores": {"stress_response": "FREEZE"}},
            "4": {"text": "Становилось тряпичным, обмякало", "scores": {"stress_response": "PLAY_DEAD"}},
            "5": {"text": "Расплывалось в улыбке", "scores": {"stress_response": "FAWN"}},
            "6": {"text": "Становилось пустым, безразличным", "scores": {"stress_response": "SURRENDER"}}
        }
    },
    {
        "text": "Как ты засыпаешь после тяжелого дня?",
        "options": {
            "1": {"text": "Мгновенно, как выключили", "scores": {"sleep": 10}},
            "2": {"text": "Долго ворочаюсь, мысли в голове", "scores": {"sleep": 4}},
            "3": {"text": "Засыпаю, но просыпаюсь ночью", "scores": {"sleep": 3}},
            "4": {"text": "Не могу уснуть без таблеток/алкоголя", "scores": {"sleep": 1}},
            "5": {"text": "Засыпаю, но снятся кошмары", "scores": {"sleep": 5}}
        }
    }
]

# Матрица ролей
ROLES_MATRIX = {
    "СБ": {1: "БОМЖ", 2: "ШНЫРЬ", 3: "СМОТРЯЩИЙ", 4: "ВОЛЬНЫЙ СТРЕЛОК", 5: "РАЗВОДЯЩИЙ", 6: "ПАХАН"},
    "ТФ": {1: "ИЖДИВЕНЕЦ", 2: "НАЁМНЫЙ РАБОЧИЙ", 3: "АРЕНДОДАТЕЛЬ", 4: "САМОЗАНЯТЫЙ", 5: "СЕЛЛЕР", 6: "ПРОИЗВОДИТЕЛЬ"},
    "УБ": {1: "ЛЖЕЭКСПЕРТ", 2: "НАЁМНЫЙ СПЕЦИАЛИСТ", 3: "НАСТАВНИК", 4: "ИССЛЕДОВАТЕЛЬ", 5: "ПРОДАВЕЦ ЗНАНИЙ", 6: "ТЕОРЕТИК"},
    "ЧВ": {1: "ТУСОВЩИК", 2: "ПРОЕКТНЫЙ", 3: "АМБАССАДОР", 4: "АРТИСТ", 5: "АГЕНТ", 6: "МЕДИАМАГНАТ"}
}

DESCRIPTIONS = {
    "СБ": {
        1: "Ты вне иерархии. Тебя нет в раскладе. Ты просто существуешь, ни на что не влияя.",
        2: "Ты обслуживаешь тех, кто сильнее. Твоя роль — быть полезным, выполнять приказы.",
        3: "Ты следишь за порядком на своей территории. У тебя есть зона ответственности.",
        4: "Ты сам по себе. Ты ничей. Ты не строишься в иерархию и не подчиняешься.",
        5: "Ты решаешь вопросы за процент. Ты знаешь нужных людей и умеешь их сводить.",
        6: "Ты наверху. Ты устанавливаешь правила. Твоё слово — закон."
    },
    "ТФ": {
        1: "Ты живёшь за счёт других. Кто-то обеспечивает твоё существование.",
        2: "Ты продаёшь своё время и руки за зарплату. Ты — надёжный винтик в большой машине.",
        3: "Ты не работаешь руками — ты работаешь имуществом. Твой доход идёт к тебе без участия.",
        4: "Ты работаешь на себя. Фриланс, шабашки, ИП без сотрудников.",
        5: "Ты продаёшь чужой товар. Ты находишь того, кто произвёл, и того, кто купит.",
        6: "Ты организовал производство. У тебя есть люди, станки, цеха."
    },
    "УБ": {
        1: "Ты продаёшь воздух. Ты говоришь красиво, но за этим ничего нет.",
        2: "Ты продаёшь свои знания за зарплату. Ты компетентен, но не создаёшь нового.",
        3: "Ты передаёшь знания другим. Учитель, наставник, преподаватель.",
        4: "Ты создаёшь новое. Ты исследователь, который идёт туда, куда никто не ходил.",
        5: "Ты продаёшь чужие знания. Издатель, популяризатор, организатор курсов.",
        6: "Ты создал систему. Твои работы цитируют, по твоим книгам учат."
    },
    "ЧВ": {
        1: "Ты всегда там, где движуха. Ты потребляешь чужое внимание, не создавая своего.",
        2: "Ты работаешь в чужих проектах. Твой талант работает на других.",
        3: "Ты — лицо бренда. Твоё имя работает на других.",
        4: "Ты создаёшь своё имя. Блогер, артист, творец.",
        5: "Ты создаёшь тех, кто создаёт контент. Продюсер, агент, менеджер.",
        6: "Ты владеешь платформой. У тебя канал, студия, СМИ."
    }
}

NARRATIVE_NAMES = {"СБ": "СИЛЫ", "ТФ": "ТРУДА", "УБ": "ЗНАНИЙ", "ЧВ": "ВНИМАНИЯ"}
BIOCHEMICAL_TO_LEVEL = {"FIGHT": 6, "FLIGHT": 4, "FREEZE": 3, "PLAY_DEAD": 2, "FAWN": 5, "SURRENDER": 1}

# ==================== СОСТОЯНИЯ ====================

class UserState(StatesGroup):
    block1_question = State()
    block1_excludes = State()
    narrative = State()
    second_narrative = State()
    block2_question = State()
    block2_resources = State()

# ==================== ХЕНДЛЕРЫ ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        "🧠 *Вариатика: твоя жизненная стратегия*\n\n"
        "Я задам 8 вопросов, чтобы понять, в каком мире ты живёшь.\n"
        "Потом ещё 15 — чтобы узнать твои ресурсы.\n\n"
        "Готов? Поехали!"
    )
    await state.set_state(UserState.block1_question)
    await state.update_data(block1_question=0, block1_excludes=[])
    await ask_block1_question(message.from_user.id, 0, state)

async def ask_block1_question(user_id, question_index, state: FSMContext):
    q = QUESTIONS_BLOCK1[question_index]
    builder = InlineKeyboardBuilder()
    for emoji, option in q["options"].items():
        builder.button(text=f"{emoji} {option['text']}", callback_data=f"b1_{question_index}_{emoji}")
    builder.adjust(2)
    await bot.send_message(user_id, f"*Вопрос {question_index+1}/8:*\n{q['text']}", reply_markup=builder.as_markup())

# ИСПРАВЛЕНО: используем @dp.callback_query() вместо @dp.callback_query_handler
@dp.callback_query(lambda c: c.data.startswith('b1_'))
async def process_block1_answer(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    _, q_index_str, emoji = callback.data.split('_')
    q_index = int(q_index_str)
    
    data = await state.get_data()
    excludes = data.get('block1_excludes', [])
    excluded = QUESTIONS_BLOCK1[q_index]["options"][emoji]["exclude"]
    excludes.append(excluded)
    await state.update_data(block1_excludes=excludes)
    
    if q_index + 1 < len(QUESTIONS_BLOCK1):
        await ask_block1_question(callback.from_user.id, q_index + 1, state)
    else:
        await determine_narrative(callback.from_user.id, state)

async def determine_narrative(user_id, state: FSMContext):
    data = await state.get_data()
    excludes = data.get('block1_excludes', [])
    counts = {"СБ": 0, "ТФ": 0, "УБ": 0, "ЧВ": 0}
    for ex in excludes:
        counts[ex] += 1
    sorted_narratives = sorted(counts.items(), key=lambda x: x[1])
    narrative = sorted_narratives[0][0]
    second_narrative = sorted_narratives[1][0] if sorted_narratives[1][1] - sorted_narratives[0][1] <= 1 else None
    
    await state.update_data(narrative=narrative, second_narrative=second_narrative, block2_question=0, block2_resources={})
    await state.set_state(UserState.block2_question)
    await bot.send_message(user_id, f"🎯 *Определено:* твой мир — *{NARRATIVE_NAMES[narrative]}*.\n\nТеперь 15 вопросов о твоих ресурсах.")
    await ask_block2_question(user_id, 0, state)

async def ask_block2_question(user_id, question_index, state: FSMContext):
    q = QUESTIONS_BLOCK2[question_index]
    builder = InlineKeyboardBuilder()
    for key, option in q["options"].items():
        text = option['text'] if len(option['text']) <= 30 else option['text'][:28] + ".."
        builder.button(text=text, callback_data=f"b2_{question_index}_{key}")
    builder.adjust(2)
    await bot.send_message(user_id, f"*Вопрос {question_index+1}/15:*\n{q['text']}", reply_markup=builder.as_markup())

# ИСПРАВЛЕНО: используем @dp.callback_query() вместо @dp.callback_query_handler
@dp.callback_query(lambda c: c.data.startswith('b2_'))
async def process_block2_answer(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    _, q_index_str, answer_key = callback.data.split('_')
    q_index = int(q_index_str)
    
    data = await state.get_data()
    resources = data.get('block2_resources', {})
    q = QUESTIONS_BLOCK2[q_index]
    scores = q["options"][answer_key]["scores"]
    
    for key, value in scores.items():
        resources[key] = value
    await state.update_data(block2_resources=resources)
    
    if q_index + 1 < len(QUESTIONS_BLOCK2):
        await ask_block2_question(callback.from_user.id, q_index + 1, state)
    else:
        await show_result(callback.from_user.id, state)

async def show_result(user_id, state: FSMContext):
    data = await state.get_data()
    narrative = data.get('narrative')
    second_narrative = data.get('second_narrative')
    resources = data.get('block2_resources', {})
    
    level = BIOCHEMICAL_TO_LEVEL.get(resources.get('stress_response', 'FREEZE'), 3)
    
    role = ROLES_MATRIX[narrative][level]
    description = DESCRIPTIONS[narrative][level]
    
    result = f"🎯 *Твой фокус:*\n\nТы — *{role}* в мире *{NARRATIVE_NAMES[narrative]}*.\n\n_{description}_\n\n"
    if second_narrative:
        result += f"*При этом* ты используешь мир *{NARRATIVE_NAMES[second_narrative]}* как средство.\n\n"
    
    stress_map = {
        "FIGHT": "Ты краснеешь в конфликте — твоя реакция атаковать.",
        "FLIGHT": "Ты бледнеешь — твоя реакция убегать.",
        "FREEZE": "Ты каменеешь — твоя реакция замирать.",
        "PLAY_DEAD": "Ты обмякаешь — твоя реакция притворяться мертвым.",
        "FAWN": "Ты улыбаешься — твоя реакция заискивать.",
        "SURRENDER": "Ты пустеешь — твоя реакция сдаваться."
    }
    if 'stress_response' in resources:
        result += f"{stress_map.get(resources['stress_response'], '')}\n\n"
    
    if level < 6:
        result += f"*Если хочешь расти:* твой следующий уровень — *{ROLES_MATRIX[narrative][level + 1]}*.\n"
    else:
        result += f"*Ты на вершине* своего мира.\n"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Пройти заново", callback_data="restart")
    await bot.send_message(user_id, result, reply_markup=builder.as_markup())
    await state.clear()

# ИСПРАВЛЕНО: используем @dp.callback_query() вместо @dp.callback_query_handler
@dp.callback_query(lambda c: c.data == 'restart')
async def restart_test(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await cmd_start(callback.message, state)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
