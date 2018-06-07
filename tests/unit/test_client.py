import pytest

import usine


@pytest.fixture
def patch_client(monkeypatch):

    def call(self, cmd, **kwargs):
        return self._build_command(cmd, **kwargs)

    def open_(self, *args, **kwargs):
        pass

    def close(self, *args, **kwargs):
        pass

    monkeypatch.setattr('usine.Client.__call__', call)
    monkeypatch.setattr('usine.Client.open', open_)
    monkeypatch.setattr('usine.Client.close', close)
    with usine.connect(hostname='foo@bar'):
        yield


def test_hostname_parsing(patch_client):
    assert usine.client.username == 'foo'
    assert usine.client.hostname == 'bar'


def test_run(patch_client):
    assert usine.run('pouet') == "sh -c $'pouet'"


def test_ls(patch_client):
    assert usine.ls('/tmp/foo') == \
        "sh -c $'ls --all --human-readable --size -l /tmp/foo'"


def test_ls_without_human_readable(patch_client):
    assert usine.ls('/tmp/foo', human_readable=False) == \
        "sh -c $'ls --all --size -l /tmp/foo'"


def test_ls_without_size(patch_client):
    assert usine.ls('/tmp/foo', size=False) == \
        "sh -c $'ls --all --human-readable -l /tmp/foo'"


def test_ls_without_all(patch_client):
    assert usine.ls('/tmp/foo', all=False) == \
        "sh -c $'ls --human-readable --size -l /tmp/foo'"


def test_ls_without_list(patch_client):
    assert usine.ls('/tmp/foo', list=False) == \
        "sh -c $'ls --all --human-readable --size /tmp/foo'"
