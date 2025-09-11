"""Unit tests"""
from configparser import ConfigParser
from client import parse_config
from webapp import NotifyPayload


def test_payload():
    """Payload construction"""
    p = NotifyPayload.construct({
        'token': 'token',
        'hostname': "hostname",
        'join_ip': 'join_ip',
        'num_players': 1,
        'max_players': 2,
        'player_name': 'player_name'
    })
    assert p.token == 'token'
    assert p.hostname == 'hostname'
    assert p.ip == 'join_ip'
    assert p.num_players == 1
    assert p.max_players == 2
    assert p.player_name == 'player_name'


def test_parse_config():
    """Parse config"""
    prsr = ConfigParser()
    prsr.read_string("""
[discord]
token=token
channel=1
ping_role=2

[server]
cert=cert
key=key
port=3000
test_get=
test_post=
""")

    config = parse_config(prsr)

    assert config.discord_token == 'token'
    assert config.channel_id == 1
    assert config.ping_role == 2
    assert config.cert_path == 'cert'
    assert config.key_path == 'key'
    assert config.port == 3000
    assert config.test_post is False
    assert config.test_get is False
