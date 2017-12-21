import inspect
import string
from contextlib import contextmanager
from getpass import getuser
from pathlib import Path

from paramiko.client import SSHClient, WarningPolicy
from paramiko.config import SSHConfig

client = None


def gray(s):
    return f'\x1b[1;30m{s}\x1b[0m'


class RemoteError(Exception):
    pass


class Formatter(string.Formatter):
    """
    Allow to have some custom formatting types.

    B: boolean attribute
    S: small boolean attribute
    V: k=v like attribute
    """

    def _vformat(self, format_string, args, kwargs, used_args, recursion_depth,
                 auto_arg_index=0):
        result = []
        for literal_text, name, spec, conversion in self.parse(format_string):

            # output the literal text
            if literal_text:
                result.append(literal_text)

            # if there's a field, output it
            if name:
                # given the name, find the object it references
                #  and the argument it came from
                obj, _ = self.get_field(name, args, kwargs)
                obj = self.convert_field(obj, conversion)

                value = ''
                if spec == 'B':
                    if obj:
                        value = '--' + name.replace('_', '-')
                elif spec == 'S':
                    if obj:
                        value = '-' + name[0]
                elif spec == 'V':
                    if obj:
                        value = '--' + name.replace('_', '-') + '=' + str(obj)
                else:
                    value = self.format_field(obj, spec)

                # format the object and append to the result
                result.append(value)

        return ''.join(result), auto_arg_index


def formattable(func):

    def wrapper(*args, **kwargs):
        spec = inspect.signature(func)
        for idx, (name, param) in enumerate(spec.parameters.items()):
            if idx < len(args):
                client.context[name] = args[idx]
            else:
                client.context[name] = kwargs.get(name, param.default)
        return func(*args, **kwargs)

    return wrapper


class Status:

    def __init__(self, channel):
        stdout = channel.makefile('rb', -1)
        stderr = channel.makefile_stderr('rb', -1)
        self.stderr = stderr.read().decode()
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
        parsed = self.parse_host(hostname)
        hostname = parsed.get('hostname')
        username = parsed.get('username')
        with (Path.home() / '.ssh/config').open() as fd:
            config.parse(fd)
        ssh_config = config.lookup(hostname)
        self.hostname = ssh_config['hostname']
        self.username = username or ssh_config.get('user', getuser())
        self._client = SSHClient()
        self._client.load_system_host_keys()
        self._client.set_missing_host_key_policy(WarningPolicy())
        self.open()
        self.formatter = Formatter()
        self.prefix = ''
        self.sudo = False
        self.cd = None
        self.env = {}

    def open(self):
        print(f'Connecting to {self.username}@{self.hostname}')
        self._client.connect(hostname=self.hostname, username=self.username)
        self._transport = self._client.get_transport()

    def close(self):
        self.client.close()

    def parse_host(self, host_string):
        user_hostport = host_string.rsplit('@', 1)
        hostport = user_hostport.pop()
        user = user_hostport[0] if user_hostport and user_hostport[0] else None

        # IPv6: can't reliably tell where addr ends and port begins, so don't
        # try (and don't bother adding special syntax either, user should avoid
        # this situation by using port=).
        if hostport.count(':') > 1:
            host = hostport
            port = None
        # IPv4: can split on ':' reliably.
        else:
            host_port = hostport.rsplit(':', 1)
            host = host_port.pop(0) or None
            port = host_port[0] if host_port and host_port[0] else None

        if port is not None:
            port = int(port)

        return {'username': user, 'hostname': host, 'port': port}

    def execute(self, cmd, **kwargs):
        channel = self._transport.open_session()
        prefix = self.prefix
        if self.cd:
            cmd = f'cd {self.cd}; {cmd}'
        if self.env:
            env = ' '.join(f'{k}={v}' for k, v in self.env.items())
            prefix = f'{prefix} {env}'
        cmd = self.format(prefix + " sh -c '" + cmd + "'")
        print(gray(cmd))
        channel.exec_command(cmd)
        ret = Status(channel)
        channel.close()
        if ret.code:
            raise RemoteError(ret.stderr)
        if ret.stdout:
            print(ret.stdout)
        return ret

    def format(self, tpl):
        return self.formatter.vformat(tpl, None, self.context)


def init(host):
    global client
    client = Client(host)


def run(cmd):
    return client.execute(cmd)


def exists(path):
    return bool(run(f'if [ -e "{path}" ]; then echo 1; fi').stdout)


@formattable
def mkdir(path, parents=True, mode=None):
    return run('mkdir {parents:B} {mode:V} {path}')


@formattable
def chown(mode, path, recursive=True, preserve_root=True):
    return run('chown {recursive:B} {mode} {path}')


@formattable
def ls(path, all=True, human_readable=True, size=True, list=True):
    return run('ls {all:B} {human_readable:B} {size:B} {list:S} {path}')


@contextmanager
@formattable
def sudo(set_home=True, preserve_env=True, user=None, login=True):
    prefix = 'sudo {set_home:B} {preserve_env:B} {user:V} {login:B}'
    if prefix not in client.prefix:
        client.prefix += prefix
        client.context.update({
            'set_home': set_home,
            'preserve_env': preserve_env,
            'user': user,
            'login': login
        })
    yield
    client.prefix.replace(prefix, '')


@contextmanager
def cd(path='~'):
    client.cd = path
    yield
    client.cd = None


@contextmanager
def env(**kwargs):
    client.env = kwargs
    yield
    client.env = {}
