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

| Name                            | Type                                                                            | Default                                                                 |
|---------------------------------|---------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| `username`                      | `str`                                                                           | `"your-twitch-username"`                                                |
| `password`                      | `str`                                                                           | `"write-your-secure-pws"`                                               |
| `claim_drops_startup`           | `bool`                                                                          | `False`                                                                 |
| `priority`                      | `StreamerSelector` or `list[StreamerSelector]` or `list[Priority]` or `Priority` | `[watch_session(), watch_streak(), weekly_rewards(), drops(), order()]` |
| `enable_analytics`              | `bool`                                                                          | `False`                                                                 |
| `disable_ssl_cert_verification` | `bool`                                                                          | `False`                                                                 |
| `disable_at_in_nickname`        | `bool`                                                                          | `False`                                                                 |
| `use_hermes`                    | `bool`                                                                          | `False`                                                                 |
| `client_session_config`| `ClientSessionConfig`| `ClientSessionConfig()`|
| `logger_settings`               | `LoggerSettings`                                                                | (see [here](#logger_settings))                                          |
| `streamer_settings`             | `StreamerSettings`                                                              | (see [here](#streamer_settings))                                        |
| `gql`                           | `AttemptStrategy` or `None`                                               | `GQLFactory`                                                            |
| `weekly_rewards`                | `BasicConfiguration` or `False` or `None`             | `None`                                   |
| `watch_streak_recovery`| `Basicconfiguration` or `False` or `None`| `None`|
| `event_manager`| `EventManagerConfiguration` or `True` or `None`| `True`      |
| `handlers`               | `list[EventHandler or EventHandlerFactory]` or None| `None`|
| `factories`| `Factories` or `None`                                                   | `None`|


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

This can be set to one of a `StreamerSelector`, a `list[StreamerSelector]` a `list[Priority]`, or a single `Priority`.
The value technically defaults to `None` but this results in the miner using a priority of
`[watch_session(), watch_streak(), weekly_rewards_selector(), drops(), order()]`.

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
- `WATCH_SESSION`: This prioritises streams that were previously being watched but haven't yet received a `WATCH`
  message. This is useful to avoid wasting minutes of watch time for a current stream when a new stream comes online, as
  Twitch may drop those minutes if you swap to another stream.
- `WEEKLY_REWARDS`: This prioritises streams that have Weekly Rewards enabled, have yet to make progress this week, and 
  have yet to make progress today.
  
#### Convenience Functions

If you want a little more customisation, but without having to write your own code, you can use one of the convenience
functions defined in `StreamerSelector.py`. These functions produce a `StreamerSelector` so they can be put together in
a list (as in the default for `priority`). Each function optionally takes a `sorting` which can be used to sort matching
Streamers, with subsequent sorting functions breaking ties in earlier ones, from left to right. This enables you to do
things like `subscribed([order_points_ascending])` which selects subscribed streamers in points ascending order rather
than in the run file order. Most of these functions work the same as their `Priority` counterparts, with the exception
of `watch_streak()` which defaults to sort by `sort_oldest_stream`.

The selector functions are:

 - `order()`
 - `watch_streak()`
 - `drops()`
 - `subscribed()`
 - `points_ascending()`
 - `points_descending()`
 - `watch_session()`
 - `weekly_rewards()`

The `sorting` functions are:

 - `sort_points_ascending:` which sorts streamers by the number of channel points ascending
 - `sort_points_descending` which sorts streamers by the number of channel points descending
 - `sort_oldest_stream` which sorts streamers by the stream start time oldest first
 - `sort_newset_stream` which sorts streamers by the stream start time newest first
 - `sort_multiplier_ascending` which sorts streamers by your points multiplier ascending
 - `sort_multipler_descending` which sorts streamers by your points multiplier descending
 - `sort_subscription_ends_at_ascending` which sorts by your subscription end time ascending
 - `sort_subscription_ends_at_descending` which sorts by your subscription end time descending

There's also `group` which allows you to specify that a given selector should only apply to a subset of Streamers:

```python
priority=[
    group(
        streamers=["streamer-1", "streamer-2", "streamer-3"],
        selector=order(),
    ),
    group(
        streamers=["streamer-4", "streamer-5", "streamer-6"],
        selector=watch_streak(),
    ),
    order(),
]
```

This will first select "streamer-1", "streamer-2", then "streamer-3" in the order defined in your run file. Then it will
consider "streamer-4", "streamer-5", and "streamer-6" if they're missing their watch streaks. Finally, it will look at
all remaining streamers in the oder defined in your run file.

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


##### `FilterSortSelector`

This selector takes a `reason` which is an object used for debug purposes, it should represent the reason streamers are
being selected by this selector (e.g. `Priority.ORDER`). It also takes a `_filter` function that should return `True` if
a Streamer could be selected. And it takes a `sorting` which is an optional list of functions that produce a "sort key"
for selectable streamers. The `sorting` functions should comply with the `key` argument
described [here](https://docs.python.org/3/library/functions.html#sorted). The convenience functions are actually
implemented by this. If `sorting` isn't provided, the streamers will be returned in the order they were provided to
`select`. For example:

```python
FilterSortSelector(
    reason="Has Tag 'DropsEnabled'",
    _filter=lambda s: "DropsEnabled" in s.stream.tags,
    sorting=[sort_oldest_stream, sort_points_ascending],
)
```

This selects Streamers with a Stream with the `DropsEnabled` tag, sorted by stream start date from earliest to newest,
then tie-breaking by the number of channel points ascending.

The [convenience functions](#convenience-functions) are actually implemented in terms of this selector:

```python
def order(sorting: list[GetSortKey] | None = None):
    return FilterSortSelector(
        reason=Priority.ORDER, _filter=match_order, sorting=sorting
    )
```

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

### `client_session_config`

This allows you to override parts of the client session object, which is used to make requests to Twitch's servers. This
allows, among other things, you to set the connection pool max size, when set to a high enough value you can avoid
connections not being cached (and an annoying warning log from a 3rd party library), which speeds up requests and
reduces CPU usage. There are other values you can change here (the client id, user agent, etc...) but I would avoid
changing those unless you have some specific requirement. E.g.:

```python
client_session=ClientSessionConfig(
  maxsize=100,
)
```

This sets the miner to use a single Session with a max HTTP(S) connection pool size of 100. This value is difficult for
the miner to automatically assign due to the concurrent nature of the application. However, as a general guide, the
value should increase linearly with the number of Streamers in your run file.

The default is:

```python
client_session_config=ClientSessionConfig(
    client_id=None,
    user_agent=None,
    device_id=None,
    session_id=None,
    version=None,
    maxsize=20,
    connections=10,
)
```

`client_id` is the id of the Twitch Client we use when making requests.
`user_agent` is the HTTP `User-Agent` Header we use when making requests.
`device_id` is a unique value that identifies your device to Twitch, this is randomly generated when the miner starts.
`session_id` is a unique value that identifies your request session to Twitch, this is also randomly generated when the
miner starts.
`version` is the Twitch Client Version we use when making request, this value is updated automatically over time.
`maxsize` is the max connection pool size, it's the number of connections to keep alive simultaneously.
`connections` is the number of connection pools to cache.

### `logger_settings`

See [here](/docs/guides/logger-settings.md) for more information.

### `streamer_settings`

See [here](/docs/guides/streamer-settings.md) for more information.

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

### `weekly_rewards`

Defines how the miner attempts to make progress on [Weekly Rewards](https://help.twitch.tv/s/article/weekly-rewards).
The default configuration, which you can use by simply not providing a value for `weekly_rewards` or setting it to 
`None`, causes the miner to attempt to make progress on up to 2 Streamers at a time. It does this by attempting to watch
first up to 30 seconds of a Clip from that Streamer. Then, if that doesn't do it (most of the time watching a Clip will
make progress) it'll watch up to 8 minutes of a VOD. If both of those fail it'll put that Streamer on cooldown for an
hour, meanwhile other Streamers can be attempted. All of these values can be changed by setting them in the
`WeeklyRewardsProgressor.BasicConfiguration`:

```python
weekly_rewards=WeeklyRewardsProgressor.BasicConfiguration(
  max_concurrent=2,
  max_clip_watch_seconds=30,
  max_vod_watch_seconds=8*60,
  interval_seconds=20,
  max_failures_per_streamer=1,
  failure_cooldown_seconds=60*60,
)
```

You can also just specify what you want to override:

```python
weekly_rewards=WeeklyRewardsProgressor.BasicConfiguration(
  max_concurrent_watch=10,
  max_failures_per_streamer=3,
  failure_cooldown_seconds=2*60*60,
)
```

This has the same behaviour as just described except it'll attempt to watch up to 10 Streamers at once, it'll try to
progress the same Streamer up to 3 times before putting them on cooldown, and the cooldown time is 2 hours.

You may also set it to `False` which will disable automatic Weekly Rewards progression.

```python
weekly_rewards=False,
```

### `watch_streak_recovery`

This defines how the miner attempts to automatically recover Watch Streaks. Twitch allows recovery of missed streaks via
Clip or VOD watching, so the miner implements that behaviour. Because both this and [Weekly Rewards](#weekly_rewards)
work via Clip and VOD watching, the configuration format is the same for both:

```python
watch_streak_recovery=WatchStreakRecovery.BasicConfiguration(
  max_concurrent=2,
  max_clip_watch_seconds=30,
  max_vod_watch_seconds=8*60,
  interval_seconds=20,
  max_failures_per_streamer=1,
  failure_cooldown_seconds=60*60,
)
```

### `event_manager`

This defines the configuration options for the miner's Event Manager. During operation, the miner will emit various
Events. This includes things like Streamers going online/offline, prediction start and end, and drops claiming. The
Event Manager handles those Events and passes them onto the [Handlers](#handlers) (defined below).

```python
EventManagerConfiguration(
    console=False,
    queue=None,
    events=Events.all(),
)
```

This is the default configuration, provided when the value is set to `True`. Here console output is disabled by default,
we expect most users to want to use the console for logging rather than Events. The `queue` configuration is `None`
which tells us to use the default values for that. And `events` is `Events.all()` which doesn't really matter because
the console is disabled.

You may also set `console` to `True` which sets up a priority Console Handler. This is useful because it allows the
Handler to bypass the queue, Events will be output to the console almost immediately regardless of your queue settings.
Also, you may set the events you want to output to the console via `events`, as with other Handlers, this may be a union
of `Events` or a list, e.g.:

```python
Events.PREDICTIONS | Events.STREAMER_ONLINE | Events.DROP_CLAIM
# is equivalent to
[Events.PREDICTIONS, Events.STREAMER_ONLINE, Events.DROP_CLAIM]
```

You can also set `event_manager` to `None`, in this case the Event Manager is disabled and no Events will be passed to Handlers. 

### `handlers`

This is an optional list of Event Handlers that can respond to Events emitted by the miner. The common use case for this
is providing data to an Event Hook like Discord or Telegram:

> [!NOTE]
> This may seem familiar, the old log Hooks have been reimplemented as Handlers with similar syntax

```python
handlers=[
    discord("https://example.com/path?token=some_token"),
    telegram(123456789, "some_token"),
]
```

In this example, a Discord and Telegram handler have been added, which send miner Events to Discord and Telegram.

We provide these convenience functions for each of the Event Handlers: `telegram`, `discord`, `matrix`, `pushover`,
`gotify`, and `webhook`. They all have some unique parameters, however, they can all be provided the following to further
customise functionality:

| Name   | Type   | Default   | Description |
|---|---|---|---|
| `name`   | `str`  | N/A  | Used for logging errors when we're unable to send the Event data. |
| `webhook_api_url` | `str`  | N/A  | This is the URL that the Event data will be sent to.  |
| `transformer`  | `EventTransformer[dict[str, str]]` | N/A  | This allows you to completely override how Event data is transformed into web request data. |
| `events`  | `list[Events]` or `Events` or `None`  | `Events.default()` (when `None`)  | This defines the Events that this Hanlder handles.  |
| `use_json`  | `bool`  | `False`  | If True, the data will be sent as JSON, otherwise plain data will be sent.  |
| `attempt_strategy`  | `AttemptStrategy` or `None`  | `AttemptStrategy(attempt_interval_seconds=2, attempts=3)` (when `None`) | The strategy to use when making web requests, 429 (rate limit) responses will be retried automatically.  |
| `timeout`  | `float` or `tuple[float, float]` or `None` | `(5, 10)` (when `None`)  | This defines the connect and request timeouts for each web request in seconds.  |
| `post_request`  | `PostRequest` or `None`  | `requests.post` (when `None`)  | Allows defining a custom post request method, useful when testing.  |

Of these, `webhook_api_url` is most frequently required (but not always). The rest are there for more advanced users who
want specific integration behaviour.

#### `telegram`

One of the Event Handlers, allows events to be sent to Telegram
using [sendMessage](https://core.telegram.org/bots/api#sendmessage).

| Name                    | Type           | Description                                                                     |
|-------------------------|----------------|---------------------------------------------------------------------------------|
| `chat_id`               | `int`          | The unique identifier of the target chat of the username of the target channel. |
| `token`                 | `str`          | The token for your Telegram bot.                                                |
| `disable_notifciations` | `bool`         | `True` to trigger Telegram notifications without sound.                         |

Note that `webhook_api_url` is not used here as telegram has a static URL. 

#### `discord`

One of the Event Handlers, allows events to be sent to Discord using
a [Webhook](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks).

| Name         | Type            | Default                             | Description                                                                                            |
|--------------|-----------------|-------------------------------------|--------------------------------------------------------------------------------------------------------|
| `username`   | `str` or `None` | `"Twitch Channel Points Miner"`     | This is the username that shows up in Discord. Set to `None` to use the app default.                   |
| `avatar_url` | `str` or `None` | `"https://i.imgur.com/X9fEkhT.png"` | This is the image that shows up next to the username in Discord. Set to `None` to use the app default. |
| `use_embeds` | `bool`          | `True`                              | Allows sending some supported messages as Discord Embeds.                                              |

#### `webhook`

One of the Event Handlers, allows events to be sent to a generic Webhook in a set format.

| Name       | Type           | Description                                   |
|------------|----------------|-----------------------------------------------|
| `method`   | `str`          | The HTTP method to use when sending data.     |

#### `matrix`

One of the `EventHandler` types, allows events to be sent to a [Matrix](https://matrix.org/docs/chat_basics/matrix-for-im/)
server.

| Name         | Type          | Description                                            |
|--------------|---------------|--------------------------------------------------------|
| `username`   | `str`         | Your Matrix username.                                  |
| `password`   | `str`         | Your Matrix password.                                  |
| `homeserver` | `str`         | The URL of the Matrix server (e.g. `"matrix.org"`      |
| `room_id`    | `str`         | The id of the room to which you want to send `Events`. |

Note that `webhook_api_url` is not used here as Matrix URLs have a set format.

#### `pushover`

One of the Event Handlers, allows events to be sent to a [Pushover](https://pushover.net/api) server.

| Name       | Type            | Description                                                                                  |
|------------|-----------------|----------------------------------------------------------------------------------------------|
| `userkey`  | `str`           | [Log in](https://pushover.net/) and the user token is on the main page.                      |
| `token`    | `str`           | Create a application on the website, and use the token shown in your application.            |
| `priority` | `int`           | The [priority](https://pushover.net/api#priority) of the messages.                           |
| `sound`    | `str`           | The [sound](https://pushover.net/api#sounds) to use for Pushover notifications.              |
| `title`    | `str` or `None` | The message title in Pushover, defaults to `"Twitch Channel Points Miner"` if set to `None`. |

#### `gotify`

One of the Event Handlers, allows events to be sent to a [Gotify](https://gotify.net/docs/index) server.

| Name       | Type          | Description                                                                                                       |
|------------|---------------|-------------------------------------------------------------------------------------------------------------------|
| `priority` | `int`         | The priority of the message.                                                                                      |

#### Custom Hooks

> [!IMPORTANT]
> The following is intended for advanced users only.

You may also implement your own Handler, this can either implement `EventHandler` or `EventHandlerFactory`:

```python
class CustomEventHandler(EventHandler):
    def handles(self) -> Events:
        return Events.STREAM_UP | Events.STREAM_DOWN
    
    def handle(self, event: Event):
        print(event)
```

In this example, we're just printing and `STREAM_UP/DOWN` Events, but you could also implement this to integrate with a
new 3rd party API.

```python
class CustomDBHandler(EventHandler):
    def __init__(self, db_service, transformer):
        self.service = db_service
    
    def handles(self):
        return Events.all()
    
    def handle(self, event: Event):
        self.service.log_event(self.transformer.transform(event))

# assume we've defined a custom database service

def custom_db_handler(db_service) -> EventHandlerFactory:
    # Do some setup with the arguments
    db_service.connect()
    db_service.authenticate()
    ...

    def factory(        
        logger_settings: LoggerSettings,
        background_tasks: list[Thread],
        default_transformer: EventTransformer[str],
        account_name: str,
    ) -> EventHandler:
        return CustomDBHandler(
            db_Service,
            default_transformer
        )
    return factory
```

In this example, we want access to the miner's default event transformer so we've created a factory that will be
provided with it during setup. A custom database service exposes a `log_event` method which allows storing the Event
text in a database table somewhere. We then provide a factory function that takes the service and the transformer and
passes them to a new `CustomDBHandler` object.

### `factories`

> [!IMPORTANT]
> This is intended for advanced users only. The vast majority of users should never need to use this.

This is a dependency injection container for the miner application, it controls setup for most of the miner's functional
units. It can be constructed as such:

```python
factories=Factories()
```
Which will produce a `Factories` containing all default values. You can also provide a custom factory for each argument:
|Argument Name   | Type   |
|-----------------------|-----------------------------|
| `streamer_selector`   | `StreamerSelectorFactory`   |
| `clip_vod_watcher_runner` | `SlottedTaskRunnerFactory`|  
| `gql`  | `GQLFactory`  |
| `ws_pool`  | `WebSocketPoolFactory`  |
| `weekly_rewards`  | `WeeklyRewardsProgressorFactory`  |
| `watch_streak_recovery`  | `WatchStreakRecoveryFactory`  |
| `default_event_transformer`| `EventTransformerFactory[str]`|
| `event_manager_runner`| `SlottedTaskRunnerFactory`|
| `event_manager`| `EventManagerFactory`|
| `chat_manager`| `ChatManagerFactory`|

#### `streamer_selector`

The miner functionality provided by this factory is the root `StreamerSelector`, this controls which Streams are watched.
This is a `StreamerSelectorFactory` which takes a streamer selector configuration and produces a root streamer selector.
The default behaviour is to take the list of provided configuration and convert it into the related Selector, for example:

```python
factory.create(Priority.DROPS)
# produces
PrioritySelector([Priority.DROPS])
```
```python
factory.create([watch_streak(), subscribed(), order()])
# produces
NestedSelector(
    [
        FilterSortSelector(
            reason=Priority.WATCH_SESSION,
            _filter=in_watch_session,
        ),
        FilterSortSelector(
            reason=Priority.SUBSCRIBED,
            _filter=is_subscribed,
            sorting=[sort_multiplier_descending],
        ),
        FilterSortSelector(
            reason=Priority.ORDER,
            _filter=match_order,
        ),
        
    ]
)
```
The end result is a selector that works according to the configuration rules defined [above](#priority).


#### `client_session`

This produces a `ClientSession` for use in the application. See [here](#client_session_config) for more information. It
should be a function that takes the config's `username`, `password`, and `client_session_config` and produces a
`ClientSession`.

#### `clip_vod_watcher_runner`

Long-running processes, like Clip/VOD watchers, need a way to ensure they complete in a given amount of time and that
all exit conditions are properly handled. We implement this using `SlottedTaskRunner` which can process tasks
concurrently in a given number of slots.

The Weekly Rewards and Watch Streak miner features require a runner to be able to perform their functions. So their
factories rely on this one to produce the underlying runners.

The default runner creates a new `SlottedTaskRunnerThread` which runs tasks in a background Thread. At most 3 tasks can
be run simultaneously with a 20-second interval between checking tasks.

#### `gql`

This produces the Twitch GQL (Graph Query Language) integration instance, required for making requests to their GQL API.
It can take a `Parser` which handles parsing the API responses from JSON and transforming them into usable, well-defined
Python objects.
It can also take a `PostRequest` function, which handles doing the actual requests. This is most useful for testing when
we don't want to communicate with the actual Twitch API.
For example:

```python
gql=GQLFactory()
```

Produces the default factory which creates an integration with a default parser and API endpoint.

```python
gql=GQLFactory(
    parser=CustomParser(),
    post_request=custom_post_request,
)
```

You might implement a `CustomParser` that implements JSON parsing differently, perhaps expanding the error states checked.
You might also implement a `custom_post_request` that implements making the API call differently, perhaps with custom retry rules.

```python
gql=CustomGQLFactory()
```

You might implement a `CustomGQLFactory` that implements the `create` method to produce an integration that works in a
different way.

#### `ws_pool`

This provides the miner with a WebSocket Pool which manages its connections to the chosen Twitch WebSocket API. Its
`create` method takes the `use_hermes` configuration value and creates a Pool, one of either the legacy PubSub Pool
or the newer Hermes pool. As with the other factories, you can implement this to provide greater control over the
relevant features.

#### `weekly_rewards`

This provides the miner with a `WeeklyRewardsProgressor` for use when the user wants to automatically progress Weekly
Rewards via Clip and VOD watching. This defines a `create` method that the miner uses to produce a
`WeeklyRewardsProgressor` instance. By default, it'll use a `BasicWeeklyRewardsProgressorFactory` which produces a
`BasicWeeklyRewardsProgressor`. This is useful if you have a different method for progressing weekly rewards, an
optimisation, or if you need better hooks into the process. For example, this is how the default behaviour could be
defined:

```python
weekly_rewards=WeeklyRewards.BasicWeeklyRewardsProgressorFactory()
```

This creates a progressor with a default configuration, and a task runner produced by the given runner factory.

#### `watch_streak_recovery`

This provides the miner with a `WatchStreakRecovery` for use when the user wants to automatically recover missing Watch
Streaks via Clip and VOD watching. This is very similar to the `weekly_rewards` object, under the hood they're both
implemented in a similar way, mainly because the Twitch requirements for both are nearly identical.

```python
watch_streak_recovery=WatchStreakRecovery.BasicWatchStreakRecoveryFactory()
```

#### `default_event_transformer`

This is used by the Events system to produce human-readable strings, similar to the ones you see in the logs. This is
for consumption by Event Hooks (Discord, Telegram, etc...).

```python
default_event_transformer=DefaultEventTransformerFactory()
```

This produces a factory that creates a transformer that takes into account various settings from your `LoggerSettings`
configuration. The format of messages will be:

```text
{emoji} {event name}
{optional "Account": account_name}
{message}
```
where

`emoji` is an emoji representative of the event or the miner's default emoji.

`optional "Account: " account_name` is the user's account name prefixed by "Account: " or nothing

`message` is a human-readable string representation of the event.

The emojis are decided by `EmojiTransformer`. The account name is decided by the value of `LoggerSettings.username`. The
message is provided by `TranslatorTransformer`, which relies on the `LoggerSettings.translator` to produce text in the
user's locale (`en` by default).

#### `event_manager_runner`

This is the task runner that processes background tasks for the Event Manager. By default, the runner uses the provided
event manager config's `max_concurrent` and `runner_loop_interval_seconds` to decide how many and how often to process
events.

#### `event_manager`

This produces the Event Manager for the miner, which is used to process events emitted by the miner. By default, we use
`DefaultEventManagerFactory` which uses the user's configuration to produce a Manager:

```python
event_manager=DefaultEventManagerFactory()
```

If no configuration is provided, the Event Manager will be disabled (the miner will produce no Events).
If the configuration is just `True`, the default configuration will be used. This is:

```python
EventManagerConfiguration(
    console=False,
    queue=None,
    events=Events.all(),
)
```

Additionally, when `queue` here is `None`, we use the default queue configuration. This is:

```python
QueueConfiguration(
    task_timeout_seconds=60,
    loop_sleep_seconds=0.5,
    max_concurrent=10,
    runner_loop_interval_seconds=0.5,
)
```

This creates a `QueueManager` that creates background tasks for emitted Events, one for each subscribed Handler. The
tasks can run for up to 60 seconds before the manager considers them failed. It can process up to 10 tasks simultaneously.

`events` is only used if `console` is enabled. It determines which Events will be output to the console.

#### `chat_manager`

This produces the `ChatManager` that the miner uses when connecting to IRC. By default, this manager will periodically
check each Streamer's online status and use their `ChatPresence` to determine whether IRC should be connected. A custom
chat manager could be provided here to connect to IRC or in a custom way or otherwise provide a unique way to manage the
connections.

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
