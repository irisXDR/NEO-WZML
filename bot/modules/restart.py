# This file is a part of NEO-WZML (github.com/irisXDR/NEO-WZML)

from asyncio import create_subprocess_exec, gather
from datetime import datetime
from os import execl as osexecl
from sys import executable

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath, remove
from pytz import timezone

from bot.version import get_version
from bot.helper.themes import BotTheme

from bot import LOGGER, intervals, scheduler, auth_chats
from bot.core.config_manager import Config, BinConfig
from bot.core.jdownloader_booter import jdownloader
from bot.core.tg_client import TgClient
from bot.core.torrent_manager import TorrentManager
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.ext_utils.db_handler import database
from bot.helper.ext_utils.files_utils import clean_all
from bot.helper.telegram_helper import button_build
from bot.helper.telegram_helper.message_utils import (
    delete_message,
    send_message,
)


@new_task
async def restart_bot(_, message):
    buttons = button_build.ButtonMaker()
    buttons.data_button("Yes!", "botrestart confirm")
    buttons.data_button("No!", "botrestart cancel")
    button = buttons.build_menu(2)
    await send_message(
        message, "<i>Are you really sure you want to restart the bot ?</i>", button
    )


@new_task
async def restart_sessions(_, message):
    buttons = button_build.ButtonMaker()
    buttons.data_button("Yes!", "sessionrestart confirm")
    buttons.data_button("No!", "sessionrestart cancel")
    button = buttons.build_menu(2)
    await send_message(
        message,
        "<i>Are you really sure you want to restart the session(s) ?!</i>",
        button,
    )


async def send_incomplete_task_message(cid, msg_id, msg):
    try:
        if msg.startswith("<blockquote><b><i>Restarted Successfully!</i></b></blockquote>"):
            await TgClient.bot.edit_message_text(
                chat_id=cid,
                message_id=msg_id,
                text=msg,
                disable_web_page_preview=True,
            )
            await remove(".restartmsg")
        else:
            await TgClient.bot.send_message(
                chat_id=cid,
                text=msg,
                disable_web_page_preview=True,
                disable_notification=True,
            )
    except Exception as e:
        LOGGER.error(e)


async def restart_notification():
    chat_id, msg_id = 0, 0
    if await aiopath.isfile(".restartmsg"):
        try:
            async with aiopen(".restartmsg", "r") as f:
                contents = (await f.read()).strip().splitlines()
            if len(contents) >= 2:
                chat_id = int(contents[0].strip())
                msg_id = int(contents[1].strip())
            else:
                LOGGER.warning(
                    ".restartmsg has %d line(s); expected 2. Ignoring.",
                    len(contents),
                )
        except (ValueError, OSError) as e:
            LOGGER.error(f"Failed to parse .restartmsg: {e}")

    now = datetime.now(timezone("Asia/Kolkata"))

    notified_chats = set()

    if Config.INCOMPLETE_TASK_NOTIFIER and Config.DATABASE_URL:
        if notifier_dict := await database.get_incomplete_tasks():
            for cid, data in notifier_dict.items():
                notified_chats.add(cid)
                msg = BotTheme(
                    "RESTART_SUCCESS" if cid == chat_id else "RESTARTED",
                    date=now.strftime("%d/%m/%y"),
                    time=now.strftime("%I:%M:%S %p"),
                    timz="Asia/Kolkata",
                    version=get_version(),
                )
                msg += "\n\n<blockquote><b><i>Incomplete tasks:</i></b></blockquote>"
                for tag, links in data.items():
                    msg += f"\n{tag}: "
                    for index, link in enumerate(links, start=1):
                        msg += f" <a href='{link}'>{index}</a> |"
                        if len(msg.encode()) > 4000:
                            await send_incomplete_task_message(cid, msg_id, msg)
                            msg = BotTheme(
                                "RESTARTED",
                                date=now.strftime("%d/%m/%y"),
                                time=now.strftime("%I:%M:%S %p"),
                                timz="Asia/Kolkata",
                                version=get_version(),
                            )
                            msg += (
                                "\n\n<blockquote><b><i>Incomplete tasks "
                                "(continued):</i></b></blockquote>"
                            )
                            msg += f"\n{tag}: "
                if msg:
                    await send_incomplete_task_message(cid, msg_id, msg)

    base_msg = BotTheme(
        "RESTARTED",
        date=now.strftime("%d/%m/%y"),
        time=now.strftime("%I:%M:%S %p"),
        timz="Asia/Kolkata",
        version=get_version(),
    )

    for cid, thread_ids in auth_chats.items():
        if cid in notified_chats:
            continue
        try:
            if thread_ids:
                for thread_id in thread_ids:
                    await TgClient.bot.send_message(
                        chat_id=cid,
                        message_thread_id=thread_id,
                        text=base_msg,
                        disable_web_page_preview=True,
                        disable_notification=True,
                    )
            else:
                await TgClient.bot.send_message(
                    chat_id=cid,
                    text=base_msg,
                    disable_web_page_preview=True,
                    disable_notification=True,
                )
        except Exception as e:
            LOGGER.error(f"Failed to send restart notification to {cid}: {e}")

    if await aiopath.isfile(".restartmsg"):
        try:
            await TgClient.bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=BotTheme(
                    "RESTART_SUCCESS",
                    date=now.strftime("%d/%m/%y"),
                    time=now.strftime("%I:%M:%S %p"),
                    timz="Asia/Kolkata",
                    version=get_version(),
                ),
            )
        except Exception as e:
            LOGGER.error(e)
        await remove(".restartmsg")


