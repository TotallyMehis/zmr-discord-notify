"""Discord notification bot client. Discord users can add a 'Looking to Play'-role to get pinged."""
from dataclasses import dataclass
import logging
import ssl
from configparser import ConfigParser
from os import path
import discord
from webapp import NotifyPayload, NotifyWebApp

logger = logging.getLogger(__name__)


@dataclass
class NotifyConfig():
    """Notification bot config"""
    discord_token: str = ''
    ping_role: int = 0
    channel_id: int = 0
    port: int = 0
    cert_path: str = ''
    key_path: str = ''
    test_get: bool = False
    test_post: bool = False


class NotifyClient(discord.Client):
    """The notifying bot :)"""

    def __init__(self, config: NotifyConfig):
        intents = discord.Intents.none()
        intents.dm_messages = True  # Respond to DMs.
        intents.guilds = True  # Find the channel.
        intents.guild_messages = True  # Respond to guild messages & to ping.
        intents.members = True  # So we can add roles.
        intents.message_content = True  # Read messages.
        super().__init__(intents=intents)
        self._init_done = False
        self.exitcode = 0
        self._my_channel: discord.TextChannel | None = None
        self._my_guild: discord.Guild | None = None
        self._my_ping_role: discord.Role | None = None
        self._config = config

        self._valid_tokens = _get_valid_tokens(
            path.join(path.dirname(__file__), '.tokens.txt'))
        assert self._valid_tokens, 'You must insert tokens in .tokens.txt file!'

        logger.info('Loaded %d tokens.', len(self._valid_tokens))
        for token in self._valid_tokens:
            logger.debug('"%s"', token)

        self._webapp = NotifyWebApp(self._on_notify, self._config.test_get)

    async def setup_hook(self):
        sslcontext = None
        if self._config.cert_path or self._config.key_path:
            sslcontext = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            sslcontext.load_cert_chain(
                self._config.cert_path, self._config.key_path)
        else:
            logger.info('NOT USING SSL')
        await self._webapp.start(self._config.port, sslcontext)

    async def on_ready(self):
        """Init"""
        logger.info('Logged on as %s', self.user)

        chnl = self.get_channel(self._config.channel_id)
        if chnl is None:
            logger.error('Channel with id %d does not exist!',
                         self._config.channel_id)
            self.exitcode = 1
            await self.close()
            return
        if not isinstance(chnl, discord.TextChannel):
            logger.error('Channel %d must be a text channel!',
                         self._config.channel_id)
            self.exitcode = 1
            await self.close()
            return

        self._my_channel = chnl
        self._my_guild = self._my_channel.guild
        self._my_ping_role = self._my_channel.guild.get_role(
            self._config.ping_role)
        if self._my_ping_role is None:
            logger.error('Role with id %d does not exist!',
                         self._config.ping_role)
            self.exitcode = 1
            await self.close()
            return

        self._init_done = True

    async def on_message(self, message: discord.Message):
        """Listen for add/remove role commands."""
        if not self.is_ready() or not self._init_done:
            logger.debug('Received message but bot is not ready yet.')
            return
        if not message.content or message.content[0] != '!':
            return
        if message.author.id == self.user.id:
            return
        # Only either in my channel or DM
        if (message.channel.id != self._config.channel_id and
                not isinstance(message.channel, discord.DMChannel)):
            return
        # Not a member of my server
        assert self._my_guild
        member = self._my_guild.get_member(message.author.id)
        if member is None:
            return

        command = message.content[1:]
        if command == 'add':
            await self._add_ping_role(member, message.channel)
        if command == 'remove':
            await self._remove_ping_role(member, message.channel)

    async def _on_notify(self, data: NotifyPayload):
        if not self.is_ready() or not self._init_done:
            logger.error(
                'Received a POST request while Discord bot is not ready!')
            return False

        if self._config.test_post:
            logger.info('Testing POST. Not sending a mention.')
            return True

        assert self._my_ping_role and self._my_channel
        assert data.token in self._valid_tokens, 'Invalid token.'

        try:
            embed = discord.Embed(
                title=_escape_everything(data.hostname),
                description=f'`connect {_escape_everything(data.ip)}`',
                color=0x13e82e)

            mention = self._my_ping_role.mention
            player_name = _escape_everything(data.player_name)
            players = data.num_players
            max_players = data.max_players
            content = f'{mention} **{player_name}** wants you to join!' + \
                f' (*{players}*/*{max_players}*)'
            await self._my_channel.send(content=content, embed=embed)
            success = True
        except discord.DiscordException as e:
            logger.error('Error sending a mention: %s', e)

        return success

    async def _add_ping_role(self, member: discord.Member, from_channel: discord.abc.Messageable):
        assert self._my_ping_role
        if self._my_ping_role in member.roles:
            await _channel_msg(
                f'{member.mention} You already have role {self._my_ping_role.name}!', from_channel)
            return
        try:
            logger.info('Adding ping role to user %s!', member.display_name)

            await member.add_roles(self._my_ping_role, reason='User requested.')
            await from_channel.send(f'{member.mention} Added role {self._my_ping_role.name}.')
        except discord.DiscordException as e:
            logger.error('Error adding a ping role: %s', e)
            try:
                await from_channel.send(
                    f'{member.mention} Failed to add role {self._my_ping_role.name}. Check log.')
            except:  # pylint: disable=W0702
                pass

    async def _remove_ping_role(self,
                                member: discord.Member,
                                from_channel: discord.abc.Messageable):
        assert self._my_ping_role
        if self._my_ping_role not in member.roles:
            await _channel_msg(
                f"{member.mention} You don't have role {self._my_ping_role.name}!", from_channel)
            return
        try:
            logger.info('Removing role from user %s!', member.display_name)

            await member.remove_roles(
                self._my_ping_role,
                reason='User requested.')
            await from_channel.send(f'{member.mention} Removed role {self._my_ping_role.name}.')
        except discord.DiscordException as e:
            logger.error('Error removing a ping role: %s', e)
            try:
                await from_channel.send(
                    f'{member.mention} Failed to remove role {self._my_ping_role.name}. Check log.')
            except:  # pylint: disable=W0702
                pass


