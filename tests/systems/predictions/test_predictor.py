import datetime
from unittest.mock import MagicMock

import pytest

from TwitchChannelPointsMiner.classes.entities.Bet import (
    BetSettings,
    Condition,
    DelayMode,
    FilterCondition,
    OutcomeKeys,
    Strategy,
)
from TwitchChannelPointsMiner.classes.entities.predictions.Bet import Bet
from TwitchChannelPointsMiner.classes.entities.predictions.Outcome import Outcome
from TwitchChannelPointsMiner.classes.entities.predictions.PredictionEvent import (
    PredictionEvent,
)
from TwitchChannelPointsMiner.classes.entities.predictions.User import User
from TwitchChannelPointsMiner.classes.events.Event import (
    EventNotActive,
    EventTooShort,
    NotEnoughPoints,
    PredictionAlreadyMade,
    PredictionFilters,
    PredictionPointsBelowMinimum,
    SettingsFiltered,
)
from TwitchChannelPointsMiner.systems.predictions.Predictor import (
    BasicPredictor,
    create_bet,
    get_prediction_time,
    skip_bet,
    skip_event,
)


def outcome(
    index: int,
    total_points=0,
    total_users=0,
    top_predictors=None,
    percentage_users=0,
    odds: float = 0,
    odds_percentage: float = 0,
    top_points=0,
):
    return Outcome(
        _id=f"{index}-id",
        color="BLUE",
        title=f"outcome {index} title",
        total_points=total_points,
        total_users=total_users,
        top_predictors=top_predictors if top_predictors is not None else [],
        percentage_users=percentage_users,
        odds=odds,
        odds_percentage=odds_percentage,
        top_points=top_points,
    )


event = PredictionEvent(
    channel_id="123456",
    event_id="019fbd01-edb8-7184-ac27-2d083f961ee8",
    title="event title",
    created_at=datetime.datetime.fromisoformat("2026-08-01T14:00:00Z"),
    created_by=User(
        _id="456789",
        display_name="PredictionCreatorUser",
    ),
    locked_at=None,
    locked_by=None,
    ended_at=None,
    ended_by=None,
    prediction_window_seconds=3 * 60,
    status="ACTIVE",
    winning_outcome_id=None,
    outcomes=[
        outcome(
            0,
            percentage_users=5,
            total_users=50,
            total_points=10000,
            odds=6.00,
            odds_percentage=16.67,
            top_points=5000,
        ),
        outcome(
            1,
            percentage_users=3,
            total_users=30,
            total_points=5000,
            odds=12.00,
            odds_percentage=8.33,
            top_points=2500,
        ),
        outcome(
            2,
            percentage_users=20,
            total_users=20,
            total_points=800,
            odds=75.00,
            odds_percentage=1.33,
            top_points=100,
        ),
        outcome(
            3,
            percentage_users=8,
            total_users=80,
            total_points=400,
            odds=150.00,
            odds_percentage=0.67,
            top_points=100,
        ),
        outcome(
            4,
            percentage_users=25,
            total_users=250,
            total_points=3000,
            odds=20.00,
            odds_percentage=5.00,
            top_points=1000,
        ),
        outcome(
            5,
            percentage_users=15,
            total_users=150,
            total_points=6000,
            odds=10.00,
            odds_percentage=10.00,
            top_points=3000,
        ),
        outcome(
            6,
            percentage_users=5,
            total_users=50,
            total_points=20000,
            odds=3.00,
            odds_percentage=33.33,
            top_points=2000,
        ),
        outcome(
            7,
            percentage_users=2,
            total_users=20,
            total_points=4000,
            odds=15.00,
            odds_percentage=6.67,
            top_points=1000,
        ),
        outcome(
            8,
            percentage_users=10,
            total_users=100,
            total_points=8000,
            odds=7.50,
            odds_percentage=13.33,
            top_points=1500,
        ),
        outcome(
            9,
            percentage_users=7,
            total_users=70,
            total_points=2800,
            odds=21.43,
            odds_percentage=4.67,
            top_points=500,
        ),
    ],
    total_points=60000,
    total_users=820,
)

