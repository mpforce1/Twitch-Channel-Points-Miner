import datetime
from unittest.mock import MagicMock

import pytest

from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.entities.predictions.Prediction import Prediction
from TwitchChannelPointsMiner.classes.entities.predictions.Result import Result
from TwitchChannelPointsMiner.classes.events.Event import (
    PredictionLose,
    PredictionRefund,
    PredictionWin,
)
from TwitchChannelPointsMiner.classes.websocket.data import Predictions
from TwitchChannelPointsMiner.classes.websocket.data import (
    PredictionsChannel,
    PredictionsUser,
)
from TwitchChannelPointsMiner.classes.websocket.data.Predictions import (
    Outcome,
    PredictionEvent,
    User,
)
from TwitchChannelPointsMiner.systems.predictions.Tracker import (
    PredictionTrackingSystem,
)


def event(status: str = "ACTIVE"):
    return PredictionEvent(
        id="019fbc32-584a-7186-b754-ee5d3ff56c68",
        channel_id="123456789",
        created_at=datetime.datetime.fromtimestamp(123456),
        created_by=User(id="4564869", display_name="TestUser"),
        ended_at=None,
        ended_by=None,
        locked_at=None,
        locked_by=None,
        outcomes=[
            Outcome(
                id="019fbc34-3c40-75bd-82f8-ecc6fa70c24f",
                color="BLUE",
                title="Outcome 1",
                total_points=0,
                total_users=0,
                top_predictors=[],
            ),
            Outcome(
                id="019fbc36-30a8-76bf-9c64-1a8963f82436",
                color="BLUE",
                title="Outcome 2",
                total_points=0,
                total_users=0,
                top_predictors=[],
            ),
        ],
        prediction_window_seconds=200,
        status=status,
        title="title",
        winning_outcome_id=None,
    )


new_event = event()
new_event_inactive = event(status="CLOSED")


test_event_created_data = [
    PredictionsChannel.EventCreated(
        timestamp=datetime.datetime.fromtimestamp(123456), event=new_event
    ),
    PredictionsChannel.EventCreated(
        timestamp=datetime.datetime.fromtimestamp(123456), event=new_event_inactive
    ),
]


@pytest.mark.parametrize("data", test_event_created_data)
def test_event_created(data):
    event_manager = MagicMock()
    predictor = MagicMock()
    streamers = [Streamer("123456789", "123456789")]
    tracker = PredictionTrackingSystem(
        streamers=streamers,
        prediction_events=dict(),
        event_manager=event_manager,
        predictor=predictor,
    )

    tracker.event_created(data)

    if data.event.status == "ACTIVE":
        event_manager.manage.assert_called_once()
        assert data.event.id in tracker.prediction_events
        predictor.event_created.assert_called_once()
    else:
        event_manager.manage.assert_not_called()
        predictor.event_created.assert_not_called()


@pytest.mark.parametrize("event_is_tracked", [False, True])
def test_event_updated(event_is_tracked):
    event_manager = MagicMock()
    predictor = MagicMock()
    prediction_events = MagicMock()
    streamers = [Streamer("123456789", "123456789")]
    tracker = PredictionTrackingSystem(
        streamers=streamers,
        prediction_events=prediction_events,
        event_manager=event_manager,
        predictor=predictor,
    )

    event = MagicMock() if event_is_tracked else None
    prediction_events.get.return_value = event

    data = MagicMock()
    data.event = MagicMock()
    data.event.id = "456123"
    data.event.channel_id = "123456789"
    data.event.title = "event title"

    tracker.event_updated(data)

    if event is not None:
        event.update.assert_called_once()
        predictor.event_updated.assert_called_once()


@pytest.mark.parametrize("event_is_tracked", [False, True])
def test_user_prediction_made(event_is_tracked):
    event_manager = MagicMock()
    predictor = MagicMock()
    prediction_events = MagicMock()
    streamer = MagicMock(spec=Streamer)
    streamer.channel_id = "123456"
    streamers: list = [streamer]
    tracker = PredictionTrackingSystem(
        streamers=streamers,
        prediction_events=prediction_events,
        event_manager=event_manager,
        predictor=predictor,
    )

    data = PredictionsUser.PredictionMade(
        timestamp=datetime.datetime.fromtimestamp(123456),
        prediction=Predictions.Prediction(
            id="019fbc98-7dc0-73ef-a45f-a2a1d7ef215e",
            event_id="019fbc98-acc8-721f-af68-28a645653656",
            outcome_id="019fbc98-fd40-76c5-bd8e-cfc6add10892",
            channel_id="123456",
            points=1000,
            predicted_at=datetime.datetime.fromtimestamp(123457),
            updated_at=datetime.datetime.fromtimestamp(123457),
            user_id="456789",
            result=None,
            user_display_name=None,
        ),
    )

    if event_is_tracked:
        outcome = MagicMock()
        outcome.title = "outcome title"
        event = MagicMock()
        event.title = "event title"
        event.outcome.return_value = outcome
        event.channel_id = "123456"
    else:
        event = None
    prediction_events.get.return_value = event

    Settings.enable_analytics = True

    tracker.user_prediction_made(data)

    if event is not None:
        assert event.prediction == Prediction(
            _id=data.prediction.id,
            event_id=data.prediction.event_id,
            outcome_id=data.prediction.outcome_id,
            channel_id=data.prediction.channel_id,
            points=data.prediction.points,
            predicted_at=data.prediction.predicted_at,
            updated_at=data.prediction.updated_at,
            user_id=data.prediction.user_id,
            result=(
                Result(
                    _type=data.prediction.result.type,
                    points_won=data.prediction.result.points_won,
                )
                if data.prediction.result is not None
                else None
            ),
            user_display_name=data.prediction.user_display_name,
        )
        streamer.persistent_annotations.assert_called_once_with(
            "PREDICTION_MADE", "Decision: outcome title - event title"
        )


