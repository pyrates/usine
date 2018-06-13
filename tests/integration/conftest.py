import os
import sys
from pathlib import Path

from pytest import fixture
from usine import connect, run, sudo


def pytest_ignore_collect():
    if not os.environ.get('USINE_TEST_HOST'):
        print('USINE_TEST_HOST is not defined: excluding integrations tests')
        return True


def pytest_configure(config):
    # Make select.select happy.
    sys.stdin = (Path(__file__).parent / 'test.txt').open()


@fixture(scope='module')
def connection():
    with connect(hostname=os.environ.get('USINE_TEST_HOST')):
        with sudo():
            run('useradd -N usinetest -d /srv/usine/ '
                '|| echo "usinetest exists"')
            yield
            run('userdel usinetest')
