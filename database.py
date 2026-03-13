"""
Модуль для работы с PostgreSQL базой данных бота "Фреди"
Все таблицы имеют префикс fredi_ для избежания конфликтов

Версия 1.0 - Полная интеграция с существующими структурами данных
"""

import asyncpg
import pickle
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class BotDatabase:
    """Класс для работы с базой данных PostgreSQL"""
    
    def __init__(self, dsn: str):
        """
        Инициализация подключения к БД
        
        Args:
            dsn: Строка подключения к PostgreSQL
        """
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self, min_size: int = 1, max_size: int = 10):
        """
        Создание пула соединений с БД
        
        Args:
            min_size: Минимальное количество соединений в пуле
            max_size: Максимальное количество соединений в пуле
        """
        try:
            self.pool = await asyncpg.create_pool(
                self.dsn,
                min_size=min_size,
                max_size=max_size,
                command_timeout=60,
                max_inactive_connection_lifetime=300
            )
            logger.info("✅ Пул соединений с PostgreSQL создан")
            
            # Создаем таблицы при подключении
            await self.create_tables()
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к PostgreSQL: {e}")
            raise
    
    async def disconnect(self):
        """Закрытие пула соединений"""
        if self.pool:
            await self.pool.close()
            logger.info("🔌 Пул соединений с PostgreSQL закрыт")
    
    @asynccontextmanager
    async def get_connection(self):
        """Контекстный менеджер для получения соединения из пула"""
        if not self.pool:
            raise RuntimeError("Пул соединений не инициализирован. Вызовите connect()")
        
        async with self.pool.acquire() as conn:
            yield conn
    
    # ====================== СОЗДАНИЕ ТАБЛИЦ ======================
    
    async def create_tables(self):
        """Создает все необходимые таблицы, если их нет"""
        async with self.get_connection() as conn:
            
            # Таблица пользователей Telegram
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fredi_users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language_code TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Таблица контекста пользователей (UserContext)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fredi_user_contexts (
                    user_id BIGINT PRIMARY KEY REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                    
                    -- Основные данные
                    name TEXT,
                    city TEXT,
                    timezone TEXT DEFAULT 'Europe/Moscow',
                    timezone_offset INTEGER DEFAULT 3,
                    gender TEXT,
                    age INTEGER,
                    birth_date DATE,
                    communication_mode TEXT DEFAULT 'coach',
                    last_context_update TIMESTAMP WITH TIME ZONE,
                    
                    -- Погода (кэш)
                    weather_cache JSONB,
                    weather_cache_time TIMESTAMP WITH TIME ZONE,
                    
                    -- Жизненный контекст
                    family_status TEXT,
                    has_children BOOLEAN DEFAULT FALSE,
                    children_ages TEXT,
                    work_schedule TEXT,
                    job_title TEXT,
                    commute_time INTEGER,
                    housing_type TEXT,
                    has_private_space BOOLEAN DEFAULT FALSE,
                    has_car BOOLEAN DEFAULT FALSE,
                    support_people TEXT,
                    resistance_people TEXT,
                    energy_level INTEGER,
                    life_context_complete BOOLEAN DEFAULT FALSE,
                    
                    -- Состояние сбора контекста
                    awaiting_context TEXT,
                    
                    -- Временные метки
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Таблица данных пользователей (user_data)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fredi_user_data (
                    user_id BIGINT PRIMARY KEY REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                    data JSONB NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Таблица для хранения сериализованных объектов UserContext (резерв)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fredi_context_objects (
                    user_id BIGINT PRIMARY KEY REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                    context_data BYTEA NOT NULL,  -- pickle объект
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Таблица маршрутов пользователей
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fredi_user_routes (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                    route_data JSONB NOT NULL,
                    current_step INTEGER DEFAULT 1,
                    progress JSONB DEFAULT '[]',
                    is_active BOOLEAN DEFAULT TRUE,
                    completed_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Таблица результатов тестов
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fredi_test_results (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                    test_type TEXT NOT NULL,  -- 'full_profile', 'stage1', 'stage2', etc
                    results JSONB NOT NULL,   -- полные результаты
                    profile_code TEXT,        -- СБ-4_ТФ-4_УБ-4_ЧВ-4
                    perception_type TEXT,      -- тип восприятия
                    thinking_level INTEGER,    -- уровень мышления 1-9
                    vectors JSONB,             -- баллы по векторам {"СБ": 3.5, "ТФ": 4.2, ...}
                    deep_patterns JSONB,       -- результаты 5 этапа
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Таблица ответов на тест (детализированно)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fredi_test_answers (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                    test_result_id BIGINT REFERENCES fredi_test_results(id) ON DELETE CASCADE,
                    stage INTEGER NOT NULL,    -- 1,2,3,4,5
                    question_index INTEGER NOT NULL,
                    question_text TEXT,
                    answer_text TEXT,
                    answer_value TEXT,         -- ключ опции (a,b,c,d или 1,2,3,4)
                    scores JSONB,              -- для этапа 1: {"EXTERNAL": 2, ...}
                    measures TEXT,              -- для этапа 2: 'СБ', 'ТФ', 'ЧВ', 'УБ', 'thinking'
                    strategy TEXT,              -- для этапа 3: 'СБ', 'ТФ', 'УБ', 'ЧВ'
                    dilts TEXT,                  -- для этапа 4: 'ENVIRONMENT', 'BEHAVIOR', etc
                    pattern TEXT,                -- для этапа 5: 'secure', 'avoidant', etc
                    target TEXT,                  -- для этапа 5: 'attachment', 'defense', etc
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Таблица напоминаний
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fredi_reminders (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                    reminder_type TEXT NOT NULL,  -- 'morning_message', 'motivation', 'checkin', 'deadline'
                    remind_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    data JSONB,
                    is_sent BOOLEAN DEFAULT FALSE,
                    sent_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Таблица событий для статистики
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fredi_events (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES fredi_users(user_id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,   -- 'start', 'test_completed', 'question_asked', 'route_started'
                    event_data JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Индексы для быстрого поиска
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_reminders_remind_at ON fredi_reminders(remind_at) WHERE is_sent = FALSE")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_events_user_id ON fredi_events(user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON fredi_events(event_type)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_test_results_user_id ON fredi_test_results(user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_test_results_profile ON fredi_test_results(profile_code)")
            
            logger.info("✅ Таблицы созданы или уже существуют")
    
    # ====================== ПОЛЬЗОВАТЕЛИ ======================
    
    async def save_telegram_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None
    ) -> bool:
        """
        Сохранение или обновление информации о пользователе Telegram
        
        Returns:
            True если пользователь создан, False если обновлен
        """
        async with self.get_connection() as conn:
            # Проверяем существование пользователя
            existing = await conn.fetchval(
                "SELECT user_id FROM fredi_users WHERE user_id = $1",
                user_id
            )
            
            if existing:
                # Обновление существующего
                await conn.execute("""
                    UPDATE fredi_users SET
                        username = $2,
                        first_name = $3,
                        last_name = $4,
                        language_code = $5,
                        updated_at = NOW(),
                        last_activity = NOW()
                    WHERE user_id = $1
                """, user_id, username, first_name, last_name, language_code)
                return False
            else:
                # Вставка нового
                await conn.execute("""
                    INSERT INTO fredi_users (
                        user_id, username, first_name, last_name, 
                        language_code, created_at, updated_at, last_activity
                    ) VALUES ($1, $2, $3, $4, $5, NOW(), NOW(), NOW())
                """, user_id, username, first_name, last_name, language_code)
                return True
    
    async def get_telegram_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о пользователе"""
        async with self.get_connection() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM fredi_users WHERE user_id = $1",
                user_id
            )
            return dict(row) if row else None
    
    async def update_last_activity(self, user_id: int):
        """Обновляет время последней активности пользователя"""
        async with self.get_connection() as conn:
            await conn.execute("""
                UPDATE fredi_users SET last_activity = NOW() WHERE user_id = $1
            """, user_id)
    
    # ====================== КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ ======================
    
    async def save_user_context(self, user_id: int, context_obj) -> None:
        """
        Сохраняет объект UserContext в БД
        
        Args:
            user_id: ID пользователя
            context_obj: Объект UserContext
        """
        # Сначала убеждаемся, что пользователь существует
        await self.save_telegram_user(user_id)
        
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO fredi_user_contexts (
                    user_id, name, city, timezone, timezone_offset, gender, age,
                    birth_date, communication_mode, last_context_update,
                    weather_cache, weather_cache_time,
                    family_status, has_children, children_ages, work_schedule,
                    job_title, commute_time, housing_type, has_private_space,
                    has_car, support_people, resistance_people, energy_level,
                    life_context_complete, awaiting_context, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                    $21, $22, $23, $24, $25, $26, NOW()
                )
                ON CONFLICT (user_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    city = EXCLUDED.city,
                    timezone = EXCLUDED.timezone,
                    timezone_offset = EXCLUDED.timezone_offset,
                    gender = EXCLUDED.gender,
                    age = EXCLUDED.age,
                    birth_date = EXCLUDED.birth_date,
                    communication_mode = EXCLUDED.communication_mode,
                    last_context_update = EXCLUDED.last_context_update,
                    weather_cache = EXCLUDED.weather_cache,
                    weather_cache_time = EXCLUDED.weather_cache_time,
                    family_status = EXCLUDED.family_status,
                    has_children = EXCLUDED.has_children,
                    children_ages = EXCLUDED.children_ages,
                    work_schedule = EXCLUDED.work_schedule,
                    job_title = EXCLUDED.job_title,
                    commute_time = EXCLUDED.commute_time,
                    housing_type = EXCLUDED.housing_type,
                    has_private_space = EXCLUDED.has_private_space,
                    has_car = EXCLUDED.has_car,
                    support_people = EXCLUDED.support_people,
                    resistance_people = EXCLUDED.resistance_people,
                    energy_level = EXCLUDED.energy_level,
                    life_context_complete = EXCLUDED.life_context_complete,
                    awaiting_context = EXCLUDED.awaiting_context,
                    updated_at = NOW()
            """,
                user_id,
                getattr(context_obj, 'name', None),
                getattr(context_obj, 'city', None),
                getattr(context_obj, 'timezone', 'Europe/Moscow'),
                getattr(context_obj, 'timezone_offset', 3),
                getattr(context_obj, 'gender', None),
                getattr(context_obj, 'age', None),
                getattr(context_obj, 'birth_date', None),
                getattr(context_obj, 'communication_mode', 'coach'),
                getattr(context_obj, 'last_context_update', None),
                json.dumps(getattr(context_obj, 'weather_cache', {})),
                getattr(context_obj, 'weather_cache_time', None),
                getattr(context_obj, 'family_status', None),
                getattr(context_obj, 'has_children', False),
                getattr(context_obj, 'children_ages', None),
                getattr(context_obj, 'work_schedule', None),
                getattr(context_obj, 'job_title', None),
                getattr(context_obj, 'commute_time', None),
                getattr(context_obj, 'housing_type', None),
                getattr(context_obj, 'has_private_space', False),
                getattr(context_obj, 'has_car', False),
                getattr(context_obj, 'support_people', None),
                getattr(context_obj, 'resistance_people', None),
                getattr(context_obj, 'energy_level', None),
                getattr(context_obj, 'life_context_complete', False),
                getattr(context_obj, 'awaiting_context', None)
            )
    
    async def load_user_context(self, user_id: int):
        """
        Загружает данные для создания объекта UserContext
        
        Returns:
            Dict с данными или None
        """
        async with self.get_connection() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM fredi_user_contexts WHERE user_id = $1",
                user_id
            )
            
            if not row:
                return None
            
            data = dict(row)
            
            # Преобразуем JSON поля
            if data.get('weather_cache'):
                data['weather_cache'] = json.loads(data['weather_cache'])
            
            return data
    
    # ====================== ДАННЫЕ ПОЛЬЗОВАТЕЛЕЙ (user_data) ======================
    
    async def save_user_data(self, user_id: int, data: Dict[str, Any]) -> None:
        """
        Сохраняет user_data[user_id] в JSONB поле
        
        Args:
            user_id: ID пользователя
            data: Словарь с данными пользователя
        """
        # Сначала убеждаемся, что пользователь существует
        await self.save_telegram_user(user_id)
        
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO fredi_user_data (user_id, data, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    data = $2,
                    updated_at = NOW()
            """, user_id, json.dumps(data, default=str))
    
    async def load_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Загружает user_data для пользователя"""
        async with self.get_connection() as conn:
            row = await conn.fetchrow(
                "SELECT data FROM fredi_user_data WHERE user_id = $1",
                user_id
            )
            
            if row and row['data']:
                return json.loads(row['data'])
            
            return {}
    
    # ====================== СЕРИАЛИЗОВАННЫЕ ОБЪЕКТЫ (резерв) ======================
    
    async def save_pickled_context(self, user_id: int, context_obj) -> None:
        """
        Сохраняет сериализованный объект UserContext (как резерв)
        
        Args:
            user_id: ID пользователя
            context_obj: Объект UserContext
        """
        async with self.get_connection() as conn:
            pickled = pickle.dumps(context_obj)
            await conn.execute("""
                INSERT INTO fredi_context_objects (user_id, context_data, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    context_data = $2,
                    updated_at = NOW()
            """, user_id, pickled)
    
    async def load_pickled_context(self, user_id: int):
        """
        Загружает сериализованный объект UserContext
        
        Returns:
            Объект UserContext или None
        """
        async with self.get_connection() as conn:
            row = await conn.fetchrow(
                "SELECT context_data FROM fredi_context_objects WHERE user_id = $1",
                user_id
            )
            
            if row and row['context_data']:
                try:
                    return pickle.loads(row['context_data'])
                except Exception as e:
                    logger.error(f"Ошибка при десериализации контекста пользователя {user_id}: {e}")
            
            return None
    
    # ====================== МАРШРУТЫ ======================
    
    async def save_user_route(
        self,
        user_id: int,
        route_data: Dict[str, Any],
        current_step: int = 1,
        progress: List = None
    ) -> int:
        """Сохраняет маршрут пользователя"""
        if progress is None:
            progress = []
        
        async with self.get_connection() as conn:
            # Деактивируем предыдущие активные маршруты
            await conn.execute("""
                UPDATE fredi_user_routes SET is_active = FALSE
                WHERE user_id = $1 AND is_active = TRUE
            """, user_id)
            
            # Вставляем новый маршрут
            route_id = await conn.fetchval("""
                INSERT INTO fredi_user_routes (
                    user_id, route_data, current_step, progress, is_active
                ) VALUES ($1, $2, $3, $4, TRUE)
                RETURNING id
            """, user_id, json.dumps(route_data), current_step, json.dumps(progress))
            
            return route_id
    
    async def load_user_route(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Загружает активный маршрут пользователя"""
        async with self.get_connection() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM fredi_user_routes
                WHERE user_id = $1 AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT 1
            """, user_id)
            
            if not row:
                return None
            
            data = dict(row)
            data['route_data'] = json.loads(data['route_data'])
            data['progress'] = json.loads(data['progress'])
            
            return data
    
    async def update_user_route(
        self,
        route_id: int,
        current_step: int,
        progress: List,
        completed: bool = False
    ):
        """Обновляет прогресс по маршруту"""
        async with self.get_connection() as conn:
            await conn.execute("""
                UPDATE fredi_user_routes SET
                    current_step = $2,
                    progress = $3,
                    is_active = NOT $4,
                    completed_at = CASE WHEN $4 THEN NOW() ELSE completed_at END,
                    updated_at = NOW()
                WHERE id = $1
            """, route_id, current_step, json.dumps(progress), completed)
    
    # ====================== РЕЗУЛЬТАТЫ ТЕСТОВ ======================
    
    async def save_test_result(
        self,
        user_id: int,
        test_type: str,
        results: Dict[str, Any],
        profile_code: Optional[str] = None,
        perception_type: Optional[str] = None,
        thinking_level: Optional[int] = None,
        vectors: Optional[Dict[str, float]] = None,
        deep_patterns: Optional[Dict] = None
    ) -> int:
        """Сохраняет результат тестирования"""
        
        # Рассчитываем векторы, если не переданы, но есть results
        if vectors is None and 'behavioral_levels' in results:
            vectors = {}
            behavioral = results.get('behavioral_levels', {})
            for vector in ['СБ', 'ТФ', 'УБ', 'ЧВ']:
                levels = behavioral.get(vector, [])
                vectors[vector] = sum(levels) / len(levels) if levels else 3.0
        
        async with self.get_connection() as conn:
            test_id = await conn.fetchval("""
                INSERT INTO fredi_test_results (
                    user_id, test_type, results, profile_code,
                    perception_type, thinking_level, vectors, deep_patterns
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """,
                user_id,
                test_type,
                json.dumps(results, default=str),
                profile_code,
                perception_type,
                thinking_level,
                json.dumps(vectors) if vectors else None,
                json.dumps(deep_patterns) if deep_patterns else None
            )
            
            return test_id
    
    async def get_user_test_results(
        self,
        user_id: int,
        limit: int = 10,
        test_type: Optional[str] = None
    ) -> List[Dict]:
        """Получает последние результаты тестов пользователя"""
        async with self.get_connection() as conn:
            if test_type:
                rows = await conn.fetch("""
                    SELECT * FROM fredi_test_results
                    WHERE user_id = $1 AND test_type = $2
                    ORDER BY created_at DESC
                    LIMIT $3
                """, user_id, test_type, limit)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM fredi_test_results
                    WHERE user_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """, user_id, limit)
            
            results = []
            for row in rows:
                data = dict(row)
                data['results'] = json.loads(data['results'])
                if data.get('vectors'):
                    data['vectors'] = json.loads(data['vectors'])
                if data.get('deep_patterns'):
                    data['deep_patterns'] = json.loads(data['deep_patterns'])
                results.append(data)
            
            return results
    
    async def get_latest_profile(self, user_id: int) -> Optional[Dict]:
        """Получает последний полный профиль пользователя"""
        results = await self.get_user_test_results(user_id, limit=1, test_type='full_profile')
        return results[0] if results else None
    
    # ====================== ОТВЕТЫ НА ТЕСТ ======================
    
    async def save_test_answer(
        self,
        user_id: int,
        test_result_id: Optional[int],
        stage: int,
        question_index: int,
        question_text: str,
        answer_text: str,
        answer_value: str,
        scores: Optional[Dict] = None,
        measures: Optional[str] = None,
        strategy: Optional[str] = None,
        dilts: Optional[str] = None,
        pattern: Optional[str] = None,
        target: Optional[str] = None
    ):
        """Сохраняет отдельный ответ на вопрос теста"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO fredi_test_answers (
                    user_id, test_result_id, stage, question_index,
                    question_text, answer_text, answer_value,
                    scores, measures, strategy, dilts, pattern, target
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """,
                user_id,
                test_result_id,
                stage,
                question_index,
                question_text,
                answer_text,
                answer_value,
                json.dumps(scores) if scores else None,
                measures,
                strategy,
                dilts,
                pattern,
                target
            )
    
    async def get_test_answers(self, test_result_id: int) -> List[Dict]:
        """Получает все ответы для конкретного результата теста"""
        async with self.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT * FROM fredi_test_answers
                WHERE test_result_id = $1
                ORDER BY stage, question_index
            """, test_result_id)
            
            answers = []
            for row in rows:
                data = dict(row)
                if data.get('scores'):
                    data['scores'] = json.loads(data['scores'])
                answers.append(data)
            
            return answers
    
    # ====================== НАПОМИНАНИЯ ======================
    
    async def add_reminder(
        self,
        user_id: int,
        reminder_type: str,
        remind_at: datetime,
        data: Optional[Dict] = None
    ) -> int:
        """Добавляет напоминание"""
        async with self.get_connection() as conn:
            reminder_id = await conn.fetchval("""
                INSERT INTO fredi_reminders (user_id, reminder_type, remind_at, data)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """, user_id, reminder_type, remind_at, json.dumps(data) if data else None)
            
            return reminder_id
    
    async def get_pending_reminders(self, limit: int = 100) -> List[Dict]:
        """Получает список неотправленных напоминаний, которые уже пора отправить"""
        async with self.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT * FROM fredi_reminders
                WHERE is_sent = FALSE AND remind_at <= NOW()
                ORDER BY remind_at
                LIMIT $1
            """, limit)
            
            reminders = []
            for row in rows:
                data = dict(row)
                if data.get('data'):
                    data['data'] = json.loads(data['data'])
                reminders.append(data)
            
            return reminders
    
    async def mark_reminder_sent(self, reminder_id: int):
        """Отмечает напоминание как отправленное"""
        async with self.get_connection() as conn:
            await conn.execute("""
                UPDATE fredi_reminders
                SET is_sent = TRUE, sent_at = NOW()
                WHERE id = $1
            """, reminder_id)
    
    async def get_user_reminders(
        self,
        user_id: int,
        include_sent: bool = False
    ) -> List[Dict]:
        """Получает все напоминания пользователя"""
        async with self.get_connection() as conn:
            if include_sent:
                rows = await conn.fetch("""
                    SELECT * FROM fredi_reminders
                    WHERE user_id = $1
                    ORDER BY remind_at DESC
                """, user_id)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM fredi_reminders
                    WHERE user_id = $1 AND is_sent = FALSE
                    ORDER BY remind_at
                """, user_id)
            
            reminders = []
            for row in rows:
                data = dict(row)
                if data.get('data'):
                    data['data'] = json.loads(data['data'])
                reminders.append(data)
            
            return reminders
    
    # ====================== СОБЫТИЯ И СТАТИСТИКА ======================
    
    async def log_event(
        self,
        user_id: int,
        event_type: str,
        event_data: Optional[Dict] = None
    ):
        """Логирует событие для статистики"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO fredi_events (user_id, event_type, event_data)
                VALUES ($1, $2, $3)
            """, user_id, event_type, json.dumps(event_data) if event_data else None)
            
            # Также обновляем last_activity
            await self.update_last_activity(user_id)
    
    async def get_stats(self, days: int = 30) -> Dict[str, Any]:
        """Получает статистику за указанный период"""
        async with self.get_connection() as conn:
            since = datetime.now() - timedelta(days=days)
            
            # Общая статистика
            total_users = await conn.fetchval("SELECT COUNT(*) FROM fredi_users")
            active_users = await conn.fetchval("""
                SELECT COUNT(DISTINCT user_id) FROM fredi_events
                WHERE created_at >= $1
            """, since)
            
            # Завершенные тесты
            completed_tests = await conn.fetchval("""
                SELECT COUNT(*) FROM fredi_test_results
                WHERE created_at >= $1
            """, since)
            
            # Распределение по типам событий
            event_types = await conn.fetch("""
                SELECT event_type, COUNT(*) as count
                FROM fredi_events
                WHERE created_at >= $1
                GROUP BY event_type
                ORDER BY count DESC
            """, since)
            
            # Распределение по типам восприятия
            perception_types = await conn.fetch("""
                SELECT perception_type, COUNT(*) as count
                FROM fredi_test_results
                WHERE perception_type IS NOT NULL AND created_at >= $1
                GROUP BY perception_type
                ORDER BY count DESC
            """, since)
            
            # Распределение по уровням мышления
            thinking_levels = await conn.fetch("""
                SELECT thinking_level, COUNT(*) as count
                FROM fredi_test_results
                WHERE thinking_level IS NOT NULL AND created_at >= $1
                GROUP BY thinking_level
                ORDER BY thinking_level
            """, since)
            
            # Распределение по профилям
            profiles = await conn.fetch("""
                SELECT profile_code, COUNT(*) as count
                FROM fredi_test_results
                WHERE profile_code IS NOT NULL AND created_at >= $1
                GROUP BY profile_code
                ORDER BY count DESC
                LIMIT 20
            """, since)
            
            # Ежедневная активность
            daily = await conn.fetch("""
                SELECT DATE(created_at) as date,
                       COUNT(DISTINCT user_id) as users,
                       COUNT(*) as events
                FROM fredi_events
                WHERE created_at >= $1
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """, since)
            
            return {
                'period_days': days,
                'total_users': total_users,
                'active_users': active_users,
                'completed_tests': completed_tests,
                'event_types': [dict(et) for et in event_types],
                'perception_types': [dict(pt) for pt in perception_types],
                'thinking_levels': [dict(tl) for tl in thinking_levels],
                'profiles': [dict(p) for p in profiles],
                'daily': [dict(d) for d in daily]
            }
    
    # ====================== ОЧИСТКА СТАРЫХ ДАННЫХ ======================
    
    async def cleanup_old_data(self, days: int = 30):
        """
        Очищает старые данные (события, неактивные маршруты и т.д.)
        
        Args:
            days: Хранить данные за последние N дней
        """
        async with self.get_connection() as conn:
            # Удаляем старые события
            deleted_events = await conn.execute("""
                DELETE FROM fredi_events
                WHERE created_at < NOW() - INTERVAL '$1 days'
            """, days)
            
            # Деактивируем старые неактивные маршруты (старше 90 дней)
            deleted_routes = await conn.execute("""
                UPDATE fredi_user_routes
                SET is_active = FALSE
                WHERE is_active = TRUE
                  AND updated_at < NOW() - INTERVAL '90 days'
            """)
            
            # Удаляем старые напоминания (отправленные или просроченные более чем на 7 дней)
            deleted_reminders = await conn.execute("""
                DELETE FROM fredi_reminders
                WHERE (is_sent = TRUE AND sent_at < NOW() - INTERVAL '7 days')
                   OR (is_sent = FALSE AND remind_at < NOW() - INTERVAL '7 days')
            """)
            
            logger.info(f"🧹 Очистка данных: {deleted_events} событий, {deleted_routes} маршрутов, {deleted_reminders} напоминаний")
    
    # ====================== МИГРАЦИЯ СУЩЕСТВУЮЩИХ ПОЛЬЗОВАТЕЛЕЙ ======================
    
    async def migrate_existing_users(
        self,
        user_data_dict: Dict[int, Dict],
        user_contexts_dict: Dict[int, Any],
        user_names_dict: Dict[int, str],
        user_routes_dict: Dict[int, Dict]
    ):
        """
        Мигрирует существующих пользователей из памяти в БД
        
        Args:
            user_data_dict: Словарь user_data
            user_contexts_dict: Словарь user_contexts
            user_names_dict: Словарь user_names
            user_routes_dict: Словарь user_routes
        """
        migrated_users = 0
        migrated_contexts = 0
        migrated_data = 0
        migrated_routes = 0
        
        for user_id in set(
            list(user_data_dict.keys()) +
            list(user_contexts_dict.keys()) +
            list(user_names_dict.keys()) +
            list(user_routes_dict.keys())
        ):
            # Сохраняем пользователя
            if user_id in user_names_dict:
                await self.save_telegram_user(
                    user_id=user_id,
                    first_name=user_names_dict[user_id]
                )
                migrated_users += 1
            
            # Сохраняем контекст
            if user_id in user_contexts_dict:
                await self.save_user_context(user_id, user_contexts_dict[user_id])
                migrated_contexts += 1
            
            # Сохраняем данные
            if user_id in user_data_dict:
                await self.save_user_data(user_id, user_data_dict[user_id])
                migrated_data += 1
                
                # Если есть результаты теста, сохраняем их отдельно
                data = user_data_dict[user_id]
                if data.get('profile_data') or data.get('ai_generated_profile'):
                    await self.save_test_result(
                        user_id=user_id,
                        test_type='full_profile',
                        results=data,
                        profile_code=data.get('profile_data', {}).get('display_name'),
                        perception_type=data.get('perception_type'),
                        thinking_level=data.get('thinking_level'),
                        vectors=data.get('behavioral_levels'),
                        deep_patterns=data.get('deep_patterns')
                    )
            
            # Сохраняем маршруты
            if user_id in user_routes_dict:
                route_data = user_routes_dict[user_id]
                await self.save_user_route(
                    user_id=user_id,
                    route_data=route_data,
                    current_step=route_data.get('current_step', 1),
                    progress=route_data.get('progress', [])
                )
                migrated_routes += 1
        
        logger.info(f"✅ Мигрировано: {migrated_users} пользователей, {migrated_contexts} контекстов, "
                   f"{migrated_data} наборов данных, {migrated_routes} маршрутов")
        
        return {
            'users': migrated_users,
            'contexts': migrated_contexts,
            'data': migrated_data,
            'routes': migrated_routes
        }
