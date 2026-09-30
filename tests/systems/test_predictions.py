import copy
import datetime
from threading import Timer
from time import sleep
from unittest.mock import MagicMock, call

from TwitchChannelPointsMiner.classes.entities.Bet import BetSettings, Strategy
from TwitchChannelPointsMiner.classes.entities.Streamer import (
    StreamerSettings,
)
from TwitchChannelPointsMiner.classes.entities.predictions.Bet import Bet
from TwitchChannelPointsMiner.classes.entities.predictions.Prediction import Prediction
from TwitchChannelPointsMiner.classes.entities.predictions.PredictionEvent import (
    PredictionEvent,
)
from TwitchChannelPointsMiner.classes.events.Event import PredictionWin
from TwitchChannelPointsMiner.classes.websocket.data import (
    Predictions,
    PredictionsChannel,
    PredictionsUser,
)
from TwitchChannelPointsMiner.systems.predictions.Predictor import BasicPredictor
from TwitchChannelPointsMiner.systems.predictions.Tracker import (
    PredictionTrackingSystem,
)
from TwitchChannelPointsMiner.utils.Utils import generate_random_uuid


def new_outcome(
    index: int,
    total_points=0,
    total_users=0,
    top_predictors=None,
):
    return Predictions.Outcome(
        id=f"{index}-id",
        color="BLUE",
        title=f"outcome {index} title",
        total_points=total_points,
        total_users=total_users,
        top_predictors=top_predictors if top_predictors is not None else [],
    )


base_event = Predictions.PredictionEvent(
    id="019fc240-9679-72b1-bae6-f28cbbb07fea",
    channel_id="123456",
    created_at=datetime.datetime.fromisoformat("2026-08-02T12:00:00Z"),
    created_by=Predictions.User(
        id="654321",
        display_name="PredictionCreatorUser",
    ),
    ended_at=None,
    ended_by=None,
    locked_at=None,
    locked_by=None,
    outcomes=[new_outcome(index) for index in range(6)],
    prediction_window_seconds=2,
    status="ACTIVE",
    title="Prediction Event title",
    winning_outcome_id=None,
)


def prediction(outcome_index: int, points: int, created_seconds_from_start: int):
    user_id = generate_random_uuid()
    return Predictions.Prediction(
        id=generate_random_uuid(),
        event_id=base_event.id,
        outcome_id=base_event.outcomes[outcome_index].id,
        channel_id=base_event.channel_id,
        points=points,
        predicted_at=base_event.created_at
        + datetime.timedelta(seconds=created_seconds_from_start),
        updated_at=base_event.created_at
        + datetime.timedelta(seconds=created_seconds_from_start),
        user_id=user_id,
        result=None,
        user_display_name=f"User_{user_id}",
    )


class MockDateTime(datetime.datetime):
    pass

