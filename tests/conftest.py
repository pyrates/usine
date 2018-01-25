import os

from pytest import fixture
from usine import connect, run


@fixture(scope='module')
def connection():
    with connect(hostname=os.environ.get('USINE_TEST_HOST')):
        run('useradd -N usinetest -d /srv/tilery/')
        yield
        run('userdel usinetest')
