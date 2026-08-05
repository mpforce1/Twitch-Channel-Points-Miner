from typing import Any
from unittest.mock import MagicMock

from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Handler import EventHandler
from TwitchChannelPointsMiner.classes.events.Event import StreamUp
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.classes.events.managers.Priority import PriorityManager
from TwitchChannelPointsMiner.classes.events.managers.Queue import QueueManager


def test_queue_manager():
    runner = MagicMock()
    task_timeout_seconds = 1
    loop_sleep_seconds = 1

    manager = QueueManager(
        runner=runner,
        task_timeout_seconds=task_timeout_seconds,
        loop_sleep_seconds=loop_sleep_seconds,
    )

    event_type = Events.STREAMER_ONLINE

    handler = MagicMock(spec=EventHandler)
    handler.handles.return_value = event_type
    manager.add_handler(handler)

    event: Any = MagicMock(spec=StreamUp)
    event.type = Events.STREAMER_ONLINE

    manager.manage(event)

    # Managing an event should put it in the queue
    assert manager.queue.get_nowait() == event

    manager._submit(event)

    # Submitting a handled event should put it in the runner
    handler.handles.assert_called_once()
    runner.start_task.assert_called_once()

    event.type = Events.STREAMER_OFFLINE
    manager._submit(event)

    # handler.handles() should get called again
    assert handler.handles.call_count == 2
    # The runner shouldn't be called again as it's not handled
    runner.start_task.assert_called_once()


def test_priority_manager():
    delegate_manager = MagicMock(spec=EventManager)
    manager = PriorityManager(delegate_manager=delegate_manager)

    event = MagicMock(spec=StreamUp)
    event.type = Events.STREAMER_ONLINE

    # No priority handler
    manager.manage(event)
    # No exception, delegate gets called
    delegate_manager.manage.assert_called_once_with(event)

    # add handler
    handler = MagicMock(spec=EventHandler)
    handler.handles.return_value = Events.STREAMER_ONLINE

    manager.set_priority_handler(handler)

    manager.manage(event)
    # Handler called
    handler.handles.assert_called_once()
    handler.handle.assert_called_once()
    # manage called again
    assert delegate_manager.manage.call_count == 2

    # Unhandled event
    event.type = Events.STREAMER_OFFLINE
    manager.manage(event)
    # Handler.handle not called again
    assert handler.handles.call_count == 2
    handler.handle.assert_called_once()
    # manage called again
    assert delegate_manager.manage.call_count == 3
