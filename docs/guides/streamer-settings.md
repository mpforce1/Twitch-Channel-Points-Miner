# `StreanerSettings`

This is the settings to use for each streamer.

## `make_predictions`

Set to `True` if you want to make predictions using your channel points.

## `follow_raid`

Set to `True` if you want to follow raids for this streamer and receive the raid bonus points.

## `claim_drops`

> [!NOTE]
> Linking your Twitch account is now a requirement for most Drops Campaigns, exceptions **may** include Drops that
> reward just Twitch badges.

This setting controls whether we consider the active, progressable Drops Campaigns for this Streamer when selecting them
to watch. This can be set to `True`, `False`, or one of the `DropsMode` enums. Your options are:

- `DropsMode.NONE` or `False`, in this case the miner will not consider Drops Campaigns for this Streamer.
  to watch.
- `DropsMode.ALL`, in this case the miner will always consider all progressable Drops Campaigns for this Streamer.
- `DropsMode.LINKED` or `True` (default), in this case the miner will only consider Drops Campaigns for Categories that
  require account linking for which you've linked your Twitch account. Campaigns that don't require linking are still
  considered.

Since Twitch now generally requires account linking, the default case `True` is equivalent to `DropsMode.LINKED`.

Despite the name, this setting does not, and never did, affect drops claiming. Claiming is done at the account level,
not the Streamer level.

## `claim_moments`

