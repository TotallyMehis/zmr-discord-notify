'''Integration tests'''
from pathlib import Path
import socket
import asyncio
import os
import aiohttp
from pytest import fixture, TempPathFactory
from webapp import NotifyPayload, NotifyWebApp
from client import _get_valid_tokens


def test_webapp_ok():
    """Webapp responds with success."""
    port = _get_random_port()

    async def _test_cb(_):
        return True
    web_app = NotifyWebApp(_test_cb)

    async def run_co(json: dict):
        try:
            await web_app.start(port)

            async with aiohttp.ClientSession() as session:
                async with session.post(f'http://127.0.0.1:{port}', json=json) as response:
                    return await response.json()
        finally:
            await web_app.stop()

    result = asyncio.run(run_co({
        'token': 'token',
        'hostname': 'hostname',
        'join_ip': 'join_ip',
        'num_players': 1,
        'max_players': 2,
        'player_name': 'player_name'
    }))
    assert result['success'] is True


def test_webapp_fail():
    """Webapp responds with failure."""
    port = _get_random_port()

    async def _test_cb(_):
        return False
    web_app = NotifyWebApp(_test_cb)

    async def run_co(json: dict):
        try:
            await web_app.start(port)

            async with aiohttp.ClientSession() as session:
                async with session.post(f'http://127.0.0.1:{port}', json=json) as response:
                    return await response.json()
        finally:
            await web_app.stop()

    result = asyncio.run(run_co({
        'token': 'token',
        'hostname': 'hostname',
        'join_ip': 'join_ip',
        'num_players': 1,
        'max_players': 2,
        'player_name': 'player_name'
    }))
    assert result['success'] is False


def test_webapp_payload():
    """Webapp parses payload correctly."""
    port = _get_random_port()

    async def _test_cb(payload: NotifyPayload):
        assert payload.token == 'token'
        assert payload.hostname == 'hostname'
        assert payload.ip == 'join_ip'
        assert payload.num_players == 1
        assert payload.max_players == 2
        assert payload.player_name == 'player_name'
        return True
    web_app = NotifyWebApp(_test_cb)

    async def run_co(json: dict):
        try:
            await web_app.start(port)

            async with aiohttp.ClientSession() as session:
                async with session.post(f'http://127.0.0.1:{port}', json=json) as response:
                    return await response.json()
        finally:
            await web_app.stop()

    result = asyncio.run(run_co({
        'token': 'token',
        'hostname': 'hostname',
        'join_ip': 'join_ip',
        'num_players': 1,
        'max_players': 2,
        'player_name': 'player_name'
    }))
    assert result['success'] is True


def test_tokens(temp_dir: Path):
    """Read tokens from file."""
    filename = os.path.join(temp_dir, 'tokens.txt')
    with open(filename, 'w', encoding='utf-8') as fp:
        fp.write("""
; Comment
token1
token2 ; Inline comment
 token3

""")

    tokens = _get_valid_tokens(filename)

    assert len(tokens) == 3
    assert tokens[0] == 'token1'
    assert tokens[1] == 'token2'
    assert tokens[2] == 'token3'


def _get_random_port():
    port = 0
    sckt = socket.socket()
    try:
        sckt.bind(('127.0.0.1', 0))
        port = int(sckt.getsockname()[1])
    finally:
        sckt.close()
    return port


@fixture(name='temp_dir', scope='function')
def _temp_dir_fixture(tmp_path_factory: TempPathFactory):
    return tmp_path_factory.mktemp('discordnotify_test')