test_create_bet_data = [
    # Unique strats
    (
        BetSettings(strategy=Strategy.MOST_VOTED, max_points=2000, percentage=100),
        1000,
        event,
        Bet(outcome_id="4-id", points=1000),
    ),
    (
        BetSettings(strategy=Strategy.HIGH_ODDS, max_points=100, percentage=5),
        10000,
        event,
        Bet(outcome_id="3-id", points=100),
    ),
    (
        BetSettings(strategy=Strategy.PERCENTAGE, max_points=2000, percentage=5),
        10000,
        event,
        Bet(outcome_id="6-id", points=500),
    ),
    (
        BetSettings(strategy=Strategy.SMART_MONEY, max_points=1, percentage=100),
        1,
        event,
        Bet(outcome_id="0-id", points=1),
    ),
    # NUMBER strategies
    (
        BetSettings(strategy=Strategy.NUMBER_1, max_points=1, percentage=100),
        1,
        event,
        Bet(outcome_id="0-id", points=1),
    ),
    (
        BetSettings(strategy=Strategy.NUMBER_2, max_points=1, percentage=100),
        1,
        event,
        Bet(outcome_id="1-id", points=1),
    ),
    (
        BetSettings(strategy=Strategy.NUMBER_3, max_points=1, percentage=100),
        1,
        event,
        Bet(outcome_id="2-id", points=1),
    ),
    (
        BetSettings(strategy=Strategy.NUMBER_4, max_points=1, percentage=100),
        1,
        event,
        Bet(outcome_id="3-id", points=1),
    ),
    (
        BetSettings(strategy=Strategy.NUMBER_5, max_points=1, percentage=100),
        1,
        event,
        Bet(outcome_id="4-id", points=1),
    ),
    (
        BetSettings(strategy=Strategy.NUMBER_6, max_points=1, percentage=100),
        1,
        event,
        Bet(outcome_id="5-id", points=1),
    ),
    (
        BetSettings(strategy=Strategy.NUMBER_7, max_points=1, percentage=100),
        1,
        event,
        Bet(outcome_id="6-id", points=1),
    ),
    (
        BetSettings(strategy=Strategy.NUMBER_8, max_points=1, percentage=100),
        1,
        event,
        Bet(outcome_id="7-id", points=1),
    ),
    (
        BetSettings(strategy=Strategy.NUMBER_9, max_points=1, percentage=100),
        1,
        event,
        Bet(outcome_id="8-id", points=1),
    ),
    (
        BetSettings(strategy=Strategy.NUMBER_10, max_points=1, percentage=100),
        1,
        event,
        Bet(outcome_id="9-id", points=1),
    ),
    # SMART with gap=5 and diff=2
    (
        BetSettings(
            strategy=Strategy.SMART, max_points=1, percentage=100, percentage_gap=5
        ),
        1,
        event,
        Bet(outcome_id="3-id", points=1),
    ),
    # SMART with gap=1 and diff=2
    (
        BetSettings(
            strategy=Strategy.SMART, max_points=1, percentage=100, percentage_gap=1
        ),
        1,
        event,
        Bet(outcome_id="4-id", points=1),
    ),
]


@pytest.mark.parametrize("settings,channel_points,event,expected", test_create_bet_data)
def test_create_bet(settings, channel_points, event, expected):
    streamer = MagicMock()
    streamer.channel_points = channel_points
    streamer.settings = MagicMock()
    streamer.settings.bet = settings
    assert create_bet(streamer, event) == expected


test_skip_event_data = [
    ("CLOSED", None, EventNotActive(status="CLOSED")),
    ("ACTIVE", MagicMock(), PredictionAlreadyMade()),
    ("ACTIVE", None, None),
]


@pytest.mark.parametrize("status,prediction,expected", test_skip_event_data)
def test_skip_event(status, prediction, expected):
    event = MagicMock()
    event.title = "Event Title"
    event.status = status
    event.prediction = prediction
    assert skip_event(event) == expected


