import os
import sys
from pathlib import Path

from pytest import fixture
from usine import connect, run


def pytest_configure(config):
    # Make select.select happy.
    sys.stdin = (Path(__file__).parent / 'test.txt').open()


@fixture(scope='module')
def connection():
    with connect(hostname=os.environ.get('USINE_TEST_HOST')):
        run('useradd -N usinetest -d /srv/tilery/ || echo "usinetest exists"')
        yield
        run('userdel usinetest')
