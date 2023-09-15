import datetime
import itertools
import pathlib
import re
import subprocess

from typing import Iterable, Iterator, Any

from data_structures import CommitInfo

first_commit_hash = 'null'

# hg help revsets
# https://book.mercurial-scm.org/read/template.html

def pairwise(iterable: Iterable[Any]) -> Iterator[tuple[Any, Any]]:
    """
    Return paired elements.

    For example:
        s -> (s0, s1), (s2, s3), (s4, s5), ...
    """
    iterable = iter(iterable)
    return itertools.zip_longest(iterable, iterable)


def get_all_branches(
    cwd: pathlib.Path | str | None = None,
) -> list[str]:
    # hg log -r : --template '{node}\n'
    if cwd is not None:
        cwd = str(cwd)

    cmd = ["hg", "branches", "-c", "--template", "{branch}\n"]

    output = subprocess.run(cmd, capture_output=True, cwd=cwd)
    return list(filter(lambda x: bool(x), output.stdout.decode().split('\n')))



def get_open_branches(
    cwd: pathlib.Path | str | None = None,
) -> list[str]:
    # hg log -r : --template '{node}\n'
    if cwd is not None:
        cwd = str(cwd)

    cmd = ["hg", "branches", "--template", "{branch}\n"]

    output = subprocess.run(cmd, capture_output=True, cwd=cwd)
    return list(filter(lambda x: bool(x), output.stdout.decode().split('\n')))


def get_closed_branches(
    cwd: pathlib.Path | str | None = None,
) -> list[str]:
    # hg log -r : --template '{node}\n'
    if cwd is not None:
        cwd = str(cwd)

    cmd = ["hg", "branches", "-c", "-r", 'closed()', "--template", "{branch}\n"]

    output = subprocess.run(cmd, capture_output=True, cwd=cwd)
    return list(filter(lambda x: bool(x), output.stdout.decode().split('\n')))


def get_current_branch(
    cwd: pathlib.Path | str | None = None,
) -> str:
    # hg log -r : --template '{node}\n'
    if cwd is not None:
        cwd = str(cwd)

    cmd = ["hg", "branch"]

    output = subprocess.run(cmd, capture_output=True, cwd=cwd)
    return output.stdout.decode().strip()


def get_hashes(
    cwd: pathlib.Path | str | None = None,
    branch: str | None = None,
) -> list[str]:
    # hg log -r : --template '{node}\n'
    if cwd is not None:
        cwd = str(cwd)

    cmd = ["hg", "log", "-r", ":", "--template", "{node}\n"]

    if branch is not None:
        cmd += ['-b', branch]
    output = subprocess.run(cmd, capture_output=True, cwd=cwd)
    return list(filter(lambda x: bool(x), output.stdout.decode().split('\n')))


def get_file_diff(
    hash: str,
    file_name: pathlib.Path,
    cwd: pathlib.Path | str | None = None,
    first: bool = False,
) -> bytes:
    # hg diff -r ".^:${CURRENT_HASH}" "${file}"
    past_commit = f'{hash}^' if first is False else first_commit_hash
    if cwd is not None:
        cwd = str(cwd)
    cmd = ['hg', 'diff', '--git', '-r', f'{past_commit}:{hash}', str(file_name)]
    output = subprocess.run(cmd, capture_output=True, cwd=cwd)
    return output.stdout


def get_info(
    hash: str,
    cwd: pathlib.Path | str | None = None,
) -> tuple[datetime.datetime, str, str, list[pathlib.Path]]:
    # hg log -r "${CURRENT_HASH}" --template '{date|rfc822date}\n{author|email}\n{desc}'
    if cwd is not None:
        cwd = str(cwd)
    cmd = ['hg', 'log', '-r', hash, '--template', '{date|isodate}\n{author}\n{desc}\n{join(files, "\n")}']
    output = subprocess.run(cmd, capture_output=True, cwd=cwd)
    data: list[str] = output.stdout.decode().split('\n')
    date: datetime.datetime = datetime.datetime.fromisoformat(data[0])
    files : list[pathlib.Path] = [ pathlib.Path(file) for file in data[3:]]
    return (date, data[1], data[2], files)


def get_file_list(
    hash: str,
    cwd: pathlib.Path | str | None = None,
) -> list[pathlib.Path]:
    # hg log -r "${HASH}" -v --template '{join(files, "\n")}'
    if cwd is not None:
        cwd = str(cwd)
    cmd = ['hg', 'log', '-r', hash, '-v', '--template', '{join(files, "\n")}']
    output = subprocess.run(cmd, capture_output=True, cwd=cwd)
    return [ pathlib.Path(file) for file in output.stdout.decode().split('\n') if file]


def get_commit_diff(
    hash: str,
    cwd: pathlib.Path | str | None = None,
    first: bool = False,
) -> list[tuple[pathlib.Path, bytes]]:
    past_commit = f'{hash}^' if first is False else first_commit_hash

    if cwd is not None:
        cwd = str(cwd)
    cmd = ['hg', 'diff', '--git', '-r', f'{past_commit}:{hash}']
    output = subprocess.run(cmd, capture_output=True, cwd=cwd)
    try:
        temp = re.split(r'(diff --git[^\n]*\n)', output.stdout.decode())[1:]
    except UnicodeDecodeError:
        files = get_file_list(hash=hash, cwd=cwd)
        return [
            (path, get_file_diff(hash=hash, file_name=path, cwd=cwd))
            for path in files
        ]
    else:
        return [
            (
                pathlib.Path(re.search(r'b/([^\n].*)\n', x)[1]),
                ''.join([x, diff]).encode()
            )
            for x, diff in pairwise(temp)
        ]

def get_full_info(
    cwd: pathlib.Path | str | None = None,
    branch: str | None = None,
) -> list[CommitInfo]:
    desc_file_splitter = '=========\n'
    branch_splitter = '-------------------\n'
    if cwd is not None:
        cwd = str(cwd)
    cmd = ['hg', 'log', '-r', ':', '--template', (
        '{node}\n{date|isodate}\n{author}\n{branch}\n' +
        desc_file_splitter +
        '{desc}\n' +
        # desc_file_splitter +
        # '{join(parents, "||")}' +
        # desc_file_splitter +
        # '{join(tags, "||")}' +
        # desc_file_splitter +
        # '{join(file_adds, "||")}' +
        # desc_file_splitter +
        # '{join(file_dels, "||")}' +
        desc_file_splitter +
        '{join(files, "\n")}' +
        branch_splitter
    )]
    if branch is not None:
        cmd += ['-b', branch]
    output = subprocess.run(cmd, capture_output=True, cwd=cwd)
    commit_list: list[str] = output.stdout.decode().split(branch_splitter)
    return_commit_data = []
    for commit in commit_list[:-1]:
        info, desc, files_raw = commit.split(desc_file_splitter)
        data = info.split('\n')
        if len(data) == 1:
            print('ERROR: ', data)
            continue

        date: datetime.datetime = datetime.datetime.fromisoformat(data[1])
        files : list[pathlib.Path] = [ pathlib.Path(file) for file in files_raw.split('\n')]
        return_commit_data.append(
            CommitInfo(
                hash=data[0],
                date=date,
                author=data[2],
                description=desc.strip(),
                branch=data[3],
                files=files,
            )
        )

    return return_commit_data
