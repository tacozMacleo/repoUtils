from typing import Any

from rich.progress import Progress

from rich.prompt import Confirm
from rich.prompt import DefaultType
from rich.prompt import TextIO
from rich.prompt import PromptType

UP = "\x1b[1A"
CLEAR = "\x1b[2K"

from rich.progress import Progress
class PauseProgress:
    def __init__(self, progress: Progress) -> None:
        self._progress = progress

    def _clear_line(self) -> None:
        for _ in self._progress.tasks:
            print(UP + CLEAR + UP)

    def __enter__(self):
        self._progress.stop()
        self._clear_line()
        return self._progress

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._progress.start()


def rich_input(
    prompt: str,
    *,
    progress: Progress,
    password: bool=False,
    stream: TextIO | None=None,
) -> str:
    progress.stop()
    try:
        return Confirm.get_input(
            console=progress.console,
            prompt=prompt,
            password=password,
            stream = stream,
        )
    finally:
        print(CLEAR + UP)
        for _ in progress.tasks:
            print(UP + CLEAR + UP)
        progress.start()
