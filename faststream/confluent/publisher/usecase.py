from collections.abc import Iterable
from typing import TYPE_CHECKING, Optional, Union

from confluent_kafka import Message
from typing_extensions import override

from faststream._internal.publisher.configs import PublisherUseCaseConfigs
from faststream._internal.publisher.usecase import PublisherUsecase
from faststream._internal.types import MsgType
from faststream.confluent.publisher.configs import ConfluentPublisherBaseConfigs
from faststream.confluent.response import KafkaPublishCommand
from faststream.message import gen_cor_id
from faststream.response.publish_type import PublishType

if TYPE_CHECKING:
    import asyncio

    from faststream._internal.basic_types import SendableMessage
    from faststream._internal.types import PublisherMiddleware
    from faststream.confluent.message import KafkaMessage
    from faststream.confluent.publisher.producer import AsyncConfluentFastProducer
    from faststream.response.response import PublishCommand


class LogicPublisher(PublisherUsecase[MsgType]):
    """A class to publish messages to a Kafka topic."""

    _producer: "AsyncConfluentFastProducer"

    def __init__(self, *, base_configs: ConfluentPublisherBaseConfigs) -> None:
        publisher_configs = PublisherUseCaseConfigs(
            broker_middlewares=base_configs.broker_middlewares,
            middlewares=base_configs.middlewares
        )
        super().__init__(publisher_configs=publisher_configs)

        self.topic = base_configs.topic
        self.partition = base_configs.partition
        self.reply_to = base_configs.reply_to
        self.headers = base_configs.headers or {}

    def add_prefix(self, prefix: str) -> None:
        self.topic = f"{prefix}{self.topic}"

    @override
    async def request(
        self,
        message: "SendableMessage",
        topic: str = "",
        *,
        key: Optional[bytes] = None,
        partition: Optional[int] = None,
        timestamp_ms: Optional[int] = None,
        headers: Optional[dict[str, str]] = None,
        correlation_id: Optional[str] = None,
        timeout: float = 0.5,
    ) -> "KafkaMessage":
        cmd = KafkaPublishCommand(
            message,
            topic=topic or self.topic,
            key=key,
            partition=partition or self.partition,
            headers=self.headers | (headers or {}),
            correlation_id=correlation_id or gen_cor_id(),
            timestamp_ms=timestamp_ms,
            timeout=timeout,
            _publish_type=PublishType.REQUEST,
        )

        msg: KafkaMessage = await self._basic_request(cmd)
        return msg


class DefaultPublisher(LogicPublisher[Message]):
    def __init__(self, *, base_configs: ConfluentPublisherBaseConfigs) -> None:
        super().__init__(base_configs=base_configs)

        self.key = base_configs.key

    @override
    async def publish(
        self,
        message: "SendableMessage",
        topic: str = "",
        *,
        key: Optional[bytes] = None,
        partition: Optional[int] = None,
        timestamp_ms: Optional[int] = None,
        headers: Optional[dict[str, str]] = None,
        correlation_id: Optional[str] = None,
        reply_to: str = "",
        no_confirm: bool = False,
    ) -> "asyncio.Future":
        cmd = KafkaPublishCommand(
            message,
            topic=topic or self.topic,
            key=key or self.key,
            partition=partition or self.partition,
            reply_to=reply_to or self.reply_to,
            headers=self.headers | (headers or {}),
            correlation_id=correlation_id or gen_cor_id(),
            timestamp_ms=timestamp_ms,
            no_confirm=no_confirm,
            _publish_type=PublishType.PUBLISH,
        )
        return await self._basic_publish(cmd, _extra_middlewares=())

    @override
    async def _publish(
        self,
        cmd: Union["PublishCommand", "KafkaPublishCommand"],
        *,
        _extra_middlewares: Iterable["PublisherMiddleware"],
    ) -> None:
        """This method should be called in subscriber flow only."""
        cmd = KafkaPublishCommand.from_cmd(cmd)

        cmd.destination = self.topic
        cmd.add_headers(self.headers, override=False)
        cmd.reply_to = cmd.reply_to or self.reply_to

        cmd.partition = cmd.partition or self.partition
        cmd.key = cmd.key or self.key

        await self._basic_publish(cmd, _extra_middlewares=_extra_middlewares)

    @override
    async def request(
        self,
        message: "SendableMessage",
        topic: str = "",
        *,
        key: Optional[bytes] = None,
        partition: Optional[int] = None,
        timestamp_ms: Optional[int] = None,
        headers: Optional[dict[str, str]] = None,
        correlation_id: Optional[str] = None,
        timeout: float = 0.5,
    ) -> "KafkaMessage":
        return await super().request(
            message,
            topic=topic,
            key=key or self.key,
            partition=partition,
            timestamp_ms=timestamp_ms,
            headers=headers,
            correlation_id=correlation_id,
            timeout=timeout,
        )


class BatchPublisher(LogicPublisher[tuple[Message, ...]]):
    @override
    async def publish(
        self,
        *messages: "SendableMessage",
        topic: str = "",
        partition: Optional[int] = None,
        timestamp_ms: Optional[int] = None,
        headers: Optional[dict[str, str]] = None,
        correlation_id: Optional[str] = None,
        reply_to: str = "",
        no_confirm: bool = False,
    ) -> None:
        cmd = KafkaPublishCommand(
            *messages,
            key=None,
            topic=topic or self.topic,
            partition=partition or self.partition,
            reply_to=reply_to or self.reply_to,
            headers=self.headers | (headers or {}),
            correlation_id=correlation_id or gen_cor_id(),
            timestamp_ms=timestamp_ms,
            no_confirm=no_confirm,
            _publish_type=PublishType.PUBLISH,
        )

        return await self._basic_publish_batch(cmd, _extra_middlewares=())

    @override
    async def _publish(
        self,
        cmd: Union["PublishCommand", "KafkaPublishCommand"],
        *,
        _extra_middlewares: Iterable["PublisherMiddleware"],
    ) -> None:
        """This method should be called in subscriber flow only."""
        cmd = KafkaPublishCommand.from_cmd(cmd, batch=True)

        cmd.destination = self.topic
        cmd.add_headers(self.headers, override=False)
        cmd.reply_to = cmd.reply_to or self.reply_to

        cmd.partition = cmd.partition or self.partition

        await self._basic_publish_batch(cmd, _extra_middlewares=_extra_middlewares)
