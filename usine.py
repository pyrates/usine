from paramiko import Channel

connection = None


def init(host):
    connection = Channel(host)
    connection.context = {}


def run(cmd):
    if connection.context['sudo']:
        cmd = f'sudo {cmd}'
    connection.execute(cmd)


class sudo:

    def __enter__(self, *args, **kwargs):
        connection.context['sudo'] = kwargs

    def __exit__(self, exception):
        del connection.context['sudo']
