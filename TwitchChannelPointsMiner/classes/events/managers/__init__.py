from threading import Thread
from typing import Literal

from TwitchChannelPointsMiner.classes.SlottedTaskRunner import (
    SlottedTaskRunnerThreadFactory,
)
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.entities.predictions.PredictionEvent import (
    PredictionEvent,
)
from TwitchChannelPointsMiner.classes.events.Manager import (
    EventManager,
    EventManagerFactory,
)
from TwitchChannelPointsMiner.classes.events.handlers.Console import (
    ConsoleConfiguration,
    ConsoleHandlerFactory,
)
from TwitchChannelPointsMiner.classes.events.managers.Delegate import (
    DelegatingManagerFactory,
)
from TwitchChannelPointsMiner.classes.events.managers.Priority import (
    PriorityManagerFactory,
)
from TwitchChannelPointsMiner.classes.events.managers.Queue import (
    QueueConfiguration,
    QueueManagerFactory,
)


class DefaultEventManagerFactory(EventManagerFactory):
    """Creates an EventManager that can output events to the console using a priority ConsoleHandler"""

    def __init__(
        self,
        console_configuration: ConsoleConfiguration | Literal[False] | None = None,
        queue_configuration: QueueConfiguration | None = None,
    ):
        self.console_configuration: ConsoleConfiguration | Literal[False] | None = (
            console_configuration
        )
        """The console configuration, or None to default configuration, or False to disable console output"""
        self.queue_configuration = (
            queue_configuration
            if queue_configuration is not None
            else QueueConfiguration(
                task_timeout_seconds=60,
                loop_sleep_seconds=0.5,
                max_concurrent=10,
                runner_loop_interval_seconds=0.5,
            )
        )
        """The queue manager configuration"""

    def create(
        self,
        config: bool,
        background_tasks: list[Thread],
        streamers: list[Streamer],
        prediction_events: dict[str, PredictionEvent],
    ):
        # use a delegating manager to enable deferred setup post task runner creation
        def post_manager_setup(manager: EventManager):
            event_manager_runner_factory = SlottedTaskRunnerThreadFactory(
                max_concurrent=self.queue_configuration.max_concurrent,
                loop_interval_seconds=self.queue_configuration.runner_loop_interval_seconds,
            )
            queue_manager_factory = QueueManagerFactory(
                runner_factory=event_manager_runner_factory,
                configuration=self.queue_configuration,
                event_manager=manager,
            )
            queue_manager = queue_manager_factory.create(
                background_tasks=background_tasks,
                streamers=streamers,
                prediction_events=prediction_events,
            )
            if self.console_configuration is False:
                # Don't output to the console
                return queue_manager
            else:
                # Use a priority manager to avoid slow logging
                priority_manager_factory = PriorityManagerFactory(
                    delegate_manager=queue_manager
                )
                priority_manager = priority_manager_factory.create(
                    background_tasks=background_tasks,
                    streamers=streamers,
                    prediction_events=prediction_events,
                )
                background_tasks.append(queue_manager)

                # Add console handler
                priority_manager.set_priority_handler(
                    ConsoleHandlerFactory(
                        configuration=self.console_configuration
                    ).create()
                )
                return priority_manager

        return DelegatingManagerFactory(post_manager_setup).create(
            background_tasks=background_tasks,
            streamers=streamers,
            prediction_events=prediction_events,
        )
