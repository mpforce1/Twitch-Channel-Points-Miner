from typing import Callable
from unittest.mock import MagicMock

import pytest

from TwitchChannelPointsMiner.classes.Settings import Settings
from TwitchChannelPointsMiner.classes.Translator import (
    Translator,
    singular_when_1,
    singular_when_0_or_1,
)
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer
from TwitchChannelPointsMiner.classes.translator.Model import (
    Pluralizable,
    Requires,
    Translation,
)
from TwitchChannelPointsMiner.logger import LoggerSettings

Settings.logger = LoggerSettings(less=True, anonymiser=None)


def test_singular_when_1():
    rule = singular_when_1
    assert rule.form(0) == "plural"
    assert rule.form(1) == "singular"
    for count in range(2, 20):
        assert rule.form(count) == "plural"


def test_singular_when_0_or_1():
    rule = singular_when_0_or_1
    assert rule.form(0) == "singular"
    assert rule.form(1) == "singular"
    for count in range(2, 20):
        assert rule.form(count) == "plural"


class TestTranslator:
    @pytest.fixture
    def translator(self):
        return Translator("locales")

    @pytest.mark.parametrize("locale", ["en"])
    def test_set_locale(self, translator, locale):
        translator.set_locale(locale)
        assert translator.default_locale == locale

    @pytest.mark.parametrize("locale", ["ab", "cd", "ef", ""])
    def test_set_locale_fail(self, translator, locale):
        with pytest.raises(ValueError):
            translator.set_locale(locale)

    def test_get_translation(self, translator):
        english_translation = MagicMock(spec=Translation)
        french_translation = MagicMock(spec=Translation)
        translator.translations = {"en": english_translation, "fr": french_translation}
        assert translator.get_translation() == english_translation
        assert translator.get_translation("fr") == french_translation
        with pytest.raises(KeyError):
            translator.get_translation("de")

    streamer_a = Streamer("streamera", "123456")
    test_translate_data = [
        (
            lambda t: t.stream_up,
            {"streamer": streamer_a},
            None,
            "streamera (0 points): Stream is Up!",
        ),
        (
            lambda t: t.stream_down,
            {"streamer": streamer_a},
            "en",
            "streamera (0 points): Stream is Down!",
        ),
    ]

    @pytest.mark.parametrize("get_value,arg,locale,expected", test_translate_data)
    def test_translate[TArg](
        self,
        translator,
        get_value: Callable[[Translation], Requires],
        arg: TArg,
        locale: str | None,
        expected: str,
    ):

        # Use simpler streamer representation
        Settings.logger = LoggerSettings(less=True)
        assert translator.translate(get_value, arg, locale) == expected

    def test_translate_fail(self, translator: Translator):
        with pytest.raises(KeyError):
            # This is technically valid syntax that generates a warning, however it also raises a KeyError at runtime
            translator.translate(
                lambda t: t.stream_up, locale=None, arg={"stream": "wrong"}
            )

    test_translate_plural_data = [
        (
            lambda t: t.stream_view_count,
            {"streamer": streamer_a, "count": 1},
            None,
            "streamera (0 points) has 1 viewer",
        ),
        (
            lambda t: t.stream_view_count,
            {"streamer": streamer_a, "count": 100},
            None,
            "streamera (0 points) has 100 viewers",
        ),
    ]

    @pytest.mark.parametrize(
        "get_pluralizable,arg,locale,expected", test_translate_plural_data
    )
    def test_translate_plural[TArg](
        self,
        translator,
        get_pluralizable: Callable[[Translation], Pluralizable[TArg]],
        arg: TArg,
        locale: str | None,
        expected: str,
    ):
        Settings.logger = LoggerSettings(less=True, anonymiser=None)
        assert translator.translate_plural(get_pluralizable, arg, locale) == expected

    def test_translate_plural_fail(self, translator: Translator):
        with pytest.raises(KeyError):
            # In this case we're both missing "count" and we've got an extra invalid key-value pair
            translator.translate_plural(
                lambda t: t.stream_view_count, {"missing": "count"}
            )

    def test_translate_list(self, translator: Translator):
        assert (
            translator.translate_list(lambda t: t.predictions.outcome_simple, []) == ""
        )
        assert (
            translator.translate_list(
                lambda t: t.predictions.outcome_simple, [{"title": "outcome 1"}]
            )
            == "【outcome 1】"
        )
        assert (
            translator.translate_list(
                lambda t: t.predictions.outcome_simple,
                [{"title": "outcome 1"}, {"title": "outcome 2"}],
            )
            == "【outcome 1】 and 【outcome 2】"
        )
        assert (
            translator.translate_list(
                lambda t: t.predictions.outcome_simple,
                [
                    {"title": "outcome 1"},
                    {"title": "outcome 2"},
                    {"title": "outcome 3"},
                ],
            )
            == "【outcome 1】, 【outcome 2】, and 【outcome 3】"
        )

    @pytest.mark.parametrize(
        "streamer,expected", [(streamer_a, " for streamera (0 points)"), (None, "")]
    )
    def test_translate_optional(
        self, translator: Translator, streamer: Streamer | None, expected: str
    ):
        assert (
            translator.translate_optional(
                lambda t: t.drops.with_streamer,
                streamer,
                lambda s: {"streamer": s},
            )
            == expected
        )

