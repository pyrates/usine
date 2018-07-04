from usine import connect, config, run


def test_proxy_command():
    config.proxy_command = 'ssh -q usine -W 127.0.0.1:22'
    with connect(hostname='ubuntu@127.0.0.1'):
        assert 'ubuntu' in run('whoami')
