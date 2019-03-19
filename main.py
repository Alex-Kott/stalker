import asyncio
import logging
import re
from logging import Logger
import sys
from asyncio import sleep
from datetime import datetime
from typing import List

from socks import SOCKS5
from telethon import TelegramClient
from telethon.events import NewMessage
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.patched import Message

from config import APP_API_HASH, APP_API_ID, PHONE_NUMBER


async def delete_read_messages(client: TelegramClient, logger: Logger):

    dialogs = await client.get_dialogs()

    for dialog in dialogs:
        messages = await client.get_messages(dialog, limit=10000)

        message_ids = [message.id for message in messages if not message.media_unread]
        logger.info(f'In dialog {dialog.title} will remove {len(message_ids)} messages')
        await client.delete_messages(dialog, message_ids)
        logger.info(f'Messages from dialog {dialog.title} removed')


def extract_link_entities(message: Message) -> List[str]:
    aliases = re.findall(r'@[^\s]+\b', message.text)
    invite_links = re.findall(r'https://t\.me\/joinchat\/[^\s]+\b', message.text)  # https://t.me/joinchat/AAAAAEXvt7XMiRRRBobjzw

    return aliases + invite_links


async def join_entities(client: TelegramClient, links: List[str]):
    for link in links:
        input_entity = await client.get_input_entity(link)
        entity = await client.get_entity(input_entity)

        res = await client(JoinChannelRequest(entity))
        print(res)


async def main(client: TelegramClient) -> None:
    await client.start()

    @client.on(NewMessage)
    async def my_event_handler(event: NewMessage):
        # print(type(event.message))
        entity_links = extract_link_entities(event.message)
        await join_entities(client, entity_links)





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
