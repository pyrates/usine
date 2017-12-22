from io import StringIO

import minicli
from usine import cd, connect, env, exists, ls, mkdir, put, run, sudo


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
        print(run('echo $FOO'))
    with sudo(user='tamer'), env(FOO='baz'):
        print(run('echo $FOO'))


@minicli.cli
def put_file():
    put(StringIO('foobarbaz'), '/tmp/foobarbaz')
    run('cat /tmp/foobarbaz')
    put('README.md', '/tmp/foobarbaz')
    run('cat /tmp/foobarbaz')


if __name__ == '__main__':
    with connect('woodland'):
        minicli.run()
