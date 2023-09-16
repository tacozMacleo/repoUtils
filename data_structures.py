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
    file_adds: list[pathlib.Path]
    file_dels: list[pathlib.Path]
    tags: list[str]
    parents: list[str]
