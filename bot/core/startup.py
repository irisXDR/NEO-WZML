# This file is a part of NEO-WZML (github.com/irisXDR/NEO-WZML)

from asyncio import create_subprocess_exec, create_subprocess_shell
from asyncio.subprocess import PIPE
from importlib import import_module
from os import environ, getenv, path as ospath

from aiofiles import open as aiopen
from aiofiles.os import makedirs, remove, path as aiopath
from aioshutil import rmtree

from bot import (
    LOGGER,
    aria2_options,
    auth_chats,
    drives_ids,
    drives_names,
    index_urls,
    shortener_dict,
    var_list,
    user_data,
    excluded_extensions,
    qbit_options,
    QBIT_DEFAULT_WEB_PASSWORD,
    rss_dict,
    sudo_users,
)
from bot.helper.ext_utils.db_handler import database
from bot.core.config_manager import Config, BinConfig
from bot.core.tg_client import TgClient
from bot.core.torrent_manager import TorrentManager


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


async def _ensure_qbit_web_password(bot_id=None):
    if qbit_options.get("web_ui_password") == QBIT_DEFAULT_WEB_PASSWORD:
        return

    current = qbit_options.get("web_ui_password")
    if current is None:
        LOGGER.info("Applying qBittorrent WebUI password from startup settings.")
    elif len(str(current)) < 6:
        LOGGER.warning(
            "Migrating qBittorrent WebUI password to meet qBittorrent 5.2+ length rules."
        )
    else:
        LOGGER.info("Overriding qBittorrent WebUI password from startup settings.")

    qbit_options["web_ui_password"] = QBIT_DEFAULT_WEB_PASSWORD
    if bot_id and database.db is not None:
        await database.db.settings.qbittorrent.update_one(
            {"_id": bot_id},
            {"$set": {"web_ui_password": QBIT_DEFAULT_WEB_PASSWORD}},
            upsert=True,
        )


async def update_qb_options():
    LOGGER.info("Get qBittorrent options from server")
    if not qbit_options:
        if not TorrentManager.qbittorrent:
            LOGGER.warning(
                "qBittorrent is not initialized. Skipping qBittorrent options update."
            )
            return
        opt = await TorrentManager.qbittorrent.app.preferences()
        qbit_options.update(opt)
        del qbit_options["listen_port"]
        for k in list(qbit_options.keys()):
            if k.startswith("rss"):
                del qbit_options[k]
        await _ensure_qbit_web_password(TgClient.ID)
        await TorrentManager.qbittorrent.app.set_preferences(
            {"web_ui_password": QBIT_DEFAULT_WEB_PASSWORD}
        )
    else:
        await _ensure_qbit_web_password(TgClient.ID)
        await TorrentManager.qbittorrent.app.set_preferences(qbit_options)


def _valid_aria2_speed(value):
    from re import fullmatch

    return bool(value) and fullmatch(r"\d+[KkMmGg]?", str(value).strip()) is not None


async def update_aria2_options():
    LOGGER.info("Get aria2 options from server")
    if not aria2_options:
        op = await TorrentManager.aria2.getGlobalOption()
        aria2_options.update(op)
    else:
        # the DB snapshot predates the config cap and would silently
        # reset it to unlimited — re-assert it on every options push
        if _valid_aria2_speed(Config.ARIA2_MAX_DL_SPEED):
            aria2_options["max-overall-download-limit"] = str(
                Config.ARIA2_MAX_DL_SPEED
            ).strip()
        await TorrentManager.aria2.changeGlobalOption(aria2_options)


