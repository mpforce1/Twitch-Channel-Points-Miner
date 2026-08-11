from typing import Callable, get_type_hints, is_typeddict
from TwitchChannelPointsMiner.JsonParser import (
    InvalidJsonShapeError,
    expect_dict,
    expect_str,
    parse_expected_value,
)
from TwitchChannelPointsMiner.classes.translator.Model import (
    ArgChangingWatchSlots,
    ArgChatMention,
    ArgCommunityGoalContribution,
    ArgConditional,
    ArgCount,
    ArgDrop,
    ArgDropWithStreamer,
    ArgDropsDrop,
    ArgError,
    ArgErrorCode,
    ArgErrorOccurred,
    ArgEventCreated,
    ArgEventUpdated,
    ArgFilters,
    ArgGainPoints,
    ArgGiftSubReceived,
    ArgJoinRaid,
    ArgNotEnoughPoints,
    ArgOutcome,
    ArgPoints,
    ArgPredictionMade,
    ArgPredictionResult,
    ArgReason,
    ArgStake,
    ArgStatus,
    ArgStreamer,
    ArgStreamerAndCount,
    ArgStreamers,
    ArgTime,
    ArgTitle,
    ArgTotalPoints,
    ArgType,
    ArgUserPrediction,
    ArgValue,
    ArgWeeklyRewardsUpdate,
    ArgWinningOutcome,
    ChangingWatchSlots,
    CommunityGoalContribution,
    Drops,
    Error,
    Filters,
    GiftSubReceived,
    Optional,
    Pluralizable,
    Points,
    PredictionMade,
    PredictionResult,
    Predictions,
    Reasons,
    Requires,
    StaticString,
    Translation,
    WeeklyRewardsUpdate,
)

# Formatters


#  Requires


def expect_has(value, field_name: str):
    """
    Expect a value to be a string and to contain the given string template identifiers.
    :param value: The value to check.
    :param field_name: The field name.
    """
    value = expect_str(value)
    # double { to escape it, another to insert expectation
    if f"{{{field_name}}}" not in value:
        raise InvalidJsonShapeError(
            path=[], message=f"{{{field_name}}} missing from {value}"
        )
    return value


def expect_has_all(value, *field_names: str):
    """
    Parser that expects the value to be a string that contains template identifiers for each of the given field names.
    :param value: The value to parse.
    :param field_names: The expected field names.
    :return: The parsed string.
    """
    value = expect_str(value)
    for field_name in field_names:
        expect_has(value, field_name)
    return value


# Ignore that warning as we're manually guaranteeing the type is correct via `expect_has_all`
def requires_by_name_parser[TArg](
    *names: str,
) -> Callable[[object], Requires[TArg]]:  # pyright: ignore [reportInvalidTypeVarUse]
    """
    Gets a parser that, given a list of field names, validates that a given string contains template identifiers
    for each.
    :param names: The field names.
    :return: The parser function.
    """

    def inner(value):
        value = expect_has_all(value, *names)
        return Requires[TArg](value=value)

    return inner


def get_typed_dict_field_names(t: type) -> list[str]:
    """
    Gets a list of the field names of each field in a TypedDict
    :param t: The type of the TypedDict to check
    :return: The names.
    """
    if is_typeddict(t):
        return [k for k in get_type_hints(t)]
    else:
        raise ValueError(
            f"Unable to get the field names of non-TypedDict type '{t.__name__}'"
        )


def requires_parser[TArg](t: type[TArg]) -> Callable[[object], Requires[TArg]]:
    """
    Gets a parser for Requires[TArg] where TArg should be a TypedDict.
    :param t: The type of the requirement.
    :return: The parser.
    """
    return requires_by_name_parser(*get_typed_dict_field_names(t))


#  Optional
def static_string_parser(value):
    return StaticString(value=expect_str(value))


def optional_parser[TArg](some_type: type[TArg]) -> Callable[[object], Optional[TArg]]:
    """
    Gets a parser that can parse Optional values.
    :param some_type: The type of the value of "some".
    :return: The parser.
    """

    def inner(value):
        value = expect_dict(value)
        return Optional(
            some=parse_expected_value(value, "some", requires_parser(some_type)),
            none=parse_expected_value(value, "none", static_string_parser),
        )

    return inner


#  Pluralizable


