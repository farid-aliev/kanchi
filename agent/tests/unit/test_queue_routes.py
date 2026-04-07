"""Tests for queue routes."""

from collections import namedtuple
from unittest.mock import MagicMock

from api.queue_routes import get_queue_stats


QueueDeclareResult = namedtuple("QueueDeclareResult", ["queue", "message_count", "consumer_count"])


def _make_app_state(monitor=None):
    state = MagicMock()
    state.monitor_instance = monitor
    return state


def _make_monitor(active_queues, counts=None):
    """Create a mock monitor with active_queues response and optional per-queue counts."""
    monitor = MagicMock()
    monitor.app.control.inspect.return_value.active_queues.return_value = active_queues

    if counts is not None:
        channel = MagicMock()
        channel.queue_declare.side_effect = lambda queue, passive: QueueDeclareResult(
            queue=queue, message_count=counts[queue], consumer_count=1
        )
        conn = MagicMock()
        conn.default_channel = channel
        monitor.app.connection_or_acquire.return_value.__enter__ = MagicMock(return_value=conn)
        monitor.app.connection_or_acquire.return_value.__exit__ = MagicMock(return_value=False)

    return monitor


def test_no_monitor_returns_empty():
    state = _make_app_state(monitor=None)
    assert get_queue_stats(state) == []


def test_no_workers_returns_empty():
    monitor = _make_monitor(active_queues=None)
    state = _make_app_state(monitor=monitor)
    assert get_queue_stats(state) == []


def test_returns_pending_counts():
    monitor = _make_monitor(
        active_queues={"worker1": [{"name": "default"}, {"name": "priority"}]},
        counts={"default": 5, "priority": 12},
    )
    state = _make_app_state(monitor=monitor)
    data = get_queue_stats(state)
    assert len(data) == 2
    assert data[0] == {"name": "priority", "pending": 12}
    assert data[1] == {"name": "default", "pending": 5}


def test_sorted_by_pending_desc():
    monitor = _make_monitor(
        active_queues={"worker1": [{"name": "a"}, {"name": "b"}, {"name": "c"}]},
        counts={"a": 1, "b": 100, "c": 50},
    )
    state = _make_app_state(monitor=monitor)
    data = get_queue_stats(state)
    assert [q["pending"] for q in data] == [100, 50, 1]


def test_queue_declare_failure_defaults_to_zero():
    monitor = MagicMock()
    monitor.app.control.inspect.return_value.active_queues.return_value = {
        "worker1": [{"name": "ok"}, {"name": "broken"}],
    }
    channel = MagicMock()

    def declare_side_effect(queue, passive):
        if queue == "broken":
            raise Exception("queue gone")
        return QueueDeclareResult(queue=queue, message_count=3, consumer_count=1)

    channel.queue_declare.side_effect = declare_side_effect
    conn = MagicMock()
    conn.default_channel = channel
    monitor.app.connection_or_acquire.return_value.__enter__ = MagicMock(return_value=conn)
    monitor.app.connection_or_acquire.return_value.__exit__ = MagicMock(return_value=False)

    state = _make_app_state(monitor=monitor)
    data = get_queue_stats(state)
    assert {"name": "ok", "pending": 3} in data
    assert {"name": "broken", "pending": 0} in data


def test_inspect_timeout_returns_empty():
    monitor = MagicMock()
    monitor.app.control.inspect.return_value.active_queues.side_effect = Exception("timeout")
    state = _make_app_state(monitor=monitor)
    assert get_queue_stats(state) == []
