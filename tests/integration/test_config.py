from usine import Config


def test_config_should_proxy_dict():
    config = Config({'key': 'value', 'other': {'sub': 'subvalue'}})
    assert config.key == 'value'
    assert config['key'] == 'value'
    assert config.get('key') == 'value'
    assert config.get('missing', 'default') == 'default'
    assert config.other.sub == 'subvalue'


def test_config_should_swallow_missing_keys():
    config = Config()
    assert not config
    assert not config.missing
    assert not config.missing.again


def test_config_setattr():
    config = Config()
    config.foo = 'bar'
    assert config.foo == 'bar'


def test_config_str():
    config = Config()
    config.foo = 'bar'
    assert f'foo{config.foo}baz' == 'foobarbaz'


def test_config_as_kwargs():
    config = Config()
    config.foo = 'bar'

    def foo(**kwargs):
        return kwargs

    assert foo(**config) == config