async def load_settings():
    if not Config.DATABASE_URL:
        return
    for p in ["thumbnails", "tokens", "rclone"]:
        if await aiopath.exists(p):
            await rmtree(p, ignore_errors=True)
    await database.connect()
    if database.db is not None:
        BOT_ID = Config.BOT_TOKEN.split(":", 1)[0]
        try:
            settings = import_module("config")
            config_file = {
                key: value.strip() if isinstance(value, str) else value
                for key, value in vars(settings).items()
                if not key.startswith("__")
            }
        except ModuleNotFoundError:
            config_file = {}
        config_file.update(
            {
                key: value.strip() if isinstance(value, str) else value
                for key, value in environ.items()
                if key in var_list
            }
        )

        old_config = await database.db.settings.deployConfig.find_one(
            {"_id": BOT_ID}, {"_id": 0}
        )
        config_dict = await database.db.settings.config.find_one(
            {"_id": BOT_ID}, {"_id": 0}
        )

        # deployConfig snapshots local config for drift detection only; runtime config lives in DB.
        if old_config is None:
            await database.db.settings.deployConfig.replace_one(
                {"_id": BOT_ID}, config_file, upsert=True
            )
        elif old_config != config_file:
            LOGGER.info(
                "Local config.py / env has drifted from the saved deployConfig "
                "snapshot — refreshing snapshot. Existing values in the `config` "
                "collection are preserved (DB is the source of truth). Use the "
                "bot's settings UI to change runtime values."
            )
            await database.db.settings.deployConfig.replace_one(
                {"_id": BOT_ID}, config_file, upsert=True
            )

        if config_dict:
            new_keys = {
                key: value
                for key, value in config_file.items()
                if hasattr(Config, key) and key not in config_dict
            }
            if new_keys:
                LOGGER.info(
                    "Seeding %d new key(s) from local config into MongoDB: %s",
                    len(new_keys),
                    ", ".join(sorted(new_keys.keys())),
                )
                await database.db.settings.config.update_one(
                    {"_id": BOT_ID}, {"$set": new_keys}, upsert=True
                )
                config_dict.update(new_keys)
            Config.load_dict(config_dict)
            LOGGER.info("Config loaded from MongoDB (DB is the source of truth)")
        else:
            LOGGER.info(
                "No saved config in MongoDB yet — using local config.py / env "
                "as the initial seed. Will be persisted by save_settings()."
            )

        if pf_dict := await database.db.settings.files.find_one(
            {"_id": BOT_ID}, {"_id": 0}
        ):
            for key, value in pf_dict.items():
                if value:
                    file_ = key.replace("__", ".")
                    async with aiopen(file_, "wb+") as f:
                        await f.write(value)

        if a2c_options := await database.db.settings.aria2c.find_one(
            {"_id": BOT_ID}, {"_id": 0}
        ):
            aria2_options.update(a2c_options)

        if not Config.DISABLE_TORRENTS:
            if qbit_opt := await database.db.settings.qbittorrent.find_one(
                {"_id": BOT_ID}, {"_id": 0}
            ):
                qbit_options.update(qbit_opt)
                await _ensure_qbit_web_password(BOT_ID)

        if await database.db.users[BOT_ID].find_one():
            rows = database.db.users[BOT_ID].find({})
            async for row in rows:
                uid = row["_id"]
                del row["_id"]
                paths = {
                    "THUMBNAIL": f"thumbnails/{uid}.jpg",
                    "RCLONE_CONFIG": f"rclone/{uid}.conf",
                    "TOKEN_PICKLE": f"tokens/{uid}.pickle",
                    "USER_COOKIE_FILE": f"cookies/{uid}/cookies.txt",
                }

                async def save_file(file_path, content):
                    dir_path = ospath.dirname(file_path)
                    if not await aiopath.exists(dir_path):
                        await makedirs(dir_path)
                    if file_path.startswith("cookies/") and file_path.endswith(".txt"):
                        async with aiopen(file_path, "wb") as f:
                            if isinstance(content, str):
                                content = content.encode("utf-8")
                            await f.write(content)
                    else:
                        async with aiopen(file_path, "wb+") as f:
                            if isinstance(content, str):
                                content = content.encode("utf-8")
                            await f.write(content)

                for key, path in paths.items():
                    if row.get(key):
                        await save_file(path, row[key])
                        row[key] = path
                user_data[uid] = row
            LOGGER.info("Users Data has been imported from MongoDB")

        if await database.db.rss[BOT_ID].find_one():
            rows = database.db.rss[BOT_ID].find({})
            async for row in rows:
                user_id = row["_id"]
                del row["_id"]
                rss_dict[user_id] = row
            LOGGER.info("RSS data has been imported from MongoDB")

        await database.create_shared_tasks_indexes()
        await database.cleanup_bot_shared_tasks(BOT_ID)

        await database.create_active_tasks_indexes()
        await database.create_universal_task_locks_indexes()

        await database.migrate_legacy_timestamps()
        await database.reconcile_universal_task_locks()

        local_value = _safe_int(Config.UNIVERSAL_MAX_TASKS, 0)

        global_doc = await database.db.settings.config.find_one(
            {"_id": "GLOBAL"}, {"_id": 0, "UNIVERSAL_MAX_TASKS": 1}
        )
        global_value = _safe_int((global_doc or {}).get("UNIVERSAL_MAX_TASKS"), 0)

        db_value = 0
        source = None
        if global_value > 0:
            db_value = global_value
            source = "GLOBAL"
        else:
            async for doc in database.db.settings.config.find(
                {"UNIVERSAL_MAX_TASKS": {"$exists": True}},
                {"_id": 1, "UNIVERSAL_MAX_TASKS": 1},
            ):
                if doc.get("_id") == "GLOBAL":
                    continue
                value = _safe_int(doc.get("UNIVERSAL_MAX_TASKS"), 0)
                if value > 0 and (db_value == 0 or value < db_value):
                    db_value = value
                    source = "BOT_DOC"

        if db_value > 0:
            if local_value != db_value:
                LOGGER.warning(
                    f"UNIVERSAL_MAX_TASKS: Local config ({local_value}) differs from DB ({db_value}). "
                    f"Using DB value from {source}."
                )
            Config.UNIVERSAL_MAX_TASKS = db_value
            await database.db.settings.config.update_one(
                {"_id": "GLOBAL"},
                {"$set": {"UNIVERSAL_MAX_TASKS": db_value}},
                upsert=True,
            )
        else:
            await database.db.settings.config.update_one(
                {"_id": "GLOBAL"},
                {"$set": {"UNIVERSAL_MAX_TASKS": local_value}},
                upsert=True,
            )
            await database.db.settings.config.update_one(
                {"_id": BOT_ID},
                {"$set": {"UNIVERSAL_MAX_TASKS": local_value}},
                upsert=True,
            )
            if local_value:
                LOGGER.info(
                    f"UNIVERSAL_MAX_TASKS initialized to {local_value} in database"
                )


