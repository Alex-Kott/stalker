import asyncio
import logging
import re
from logging import Logger
import sys
from typing import List, Tuple

from socks import SOCKS5
from telethon import TelegramClient
from telethon.errors import UserAlreadyParticipantError
from telethon.events import NewMessage
from telethon.tl.custom import Forward
from telethon.tl.functions.channels import JoinChannelRequest, GetFullChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, GetBotCallbackAnswerRequest
from telethon.tl.patched import Message
from telethon.tl.types import Channel, InputChannel, User, InputPeerChannel
from telethon.tl.types.messages import ChatFull

from config import APP_API_HASH, APP_API_ID, PHONE_NUMBER


async def delete_read_messages(client: TelegramClient, logger: Logger):

    dialogs = await client.get_dialogs()

    for dialog in dialogs:
        messages = await client.get_messages(dialog, limit=10000)

        message_ids = [message.id for message in messages if not message.media_unread]
        logger.info(f'In dialog {dialog.title} will remove {len(message_ids)} messages')
        await client.delete_messages(dialog, message_ids)
        logger.info(f'Messages from dialog {dialog.title} removed')


def extract_link_entities(message_text: str) -> Tuple[List[str], List[str]]:
    user_names = re.findall(r'\B@[^\s]+\b', message_text)
    user_names.extend(re.findall(r'(?<=https:\/\/t.me\/)[\w]+', message_text))
    user_names = list(filter(lambda x: not x.startswith('joinchat'), user_names))  # пока такой костыль

    invite_hashes = re.findall(r'(?<=https://t\.me\/joinchat\/)[\w-]+\b', message_text)  # https://t.me/joinchat/A6Fntkc1XV4l3_IzENINAQ

    return user_names, invite_hashes


async def join_public_chats_and_channels(client, user_names):
    for user_name in user_names:
        try:
            entity: Channel = await client.get_entity(user_name)
        except Exception as e:
            print(e, user_name)
            continue

        await asyncio.sleep(1)
        if isinstance(entity, InputChannel) or isinstance(entity, InputPeerChannel) or isinstance(entity, Channel):
            entity_full: ChatFull = await client(GetFullChannelRequest(entity))

            usernames, invite_hashes = extract_link_entities(entity_full.full_chat.about)

            await asyncio.sleep(1)
            await join_private_chats_and_channels(client, invite_hashes)
            await asyncio.sleep(1)
            await join_public_chats_and_channels(client, usernames)
            await asyncio.sleep(1)

            await client(JoinChannelRequest(entity))
        else:
            print(f"Not joined: {user_name}, type {type(entity)}")

        await asyncio.sleep(1)


async def join_private_chats_and_channels(client: TelegramClient, hashes: List[str]):
    for _hash in hashes:
        await asyncio.sleep(1)
        try:
            await client(ImportChatInviteRequest(_hash))
            await asyncio.sleep(1)
        except UserAlreadyParticipantError:
            pass


async def join_forward_author(client: TelegramClient, forward: Forward):
    await asyncio.sleep(1)
    input_entity = await forward.get_input_chat()
    await asyncio.sleep(1)
    if input_entity:
        await client(JoinChannelRequest(input_entity))


async def handle_antibot(client: TelegramClient, event: NewMessage.Event):
    # for @Cyberdyne_Systems_bot
    sender: User = event.message.sender
    message: Message = event.message
    if sender.username == 'Cyberdyne_Systems_bot':
        # GetBotCallbackAnswerRequest
        rows = message.reply_markup.rows
        if rows[0].buttons[0].text == 'Идём':
            passed_button_number = 0
        else:
            passed_button_number = 1

        await client(GetBotCallbackAnswerRequest(message.chat, message.id,
                                                 data=message.reply_markup.rows[0].buttons[passed_button_number].data))


async def main(client: TelegramClient) -> None:
    await client.start()

    @client.on(NewMessage)
    async def new_message_handler(event: NewMessage.Event):
        # TODO сделать обход

        if event.message.is_reply:
            await handle_antibot(client, event)

        if event.message.forward:
            await join_forward_author(client, event.message.forward)

        user_names, invite_hashes = extract_link_entities(event.message.text)
        print(user_names)

        await join_public_chats_and_channels(client, user_names)
        await join_private_chats_and_channels(client, invite_hashes)

    await client.run_until_disconnected()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M',
                        filename='/tmp/message_remover_log')
    base_logger = logging.getLogger()
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    stream_handler.setFormatter(formatter)
    base_logger.addHandler(stream_handler)

    proxy = None
    proxy = (SOCKS5, '51.144.86.230', 18001, True, 'usrTELE', 'avt231407')
    telegram_client = TelegramClient(PHONE_NUMBER.strip('+'),
                                     APP_API_ID,
                                     APP_API_HASH,
                                     proxy=proxy,
                                     base_logger=base_logger)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(telegram_client))
