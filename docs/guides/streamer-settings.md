# `StreanerSettings`

This is the settings to use for each streamer.

## `make_predictions`

Set to `True` if you want to make predictions using your channel points.

## `follow_raid`

Set to `True` if you want to follow raids for this streamer and receive the raid bonus points.

## `claim_drops`

Set to `True` if you want to claim Drops for Campaigns this streamer is in. Will claim all drops for which you've met
the watch time requirements once every 15 minutes.

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
the latest stream segment. This does not result in the miner downloading **any** stream video. In the process, we also
get a `PlaybackAccessToken` from Twitch. This may result in better watch simulation, users have reported getting more
gift subs with this enabled.

This can be set to either `False`, in which case HLS playback is disabled, or an `HLSSettings` object which allows you
to set the number of seconds before expiry to refresh the `PlaybackAccessToken`:

```python
HLSSettings(
    refresh_before=5 * 60
)
```

In this example, I've set the number of seconds to `5 * 60` or 5 minutes. This will cause the token to get refreshed
once we get to 5 minutes before the token expires. Tokens typically last for 20 minutes. The default is 120 seconds (2
minutes).

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
