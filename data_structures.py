import pathlib
import datetime

from dataclasses import dataclass

@dataclass
class CommitInfo:
    date: datetime.datetime
    author: str
    description: str
    branch: str
    hash: str
    files: list[pathlib.Path]