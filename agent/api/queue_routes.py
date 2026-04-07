"""API routes for queue-related endpoints."""

from typing import List, Dict
from fastapi import APIRouter, Depends
from config import Config
from security.dependencies import get_auth_dependency


def get_queue_stats(app_state) -> List[Dict]:
    """Get pending task counts per queue from the broker."""
    if not app_state.monitor_instance:
        return []

    app = app_state.monitor_instance.app

    # Discover queues from workers
    try:
        inspector = app.control.inspect(timeout=1.0)
        active_queues_resp = inspector.active_queues() or {}
    except Exception:
        return []

    queue_names = set()
    for worker_queues in active_queues_resp.values():
        for q in worker_queues:
            queue_names.add(q["name"])

    if not queue_names:
        return []

    # Get pending message count per queue from broker
    stats = []
    try:
        with app.connection_or_acquire() as conn:
            for name in sorted(queue_names):
                try:
                    result = conn.default_channel.queue_declare(
                        queue=name, passive=True
                    )
                    stats.append({
                        "name": name,
                        "pending": result.message_count,
                    })
                except Exception:
                    stats.append({"name": name, "pending": 0})
    except Exception:
        return []

    stats.sort(key=lambda q: q["pending"], reverse=True)
    return stats


def create_router(app_state) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["queues"])

    config = app_state.config or Config.from_env()
    require_user_dep = get_auth_dependency(app_state, require=True)
    if config.auth_enabled:
        router.dependencies.append(Depends(require_user_dep))

    @router.get("/queues")
    def get_queues() -> List[Dict]:
        return get_queue_stats(app_state)

    return router
