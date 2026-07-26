# This file is a part of NEO-WZML (github.com/irisXDR/NEO-WZML)

from ast import literal_eval
from asyncio import (
    create_subprocess_exec,
    create_subprocess_shell,
    gather,
    sleep,
)
from functools import partial
from io import BytesIO
from os import getcwd
from time import time

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from aiofiles.os import remove, rename
from aioshutil import rmtree
from pyrogram.filters import create
from pyrogram.handlers import MessageHandler

from bot import (
    LOGGER,
    aria2_options,
    drives_ids,
    drives_names,
    index_urls,
    intervals,
    jd_listener_lock,
    QBIT_DEFAULT_WEB_PASSWORD,
    qbit_options,
    task_dict,
    shortener_dict,
    excluded_extensions,
    auth_chats,
    sudo_users,
)
from bot.core.config_manager import Config
from bot.helper.themes import BotTheme
from bot.core.tg_client import TgClient
from bot.helper.ext_utils.bot_utils import new_task, SetInterval
from bot.core.torrent_manager import TorrentManager
from bot.core.startup import update_qb_options, update_variables
from bot.helper.ext_utils.db_handler import database
from bot.core.jdownloader_booter import jdownloader
from bot.helper.ext_utils.task_manager import start_from_queued
from bot.helper.mirror_leech_utils.rclone_utils.serve import rclone_serve_booter
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    send_file,
    send_message,
    update_status_message,
)
from .rss import add_job
from .search import initiate_search_tools

bool_vars = [
    'AS_DOCUMENT', 'BOT_PM', 'STOP_DUPLICATE', 'SET_COMMANDS',
    'SAVE_MSG', 'SHOW_MEDIAINFO', 'SOURCE_LINK', 'SAFE_MODE',
    'SHOW_EXTRA_CMDS', 'IS_TEAM_DRIVE', 'USE_SERVICE_ACCOUNTS',
    'WEB_PINCODE', 'EQUAL_SPLITS', 'DISABLE_DRIVE_LINK',
    'DELETE_LINKS', 'CLEAN_LOG_MSG', 'USER_TD_MODE',
    'INCOMPLETE_TASK_NOTIFIER',
    'SCREENSHOTS_MODE', 'STRICT_MODE',
    'DISABLE_TORRENTS', 'DISABLE_LEECH',
    'DISABLE_BULK', 'DISABLE_MULTI', 'DISABLE_SEED',
    'DISABLE_FF_MODE', 'JD_MODE',
    'MEGA_ENABLED', 'TERABOX_ENABLED', 'MEDIA_STORE', 'SHOW_CLOUD_LINK',
    'UPDATE_PKGS', 'AUTO_UPDATE', 'USE_HYPER',
]

start_dict = {}
state_dict = {}
edit_key_dict = {}
handler_dict = {}
DEFAULT_VALUES = {
    "LEECH_SPLIT_SIZE": TgClient.MAX_SPLIT_SIZE,
    "RSS_DELAY": 600,
    "STATUS_UPDATE_INTERVAL": 15,
    "SEARCH_LIMIT": 0,
    "UPSTREAM_BRANCH": "master",
    "DEFAULT_UPLOAD": "rc",
    "BOT_MAX_TASKS": 0,
    "QUEUE_ALL": 0,
    "QUEUE_DOWNLOAD": 0,
    "QUEUE_UPLOAD": 0,
    "USER_MAX_TASKS": 0,
    "UNIVERSAL_MAX_TASKS": 0,
}


async def _restart_web_server():
    """Apply the current `Config.BASE_URL` / `Config.BASE_URL_PORT` to the
    gunicorn web server *immediately*.

    - Always kill any running gunicorn first (so port changes take effect
      cleanly and a now-empty BASE_URL really shuts the surface down).
    - Then re-spawn gunicorn ONLY if `Config.BASE_URL` is set, on the
      configured port.

    Call this from any code path that mutates BASE_URL / BASE_URL_PORT so
    the change is live the moment the operator saves it — no full bot
    restart required.
    """
    try:
        await (
            await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")
        ).wait()
    except Exception as e:
        LOGGER.warning(f"_restart_web_server: pkill failed: {e}")
    if Config.BASE_URL:
        try:
            port = int(Config.BASE_URL_PORT or 80)
        except (TypeError, ValueError):
            port = 80
        try:
            await create_subprocess_shell(
                "gunicorn -k uvicorn.workers.UvicornWorker -w 1 "
                f"web.wserver:app --bind 0.0.0.0:{port}"
            )
            LOGGER.info(f"gunicorn restarted on port {port} for BASE_URL={Config.BASE_URL!r}")
        except Exception as e:
            LOGGER.error(f"_restart_web_server: spawn failed: {e}")
    else:
        LOGGER.info("BASE_URL is empty — gunicorn left stopped.")


