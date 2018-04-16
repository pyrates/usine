from io import StringIO

import minicli
from usine import cd, connect, env, exists, ls, mkdir, put, run, sudo, screen


@minicli.cli
def create_bar():
    with sudo(user='tamer'), cd('/srv/'):
        if exists('/tmp/foo'):
            mkdir('/tmp/foo/bar')
        else:
            print('/tmp/foo does not exist')
            ls('tamer')


@minicli.cli
def pass_env():
    with env(FOO='bar'):
        run('echo $FOO')
    with sudo(user='tamer'), env(FOO='baz'):
        run('echo $FOO')


@minicli.cli
def put_file():
    with sudo(user='tamer'):
        put('README.md', '/tmp/foobarbaz')
        ls('/tmp/foobarbaz')
        run('cat /tmp/foobarbaz')
        put(StringIO('foobarbazéé'), '/tmp/foobarbaz')
        run('cat /tmp/foobarbaz')


@minicli.cli
def with_screen(name='usine', target='8.8.8.8'):
    with screen(name):
        run(f'ping {target}')


@minicli.cli
def python():
    run('python')


if __name__ == '__main__':
    with connect('woodland'):
        minicli.run()
