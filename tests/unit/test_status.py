from usine import Status


def test_str():
    status = Status('stdout', 'stderr', 0)
    assert str(status) == 'stdout'


def test_contains():
    status = Status('stdout foo', 'stderr', 0)
    assert 'foo' in status


def test_boolean():
    status = Status('stdout', 'stderr', 0)
    if not status:
        raise AssertionError('Status is falsy')
    status = Status('stdout', 'stderr', 1)
    if status:
        raise AssertionError('Status is truthy')