test_skip_bet_data = [
    # Fewer than 0 points
    (
        BetSettings(filter_condition=None),
        Bet(outcome_id="0-id", points=-1),
        PredictionPointsBelowMinimum(bet=Bet(outcome_id="0-id", points=-1)),
    ),
    # No filter, accept
    (BetSettings(filter_condition=None), Bet(outcome_id="0-id", points=0), None),
    # PERCENTAGE_USERS: pass, fail, fail
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.PERCENTAGE_USERS, where=Condition.GT, value=4
            )
        ),
        Bet(outcome_id="0-id", points=0),
        None,
    ),
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.PERCENTAGE_USERS, where=Condition.GT, value=5
            )
        ),
        Bet(outcome_id="0-id", points=0),
        SettingsFiltered(
            condition=FilterCondition(
                by=OutcomeKeys.PERCENTAGE_USERS, where=Condition.GT, value=5
            ),
            compared_value=5,
        ),
    ),
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.PERCENTAGE_USERS, where=Condition.GT, value=6
            )
        ),
        Bet(outcome_id="0-id", points=0),
        SettingsFiltered(
            condition=FilterCondition(
                by=OutcomeKeys.PERCENTAGE_USERS, where=Condition.GT, value=6
            ),
            compared_value=5,
        ),
    ),
    # ODDS_PERCENTAGE, pass, fail, fail
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.ODDS_PERCENTAGE, where=Condition.LT, value=17
            )
        ),
        Bet(outcome_id="0-id", points=0),
        None,
    ),
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.ODDS_PERCENTAGE, where=Condition.LT, value=16.67
            )
        ),
        Bet(outcome_id="0-id", points=0),
        SettingsFiltered(
            condition=FilterCondition(
                by=OutcomeKeys.ODDS_PERCENTAGE, where=Condition.LT, value=16.67
            ),
            compared_value=16.67,
        ),
    ),
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.ODDS_PERCENTAGE, where=Condition.LT, value=16
            )
        ),
        Bet(outcome_id="0-id", points=0),
        SettingsFiltered(
            condition=FilterCondition(
                by=OutcomeKeys.ODDS_PERCENTAGE, where=Condition.LT, value=16
            ),
            compared_value=16.67,
        ),
    ),
    # ODDS, pass, pass, fail
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.ODDS, where=Condition.GTE, value=5
            )
        ),
        Bet(outcome_id="0-id", points=0),
        None,
    ),
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.ODDS, where=Condition.GTE, value=6
            )
        ),
        Bet(outcome_id="0-id", points=0),
        None,
    ),
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.ODDS, where=Condition.GTE, value=7
            )
        ),
        Bet(outcome_id="0-id", points=0),
        SettingsFiltered(
            condition=FilterCondition(
                by=OutcomeKeys.ODDS, where=Condition.GTE, value=7
            ),
            compared_value=6.00,
        ),
    ),
    # TOP_POINTS, pass, pass, fail
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.TOP_POINTS, where=Condition.LTE, value=6000
            )
        ),
        Bet(outcome_id="0-id", points=0),
        None,
    ),
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.TOP_POINTS, where=Condition.LTE, value=5000
            )
        ),
        Bet(outcome_id="0-id", points=0),
        None,
    ),
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.TOP_POINTS, where=Condition.LTE, value=4999
            )
        ),
        Bet(outcome_id="0-id", points=0),
        SettingsFiltered(
            condition=FilterCondition(
                by=OutcomeKeys.TOP_POINTS, where=Condition.LTE, value=4999
            ),
            compared_value=5000,
        ),
    ),
    # TOTAL_USERS, pass, fail
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.TOTAL_USERS, where=Condition.GT, value=800
            )
        ),
        Bet(outcome_id="0-id", points=0),
        None,
    ),
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.TOTAL_USERS, where=Condition.LT, value=800
            )
        ),
        Bet(outcome_id="0-id", points=0),
        SettingsFiltered(
            condition=FilterCondition(
                by=OutcomeKeys.TOTAL_USERS, where=Condition.LT, value=800
            ),
            compared_value=820,
        ),
    ),
    # TOTAL_POINTS, pass, fail
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.TOTAL_POINTS, where=Condition.GTE, value=60000
            )
        ),
        Bet(outcome_id="0-id", points=0),
        None,
    ),
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.TOTAL_POINTS, where=Condition.LTE, value=50000
            )
        ),
        Bet(outcome_id="0-id", points=0),
        SettingsFiltered(
            condition=FilterCondition(
                by=OutcomeKeys.TOTAL_POINTS, where=Condition.LTE, value=50000
            ),
            compared_value=60000,
        ),
    ),
    # DECISION_USERS, pass, fail
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.DECISION_USERS, where=Condition.LT, value=100
            )
        ),
        Bet(outcome_id="0-id", points=0),
        None,
    ),
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.DECISION_USERS, where=Condition.GT, value=50
            )
        ),
        Bet(outcome_id="0-id", points=0),
        SettingsFiltered(
            condition=FilterCondition(
                by=OutcomeKeys.DECISION_USERS, where=Condition.GT, value=50
            ),
            compared_value=50,
        ),
    ),
    # DECISION_POINTS, pass, fail
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.DECISION_POINTS, where=Condition.LTE, value=20000
            )
        ),
        Bet(outcome_id="0-id", points=0),
        None,
    ),
    (
        BetSettings(
            filter_condition=FilterCondition(
                by=OutcomeKeys.DECISION_POINTS, where=Condition.GTE, value=15000
            )
        ),
        Bet(outcome_id="0-id", points=0),
        SettingsFiltered(
            condition=FilterCondition(
                by=OutcomeKeys.DECISION_POINTS, where=Condition.GTE, value=15000
            ),
            compared_value=5000,
        ),
    ),
]


