"""Models the `epics` section of YAML hardware configuration file.

Provides an API to read configured EPICS channels.
"""

from typing import (
    Dict,
    Iterable,
    Optional,
    Tuple,
)

from pydantic import (
    BaseModel,
    RootModel,
)


class Channel(BaseModel):
    """EPICS channel configuration."""

    suffix: Optional[str] = None
    polling_period: Optional[int] = None


class Prefix(BaseModel):
    """Configuration of an EPICS prefix section."""

    channels: Optional[Dict[str, Optional[Channel]]]

    def get_channels(self) -> Iterable[Tuple[str, Channel]]:
        """Get all channels configured for prefix.

        This method will fill in optional configuration properties for a channel.
        """

        def setup_channel_config(channel_name, channel_config):
            """Set-up channel config model object

            Deals with filling in optional configuration properties.
            """
            if channel_config is None:
                channel_config = Channel()

            if channel_config.suffix is None:
                channel_config.suffix = channel_name

            return channel_config

        if self.channels is None:
            return []

        for channel_name, channel_config in self.channels.items():
            yield channel_name, setup_channel_config(channel_name, channel_config)


class EpicsConfig(RootModel[Dict[str, Prefix]]):
    """The 'epics' section of the hardware object's YAML configuration file."""

    def get_prefixes(self) -> Iterable[Tuple[str, Prefix]]:
        """Get all prefixes specified in this section."""
        return list(self.root.items())
