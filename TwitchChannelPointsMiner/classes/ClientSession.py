import string
from dataclasses import dataclass
from secrets import choice, token_hex
from typing import Protocol

import requests
from requests.adapters import HTTPAdapter

from TwitchChannelPointsMiner.classes.TwitchLogin import TwitchLogin
from TwitchChannelPointsMiner.constants import CLIENT_ID, CLIENT_VERSION
from TwitchChannelPointsMiner.utils.Utils import get_user_agent


class ClientSession:
    """Represents a Client Session with Twitch."""

    def __init__(
        self,
        login: TwitchLogin,
        user_agent: str,
        session: requests.Session,
        version: str,
        device_id: str,
        session_id: str,
        version_outdated: bool = False,
    ):
        self.login = login
        self.user_agent = user_agent
        self.session = session
        self.version = version
        self.version_outdated = version_outdated
        self.device_id = device_id
        self.session_id = session_id


@dataclass
class ClientSessionConfig:
    client_id: str | None = None
    user_agent: str | None = None
    device_id: str | None = None
    session_id: str | None = None
    version: str | None = None
    maxsize: int = 20
    connections: int = 10


class ClientSessionFactory(Protocol):
    def __call__(
        self, username: str, password: str | None, config: ClientSessionConfig
    ) -> ClientSession: ...


def client_session_factory(
    username: str,
    password: str | None,
    config: ClientSessionConfig,
) -> ClientSession:
    # Set up defaults
    client_id = config.client_id if config.client_id else CLIENT_ID
    user_agent = (
        config.user_agent if config.user_agent is not None else get_user_agent("CHROME")
    )
    version = config.version if config.version is not None else CLIENT_VERSION
    device_id = (
        config.device_id
        if config.device_id
        else "".join(choice(string.ascii_letters + string.digits) for _ in range(32))
    )
    session_id = token_hex(16)

    # Set up the login
    login = TwitchLogin(client_id, device_id, username, user_agent, password=password)

    # Set up the session http(s) adapters with custom config
    session = requests.Session()
    adapter = HTTPAdapter(
        pool_connections=config.connections,
        pool_maxsize=config.maxsize,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    # Add the user agent to the session headers
    session.headers.update({"User-Agent": user_agent})

    return ClientSession(
        login=login,
        user_agent=user_agent,
        session=session,
        version=version,
        device_id=device_id,
        session_id=session_id,
        version_outdated=True,
    )
