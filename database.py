# database.py
import asyncpg
import json
import pickle
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class BotDatabase:
    """База данных для бота на PostgreSQL"""
    
    def __init__(self, dsn: str):
        """
        Инициализация с DSN строкой подключения
        Пример: postgresql://user:pass@host:port/db
        """
        self.dsn = dsn
        self.pool = None
    
    async def connect(self):
        """Создаёт пул соединений"""
        self.pool = await asyncpg.create_pool(self.dsn)
        await self.init_database()
        logger.info("✅ Подключение к БД установлено")
    
    async def disconnect(self):
        """Закрывает пул соединений"""
        if self.pool:
            await self.pool.close()
            logger.info("✅ Подключение к БД закрыто")
    
    @asynccontextmanager
    async def get_connection(self):
        """Контекстный менеджер для получения соединения"""
        async with self.pool.acquire() as conn:
            yield conn
    
    async def init_database(self):
        """Создаёт таблицы с префиксом fredi_"""
        async with self.get_connection() as conn:
            # Таблица пользователей Telegram
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fredi_telegram_users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language_code TEXT,
                    is_bot BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для данных пользователей (user_data)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fredi_user_data (
                    user_id BIGINT PRIMARY KEY,
                    data JSONB NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES fredi_telegram_users(user_id) ON DELETE CASCADE
                )
            """)
            
            # Таблица для контекста пользователей (UserContext)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fredi_user_contexts (
                    user_id BIGINT PRIMARY KEY,
                    context BYTEA NOT NULL,  -- pickle объект
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES fredi_telegram_users(user_id) ON DELETE CASCADE
                )
            """)
            
            # Таблица для маршрутов пользователей
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fredi_user_routes (
                    user_id BIGINT PRIMARY KEY,
                    route_data JSONB,
                    current_step INTEGER DEFAULT 1,
                    progress JSONB,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES fredi_telegram_users(user_id) ON DELETE CASCADE
                )
            """)
            
            # Таблица для результатов тестов
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fredi_test_results (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    test_type TEXT NOT NULL,
                    results JSONB NOT NULL,
                    profile_code TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES fredi_telegram_users(user_id) ON DELETE CASCADE
                )
            """)
            
            # Таблица для статистики событий
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fredi_events (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    event_type TEXT NOT NULL,
                    event_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица для напоминаний
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS fredi_reminders (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    reminder_type TEXT NOT NULL,
                    remind_at TIMESTAMP NOT NULL,
                    data JSONB,
                    is_sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES fredi_telegram_users(user_id) ON DELETE CASCADE
                )
            """)
            
            # Индексы для ускорения
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_fredi_events_user_id ON fredi_events(user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_fredi_events_created_at ON fredi_events(created_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_fredi_reminders_remind_at ON fredi_reminders(remind_at)")
            
            logger.info("✅ Таблицы fredi_* созданы/проверены")
    
    # === РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ===
    
    async def save_telegram_user(self, user_id: int, **kwargs):
        """Сохраняет или обновляет информацию о пользователе"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO fredi_telegram_users 
                (user_id, username, first_name, last_name, language_code, is_bot, last_seen)
                VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    language_code = EXCLUDED.language_code,
                    last_seen = CURRENT_TIMESTAMP
            """, 
                user_id,
                kwargs.get('username'),
                kwargs.get('first_name'),
                kwargs.get('last_name'),
                kwargs.get('language_code'),
                kwargs.get('is_bot', False)
            )
    
    async def get_telegram_user(self, user_id: int) -> Optional[Dict]:
        """Получает информацию о пользователе"""
        async with self.get_connection() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM fredi_telegram_users WHERE user_id = $1",
                user_id
            )
            return dict(row) if row else None
    
    # === РАБОТА С ДАННЫМИ ПОЛЬЗОВАТЕЛЯ (user_data) ===
    
    async def save_user_data(self, user_id: int, data: Dict[str, Any]):
        """Сохраняет user_data"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO fredi_user_data (user_id, data, updated_at)
                VALUES ($1, $2::jsonb, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    data = EXCLUDED.data,
                    updated_at = CURRENT_TIMESTAMP
            """, user_id, json.dumps(data, ensure_ascii=False))
    
    async def load_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Загружает user_data"""
        async with self.get_connection() as conn:
            row = await conn.fetchrow(
                "SELECT data FROM fredi_user_data WHERE user_id = $1",
                user_id
            )
            return dict(row['data']) if row else None
    
    # === РАБОТА С КОНТЕКСТОМ ===
    
    async def save_user_context(self, user_id: int, context):
        """Сохраняет объект UserContext (через pickle)"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO fredi_user_contexts (user_id, context, updated_at)
                VALUES ($1, $2, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    context = EXCLUDED.context,
                    updated_at = CURRENT_TIMESTAMP
            """, user_id, pickle.dumps(context))
    
    async def load_user_context(self, user_id: int):
        """Загружает объект UserContext"""
        async with self.get_connection() as conn:
            row = await conn.fetchrow(
                "SELECT context FROM fredi_user_contexts WHERE user_id = $1",
                user_id
            )
            return pickle.loads(row['context']) if row else None
    
    # === РАБОТА С МАРШРУТАМИ ===
    
    async def save_user_route(self, user_id: int, route_data: Dict, step: int = 1, progress: List = None):
        """Сохраняет маршрут пользователя"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO fredi_user_routes (user_id, route_data, current_step, progress, updated_at)
                VALUES ($1, $2::jsonb, $3, $4::jsonb, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    route_data = EXCLUDED.route_data,
                    current_step = EXCLUDED.current_step,
                    progress = EXCLUDED.progress,
                    updated_at = CURRENT_TIMESTAMP
            """, user_id, json.dumps(route_data), step, json.dumps(progress or []))
    
    async def load_user_route(self, user_id: int) -> Optional[Dict]:
        """Загружает маршрут пользователя"""
        async with self.get_connection() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM fredi_user_routes WHERE user_id = $1",
                user_id
            )
            if row:
                return {
                    'route_data': dict(row['route_data']),
                    'current_step': row['current_step'],
                    'progress': list(row['progress']) if row['progress'] else []
                }
            return None
    
    # === РЕЗУЛЬТАТЫ ТЕСТОВ ===
    
    async def save_test_result(self, user_id: int, test_type: str, results: Dict, profile_code: str = None):
        """Сохраняет результат теста"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO fredi_test_results (user_id, test_type, results, profile_code)
                VALUES ($1, $2, $3::jsonb, $4)
            """, user_id, test_type, json.dumps(results), profile_code)
    
    async def get_user_test_results(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Получает последние результаты тестов пользователя"""
        async with self.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT * FROM fredi_test_results 
                WHERE user_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2
            """, user_id, limit)
            return [dict(row) for row in rows]
    
    # === СОБЫТИЯ И СТАТИСТИКА ===
    
    async def log_event(self, user_id: int, event_type: str, event_data: Dict = None):
        """Логирует событие"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO fredi_events (user_id, event_type, event_data)
                VALUES ($1, $2, $3::jsonb)
            """, user_id, event_type, json.dumps(event_data or {}))
    
    async def get_stats(self, days: int = 30) -> Dict:
        """Получает статистику за последние N дней"""
        async with self.get_connection() as conn:
            # Активные пользователи
            active = await conn.fetchval("""
                SELECT COUNT(DISTINCT user_id) 
                FROM fredi_events 
                WHERE created_at > CURRENT_TIMESTAMP - $1::interval
            """, f"{days} days")
            
            # Всего пользователей
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM fredi_telegram_users"
            )
            
            # События по дням
            daily = await conn.fetch("""
                SELECT 
                    DATE(created_at) as day,
                    COUNT(*) as count
                FROM fredi_events
                WHERE created_at > CURRENT_TIMESTAMP - $1::interval
                GROUP BY DATE(created_at)
                ORDER BY day DESC
            """, f"{days} days")
            
            # Типы событий
            event_types = await conn.fetch("""
                SELECT 
                    event_type,
                    COUNT(*) as count
                FROM fredi_events
                WHERE created_at > CURRENT_TIMESTAMP - $1::interval
                GROUP BY event_type
                ORDER BY count DESC
            """, f"{days} days")
            
            return {
                'total_users': total,
                'active_users': active,
                'daily_events': [dict(row) for row in daily],
                'event_types': [dict(row) for row in event_types]
            }
    
    # === НАПОМИНАНИЯ ===
    
    async def add_reminder(self, user_id: int, reminder_type: str, remind_at: datetime, data: Dict = None):
        """Добавляет напоминание"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO fredi_reminders (user_id, reminder_type, remind_at, data)
                VALUES ($1, $2, $3, $4::jsonb)
            """, user_id, reminder_type, remind_at, json.dumps(data or {}))
    
    async def get_pending_reminders(self) -> List[Dict]:
        """Получает все неотправленные напоминания, которые уже пора отправить"""
        async with self.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT * FROM fredi_reminders 
                WHERE remind_at <= CURRENT_TIMESTAMP 
                AND is_sent = FALSE
                ORDER BY remind_at
            """)
            return [dict(row) for row in rows]
    
    async def mark_reminder_sent(self, reminder_id: int):
        """Отмечает напоминание как отправленное"""
        async with self.get_connection() as conn:
            await conn.execute(
                "UPDATE fredi_reminders SET is_sent = TRUE WHERE id = $1",
                reminder_id
            )
    
    # === ОЧИСТКА СТАРЫХ ДАННЫХ ===
    
    async def cleanup_old_data(self, days: int = 30):
        """Очищает старые события и отправленные напоминания"""
        async with self.get_connection() as conn:
            # Удаляем старые события
            events = await conn.execute("""
                DELETE FROM fredi_events 
                WHERE created_at < CURRENT_TIMESTAMP - $1::interval
            """, f"{days} days")
            
            # Удаляем отправленные напоминания старше 7 дней
            reminders = await conn.execute("""
                DELETE FROM fredi_reminders 
                WHERE is_sent = TRUE 
                AND created_at < CURRENT_TIMESTAMP - INTERVAL '7 days'
            """)
            
            logger.info(f"🧹 Очистка: удалено {events} событий, {reminders} напоминаний")
