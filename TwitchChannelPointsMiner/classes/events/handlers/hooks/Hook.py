import logging
from typing import Protocol

import requests

from TwitchChannelPointsMiner.classes.Settings import Events
from TwitchChannelPointsMiner.classes.events.Event import Event
from TwitchChannelPointsMiner.classes.events.Handler import EventHandler
from TwitchChannelPointsMiner.classes.events.Transformer import EventTransformer
from TwitchChannelPointsMiner.utils.AttemptStrategy import (
    AttemptStrategy,
    SuccessResult,
)
from TwitchChannelPointsMiner.utils.QueueRunner import QueueRunner

logger = logging.getLogger(__name__)


class PostRequest(Protocol):
    def __call__(
        self, url: str, data: dict[str, str] | None = None, json=None, **kwargs
    ) -> requests.Response: ...


class WebhookHandler(EventHandler):
    """
    Event handler that sends events to a Webhook, automatically handles HTTP 429 Status and ensures messages get
    sent in order.
    """

    def __init__(
        self,
        name: str,
        webhook_api_url: str,
        transformer: EventTransformer[dict[str, str]],
        events: list[Events] | Events | None = None,
        use_json: bool = False,
        attempt_strategy: AttemptStrategy | None = None,
        timeout: float | tuple[float, float] | None = None,
        post_request: PostRequest | None = None,
        runner: QueueRunner | None = None,
    ):
        self.name = name
        """The name of this handler"""
        self.webhook_api_url = webhook_api_url
        """The Discord Webhook URL to which to send messages"""
        self.events = (
            Events.union(events)
            if isinstance(events, list)
            else (events if events is not None else Events.default())
        )
        """The events handled by this hook"""
        self.use_json = use_json
        """If True, the request will be sent as json, if False plain data will be sent."""
        self.transformer = transformer
        """The transformer that produces the data."""
        self.attempt_strategy = (
            attempt_strategy
            if attempt_strategy is not None
            else AttemptStrategy(attempt_interval_seconds=2)
        )
        """The attempt strategy to use when making requests, 429 responses will be retried with a 2s cooldown"""
        self.timeout = timeout if timeout is not None else (5, 10)
        """The timeout in seconds, either a single value or a tuple of (connect, request)"""
        self.post_request = post_request if post_request is not None else requests.post
        """The method by which to send the request, mostly used for testing"""
        self.runner: QueueRunner[Event] = (
            runner
            if runner is not None
            else QueueRunner[Event](
                name="Webhook",
                remove_on_failure=False,
                sleep_interval_seconds=0.2,
                process_item=self._process_item,
            )
        )
        """
        The underlying runner enabling sequential processing of events.
        Defaults to a queue runner that keeps items in the queue until processed 
        and waits 0.2 seconds between checking for queued items.
        """
        self.runner.start()

    def handles(self):
        return self.events

    def _make_request(self, data: dict[str, str]):
        return self.post_request(
            url=self.webhook_api_url,
            data=data if not self.use_json else None,
            json=data if self.use_json else None,
            timeout=self.timeout,
        )

    def _validate(self, response: requests.Response):
        response.raise_for_status()

    def _retryable(self, exception: Exception):
        """
        Retryable if it's an HTTPError with a response with status code 429 (too many requests),
        anything else is a failure.
        """
        match exception:
            case requests.HTTPError():
                if exception.response is None:
                    return False
                else:
                    # 429 means we need to wait for 2s for the message rate to decrease
                    return exception.response.status_code == 429
            case _:
                return False

    def _exception_context(self, exception: Exception):
        """
        Creates exception stack traces where required, none are required by default.
        :param exception: The exception.
        :return: The stack trace.
        """
        return None

    def _process_item(self, item: Event):
        """Makes attempts and turns the result into a bool"""
        data = self.transformer.transform(item)
        result = self.attempt_strategy.make_attempts(
            lambda: self._make_request(data),
            self._validate,
            self._retryable,
            self._exception_context,
        )
        if isinstance(result, SuccessResult):
            return True
        else:
            logger.error(
                f"{self.name}: unable to send event {item.type.name}: {result}"
            )
            return False

    def handle(self, event: Event):
        self.runner.enqueue(event)
