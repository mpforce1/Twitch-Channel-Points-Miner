import datetime
import logging
from threading import Timer

from dateutil import parser as dateparser

from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.Twitch import Twitch
from TwitchChannelPointsMiner.classes.entities.EventPrediction import EventPrediction
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.events.Event import (
    NotEnoughPoints,
    PredictionEventCreated,
    PredictionFilters,
    prediction_result_for,
)
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.classes.websocket.data import PredictionsChannel, PredictionsUser
from TwitchChannelPointsMiner.utils.Entities import find_streamer

logger = logging.getLogger(__name__)


class PredictionSystem:
    def __init__(
        self,
        twitch: Twitch,
        streamers: list[Streamer],
        prediction_events: dict[str, EventPrediction],
        event_manager: EventManager,
    ):
        self.twitch = twitch
        self.streamers = streamers
        self.prediction_events = prediction_events
        self.event_manager = event_manager

    def event_created(self, data: PredictionsChannel.EventCreated):
        event_id = data.event.id
        event_status = data.event.status
        if event_status == "ACTIVE":
            streamer = find_streamer(self.streamers, data.event.channel_id)
            prediction_window_seconds = data.event.prediction_window_seconds
            # Reduce prediction window by streamer settings
            prediction_window_seconds = streamer.get_prediction_window(
                prediction_window_seconds
            )
            event = EventPrediction(
                streamer,
                event_id,
                data.event.title,
                data.event.created_at,
                prediction_window_seconds,
                event_status,
                data.event.outcomes,  # TODO fix this
            )
            if streamer.is_online and event.closing_bet_after(data.timestamp) > 0:
                bet_settings = streamer.settings.bet
                if (
                    bet_settings.minimum_points is None
                    or streamer.channel_points > bet_settings.minimum_points
                ):
                    self.prediction_events[event_id] = event
                    start_after = event.closing_bet_after(data.timestamp)

                    place_bet_thread = Timer(
                        start_after,
                        self.twitch.make_predictions,
                        (self.prediction_events[event_id],),
                    )
                    place_bet_thread.daemon = True
                    place_bet_thread.start()

                    logger.info(
                        f"Place the bet after: {start_after}s for: {self.prediction_events[event.event_id]}"
                    )
                    self.event_manager.manage(
                        PredictionEventCreated(
                            timestamp=data.timestamp,
                            channel_id=data.event.channel_id,
                            event=data.event,
                        )
                    )
                else:
                    logger.info(
                        f"{streamer} have only {streamer.channel_points} channel points and the minimum for bet is: {bet_settings.minimum_points}"
                    )
                    self.event_manager.manage(
                        PredictionFilters(
                            timestamp=data.timestamp,
                            channel_id=data.event.channel_id,
                            event_id=event.event_id,
                            reason=NotEnoughPoints(
                                channel_id=data.event.channel_id,
                                channel_points=streamer.channel_points,
                                minimum_points=bet_settings.minimum_points,
                            ),
                        )
                    )

    def event_updated(self, data: PredictionsChannel.EventUpdated):
        event_id = data.event.id
        event_status = data.event.status
        self.prediction_events[event_id].status = event_status
        # Game over we can't update any more the values... The bet was placed!
        if (
            self.prediction_events[event_id].bet_placed is False
            and self.prediction_events[event_id].bet.decision == {}
        ):
            self.prediction_events[event_id].bet.update_outcomes(
                data.event.outcomes
            )  # TODO fix this

    def event_closed(self):
        # TODO this will come from an update
        pass

    def event_refunded(self):
        pass  # TODO call from result

    def user_prediction_made(self, data: PredictionsUser.PredictionMade):
        event_id = data.prediction.event_id
        event_prediction = self.prediction_events.get(event_id, None)
        if event_prediction is None:
            logger.debug(f"Ignoring prediction made for {event_id}, unmanaged event")
            return
        streamer = find_streamer(self.streamers, data.prediction.channel_id)
        event_prediction.bet_confirmed = True
        # Analytics switch
        if Settings.enable_analytics is True:
            streamer.persistent_annotations(
                "PREDICTION_MADE",
                f"Decision: {event_prediction.bet.decision['choice']} - {event_prediction.title}",
            )

    def prediction_result(self, data: PredictionsUser.PredictionResult):
        event_id = data.prediction.event_id
        channel_id = data.prediction.channel_id
        event_prediction = self.prediction_events.get(event_id, None)
        if event_prediction is None:
            logger.debug(f"Ignoring result for {event_id}, unmanaged Prediction Event")
            return
        streamer = find_streamer(self.streamers, channel_id)
        points = event_prediction.parse_result(data.prediction.result)# TODO fix this

        decision = event_prediction.bet.get_decision()
        choice = event_prediction.bet.decision["choice"]

        logger.info(
            f"{event_prediction} - Decision: {choice}: {decision['title']} "
            f"({decision['color']}) - Result: {event_prediction.result['string']}"
        )

        prediction_result_event = prediction_result_for(
            _type=event_prediction.result["type"],
            channel_id=channel_id,
            event_id=event_id,
            decision_title=decision["title"],
            decision_id=decision["id"],
            decision_color=decision["color"],
            stake=points["placed"],
            gain=points.get("won", 0),
        )
        if prediction_result_event is None:
            logger.error(
                f"Unknown prediction result type: {event_prediction.result["type"]}"
            )
        else:
            self.event_manager.manage(prediction_result_event)

        streamer.update_history("PREDICTION", points["gained"])

        # Remove duplicate history records from previous message sent in community-points-user-v1
        if event_prediction.result["type"] == "REFUND":
            streamer.update_history(
                "REFUND",
                -points["placed"],
                counter=-1,
            )
        elif event_prediction.result["type"] == "WIN":
            streamer.update_history(
                "PREDICTION",
                -points["won"],
                counter=-1,
            )

        if event_prediction.result["type"]:
            # Analytics switch
            if Settings.enable_analytics is True:
                streamer.persistent_annotations(
                    event_prediction.result["type"],
                    f"{event_prediction.title}",
                )
