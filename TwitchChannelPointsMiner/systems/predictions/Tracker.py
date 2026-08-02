import logging

from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.entities.predictions.Prediction import Prediction
from TwitchChannelPointsMiner.classes.entities.predictions.PredictionEvent import (
    PredictionEvent,
)
from TwitchChannelPointsMiner.classes.events.Event import (
    PredictionEventCreated,
    prediction_result_for,
)
from TwitchChannelPointsMiner.classes.events.Manager import EventManager
from TwitchChannelPointsMiner.classes.websocket.data import (
    PredictionsChannel,
    PredictionsUser,
)
from TwitchChannelPointsMiner.systems.Predictions import (
    PredictionSystem,
    PredictionSystemFactory,
)
from TwitchChannelPointsMiner.systems.predictions.Predictor import Predictor
from TwitchChannelPointsMiner.utils.Entities import find_streamer

logger = logging.getLogger(__name__)


class PredictionTrackingSystem(PredictionSystem):
    """PredictionSystem that tracks the predictions."""

    def __init__(
        self,
        streamers: list[Streamer],
        prediction_events: dict[str, PredictionEvent],
        event_manager: EventManager,
        predictor: Predictor,
    ):
        self.streamers = streamers
        self.prediction_events = prediction_events
        self.event_manager = event_manager
        self.predictor = predictor

    def event_created(self, data: PredictionsChannel.EventCreated):
        if data.event.status == "ACTIVE":
            # Ignore inactive events
            event = PredictionEvent.from_ws(data.event)
            self.prediction_events[event.event_id] = event
            self.event_manager.manage(
                PredictionEventCreated(
                    timestamp=event.created_at,
                    channel_id=event.channel_id,
                    event=data.event,
                )
            )
            self.predictor.event_created(event)

    def event_updated(self, data: PredictionsChannel.EventUpdated):
        event_id = data.event.id
        event = self.prediction_events.get(event_id, None)
        if event is None:
            logger.debug(
                f"Ignoring update for untracked Prediction Event '{data.event.title}'"
            )
            return
        event.update(data.event)
        self.predictor.event_updated(event)

    def user_prediction_made(self, data: PredictionsUser.PredictionMade):
        event_id = data.prediction.event_id
        event = self.prediction_events.get(event_id, None)
        if event is None:
            logger.debug(f"Ignoring prediction made for {event_id}, untracked event")
            return
        event.prediction = Prediction.from_ws(data.prediction)
        # Analytics switch
        if Settings.enable_analytics is True:
            streamer = find_streamer(self.streamers, data.prediction.channel_id)
            decision = event.outcome(event.prediction.outcome_id)
            streamer.persistent_annotations(
                "PREDICTION_MADE",
                f"Decision: {decision.title} - {event.title}",
            )

    def user_prediction_result(self, data: PredictionsUser.PredictionResult):
        event_id = data.prediction.event_id
        channel_id = data.prediction.channel_id
        event = self.prediction_events.get(event_id, None)
        if event is None:
            logger.debug(f"Ignoring result for {event_id}, untracked Prediction Event")
            return
        if event.prediction is None:
            logger.error(f"Result given for Prediction Event without a User Prediction")
            return
        if data.prediction.result is None:
            logger.error(f"Result given for Prediction Event containing no Result data")
            return
        event.prediction = Prediction.from_ws(data.prediction)
        if event.prediction.result is None:
            logger.error(f"Result event without a Result")
            return
        streamer = find_streamer(self.streamers, channel_id)
        stake = event.prediction.points
        gain = (
            data.prediction.result.points_won
            if data.prediction.result.points_won is not None
            else 0
        )

        decision = event.outcome(event.prediction.outcome_id)

        logger.info(
            event.describe_result(
                Settings.logger.anonymiser.username(streamer.username)
            )
        )

        result_type = data.prediction.result.type

        prediction_result_event = prediction_result_for(
            _type=result_type,
            channel_id=channel_id,
            event_id=event_id,
            decision_title=decision.title,
            decision_id=decision.id,
            decision_color=decision.color,
            stake=stake,
            gain=gain,
        )
        if prediction_result_event is None:
            logger.error(f"Unknown prediction result type: {result_type}")
        else:
            self.event_manager.manage(prediction_result_event)

        streamer.update_history("PREDICTION", gain)

        # Remove duplicate history records from previous message sent in community-points-user-v1
        if result_type == "REFUND":
            streamer.update_history(
                "REFUND",
                -stake,
                counter=-1,
            )
        elif result_type == "WIN":
            streamer.update_history(
                "PREDICTION",
                -gain,
                counter=-1,
            )

        # Analytics switch
        if Settings.enable_analytics is True:
            streamer.persistent_annotations(
                result_type,
                f"{event.title}",
            )


class PredictionTrackingSystemFactory(PredictionSystemFactory):
    def create(
        self,
        streamers: list[Streamer],
        prediction_events: dict[str, PredictionEvent],
        event_manager: EventManager,
        predictor: Predictor,
    ):
        return PredictionTrackingSystem(
            streamers=streamers,
            prediction_events=prediction_events,
            event_manager=event_manager,
            predictor=predictor,
        )