def pluralizable_parser[TArg: ArgCount](
    arg_type: type[TArg],
) -> Callable[[object], Pluralizable[TArg]]:
    """
    Gets a parser that can parse Pluralizable values.
    :param arg_type: The type of the plural values.
    :return: The parser.
    """

    def inner(value):
        value = expect_dict(value)
        return Pluralizable[TArg](
            singular=parse_expected_value(value, "singular", requires_parser(arg_type)),
            plural=parse_expected_value(value, "plural", requires_parser(arg_type)),
        )

    return inner


# Model


#  Predictions
def prediction_made_parser(value):
    value = expect_dict(value)
    return PredictionMade(
        points=parse_expected_value(value, "points", pluralizable_parser(ArgCount)),
        total_update=parse_expected_value(
            value, "total_update", optional_parser(ArgTotalPoints)
        ),
        main=parse_expected_value(value, "main", requires_parser(ArgPredictionMade)),
    )


def reasons_parser(value):
    value = expect_dict(value)
    return Reasons(
        too_short=parse_expected_value(value, "too_short", requires_parser(ArgTime)),
        not_enough_points=parse_expected_value(
            value, "not_enough_points", requires_parser(ArgNotEnoughPoints)
        ),
        not_active=parse_expected_value(
            value, "not_active", requires_parser(ArgStatus)
        ),
        below_minimum=parse_expected_value(
            value, "below_minimum", requires_parser(ArgStake)
        ),
        settings=parse_expected_value(
            value, "settings", requires_parser(ArgConditional)
        ),
    )


def filters_parser(value):
    value = expect_dict(value)
    return Filters(
        reasons=parse_expected_value(value, "reasons", reasons_parser),
        main=parse_expected_value(value, "main", requires_parser(ArgFilters)),
    )


def points_parser(value):
    value = expect_dict(value)
    return Points(
        win=parse_expected_value(value, "win", requires_parser(ArgPoints)),
        lose=parse_expected_value(value, "lose", requires_parser(ArgPoints)),
        refund=parse_expected_value(value, "refund", requires_parser(ArgPoints)),
    )


def prediction_result_parser(value):
    value = expect_dict(value)
    return PredictionResult(
        winning_outcome=parse_expected_value(
            value, "winning_outcome", optional_parser(ArgWinningOutcome)
        ),
        user_prediction=parse_expected_value(
            value, "user_prediction", requires_parser(ArgUserPrediction)
        ),
        user_result=parse_expected_value(
            value, "user_result", requires_parser(ArgType)
        ),
        points=parse_expected_value(value, "points", points_parser),
        main=parse_expected_value(value, "main", requires_parser(ArgPredictionResult)),
    )


def predictions_parser(value):
    value = expect_dict(value)
    return Predictions(
        outcome_simple=parse_expected_value(
            value, "outcome_simple", requires_parser(ArgTitle)
        ),
        outcome=parse_expected_value(value, "outcome", requires_parser(ArgOutcome)),
        event_created=parse_expected_value(
            value, "event_created", requires_parser(ArgEventCreated)
        ),
        prediction_made=parse_expected_value(
            value, "prediction_made", prediction_made_parser
        ),
        filters=parse_expected_value(value, "filters", filters_parser),
        event_update=parse_expected_value(
            value, "event_update", requires_parser(ArgEventUpdated)
        ),
        prediction_result=parse_expected_value(
            value, "prediction_result", prediction_result_parser
        ),
        prediction_failed=parse_expected_value(
            value, "prediction_failed", requires_parser(ArgErrorCode)
        ),
    )


#  Other


def weekly_rewards_update_parser(value):
    value = expect_dict(value)
    return WeeklyRewardsUpdate(
        days=parse_expected_value(value, "days", pluralizable_parser(ArgCount)),
        main=parse_expected_value(
            value, "main", requires_parser(ArgWeeklyRewardsUpdate)
        ),
    )


def drops_parser(value):
    value = expect_dict(value)
    return Drops(
        drop=parse_expected_value(value, "drop", requires_parser(ArgDropsDrop)),
        progress=parse_expected_value(
            value, "progress", requires_parser(ArgDropWithStreamer)
        ),
        with_streamer=parse_expected_value(
            value, "with_streamer", optional_parser(ArgStreamer)
        ),
        claim_available=parse_expected_value(
            value, "claim_available", requires_parser(ArgDropWithStreamer)
        ),
        claim=parse_expected_value(value, "claim", requires_parser(ArgDrop)),
    )


