import logging
import time
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Thread

from TwitchChannelPointsMiner.classes.SlottedTaskRunner import (
    SlottedTaskRunner,
)
from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Handler import EventHandler
from TwitchChannelPointsMiner.classes.events.Manager import (
    EventManager,
)
from TwitchChannelPointsMiner.utils.Utils import interruptible_sleep

logger = logging.getLogger(__name__)


@dataclass
class QueueConfiguration:
    task_timeout_seconds: float
    loop_sleep_seconds: float
    max_concurrent: int
    runner_loop_interval_seconds: float


class QueueManager(Thread, EventManager):
    """An Event Manager that queues Events to periodically submit to registered handlers."""

    def __init__(
        self,
        runner: SlottedTaskRunner,
        task_timeout_seconds: float,
        loop_sleep_seconds: float,
        queue: Queue[Event] | None = None,
        handlers: list[EventHandler] | None = None,
    ):
        super().__init__(name="QueueManager", daemon=True)
        self.runner = runner
        self.task_timeout_seconds = task_timeout_seconds
        self.loop_sleep_seconds = loop_sleep_seconds
        self.queue = queue if queue is not None else Queue()
        self.handlers = handlers if handlers is not None else list[EventHandler]()
        self.running = True

    def add_handler(self, handler: EventHandler):
        self.handlers.append(handler)

    def _handle_lambda(self, handler: EventHandler, event: Event):
        return lambda: handler.handle(event)

    def _submit(self, event: Event):
        """
        Submits the event to each handler concurrently.
        :param event: The event to submit.
        """
        for handler in self.handlers:
            if event.type in handler.handles():
                # Avoid being unable to submit a task
                while not self.runner.start_task(
                    context=event,
                    task=self._handle_lambda(handler, event),
                    timeout_seconds=self.task_timeout_seconds,
                    on_complete=None,
                ):
                    # Unfortunate, ideally the manager should be set up with enough threads to avoid this
                    logger.debug(f"All slots full, waiting 0.1 seconds")
                    time.sleep(0.1)

    def manage(self, event: Event):
        self.queue.put_nowait(event)

    def run(self):
        while self.running:
            # Process all events in the queue
            while self.runner.has_free_slot():
                # stop once the runner is full to try and avoid sleeping in _submit
                try:
                    event = self.queue.get_nowait()
                    self._submit(event)
                except Empty:
                    break
            # Once all events that can be processed
            interruptible_sleep(lambda: self.running, self.loop_sleep_seconds)
        self.runner.stop()
