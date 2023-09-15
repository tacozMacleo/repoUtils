#!/usr/bin/env python3
import argparse
import datetime
import pathlib
import itertools
import re

from dataclasses import dataclass
from typing import Any, Callable

from rich.progress import Progress  # type: ignore
from rich.console import Console  # type: ignore
# from rich.prompt import Confirm

import hg_api
import git_api

from data_structures import CommitInfo
from rich_helpers import rich_input

console = Console()


error_count: int = 0


def touch_file(file: pathlib.Path, cwd: pathlib.Path) -> None:
    new_file: pathlib.Path = cwd / file
    new_file.parent.mkdir(parents=True, exist_ok=True)
    new_file.touch()


def pause_script(progress, rc: int, stdout: str , stderr: str) -> None:
    rich_input(
        'Press Enter to continue!',
        progress=progress
    )


def pause_point(progress, pause: bool, rc: int, stdout:str , stderr: str) -> None:
    if pause:
        pause_script(progress, rc, stdout, stderr)


def error_handle(progress, text:str, pause: bool, rc: int, stdout:str , stderr: str, commit_hash, diff) -> None:
    if rc == 0:
        return
    global error_count
    error_count += 1

    progress.console.print(f'[bold red]{text} [/bold red] {commit_hash}\n{stdout}\n{stderr}')
    progress.console.print(diff)
    with open(f"error_out/{error_count}-{commit_hash}.diff", 'wb') as file:
        file.write(diff)

    pause_point(progress=progress, pause=pause, rc=rc, stdout=stdout, stderr=stderr)


def shorten_path(
    filter_path: pathlib.Path,
    file_path: pathlib.Path
) -> pathlib.Path:
    r_path: tuple[str, ...]
    for x, y in itertools.zip_longest(filter_path.parts, file_path.parts):
        if x != y: break
    r_path = file_path.parts[file_path.parts.index(y):]
    return pathlib.Path('/'.join(r_path))


def shorten_diff_file_path(
    shorten_by: pathlib.Path,
    diff: bytes,
) -> bytes:

    first_regex: bytes = b'diff --git a/(.*) b/(.*)\n'
    files = re.search(first_regex, diff)

    if files is None:
        return diff

    old_from_file, old_to_file = map(lambda x: pathlib.Path(x.decode()), files.groups())
    new_from_file = shorten_path(shorten_by, old_from_file)
    new_to_file = shorten_path(shorten_by, old_to_file)

    # count = 3 if b'copy from ' in diff else 2

    return diff.replace(
        str(old_from_file).encode(),  # Old
        str(new_from_file).encode(),  # New
        # count  # Count
    ).replace(
        str(old_to_file).encode(),  # Old
        str(new_to_file).encode(),  # New
        # count  # Count
    )


