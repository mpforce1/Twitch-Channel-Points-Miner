from queue import Empty, Queue

from TwitchChannelPointsMiner.classes.SlottedTaskRunner import SlottedTaskRunner
from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Handler import Handler
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.utils.Utils import interruptible_sleep


class QueueManager(EventManager):
    """An Event Manager that queues Events to periodically submit to registered handlers."""

    def __init__(
        self,
        runner: SlottedTaskRunner,
        task_timeout_seconds: float,
        loop_sleep_seconds: float,
        queue: Queue[Event] | None = None,
        handlers: list[Handler] | None = None,
    ):
        super().__init__(name="QueueManager", daemon=True)
        self.runner = runner
        self.task_timeout_seconds = task_timeout_seconds
        self.loop_sleep_seconds = loop_sleep_seconds
        self.queue = queue if queue is not None else Queue()
        self.handlers = handlers if handlers is not None else list[Handler]()
        self.running = True

    def add_handler(self, handler: Handler):
        self.handlers.append(handler)

    def _handle_lambda(self, handler: Handler, event: Event):
        return lambda: handler.handle(event)

    def _submit(self, event: Event):
        """
        Submits the event to each handler concurrently.
        :param event: The event to submit.
        """
        for handler in self.handlers:
            if event.type in handler.handles():
                self.runner.start_task(
                    context=event,
                    task=self._handle_lambda(handler, event),
                    timeout_seconds=self.task_timeout_seconds,
                    on_complete=None,
                )

    def manage(self, event: Event):
        self.queue.put_nowait(event)

    def run(self):
        while self.running:
            try:
                event = self.queue.get_nowait()
                self._submit(event)
            except Empty:
                pass
            interruptible_sleep(lambda: self.running, self.loop_sleep_seconds)
        self.runner.stop()
