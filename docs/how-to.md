# How-to guides

## How to run a command with sudo

Use the `sudo` context manager.

```python
from usine import run, sudo

with sudo():
    run('apt install foo')
```


## How to pass environment variables

Use the `env` context manager.

```python
from usine import run, env

with env(SOMETHING='foo'):
    run('echo $SOMETHING')
    # 'foo'
```

# How to integrate with minicli

Usine focuses on managing the remote actions, and thus does not include any
command line tool.

It can be integrated with any tool (`argparse`, `click`…), here we'll cover
the integration with [minicli](http://minicli.readthedocs.io/en/latest/) as this
is the tool we use ourselves.

Here is a basic example:

```python
# myscript.py
from usine import run, connect
import minicli


@minicli.cli
def mycommand(arg1, force=False):
    dosomething()

if __name__ == '__main__':
    with connect(hostname='myhost'):
        minici.run()
```

And now you can run it like this:

    myscript.py mycommand --force

If you want to expose the hostname in the command line (or any other global
variable like the `configpath`), here is a more complete example:


```python
# myscript.py
from usine import run, connect
import minicli


@minicli.cli
def mycommand(arg1, force=False):
    dosomething()


@minicli.wrap
def wrapper(hostname, configpath)
    with connect(hostname=hostname, configpath=configpath):
        yield  # This will make minicli run.


if __name__ == '__main__':
    minici.run(hostname='default', configpath='config/default.yml')
```

And you can run it like this:

    myscript.py mycommand --force --hostname production


# How to use proxy command

You can define a SSH proxy command through the config:

```yml
proxy_command: ssh -q user@bastion -W remote_host:22
username: remote_user
hostname: remote_host
```

This will connect to `remote_host` through `bastion` host.
Note: when using `proxy_command`, `username` and `hostname` should reflect the
host and user of the target machine (not the proxy server).
