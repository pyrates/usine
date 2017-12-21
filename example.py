from usine import sudo, exists, mkdir, init, ls, cd, env, run
import minicli


@minicli.cli
def create_bar():
    with sudo(user='tamer'), cd('/srv/'):
        if exists('/tmp/foo'):
            mkdir('/tmp/foo/bar')
        else:
            print('/tmp/foo does not exist')
            print(ls('tamer'))


@minicli.cli
def pass_env():
    with env(FOO='bar'):
        print(run('echo $FOO'))
    with sudo(user='tamer'), env(FOO='baz'):
        print(run('echo $FOO'))


if __name__ == '__main__':
    init('woodland')
    minicli.run()
