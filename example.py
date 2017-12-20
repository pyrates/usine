from usine import sudo, exists, mkdir, init
import minicli


@minicli.cli
def create_bar():
    with sudo(user='tamer'):
        if exists('/foo'):
            mkdir('/foo/bar')


if __name__ == '__main__':
    init('foo.bar')
    minicli.run()