async def get_buttons(key=None, edit_type=None, edit_mode=False, message=None):
    chat_id = message.chat.id if message else None
    state = state_dict.get(chat_id, "view") if chat_id else "view"
    offset = start_dict.get(chat_id, 0) if chat_id else 0
    buttons = ButtonMaker()
    if key is None:
        buttons.data_button("Aria2c Settings", "botset aria")
        buttons.data_button("Config Variables", "botset var")
        buttons.data_button("JDownloader Sync", "botset syncjd")
        buttons.data_button("Private Files", "botset private open")
        buttons.data_button("Qbit Settings", "botset qbit")
        buttons.data_button("Universal Tasks", "botset universal")
        buttons.data_button("Close", "botset close")
        msg = '<blockquote><b><i>Bot Settings:</i></b></blockquote>'
    elif edit_type is not None:
        if edit_type == "botvar":
            from bot.helper.ext_utils.help_messages import config_descriptions

            msg = f'<b>Variable:</b> <code>{key}</code>\n\n'
            msg += f'<b>Description:</b> {config_descriptions.get(key, "No description.")}\n\n'

            if message and message.chat.type.name in ["PRIVATE", "BOT"]:
                current_value = Config.get(key)
                value_str = str(current_value) if current_value not in [None, ""] else "None"
                msg += f'<b>Value:</b> <spoiler>{value_str}</spoiler>\n\n'
            else:
                buttons.data_button('View Value', f"botset showvar {key}", position="header")

            restart_vars = ['BOT_TOKEN', 'TELEGRAM_API', 'TELEGRAM_HASH', 'OWNER_ID',
                            'CMD_SUFFIX', 'USER_SESSION_STRING', 'DATABASE_URL', 'TG_PROXY']
            if edit_mode and key in restart_vars:
                msg += '<b>Note:</b> Restart required for this edit to take effect!\n\n'

            if key in bool_vars:
                msg += '<i>Choose a valid value for the above variable</i>'
                buttons.data_button('True', f"botset boolvar {key} on")
                buttons.data_button('False', f"botset boolvar {key} off")

            elif key not in bool_vars:
                if edit_mode:
                    msg += '<i>Send a valid value for the above variable.</i> <b>Timeout:</b> 60 sec'
                    buttons.data_button("Stop Edit", f"botset editbotvar {key}")
                else:
                    msg += '<i>Click "Edit Value" to modify this variable.</i>'
                    buttons.data_button("Edit Value", f"botset editbotvar {key} edit")

            if key not in ["TELEGRAM_HASH", "TELEGRAM_API", "OWNER_ID", "BOT_TOKEN"] and key not in bool_vars:
                buttons.data_button("Default", f"botset resetvar {key}")

            buttons.data_button("Back", "botset var", position="footer")
            buttons.data_button("Close", "botset close", position="footer")
        elif edit_type == "ariavar":
            buttons.data_button("Back", "botset aria")
            if key != "newkey":
                buttons.data_button("Empty String", f"botset emptyaria {key}")
            buttons.data_button("Close", "botset close")
            msg = (
                "Send a key with value. Example: https-proxy-user:value. Timeout: 60 sec"
                if key == "newkey"
                else f"Send a valid value for {key}. Current value is '{aria2_options[key]}'. Timeout: 60 sec"
            )
        elif edit_type == "qbitvar":
            buttons.data_button("Back", "botset qbit")
            buttons.data_button("Empty String", f"botset emptyqbit {key}")
            buttons.data_button("Close", "botset close")
            msg = f"Send a valid value for {key}. Current value is '{qbit_options[key]}'. Timeout: 60 sec"
    elif key == "var":
        conf_dict = Config.get_all()
        conf_dict.pop("USER_TRANSMISSION", None)
        conf_dict.pop("UNIVERSAL_MAX_TASKS", None)
        for k in sorted(list(conf_dict.keys()))[offset : 10 + offset]:
            if k == "DATABASE_URL" and state != "view":
                continue
            buttons.data_button(k, f"botset editbotvar {k}")
        if state == "view":
            buttons.data_button("Edit", "botset edit var")
        else:
            buttons.data_button("View", "botset view var")
        buttons.data_button("Back", "botset back")
        buttons.data_button("Close", "botset close")
        for x in range(0, len(conf_dict), 10):
            buttons.data_button(
                f"{int(x / 10)}", f"botset start var {x}", position="footer"
            )
        msg = f"Config Variables | Page: {int(offset / 10)} | State: {state}"
    elif key == "private":
        if edit_mode:
            buttons.data_button("Stop Invoke File", "botset private stop", "header")
        else:
            buttons.data_button("Create New File", "botset private new")
            buttons.data_button("Add/Delete File", "botset private edit")
        buttons.data_button("Back", "botset back", position="footer")
        buttons.data_button("Close", "botset close", position="footer")
        txt = "\n • ".join(
            [
                f"<code>{fn}</code>: <b>{'Exists' if await aiopath.isfile(fn) else 'Not Exists'}</b>"
                for fn in [
                    "config.py",
                    "token.pickle",
                    "rclone.conf",
                    "accounts.zip",
                    "list_drives.txt",
                    "shortener.txt",
                    "cookies.txt",
                    "terabox.txt",
                    ".netrc",
                ]
            ]
        )
        msg = f"""<u>Send any of these private files:</u>

<code>config.py, token.pickle, rclone.conf, accounts.zip, list_drives.txt, shortener.txt, cookies.txt, terabox.txt, .netrc or any other file!</code>

 • {txt}

<i>To delete private file send only the file name as text message with or without extension.</i>
<b>NOTE:</b> Changing .netrc will not take effect for aria2c until restart."""
        if edit_mode:
            msg += "\n\n<i>Send the file name to delete the file, file to save the file & for new file create, follow below format.</i> \n\n<b>Format:</b> \nfile_name\n\ncontents of file</i>\n\n<b>Time Left :</b> <code>60 sec</code>"
    elif key == "universal":
        msg = "<blockquote><b>Universal Task Limit</b></blockquote>\n\n"
        msg += "This setting is shared across ALL bots using the same database.\n"
        msg += "Limits total tasks per user across all bot instances.\n\n"

        current = Config.UNIVERSAL_MAX_TASKS
        msg += f"<b>Current Value:</b> <code>{current if current > 0 else 'Disabled (0)'}</code>\n\n"

        if edit_mode:
            msg += "<i>Send a new value (0 = disabled, or a positive number):</i>\n"
            msg += "<b>Timeout:</b> <code>60 sec</code>"
            buttons.data_button("Stop Edit", "botset edit universal")
        else:
            msg += "<i>Click Edit to modify this value.</i>"
            buttons.data_button("Edit Value", "botset edit universal")

        buttons.data_button("Back", "botset back")
        buttons.data_button("Close", "botset close")
    elif key == "aria":
        for k in sorted(list(aria2_options.keys()))[offset : 10 + offset]:
            if k not in ["checksum", "index-out", "out", "pause", "select-file"]:
                buttons.data_button(k, f"botset ariavar {k}")
        if state == "view":
            buttons.data_button("Edit", "botset edit aria")
        else:
            buttons.data_button("View", "botset view aria")
        buttons.data_button("Add new key", "botset ariavar newkey")
        buttons.data_button("Back", "botset back")
        buttons.data_button("Close", "botset close")
        for x in range(0, len(aria2_options), 10):
            buttons.data_button(
                f"{int(x / 10)}", f"botset start aria {x}", position="footer"
            )
        msg = f"Aria2c Options | Page: {int(offset / 10)} | State: {state}"
    elif key == "qbit":
        for k in sorted(list(qbit_options.keys()))[offset : 10 + offset]:
            buttons.data_button(k, f"botset qbitvar {k}")
        if state == "view":
            buttons.data_button("Edit", "botset edit qbit")
        else:
            buttons.data_button("View", "botset view qbit")
        buttons.data_button("Sync Qbittorrent", "botset syncqbit")
        buttons.data_button("Back", "botset back")
        buttons.data_button("Close", "botset close")
        for x in range(0, len(qbit_options), 10):
            buttons.data_button(
                f"{int(x / 10)}", f"botset start qbit {x}", position="footer"
            )
        msg = f"Qbittorrent Options | Page: {int(offset / 10)} | State: {state}"

    return msg, buttons.build_menu(1 if key is None else 2)


