# Classes


## Client

The `Client` class is the Usine orchestrator. You generally should not interact
directly with it.

### Constructor arguments

- **hostname**: a `str` representing the host to connect to. It can be a domain,
  an IP address, an SSH host, a `user@host` string…
- **configpath**: a filepath (or list of filepaths) to yaml config file(s) to
  be loaded.


## Config

The `Config` class is a key/value proxy. You'll generally use it through the
`config` singleton.

You can access config properties with the dot syntax:

```python
from usine import config

print(config.property)
```


## Status

A command status. You can print it to get the command output or test it
in a boolean context to check its exit code.

```python
from usine import run

status = run('createuser bob')
if not status:
    do_something()
```


# Connection helpers


## enter

Create the `client` singleton, which will initiate the SSH connection.

It takes the same arguments as the `Client`, plus an optional `client` kwarg
that you can use to define the `Client` class to be instantiated.


## exit

Close the SSH connection.


## connect

`connect` is a contextmanager that will call `enter` and `exit` for you.

```
from usine import connect

with connect(hostname='me@remote'):
    run('something')
```


# Command helpers


## run(cmd)

This is the main helper, which basically runs any command on the remote server.

##### Arguments

- **cmd**: the actual command to be run

Return a `Status` instance.


## exists(path)

Check if a path (file or directory) exists on the remote server.

##### Arguments

- **path**: the path to check


## mkdir(path, parents=True, mode=None)

Run `mkdir` command on the remote server to create a directory. See `man mkdir`
for more info about the command.

##### Arguments:

- **path**: the path of the directory
- **parents** (default: `True`): also create parents directory if needed and do
  not raise if the directory already exists.
- **mode**: optional file mode


## chown(mode, path, recursive=True, preserve_root=True)

Run `chown` command in the remote server to change file or directory ownership.
See `man chown` for more info.

##### Arguments

- **mode**: `user:group` to change the ownership to
- **path**: the path of the file or directory
- **recursive** (default: `True`): operate on files and directories recursively


## ls(path, all=True, human_readable=True, size=True, list=True)

Run `ls` command on the remote server.


##### Arguments

- **path**: the path of the file or directory to consider
- **all** (default: `True`): do not ignore entries starting with `.`
- **human_readable** (default: `True`): print sizes in a humand readable format
- **size** (default: `True`): also print size
- **list** (default: `True`): use a long listing format


## mv(src, dest)

Run the `mv` command on the remote server.

##### Arguments

- **srv**: the path for the source
- **dest**: the path of the destination


## cp(src, dest, interactive=False, recursive=True, link=False, update=False)

Run the `cp` command on the remote server.

##### Arguments

- **src**: the path for the source
- **dest**: the path of the destination
- **interactive** (default: `False`): prompt before overwrite
- **recursive** (default: `True`): copy directories recursively
- **link** (default: `False`): hard link files instead of copying
- **update** (default: `False`): copy only when the SOURCE file is newer than the
  destination file or when the destination file is missing


# File helpers


## put(local, remote, force=False)

Send a local file or directory to the remote server.

##### Arguments

- **local**: a reference to a file (can be a `pathlib.Path` instance, a `str`
  or a `io.BytesIO` instance) or to a directory (`pathlib.Path` or `str`)
- **remote**: the remote path
- **force** (default: `False`): override remote file even if it's newer


## get(remote, local)

Fetch a remote file.

##### Arguments

- **local**: a reference to a file (can be a `pathlib.Path` instance, a `str`
  or a `io.BytesIO` instance)
- **remote**: the remote path


# Context managers


## sudo(set_home=True, preserve_env=True, user=None, login=None)

Run the command in a `sudo` context. See `man sudo` for more info about using
`sudo`.

##### Arguments

- **set_home** (default: `True`): request that the security policy set the HOME
  environment variable to the home directory specified by the target user's
  password database entry
- **preserve_env** (default: `True`): preserve environment variable
- **user** (default: `None`): run the command as this user
- **login** (default: `None`): run the shell specified by the target user's
  password database entry as a login shell


## cd(path)

Prefix all path to be run in command with this path.

##### Arguments

- **path** (default: `~`): the path to use as prefix


## env(**kwargs)

Define environment variables.

##### Arguments

- **kwargs**: key/value pair to set environment variables


## screen(name)

Run the command inside a screen.

##### Arguments

- **name** (default: `usine`) the name of the screen to be created
