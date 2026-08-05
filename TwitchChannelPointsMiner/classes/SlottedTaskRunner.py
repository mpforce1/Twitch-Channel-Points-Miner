import abc
import logging
import time
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from threading import Lock, Thread
from typing import Callable

from TwitchChannelPointsMiner.classes.events.Event import Error
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.utils import interruptible_sleep

logger = logging.getLogger(__name__)


@dataclass
class Slot[Context, Result]:
    context: Context
    """The context for this slot."""
    future: Future[Result]
    """The submitted task."""
    start_time: float
    """The time the task was started."""
    timeout_seconds: float
    """The amount of seconds the task is allowed to run."""
    on_complete: Callable[[Context, Result], None] | None
    """A callback that will be called upon task completion."""


class SlottedTaskRunner[Context, Result](abc.ABC):
    """Runs tasks in a given number of "Slots" that can only be occupied by 1 task at a time."""

    @abc.abstractmethod
    def has_free_slot(self) -> bool:
        """
        Checks if this runner has any free slots.
        :return: True if there are any free slots, False otherwise.
        """
        pass

    @abc.abstractmethod
    def has_context(self, context: Context) -> bool:
        """
        Checks if the given context is currently being used by one of the Slots.
        :param context: The context to check.
        :return: True if the context is in one of the slots, False otherwise.
        """
        pass

    @abc.abstractmethod
    def start_task(
        self,
        context: Context,
        task: Callable[[], Result],
        timeout_seconds: float,
        on_complete: Callable[[Context, Result], None] | None,
    ) -> bool:
        """
        Runs the given task if there's a free slot.
        :param context: The context for the task.
        :param task: The task to run.
        :param timeout_seconds: The number of seconds to run the task before timing out.
        :param on_complete: A callback that is called when the result is obtained.
        :return: True if the task could be started, False otherwise.
        """
        pass

    def stop(self):
        """
        Stops this runner and any remaining tasks.
        :return:
        """
        pass


class SlottedTaskRunnerThread[Context, Result](
    SlottedTaskRunner[Context, Result], Thread
):

    def __init__(
        self,
        name: str,
        event_manager: EventManager,
        max_concurrent: int | None = 2,
        loop_interval_seconds: float = 20,
    ):
        super().__init__(name=f"{name} Runner", daemon=True)
        self.event_manager = event_manager
        if max_concurrent is not None and max_concurrent <= 0:
            raise ValueError(f"max_concurrent must be greater than 0: {max_concurrent}")
        self.max_concurrent = max_concurrent
        """ The maximum amount of tasks to run concurrently. """
        self.loop_interval_seconds = loop_interval_seconds
        """ The amount of seconds in between iterations of the watch loop. """
        self._executor = ThreadPoolExecutor(
            max_workers=self.max_concurrent,
            thread_name_prefix="weekly_reawrds_watcher",
        )
        if max_concurrent is None:
            self._slots = list[Slot[Context, Result] | None]()
        else:
            self._slots: list[Slot[Context, Result] | None] = [
                None for _ in range(max_concurrent)
            ]
        self.running = False
        self._lock = Lock()

    def has_free_slot(self) -> bool:
        with self._lock:
            return any(slot is None for slot in self._slots)

    def has_context(self, context: Context):
        with self._lock:
            return any(
                slot.context == context for slot in self._slots if slot is not None
            )

    def start_task(
        self,
        context: Context,
        task: Callable[[], Result],
        timeout_seconds: float,
        on_complete: Callable[[Context, Result], None] | None,
    ) -> bool:
        with self._lock:
            for index, slot in enumerate(self._slots):
                if slot is None:
                    logger.debug(f"{self.name}: Submitting {context} in slot {index}")
                    future = self._executor.submit(task)
                    self._slots[index] = Slot(
                        context=context,
                        future=future,
                        start_time=time.monotonic(),
                        timeout_seconds=timeout_seconds,
                        on_complete=on_complete,
                    )
                    return True
            return False

    def manage_slots(self):
        """
        Checks the slots and removes items that have finished or timed out.
        """
        with self._lock:
            for slot_index in range(len(self._slots)):
                slot = self._slots[slot_index]
                if slot is not None:
                    try:
                        done = False
                        if slot.future.done():
                            logger.debug(
                                f"{self.name}: Slot {slot_index} done: {slot.context}"
                            )
                            self._slots[slot_index] = None
                            done = True
                        elif time.monotonic() - slot.start_time > slot.timeout_seconds:
                            logger.debug(
                                f"{self.name}: Slot {slot_index} timed out: {slot.context}"
                            )
                            self.event_manager.manage(
                                Error(
                                    context=self.name,
                                    message=f"Slot {slot_index} timed out for {slot.context}",
                                    error=None,
                                )
                            )
                            self._slots[slot_index] = None
                            done = True
                    except Exception as e:
                        logger.error(
                            f"{self.name}: Slot {slot_index} for: {slot.context}: error: {e}"
                        )
                        self.event_manager.manage(
                            Error(
                                context=self.name,
                                message=f"Error processing slot {slot_index} for {slot.context}",
                                error=e,
                            )
                        )
                        self._slots[slot_index] = None
                        done = True
                    if done:
                        try:
                            result = next(
                                futures.as_completed([slot.future], timeout=0)
                            ).result(timeout=0)
                            if slot.on_complete is not None:
                                slot.on_complete(slot.context, result)
                        except TimeoutError:
                            pass
                        except Exception as e:
                            logger.error(f"Exception processing result: {e}")
                            self.event_manager.manage(
                                Error(
                                    context=self.name,
                                    message=f"Exception processing result for {slot.context}",
                                    error=e,
                                )
                            )

    def run(self):
        """
        Periodically checks all Streamers weekly reward status and attempts to watch Clips/VODs for those that haven't
        yet advanced theirs today/this week.
        """
        self.running = True
        try:
            while self.running:
                self.manage_slots()
                interruptible_sleep(
                    running_flag=lambda: self.running,
                    duration=self.loop_interval_seconds,
                )
        finally:
            logger.debug("SlottedTaskRunner Stopping")
            # Wait for any running tasks to finish
            # they should be implemented in a way that periodically checks if they need to end early
            self._executor.shutdown(wait=True, cancel_futures=True)
            logger.debug("SlottedTaskRunner Stopped")

    def stop(self):
        self.running = False


class SlottedTaskRunnerFactory(abc.ABC):
    @abc.abstractmethod
    def create[Context, Result](
        self, name: str, event_manager: EventManager
    ) -> SlottedTaskRunner[
        Context, Result
    ]:  # pyright: ignore [reportInvalidTypeVarUse]
        pass


class SlottedTaskRunnerThreadFactory(SlottedTaskRunnerFactory):
    def __init__(self, max_concurrent: int = 3, loop_interval_seconds: float = 20):
        self.max_concurrent = max_concurrent
        self.loop_interval_seconds = loop_interval_seconds

    def create[Context, Result](
        self, name: str, event_manager: EventManager
    ) -> SlottedTaskRunner[
        Context, Result
    ]:  # pyright: ignore [reportInvalidTypeVarUse]
        runner = SlottedTaskRunnerThread[Context, Result](
            name=name,
            event_manager=event_manager,
            max_concurrent=self.max_concurrent,
            loop_interval_seconds=self.loop_interval_seconds,
        )
        runner.start()
        return runner
