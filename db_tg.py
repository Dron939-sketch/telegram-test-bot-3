#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для сохранения данных Telegram бота в единую БД Фреди (fredi_db_flz2)
Версия 1.0 - прямые asyncpg вызовы без пула
"""

import os
import json
import logging
import asyncio
import asyncpg
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================
# ПОДКЛЮЧЕНИЕ
# ============================================

_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://fredi_db_flz2_user:PP1FP91G1P6mn1uS8iBLGlk38bKqzkGy@dpg-d739b31r0fns739a7oj0-a.oregon-postgres.render.com/fredi_db_flz2"
).replace("?sslmode=require", "").replace("?ssl=true", "").strip()


async def _get_conn() -> asyncpg.Connection:
    """Создаёт новое соединение с БД"""
    return await asyncpg.connect(_DB_URL, ssl='require', timeout=15)


# ============================================
# ПОЛЬЗОВАТЕЛИ
# ============================================

async def save_user(user_id: int, username: str = None,
                    first_name: str = None, last_name: str = None):
    """Сохраняет или обновляет пользователя"""
    try:
        conn = await _get_conn()
        try:
            await conn.execute("""
                INSERT INTO fredi_users (
                    user_id, username, first_name, last_name,
                    created_at, updated_at, last_activity
                ) VALUES ($1, $2, $3, $4, NOW(), NOW(), NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    updated_at = NOW(),
                    last_activity = NOW()
            """, user_id, username, first_name, last_name)
            logger.info(f"💾 Пользователь {user_id} сохранён")
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"⚠️ save_user {user_id}: {e}")


async def load_user_data(user_id: int) -> Optional[Dict]:
    """Загружает данные пользователя из БД"""
    try:
        conn = await _get_conn()
        try:
            row = await conn.fetchrow(
                "SELECT data FROM fredi_user_data WHERE user_id = $1", user_id)
            if row and row['data']:
                data = row['data']
                return data if isinstance(data, dict) else json.loads(data)
            return None
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"⚠️ load_user_data {user_id}: {e}")
        return None


async def load_user_context(user_id: int) -> Optional[Dict]:
    """Загружает контекст пользователя из БД"""
    try:
        conn = await _get_conn()
        try:
            row = await conn.fetchrow(
                "SELECT * FROM fredi_user_contexts WHERE user_id = $1", user_id)
            return dict(row) if row else None
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"⚠️ load_user_context {user_id}: {e}")
        return None


# ============================================
# СОХРАНЕНИЕ ДАННЫХ ТЕСТА
# ============================================

async def save_test_data(user_id: int, data: Dict):
    """Сохраняет данные теста (FSM state data) в fredi_user_data"""
    try:
        conn = await _get_conn()
        try:
            # Убеждаемся что пользователь существует
            await conn.execute("""
                INSERT INTO fredi_users (user_id, created_at, updated_at, last_activity)
                VALUES ($1, NOW(), NOW(), NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    last_activity = NOW(), updated_at = NOW()
            """, user_id)

            # Сохраняем данные
            json_data = json.dumps(data, default=str, ensure_ascii=False)
            await conn.execute("""
                INSERT INTO fredi_user_data (user_id, data, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    data = $2, updated_at = NOW()
            """, user_id, json_data)
            logger.debug(f"💾 Данные теста {user_id} сохранены")
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"⚠️ save_test_data {user_id}: {e}")


async def save_context(user_id: int, context):
    """Сохраняет UserContext в fredi_user_contexts"""
    try:
        conn = await _get_conn()
        try:
            await conn.execute("""
                INSERT INTO fredi_users (user_id, created_at, updated_at, last_activity)
                VALUES ($1, NOW(), NOW(), NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    last_activity = NOW(), updated_at = NOW()
            """, user_id)

            weather_json = None
            if hasattr(context, 'weather_cache') and context.weather_cache:
                weather_json = json.dumps(context.weather_cache, ensure_ascii=False)

            await conn.execute("""
                INSERT INTO fredi_user_contexts (
                    user_id, name, age, gender, city,
                    communication_mode, weather_cache,
                    family_status, has_children, energy_level,
                    life_context_complete, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    age = EXCLUDED.age,
                    gender = EXCLUDED.gender,
                    city = EXCLUDED.city,
                    communication_mode = EXCLUDED.communication_mode,
                    weather_cache = EXCLUDED.weather_cache,
                    family_status = EXCLUDED.family_status,
                    has_children = EXCLUDED.has_children,
                    energy_level = EXCLUDED.energy_level,
                    life_context_complete = EXCLUDED.life_context_complete,
                    updated_at = NOW()
            """,
                user_id,
                getattr(context, 'name', None),
                getattr(context, 'age', None),
                getattr(context, 'gender', None),
                getattr(context, 'city', None),
                getattr(context, 'communication_mode', 'coach'),
                weather_json,
                getattr(context, 'family_status', None),
                getattr(context, 'has_children', False),
                getattr(context, 'energy_level', None),
                getattr(context, 'life_context_complete', False),
            )
            logger.debug(f"💾 Контекст {user_id} сохранён")
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"⚠️ save_context {user_id}: {e}")


async def save_test_result(user_id: int, data: Dict):
    """Сохраняет финальный результат теста в fredi_test_results"""
    try:
        profile_data = data.get('profile_data', {})
        behavioral_levels = data.get('behavioral_levels', {})
        perception_type = data.get('perception_type')
        thinking_level = data.get('thinking_level')
        logger.info(f"📊 save_test_result {user_id}: profile={profile_data.get('display_name')}, perception={perception_type}, thinking={thinking_level}")

        # Считаем векторы
        vectors = {}
        for k, levels in behavioral_levels.items():
            vectors[k] = sum(levels) / len(levels) if levels else 3.0

        conn = await _get_conn()
        try:
            await conn.execute("""
                INSERT INTO fredi_test_results (
                    user_id, test_type, results,
                    profile_code, perception_type, thinking_level,
                    vectors, behavioral_levels, deep_patterns
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                user_id,
                'full_profile',
                json.dumps(data, default=str, ensure_ascii=False),
                profile_data.get('display_name'),
                perception_type,
                thinking_level,
                json.dumps(vectors, ensure_ascii=False),
                json.dumps(behavioral_levels, ensure_ascii=False),
                json.dumps(data.get('deep_patterns', {}), ensure_ascii=False),
            )
            logger.info(f"💾 Результат теста {user_id} сохранён")
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"⚠️ save_test_result {user_id}: {e}")


def save_test_data_sync(user_id: int, data: Dict, extra: Dict = None):
    """Синхронная обёртка — запускает сохранение в фоне"""
    if extra:
        merged = {**data, **extra}
    else:
        merged = data
    asyncio.create_task(save_test_data(user_id, merged))


def save_context_sync(user_id: int, context):
    """Синхронная обёртка — запускает сохранение в фоне"""
    asyncio.create_task(save_context(user_id, context))