If set to `True`, [moments](https://help.twitch.tv/s/article/moments) will be claimed when available.

## `watch_streak`

If set to `True` and `Priority.STREAK` is used, the miner will attempt to watch long enough to get the Watch Streak for
this streamer.

## `community_goals`

If `True`, the miner will contribute the maximum channel points per stream to the streamer's community challenge goals.

## `chat`

Join the streamer's IRC chat, can be set to one of these `ChatPresence`:

| Name      | Description                                                     |
|-----------|-----------------------------------------------------------------|
| `ALWAYS`  | Always attempt to join this streamer's chat.                    |
| `NEVER`   | Never attempt to join this streamer's chat.                     |
| `ONLINE`  | Only attempt to join this streamer's chat when they're online.  |
| `OFFLINE` | Only attempt to join this streamer's chat when they're offline. |

## `simulate_hls_playback`

This enables what was previously called M3U8 playback, essentially we simulate "watching" by making a HEAD request to
stream segments. This does not result in the miner downloading **any** stream video. In the process, we also get a
`PlaybackAccessToken` from Twitch. This may result in better watch simulation, users have reported getting more gift
subs with this enabled.

This can be set to either `False`, in which case HLS playback is disabled, or an `HLSSettings` object which allows you
to set the number of seconds before expiry to refresh the `PlaybackAccessToken`, and the playback method:

```python
HLSSettings(
    refresh_before=5 * 60,
    watch_all_segments="enable",  # "enable", "disable", or "drops"
)
```

In this example, I've set the number of seconds to `5 * 60` or 5 minutes. This will cause the token to get refreshed
once we get to 5 minutes before the token expires. Tokens typically last for 20 minutes. The default is 120 seconds (2
minutes). We also set the `watch_all_segments` to `"enable"` which causes the miner to always request all stream
segments when simulating HLS playback. It can be set to any of the following strings:

- `"enable"`, always attempt to watch every stream segment.
- `"disable"`, never attempt to watch every stream segment, only watch the last available segment.
- `"drops"` (default), only attempt to watch every stream segment if the Stream has an active, progressable Drops
  Campaign.

When requesting all stream segments, we make about 10 times as many network requests as when only requesting the last
segment. So this playback mode has higher network traffic than just requesting the last segment, but it's closer to
simulating the actual playback of Twitch's video players.

`"disable"` is a great option if you don't care about drops, this will allow you to collect channel points with the
least network traffic. `"enable"` is a great option if you want closer playback simulation to the actual Twitch players.
`"drops"` is a middle option, for if you want to progress Drops but want to reduce network traffic as much as possible
given that.

In the default case, HLS Playback is enabled with `refresh_before=2 * 60` (2 minutes) and `watch_all_segments="drops"`.

## `weekly_rewards`

Enables automatic progression of Weekly Rewards for this streamer. This includes both selecting them when using
`Priority.WEEKLY_REWARDS` and automatic progression when the streamer is offline. Defaults to `True`.

## 'points_limit'

Set this to a whole positive number (e.g. `1000`, `50000`) to enable a limit on the amount of points that the miner will
attempt to get for this Streamer. This only applies to `Priority.ORDER`, `Priority.POINTS_ASCENDING`,
`Priority.POINTS_DESCENDING`, and `Priority.SUBSCRIBED`. Set this to `None` or `False` to disable.

## `bet`

> [!NOTE]
> Terminology:
>
> - "Prediction Event" refers to the event on which you can make predictions.
> - "Outcome" refers to one of the options you can select in a prediction event.
> - "Prediction" refers to an individual wager on an outcome in a prediction event.
> - "Decision" refers to the outcome miner has decided to pick.

Set this to a `BetStrategy` to configure how the miner makes predictions for prediction events for this streamer.

| Name               | Type              | Default          | Description                                                                                                                                                     |
|--------------------|-------------------|------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `strategy`         | `Strategy`        | `Strategy.SMART` | See [here](#strategy) for more information.                                                                                                                     |
| `percentage`       | `int`             | `5`              | The maximum percentage of your channel points to wager in a given prediction.                                                                                   |
| `percentage_gap`   | `int`             | `20`             | In the `SMART` strategy, if the difference between outcomes 1 and 2 is less than this `ODDS` will be used, otherwise `TOTAL_USERS` will be used.                |
| `max_points`       | `int`             | `50000`          | The maximum number of your channel points to wager in a given prediction.                                                                                       |
| `minimum_points`   | `int`             | `0`              | If you have fewer than this many channel points, predictions will not be made.                                                                                  |
| `stealth_mode`     | `bool`            | `False`          | If `True` always wagers fewer than the highest number of points on the decided outcome. This avoids your username being displayed in the web client if you win. |
| `filter_condition` | `FilterCondition` | `None`           | See [here](#filter_condition) for more information.                                                                                                             |
| `delay`            | `float`           | `6`              | Relates to `delay_mode`, expressed as a number of seconds.                                                                                                      |
| `delay_mode`       | `DelayMode`       | `FROM_END`       | See [here](#delay_mode) for more information.                                                                                                                   |

### Example

- If you want to make a prediction ONLY if the total of predictors in the event is greater than 200:
    - `FilterCondition(by=OutcomeKeys.TOTAL_USERS, where=Condition.GT, value=200)`
- If you want to make a prediction ONLY if the winning odds of your decision is greater than or equal to 1.3:
    - `FilterCondition(by=OutcomeKeys.ODDS, where=Condition.GTE, value=1.3)`
- If you want to make a prediction ONLY if the prediction with the most points is lower than 2000:
    - `FilterCondition(by=OutcomeKeys.TOP_POINTS, where=Condition.LT, value=2000)`

### `strategy`

| Name          | Description                                                                                               |
|---------------|-----------------------------------------------------------------------------------------------------------|
| `MOST_VOTED`  | Makes predictions on the outcome with the most number of individual predictions.                          |
| `HIGH_ODDS`   | Makes predictions on the outcome with the highest odds (lowest percentage).                               |
| `PERCENTAGE`  | Makes predictions on the outcome with the highest percentage (lowest odds).                               |
| `SMART_MONEY` | Makes predictions on the outcome with the highest number of points in an individual predciton.            |
| `SMART`       | If more than `percentage_gap` choose a given outcome then choose that outcome. Otherwise use `HIGH_ODDS`. |
| `NUMBER_[N]`  | Where `[N]` is the nth outcome in the list. You can pick any outcome from 1 to 8.                         |

### `filter_condition`

A `FilterCondition` takes the following arguments:

| Name    | Type          | Description                                                                                               |
|---------|---------------|-----------------------------------------------------------------------------------------------------------|
| `by`    | `OutcomeKeys` | See [here](#by) for more information.                                                                     |
| `where` | `Condition`   | `GT` (greater than), `LT` (less than), `GTE` (greater than or equal to), or `LTE`(less than or equal to). |
| `value` | `float`       | The number in the condition.                                                                              |

For example:

```python3
FilterCondition(
    by=OutcomeKeys.TOTAL_USERS,
    where=Condition.LTE,
    value=800,
)
```

Skips prediction events where the total number of users that have made a prediction is less than or equal to 800.

#### `by`

An `OutcomeKeys` can be one of the following:

| Name               | Outcome/Decision/Total | Description                                                                                                                     |
|--------------------|------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| `PERCENTAGE_USERS` | Outcome                | The percentage of number of users who have made a prediction on this outcome.                                                   |
| `ODDS_PERCENTAGE`  | Outcome                | The percentage of points wagered on this outcome expressed as a percentage, i.e. 50% of points would be `50` rather than `0.5`. |
| `ODDS`             | Outcome                | The value of the odds of this outcome.                                                                                          |
| `DECISION_USERS`   | Decision               | The total number of users that have placed a prediction on the decided outcome.                                                 |
| `DECISION_POINTS`  | Decision               | The total number of points that have been placed on the decided outcome.                                                        |
| `TOP_POINTS`       | Outcome                | The outcome with the most total points wagered.                                                                                 |
| `TOTAL_USERS`      | Total                  | The total number of users that have placed a wager in this prediction event.                                                    |
| `TOTAL_POINTS`     | Total                  | The total number of points that have been placed on this prediction event.                                                      |

- "Outcome" means a specific outcome in the prediction
- "Decision" means the outcome that the miner has decided to choose.
- "Total" means the total of the relevant thing in the prediction event, rather than any specific outcome.

#### `delay_mode`

A `DelayMode` can be one of the following:

| Name         | Description                                                       |
|--------------|-------------------------------------------------------------------|
| `FROM_START` | Waits `delay` seconds the start of the event.                     |
| `FROM_END`   | Waits until `delay` seconds until the end of the event.           |
| `PERCENTAGE` | Waits `delay`% of the event duration from the start of the event. |
