import inspect
import os
import select
import string
import sys
import termios
import tty
import time
from contextlib import contextmanager
from getpass import getuser
from hashlib import md5
from io import BytesIO, StringIO
from pathlib import Path

import paramiko
import yaml
from paramiko.client import SSHClient, WarningPolicy
from paramiko.config import SSHConfig
from progressist import ProgressBar

client = None


@contextmanager
def character_buffered():
    """
    Force local terminal ``sys.stdin`` be character, not line, buffered.
    C/P from Invoke.
    """
    if not sys.stdin.isatty():  # w/ pytest?
        yield
        return
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin)
    try:
        yield
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def gray(s):
    return f'\x1b[1;30m{s}\x1b[0m'


def red(s):
    return f'\x1b[1;41m{s}\x1b[0m'


class RemoteError(Exception):
    pass


class Config(dict):

    def __getattr__(self, key):
        value = self.get(key)
        # Allow to chain getattr (eg. config.foo.bar)
        if isinstance(value, dict):
            value = Config(value)
        return value

    def __setattr__(self, key, value):
        self[key] = value


config = Config()  # singleton.


class Template(string.Template):
    # Default delimiter ($) clashes at least with Nginx DSL.
    delimiter = '$$'


def template(source, **context):
    if hasattr(source, 'read'):
        template = Template(source.read())
    else:
        with Path(source).open() as f:
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
        old_context = client.context.copy()
        for idx, (name, param) in enumerate(spec.parameters.items()):
            if idx < len(args):
                client.context[name] = args[idx]
            else:
                client.context[name] = kwargs.get(name, param.default)
        res = func(*args, **kwargs)
        client.context = old_context
        return res

    return wrapper


class Status:

    def __init__(self, stdout, stderr, exit_status):
        self.stderr = stderr
        self.stdout = stdout
        self.code = exit_status

    def __contains__(self, other):
        return other in self.stdout

    def __str__(self):
        return self.stdout

    def __bool__(self):
        return self.code == 0


class Client:

    context = {}

    def __init__(self, hostname, configpath=None, dry_run=False):
        ssh_config = SSHConfig()
        if not hostname:
            print(red('"hostname" must be defined'))
            sys.exit(1)
        parsed = self.parse_host(hostname)
        hostname = parsed.get('hostname')
        username = parsed.get('username')
        if configpath:
            if not isinstance(configpath, (list, tuple)):
                configpath = [configpath]
            for path in configpath:
                self._load_config(path, hostname)
        with (Path.home() / '.ssh/config').open() as fd:
            ssh_config.parse(fd)
        ssh_config = ssh_config.lookup(hostname)
        self.dry_run = dry_run
        self.hostname = config.hostname or ssh_config['hostname']
        self.username = (username or config.username
                         or ssh_config.get('user', getuser()))
        self.formatter = Formatter()
        self.sudo = ''
        self.cd = None
        self.screen = None
        self.env = {}
        self._sftp = None
        self.proxy_command = ssh_config.get('proxycommand',
                                            config.proxy_command)
        self.open()

    def open(self):
        self._client = SSHClient()
        self._client.load_system_host_keys()
        self._client.set_missing_host_key_policy(WarningPolicy())
        print(f'Connecting to {self.username}@{self.hostname}')
        if self.proxy_command:
            print('ProxyCommand:', self.proxy_command)
        sock = (paramiko.ProxyCommand(self.proxy_command)
                if self.proxy_command else None)
        try:
            self._client.connect(hostname=self.hostname,
                                 username=self.username, sock=sock)
        except paramiko.ssh_exception.BadHostKeyException:
            sys.exit('Connection error: bad host key')
        self._transport = self._client.get_transport()

    def close(self):
        print(f'\nDisconnecting from {self.username}@{self.hostname}')
        self._client.close()

    def _load_config(self, path, hostname):
        with Path(path).open() as fd:
            conf = yaml.load(fd)
            if hostname in conf:
                conf.update(conf[hostname])
            config.update(conf)

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

    def _build_command(self, cmd, **kwargs):
        prefix = ''
        if self.cd:
            cmd = f'cd {self.cd}; {cmd}'
        if self.env:
            prefix = ' '.join(f'{k}={v}' for k, v in self.env.items())
        if self.sudo:
            prefix = f'{self.sudo} {prefix}'
        cmd = self.format(f"{prefix} sh -c $'{cmd}'")
        if self.screen:
            cmd = f'screen -UD -RR -S {self.screen} {cmd}'
        return cmd.strip().replace('  ',  ' ')

    def _call_command(self, cmd, **kwargs):
        channel = self._transport.open_session()
        try:
            size = os.get_terminal_size()
        except IOError:
            channel.get_pty()  # Fails when ran from pytest.
        else:
            channel.get_pty(width=size.columns, height=size.lines)
        channel.exec_command(cmd)
        channel.setblocking(False)  # Allow to read from empty buffer.
        stdout = channel.makefile('r', -1)
        stderr = channel.makefile_stderr('r', -1)
        proxy_stdout = b''
        buf = b''
        while True:
            while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                # TODO compute bytes_to_read like in invoke?
                data = sys.stdin.read(1)
                if data:
                    channel.sendall(data)
                else:
                    break
            if not channel.recv_ready():
                if buf:  # We may have read some buffer yet, let's output it.
                    sys.stdout.write(buf.decode())
                    sys.stdout.flush()
                    buf = b''
                if channel.exit_status_ready():
                    break
                continue
            try:
                data = stdout.read(1)
            except Exception:  # Not sure how to catch socket.timeout properly.
                pass
            else:
                proxy_stdout += data
                buf += data
                if data == b'\n':
                    sys.stdout.write(buf.decode())
                    sys.stdout.flush()
                    buf = b''
                continue
            time.sleep(paramiko.io_sleep)
        channel.setblocking(True)  # Make sure we now wait for stderr.
        ret = Status(proxy_stdout.decode(), stderr.read().decode().strip(),
                     channel.recv_exit_status())
        channel.close()
        if ret.code:
            print(red(ret.stderr))
            sys.exit(ret.code)
        return ret

    def __call__(self, cmd, **kwargs):
        cmd = self._build_command(cmd, **kwargs)
        print(gray(cmd))
        if self.dry_run:
            return Status('¡DRY RUN!', '¡DRY RUN!', 0)
        with character_buffered():
            return self._call_command(cmd, **kwargs)

    def format(self, tpl):
        try:
            return self.formatter.vformat(tpl, None, self.context)
        except KeyError as e:
            print(red(f'Missing key {e}'))
            sys.exit(1)

    @property
    def sftp(self):
        if not self._sftp:
            self._sftp = self._client.open_sftp()
        return self._sftp


