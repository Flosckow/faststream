import os
import subprocess
import threading
import time
from collections.abc import Generator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from textwrap import dedent
from typing import Protocol

import pytest

from faststream import FastStream


@pytest.fixture()
def broker():
    # separate import from e2e tests
    from faststream.rabbit import RabbitBroker

    return RabbitBroker()


@pytest.fixture()
def app_without_logger(broker) -> FastStream:
    return FastStream(broker, logger=None)


@pytest.fixture()
def app_without_broker() -> FastStream:
    return FastStream()


@pytest.fixture()
def app(broker) -> FastStream:
    return FastStream(broker)


class GenerateTemplateFactory(Protocol):
    def __call__(
        self, code: str, filename: str = "temp_app.py"
    ) -> AbstractContextManager[Path]: ...


@pytest.fixture()
def generate_template(
    tmp_path: "Path",
) -> GenerateTemplateFactory:
    @contextmanager
    def factory(
        code: str, filename: str = "temp_app.py"
    ) -> Generator["Path", None, None]:
        temp_dir = tmp_path / "faststream_templates"
        temp_dir.mkdir(exist_ok=True)

        file_path: Path = temp_dir / filename
        cleaned_code = dedent(code).strip()

        file_path.write_text(cleaned_code)

        try:
            yield file_path
        finally:
            file_path.unlink(missing_ok=True)

    return factory


class CliThread(Protocol):
    process: subprocess.Popen | None

    def stop(self) -> None: ...


class FastStreamCLIFactory(Protocol):
    def __call__(
        self,
        cmd: list[str],
        wait_time: float = 1.5,
        extra_env: dict[str, str] | None = None,
    ) -> AbstractContextManager[CliThread]: ...


@pytest.fixture()
def faststream_cli(tmp_path: "Path") -> FastStreamCLIFactory:
    @contextmanager
    def factory(
        cmd: list[str],
        wait_time: float = 1.5,
        extra_env: dict[str, str] | None = None,
    ) -> Generator[CliThread, None, None]:
        class RealCLIThread(threading.Thread):
            def __init__(self, command: list[str], env: dict[str, str]) -> None:
                super().__init__()
                self.command = command
                self.process: subprocess.Popen | None = None
                self.env = env

            def run(self) -> None:
                self.process = subprocess.Popen(
                    self.command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    shell=False,
                    env=self.env,
                )
                self.process.wait()

            def stop(self) -> None:
                if self.process:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                    self.process = None

        extra_env = extra_env or {}
        env = os.environ.copy()
        env.update(**extra_env)
        cli = RealCLIThread(cmd, env)
        cli.start()
        time.sleep(wait_time)

        try:
            yield cli
        finally:
            cli.stop()
            cli.join()

    return factory
