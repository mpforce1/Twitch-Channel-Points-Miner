# Advanced Configuration

> [!NOTE]
> We are planning to introduce a text based configration method to help simplify this process.

Configuration is done via the `run.py` file. Please see the [example](/example.py) file for a configuration that uses
all available options.

There are 2 main sections to the file: [`TwitchChannelPointsMiner`](#twitchchannelpointsminer) and [
`TwitchChannelPointsMiner.mine`](#twitchchannelpointsminermine).

## TwitchChannelPointsMiner

This section explains all the configuration options for the miner. Each option is explained in the example, here we
expand more on their usage.

| Name                            | Type                                                 | Default                                             |
|---------------------------------|------------------------------------------------------|-----------------------------------------------------|
| `username`                      | `str`                                                | `"your-twitch-username"`                            |
| `password`                      | `str`                                                | `"write-your-secure-pws"`                           |
| `claim_drops_startup`           | `bool`                                               | `False`                                             |
| `priority`                      | `StreamerSelector` or `list[Priority]` or `Priority` | `[Priority.STREAK, Priority.DROPS, Priority.ORDER]` |
| `enable_analytics`              | `bool`                                               | `False`                                             |
| `disable_ssl_cert_verification` | `bool`                                               | `False`                                             |
| `disable_at_in_nickname`        | `bool`                                               | `False`                                             |
| `use_hermes`                    | `bool`                                               | `False`                                             |
| `logger_settings`               | `LoggerSettings`                                     | (see [here](#logger_settings))                      |
| `streamer_settings`             | `StreamerSettings`                                   | (see [here](#streamer_settings))                    |
| `gql`                           | `AttemptStrategy` or `GQLFactory`                    | `GQLFactory`                                        |

### `username`

This is the username of the Twitch account for which you want to mine channel points. If you do not change this value,
or you leave it empty, then the miner will output an error and halt. 

### `password`

This is the password of the Twitch account for which you want to mine channel points. If you do not change this value,
or you leave it empty, then the miner will output an error and halt.

### `claim_drops_startup`

If `True` the miner will automatically claim all unclaimed drops from your inventory at startup. If `False` it does not
do this.

### `priority`

This can be set to one of a `StreamerSelector`, a `list[Priority]`, or a single `Priority`. The value technically
defaults to `None` but this results in the miner using a priority of
`[Priority.STREAK, Priority.DROPS, Priority.ORDER]`.

#### `Priority` or `list[Priority]`

This is the most common use case. You can either use a single `Priority` or you can put several in a list. The miner
will prioritise watching streams according to each priority from left to right in the list.

`Priority` has several values:

- `ORDER`: This prioritises all streamers in the `streamers` list in the order they are defined from left to right (and
  top to bottom depending on formatting). If it exhausts this list, and you've provided `followers=True`, it will then
  consider all streamers in your followers list in the order you configure.
- `POINTS_ASCENDING`: This prioritises all streamers from the least channel points to the most.
- `POINTS_DESCENDING`: This prioritises all streamers from the most channel points to the least.
- `STREAK`: This prioritises streams that the miner thinks you don't yet have the streak for the current stream. Streak
  detection is not 100% so the miner may attempt to mine up to 2 `WATCH` messages before assuming it has the streak.
  This is due to a limitation of the Twitch API.
- `DROPS`: This prioritises streams with an active drops campaign with unclaimed drops. Ignores drops that require subs.
- `SUBSCRIBED`: This prioritises streamers for which you have an active subscription.
  
#### `StreamerSelector`

> [!WARNING]
> This is intended for advanced users as it requires an understanding of Python syntax and basic coding.

You can completely override the way the miner selects streamers to watch by providing a custom `StreamerSelector`.
See [here](/TwitchChannelPointsMiner/classes/StreamerSelector.py) to see how they are implemented. While you can
implement this yourself to provide arbitrary selection behaviour, we also ship the miner with several possible
implementations:

##### `PrioritySelector`

This is the default selector, it takes a `list[Priority]` and chooses streamers according to each `Priority` from left
to right. Optionally, you may override the function used per `Priority` by setting it in `priority_function_overrides`,
this is a `dict[Priority, PriorityFunction]` where `PriorityFunction` is something that takes a
`streamer: Sequence[Streamer]` and a `max_amount: int` and returns a `list[str]` where the strings are the channel ids
of the streams selected. For example: 

```python3
PrioritySelector(
    priorities=[Priority.STREAK, Priority.ORDER],
    priority_function_overrides={
        Priority.STREAK: priority_streak_by_earliest_stream_created_at,
    }
)
```

In this case, we've overridden the functionality of the `STREAK` selector to the
`priority_streak_by_earliest_stream_created_at` function. This will still select only from streams without the streak
but will prioritise them based on the time the stream started rather than the order they appear in the `streamers` list.

You can also write your own priority function(s) to use, they'll work as long as they comply with the `PriorityFunction`
interface. For example:

```python3
def my_priority_function(streamers: Sequence[Streamer], max_amount: int) -> list[str]:
    return list(reversed(streamers))[:max_amount]

PrioritySelector(
    priorities=[Priority.STREAK, Priority.ORDER],
    priority_function_overrides={
        Priority.ORDER: my_priority_function,
    }
)
```

In this case, when considering order the selector will check the `my_priority_function` function. This function
prioritises streamers in the reverse of the order they are defined.

##### `PriorityGroupSelector`

This selector applies a given `PrioritySelector` to a particular group of streamers. The streamers can be configured in
several different ways:

It can take a `list[str]` (Twitch usernames). It will select only streamers with the given usernames using the given
selector. For example:

```python3
PriorityGroupSelector(
    streamers=["streamer1", "streamer2"],
    selector=PrioritySelector(
        priorities=[Priority.Order]
    )
)
```

This will attempt to select only `streamer1` or `streamer2` in that order.

You can also not specify `streamers` in which case it will consider all streamers:

```python3
PriorityGroupSelector(
    selector=PrioritySelector(
        priorities=[Priority.Order]
    )
)
```

The same thing happens if you supply `streamers` with an empty list (`[]`):

```python3
PriorityGroupSelector(
    streamers=[],
    selector=PrioritySelector(
        priorities=[Priority.Order]
    )
)
```

You can also specify a `StreamerSource` to consider only streamers that were sourced in the given way:

```python3
PriorityGroupSelector(
    streamers=StreamerSource.Streamers,
    selector=PrioritySelector(
        priorities=[Priority.Order]
    )
)
```

`StreamerSource.Streamers` means all streamers specified in your `streamers` list, not including followers,
see [here](#streamers) for details. `StreamerSource.Followers` means all streamers that your account follows, see
[here](#followers) for details.

You may also specify an arbitrary filter function:

> [!IMPORTANT]
> Please test that your filter function works the way you expect. We can't help debug code that's not part of the
> project.

```python3
PriorityGroupSelector(
    streamers=lambda streamer: streamer.channel_points < 5000,
    selector=PrioritySelector(
        priorities=[Priority.Order]
    )
)
```

In this case we've specified a function that takes a `Streamer` and returns `True` if they have fewer than 5000 channel
points. You can replace that function with anything that takes a `Streamer` and returns a `bool`.

##### `NestedSelector`

This allows you to specify multiple `StreamerSelectors` in a list and delegate to them in order from left to right. For
example:

```python3
NestedSelector(
    [
        PriorityGroupSelector(
            selector=PrioritySelector(
                priorities=[Priority.STREAK]
            )
        ),
        PriorityGroupSelector(
            streamers=["streamer1", "streamer2"],
            selector=PrioritySelector(
                priorities=[Priority.ORDER]
            )
        ),
        PrioritySelector(
            priorities=[Priotiry.DROPS, Priority.ORDER]
        )
    ]
)
```

This would prioritise:

1. First any streams that don't yet have the watch streak for the current stream.
2. Then `streamer1` and `streamer2`.
3. Finally, all streamers first by `DROPS` then by `ORDER`.

### `enable_analytics`

If set to `True` you can run the analytics server by calling `TwitchChannelPointsMiner.analytics()`. If set to `False`
the miner won't bother doing setup tasks for the analytics server.

For more information on the analytics server please see [here](analytics.md).

### `disable_ssl_cert_verification`

> [!CAUTION]
> This is not recommended due to security concerns.

This allows you to disable verification of SSL Certificates during WebSocket connections. Can potentially fix
`SSL: CERTIFICATE_VERIFY_FAILED` errors but comes with the risk of man in the middle attacks. Use at your own risk.

### `disable_at_in_nickname`

If this is set to `True` and you're using the `CHAT_MENTION` event (when your username gets mentioned in chat) the miner
will consider mentions of your username that don't include the '@' symbol. For example, if your username is `myusername`
both `Hi @myusername` and `Hi myusername` will trigger the `Event`. 

### `use_hermes`

If set to `True` the miner will use the Twitch Hermes WebSocket API when listening for events. This is a more recent API
that the current Twitch Web Client uses. We default to `False` as the old PubSub WebSocket API hasn't yet been disabled
and still works.

### `logger_settings`

This allows you to configure logging options. See [here](logs.md) for some examples.

| Name               | Type              | Default             |
|--------------------|-------------------|---------------------|
| `save`             | `bool`            | `True`              |
| `console_level`    | `int`             | `logging.INFO`      |
| `console_username` | `bool`            | `False`             |
| `auto_clear`       | `bool`            | `True`              |
| `time_zone`        | `str`             | `""` (empty string) |
| `file_level`       | `int`             | `logging.DEBUG`     |
| `emoji`            | `bool`            | `True`              |
| `less`             | `bool`            | `False`             |
| `colored`          | `bool`            | `True`              |
| `color_palette`    | `ColorPalette`    | `None`              |
| `telegram`         | `Telegram`        | `None`              |
| `discord`          | `Discord`         | `None`              |
| `webhook`          | `WebHook`         | `None`              |
| `matrix`           | `Matrix`          | `None`              |
| `pushover`         | `Pushover`        | `None`              |
| `gotify`           | `Gotify`          | `None`              |
| `hooks`            | `list[EventHook]` | `[]` (empty list)   |

#### `save`

If set to `True` the miner will save logs to a file in the `logs` directory. If `False` then logs will not be saved.

#### `console_level`

Set this to change the [log level](https://docs.python.org/3/library/logging.html#logging-levels) the miner will output
to the console. The default is `INFO` which means all logs from `ERROR` to `INFO` will be logged, while `DEBUG` logs
will be ignored.

As another example, you can set this to `ERROR` to only see `ERROR` logs, ignoring `DEBUG`, `INFO`, and `WARNING` logs.

You'll see `NOTSET` and `CRITIAL` in the `logging` documentation but the miner doesn't use those.

#### `console_username`

Adds a username to the beginning of every console log line if `True`. Also adds it any configured `EventHooks`
(Telegram, Discord, etc). Useful when you have several accounts.

#### `auto_clear`

Creates a file rotation handler with an interval of 1 day and backup count of 7 if `True` (default). This means the
miner will maintain 7 log files going back the last 7 days, after a day of logs the miner will:

1. Rename the current log file, appending the current date (formatted like `[username].log.[yyyy-mm-dd]`).
2. Potentially delete the oldest log file if more than 7 would exist.
3. Create a new log file and begin writing logs to that.

#### `time_zone`

Sets a specific time zone for console and file loggers.
Use [tz database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) names. Example: "America/Denver".

#### `file_level`

Similar to [`console_level`](#console_level), set this to change
the [log level](https://docs.python.org/3/library/logging.html#logging-levels) the miner will output to the file(s).

Using `DEBUG` will result in a large file size due to the amount of `DEBUG` logs produced. If this is too large for you
please try changing this to `INFO`.  

#### `emoji`

On Windows, the miner has a problem printing emoji, so you can try setting to `False` to disable emoji.

#### `less`

Reduces the length of most miner logs by attempting to include only the most important information. Use this if you need
shorter logs or a smaller file size.

#### `colored`

Set to `True` to enable coloured text when outputting logs to the console.

#### `color_palette`

Customises the colours used when printing to the console. Set this to a `ColorPalette` object, you can pass
any [Events](/TwitchChannelPointsMiner/classes/Settings.py) as a named argument set to any of the following
colours: `BLACK`, `RED`, `GREEN`, `YELLOW`, `BLUE`, `MAGENTA`, `CYAN`, `WHITE`, `RESET`. The names and values are
case-insensitive, and you may use a direct reference to the same `colorama.Fore` colours.

For example:

```python3
ColorPalette(
    STREAMER_online="GREEN",
    streamer_offline="red",
    BET_wiN=Fore.MAGENTA,
)
```

In this case, `STREAMER_ONLINE` events will be logged in `GREEN`, `STREAMER_OFFLINE` events will be logged in `RED`, and
`BET_WIN` events will be logged in `MAGENTA`.

#### `telegram`

One of the `EventHook` types, allows events to be sent to Telegram
using [sendMessage](https://core.telegram.org/bots/api#sendmessage).

| Name                    | Type           | Description                                                                     |
|-------------------------|----------------|---------------------------------------------------------------------------------|
| `chat_id`               | `int`          | The unique identifier of the target chat of the username of the target channel. |
| `token`                 | `str`          | The token for your Telegram bot.                                                |
| `events`                | `list[Events]` | The `Events` you want to send to telegram.                                      |
| `disable_notifciations` | `bool`         | `True` to trigger Telegram notifications without sound.                         |


#### `discord`

One of the `EventHook` types, allows events to be sent to Discord using
a [Webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks).

| Name          | Type           | Description                                  |
|---------------|----------------|----------------------------------------------|
| `webhook_api` | `str`          | This is the "Webhook URL" Discord gives you. |
| `events`      | `list[Events]` | The `Events` you want to send to Discord.    |

#### `webhook`

One of the `EventHook` types, allows events to be sent to a generic Webhook in a set format.

| Name       | Type           | Description                                   |
|------------|----------------|-----------------------------------------------|
| `endpoint` | `str`          | The URL of the Webhook.                       |
| `method`   | `str`          | The HTTP method to use when sending data.     |
| `events`   | `list[Events]` | The `Events` you want to send to the Webhook. |

#### `matrix`

One of the `EventHook` types, allows events to be sent to a [Matrix](https://matrix.org/docs/chat_basics/matrix-for-im/)
server.

| Name         | Type          | Description                                            |
|--------------|---------------|--------------------------------------------------------|
| `username`   | `str`         | Your Matrix username.                                  |
| `password`   | `str`         | Your Matrix password.                                  |
| `homeserver` | `str`         | The URL of the Matrix server (e.g. `"matrix.org"`      |
| `room_id`    | `str`         | The id of the room to which you want to send `Events`. |
| `events`     | `list[Event]` | The `Events` you want to send to Matrix.               |

#### `Pushover`

One of the `EventHook` types, allows events to be sent to a [Pushover](https://pushover.net/api) server.

| Name       | Type           | Description                                                                       |
|------------|----------------|-----------------------------------------------------------------------------------|
| `userkey`  | `str`          | [Log in](https://pushover.net/) and the user token is on the main page.           |
| `token`    | `str`          | Create a application on the website, and use the token shown in your application. |
| `priority` | `int`          | The [priority](https://pushover.net/api#priority) of the messages.                |
| `sound`    | `str`          | The [sound](https://pushover.net/api#sounds) to use for Pushover notifications.   |
| `events`   | `list[Events]` | The `Events` you want to send to Pushover.                                        |

#### `gotify`

One of the `EventHook` types, allows events to be send to a [Gotify](https://gotify.net/docs/index) server.

| Name       | Type          | Description                                                                                                       |
|------------|---------------|-------------------------------------------------------------------------------------------------------------------|
| `endpoint` | `str`         | The full URL of the gotify server, including the path and token. i.e. `"https://example.com/message?token=TOKEN"` |
| `priority` | `int`         | The priority of the message.                                                                                      |
| `events`   | `list[Event]` | The `Events` you want to send to Gotify.                                                                          |


#### `hooks`

A list of arbitrary `EventHook` objects. This can be used in place of or in addition to the above `EventHook` types.
This list allows you to define multiple hooks of any type. For example:

```python3
hooks=[
    Discord(
        webhook_api="https://discord.com/api/webhooks/0123456789/0a1B2c3D4e5F6g7H8i9J",
        events=[Events.GAIN_FOR_RAID, Events.GAIN_FOR_WATCH,
                Events.GAIN_FOR_CLAIM, Events.GAIN_FOR_WATCH_STREAK],
    ),
    Discord(
        webhook_api="https://discord.com/api/webhooks/9876543210/78ad737ba0e951cdfbde",
        events=[Events.BET_GENERAL, Events.BET_LOSE,
                Events.BET_WIN, Events.BET_REFUND],
    ),
    Gotify(
        endpoint="https://example.com/message?token=TOKEN",
        priority=8,
        events=[Events.STREAMER_ONLINE, Events.STREAMER_OFFLINE]
    ),
    Gotify(
        endpoint="https://example.com/message?token=TOKEN2",
        priority=8,
        events=[Events.JOIN_RAID, Events.CHAT_MENTION]
    ),
]    
```

This sends `GAIN_FOR...` events to one Discord Webhook and `BET...` events to a different one. It also sends
`STREAMER_ONLINE/OFFLINE` events to a Gotify application and sends `JOIN_RAID` and `CHAT_MENTION` events to another. 

### `streamer_settings`

This is the default settings to use for each streamer.

#### `make_predictions`

Set to `True` if you want to make predictions using your channel points.

#### `follow_raid`

Set to `True` if you want to follow raids for this streamer and receive the raid bonus points.

#### `claim_drops`

Set to `True` if you want to claim Drops for Campaigns this streamer is in. Will claim all drops for which you've met
the watch time requirements once every 15 minutes.

#### `claim_moments`

If set to `True`, [moments](https://help.twitch.tv/s/article/moments) will be claimed when available.

#### `watch_streak`

If set to `True` and `Priority.STREAK` is used, the miner will attempt to watch long enough to get the Watch Streak for
this streamer.

#### `community_goals`

If `True`, the miner will contribute the maximum channel points per stream to the streamer's community challenge goals.

#### `chat`

Join the streamer's IRC chat, can be set to one of these `ChatPresence`:

| Name      | Description                                                    |
|-----------|----------------------------------------------------------------|
| `ALWAYS`  | Always attempt to join this streamer's chat.                   |
| `NEVER`   | Never attempt to join this streamer's chat.                    |
| `ONLINE`  | Only attempt to join this streamer's chat when they're online. |
| `OFFLINE` | Only attempt to join this streamer's chat when thy're offline. |

#### `bet`

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

##### Example

- If you want to make a prediction ONLY if the total of predictors in the event is greater than 200:
  - `FilterCondition(by=OutcomeKeys.TOTAL_USERS, where=Condition.GT, value=200)`
- If you want to make a prediction ONLY if the winning odds of your decision is greater than or equal to 1.3:
  - `FilterCondition(by=OutcomeKeys.ODDS, where=Condition.GTE, value=1.3)`
- If you want to make a prediction ONLY if the prediction with the most points is lower than 2000:
  - `FilterCondition(by=OutcomeKeys.TOP_POINTS, where=Condition.LT, value=2000)`

##### `strategy`

| Name          | Description                                                                                               |
|---------------|-----------------------------------------------------------------------------------------------------------|
| `MOST_VOTED`  | Makes predictions on the outcome with the most number of individual predictions.                          |
| `HIGH_ODDS`   | Makes predictions on the outcome with the highest odds (lowest percentage).                               |
| `PERCENTAGE`  | Makes predictions on the outcome with the highest percentage (lowest odds).                               |
| `SMART_MONEY` | Makes predictions on the outcome with the highest number of points in an individual predciton.            |
| `SMART`       | If more than `percentage_gap` choose a given outcome then choose that outcome. Otherwise use `HIGH_ODDS`. |
| `NUMBER_[N]`  | Where `[N]` is the nth outcome in the list. You can pick any outcome from 1 to 8.                         |

##### `filter_condition`

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

###### `by`

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

###### `delay_mode`

A `DelayMode` can be one of the following:

| Name         | Description                                                       |
|--------------|-------------------------------------------------------------------|
| `FROM_START` | Waits `delay` seconds the start of the event.                     |
| `FROM_END`   | Waits until `delay` seconds until the end of the event.           |
| `PERCENTAGE` | Waits `delay`% of the event duration from the start of the event. |

### `gql`

Defines how the miner interacts with the Twitch GQL (Graph Query Language) API. The default behaviour is to make up to 3
attempts with a 1-second delay between attempts. However, some responses shouldn't be retried, so in those cases we stop
making attempts early.

| Key                      | Type | Default | Description                                                                                                                                       |
|--------------------------|------|---------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| attempts                 | int  | 3       | The number of attempts the miner will make per request to the Twitch GQL API.<br/>Must be at least 1 in order to make any requests.               |
| attempt_interval_seconds | int  | 1       | The number of seconds the miner will wait in between attempts.                                                                                    |

#### Examples
```python
gql=None
```
In this case the default behaviour will be used, which is the miner will make up to 3 attempts at each request with a
1-second delay between each request. Omitting the `gql` key (and value) will also cause the miner to use this default
behaviour.

```python
gql=AttemptStrategy(
   attempts=5,
   attempt_interval_seconds=2
)
```
In this case the miner will make up 5 attempts at each request with a 2-second delay between each request.

```python
gql=GQLFactory(
   attempt_strategy=AttemptStrategy(
      attempts=3,
      attempt_interval_seconds=1
   ),
   parser=Parser(),
   post_request
)
```
> [!IMPORTANT]
> This is intended for advanced users only.

You can completely override the GQL implementation by providing
a [GQLFactory](/TwitchChannelPointsMiner/classes/gql/Integration.py) instance. The base usage allows you to
override the `attempt_strategy`, `parser`, and `post_request`. `attempt_strategy` has already been covered, but it
allows you to define how the GQL integration makes attempts at each request. `parser` is the class responsible for
parsing the json returned from the GQL API into usable types. `post_request` is the function that can make web requests
to the API. We don't expect most users to need to do more than override the `attempt_strategy`, which is why we allow
passing that directly to the value of `gql`. Advanced users can also override the factory type for even more
customization, perhaps returning a custom subclass of `GQL` that overrides the original behaviour entirely.

## `TwitchChannelPointsMiner.mine`

This is where you list the streamers you want to mine. There are 4 arguments you can pass: `streamers`, `blacklist`,
`followers`, and `followers_order`.

### `streamers`

Here you can specify the streamers you want to mine and override the default streamer settings on a per-streamer basis.
The valid values for an entry in this list are either a string representing the streamer's username or a `Streamer`
object. You may mix both options. For example:

```python3
[
    "streamer1",
    "streamer2",
    Streamer(
        "streamer3",
        settings=StreamerSettings(
            make_predictions=False
        )
    ),
    Streamer(
        "streamer4",
        settings=StreamerSettings(
            community_goals=True
        )
    ),
    "streamer5"
]
```

In this case we want to mine 4 streamers, "streamer1", "streamer2", and "streamer3" will use whatever default settings
you provided earlier. While "streamer3" and "streamer4" have overidden the `make_predictions` and `community_goals`
values respectively.

When overriding values in `StreamerSettings` the miner will only override the specific values you provide. Meaning
values not specified will be set to the values given above rather than the miner default for `StreamerSettings`.

### `blacklist`

This is a list of streamers that you don't want to miner. Mainly useful in order to filter out streamers from your
`followers` list. It should be formatted as a list of strings where each string is the channel name of the streamer you
don't want to mine, i.e. `["streamer1", "streamer2"]`.

### `followers`

Set this to `True` to mine streamers that your account follows. The miner will, at startup, download your followers list
and append them to the bottom of the `streamers` list.

### `followers_order`

This is the order followers will be in when added to the `streamers` list. Possible values are `ASC` which sorts them by
oldest follow first, or `DESC` which sorts them by most recent follow first.