@contextmanager
def connect(*args, **kwargs):
    enter(*args, **kwargs)
    yield client
    exit()


def enter(*args, **kwargs):
    global client
    klass = kwargs.pop('client', Client)
    client = klass(*args, **kwargs)


def exit():
    client.close()


def run(cmd):
    return client(cmd)


def exists(path):
    try:
        run(f'test -e {path}')
    except SystemExit:
        return False
    return not client.dry_run


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


@formattable
def cp(src, dest, interactive=False, recursive=True, link=False, update=False):
    return run('cp {interactive:bool} {recursive:bool} {link:bool} '
               '{update:bool} {src} {dest}')


def put(local, remote, force=False):
    user = client.context.get('user')
    if client.cd:
        remote = Path(client.cd) / remote
    if not hasattr(local, 'read'):
        local = Path(local)
        if local.is_dir():
            with sudo():  # Force reset to SSH user.
                mkdir(remote)
                if user:
                    chown(user, remote)
            for path in local.rglob('*'):
                relative_path = path.relative_to(local)
                put(path, remote / relative_path)
            return
        if not force and exists(remote):
            lstat = os.stat(str(local))
            rstat = client.sftp.stat(str(remote))
            if (lstat.st_size == rstat.st_size
               and lstat.st_mtime <= rstat.st_mtime):
                print(f'{local} => {remote}: SKIPPING (reason: up to date)')
                return
    elif isinstance(local, StringIO):
        local = BytesIO(local.read().encode())
    if hasattr(local, 'read'):
        func = client.sftp.putfo
        bar = ProgressBar(prefix=f'Sending to {remote}', animation='{spinner}',
                          template='{prefix} {animation} {done:B}')
    else:
        bar = ProgressBar(prefix=f'{local} => {remote}')
        func = client.sftp.put
    if client.dry_run:
        print(bar.prefix)
        return
    tmp = str(Path('/tmp') / md5(str(remote).encode()).hexdigest())
    try:
        func(local, tmp,
             callback=lambda done, total: bar.update(done=done, total=total),
             confirm=True)
    except OSError as err:
        print(red(f'Error while processing {remote}'))
        print(red(err))
        sys.exit(1)
    if hasattr(local, 'read'):
        bar.finish()
    with sudo():  # Force reset to SSH user.
        mv(tmp, remote)
        if user:
            chown(user, remote)


def get(remote, local):
    if client.cd:
        remote = Path(client.cd) / remote
    if hasattr(local, 'read'):
        func = client.sftp.getfo
        bar = ProgressBar(prefix=f'Reading from {remote}',
                          animation='{spinner}',
                          template='{prefix} {animation} {done:B}')
    else:
        bar = ProgressBar(prefix=f'{remote} => {local}',
                          template='{prefix} {animation} {percent} '
                                   '({done:B}/{total:B}) ETA: {eta}')
        func = client.sftp.get
    func(str(remote), local,
         callback=lambda done, total: bar.update(done=done, total=total))
    if hasattr(local, 'read'):
        local.seek(0)
        bar.finish()


@contextmanager
def sudo(set_home=True, preserve_env=True, user=None, login=None):
    prefix = ('sudo {set_home:bool} {preserve_env:bool} {user:equal} '
              '{login:bool}')
    if login is None:
        login = user is not None
    previous = client.sudo
    previous_context = client.context.copy()
    client.context.update({
        'set_home': set_home,
        'preserve_env': preserve_env,
        'user': user,
        'login': login
    })
    client.sudo = prefix
    yield
    client.sudo = previous
    client.context = previous_context


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


@contextmanager
def screen(name='usine'):
    client.screen = name
    yield
    client.screen = None
