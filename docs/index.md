Usine is a minimalist and pythonnic deployment tool.

It that tries to do as little as possible for you not
to stay on your way.


## What it does

- manages SSH connection (with [paramiko](http://paramiko.org/))
- manages configuration files
- allows you to run commands in a remote server
- wraps some common commands for a more pythonnic API (and thus ease the use of
  `*args` and `**kwargs` patterns)
- exposes some pythonic helpers to manage env vars, sudo and such


## Example

Here is what a very basic script would look like:

```python
from usine import run, connect

with connect(hostname='me@remote'):
    run('ls /tmp/foobar')
```

## When to use it

When you have a few servers to maintain and you want to be sure every
needed command is documented and reproductible by you and your comates.


## When not to use it

When you want a generic deployment script that would run from any device to
any OS with a lot of configuration options.

## Why another deployment tool?

We used to use [Fabric](http://fabfile.org/) a lot. But it tooks age for it to
be python 3 ready, and this is where we started working on Usine. Eventually
Fabric 2 was released, but the API changed and was lacking its original simplicity
(`ctx` everywhere, no more context managers, code more complexe with `Invoke`
integration…), so we decided to continue working with Usine, and eventually
release it and document it.


## More:

- [reference](reference.md)
- [how-to guides](how-to.md)