@new_task
async def confirm_restart(_, query):
    await query.answer()
    data = query.data.split()
    message = query.message
    reply_to = message.reply_to_message
    await delete_message(message)
    if data[1] == "confirm":
        intervals["stopAll"] = True
        # the replied-to /restart command may already be deleted (e.g.
        # DELETE_LINKS) — fall back to the chat id so the notice still sends
        restart_message = await send_message(
            reply_to or message.chat.id, "<i>Restarting...</i>"
        )
        await TgClient.stop()
        if scheduler.running:
            scheduler.shutdown(wait=False)
        if qb := intervals.get("qb"):
            qb.cancel()
        if jd := intervals.get("jd"):
            jd.cancel()
        if st := intervals.get("status"):
            for intvl in list(st.values()):
                intvl.cancel()
        await clean_all()
        await TorrentManager.close_all()
        if jdownloader.is_connected:
            await gather(
                jdownloader.device.downloadcontroller.stop_downloads(),
                jdownloader.device.linkgrabber.clear_list(),
                jdownloader.device.downloads.cleanup(
                    "DELETE_ALL",
                    "REMOVE_LINKS_AND_DELETE_FILES",
                    "ALL",
                ),
            )
            await jdownloader.close()
        proc1 = await create_subprocess_exec(
            "pkill",
            "-9",
            "-f",
            f"gunicorn|{BinConfig.ARIA2_NAME}|{BinConfig.QBIT_NAME}|"
            f"{BinConfig.FFMPEG_NAME}|{BinConfig.RCLONE_NAME}|"
            f"JDownloader\\.jar|7z|split",
        )
        proc2 = await create_subprocess_exec("python3", "update.py")
        rc1, rc2 = await gather(proc1.wait(), proc2.wait())
        if rc2 != 0:
            LOGGER.warning(
                "update.py exited with %s during restart; continuing anyway "
                "(restart proceeds even if self-update failed).",
                rc2,
            )
        # send_message returns an error string on failure; nothing past this
        # point may raise, or the re-exec is skipped and the bot stays down
        if restart_message is not None and not isinstance(restart_message, str):
            try:
                async with aiopen(".restartmsg", "w") as f:
                    await f.write(
                        f"{restart_message.chat.id}\n{restart_message.id}\n"
                    )
            except OSError as e:
                LOGGER.error(f"Failed to write .restartmsg: {e}")
        osexecl(executable, executable, "-m", "bot")
    else:
        await delete_message(message, reply_to)
