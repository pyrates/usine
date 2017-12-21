from usine import sudo, exists, mkdir, init, ls
import minicli


@minicli.cli
def create_bar():
    with sudo(user='tamer'):
        if exists('/foo'):
            mkdir('/foo/bar')
        else:
            print('/foo does not exist')
            print(ls('/srv/tamer'))


if __name__ == '__main__':
    init('woodland')
    minicli.run()
