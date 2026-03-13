from unittest.mock import MagicMock
import pytest

from TwitchChannelPointsMiner.classes.Anonymiser import (
    Anonymiser, Deanonymiser, RandomAnonymiser, ConsistentAnonymiser,
    IncrementingIdStore, RandomSource, IdStore, UUIDStore
)
from TwitchChannelPointsMiner.classes.entities.PubsubTopic import PubsubTopic
from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer


class MockAnonymiser(Anonymiser):
    def __init__(self):
        self.mock_channel_id = MagicMock()
        self.mock_username = MagicMock()
        self.mock_channel_points = MagicMock()
        self.mock_hermes_subscription_id = MagicMock()

    def channel_id(self, channel_id: str) -> str:
        return self.mock_channel_id(channel_id)

    def username(self, username: str) -> str:
        return self.mock_username(username)

    def channel_points(self, streamer: Streamer) -> int:
        return self.mock_channel_points(streamer)

    def hermes_subscription_id(self, _id: str) -> str:
        return self.mock_hermes_subscription_id(_id)


class TestAnonymiser:
    test_topic_data = [
        ["123.456", "456"],
        [PubsubTopic("example-topic-v1", "01234"), "01234"],
        [PubsubTopic("example-topic-v1", "01234", Streamer("StreamerUsername", channel_id="56789")), "56789"],
    ]

    @pytest.mark.parametrize("topic,expected_call_id", test_topic_data)
    def test_topic(self, topic: str | PubsubTopic, expected_call_id: str):
        anonymiser = MockAnonymiser()
        anonymiser.topic(topic)
        anonymiser.mock_channel_id.assert_called_once_with(expected_call_id)


class TestDeanonymiser:
    test_streamer_name_data = [
        ["", ""],
        ["a", "a"],
        ["streamer", "streamer"],
        ["username", "username"],
    ]

    @pytest.mark.parametrize("username,expected_name", test_streamer_name_data)
    def test_streamer_name(self, username: str, expected_name: str) -> None:
        anonymiser = Deanonymiser()
        assert anonymiser.streamer_username(Streamer(username)) == expected_name

    test_channel_points_data = [
        [0, 0],
        [1, 1],
        [10, 10],
        [1_000_000, 1_000_000],
        [3458901, 3458901],
    ]

    @pytest.mark.parametrize("points,expected_points", test_channel_points_data)
    def test_channel_points(self, points: int, expected_points: int) -> None:
        anonymiser = Deanonymiser()
        assert anonymiser.channel_points(Streamer("test", channel_points=points)) == expected_points


class TestRandomAnonymiser:
    def test_streamer_name(self):
        names = ["Streamer 5", "Streamer 1", "Streamer 35", "Streamer 82", "Streamer 4"]
        random_int = MagicMock()
        random_int.side_effect = [5, 1, 35, 82, 4]
        anonymiser = RandomAnonymiser(RandomSource(random_int))

        for name in names:
            assert anonymiser.streamer_username(Streamer(name)) == name

    def test_channel_points(self):
        points = [0, 123, 43_809, 233, 999]
        random_int = MagicMock()
        random_int.side_effect = points
        anonymiser = RandomAnonymiser(RandomSource(random_int))

        for point in points:
            assert anonymiser.channel_points(Streamer("test")) == point


class MockIdStore(IdStore[str]):
    def __init__(self):
        super().__init__()
        self.mock_next_id = MagicMock()

    def _next_id(self) -> str:
        return self.mock_next_id()


class TestIdStore:
    def test_id(self):
        id_store = MockIdStore()
        id_store.id("test key")
        id_store.mock_next_id.assert_called_once()


class TestUUIDStore:
    def test_id(self):
        """ Tests that the ids are unique and consistent. """
        store = UUIDStore()

        ids = [
            "streamer_a",
            "streamer_b",
            "streamer_c",
            "streamer_d",
            "streamer_e",
        ]

        anonymous_ids = set()

        for _id in ids:
            first_id = store.id(_id)
            second_id = store.id(_id)
            assert first_id == second_id
            assert not first_id in anonymous_ids
            anonymous_ids.add(first_id)


class TestIncrementingIdStore:
    def test_id(self):
        """ Tests that the ids are unique and consistent. """
        store = IncrementingIdStore()

        ids = [
            "streamer_a",
            "streamer_b",
            "streamer_c",
            "streamer_d",
            "streamer_e",
        ]

        anonymous_ids = set()

        for _id in ids:
            first_id = store.id(_id)
            second_id = store.id(_id)
            assert first_id == second_id
            assert not first_id in anonymous_ids
            anonymous_ids.add(first_id)


class TestConsistentAnonymiser:
    def test_streamer_id_empty_string(self):
        anonymiser = ConsistentAnonymiser()
        assert anonymiser.channel_id("") == ""

    test_channel_points_data = [
        [0, []],
        [123, [10, 0, -50, 450, 10_000]],
        [23_423, [-23_423, 10, 100]]
    ]

    @pytest.mark.parametrize("initial_points,deltas", test_channel_points_data)
    def test_channel_points(self, initial_points: int, deltas: list[int]):
        """ Tests that channel points are consistent and are correctly updated by a list of point deltas. """
        random_int = MagicMock()
        random_int.return_value = 1000

        streamer = Streamer("test", channel_points=initial_points)

        anonymiser = ConsistentAnonymiser(random_source=RandomSource(random_int))

        assert anonymiser.channel_points(streamer) == 1000

        current_expected_points = 1000
        for delta in deltas:
            streamer.channel_points += delta
            current_expected_points += delta
            assert anonymiser.channel_points(streamer) == current_expected_points
