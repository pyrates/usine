from io import BytesIO, StringIO
from pathlib import Path

from usine import put, run, cd


def test_put_bytesio(connection):
    remote = '/tmp/usinetestput'
    put(BytesIO(b'foobar'), remote)
    assert run(f'cat {remote}').stdout == 'foobar'
    run(f'rm {remote}')


def test_put_bytesio_with_non_ascii_chars(connection):
    remote = '/tmp/usinetestput'
    put(BytesIO('foobarœé'.encode()), remote)
    assert run(f'cat {remote}').stdout == 'foobarœé'
    run(f'rm {remote}')


def test_put_stringio(connection):
    remote = '/tmp/usinetestput'
    put(StringIO('foobarœé'), remote)
    assert run(f'cat {remote}').stdout == 'foobarœé'
    run(f'rm {remote}')


def test_put_path(connection):
    remote = '/tmp/usinetestput'
    put(Path(__file__).parent / 'test.txt', remote)
    assert run(f'cat {remote}').stdout == 'foobarœé\r\n'
    run(f'rm {remote}')


def test_put_path_as_string(connection):
    remote = '/tmp/usinetestput'
    put(str(Path(__file__).parent / 'test.txt'), remote)
    assert run(f'cat {remote}').stdout == 'foobarœé\r\n'
    run(f'rm {remote}')


def test_put_with_cd(connection):
    remote = 'usinetestput'
    with cd('/tmp'):
        put(str(Path(__file__).parent / 'test.txt'), remote)
        assert run(f'cat {remote}').stdout == 'foobarœé\r\n'
        run(f'rm {remote}')