def gift_sub_received_parser(value):
    value = expect_dict(value)
    return GiftSubReceived(
        gifter=parse_expected_value(value, "gifter", optional_parser(ArgValue)),
        days=parse_expected_value(value, "days", pluralizable_parser(ArgCount)),
        main=parse_expected_value(value, "main", requires_parser(ArgGiftSubReceived)),
    )


def changing_watch_slots_parser(value):
    value = expect_dict(value)
    return ChangingWatchSlots(
        streamer=parse_expected_value(value, "streamer", requires_parser(ArgStreamer)),
        adding=parse_expected_value(value, "adding", optional_parser(ArgStreamers)),
        dropping=parse_expected_value(value, "dropping", optional_parser(ArgStreamers)),
        main=parse_expected_value(
            value, "main", requires_parser(ArgChangingWatchSlots)
        ),
    )


def community_goal_contribution_parser(value):
    value = expect_dict(value)
    return CommunityGoalContribution(
        points=parse_expected_value(value, "points", pluralizable_parser(ArgCount)),
        main=parse_expected_value(
            value, "main", requires_parser(ArgCommunityGoalContribution)
        ),
    )


def error_parser(value):
    value = expect_dict(value)
    return Error(
        error_str=parse_expected_value(value, "error_str", optional_parser(ArgError)),
        occurred=parse_expected_value(
            value, "occurred", requires_parser(ArgErrorOccurred)
        ),
    )


# Main parser


def translation_parser(root):
    root = expect_dict(root)
    return Translation(
        stream_up=parse_expected_value(root, "stream_up", requires_parser(ArgStreamer)),
        stream_down=parse_expected_value(
            root, "stream_down", requires_parser(ArgStreamer)
        ),
        stream_view_count=parse_expected_value(
            root,
            "stream_view_count",
            pluralizable_parser(ArgStreamerAndCount),
        ),
        streamer_online=parse_expected_value(
            root, "streamer_online", requires_parser(ArgStreamer)
        ),
        streamer_offline=parse_expected_value(
            root, "streamer_offline", requires_parser(ArgStreamer)
        ),
        bonus_points_available=parse_expected_value(
            root, "bonus_points_available", requires_parser(ArgStreamer)
        ),
        gain_points=parse_expected_value(
            root, "gain_points", requires_parser(ArgGainPoints)
        ),
        points_spent=parse_expected_value(
            root,
            "points_spent",
            pluralizable_parser(ArgStreamerAndCount),
        ),
        watch_streak_progress=parse_expected_value(
            root,
            "watch_streak_progress",
            requires_parser(ArgStreamer),
        ),
        watch_streak_missing=parse_expected_value(
            root,
            "watch_streak_missing",
            requires_parser(ArgStreamer),
        ),
        watch_streak_recovery=parse_expected_value(
            root, "watch_streak_recovery", requires_parser(ArgStreamer)
        ),
        weekly_rewards_update=parse_expected_value(
            root, "weekly_rewards_update", weekly_rewards_update_parser
        ),
        predictions=parse_expected_value(root, "predictions", predictions_parser),
        moment_claim_available=parse_expected_value(
            root, "moment_claim_available", requires_parser(ArgStreamer)
        ),
        drops=parse_expected_value(root, "drops", drops_parser),
        chat_mention=parse_expected_value(
            root, "chat_mention", requires_parser(ArgChatMention)
        ),
        gift_sub_received=parse_expected_value(
            root, "gift_sub_received", gift_sub_received_parser
        ),
        join_raid=parse_expected_value(root, "join_raid", requires_parser(ArgJoinRaid)),
        bonus_points_claim=parse_expected_value(
            root, "bonus_points_claim", requires_parser(ArgStreamer)
        ),
        moment_claim=parse_expected_value(
            root, "moment_claim", requires_parser(ArgStreamer)
        ),
        changing_watch_slots=parse_expected_value(
            root, "changing_watch_slots", changing_watch_slots_parser
        ),
        community_goal_contribution=parse_expected_value(
            root, "community_goal_contribution", community_goal_contribution_parser
        ),
        shutdown=parse_expected_value(root, "shutdown", requires_parser(ArgReason)),
        error=parse_expected_value(root, "error", error_parser),
    )
