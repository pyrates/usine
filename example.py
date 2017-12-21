from usine import sudo, exists, mkdir, init, ls, cd
import minicli


@minicli.cli
def create_bar():
    with sudo(user='tamer'), cd('/srv/'):
        if exists('/tmp/foo'):
            mkdir('/tmp/foo/bar')
        else:
            print('/tmp/foo does not exist')
            print(ls('tamer'))


if __name__ == '__main__':
    init('woodland')
    minicli.run()