@pytest.mark.parametrize("settings,bet,expected", test_skip_bet_data)
def test_skip_bet(settings, bet, expected):
    streamer = MagicMock()
    streamer.settings = MagicMock()
    streamer.settings.bet = settings
    assert skip_bet(streamer, event, bet) == expected


start_time_a = datetime.datetime.fromisoformat("2026-08-01T15:00:00Z")
test_get_prediction_time_data = [
    # FROM_START
    (
        DelayMode.FROM_START,
        10,
        start_time_a,
        120,
        datetime.datetime.fromisoformat("2026-08-01T15:00:10Z"),
    ),
    # FROM_START, clamped to end
    (
        DelayMode.FROM_START,
        200,
        start_time_a,
        120,
        datetime.datetime.fromisoformat("2026-08-01T15:02:00Z"),
    ),
    # FROM_END
    (
        DelayMode.FROM_END,
        10,
        start_time_a,
        120,
        datetime.datetime.fromisoformat("2026-08-01T15:01:50Z"),
    ),
    # FROM_END, clamped to start
    (
        DelayMode.FROM_END,
        200,
        start_time_a,
        120,
        datetime.datetime.fromisoformat("2026-08-01T15:00:00Z"),
    ),
    # PERCENTAGE, at start
    (
        DelayMode.PERCENTAGE,
        0,
        start_time_a,
        120,
        datetime.datetime.fromisoformat("2026-08-01T15:00:00Z"),
    ),
    # PERCENTAGE, middle
    (
        DelayMode.PERCENTAGE,
        0.5,
        start_time_a,
        120,
        datetime.datetime.fromisoformat("2026-08-01T15:01:00Z"),
    ),
    # PERCENTAGE, end
    (
        DelayMode.PERCENTAGE,
        1,
        start_time_a,
        120,
        datetime.datetime.fromisoformat("2026-08-01T15:02:00Z"),
    ),
    # PERCENTAGE, clamped to start
    (
        DelayMode.PERCENTAGE,
        -1,
        start_time_a,
        120,
        datetime.datetime.fromisoformat("2026-08-01T15:00:00Z"),
    ),
    # PERCENTAGE, clamped to end
    (
        DelayMode.PERCENTAGE,
        1.5,
        start_time_a,
        120,
        datetime.datetime.fromisoformat("2026-08-01T15:02:00Z"),
    ),
    # Default
    (
        None,
        10,
        start_time_a,
        120,
        datetime.datetime.fromisoformat("2026-08-01T15:02:00Z"),
    ),
]


@pytest.mark.parametrize(
    "delay_mode,delay,created_at,prediction_window_seconds,expected",
    test_get_prediction_time_data,
)
def test_get_prediction_time(
    delay_mode, delay, created_at, prediction_window_seconds, expected
):
    streamer = MagicMock()
    streamer.settings = MagicMock()
    streamer.settings.bet = BetSettings(delay_mode=delay_mode, delay=delay)

    event = MagicMock()
    event.created_at = created_at
    event.prediction_window_seconds = prediction_window_seconds

    assert get_prediction_time(streamer, event) == expected


test_make_prediction_data = [
    # Event untracked
    (False, False, None, None, False, False, False),
    # Streamer untracked
    (True, False, None, None, False, False, False),
    # Event skipped
    (True, True, "Skip Event", None, False, False, True),
    # Create bet filter
    (True, True, None, "Skip create bet", False, False, True),
    # Skip bet
    (
        True,
        True,
        None,
        Bet(outcome_id="019fdd38-d82c-7575-b487-aa60a611d33b", points=10),
        "Skip bet",
        False,
        True,
    ),
    # All pass
    (
        True,
        True,
        None,
        Bet(outcome_id="019fdd39-13b9-74a9-bab7-126d366c0312", points=100),
        None,
        True,
        False,
    ),
]


