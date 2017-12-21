from getpass import getuser
from pathlib import Path

from paramiko.client import SSHClient, WarningPolicy
from paramiko.config import SSHConfig

client = None


class Status:

    def __init__(self, channel):
        stdout = channel.makefile('rb', -1)
        stderr = channel.makefile_stderr('rb', -1)
        self.stderr = ''.join(str(lines) for lines in stderr.readlines())
        self.stdout = stdout.read().decode()
        self.code = channel.recv_exit_status()

    def __str__(self):
        return self.stdout

    def __bool__(self):
        return self.code == 0


class Client:

    context = {}

    def __init__(self, hostname):
        config = SSHConfig()
        with (Path.home() / '.ssh/config').open() as fd:
            config.parse(fd)
        ssh_config = config.lookup(hostname)
        self.hostname = ssh_config['hostname']
        self.username = ssh_config.get('user', getuser())
        self._client = SSHClient()
        self._client.load_system_host_keys()
        self._client.set_missing_host_key_policy(WarningPolicy())
        self.open()

    def open(self):
        print(self.hostname, self.username)
        self._client.connect(hostname=self.hostname, username=self.username)
        self._transport = self._client.get_transport()

    def close(self):
        self.client.close()

    def execute(self, cmd):
        print(cmd)
        channel = self._transport.open_session()
        channel.exec_command(cmd)
        ret = Status(channel)
        channel.close()
        return ret


def init(host):
    global client
    client = Client(host)


def run(cmd):
    if client.context['sudo']:
        cmd = f'sudo {cmd}'
    return client.execute(cmd)


def exists(path):
    return bool(run(f'if [ -f "{path}" ]; then echo 1; fi').stdout)


def mkdir(path, parents=True, mode=None):
    p = '--parents' if parents else ''
    m = f'--mode {mode}' if mode else ''
    return run(f'mkdir {p} {m} {path}')


def ls(path):
    return run(f'ls -lisah {path}')


class sudo:

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __enter__(self, *args, **kwargs):
        client.context['sudo'] = self.kwargs

    def __exit__(self, type, value, traceback):
        del client.context['sudo']
