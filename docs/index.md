Usine is a deployement tool that tries to make as little as possible for you not
to stay on your way.

Basically it's just plain command wrapped into python functions. No DSL.


Here is what a very basic script would look like:

```python
from usine import run, connect

with connect(hostname='me@remote'):
    run('ls /tmp/foobar')
```
