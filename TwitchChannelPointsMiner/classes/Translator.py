import abc
import json
import os
from typing import Callable, Iterable, Literal, Sequence

from TwitchChannelPointsMiner.classes.translator.Model import (
    ArgCount,
    Optional,
    Pluralizable,
    Requires,
    Translation,
)
from TwitchChannelPointsMiner.classes.translator.Parser import translation_parser
from TwitchChannelPointsMiner.utils.Utils import oxford_comma_list

PluralForm = Literal["singular", "plural"]
"""The plural form of a noun, either singular or plural"""


class PluralRule(abc.ABC):
    """Tells us, based on count, what the plural form should be"""

    @abc.abstractmethod
    def form(self, count: int | float) -> PluralForm:
        pass


class SingularWhenInSet(PluralRule):
    """A noun is plural when the count is in the given set"""

    def __init__(self, singular: set[int]):
        self.singular = singular

    def form(self, count: int | float) -> PluralForm:
        return "singular" if count in self.singular else "plural"


singular_when_1 = SingularWhenInSet({1})
"""A noun is plural when the count is exactly 1"""
singular_when_0_or_1 = SingularWhenInSet({0, 1})
"""A noun is plural when the count is either 0 or 1"""


# Translator


class Translator:
    """Translates a Translation into human-readable strings"""

    def __init__(self, locales_directory: str, default_locale: str | None = None):
        self.locales_directory = locales_directory
        """The directory containing the locale translation files"""
        self.default_locale = default_locale if default_locale is not None else "en"
        """The default locale to use, begins with 'en'"""
        self.translations: dict[str, Translation] = {}
        """The loaded translations"""
        self.plural_rules: dict[str, PluralRule] = {
            "en": singular_when_1,
            "fr": singular_when_0_or_1,
        }
        """The rules for handling plural values"""
        self.list_rules: dict[str, Callable[[Sequence[str]], str]] = {
            "en": oxford_comma_list,
        }
        """The rules for handling lists of values"""
        self._load_locales()

    def _load_locales(self):
        """
        Iterates through all the files in the `locales` directory and loads them as Translations.
        """
        for filename in os.listdir(self.locales_directory):
            if filename.endswith(".json"):
                locale_name = filename.replace(".json", "")
                with open(
                    os.path.join(self.locales_directory, filename),
                    "r",
                    encoding="utf-8",
                ) as file:
                    self.translations[locale_name] = translation_parser(json.load(file))

    def set_locale(self, locale_code: str):
        """
        Sets the current default locale to the given locale code.
        :param locale_code: The code to set.
        :raises ValueError: If the locale is not loaded.
        """
        if locale_code in self.translations:
            self.default_locale = locale_code
        else:
            raise ValueError(f"Unknown locale: {locale_code}")

    def get_translation(self, locale: str | None = None):
        """
        Gets the Translation for the given locale (or the default one if `locale` is None).
        :param locale: The locale for which to get the Translation.
        :return:
        """

        return self.translations[locale if locale is not None else self.default_locale]

    def translate[TArg](
        self,
        get_value: Callable[[Translation], Requires[TArg]],
        arg: TArg,
        locale: str | None = None,
    ) -> str:
        return get_value(self.get_translation(locale)).format(arg)

    def translate_str(
        self,
        get_value: Callable[[Translation], str],
        locale: str | None = None,
    ) -> str:
        return get_value(self.get_translation(locale))

    def translate_plural[TArg: ArgCount](
        self,
        get_pluralizable: Callable[[Translation], Pluralizable[TArg]],
        arg: TArg,
        locale: str | None = None,
    ):
        rule = self.plural_rules.get(
            locale if locale is not None else self.default_locale, singular_when_1
        )
        pluralizable = get_pluralizable(self.get_translation(locale))
        if rule.form(arg["count"]) == "singular":
            value = pluralizable.singular
        else:
            value = pluralizable.plural
        return value.format(arg)

    def translate_list[TArg](
        self,
        get_value: Callable[[Translation], Requires[TArg]],
        args: Iterable[TArg],
        locale: str | None = None,
    ):
        return self.list_rules.get(
            locale if locale is not None else self.default_locale, oxford_comma_list
        )([self.translate(get_value, arg, locale) for arg in args])

    def translate_list_plural[TArg: ArgCount](
        self,
        get_value: Callable[[Translation], Pluralizable[TArg]],
        args: Iterable[TArg],
        locale: str | None = None,
    ):
        return self.list_rules.get(
            locale if locale is not None else self.default_locale, oxford_comma_list
        )([self.translate_plural(get_value, arg, locale) for arg in args])

    def translate_optional[TValue, TArgs](
        self,
        get_value: Callable[[Translation], Optional[TArgs]],
        maybe_value: TValue | None,
        get_args: Callable[[TValue], TArgs],
        locale: str | None = None,
    ):
        translation = self.get_translation(locale)
        optional = get_value(translation)
        if maybe_value is None:
            return optional.none.format()
        else:
            return optional.some.format(get_args(maybe_value))
