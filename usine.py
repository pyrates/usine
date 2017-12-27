import inspect
import string
import sys
from contextlib import contextmanager
from io import StringIO
from getpass import getuser
from hashlib import md5
from pathlib import Path

from paramiko.client import SSHClient, WarningPolicy
from paramiko.config import SSHConfig
from progressist import ProgressBar
import yaml

client = None


def gray(s):
    return f'\x1b[1;30m{s}\x1b[0m'


def red(s):
    return f'\x1b[1;41m{s}\x1b[0m'


class RemoteError(Exception):
    pass


class Config:

    def __init__(self, value=None):
        if isinstance(value, Config):
            value = value.value
        super().__setattr__('value', value or {})

    def get(self, key, default=None):
        try:
            return Config(self.value.get(key, default))
        except AttributeError:
            return Config(default)

    def __getitem__(self, key):
        return self.__getattr__(key)

    def __getattr__(self, key):
        try:
            return Config(self.value.get(key))
        except AttributeError:
            return Config()

    def __setattr__(self, key, value):
        self.value[key] = value

    def __str__(self):
        return str(self.value)

    def __eq__(self, other):
        return other == self.value

    # https://eev.ee/blog/2012/03/24/python-faq-equality/
    # No way to override "is" behaviour, so no way to do "config.key is None"…
    def __bool__(self):
        return bool(self.value)

    def __hash__(self):
        return hash(self.value)

    def __iter__(self):
        return iter(self.value)

    def items(self):
        return self.value.items()

    def update(self, other):
        self.value.update(other)


config = Config()  # singleton.


class Template(string.Template):
    # Default delimiter ($) clashes at least with Nginx DSL.
    delimiter = '$$'


def template(path, **context):
    with Path(path).open() as f:
        template = Template(f.read())
        return StringIO(template.substitute(**context))


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
                if spec == 'bool':
                    if obj:
                        value = '--' + name.replace('_', '-')
                elif spec == 'initial':
                    if obj:
                        value = '-' + name[0]
                elif spec == 'equal':
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

    def __init__(self, stdout, stderr, exit_status):
        self.stderr = stderr.read().decode()
        self.stdout = stdout.read().decode()
        self.code = exit_status

    def __str__(self):
        return self.stdout

    def __bool__(self):
        return self.code == 0


class Client:

    context = {}

    def __init__(self, hostname, configpath=None):
        ssh_config = SSHConfig()
        parsed = self.parse_host(hostname)
        hostname = parsed.get('hostname')
        username = parsed.get('username')
        if configpath:
            with Path(configpath).open() as fd:
                yaml_conf = yaml.load(fd)
                if hostname in yaml_conf:
                    yaml_conf.update(yaml_conf[hostname])
                config.update(yaml_conf)
        with (Path.home() / '.ssh/config').open() as fd:
            ssh_config.parse(fd)
        ssh_config = ssh_config.lookup(hostname)
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
        self._sftp = None

    def open(self):
        print(f'Connecting to {self.username}@{self.hostname}')
        self._client.connect(hostname=self.hostname, username=self.username)
        self._transport = self._client.get_transport()

    def close(self):
        self._client.close()

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
        stdout = channel.makefile('r', -1)
        stderr = channel.makefile_stderr('r', -1)
        buf = b''
        while True:
            data = stdout.read(1)
            if not data:
                if buf:
                    sys.stdout.write(buf.decode())
                break
            buf += data
            if buf.endswith(b'\n'):
                sys.stdout.write(buf.decode())
                buf = b''
        ret = Status(stdout, stderr, channel.recv_exit_status())
        channel.close()
        if ret.code:
            red(ret.stderr)
            sys.exit(ret.code)
        return ret

    def format(self, tpl):
        return self.formatter.vformat(tpl, None, self.context)

    @property
    def sftp(self):
        if not self._sftp:
            self._sftp = self._client.open_sftp()
        return self._sftp


@contextmanager
def connect(*args, **kwargs):
    global client
    client = Client(*args, **kwargs)
    yield client
    client.close()


def run(cmd):
    return client.execute(cmd)


def exists(path):
    return bool(run(f'if [ -e "{path}" ]; then echo 1; fi').stdout)


@formattable
def mkdir(path, parents=True, mode=None):
    return run('mkdir {parents:bool} {mode:equal} {path}')


@formattable
def chown(mode, path, recursive=True, preserve_root=True):
    return run('chown {recursive:bool} {mode} {path}')


@formattable
def ls(path, all=True, human_readable=True, size=True, list=True):
    return run('ls {all:bool} {human_readable:bool} {size:bool} {list:initial}'
               ' {path}')


def mv(src, dest):
    return run(f'mv {src} {dest}')


def put(local, remote, owner=None):
    bar = ProgressBar(prefix=f'{local} => {remote}')
    tmp = str(Path('/tmp') / md5(remote.encode()).hexdigest())
    func = client.sftp.putfo if hasattr(local, 'read') else client.sftp.put
    func(local, tmp, lambda done, total: bar.update(done=done, total=total))
    mv(tmp, remote)
    if owner:
        chown(owner, remote)


def get(remote, local):
    bar = ProgressBar(prefix=f'{remote} => {local}')
    func = client.sftp.getfo if hasattr(local, 'write') else client.sftp.get
    func(remote, local, lambda done, total: bar.update(done=done, total=total))


@contextmanager
@formattable
def sudo(set_home=True, preserve_env=True, user=None, login=None):
    prefix = ('sudo {set_home:bool} {preserve_env:bool} {user:equal} '
              '{login:bool}')
    if login is None:
        login = user is not None
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
