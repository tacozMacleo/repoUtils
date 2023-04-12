#!/usr/bin/env python3
import argparse
import datetime
import pathlib
import itertools

from dataclasses import dataclass

from rich.progress import Progress  # type: ignore
from rich.console import Console  # type: ignore

import hg_api
import git_api

console = Console()


@dataclass
class CommitInfo:
    date: datetime.datetime
    author: str
    description: str
    branch: str
    hash: str
    files: list[pathlib.Path]


def shorten_path(
    filter_path: pathlib.Path,
    file_path: pathlib.Path
) -> pathlib.Path:
    r_path: tuple[str, ...]
    for x, y in itertools.zip_longest(filter_path.parts, file_path.parts):
        if x != y: break
    r_path = file_path.parts[file_path.parts.index(y):]
    return pathlib.Path('/'.join(r_path))


def fix_diff_path(
    old_path: pathlib.Path,
    new_path: pathlib.Path,
    diff: bytes
) -> bytes:
    return diff.replace(
        str(old_path).encode(),  # Old
        str(new_path).encode(),  # New
        3 if b'/dev/null' in diff else 4  # Count
    )


def generate_repo_info(
    repo_path: pathlib.Path,
    branch: str | None = None
) -> list[CommitInfo]:
    hash_length = len(hg_api.get_hashs(cwd=repo_path, branch=branch))

    r_data: list[CommitInfo] = []

    with Progress() as progress:
        task = progress.add_task("Generating Commit list...", total=hash_length)

        for commit_info in hg_api.get_full_info(cwd=repo_path, branch=branch):
            commit_hash, date, auther, desc, branch, files = commit_info
            progress.update(task, description=f"Parsing commit <{commit_hash}>")

            r_data.append(CommitInfo(
                date=date,
                author=auther,
                description=desc,
                branch=branch,
                hash=commit_hash,
                files=files
            ))
            progress.advance(task)
        progress.update(task, description='All commits parsed.')

    return r_data


def transfer_repo(
    data: list[CommitInfo],
    src_repo: pathlib.Path,
    dst_repo: pathlib.Path,
    file_filter: pathlib.Path,
    reducer: bool,
) -> None:
    something_added: bool = False
    with Progress() as progress:
        task_commit = progress.add_task(f"Checking commit...", total=len(data))

        for commit in data:
            progress.update(task_commit, description=f"Checking <{commit.hash}>")
            file_task = progress.add_task(f"Checking files.", total=len(commit.files))

            for file in commit.files:
                if file_filter in file.parents or file_filter == file:
                    progress.update(file_task, description=f'Adding: {file}')
                    diff = hg_api.get_file_diff(hash=commit.hash, file_name=file, cwd=src_repo)

                    if reducer:
                        old_path = file
                        file = shorten_path(file_filter, file)
                        diff = fix_diff_path(old_path, file, diff)

                    if len(diff) <= 1:
                        progress.console.print(f'[bold red]Warning Empty Diff for: [/bold red] {file}')

                    rc, *std = git_api.create_file(file=file, diff=diff, cwd=dst_repo)

                    if rc != 0:
                        progress.console.print(f'[bold red]Warning Create file error: [/bold red] {commit.hash}\n{std[0]}\n{std[1]}')
                        progress.console.print(diff)

                    git_api.add_file(file_name=file, cwd=dst_repo)
                    something_added = True
                    progress.advance(file_task)

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

    data = generate_repo_info(args.repo, branch=args.branch)

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
        exit(-3)

    transfer_repo(
        data=data,
        src_repo=args.repo,
        dst_repo=args.out,
        file_filter=args.filter,
        reducer=args.shorten,
    )