async def update_buttons(message, key=None, edit_type=None, edit_mode=False):
    msg, button = await get_buttons(key, edit_type, edit_mode, message)
    await edit_message(message, msg, button)


@new_task
async def edit_variable(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
        if key == "INCOMPLETE_TASK_NOTIFIER" and Config.DATABASE_URL:
            await database.trunc_table("tasks")
    elif key == "STATUS_UPDATE_INTERVAL":
        try:
            value = int(value)
        except (TypeError, ValueError):
            await send_message(
                message,
                "Invalid value! STATUS_UPDATE_INTERVAL must be an integer (seconds).",
            )
            return await update_buttons(pre_message, "var")
        if len(task_dict) != 0 and (st := intervals["status"]):
            for cid, intvl in list(st.items()):
                intvl.cancel()
                intervals["status"][cid] = SetInterval(
                    value, update_status_message, cid
                )
    elif key == "TORRENT_TIMEOUT":
        try:
            value = int(value)
        except (TypeError, ValueError):
            await send_message(
                message,
                "Invalid value! TORRENT_TIMEOUT must be an integer (seconds).",
            )
            return await update_buttons(pre_message, "var")
        await TorrentManager.change_aria2_option("bt-stop-timeout", str(value))
    elif key == "LEECH_SPLIT_SIZE":
        try:
            value = min(int(value), TgClient.MAX_SPLIT_SIZE)
        except (TypeError, ValueError):
            await send_message(
                message,
                "Invalid value! LEECH_SPLIT_SIZE must be an integer (bytes).",
            )
            return await update_buttons(pre_message, "var")
    elif key == "BASE_URL_PORT":
        try:
            value = int(value)
        except (TypeError, ValueError):
            await send_message(
                message,
                "Invalid value! BASE_URL_PORT must be an integer.",
            )
            return await update_buttons(pre_message, "var")
    elif key == "EXCLUDED_EXTENSIONS":
        fx = value.split()
        excluded_extensions.clear()
        excluded_extensions.extend(["aria2", "!qB"])
        for x in fx:
            x = x.lstrip(".")
            excluded_extensions.append(x.strip().lower())
    elif key == "GDRIVE_ID":
        if drives_names and drives_names[0] == "Main":
            drives_ids[0] = value
        else:
            drives_ids.insert(0, value)
    elif key == "INDEX_URL":
        if drives_names and drives_names[0] == "Main":
            index_urls[0] = value
        else:
            index_urls.insert(0, value)
    elif key == "LINKS_LOG_ID":
        if value.strip():
            try:
                value = int(value.strip())
            except ValueError:
                await send_message(
                    message,
                    "Invalid value! LINKS_LOG_ID must be a valid integer chat ID.",
                )
                return await update_buttons(pre_message, "var")
    elif key == "MIRROR_LOG_ID":
        if value.strip():
            try:
                value = int(value.strip())
            except ValueError:
                await send_message(
                    message,
                    "Invalid value! MIRROR_LOG_ID must be a valid integer chat ID.",
                )
                return await update_buttons(pre_message, "var")
    elif key == "AUTHORIZED_CHATS":
        parsed = {}
        try:
            for id_ in value.split():
                chat_id, *thread_ids = id_.split("|")
                chat_id_int = int(chat_id.strip())
                if thread_ids:
                    parsed[chat_id_int] = [int(t.strip()) for t in thread_ids]
                else:
                    parsed[chat_id_int] = []
        except (TypeError, ValueError) as e:
            await send_message(
                message,
                f"Invalid AUTHORIZED_CHATS entry: {e}. "
                "Format: `<chat_id>` or `<chat_id>|<thread_id>...`, "
                "space-separated.",
            )
            return await update_buttons(pre_message, "var")
        auth_chats.clear()
        auth_chats.update(parsed)
    elif key == "SUDO_USERS":
        try:
            new_sudos = [int(x.strip()) for x in value.split()]
        except (TypeError, ValueError) as e:
            await send_message(
                message,
                f"Invalid SUDO_USERS entry: {e}. "
                "Format: space-separated integer user IDs.",
            )
            return await update_buttons(pre_message, "var")
        sudo_users.clear()
        sudo_users.extend(new_sudos)
        value = " ".join(str(x) for x in new_sudos)
    elif key == "LOGIN_PASS":
        value = str(value)
    elif key == "DEBRID_LINK_API":
        value = str(value)
    elif value.isdigit():
        value = int(value)
    elif value.startswith("[") and value.endswith("]"):
        try:
            value = literal_eval(value)
        except (ValueError, SyntaxError) as e:
            LOGGER.error(f"Invalid list literal for {key}: {e}")
            await send_message(message, f"Invalid list literal: {e}")
            return
    elif value.startswith("{") and value.endswith("}"):
        try:
            value = literal_eval(value)
        except (ValueError, SyntaxError) as e:
            LOGGER.error(f"Invalid dict literal for {key}: {e}")
            await send_message(message, f"Invalid dict literal: {e}")
            return
    Config.set(key, value)
    await update_buttons(pre_message, "var")
    await delete_message(message)
    await database.update_config({key: value})
    if key in ["SEARCH_PLUGINS", "SEARCH_API_LINK"]:
        await initiate_search_tools()
    elif key in ["QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"]:
        await start_from_queued()
    elif key in [
        "RCLONE_SERVE_URL",
        "RCLONE_SERVE_PORT",
        "RCLONE_SERVE_USER",
        "RCLONE_SERVE_PASS",
    ]:
        await rclone_serve_booter()
    elif key in ["JD_EMAIL", "JD_PASS"]:
        await jdownloader.boot()
    elif key in ["BASE_URL", "BASE_URL_PORT"]:
        await _restart_web_server()
    elif key == "RSS_DELAY":
        add_job()


@new_task
async def edit_aria(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if key == "newkey":
        key, value = [x.strip() for x in value.split(":", 1)]
    elif value.lower() == "true":
        value = "true"
    elif value.lower() == "false":
        value = "false"
    await TorrentManager.change_aria2_option(key, value)
    await update_buttons(pre_message, "aria")
    await delete_message(message)
    await database.update_aria2(key, value)


@new_task
async def edit_qbit(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if key == "web_ui_password":
        value = QBIT_DEFAULT_WEB_PASSWORD
        await send_message(
            message,
            "qBittorrent WebUI password is managed by startup and set to adminadmin.",
        )
    elif value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
    elif key == "max_ratio":
        value = float(value)
    elif value.isdigit():
        value = int(value)
    await TorrentManager.qbittorrent.app.set_preferences({key: value})
    qbit_options[key] = value
    await update_buttons(pre_message, "qbit")
    await delete_message(message)
    await database.update_qbittorrent(key, value)


@new_task
async def edit_universal(_, message, pre_message):
    handler_dict[message.chat.id] = False
    value = message.text.strip()
    try:
        value = int(value)
        if value < 0:
            value = 0
    except ValueError:
        await send_message(message, "Invalid value! Send a number (0 or positive).")
        return await update_buttons(pre_message, "universal")

    Config.UNIVERSAL_MAX_TASKS = value
    await update_buttons(pre_message, "universal")
    await delete_message(message)
    await database.update_universal_max_tasks(value)


async def sync_jdownloader():
    async with jd_listener_lock:
        if not Config.DATABASE_URL or not jdownloader.is_connected:
            return
        await jdownloader.device.system.exit_jd()
    if await aiopath.exists("cfg.zip"):
        await remove("cfg.zip")
    await (
        await create_subprocess_exec("7z", "a", "cfg.zip", "/JDownloader/cfg")
    ).wait()
    await database.update_private_file("cfg.zip")


@new_task
async def update_private_file(_, message, pre_message, key, new_file=False):
    handler_dict[message.chat.id] = False
    file_name = None
    if not message.media and (file_name := message.text):
        if new_file:
            file_name, content = file_name.split("\n", 1)
            file_name = file_name.strip()
            async with aiopen(file_name, "w") as f:
                await f.write(content.strip())
        else:
            if await aiopath.isfile(file_name) and file_name != "config.py":
                await remove(file_name)
            if file_name == "accounts.zip":
                if await aiopath.exists("accounts"):
                    await rmtree("accounts", ignore_errors=True)
                if await aiopath.exists("rclone_sa"):
                    await rmtree("rclone_sa", ignore_errors=True)
                Config.USE_SERVICE_ACCOUNTS = False
                await database.update_config({"USE_SERVICE_ACCOUNTS": False})
            elif file_name in [".netrc", "netrc"]:
                await (await create_subprocess_exec("touch", ".netrc")).wait()
                await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
                await (
                    await create_subprocess_exec("cp", ".netrc", "/root/.netrc")
                ).wait()
        await delete_message(message)
    elif doc := message.document:
        file_name = doc.file_name
        fpath = f"{getcwd()}/{file_name}"
        if await aiopath.exists(fpath):
            await remove(fpath)
        await message.download(file_name=fpath)
        if file_name == "accounts.zip":
            if await aiopath.exists("accounts"):
                await rmtree("accounts", ignore_errors=True)
            if await aiopath.exists("rclone_sa"):
                await rmtree("rclone_sa", ignore_errors=True)
            await (
                await create_subprocess_exec(
                    "7z", "x", "-o.", "-aoa", "accounts.zip", "accounts/*.json"
                )
            ).wait()
            await (
                await create_subprocess_exec("chmod", "-R", "777", "accounts")
            ).wait()
        elif file_name in [".netrc", "netrc"]:
            if file_name == "netrc":
                await rename("netrc", ".netrc")
                file_name = ".netrc"
            await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
            await (await create_subprocess_exec("cp", ".netrc", "/root/.netrc")).wait()
        elif file_name == "config.py":
            await load_config()
        if "@github.com" in Config.UPSTREAM_REPO:
            buttons = ButtonMaker()
            msg = "Push to UPSTREAM_REPO ?"
            buttons.data_button("Yes!", f"botset push {file_name}")
            buttons.data_button("No", "botset close")
            await send_message(message, msg, buttons.build_menu(2))
        else:
            await delete_message(message)
    if file_name is None:
        return
    if file_name == "rclone.conf":
        await rclone_serve_booter()
    elif file_name == "list_drives.txt" and await aiopath.exists("list_drives.txt"):
        drives_ids.clear()
        drives_names.clear()
        index_urls.clear()
        if Config.GDRIVE_ID:
            drives_names.append("Main")
            drives_ids.append(Config.GDRIVE_ID)
            index_urls.append(Config.INDEX_URL)
        async with aiopen("list_drives.txt", "r+") as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                drives_ids.append(temp[1])
                drives_names.append(temp[0].replace("_", " "))
                if len(temp) > 2:
                    index_urls.append(temp[2])
                else:
                    index_urls.append("")
    elif file_name == "shortener.txt" and await aiopath.exists("shortener.txt"):
        async with aiopen("shortener.txt", "r+") as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                if len(temp) == 2:
                    shortener_dict[temp[0]] = temp[1]
    await update_buttons(pre_message, key)
    await database.update_private_file(file_name)


async def event_handler(client, query, pfunc, rfunc, document=False):
    chat_id = query.message.chat.id
    handler_dict[chat_id] = True
    start_time = update_time = time()

    async def event_filter(_, __, event):
        user = event.from_user or event.sender_chat
        query_user = query.from_user or query.sender_chat
        return bool(
            user is not None
            and query_user is not None
            and user.id == query_user.id
            and event.chat.id == chat_id
            and (event.text or event.document and document)
        )

    handler = client.add_handler(
        MessageHandler(pfunc, filters=create(event_filter)), group=-1
    )
    while handler_dict[chat_id]:
        await sleep(0.5)

        if time() - start_time > 60:
            handler_dict[chat_id] = False
            await rfunc()
        elif document:
            if time() - update_time > 6 and handler_dict[chat_id]:
                update_time = time()
                msg = await client.get_messages(chat_id, query.message.id)
                text = msg.text.split("\n")
                text[-1] = (
                    f"<b>Time Left :</b> <code>{round(60 - (time() - start_time), 2)} sec</code>"
                )
                await edit_message(msg, "\n".join(text), msg.reply_markup)
    client.remove_handler(*handler)


@new_task
async def edit_bot_settings(client, query):
    data = query.data.split()
    message = query.message
    chat_id = message.chat.id
    handler_dict[chat_id] = False
    state = state_dict.get(chat_id, "view")
    if data[1] == "close":
        handler_dict[chat_id] = False
        await query.answer()
        await delete_message(message.reply_to_message)
        await delete_message(message)
    elif data[1] == "back":
        handler_dict[chat_id] = False
        await query.answer()
        start_dict[chat_id] = 0
        await update_buttons(message, None)
    elif data[1] == "syncjd":
        if not Config.JD_EMAIL or not Config.JD_PASS:
            await query.answer(
                "No Email or Password provided!",
                show_alert=True,
            )
            return
        await query.answer(
            "Syncronization Started. JDownloader will get restarted. It takes up to 10 sec!",
            show_alert=True,
        )
        await sync_jdownloader()
    elif data[1] in ["var", "aria", "qbit"]:
        await query.answer()
        await update_buttons(message, data[1])
    elif data[1] == "resetvar":
        handler_dict[chat_id] = False
        await query.answer()
        value = ""
        if data[2] in DEFAULT_VALUES:
            value = DEFAULT_VALUES[data[2]]
            if (
                data[2] == "STATUS_UPDATE_INTERVAL"
                and len(task_dict) != 0
                and (st := intervals["status"])
            ):
                for key, intvl in list(st.items()):
                    intvl.cancel()
                    intervals["status"][key] = SetInterval(
                        value, update_status_message, key
                    )
        elif data[2] == "RSS_SIZE_LIMIT":
            value = 0
        elif data[2] == "EXCLUDED_EXTENSIONS":
            excluded_extensions.clear()
            excluded_extensions.extend(["aria2", "!qB"])
        elif data[2] == "TORRENT_TIMEOUT":
            await TorrentManager.change_aria2_option("bt-stop-timeout", "0")
            await database.update_aria2("bt-stop-timeout", "0")
        elif data[2] == "BASE_URL":
            pass
        elif data[2] == "BASE_URL_PORT":
            value = 80
        elif data[2] == "GDRIVE_ID":
            if drives_names and drives_names[0] == "Main":
                drives_names.pop(0)
                drives_ids.pop(0)
                index_urls.pop(0)
        elif data[2] == "INDEX_URL":
            if drives_names and drives_names[0] == "Main":
                index_urls[0] = ""
        elif data[2] == "INCOMPLETE_TASK_NOTIFIER":
            await database.trunc_table("tasks")
        elif data[2] in ["JD_EMAIL", "JD_PASS"]:
            await create_subprocess_exec("pkill", "-9", "-f", "java")
        elif data[2] == "AUTHORIZED_CHATS":
            auth_chats.clear()
        elif data[2] == "SUDO_USERS":
            sudo_users.clear()
        Config.set(data[2], value)
        await update_buttons(message, "var")
        if data[2] == "DATABASE_URL":
            await database.disconnect()
        await database.update_config({data[2]: value})
        if data[2] in ["SEARCH_PLUGINS", "SEARCH_API_LINK"]:
            await initiate_search_tools()
        elif data[2] in ["QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"]:
            await start_from_queued()
        elif data[2] in [
            "RCLONE_SERVE_URL",
            "RCLONE_SERVE_PORT",
            "RCLONE_SERVE_USER",
            "RCLONE_SERVE_PASS",
        ]:
            await rclone_serve_booter()
        elif data[2] in ["BASE_URL", "BASE_URL_PORT"]:
            await _restart_web_server()
    elif data[1] == "syncqbit":
        handler_dict[chat_id] = False
        await query.answer(
            "Syncronization Started. It takes up to 2 sec!", show_alert=True
        )
        qbit_options.clear()
        await update_qb_options()
        await database.save_qbit_settings()
    elif data[1] == "emptyaria":
        handler_dict[chat_id] = False
        await query.answer()
        aria2_options[data[2]] = ""
        await update_buttons(message, "aria")
        await TorrentManager.change_aria2_option(data[2], "")
        await database.update_aria2(data[2], "")
    elif data[1] == "emptyqbit":
        handler_dict[chat_id] = False
        await query.answer()
        if data[2] == "web_ui_password":
            return await query.answer(
                "qBittorrent WebUI password is managed by startup and cannot be emptied.",
                show_alert=True,
            )
        await TorrentManager.qbittorrent.app.set_preferences({data[2]: ""})
        qbit_options[data[2]] = ""
        await update_buttons(message, "qbit")
        await database.update_qbittorrent(data[2], "")
    elif data[1] == "private":
        await query.answer()
        if data[2] in ("open", "stop"):
            await update_buttons(message, data[1])
        elif data[2] in ("edit", "new"):
            await update_buttons(message, data[1], edit_mode=True)
            pfunc = partial(
                update_private_file,
                pre_message=message,
                key=data[1],
                new_file=data[2] == "new",
            )
            rfunc = partial(update_buttons, message, data[1])
            await event_handler(client, query, pfunc, rfunc, True)
    elif data[1] == "showvar":
        key = data[2]
        value = Config.get(key)

        if value is None or value == "":
            value_str = "None"
        else:
            value_str = str(value)

        if len(value_str) > 200:
            await query.answer()
            with BytesIO(value_str.encode()) as ofile:
                ofile.name = f"{key}_value.txt"
                await send_file(message, ofile)
        else:
            await query.answer(
                f"{key} = {value_str}",
                show_alert=True
            )
    elif data[1] == "boolvar":
        key = data[2]
        value = data[3]

        new_value = value == "on"

        Config.set(key, new_value)

        if Config.DATABASE_URL:
            await database.update_config({key: new_value})

        await query.answer(f"✅ {key} set to {new_value}", show_alert=True)
        await update_buttons(message, key, "botvar")
    elif data[1] == "editbotvar":
        key = data[2]
        await query.answer()

        new_edit_mode = len(data) == 4 and data[3] == "edit"

        if new_edit_mode:
            state_dict[chat_id] = "edit"
        else:
            state_dict[chat_id] = "view"

        await update_buttons(message, key, "botvar", edit_mode=new_edit_mode)

        if new_edit_mode and key not in bool_vars:
            pfunc = partial(edit_variable, pre_message=message, key=key)
            rfunc = partial(update_buttons, message, key, "botvar", False)
            await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "ariavar" and (state == "edit" or data[2] == "newkey"):
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_aria, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, "aria")
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "ariavar" and state == "view":
        value = f"{aria2_options[data[2]]}"
        if len(value) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await send_file(message, out_file)
            return
        elif value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "qbitvar" and state == "edit":
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_qbit, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, "qbit")
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "qbitvar" and state == "view":
        value = f"{qbit_options[data[2]]}"
        if len(value) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await send_file(message, out_file)
            return
        elif value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "universal" and state == "edit":
        await query.answer()
        await update_buttons(message, "universal")
        pfunc = partial(edit_universal, pre_message=message)
        rfunc = partial(update_buttons, message, "universal")
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "universal" and state == "view":
        await query.answer()
        await update_buttons(message, "universal")
    elif data[1] == "edit":
        handler_dict[chat_id] = False
        await query.answer()
        state_dict[chat_id] = "edit"
        if data[2] == "universal":
            await update_buttons(message, data[2], edit_mode=True)
            pfunc = partial(edit_universal, pre_message=message)
            rfunc = partial(update_buttons, message, "universal")
            await event_handler(client, query, pfunc, rfunc)
        else:
            await update_buttons(message, data[2])
    elif data[1] == "view":
        handler_dict[chat_id] = False
        await query.answer()
        state_dict[chat_id] = "view"
        await update_buttons(message, data[2])
    elif data[1] == "start":
        await query.answer()
        new_offset = int(data[3])
        if start_dict.get(chat_id, 0) != new_offset:
            start_dict[chat_id] = new_offset
            await update_buttons(message, data[2])
    elif data[1] == "push":
        await query.answer()
        filename = data[2].rsplit(".zip", 1)[0]
        from re import fullmatch as _refull
        _safe_re = r"[A-Za-z0-9_./-]+"
        if not _refull(_safe_re, filename) or filename.startswith("-"):
            LOGGER.error(f"bot_settings push: rejecting unsafe filename: {filename!r}")
            await delete_message(message.reply_to_message)
            await delete_message(message)
            return
        upstream_branch = Config.UPSTREAM_BRANCH or ""
        if not _refull(r"[A-Za-z0-9_./-]+", upstream_branch) or upstream_branch.startswith("-"):
            LOGGER.error(
                "bot_settings push: rejecting unsafe UPSTREAM_BRANCH: "
                f"{upstream_branch!r}"
            )
            await delete_message(message.reply_to_message)
            await delete_message(message)
            return

        async def _git(*args):
            proc = await create_subprocess_exec("git", *args)
            return await proc.wait()

        if await aiopath.exists(filename):
            await _git("add", "-f", "--", filename)
        else:
            await _git("rm", "-r", "--cached", "--", filename)
        await _git("commit", "-sm", "botsettings", "-q")
        await _git("push", "origin", upstream_branch, "-qf")
        await delete_message(message.reply_to_message)
        await delete_message(message)


@new_task
async def send_bot_settings(_, message):
    chat_id = message.chat.id
    handler_dict[chat_id] = False
    start_dict[chat_id] = 0
    msg, button = await get_buttons(message=message)
    await send_message(message, msg, button)


async def load_config():
    Config.load()
    drives_ids.clear()
    drives_names.clear()
    index_urls.clear()
    await update_variables()

    if not await aiopath.exists("accounts"):
        Config.USE_SERVICE_ACCOUNTS = False

    if len(task_dict) != 0 and (st := intervals["status"]):
        for key, intvl in list(st.items()):
            intvl.cancel()
            intervals["status"][key] = SetInterval(
                Config.STATUS_UPDATE_INTERVAL, update_status_message, key
            )

    if Config.TORRENT_TIMEOUT:
        await TorrentManager.change_aria2_option(
            "bt-stop-timeout", f"{Config.TORRENT_TIMEOUT}"
        )
        await database.update_aria2("bt-stop-timeout", f"{Config.TORRENT_TIMEOUT}")

    if not Config.INCOMPLETE_TASK_NOTIFIER:
        await database.trunc_table("tasks")

    await _restart_web_server()

    if Config.DATABASE_URL:
        await database.connect()
        config_dict = Config.get_all()
        await database.update_config(config_dict)
    else:
        await database.disconnect()
    await gather(initiate_search_tools(), start_from_queued(), rclone_serve_booter())
    add_job()