@pytest.mark.parametrize(
    "event_tracked,streamer_tracked,skip_event,bet,skip_bet,expect_make_prediction,expect_manage_event",
    test_make_prediction_data,
)
def test_make_prediction(
    event_tracked,
    streamer_tracked,
    skip_event,
    bet,
    skip_bet,
    expect_make_prediction,
    expect_manage_event,
):
    prediction_events = dict()
    streamers = []
    channel_id = "123456"
    event_id = "019fbda4-8e1f-73b3-91dd-d22208f27d4c"
    if event_tracked:
        event = MagicMock()
        event.id = event_id
        event.channel_id = channel_id
        prediction_events[event_id] = event
    if streamer_tracked:
        streamer = MagicMock()
        streamer.channel_id = channel_id
        streamers.append(streamer)

    twitch = MagicMock()
    event_manager = MagicMock()

    predictor = BasicPredictor(
        twitch=twitch,
        streamers=streamers,
        prediction_events=prediction_events,
        event_manager=event_manager,
    )
    predictor.skip_event = MagicMock()
    predictor.skip_event.return_value = skip_event
    predictor.create_bet = MagicMock()
    predictor.create_bet.return_value = bet
    predictor.skip_bet = MagicMock(spec=Bet)
    predictor.skip_bet.return_value = skip_bet

    predictor.make_prediction(event_id)

    if expect_make_prediction:
        twitch.make_prediction.assert_called_once()
    if expect_manage_event:
        event_manager.manage.assert_called()


start_time_b = datetime.datetime.fromisoformat("2026-08-02T06:00:00Z")
test_event_created_data = [
    # Streamer untracked
    (False, 0, 0, False, start_time_b, start_time_b, False, None),
    # Not enough points, 10 < 100
    (True, 100, 10, True, start_time_b, start_time_b, False, None),
    # Event too short by 1s
    (
        True,
        10,
        100,
        False,
        datetime.datetime.fromisoformat("2026-08-02T06:00:01Z"),
        datetime.datetime.fromisoformat("2026-08-02T06:00:02Z"),
        True,
        None,
    ),
    # Event too short by 1s
    (
        True,
        None,
        100,
        False,
        datetime.datetime.fromisoformat("2026-08-02T06:10:00Z"),
        datetime.datetime.fromisoformat("2026-08-02T06:00:02Z"),
        False,
        10 * 60 - 2,
    ),
]


@pytest.mark.parametrize(
    "streamer_tracked,minimum_points,channel_points,expect_not_enough_points,prediction_time,time_now,expect_event_too_short,expected_timer_seconds",
    test_event_created_data,
)
def test_event_created(
    streamer_tracked,
    minimum_points,
    channel_points,
    expect_not_enough_points,
    prediction_time,
    time_now,
    expect_event_too_short,
    expected_timer_seconds,
):
    channel_id = "123456"
    event_id = "019fc0d5-6978-7318-927c-79806d2629c1"
    streamers = []
    event = MagicMock()
    event.event_id = event_id
    event.channel_id = channel_id
    prediction_events: dict = {event_id: event}
    if streamer_tracked:
        streamer = MagicMock()
        streamer.channel_id = channel_id
        streamer.channel_points = channel_points
        streamer.settings = MagicMock()
        streamer.settings.bet = BetSettings(minimum_points=minimum_points)
        streamers.append(streamer)

    event_manager = MagicMock()

    timer = MagicMock()
    create_timer = MagicMock()
    create_timer.return_value = timer

    predictor = BasicPredictor(
        twitch=MagicMock(),
        streamers=streamers,
        prediction_events=prediction_events,
        event_manager=event_manager,
        timer_factory=create_timer,
    )
    predictor.get_prediction_time = MagicMock()
    predictor.get_prediction_time.return_value = prediction_time

    class MockDateTime:
        @classmethod
        def now(cls, tz=None):
            return time_now

    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(datetime, "datetime", MockDateTime)
        predictor.event_created(event)

    if expect_not_enough_points:
        event_manager.manage.assert_called_once_with(
            PredictionFilters(
                timestamp=time_now,
                streamer=streamer,
                prediction_event=event,
                reason=NotEnoughPoints(
                    channel_points=channel_points, minimum_points=minimum_points
                ),
            )
        )

    if expect_event_too_short:
        event_manager.manage.assert_called_once_with(
            PredictionFilters(
                timestamp=time_now,
                streamer=streamer,
                prediction_event=event,
                reason=EventTooShort(prediction_time=prediction_time),
            ),
        )

    if expected_timer_seconds is not None:
        event_manager.manage.assert_not_called()
        # Created and started timer
        create_timer.assert_called_once_with(
            expected_timer_seconds, predictor.make_prediction, [event_id]
        )
        assert timer.daemon is True
        timer.start.assert_called_once()
