import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class BegetConfig:
    login: str
    password: str
    timeout: int = 30

    def __post_init__(self) -> None:
        if not self.login or not self.password:
            raise ValueError(
                "BEGET_API_LOGIN and BEGET_API_PASSWORD must be set. "
                "Pass them as environment variables or in a .env file."
            )


def load_config() -> BegetConfig:
    load_dotenv()
    config = BegetConfig(
        login=os.getenv("BEGET_API_LOGIN", ""),
        password=os.getenv("BEGET_API_PASSWORD", ""),
    )
    log.info("Config loaded for user '%s'", config.login)
    return config
