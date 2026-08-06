import logging
import os
import platform
import queue
import sys
from datetime import datetime
from logging import LogRecord
from logging.handlers import QueueHandler, QueueListener, TimedRotatingFileHandler
from pathlib import Path

import emoji
import pytz
from colorama import Fore, init

from TwitchChannelPointsMiner.classes.Anonymiser import Anonymiser, ConsistentAnonymiser, Deanonymiser
from TwitchChannelPointsMiner.classes.Discord import Discord
from TwitchChannelPointsMiner.classes.EventHook import EventHook
from TwitchChannelPointsMiner.classes.Gotify import Gotify
from TwitchChannelPointsMiner.classes.Matrix import Matrix
from TwitchChannelPointsMiner.classes.Pushover import Pushover
from TwitchChannelPointsMiner.classes.Settings import Events
from TwitchChannelPointsMiner.classes.Telegram import Telegram
from TwitchChannelPointsMiner.classes.Webhook import Webhook
from TwitchChannelPointsMiner.utils import remove_emoji


# Fore: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET.
class ColorPalette(object):
    def __init__(self, **kwargs):
        # Init with default values RESET for all and GREEN and RED only for WIN and LOSE bet
        # Then set args from kwargs
        for k in Events:
            if k.name is not None:
                setattr(self, k.name, Fore.RESET)
        setattr(self, "BET_WIN", Fore.GREEN)
        setattr(self, "BET_LOSE", Fore.RED)

        for k in kwargs:
            if k.upper() in dir(self) and getattr(self, k.upper()) is not None:
                if kwargs[k] in [
                    Fore.BLACK,
                    Fore.RED,
                    Fore.GREEN,
                    Fore.YELLOW,
                    Fore.BLUE,
                    Fore.MAGENTA,
                    Fore.CYAN,
                    Fore.WHITE,
                    Fore.RESET,
                ]:
                    setattr(self, k.upper(), kwargs[k])
                elif kwargs[k].upper() in [
                    "BLACK",
                    "RED",
                    "GREEN",
                    "YELLOW",
                    "BLUE",
                    "MAGENTA",
                    "CYAN",
                    "WHITE",
                    "RESET",
                ]:
                    setattr(self, k.upper(), getattr(Fore, kwargs[k].upper()))


    def get(self, key):
        color = getattr(self, str(key)) if str(key) in dir(self) else None
        return Fore.RESET if color is None else color


class LoggerSettings:
    __slots__ = [
        "save",
        "less",
        "console_enabled",
        "console_level",
        "console_username",
        "time_zone",
        "file_level",
        "emoji",
        "colored",
        "color_palette",
        "auto_clear",
        "telegram",
        "discord",
        "webhook",
        "matrix",
        "pushover",
        "gotify",
        "hooks",
        "username",
        "redact_secrets",
        "anonymiser",
    ]

    def __init__(
        self,
        save: bool = True,
        less: bool = False,
        console_enabled: bool = True,
        console_level: int = logging.INFO,
        console_username: bool = False,
        time_zone: str | None = None,
        file_level: int = logging.DEBUG,
        emoji: bool = platform.system() != "Windows",
        colored: bool = False,
        color_palette: ColorPalette = ColorPalette(),
        auto_clear: bool = True,
        telegram: Telegram | None = None,
        discord: Discord | None = None,
        webhook: Webhook | None = None,
        matrix: Matrix | None = None,
        pushover: Pushover | None = None,
        gotify: Gotify | None = None,
        hooks: list[EventHook] | None = None,
        username: str | None = None,
        redact_secrets: bool = False,
        anonymiser: Anonymiser | bool | None = None
    ):
        self.save = save
        self.less = less
        self.console_enabled = console_enabled
        self.console_level = console_level
        self.console_username = console_username
        self.time_zone = time_zone
        self.file_level = file_level
        self.emoji = emoji
        self.colored = colored
        self.color_palette = color_palette
        self.auto_clear = auto_clear
        self.telegram = telegram
        self.discord = discord
        self.webhook = webhook
        self.matrix = matrix
        self.pushover = pushover
        self.gotify = gotify
        self.hooks = hooks if hooks is not None else []
        named_hooks: list[EventHook | None] = [self.telegram, self.discord, self.webhook, self.matrix, self.pushover,
                                               self.gotify]
        self.hooks.extend(hook for hook in named_hooks if hook is not None)
        self.username = username
        self.redact_secrets = redact_secrets
        if anonymiser is None or anonymiser is False:
            self.anonymiser: Anonymiser = Deanonymiser()
        elif anonymiser is True:
            self.anonymiser: Anonymiser = ConsistentAnonymiser()
        else:
            self.anonymiser: Anonymiser = anonymiser


class ExceptionFormatter(logging.Formatter):
    """Formatter that delegates formatting Exceptions to the Settings' Anonymiser."""
    def __init__(self, settings: LoggerSettings):
        self.settings = settings
        super().__init__()

    def formatException(self, ei):
        return self.settings.anonymiser.format_exception(ei)


