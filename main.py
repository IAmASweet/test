import asyncio
import re
from telethon.errors import rpcerrorlist as e
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from tzlocal import get_localzone
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl import types
from csv_process import update_from_dict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from komm import scrape_kommersant
from rbc import scrape_rbc
from change import scrape_change_org
from vc import scrape_vc
import dotenv
from playwright._impl._api_types import Error, TimeoutError
import os
from settings.settings import get_config, logger, read_yaml, change_value_in_yaml
from utils.time_process import write_time
from utils.create_csv import create_csv
from test.test import test

dotenv_file = dotenv.find_dotenv()
minutes = int(get_config(section='Default', key='minutes'))
PATH_CSV = get_config('Default', 'path_csv')
dotenv.load_dotenv()


def get_telethon_session():
    telethon_session_env = os.environ.get("TELETHON_SESSION")
    return telethon_session_env


async def main(tele_client, scheduler):
    await tele_client.start()
    print("Программа запущена")
    logger.info("Программа запущена")
    hours_string: str = get_config("Default", "hours")
    hours: list[str] = hours_string.strip().replace(" ", "").split(',')
    for hour in hours:
        scheduler.add_job(periodic_tasks, "cron", hour=int(hour))
    scheduler.start()
    logger.info("Планировщик запущен")
    await check_new_channels(tele_client)
    links_dict: dict[str, list] = read_yaml("settings/channels.yaml")
    links = links_dict['links']

    @tele_client.on(events.NewMessage(chats=links))
    async def spy_handler(event):
        chat_from = event.chat if event.chat else (await event.get_chat())
        chat_title = chat_from.title
        print(f"Получен пост из канала {chat_title}")
        logger.info(f"Получен пост из канала {chat_title}")
        msg = event.raw_text
        str_replaced = re.sub('[^\x00-\x7Fа-яА-Я]', "", msg)
        arr_text = str_replaced.split("\n\n", maxsplit=1)
        pattern = r'[\n]'
        arr_news = []
        for item in arr_text:
            text = re.sub(pattern, " ", item)
            arr_news.append(text)
        if len(arr_news) == 2:
            await update_from_dict([{'title': arr_news[0],
                                     'content': arr_news[1]}])
            print(f"Продолжаю наблюдение за {chat_title}")
            logger.info(f"Продолжаю наблюдение за {chat_title}")

    await tele_client.run_until_disconnected()


async def check_new_channels(client: TelegramClient) -> None:
    invites: dict = read_yaml("settings/channels.yaml")
    invites_links: list[str] = invites['links']
    async for dialog in client.iter_dialogs():
        if dialog.is_channel:
            channel_username = dialog.entity.username
            link = f'https://t.me/{channel_username}'
            if link in invites_links:
                invites_links.remove(link)
    if invites_links:
        await adding_new_channels(client, invites_links)


async def adding_new_channels(client: TelegramClient,
                              invites_links: list[str]) -> None:
    for invite in invites_links:
        try:
            if re.search(r'\+', invite):
                hash_chat = re.sub(r'https://t.me/\+', '', invite)
                update: types.Updates = \
                    await client(ImportChatInviteRequest(hash_chat.strip()))
            elif re.search(r'joinchat', invite):
                hash_chat = re.sub('https://t.me/joinchat/', '', invite)
                update: types.Updates = \
                    await client(ImportChatInviteRequest(hash_chat.strip()))
            else:
                update: types.Updates = \
                    await client(JoinChannelRequest(invite))
        except e.FloodWaitError as error:
            print(error)
            logger.info(error)
            await asyncio.sleep(error.seconds)
        except e.UserAlreadyParticipantError as error:
            print(error)
            logger.info(error)
        except Exception as error:
            print(error)
            logger.info(error)
        else:
            adding_channel_to_file(update, invite)
            print(f"Новый канал {invite} добавлен в список чатов")
            logger.info(f"Новый канал {invite} добавлен в список чатов")


def adding_channel_to_file(update: types.Updates,
                           invite: str) -> None:
    channel_username = update.chats[0].username
    link = f'https://t.me/{channel_username}'
    change_value_in_yaml(invite, link, 'links',
                         "settings/channels.yaml")


async def periodic_tasks():
    await asyncio.gather(scrape())
    test()
    encoding = get_config('Default', 'encoding')
    await create_csv(PATH_CSV, encoding=encoding)


async def scrape():
    try:
        await scrape_kommersant()
    except (Error, TimeoutError) as error:
        logger.info(f"Ошибка при парсинге Коммерсант {error}")
    try:
        await scrape_vc()
    except (Error, TimeoutError) as error:
        logger.info(f"Ошибка при парсинге Vc {error}")
    try:
        await scrape_rbc()
    except (Error, TimeoutError) as error:
        logger.info(f"Ошибка при парсинге Rbc {error}")
    try:
        await scrape_change_org()
    except (Error, TimeoutError) as error:
        logger.info(f"Ошибка при парсинге Change org {error}")
    await write_time("settings/time.txt")


if __name__ == "__main__":
    api_id = os.environ.get("API_ID")
    api_hash = os.environ.get("API_HASH")
    telethon_session = get_telethon_session()
    scheduler = AsyncIOScheduler(timezone=str(get_localzone()))
    try:
        if len(telethon_session) < 3 or telethon_session is None:
            with TelegramClient(StringSession(),
                                int(api_id),
                                api_hash) as client:
                telethon_session = client.session.save()
                os.environ['TELETHON_SESSION'] = telethon_session.strip()
                dotenv.set_key(dotenv_file,
                               'TELETHON_SESSION',
                               os.environ['TELETHON_SESSION'])
                client.loop.run_until_complete(main(client, scheduler))
        else:
            with TelegramClient(StringSession(telethon_session),
                                int(api_id),
                                api_hash) as client:
                client.loop.run_until_complete(main(client, scheduler))

    except (ValueError, ConnectionError) as e:
        logger.info(f"Произошла ошибка при запуске Telethon. {e} ")
        print(f"Произошла ошибка при запуске Telethon. {e} ")
    except KeyboardInterrupt:
        print("Работа программы завершена")
        logger.info("Работа программы завершена")
    except Exception as e:
        logger.info(e)
        print("\nРабота программы завершена")
        logger.info("Работа программы завершена")
