# `logger_settings`

This allows you to configure logging options. See [here](logs.md) for some examples.

| Name               | Type                             | Default             |
|--------------------|----------------------------------|---------------------|
| `save`             | `bool`                           | `True`              |
| `console_level`    | `int`                            | `logging.INFO`      |
| `console_username` | `bool`                           | `False`             |
| `console_truncate`| `int` or `"console"` or `False`| `False`|
| `auto_clear`       | `bool`                           | `True`              |
| `time_zone`        | `str`                            | `""` (empty string)|
| `file_level`       | `int`                            | `logging.DEBUG`     |
| `emoji`            | `bool`                           | `True`              |
| `less`             | `bool`                           | `False`             |
| `colored`          | `bool`                           | `True`              |
| `color_palette`    | `ColorPalette`                   | `None`              |
| `drops_progress` | `bool`| `True`|
| `redact_secrets`   | `bool`                           | `False`             |
| `anonymiser`       | `Anonymiser` or `bool` or `None` | `None`              |
| `username`| `str` or `None`| `None`|
| `translator`| `Translator` or `None`| `None`|
| `locale`          | `str` or `None`               | `None`|


## `save`

If set to `True` the miner will save logs to a file in the `logs` directory. If `False` then logs will not be saved.

## `console_level`

Set this to change the [log level](https://docs.python.org/3/library/logging.html#logging-levels) the miner will output
to the console. The default is `INFO` which means all logs from `ERROR` to `INFO` will be logged, while `DEBUG` logs
will be ignored.

As another example, you can set this to `ERROR` to only see `ERROR` logs, ignoring `DEBUG`, `INFO`, and `WARNING` logs.

You'll see `NOTSET` and `CRITIAL` in the `logging` documentation but the miner doesn't use those.

## `console_username`

Adds a username to the beginning of every console log line if `True`. Also adds it any configured `EventHooks`
(Telegram, Discord, etc). Useful when you have several accounts.

## `console_truncate`

If set to something other than `None`, when formatting logs for the console, the length of the log message will be
truncated based on the given value:

- `None`, in this case this setting has no effect, log messages will not be modified.
- `int`, in this case the message will be at most the given number of characters long. For example, if set to `10` a
  message will be at most 10 characters.
- `"console"`, in this case the message will be truncated to the width of the console, ensuring that all logs fit in a
  single line.

## `auto_clear`

Creates a file rotation handler with an interval of 1 day and backup count of 7 if `True` (default). This means the
miner will maintain 7 log files going back the last 7 days, after a day of logs the miner will:

1. Rename the current log file, appending the current date (formatted like `[username].log.[yyyy-mm-dd]`).
2. Potentially delete the oldest log file if more than 7 would exist.
3. Create a new log file and begin writing logs to that.

## `time_zone`

Sets a specific time zone for console and file loggers.
Use [tz database](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) names. Example: "America/Denver".

## `file_level`

Similar to [`console_level`](#console_level), set this to change
the [log level](https://docs.python.org/3/library/logging.html#logging-levels) the miner will output to the file(s).

Using `DEBUG` will result in a large file size due to the amount of `DEBUG` logs produced. If this is too large for you
please try changing this to `INFO`.  

## `emoji`

On Windows, the miner has a problem printing emoji, so you can try setting to `False` to disable emoji.

## `less`

Reduces the length of most miner logs by attempting to include only the most important information. Use this if you need
shorter logs or a smaller file size.

## `colored`

Set to `True` to enable coloured text when outputting logs to the console.

## `color_palette`

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


## `drops_progress`

Set this control whether drops progress is logged. When `True` drops progress will be logged as we get updates from
Twitch. This is usually infrequently at the start of progression, but more frequently in the last 10 mins or so. When
`False` no drops progress will be logged. E.g.:

```python
drops_progress=True, # Causes progress to be printed
```

```python
drops_progress=False, # Causes progress to not be printed
```

The logs look like:

```text
|████████  |    83.33% [50/60]: streamer1: Category: Drop name: 1/5
```

Where the first part (`|████████  |`) is a progress bar that shows you at a glance the progress made on this Drop. The
next bit (`83.33%`) is the percentage progress made on this drop, and next to that (`[50/60]`) is the actual minutes
watched progress shown out of the number of minutes required. Next we log the name of the streamer (`streamer`),
followed by the category name (`Category`), and the Drop name (`Drop name`). Finally we show the Campaign progress
(`1/5`), which is the number of the current Drop shown out of the total count of progressable Drops. In this case,
we're currently 50 out of 60 minutes into progressing "Drop name" for the "Category" category, progress is happening via
watching Streamer "streamer1". The Campaign has 5 total progressable Drops and this is the first progressable Drop in
the Campaign.

## `redact_secrets`

Set this to `True` to have secrets (passwords and authentication tokens) redacted from the logs. In particular, this
currently affects PubSub request logging.

## `anonymiser`

> [!NOTE]
> Credit to [Klaro](https://github.com/0x8fv) and their
> work [here](https://github.com/0x8fv/Twitch-Channel-Points-Miner/blob/940c98409e5821900752815cd9550ae5b750b597/TwitchChannelPointsMiner/privacy/anonymizer.go)
> for inspiring this feature!

> [!WARNING]
> While this does work for logged information the miner _**itself**_ generates, it cannot work for information
> _**received**_ from external sources like the Twitch GQL and WebSocket APIs.

Set this to `True` to automatically anonymise, to the extent possible, all identifying information in the logs. This
works for channel ids, usernames, points, WebSocket topics, and Hermes subscription ids.

By default, this is set to `False`. Setting it to `False` or `None` will cause no information to be anonymised.

*Example logs:*
```text
12/03 09:18:52 - Twitch Channel Points Miner-1.1.0 (fork by mpforce1)
12/03 09:18:52 - https://github.com/mpforce1/Twitch-Channel-Points-Miner
12/03 09:18:54 - 🌐  Analytics running on http://0.0.0.0:5000/
12/03 09:18:54 - 💣  Start session: 'a0ae3a4d-2cf8-4573-bfg1-a310a060a930'
12/03 09:18:54 - 🤓  Loading data for 17 streamers. Please wait...
12/03 09:18:56 - 😴  Streamer7 (195.37k points) is Offline!
12/03 09:18:56 - 😴  Streamer6 (757.73k points) is Offline!
12/03 09:18:56 - 😴  Streamer4 (265.12k points) is Offline!
12/03 09:18:56 - 😴  Streamer1 (517.41k points) is Offline!
12/03 09:18:56 - 🚀  Detected WATCH_STREAK for Streamer9 (989.18k points)
12/03 09:18:56 - 😴  Streamer2 (747.28k points) is Offline!
12/03 09:18:56 - 😴  Streamer10 (559.75k points) is Offline!
12/03 09:18:56 - 😴  Streamer5 (696.38k points) is Offline!
12/03 09:18:56 - 😴  Streamer8 (505.82k points) is Offline!
12/03 09:18:56 - 💬  Join IRC Chat: Streamer3
12/03 09:18:56 - 🥳  Streamer3 (157.89k points) is Online!
12/03 09:18:56 - 💬  Join IRC Chat: Streamer9
12/03 09:18:56 - 🥳  Streamer9 (989.18k points) is Online!
12/03 09:18:58 - 🚀  Detected WATCH_STREAK for Streamer16 (174.22k points)
12/03 09:18:58 - 😴  Streamer17 (320.06k points) is Offline!
12/03 09:18:58 - 😴  Streamer12 (803.47k points) is Offline!
12/03 09:18:58 - 🚀  Detected WATCH_STREAK for Streamer11 (370.13k points)
12/03 09:18:58 - 😴  Streamer13 (503.6k points) is Offline!
12/03 09:18:58 - 😴  Streamer14 (242.69k points) is Offline!
12/03 09:18:58 - 🚀  Detected WATCH_STREAK for Streamer15 (364.78k points)
12/03 09:18:58 - 💬  Join IRC Chat: Streamer11
12/03 09:18:58 - 🥳  Streamer11 (370.13k points) is Online!
12/03 09:18:59 - 💬  Join IRC Chat: Streamer15
12/03 09:18:59 - 🥳  Streamer15 (364.78k points) is Online!
12/03 09:18:59 - 💬  Join IRC Chat: Streamer16
12/03 09:18:59 - 🥳  Streamer16 (174.22k points) is Online!
12/03 09:37:21 - 🚀  +10 → Streamer9 (989.19k points) - Reason: WATCH.
12/03 09:38:12 - 🚀  +10 → Streamer3 (157.9k points) - Reason: WATCH.
12/03 09:42:21 - 🚀  +10 → Streamer9 (989.2k points) - Reason: WATCH.
12/03 09:43:12 - 🚀  +10 → Streamer3 (157.91k points) - Reason: WATCH.
12/03 09:47:22 - 🚀  +10 → Streamer9 (989.21k points) - Reason: WATCH.
12/03 09:47:22 - 🚀  +50 → Streamer9 (989.26k points) - Reason: CLAIM.
12/03 09:48:10 - 🚀  +10 → Streamer3 (157.92k points) - Reason: WATCH.
12/03 09:48:10 - 🚀  +50 → Streamer3 (157.97k points) - Reason: CLAIM.
12/03 09:52:20 - 🚀  +10 → Streamer9 (989.27k points) - Reason: WATCH.
12/03 09:53:12 - 🚀  +10 → Streamer3 (157.98k points) - Reason: WATCH.
12/03 09:57:21 - 🚀  +10 → Streamer9 (989.28k points) - Reason: WATCH.
12/03 09:58:12 - 🚀  +10 → Streamer3 (157.99k points) - Reason: WATCH.
12/03 10:02:22 - 🚀  +10 → Streamer9 (989.29k points) - Reason: WATCH.
12/03 10:02:22 - 🚀  +50 → Streamer9 (989.34k points) - Reason: CLAIM.
12/03 10:03:11 - 🚀  +10 → Streamer3 (158k points) - Reason: WATCH.
12/03 10:03:11 - 🚀  +50 → Streamer3 (158.05k points) - Reason: CLAIM.
12/03 10:04:50 - 🎭  Joining raid from Streamer15 (364.78k points) to Streamer18!
12/03 10:05:08 - 🚀  +250 → Streamer15 (365.03k points) - Reason: RAID.
12/03 10:05:26 - 💬  Leave IRC Chat: Streamer15
12/03 10:05:26 - 😴  Streamer15 (365.03k points) is Offline!
12/03 10:07:22 - 🚀  +10 → Streamer9 (989.35k points) - Reason: WATCH.
12/03 10:08:13 - 🚀  +10 → Streamer3 (158.06k points) - Reason: WATCH.
12/03 10:10:26 - 🚀  +10 → Streamer9 (989.36k points) - Reason: WATCH.
12/03 10:13:12 - 🚀  +10 → Streamer3 (158.07k points) - Reason: WATCH.
12/03 10:17:22 - 🚀  +10 → Streamer9 (989.37k points) - Reason: WATCH.
12/03 10:17:22 - 🚀  +50 → Streamer9 (989.42k points) - Reason: CLAIM.
12/03 10:18:12 - 🚀  +10 → Streamer3 (158.08k points) - Reason: WATCH.
12/03 10:18:12 - 🚀  +50 → Streamer3 (158.13k points) - Reason: CLAIM.
12/03 10:22:22 - 🚀  +10 → Streamer9 (989.43k points) - Reason: WATCH.
12/03 10:23:13 - 🚀  +10 → Streamer3 (158.14k points) - Reason: WATCH.
12/03 10:27:22 - 🚀  +10 → Streamer9 (989.44k points) - Reason: WATCH.
12/03 10:28:12 - 🚀  +10 → Streamer3 (158.15k points) - Reason: WATCH.
12/03 10:32:21 - 🚀  +10 → Streamer9 (989.45k points) - Reason: WATCH.
12/03 10:32:21 - 🚀  +50 → Streamer9 (989.5k points) - Reason: CLAIM.
12/03 10:33:13 - 🚀  +10 → Streamer3 (158.16k points) - Reason: WATCH.
12/03 10:33:13 - 🚀  +50 → Streamer3 (158.21k points) - Reason: CLAIM.
12/03 10:37:22 - 🚀  +10 → Streamer9 (989.51k points) - Reason: WATCH.
12/03 10:38:12 - 🚀  +10 → Streamer3 (158.22k points) - Reason: WATCH.
12/03 10:42:22 - 🚀  +10 → Streamer9 (989.52k points) - Reason: WATCH.
12/03 10:43:12 - 🚀  +10 → Streamer3 (158.23k points) - Reason: WATCH.
12/03 10:43:29 - CTRL+C Detected! Please wait just a moment!
12/03 10:43:29 - 💬  Leave IRC Chat: Streamer3
12/03 10:43:29 - 💬  Leave IRC Chat: Streamer9
12/03 10:43:29 - 💬  Leave IRC Chat: Streamer16
12/03 10:43:29 - 💬  Leave IRC Chat: Streamer11



12/03 10:43:38 - 🛑  Ending session: 'a0ae3a4d-2cf8-4573-bfg1-a310a060a930'
12/03 10:43:38 - 📄  Logs file: /usr/src/app/logs/Streamer19.log
12/03 10:43:38 - ⌛  Duration 1:24:46.543687
12/03 10:43:38 - 💰  Streamer3 (158.23k points), Total Points Gained: 340
                         CLAIM (4 times, 200 gained)
                         WATCH (14 times, 140 gained)
12/03 10:43:38 - 💰  Streamer9 (989.52k points), Total Points Gained: 340
                         CLAIM (4 times, 200 gained)
                         WATCH (14 times, 140 gained)
12/03 10:43:38 - 💰  Streamer15 (365.03k points), Total Points Gained: 250
                         RAID (1 times, 250 gained)
```

You can see in this example that the amount of points gained from start to end for each Streamer is consistent, along
with the streamer usernames. Even the `Logs file` path is anonymised, keep this in mind since this should actually be
in a file named with your real username.

The `ConsistentAnonymiser` and `RandomAnonymiser` can optionally specify some configuration options for each type of
anonymisation.

**`channel_ids`**

Can be set to `True` to enable anonymising channel ids, this includes your own user id (since users are also channels),
as well as streamer channel ids. In addition, some Hermes WebSocket API ids include the channel id (Twitch may phase
this out in future) so these also get anonymised. If `False` then channel ids will not be anonymised. Defaults to
`True`.

**`usernames`**

Can be set to `True` to enable anonymising streamer usernames, this includes your own username. If `False` then 
usernames will not be anonymised. Defaults to `True`.

**`channel_points`**

Can be set to `True` to enable anonymising streamer channel points. If `False` then channel points will not be
anonymised. Defaults to `True`.

**`strict`**

If this is set to `True` then all web API responses will be redacted. This is useful because we cannot guarantee that
text the miner didn't create doesn't contain data that should be anonymised. You can optionally set it to `False` to
allow logging these responses. This can be useful if it's not possible to debug an issue without checking the response
text, although it comes with more risk of leaking data that you might want anonymised.

**`base_path`**

This is the configuration option for filepath anonymisation. This is useful if you want to anonymise your local system
user's name. You can set this to `True` to enable this feature, this is all you should need to do but advanced users may
want to specify a `str` that represents the "base path" of files to be redacted. For example:

```text
If
    `base_path` = "/home/username/miner"
Then
    "/home/username/miner/module_1/module_2/some_python_file.py"
Becomes
    "[PATH REDACTED]/module_1/module_2/some_python_file.py"
```

You can see how the `username` part of the filepath has been removed.

This will apply to all paths logged as part of exception stack traces in `ERROR` logging.

### `ConsistentAnonymiser`

This is the `Anonymiser` used when `anonymiser` is set to `True`, it will generate random values for each type of
anonymised data and return the same random value each time that same data is requested. For example, say a Streamer with
username `bingo` gets logged, the anonymiser may anonymise them as `Streamer5`. Each time the username for this streamer
is logged, it will log `Streamer5`.

In addition, when logging channel points only the initial value is randomised. As that channel gains/loses points the
amount logged will reflect the change amount. For example, a channel has `500` points which gets randomised to `2000`
points. The value you'll initially see logged will be `2000`. If they then gain `50` points you'll see `2050` points
logged.

```python3
ConsistentAnonymiser(
    channel_ids=True,
    usernames=True,
    channel_points=True,
    strict=True,
    base_path=True,
    random_points_min=100,
    random_points_max=1_000_000,
    random_source=RandomSource(
        random_int=random.randint,
        random_uuid=generate_random_uuid,
    ),
)
```

`random_points_min` to `random_points_max` defines the range of possible values when generating the initial random
channel points for a Streamer. In this example, channel points will be in the range `100` to `1_000_000`.

`random_source` mostly exists for testing. It allows you to override the way randomness is generated. By default, it
uses the built-in functions [`random.randint`](https://docs.python.org/3/library/random.html#random.randint) and
[`uuid.v4`](https://docs.python.org/3/library/uuid.html#uuid.uuid4) to generate channel points and UUIDs.

### `Deanonymiser`

This is the `Anonymiser` used when `anonymiser` is set to `False`. It does not alter information. `strict` is set to
`False` for this anonymiser, but you can set it to `True` if you want that behaviour.

```python3
Deanonymiser(
    strict=False
)
```

### `RandomAnonymiser`

This anonymises information in a more random way. Unlike `ConsistentAnonymiser`, each value is randomly generated each
time it is logged. For example, a Streamer's username might be `Streamer5` the first time it's logged and `Streamer100`
the next time.

```python3
RandomAnonymiser(
    channel_ids=True,
    usernames=True,
    channel_points=True,
    strict=True,
    base_path=True,
    random_source=RandomSource(
        random_int=random.randint,
        random_uuid=generate_random_uuid,
    )
)
```

`strict` is `True` by default for this anonymiser, but you can set it to `False` if you want that behaviour.

Configuration for the `RandomSource` is the same as `ConsistentAnonymiser`.

## `username`

Set this to set a username to prepend each console log message with. For example, if your `username` is `"my-username"`,
a log might look like:

```text
my-username  🚀  +12 → Streamer(username=streamer-username, channel_id=0000000, channel_points=64230) - Reason: WATCH.
```

## `translator`

Set this to set the default `Translator` used when processing `Events` into text. Generally, you don't need to override
this unless you want to provide a custom translation method. However, here is an example:

```python
translator=Translator(
    locales_directory="./locales",
    default_locale="en",
)
```

In this case the Translator will load translation files in the `"./locales"` directory, and it will default to the
locale file called `en.json` (an English translation).

See [here](/docs/guides/translation.md) for more information on writing custom translations.

## `locale`

Set this to override the locale used by the translator, by default the `en` locale is used. if another locale is
available, you may set this value to the code for that locale.

Contributions for translations will be considered, please see [here](/docs/CONTRIBUTING.md) for more information.