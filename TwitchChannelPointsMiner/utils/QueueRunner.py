import logging
import time
from collections import deque
from threading import Lock, Thread
from typing import Callable

logger = logging.getLogger(__name__)


class QueueRunner[Item](Thread):
    """A threaded runner that queues items to be processed in turn"""

    def __init__(
        self,
        name: str,
        remove_on_failure: bool,
        sleep_interval_seconds: float,
        process_item: Callable[[Item], bool],
    ):
        super().__init__(name=f"{name} Queue Runner", daemon=True)
        self.remove_on_failure = remove_on_failure
        """
        If True the queued items will be removed on success or failure, 
        if False it will continue retrying an item until successful.
        """
        self.sleep_interval_seconds = sleep_interval_seconds
        """The number of seconds between processing tasks"""
        self.process_item = process_item
        """The function to use when processing items"""
        self.queue = deque[Item]()
        """The underlying queue"""
        self._lock = Lock()
        """Concurrency lock"""
        self.running = False

    def enqueue(self, item: Item):
        """
        Queues the given item to be processed.
        :param item: The item.
        """
        with self._lock:
            self.queue.append(item)

    def run(self):
        self.running = True
        while self.running:
            # Process all items until the queue is empty
            while self.running:
                with self._lock:
                    has_item = len(self.queue) > 0
                # drop the lock early to avoid holding it for too long
                # this is the only place we remove items so it should be fine
                if has_item:
                    item = self.queue[0]
                    if self.process_item(item) or self.remove_on_failure:
                        # Remove from the queue
                        with self._lock:
                            self.queue.popleft()
                else:
                    break
            time.sleep(self.sleep_interval_seconds)

    def shutdown(self):
        self.running = False
