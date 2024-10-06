import warnings
from typing import Optional

from faststream._internal.proto import NameProxy
from faststream.exceptions import SetupError


class StreamSub(NameProxy):
    """A class to represent a Redis Stream subscriber."""

    __slots__ = (
        "_prefix",
        "_value",
        "polling_interval",
        "last_id",
        "group",
        "consumer",
        "no_ack",
        "batch",
        "max_records",
        "maxlen",
    )

    def __init__(
        self,
        stream: Optional[str] = None,
        polling_interval: Optional[int] = 100,
        group: Optional[str] = None,
        consumer: Optional[str] = None,
        batch: bool = False,
        no_ack: bool = False,
        last_id: Optional[str] = None,
        maxlen: Optional[int] = None,
        max_records: Optional[int] = None,
    ) -> None:
        if (group and not consumer) or (not group and consumer):
            raise SetupError("You should specify `group` and `consumer` both")

        if group and consumer and no_ack:
            warnings.warn(
                message="`no_ack` has no effect with consumer group",
                category=RuntimeWarning,
                stacklevel=1,
            )

        if last_id is None:
            last_id = "$"

        super().__init__(stream)

        self.group = group
        self.consumer = consumer
        self.polling_interval = polling_interval
        self.batch = batch
        self.no_ack = no_ack
        self.last_id = last_id
        self.maxlen = maxlen
        self.max_records = max_records
