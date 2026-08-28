from TwitchChannelPointsMiner.classes.entities.Streamer import Streamer


def find_streamer(streamers: list[Streamer], channel_id: str) -> Streamer:
    """
    Gets the Streamer in the given list with the given channel id.
    :param streamers: The Streamers to check.
    :param channel_id: The id of the Streamer to find.
    :return: The streamer.
    :raises KeyError: If a Streamer with the given id couldn't be found.
    """
    for streamer in streamers:
        if streamer.channel_id == channel_id:
            return streamer
    raise KeyError(
        f"Streamer with channel_id ({channel_id}) not found in streamer list."
    )
