import logging
from threading import Thread
from typing import Literal

from TwitchChannelPointsMiner.classes.SlottedTaskRunner import (
    SlottedTaskRunnerFactory,
    SlottedTaskRunnerThreadFactory,
)
from TwitchChannelPointsMiner.classes.events.Events import Events
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.classes.events.Transformer import EventTransformerFactory
from TwitchChannelPointsMiner.classes.events.handlers.Console import (
    ConsoleHandler,
)
from TwitchChannelPointsMiner.classes.events.managers.Delegate import (
    DelegatingManager,
)
from TwitchChannelPointsMiner.classes.events.managers.Factory import (
    EventManagerConfiguration,
    EventManagerFactory,
)
from TwitchChannelPointsMiner.classes.events.managers.Ignore import IgnoreEventManager
from TwitchChannelPointsMiner.classes.events.managers.Priority import (
    PriorityManager,
)
from TwitchChannelPointsMiner.classes.events.managers.Queue import (
    QueueConfiguration,
    QueueManager,
)
from TwitchChannelPointsMiner.classes.events.transformers import (
    DefaultTransformerFactory,
)
from TwitchChannelPointsMiner.logger import LoggerSettings

logger = logging.getLogger(__name__)


class DefaultEventManagerFactory(EventManagerFactory):
    """Creates an EventManager that can output events to the console using a priority ConsoleHandler"""

    def __init__(
        self,
        runner_factory: SlottedTaskRunnerFactory | None = None,
        transformer_factory: EventTransformerFactory[str] | None = None,
    ):
        self.runner_factory = runner_factory
        self.transformer_factory = transformer_factory
        self._manager = None

    def _create(
        self,
        config: EventManagerConfiguration | Literal[True] | None,
        settings: LoggerSettings,
        background_tasks: list[Thread],
    ) -> EventManager:
        logger.info(f"Creating event manager")
        # Ignore any events if configuration is None
        if config is None:
            logger.info(f"Ignoring all events")
            return IgnoreEventManager()

        # If True, use the default
        if config is True:
            logger.info(f"Using default config")
            config = EventManagerConfiguration()

        # use a delegating manager to enable deferred management of task runner events
        manager = DelegatingManager()
        # Setup queue
        queue_config = (
            config.queue
            if config.queue is not None
            else QueueConfiguration(
                task_timeout_seconds=60,
                loop_sleep_seconds=0.5,
                max_concurrent=10,
                runner_loop_interval_seconds=0.5,
            )
        )
        # Either use the base runner factory or use the values from the config to create a thread factory
        task_runner_factory = (
            self.runner_factory
            if self.runner_factory is not None
            else SlottedTaskRunnerThreadFactory(
                max_concurrent=queue_config.max_concurrent,
                loop_interval_seconds=queue_config.runner_loop_interval_seconds,
            )
        )
        runner = task_runner_factory.create(
            name="Queue Event Manager", event_manager=manager
        )
        queue_manager = QueueManager(
            runner=runner,
            task_timeout_seconds=queue_config.task_timeout_seconds,
            loop_sleep_seconds=queue_config.loop_sleep_seconds,
        )
        queue_manager.start()
        background_tasks.append(queue_manager)
        if not config.console:
            logger.info(f"Not using console")
            # Don't output to the console
            manager.set_manager(queue_manager)
        else:
            logger.info(f"Using console")
            # Use a priority manager to avoid slow logging
            priority_manager = PriorityManager(delegate_manager=queue_manager)
            # Add console handler
            transformer_factory = (
                self.transformer_factory
                if self.transformer_factory is not None
                else DefaultTransformerFactory()
            )
            priority_manager.set_priority_handler(
                ConsoleHandler(
                    events=Events.reduce(config.events),
                    transformer=transformer_factory.create(settings=settings),
                )
            )
            manager.set_manager(priority_manager)
        return manager

    def create(
        self,
        config: EventManagerConfiguration | Literal[True] | None,
        settings: LoggerSettings,
        background_tasks: list[Thread],
    ):
        # By default, use a singleton manager
        if self._manager is None:
            self._manager = self._create(config, settings, background_tasks)
        return self._manager
