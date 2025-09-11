"""Notification aiohttp web application."""
import logging
from dataclasses import dataclass
from ssl import SSLContext
from collections.abc import Callable
from typing import Awaitable
from aiohttp import web

logger = logging.getLogger(__name__)


@dataclass
class NotifyPayload:
    """Payload from server."""
    token: str = ''
    hostname: str = ''
    ip: str = ''
    num_players: int = 0
    max_players: int = 0
    player_name: str = ''

    @staticmethod
    def construct(data: dict):
        """Construct from JSON object."""
        return NotifyPayload(token=str(data['token']),
                             hostname=str(data['hostname']),
                             ip=data['join_ip'],
                             num_players=int(data['num_players']),
                             max_players=int(data['max_players']),
                             player_name=str(data['player_name']))


class NotifyWebApp():
    """Web application"""

    def __init__(self, callback: Callable[[NotifyPayload], Awaitable[bool]], register_get=False):
        self.callback = callback
        self._webapp = web.Application()
        self._webapp.router.add_post('/', self._handle_webrequest)
        if register_get:
            self._webapp.router.add_get('/', self._handle_webrequest_test_get)
            logger.info('Added test GET handler.')
        self._site: web.TCPSite | None = None

    async def start(self, port: int, ssl_context: SSLContext | None = None):
        """Start the web application."""
        await self._init_webapp(port, ssl_context)

    async def stop(self):
        """Stop the web application."""
        await self._site.stop()

    async def _handle_webrequest(self, request: web.Request):
        """Handles the POST request from game servers."""
        data = None
        try:
            d = await request.json()
            logger.debug('Received valid JSON:')
            logger.debug('%s', d)
            data = NotifyPayload.construct(d)
        except Exception as e:  # pylint: disable=W0718
            logger.error(
                'Error occurred when parsing json from request: %s', e)
            try:
                body = await request.text()
                logger.error('Body: %s', body)
            except:  # pylint: disable=W0702
                pass

        if data is None:
            return _send_response(False)

        success = False
        try:
            success = await self.callback(data)
        except:  # pylint: disable=W0702
            logger.error('Failed to process request?', exc_info=True)
        return _send_response(success)

    async def _handle_webrequest_test_get(self, _: web.Request):
        logger.info('Received test GET request!')
        return web.json_response({'message': 'Hello!'})

    async def _init_webapp(self, port: int, ssl_context: SSLContext):
        """Init web app"""
        try:
            logger.info('Initializing HTTP server...')

            runner = web.AppRunner(self._webapp)
            await runner.setup()
            self._site = web.TCPSite(
                runner, port=port, ssl_context=ssl_context)
            await self._site.start()
        except Exception as e:  # pylint: disable=W0718
            logger.error('Error initializing web server: %s', e)
        else:
            logger.info('Started HTTP server on port %d.', port)


def _send_response(success: bool) -> web.Response:
    status = 200 if success else 400
    data = {'success': success}
    return web.json_response(data, status=status)