test_user_prediction_result_data = [
    (False, False, None),
    (True, False, None),
    (True, True, None),
    (True, True, Predictions.Result(type="WIN", points_won=5000)),
    (True, True, Predictions.Result(type="LOSE", points_won=None)),
    (True, True, Predictions.Result(type="REFUND", points_won=None)),
]


@pytest.mark.parametrize(
    "event_is_tracked,user_predicted,result", test_user_prediction_result_data
)
def test_user_prediction_result(
    event_is_tracked, user_predicted, result: Predictions.Result | None
):
    prediction_events = {}
    if event_is_tracked:
        event = MagicMock()
        event.id = "019fbcc6-e84f-7406-acde-fe591ac13fb9"
        event.channel_id = "123456"
        prediction_events["019fbcc6-e84f-7406-acde-fe591ac13fb9"] = event

        outcome = MagicMock()
        outcome.title = "decision outcome title"
        outcome.id = "019fbcce-3f87-7603-823f-61c2f36f2fd9"
        outcome.color = "BLUE"

        event.outcome.return_value = outcome

        if user_predicted:
            prediction = MagicMock()
            prediction.result = result
        else:
            prediction = None
        event.prediction = prediction
    else:
        event = None
        prediction = None

    streamer = MagicMock(spec=Streamer)
    streamer.channel_id = "123456"
    streamers: list = [streamer]

    event_manager = MagicMock()
    predictor = MagicMock()

    tracker = PredictionTrackingSystem(
        streamers=streamers,
        prediction_events=prediction_events,
        event_manager=event_manager,
        predictor=predictor,
    )

    data = PredictionsUser.PredictionResult(
        timestamp=datetime.datetime.fromtimestamp(123465),
        prediction=Predictions.Prediction(
            id="019fbcc6-9120-74ff-acd9-eb4b49f14da9",
            event_id="019fbcc6-e84f-7406-acde-fe591ac13fb9",
            outcome_id="019fbcc7-2180-7195-af6f-febb739eff72",
            channel_id="123456",
            points=2000,
            predicted_at=datetime.datetime.fromtimestamp(123456),
            updated_at=datetime.datetime.fromtimestamp(123456),
            user_id="456789",
            result=result,
            user_display_name=None,
        ),
    )

    Settings.enable_analytics = True

    timestamp = datetime.datetime.fromtimestamp(123456)

    with pytest.MonkeyPatch.context() as patcher:
        mock_datetime = MagicMock()
        mock_datetime.now = MagicMock()
        mock_datetime.now.return_value = timestamp
        patcher.setattr(datetime, "datetime", mock_datetime)
        tracker.user_prediction_result(data)

    if event is not None and prediction is not None and result is not None:
        assert event.prediction == Prediction(
            _id=data.prediction.id,
            event_id=data.prediction.event_id,
            outcome_id=data.prediction.outcome_id,
            channel_id=data.prediction.channel_id,
            points=data.prediction.points,
            predicted_at=data.prediction.predicted_at,
            updated_at=data.prediction.updated_at,
            user_id=data.prediction.user_id,
            result=(
                Result(
                    _type=data.prediction.result.type,
                    points_won=data.prediction.result.points_won,
                )
                if data.prediction.result is not None
                else None
            ),
            user_display_name=data.prediction.user_display_name,
        )

        if result is not None:
            expected_update_history_calls = 1
            if result.type == "WIN":
                expected_update_history_calls += 1
                expected_event = PredictionWin(
                    timestamp=timestamp,
                    streamer=streamer,
                    prediction_event=event,
                )
            elif result.type == "LOSE":
                expected_event = PredictionLose(
                    timestamp=timestamp,
                    streamer=streamer,
                    prediction_event=event,
                )
            else:
                expected_update_history_calls += 1
                expected_event = PredictionRefund(
                    timestamp=timestamp,
                    streamer=streamer,
                    prediction_event=event,
                )
            event_manager.manage.assert_called_once_with(expected_event)

            assert streamer.update_history.call_count == expected_update_history_calls
            streamer.persistent_annotations.assert_called_once()