async def save_settings():
    if database.db is None:
        return
    config_file = Config.get_all()
    await database.db.settings.config.update_one(
        {"_id": TgClient.ID}, {"$set": config_file}, upsert=True
    )
    if await database.db.settings.aria2c.find_one({"_id": TgClient.ID}) is None:
        await database.db.settings.aria2c.update_one(
            {"_id": TgClient.ID}, {"$set": aria2_options}, upsert=True
        )
    if await database.db.settings.qbittorrent.find_one({"_id": TgClient.ID}) is None:
        await database.save_qbit_settings()


async def update_variables():
    if (
        Config.LEECH_SPLIT_SIZE > TgClient.MAX_SPLIT_SIZE
        or Config.LEECH_SPLIT_SIZE == 2097152000
        or not Config.LEECH_SPLIT_SIZE
    ):
        Config.LEECH_SPLIT_SIZE = TgClient.MAX_SPLIT_SIZE

    if Config.AUTHORIZED_CHATS:
        aid = Config.AUTHORIZED_CHATS.split()
        for id_ in aid:
            try:
                chat_id, *thread_ids = id_.split("|")
                chat_id = int(chat_id.strip())
            except (ValueError, AttributeError) as e:
                LOGGER.error(
                    f"AUTHORIZED_CHATS entry {id_!r} is not a valid chat id "
                    f"(format: <chat_id>[|thread_id...]): {e}"
                )
                continue
            valid_threads = []
            for t in thread_ids:
                try:
                    valid_threads.append(int(t.strip()))
                except (ValueError, AttributeError):
                    LOGGER.error(
                        f"AUTHORIZED_CHATS entry {id_!r} has an invalid "
                        f"thread id {t!r}; skipping that thread."
                    )
            auth_chats[chat_id] = valid_threads

    if Config.SUDO_USERS:
        for id_ in Config.SUDO_USERS.split():
            try:
                sudo_users.append(int(id_.strip()))
            except (ValueError, AttributeError):
                LOGGER.error(f"SUDO_USERS entry {id_!r} is not a valid user id; skipping.")

    if Config.EXCLUDED_EXTENSIONS:
        new_excluded = ["aria2", "!qB"]
        for x in Config.EXCLUDED_EXTENSIONS.split():
            cleaned = x.lstrip(".").strip().lower()
            if cleaned and cleaned not in new_excluded:
                new_excluded.append(cleaned)
        excluded_extensions[:] = new_excluded

    if Config.GDRIVE_ID:
        drives_names.append("Main")
        drives_ids.append(Config.GDRIVE_ID)
        index_urls.append(Config.INDEX_URL)

    if await aiopath.exists("list_drives.txt"):
        async with aiopen("list_drives.txt", "r") as f:
            lines = await f.readlines()
        for line in lines:
            temp = line.split()
            if len(temp) < 2:
                LOGGER.warning(f"list_drives.txt: skipping malformed line: {line!r}")
                continue
            drives_ids.append(temp[1])
            drives_names.append(temp[0].replace("_", " "))
            index_urls.append(temp[2] if len(temp) > 2 else "")

    if await aiopath.exists("shortener.txt"):
        async with aiopen("shortener.txt", "r") as f:
            lines = await f.readlines()
        for line in lines:
            temp = line.strip().split()
            if len(temp) == 2:
                shortener_dict[temp[0]] = temp[1]


