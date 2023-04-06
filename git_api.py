import datetime
import pathlib
import subprocess
import tempfile

first_commit_hash = ['git', 'hash-object', '-t', 'tree', '/dev/null']


def create_branch(
    branch_name: str = 'imported',
    cwd: pathlib.Path | str | None = None
):
    # git checkout -b {branch_name}
    if cwd is not None:
        cwd = str(cwd)
    cmd = ['git', 'checkout', '-b', branch_name]
    output = subprocess.run(cmd, capture_output=True, cwd=cwd)
    # print('create_branch, stdout:', output.stdout.decode())
    # print('create_branch, stderr:', output.stderr.decode())
    return output.returncode, output.stdout.decode(), output.stderr.decode()

def add_file(
    file_name: pathlib.Path,
    cwd: pathlib.Path | str | None = None
):
    # git add {file_name}
    if cwd is not None:
        cwd = str(cwd)
    cmd = ['git', 'add', str(file_name)]
    output = subprocess.run(cmd, capture_output=True, cwd=cwd)
    # print('add_file, stdout:', output.stdout.decode())
    # print('add_file, stderr:', output.stderr.decode())

def commit(
    desc: str,
    author: str,
    date: datetime.datetime,
    cwd: pathlib.Path | str | None = None
):
    # git commit -m {desc} --date={date.isoformat()} --author={author}
    if cwd is not None:
        cwd = str(cwd)
    cmd = [
        'git', 'commit',
        '-m', f'{desc}',
        f'--date={date.isoformat()}',
        f'--author={author}'
    ]
    output = subprocess.run(cmd, capture_output=True, cwd=cwd)
    # print('Commit, stdout:', output.stdout.decode())
    # print('Commit, stderr:', output.stderr.decode())

def create_file(
    file: pathlib.Path,
    diff: bytes,
    cwd: pathlib.Path | str | None = None
):
    # git apply {diff}
    new_file: pathlib.Path = cwd / file
    # print(f'{cwd=}')
    # print(f'{file=}')
    if cwd is not None:
        cwd = str(cwd)
    new_file.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('wb') as temp_file:
        temp_file.write(diff)
        temp_file.flush()
        cmd = ['git', 'apply', temp_file.name]
        output = subprocess.run(cmd, capture_output=True, cwd=cwd)
    # print('Create_file, stdout: ', output.stdout.decode())
    # print('Create_file, stderr: ', output.stderr.decode())
