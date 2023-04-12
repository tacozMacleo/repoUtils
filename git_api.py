import datetime
import pathlib
import subprocess
import tempfile

first_commit_hash = ['git', 'hash-object', '-t', 'tree', '/dev/null']


def create_branch(
    branch_name: str,
    cwd: pathlib.Path,
):
    # git checkout -b {branch_name}
    cmd = ['git', 'checkout', '-b', branch_name]
    output = subprocess.run(cmd, capture_output=True, cwd=str(cwd))
    # print('create_branch, stdout:', output.stdout.decode())
    # print('create_branch, stderr:', output.stderr.decode())
    return output.returncode, output.stdout.decode(), output.stderr.decode()

def add_file(
    file_name: pathlib.Path,
    cwd: pathlib.Path,
):
    # git add {file_name}
    cmd = ['git', 'add', str(file_name)]
    output = subprocess.run(cmd, capture_output=True, cwd=str(cwd))
    # print('add_file, stdout:', output.stdout.decode())
    # print('add_file, stderr:', output.stderr.decode())
    return output.returncode, output.stdout.decode(), output.stderr.decode()

def commit(
    desc: str,
    author: str,
    date: datetime.datetime,
    cwd: pathlib.Path,
):
    # git commit -m {desc} --date={date.isoformat()} --author={author}
    cmd = [
        'git', 'commit',
        '-m', f'{desc}'
    ]
    name = author.split('<')[0].strip()
    email = author.split('<')[0].replace('>', '').strip()
    env = {
        'GIT_AUTHOR_NAME': name,
        'GIT_AUTHOR_EMAIL': email,
        'GIT_AUTHOR_DATE': date.isoformat(),
        'GIT_COMMITTER_NAME': name,
        'GIT_COMMITTER_EMAIL': email,
        'GIT_COMMITTER_DATE': date.isoformat(),
    }
    output = subprocess.run(cmd, capture_output=True, cwd=str(cwd), env=env)
    # print('Commit, stdout:', output.stdout.decode())
    # print('Commit, stderr:', output.stderr.decode())
    return output.returncode, output.stdout.decode(), output.stderr.decode()

def create_file(
    file: pathlib.Path,
    diff: bytes,
    cwd: pathlib.Path,
):
    # git apply {diff}
    # print(f'{cwd=}')
    # print(f'{file=}')
    new_file: pathlib.Path = cwd / file
    new_file.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile('wb') as temp_file:
        temp_file.write(diff)
        temp_file.flush()
        cmd = ['git', 'apply', temp_file.name]
        output = subprocess.run(
            cmd,
            capture_output=True,
            cwd=str(cwd) if cwd is not None else cwd
        )
    # print('Create_file, stdout: ', output.stdout.decode())
    # print('Create_file, stderr: ', output.stderr.decode())
    return output.returncode, output.stdout.decode(), output.stderr.decode()