class RepoConverter:

    src_repo: pathlib.Path
    repo_branch_info: dict[str, list[CommitInfo]]

    def __init__(
        self,
        src_repo: pathlib.Path,
    ):
        self.src_repo = src_repo
        self.repo_branch_info = {}
        self._generate_repo_info()

    def _generate_repo_info(self):
        branches = hg_api.get_open_branches(cwd=self.src_repo)
        branches += hg_api.get_closed_branches(cwd=self.src_repo)

        with Progress() as progress:
            task_branch = progress.add_task("Loading branch:...", total=len(branches))
            for branch in branches:
                progress.update(task_branch, description=f"Loading: {branch}")
                self.repo_branch_info[branch] = hg_api.get_full_info(
                    cwd=self.src_repo, branch=branch
                )
                progress.advance(task_branch)

    def transfer_repo(
        self,
        branch: str,
        dst_repo: pathlib.Path,
        file_filter: pathlib.Path,
        reducer: bool,
        pause: bool = False,
    ) -> None:
        self.file_filter = file_filter
        self.reducer = reducer
        self.pause = pause

        something_added: bool = False
        with Progress() as progress:
            task_commit = progress.add_task(f"Checking commit...", total=len(self.repo_branch_info))

            first_commit = True

            for commit in self.repo_branch_info.get(branch, []):
                progress.update(task_commit, description=f"Checking <{commit.hash}>")
                file_task = progress.add_task(f"Checking files.", total=len(commit.files))

                do_last: list[tuple[pathlib.Path, str, bytes]] = []

                for file in commit.files:
                    if file_filter not in file.parents and file_filter != file:
                        continue
                    progress.update(file_task, description=f'Adding: {file}')
                    diff = hg_api.get_file_diff(
                        hash=commit.hash,
                        file_name=file,
                        cwd=self.src_repo,
                        first=first_commit,
                    )

                    if reducer:
                        old_path = file
                        file = shorten_path(file_filter, file)
                        diff = shorten_diff_file_path(file_filter, diff)

                    if len(diff) <= 1:
                        progress.console.print(f'[bold red]Warning Empty Diff for: [/bold red] {file}')
                        # touch_file(file=file, cwd=dst_repo)

                    if b'deleted file ' in diff:
                        do_last.append((file, commit.hash, diff))
                        continue

                    rc, *std = git_api.create_file(file=file, diff=diff, cwd=dst_repo)

                    error_handle(
                        progress=progress, text="Warning Create file error:",
                        pause=pause, rc=rc, stdout=std[0], stderr=std[1],
                        commit_hash=commit.hash, diff=diff
                    )

                    rc, *std = git_api.add_file(file_name=file, cwd=dst_repo)
                    error_handle(
                        progress=progress, text="Warning Add file error",
                        pause=pause, rc=rc, stdout=std[0], stderr=std[1],
                        commit_hash=commit.hash, diff=diff
                    )

                    something_added = True
                    progress.advance(file_task)

                for file, commit_hash, diff in do_last:
                    rc, *std = git_api.create_file(file=file, diff=diff, cwd=dst_repo)

                    error_handle(
                        progress=progress, text="end: Warning Create file error:",
                        pause=pause, rc=rc, stdout=std[0], stderr=std[1],
                        commit_hash=commit_hash, diff=diff
                    )

                    rc, *std = git_api.add_file(file_name=file, cwd=dst_repo)

                    error_handle(
                        progress=progress, text="end: Warning Add file error:",
                        pause=pause, rc=rc, stdout=std[0], stderr=std[1],
                        commit_hash=commit_hash, diff=diff
                    )

                    something_added = True
                    progress.advance(file_task)

                first_commit = False

                progress.update(file_task, visible=False)

                if something_added:
                    git_api.commit(
                        desc=commit.description,
                        author=commit.author,
                        date=commit.date,
                        cwd=dst_repo,
                    )
                progress.advance(task_commit)
                something_added = False


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # parser.add_argument(
    #     '-v', '--verbose',
    #     action='store_true',
    #     help='The Repo to parse.'
    # )
    parser.add_argument(
        '-s', '--shorten',
        action='store_true',
        help='Shorten the path with the filter. (Folders only)'
    )
    parser.add_argument(
        '-p', '--pause',
        action='store_true',
        help='Pause the converter on failure.',
    )
    parser.add_argument(
        '-r', '--repo',
        type=pathlib.Path,
        required=True,
        help='The Repo to parse.'
    )
    parser.add_argument(
        '-o', '--out',
        type=pathlib.Path,
        required=True,
        help='The new repo to commit to.'
    )
    parser.add_argument(
        '-f', '--filter',
        type=pathlib.Path,
        default=pathlib.Path('.'),
        help='A file filter.'
    )
    parser.add_argument(
        '-b', '--branch',
        type=str,
        help='Only apply changes from given branch.'
    )
    parser.add_argument(
        '--branch-dst',
        type=str,
        default='imported',
        help='Set the output destination branch.'
    )


    args = parser.parse_args()

    if not args.repo.is_dir():
        exit(-1)
        console.print('repo Path need to be to the repo Root folder.')
    if not (args.repo / '.hg').exists():
        console.print('No repo founded in the given source folder.')
        exit(-1)
    if not (args.out / '.git').exists():
        console.print('No git repo found in the given output folder.')
        exit(-1)

    the_repo = RepoConverter(args.repo)

    verbose = lambda *args, **kwargs: None

    # if args.verbose:
    #     for commit in data:
    #         if any([args.filter in file.parents or args.filter == file for file in commit.files]):
    #             console.print(commit)
    #     exit()

    branch_rc, branch_out, branch_err = git_api.create_branch(branch_name=args.branch_dst, cwd=args.out)
    if branch_rc != 0:
        console.print('[bold red]Create Branch failed.[/bold red]')
        console.print('Did you remember to create a git repo and make the first commit?')
        console.print(branch_out)
        console.print(branch_err)
        if not Confirm.ask('Continue anyway?'):
            console.print('Aborting!')
            exit(-3)

    the_repo.transfer_repo(
        branch=hg_api.get_current_branch(cwd=args.repo),
        dst_repo=args.out,
        file_filter=args.filter,
        reducer=args.shorten,
        pause=args.pause,
    )
