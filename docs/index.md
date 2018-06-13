Usine is a minimalist and pythonic remote automation tool.

It will do as little as possible not to be in the way.


## What it does

- manage SSH connection (with [paramiko](http://paramiko.org/))
- manage configuration files
- allow you to run commands in a remote server
- wrap some common commands for a more pythonic API (and thus ease the use of
  `*args` and `**kwargs` patterns)
- expose some pythonic helpers to manage env vars, sudo and such


## Install


    pip install usine


## Example

Here is what a very basic script would look like:

```python
from usine import run, connect

with connect(hostname='me@remote'):
    run('ls /tmp/foobar')
```

## When to use it?

When you have a few servers to maintain and you want to be sure every
command needed is documented and reproducible by you and your comates.


## When not to use it?

When you want a generic deployment script that would run from any device to
any OS with a lot of configuration options.

## Why another deployment tool?

We used to use [Fabric](http://fabfile.org/) a lot. But it took ages to
be python 3 ready, and this is where we started working on Usine. Eventually
Fabric 2 was released, but the API changed and was lacking its original simplicity
(`ctx` everywhere, no more context managers, code more complex with `Invoke`
integration…), so we decided to continue working with Usine, and eventually
release it and document it.


## More:

- [reference](reference.md)
- [how-to guides](how-to.md)
