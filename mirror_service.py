"""
mirror_service.py — Завершает зеркальный тест когда друг проходит тест в боте.
Вызывает POST /api/mirrors/complete на бэкенде Фреди.

Логика: НЕ зависим от FSM state. Берём mirror_code из БД через
GET /api/mirrors/pending/{friend_user_id}. Одна БД для всех платформ.
"""
import os
import logging
import httpx

logger = logging.getLogger(__name__)

FREDI_API_BASE = os.environ.get("FREDI_API_BASE", "https://fredi-backend-flz2.onrender.com")


async def complete_mirror_if_needed(user_id: int, state_data: dict):
    """Проверяет БД на pending зеркало и завершает его."""

    # 1. Сначала пробуем из state (если повезло и не потерялось)
    mirror_code = state_data.get("mirror_code")

    # 2. Если в state нет — спрашиваем БД напрямую
    if not mirror_code:
        mirror_code = await _check_db_for_mirror(user_id)

    if not mirror_code:
        logger.info(f"🪞 [MIRROR] No mirror for user={user_id} (checked state + DB)")
        return

    try:
        vectors = {}
        for k, levels in (state_data.get("behavioral_levels") or {}).items():
            vectors[k] = sum(levels) / len(levels) if levels else 3.0

        profile_data = state_data.get("profile_data") or {}

        payload = {
            "mirror_code": mirror_code,
            "friend_user_id": user_id,
            "friend_name": state_data.get("user_name", "Друг"),
            "friend_profile_code": profile_data.get("display_name") if isinstance(profile_data, dict) else None,
            "friend_vectors": vectors,
            "friend_deep_patterns": state_data.get("deep_patterns") or {},
            "friend_ai_profile": state_data.get("ai_generated_profile", ""),
            "friend_perception_type": state_data.get("perception_type"),
            "friend_thinking_level": state_data.get("thinking_level"),
        }

        logger.info(f"🪞 [MIRROR] Sending complete: code={mirror_code}, user={user_id}, vectors={vectors}")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{FREDI_API_BASE}/api/mirrors/complete", json=payload)
            body = resp.text[:200]
            logger.info(f"🪞 [MIRROR] Response: {mirror_code} -> HTTP {resp.status_code}, body={body}")
    except Exception as e:
        logger.error(f"🪞 [MIRROR] Error completing mirror {mirror_code}: {e}", exc_info=True)


async def _check_db_for_mirror(user_id: int):
    """Проверяет БД: есть ли активное зеркало где friend_user_id = этот пользователь."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{FREDI_API_BASE}/api/mirrors/pending/{user_id}")
            if resp.status_code == 200:
                data = resp.json()
                code = data.get("mirror_code")
                if code:
                    logger.info(f"🪞 [MIRROR] Found pending mirror in DB: user={user_id}, code={code}")
                    return code
    except Exception as e:
        logger.error(f"🪞 [MIRROR] DB check error: {e}")
    return None
