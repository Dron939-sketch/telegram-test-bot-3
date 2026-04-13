"""
mirror_service.py — Завершает зеркальный тест когда друг проходит тест в боте.
Вызывает POST /api/mirrors/complete на бэкенде Фреди.
"""
import os
import logging
import httpx

logger = logging.getLogger(__name__)

FREDI_API_BASE = os.environ.get("FREDI_API_BASE", "https://fredi-backend-flz2.onrender.com")


async def complete_mirror_if_needed(user_id: int, state_data: dict):
    """Если пользователь пришёл по mirror-ссылке, отправляем результаты владельцу зеркала."""
    mirror_code = state_data.get("mirror_code")
    if not mirror_code:
        logger.info(f"🪞 [MIRROR] complete_mirror_if_needed: no mirror_code for user={user_id}")
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

        logger.info(f"🪞 [MIRROR] Sending to {FREDI_API_BASE}/api/mirrors/complete: code={mirror_code}, user={user_id}, vectors={vectors}")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{FREDI_API_BASE}/api/mirrors/complete", json=payload)
            body = resp.text[:200]
            logger.info(f"🪞 [MIRROR] Response: {mirror_code} -> HTTP {resp.status_code}, body={body}")
    except Exception as e:
        logger.error(f"🪞 [MIRROR] Error completing mirror {mirror_code}: {e}", exc_info=True)
