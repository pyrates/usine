import pytest
from usine import cd, cp, env, exists, ls, mkdir, mv, run


def test_simple_run(connection):
    res = run('echo pouet')
    assert res.stdout == 'pouet\r\n'


def test_folder_creation_existence_and_deletion(connection):
    path = '/tmp/usinetestfolder'
    run(f'rmdir {path} || exit 0')
    assert not exists(path)
    mkdir(path)
    assert exists(path)
    run(f'rmdir {path}')
    assert not exists(path)


def test_trying_to_create_existing_folder(connection):
    path = '/tmp/usinetestfolder'
    run(f'rmdir {path} || exit 0')
    mkdir(path)
    mkdir(path)  # Should not fail
    with pytest.raises(SystemExit):
        mkdir(path, parents=False)
    run(f'rmdir {path}')


def test_folder_creation_existence_and_deletion_with_subfolder(connection):
    path = '/tmp/usinetestfolder'
    subpath = f'{path}/subfolder'
    run(f'rmdir {subpath} || exit 0')
    run(f'rmdir {path} || exit 0')
    assert not exists(path)
    with pytest.raises(SystemExit):
        mkdir(subpath, parents=False)
    mkdir(subpath)
    assert exists(subpath)
    run(f'rmdir {subpath}')
    run(f'rmdir {path}')
    assert not exists(path)


def test_file_creation_existence_and_deletion(connection):
    path = '/tmp/usinetestfile'
    run(f'rm {path} || exit 0')
    assert not exists(path)
    run(f'touch {path}')
    assert exists(path)
    run(f'rm {path}')
    assert not exists(path)


def test_file_mv(connection):
    path = '/tmp/usinetestfile'
    newpath = '/tmp/usinenewtestfile'
    run(f'rm {newpath} || exit 0')
    run(f'touch {path}')
    mv(path, newpath)
    assert exists(newpath)
    assert not exists(path)
    run(f'rm {newpath}')
    assert not exists(newpath)


def test_file_cp(connection):
    path = '/tmp/usinetestfile'
    targetpath = '/tmp/usinetargettestfile'
    run(f'rm {targetpath} || exit 0')
    run(f'touch {path}')
    cp(path, targetpath)
    assert exists(targetpath)
    assert exists(path)
    run(f'rm {targetpath}')
    assert not exists(targetpath)
    run(f'rm {path}')
    assert not exists(path)


def test_folder_mv(connection):
    path = '/tmp/usinetestfolder'
    newpath = '/tmp/usinenewtestfolder'
    run(f'rmdir {newpath} || exit 0')
    mkdir(path)
    mv(path, newpath)
    assert exists(newpath)
    assert not exists(path)
    run(f'rmdir {newpath}')
    assert not exists(newpath)


def test_folder_cp(connection):
    path = '/tmp/usinetestfolder'
    targetpath = '/tmp/usinetargettestfolder'
    run(f'rmdir {targetpath} || exit 0')
    mkdir(path)
    cp(path, targetpath)
    assert exists(targetpath)
    assert exists(path)
    run(f'rmdir {targetpath}')
    assert not exists(targetpath)
    run(f'rmdir {path}')
    assert not exists(path)


def test_ls(connection, capsys):
    assert 'hosts' in ls('/etc/').stdout
    out, err = capsys.readouterr()
    assert 'hosts' in out


def test_env():
    with env(FOO='pouet'):
        res = run('echo $FOO')
    assert res.stdout == 'pouet\r\n'


def test_cd():
    with cd('/tmp'):
        res = run('pwd')
    assert res.stdout == '/tmp\r\n'
