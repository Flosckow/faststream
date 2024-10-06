from functools import cached_property
from typing import Optional

from faststream._internal.proto import NameProxy


class ListSub(NameProxy):
    """A class to represent a Redis List subscriber."""

    __slots__ = (
        "_prefix",
        "_value",
        "batch",
        "max_records",
        "polling_interval",
    )

    def __init__(
        self,
        list_name: Optional[str] = None,
        batch: bool = False,
        max_records: int = 10,
        polling_interval: float = 0.1,
    ) -> None:
        super().__init__(list_name)

        self.batch = batch
        self.max_records = max_records
        self.polling_interval = polling_interval

    @cached_property
    def records(self) -> Optional[int]:
        return self.max_records if self.batch else None