class FileFormatter(logging.Formatter):
    def __init__(self, *, fmt, settings: LoggerSettings, datefmt=None):
        self.settings = settings
        self.timezone = None
        if settings.time_zone:
            try:
                self.timezone = pytz.timezone(settings.time_zone)
                logging.info(f"File logger time zone set to: {self.timezone}")
            except pytz.UnknownTimeZoneError:
                logging.error(
                    f"File logger: invalid time zone: {settings.time_zone}"
                )
        logging.Formatter.__init__(self, fmt=fmt, datefmt=datefmt)

    def formatTime(self, record, datefmt=None):
        if self.timezone:
            dt = datetime.fromtimestamp(record.created, self.timezone)
        else:
            dt = datetime.fromtimestamp(record.created)
        return dt.strftime(datefmt or self.default_time_format)


class GlobalFormatter(logging.Formatter):
    def __init__(self, *, fmt, settings: LoggerSettings, datefmt=None):
        self.settings = settings
        self.timezone = None
        if settings.time_zone:
            try:
                self.timezone = pytz.timezone(settings.time_zone)
                logging.info(
                    f"Console logger time zone set to: {self.timezone}"
                )
            except pytz.UnknownTimeZoneError:
                logging.error(
                    f"Console logger: invalid time zone: {settings.time_zone}"
                )
        logging.Formatter.__init__(self, fmt=fmt, datefmt=datefmt)

    def formatTime(self, record, datefmt=None):
        if self.timezone:
            dt = datetime.fromtimestamp(record.created, self.timezone)
        else:
            dt = datetime.fromtimestamp(record.created)
        return dt.strftime(datefmt or self.default_time_format)

    def format(self, record):
        record.emoji_is_present = (
            record.emoji_is_present if hasattr(
                record, "emoji_is_present"
            ) else False
        )
        if (
                hasattr(record, "emoji")
                and self.settings.emoji is True
                and record.emoji_is_present is False
        ):
            record.msg = emoji.emojize(
                f"{record.emoji}  {record.msg.strip()}", language="alias"
            )
            record.emoji_is_present = True

        if self.settings.emoji is False:
            if "\u2192" in record.msg:
                record.msg = record.msg.replace("\u2192", "-->")

            # With the update of Stream class, the Stream Title may contain emoji
            # Full remove using a method from utils.
            record.msg = remove_emoji(record.msg)

        if self.settings.username is not None:
            record.msg = f"{self.settings.username} {record.msg}"

        if hasattr(record, "event"):
            for hook in self.settings.hooks:
                hook.validate_and_send(record)

            if self.settings.colored is True:
                record.msg = (
                    f"{self.settings.color_palette.get(record.event.name)}{record.msg}"
                )
        return super().format(record)

class LimitedConsoleHandler(logging.StreamHandler):
    def emit(self, record: LogRecord) -> None:
        if hasattr(record, "force_console"):
            super().emit(record)



def configure_loggers(username, settings: LoggerSettings):
    if settings.colored is True:
        init(autoreset=True)

    # Queue handler that will handle the logger queue
    logger_queue = queue.Queue(-1)
    queue_handler = QueueHandler(logger_queue)
    queue_handler.setFormatter(ExceptionFormatter(settings=settings))
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    # Add the queue handler to the root logger
    # Send log messages to another thread through the queue
    root_logger.addHandler(queue_handler)

    global_formatter = GlobalFormatter(
        fmt=(
            "%(asctime)s - %(levelname)s - [%(funcName)s]: %(message)s"
            if settings.less is False
            else "%(asctime)s - %(message)s"
        ),
        datefmt=(
            "%d/%m/%y %H:%M:%S" if settings.less is False else "%d/%m %H:%M:%S"
        ),
        settings=settings,
    )

    handlers = []

    if settings.console_enabled:
        # Adding a username to the format based on settings
        console_username = "" if settings.console_username is False else f"[{username}] "
        settings.username = console_username
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(settings.console_level)
        console_handler.setFormatter(global_formatter)
        handlers.append(console_handler)
    else:
        # We still want top level messages to log to the console
        console_handler = LimitedConsoleHandler(sys.stdout)
        console_handler.setLevel(settings.console_level)
        console_handler.setFormatter(global_formatter)
        handlers.append(console_handler)

    logs_file = None
    if settings.save is True:
        logs_path = os.path.join(Path().absolute(), "logs")
        Path(logs_path).mkdir(parents=True, exist_ok=True)
        if settings.auto_clear is True:
            logs_file = os.path.join(
                logs_path,
                f"{username}.log",
            )
            file_handler = TimedRotatingFileHandler(
                logs_file,
                when="D",
                interval=1,
                backupCount=7,
                encoding="utf-8",
                delay=False,
            )
        else:
            # Getting time zone from the global formatter
            tz = "" if global_formatter.timezone is False else global_formatter.timezone
            logs_file = os.path.join(
                logs_path,
                f"{username}.{datetime.now(tz).strftime('%Y%m%d-%H%M%S')}.log",
            )
            file_handler = logging.FileHandler(logs_file, "w", "utf-8")

        file_handler.setFormatter(
            FileFormatter(
                fmt="%(asctime)s - %(levelname)s - %(name)s - [%(funcName)s]: %(message)s",
                datefmt="%d/%m/%y %H:%M:%S",
                settings=settings
            )
        )
        file_handler.setLevel(settings.file_level)

        handlers.append(file_handler)

    # Add logger handlers to the logger queue and start the process
    queue_listener = QueueListener(
        logger_queue, *handlers, respect_handler_level=True
    )
    queue_listener.start()
    return logs_file, queue_listener