def test_full(monkeypatch):
    """Integration test for Tracker and Predictor"""
    # Patch datetime
    now = datetime.datetime.fromisoformat("2026-08-02T12:00:01Z")
    mock_datetime = MockDateTime
    mock_datetime.now = MagicMock()
    mock_datetime.now.return_value = now
    monkeypatch.setattr(datetime, "datetime", mock_datetime)
    # Streamer with default settings (except delay=0 and strategy=SMART_MONEY)
    settings = BetSettings(delay=0, strategy=Strategy.SMART_MONEY)
    settings.default()
    streamer = MagicMock()
    streamer.username = "123456username"
    streamer.channel_id = "123456"
    streamer.settings = StreamerSettings(bet=settings)
    streamer.channel_points = 1000
    streamers: list = [streamer]
    prediction_events = dict()
    twitch = MagicMock()
    event_manager = MagicMock()

    predictor = BasicPredictor(
        twitch=twitch,
        streamers=streamers,
        prediction_events=prediction_events,
        event_manager=event_manager,
        timer_factory=Timer,
    )
    tracker = PredictionTrackingSystem(
        streamers=streamers,
        prediction_events=prediction_events,
        event_manager=event_manager,
        predictor=predictor,
    )

    # Begin event
    event_created_data = PredictionsChannel.EventCreated(
        timestamp=datetime.datetime.fromisoformat("2026-08-02T12:00:01Z"),
        event=copy.deepcopy(base_event),
    )
    tracker.event_created(event_created_data)

    # Event data should now be in the dict
    assert prediction_events.get(base_event.id, None) == PredictionEvent.from_ws(
        event_created_data.event
    )

    # Update, predictions on outcomes
    event_updated = copy.deepcopy(base_event)
    outcome_0 = event_updated.outcomes[0]
    outcome_0.top_predictors = [
        prediction(0, 100, 1),
        prediction(0, 90, 1),
        prediction(0, 10, 1),
    ]
    outcome_0.total_users = 3
    outcome_0.total_points = 200

    outcome_1 = event_updated.outcomes[1]
    outcome_1.top_predictors = [
        prediction(1, 100, 1),
    ]
    outcome_1.total_users = 1
    outcome_1.total_points = 100

    outcome_5 = event_updated.outcomes[5]
    outcome_5.top_predictors = [
        prediction(5, 400, 0),
        prediction(5, 100, 1),
    ]
    outcome_5.total_users = 2
    outcome_5.total_points = 500
    event_updated_data = PredictionsChannel.EventUpdated(
        timestamp=datetime.datetime.fromisoformat("2026-08-02T12:00:01Z"),
        event=event_updated,
    )

    # Send update
    tracker.event_updated(event_updated_data)

    # Data should be updated
    assert prediction_events.get(base_event.id, None) == PredictionEvent.from_ws(
        event_updated
    )

    # Wait for prediction time
    sleep(1)

    # Prediction should have been made
    twitch.make_prediction.assert_called_once()
    bet: Bet = twitch.make_prediction.call_args_list[0][0][2]
    # Bet on 5 as it has the highest individual bet, 50 points as that's 5% of user's points
    assert bet == Bet(outcome_id="5-id", points=50)

    # Simulate twitch's response
    prediction_made = PredictionsUser.PredictionMade(
        timestamp=datetime.datetime.fromisoformat("2026-08-02T12:00:03Z"),
        prediction=Predictions.Prediction(
            id="019fc321-87d0-71e9-86fe-cb2f3932c3ae",
            event_id=base_event.id,
            outcome_id=base_event.outcomes[5].id,
            channel_id=base_event.channel_id,
            points=50,
            predicted_at=datetime.datetime.fromisoformat("2026-08-02T12:00:02Z"),
            updated_at=datetime.datetime.fromisoformat("2026-08-02T12:00:02Z"),
            user_id="456789",
            result=None,
            user_display_name=None,
        ),
    )

    tracker.user_prediction_made(prediction_made)

    # Event updated
    assert prediction_events[base_event.id].prediction == Prediction.from_ws(
        prediction_made.prediction
    )

    # Simulate result
    prediction_with_result = copy.deepcopy(prediction_made.prediction)
    prediction_with_result.result = Predictions.Result(type="WIN", points_won=500)
    prediction_result = PredictionsUser.PredictionResult(
        timestamp=datetime.datetime.fromisoformat("2026-08-02T12:00:03Z"),
        prediction=prediction_with_result,
    )

    tracker.user_prediction_result(prediction_result)

    # Event manager
    event_resulted_expected = PredictionEvent.from_ws(copy.deepcopy(event_updated))
    event_resulted_expected.prediction = Prediction.from_ws(
        copy.deepcopy(prediction_with_result)
    )
    event_manager.manage.assert_has_calls(
        [
            call(
                PredictionWin(
                    timestamp=now,
                    streamer=streamer,
                    prediction_event=event_resulted_expected,
                )
            )
        ],
        True,
    )

    # History, once for the prediction, then again to reverse it
    streamer.update_history.assert_has_calls(
        [call("PREDICTION", 500), call("PREDICTION", -500, counter=-1)], True
    )
