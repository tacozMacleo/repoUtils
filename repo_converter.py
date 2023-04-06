#!/usr/bin/env python3
import argparse
import datetime
import pathlib
import pickle

from dataclasses import dataclass

from rich.progress import Progress
from rich.console import Console

import hg_api
import git_api

console = Console()

# @dataclass
# class FileInfo:
#     file: pathlib.Path
#     diff: bytes


@dataclass
class CommitInfo:
    date: datetime.datetime
    author: str
    description: str
    hash: str
    # files: list[FileInfo]
    files: list[pathlib.Path]


def generate_repo_info(repo_path: pathlib.Path) -> list[CommitInfo]:
    if not repo_path.is_dir():
        raise ValueError('repo Path need to be to the repo Root folder.')
    hg_repo_path = repo_path / '.hg'
    if not hg_repo_path.exists():
        raise ValueError('No repo foudn in the given folder.')
    
    hash_length = len(hg_api.get_hashs(cwd=repo_path))

    r_data: list[CommitInfo] = []

    with Progress() as progress:
        task = progress.add_task("Generating Commit list...", total=hash_length)

        for commit_info in hg_api.get_full_info(cwd=repo_path):
            commit_hash, date, auther, desc, files = commit_info
            progress.update(task, description=f"Parsing commit <{commit_hash}>")
            # files = [
            #     FileInfo(
            #         file=file,
            #         diff=diff,
            #     )
            #     for file, diff in hg_api.get_commit_diff(hash=commit_hash, cwd=repo_path)
            # ]
            r_data.append(CommitInfo(
                date=date,
                author=auther,
                description=desc,
                hash=commit_hash,
                files=files
            ))
            progress.advance(task)
        progress.update(task, description='All commits parsed.')

    return r_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # parser.add_argument(
    #     '-v', '--verbose',
    #     action='store_true',
    #     help='The Repo to parse.'
    # )
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
        help='A file filter'
    )

    args = parser.parse_args()

    data = generate_repo_info(args.repo)

    something_added: bool = False

    verbose = lambda *args, **kwargs: None

    # if args.verbose:
    #     args.verbose = console.print

    branch_rc, branch_out, branch_err = git_api.create_branch(cwd=args.out)
    if branch_rc != 0:
        console.print('[bold red]Create Branch failed.[/bold red]')
        console.print('Did you remember to create a git repo and make the first commit?')
        console.print(branch_out)
        console.print(branch_err)
        exit(-3)
    with Progress() as progress:
        task_commit = progress.add_task(f"Checking commit...", total=len(data))
        for commit in data:
            progress.update(task_commit, description=f"Checking <{commit.hash}>")
            file_task = progress.add_task(f"Checking files.", total=len(commit.files))
            for file in commit.files:
                if args.filter in file.parents or args.filter == file:
                    progress.update(file_task, description=f'Adding: {file}')
                    diff = hg_api.get_file_diff(hash=commit.hash, file_name=file, cwd=args.repo)
                    if len(diff) <= 1:
                        progress.console.print(f'[bold red]Warning Empty Diff for: [/bold red] {file}')
                    git_api.create_file(file=file, diff=diff, cwd=args.out)
                    git_api.add_file(file_name=file, cwd=args.out)
                    something_added = True
                    progress.advance(file_task)
            progress.update(file_task, visible=False)

            if something_added:
                git_api.commit(
                    desc=commit.description,
                    author=commit.author,
                    date=commit.date,
                    cwd=args.out,
                )
            progress.advance(task_commit)
            something_added = False
