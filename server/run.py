"""Run this."""
from configparser import ConfigParser
import logging
import sys
from os import path
import discord
from client import NotifyClient, parse_config

LOG_FORMAT = '[%(asctime)s] [%(levelname)s] [%(threadName)s] %(name)s: %(message)s'


logger = logging.getLogger(__name__)


def _main():
    # Read our config
    parser = ConfigParser()
    with open(path.join(path.dirname(__file__), '.config.ini'), encoding='utf-8') as fp:
        parser.read_file(fp)

    # Init logger
    log_level_str = parser.get(
        'server', 'logging', fallback='').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logging.basicConfig(level=log_level, format=LOG_FORMAT)

    config = parse_config(parser)

    client = NotifyClient(config)
    try:
        client.run(config.discord_token, log_handler=None)
    except discord.LoginFailure as e:
        logger.error(
            'Failed to log in! Make sure your token is correct! Exception: %s', e)
        sys.exit(2)
    except:  # pylint: disable=W0702
        logger.error('Discord bot ended unexpectedly.', exc_info=True)
        sys.exit(1)

    if client.exitcode > 0:
        sys.exit(client.exitcode)


if __name__ == '__main__':
    _main()