async def load_configurations():
    if not await aiopath.exists(".netrc"):
        async with aiopen(".netrc", "w"):
            pass

    await (
        await create_subprocess_shell(
            "chmod 600 .netrc && cp .netrc /root/.netrc"
        )
    ).wait()

    aria2_cmd = (
        f"{BinConfig.ARIA2_NAME} --allow-overwrite=true --auto-file-renaming=true "
        f"--bt-enable-lpd=true --bt-detach-seed-only=true --bt-remove-unselected-file=true "
        f"--bt-max-peers=0 --enable-rpc=true --rpc-listen-port=6800 --rpc-listen-all=false --rpc-max-request-size=1024M "
        f"--max-connection-per-server=10 --max-concurrent-downloads=1000 --split=10 "
        f"--seed-ratio=0 --check-integrity=true --continue=true --daemon=true "
        f"--disk-cache=40M --force-save=true --min-split-size=10M --follow-torrent=mem "
        f"--check-certificate=false --optimize-concurrent-downloads=true "
        f"--http-accept-gzip=true --max-file-not-found=0 --max-tries=20 "
        f"--peer-id-prefix=-qB4520- --reuse-uri=true --content-disposition-default-utf8=true "
        f"--user-agent=Wget/1.12 --peer-agent=qBittorrent/4.5.2 --quiet=true "
        f"--summary-interval=0 --max-upload-limit=1K --file-allocation=none"
    )
    if Config.ARIA2_MAX_DL_SPEED:
        # cap aggregate download rate so a fast mirror can't saturate the
        # VPS disk/NIC and freeze the whole machine (e.g. "80M")
        if _valid_aria2_speed(Config.ARIA2_MAX_DL_SPEED):
            aria2_cmd += (
                f" --max-overall-download-limit="
                f"{str(Config.ARIA2_MAX_DL_SPEED).strip()}"
            )
        else:
            LOGGER.error(
                f"Invalid ARIA2_MAX_DL_SPEED '{Config.ARIA2_MAX_DL_SPEED}' "
                f"(use digits + optional K/M/G, e.g. 80M) — ignoring"
            )
    await (await create_subprocess_shell(aria2_cmd)).wait()

    PORT = getenv("PORT", "") or Config.BASE_URL_PORT
    if PORT:
        await create_subprocess_shell(
            f"gunicorn -k uvicorn.workers.UvicornWorker -w 1 web.wserver:app --bind 0.0.0.0:{PORT}"
        )
        await create_subprocess_shell("python3 cron_boot.py")

    if await aiopath.exists("cfg.zip"):
        LOGGER.info("Restoring JDownloader Configuration...")
        if await aiopath.exists("/JDownloader/cfg"):
            await rmtree("/JDownloader/cfg", ignore_errors=True)
        await (
            await create_subprocess_exec(
                "7z", "x", "cfg.zip", "-o/JDownloader", stdout=PIPE, stderr=PIPE
            )
        ).wait()

    if await aiopath.exists("accounts.zip"):
        if await aiopath.exists("accounts"):
            await rmtree("accounts")
        await (
            await create_subprocess_exec(
                "7z",
                "x",
                "-o.",
                "-aoa",
                "accounts.zip",
                "accounts/*.json",
                stdout=PIPE,
                stderr=PIPE,
            )
        ).wait()
        await (await create_subprocess_exec("chmod", "-R", "777", "accounts")).wait()
        await remove("accounts.zip")

    if not await aiopath.exists("accounts"):
        Config.USE_SERVICE_ACCOUNTS = False

    LOGGER.info("About to initialize TorrentManager...")
    await TorrentManager.initiate()
    LOGGER.info("TorrentManager initialized successfully")

    if Config.DISABLE_TORRENTS:
        LOGGER.info("Torrents are disabled. Skipping qBittorrent initialization.")
    else:
        try:
            await _ensure_qbit_web_password(TgClient.ID)
            await TorrentManager.qbittorrent.app.set_preferences(qbit_options)
        except Exception as e:
            LOGGER.error(f"Failed to configure qBittorrent: {e}")