def parse_config(prsr: ConfigParser):
    """Parse config."""
    discord_token = prsr.get('discord', 'token', fallback=None)
    assert discord_token, 'You need to set discord token!'
    ping_role = prsr.getint('discord', 'ping_role', fallback=None)
    assert ping_role, 'You need to set ping role id!'
    channel_id = prsr.getint('discord', 'channel', fallback=None)
    assert channel_id, 'You need to set channel id!'
    port = prsr.getint('server', 'port', fallback=None)
    assert port, 'You need to set port!'
    cert_path = prsr.get('server', 'cert', fallback=None)
    key_path = prsr.get('server', 'key', fallback=None)
    test_get = True if prsr.get(
        'server', 'test_get', fallback=None) else False
    test_post = True if prsr.get(
        'server', 'test_post', fallback=None) else False
    return NotifyConfig(discord_token=discord_token,
                        ping_role=ping_role,
                        channel_id=channel_id,
                        port=port,
                        cert_path=cert_path,
                        key_path=key_path,
                        test_get=test_get,
                        test_post=test_post)


async def _channel_msg(msg: str, channel: discord.abc.Messageable):
    assert channel
    try:
        await channel.send(msg)
    except discord.DiscordException as e:
        logger.error('Error sending a channel message: %s', e)


def _escape_everything(data: str):
    return discord.utils.escape_markdown(discord.utils.escape_mentions(data))


def _get_valid_tokens(filename: str):
    tokens: list[str] = []
    with open(filename, encoding='utf-8') as fp:
        lines = fp.readlines()
        for line in lines:

            # Check for comments
            try:
                comment_index = line.index(';')
                if comment_index == 0:
                    continue
                line = line[:comment_index]
            except ValueError:
                pass
            token = line.strip()
            if len(token) == 0:
                continue
            tokens.append(token)

    return tokens
