# This file is a part of NEO-WZML (github.com/irisXDR/NEO-WZML)

from asyncio import gather, iscoroutinefunction
from html import escape
from re import findall
from time import time

from psutil import cpu_percent, disk_usage, virtual_memory
from pyrogram import __version__ as pyrover


def _tgram_engine():
    # wzgram/pyroblack both install as module `pyrogram`; report the
    # actual distribution so the status engine tag is truthful
    from importlib.metadata import PackageNotFoundError, version as pkg_version

    for dist, label in (("wzgram", "wzgram"), ("pyroblack", "Pyro")):
        try:
            return f"{label} v{pkg_version(dist)}"
        except PackageNotFoundError:
            continue
    return f"Pyro v{pyrover}"


# invariant at runtime — resolve once instead of scanning site-packages
# dist-info on every EngineStatus() instantiation
_TGRAM_ENGINE = _tgram_engine()
from bot import (
    DOWNLOAD_DIR,
    bot_cache,
    bot_start_time,
    status_dict,
    task_dict,
    task_dict_lock,
)
from bot.core.config_manager import Config
from bot.helper.themes import BotTheme
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker

SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]


class MirrorStatus:
    STATUS_UPLOAD = "Upload"
    STATUS_DOWNLOAD = "Download"
    STATUS_CLONE = "Clone"
    STATUS_QUEUEDL = "QueueDl"
    STATUS_QUEUEUP = "QueueUp"
    STATUS_PAUSED = "Pause"
    STATUS_ARCHIVE = "Archive"
    STATUS_EXTRACT = "Extract"
    STATUS_SPLIT = "Split"
    STATUS_CHECK = "CheckUp"
    STATUS_SEED = "Seed"
    STATUS_SAMVID = "SamVid"
    STATUS_CONVERT = "Convert"
    STATUS_FFMPEG = "FFmpeg"
    STATUS_YT = "YouTube"
    STATUS_METADATA = "Metadata"
    STATUS_MERGING = "Merging"


class EngineStatus:
    def __init__(self):
        ver = bot_cache.get("eng_versions", {})
        self.STATUS_ARIA2 = f"Aria2 v{ver.get('aria2', 'N/A')}"
        self.STATUS_AIOHTTP = f"AioHttp v{ver.get('aiohttp', 'N/A')}"
        self.STATUS_GDAPI = f"Google-API v{ver.get('gapi', 'N/A')}"
        self.STATUS_QBIT = f"qBit v{ver.get('qBittorrent', 'N/A')}"
        self.STATUS_TGRAM = _TGRAM_ENGINE
        self.STATUS_MEGA = f"MegaSDK v{ver.get('mega', '8.1.1')}"
        self.STATUS_TERABOX = f"teraboxSDK v{ver.get('terabox', '1.0.0')}"
        self.STATUS_YTDLP = f"yt-dlp v{ver.get('yt-dlp', 'N/A')}"
        self.STATUS_FFMPEG = f"ffmpeg v{ver.get('ffmpeg', 'N/A')}"
        self.STATUS_7Z = f"7z v{ver.get('7z', 'N/A')}"
        self.STATUS_RCLONE = f"RClone v{ver.get('rclone', 'N/A')}"
        self.STATUS_QUEUE = "QSystem v2"
        self.STATUS_JD = "JDownloader v2"
        self.STATUS_YT = "Youtube-Api"
        self.STATUS_METADATA = "Metadata"
        self.STATUS_UPHOSTER = "Uphoster"


STATUSES = {
    "ALL": "All",
    "DL": MirrorStatus.STATUS_DOWNLOAD,
    "UP": MirrorStatus.STATUS_UPLOAD,
    "QD": MirrorStatus.STATUS_QUEUEDL,
    "QU": MirrorStatus.STATUS_QUEUEUP,
    "AR": MirrorStatus.STATUS_ARCHIVE,
    "EX": MirrorStatus.STATUS_EXTRACT,
    "SD": MirrorStatus.STATUS_SEED,
    "CL": MirrorStatus.STATUS_CLONE,
    "CM": MirrorStatus.STATUS_CONVERT,
    "SP": MirrorStatus.STATUS_SPLIT,
    "SV": MirrorStatus.STATUS_SAMVID,
    "FF": MirrorStatus.STATUS_FFMPEG,
    "PA": MirrorStatus.STATUS_PAUSED,
    "CK": MirrorStatus.STATUS_CHECK,
    "MG": MirrorStatus.STATUS_MERGING,
}


async def get_task_by_gid(gid: str):
    async with task_dict_lock:
        for tk in task_dict.values():
            if hasattr(tk, "seeding"):
                await tk.update()
            task_gid = tk.gid()
            if task_gid and task_gid == gid:
                return tk
        return None


async def get_specific_tasks(status, user_id):
    snapshot = list(task_dict.values())
    if status == "All":
        if user_id:
            return [tk for tk in snapshot if tk.listener.user_id == user_id]
        return snapshot
    tasks_to_check = (
        [tk for tk in snapshot if tk.listener.user_id == user_id]
        if user_id
        else snapshot
    )
    coro_tasks = [tk for tk in tasks_to_check if iscoroutinefunction(tk.status)]
    coro_statuses = await gather(
        *[tk.status() for tk in coro_tasks], return_exceptions=True
    )
    result = []
    coro_index = 0
    for tk in tasks_to_check:
        if tk in coro_tasks:
            st = coro_statuses[coro_index]
            coro_index += 1
            if isinstance(st, BaseException):
                continue
        else:
            try:
                st = tk.status()
            except Exception:
                continue
        if (st == status) or (
            status == MirrorStatus.STATUS_DOWNLOAD and st not in STATUSES.values()
        ):
            result.append(tk)
    return result


async def get_all_tasks(req_status: str, user_id):
    async with task_dict_lock:
        return await get_specific_tasks(req_status, user_id)


def get_raw_file_size(size):
    num, unit = size.split()
    return int(float(num) * (1024 ** SIZE_UNITS.index(unit)))


def get_readable_file_size(size_in_bytes):
    if not size_in_bytes:
        return "0B"

    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1

    return f"{size_in_bytes:.2f}{SIZE_UNITS[index]}"


def get_readable_time(seconds: int):
    periods = [("d", 86400), ("h", 3600), ("m", 60), ("s", 1)]
    result = ""
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f"{int(period_value)}{period_name}"
    return result


def get_raw_time(time_str: str) -> int:
    time_units = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    return sum(
        int(value) * time_units[unit]
        for value, unit in findall(r"(\d+)([dhms])", time_str)
    )


def time_to_seconds(time_duration):
    try:
        parts = time_duration.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = map(float, parts)
        elif len(parts) == 2:
            hours = 0
            minutes, seconds = map(float, parts)
        elif len(parts) == 1:
            hours = 0
            minutes = 0
            seconds = float(parts[0])
        else:
            return 0
        return hours * 3600 + minutes * 60 + seconds
    except Exception:
        return 0


def speed_string_to_bytes(size_text):
    if isinstance(size_text, (int, float)):
        return float(size_text)
    size = 0
    size_text = size_text.lower()
    if "k" in size_text:
        size += float(size_text.split("k")[0]) * 1024
    elif "m" in size_text:
        size += float(size_text.split("m")[0]) * 1048576
    elif "g" in size_text:
        size += float(size_text.split("g")[0]) * 1073741824
    elif "t" in size_text:
        size += float(size_text.split("t")[0]) * 1099511627776
    elif "b" in size_text:
        size += float(size_text.split("b")[0])
    return size


def get_progress_bar_string(pct):
    try:
        pct = float(str(pct).strip().rstrip("%").strip() or 0)
    except (TypeError, ValueError):
        pct = 0
    p = min(max(pct, 0), 100)
    cFull = int(p // 8)
    p_str = "⬢" * cFull
    p_str += "⬡" * (12 - cFull)
    return f"[{p_str}]"


async def get_readable_message(sid, is_user, page_no=1, status="All", page_step=1):
    msg = ""
    button = None

    tasks = await get_specific_tasks(status, sid if is_user else None)

    STATUS_LIMIT = max(int(Config.STATUS_LIMIT or 0) or 10, 1)
    tasks_no = len(tasks)
    pages = (max(tasks_no, 1) + STATUS_LIMIT - 1) // STATUS_LIMIT
    if page_no > pages:
        page_no = (page_no - 1) % pages + 1
        status_dict[sid]["page_no"] = page_no
    elif page_no < 1:
        page_no = pages - (abs(page_no) % pages)
        status_dict[sid]["page_no"] = page_no
    start_position = (page_no - 1) * STATUS_LIMIT

    for index, task in enumerate(
        tasks[start_position : STATUS_LIMIT + start_position], start=1
    ):
        if status != "All":
            tstatus = status
        elif iscoroutinefunction(task.status):
            tstatus = await task.status()
        else:
            tstatus = task.status()

        msg_date = getattr(task.listener.message, "date", None)
        try:
            elapsed = time() - msg_date.timestamp() if msg_date else 0
        except AttributeError:
            elapsed = 0
        msg_link = (
            task.listener.message.link
            if task.listener.is_super_chat and not Config.DELETE_LINKS
            else ""
        )

        msg += BotTheme(
            "STATUS_NAME",
            TaskNum=index + start_position,
            Name=(
                "Task is being Processed!"
                if Config.SAFE_MODE and elapsed >= Config.STATUS_UPDATE_INTERVAL
                else escape(f"{task.name()}")
            ),
        )

        if (
            tstatus not in [MirrorStatus.STATUS_SEED, MirrorStatus.STATUS_QUEUEUP]
            and task.listener.progress
        ):
            progress = task.progress()
            msg += BotTheme(
                "BAR", Bar=f"{get_progress_bar_string(progress)} {progress}"
            )
            msg += BotTheme(
                "PROCESSED",
                Processed=f"{task.processed_bytes()} of {task.size()}",
            )
            msg += BotTheme("STATUS", Status=tstatus, Url=msg_link)
            msg += BotTheme("ETA", Eta=task.eta())
            msg += BotTheme("SPEED", Speed=task.speed())
            msg += BotTheme("ELAPSED", Elapsed=get_readable_time(elapsed))
            msg += BotTheme("ENGINE", Engine=task.engine)
            msg += BotTheme("STA_MODE", Mode=f"{task.listener.mode[0]} - {task.listener.mode[1]}")
            if task.engine.startswith("qBit") and hasattr(task, "seeders_num"):
                try:
                    msg += BotTheme("SEEDERS", Seeders=task.seeders_num())
                    msg += BotTheme("LEECHERS", Leechers=task.leechers_num())
                except Exception:
                    pass
        elif tstatus == MirrorStatus.STATUS_SEED:
            msg += BotTheme("STATUS", Status=tstatus, Url=msg_link)
            msg += BotTheme("SEED_SIZE", Size=task.size())
            msg += BotTheme("SEED_SPEED", Speed=task.seed_speed())
            msg += BotTheme("UPLOADED", Upload=task.uploaded_bytes())
            msg += BotTheme("RATIO", Ratio=task.ratio())
            msg += BotTheme("TIME", Time=task.seeding_time())
            msg += BotTheme("SEED_ENGINE", Engine=task.engine)
        else:
            msg += BotTheme("STATUS", Status=tstatus, Url=msg_link)
            msg += BotTheme("STATUS_SIZE", Size=task.size())
            msg += BotTheme("NON_ENGINE", Engine=task.engine)

        msg += BotTheme("USER", User=task.listener.user.mention(style="html"))
        msg += BotTheme("ID", Id=task.listener.user_id)
        if task.engine.startswith("qBit"):
            msg += BotTheme(
                "BTSEL", Btsel=f"/{BotCommands.SelectCommand[1]}_{task.gid()}"
            )
        msg += BotTheme(
            "CANCEL", Cancel=f"/{BotCommands.CancelTaskCommand[1]}_{task.gid()}"
        )

    if len(msg) == 0:
        if status == "All":
            return None, None
        else:
            msg = f"No Active {status} Tasks!\n\n"

    dl_speed = 0
    up_speed = 0

    def convert_speed_to_bytes_per_second(spd):
        if spd is None:
            return 0
        spd = str(spd).strip()
        if not spd:
            return 0
        sp_upper = spd.upper()
        try:
            if "K" in sp_upper:
                return float(sp_upper.split("K", 1)[0]) * 1024
            if "M" in sp_upper:
                return float(sp_upper.split("M", 1)[0]) * 1048576
            if "G" in sp_upper:
                return float(sp_upper.split("G", 1)[0]) * 1073741824
            if "T" in sp_upper:
                return float(sp_upper.split("T", 1)[0]) * 1099511627776
            if "B" in sp_upper:
                # Plain bytes/s — strip the unit and trailing "/S" / "PS".
                num = sp_upper.split("B", 1)[0]
                return float(num) if num else 0
        except (ValueError, TypeError):
            return 0
        return 0

    for task in tasks:
        try:
            tstatus = (
                await task.status() if iscoroutinefunction(task.status) else task.status()
            )
        except Exception:
            continue
        try:
            spd = task.speed() if tstatus != MirrorStatus.STATUS_SEED else task.seed_speed()
        except Exception:
            spd = None
        speed_in_bytes_per_second = convert_speed_to_bytes_per_second(spd)
        if tstatus == MirrorStatus.STATUS_DOWNLOAD:
            dl_speed += speed_in_bytes_per_second
        elif tstatus in [MirrorStatus.STATUS_UPLOAD, MirrorStatus.STATUS_SEED]:
            up_speed += speed_in_bytes_per_second

    msg += BotTheme("FOOTER")
    buttons = ButtonMaker()
    buttons.data_button(BotTheme("REFRESH", Page=f"{page_no}/{pages}"), f"status {sid} ref")

    if len(tasks) > STATUS_LIMIT:
        if Config.BOT_MAX_TASKS:
            msg += BotTheme(
                "BOT_TASKS",
                Tasks=tasks_no,
                Ttask=Config.BOT_MAX_TASKS,
                Free=Config.BOT_MAX_TASKS - tasks_no,
            )
        else:
            msg += BotTheme("TASKS", Tasks=tasks_no)

        buttons = ButtonMaker()
        buttons.data_button(BotTheme("PREVIOUS"), f"status {sid} pre")
        buttons.data_button(
            BotTheme("REFRESH", Page=f"{page_no}/{pages}"), f"status {sid} ref"
        )
        buttons.data_button(BotTheme("NEXT"), f"status {sid} nex")

    button = buttons.build_menu(3)
    msg += BotTheme("Cpu", cpu=cpu_percent())
    msg += BotTheme(
        "FREE",
        free=get_readable_file_size(disk_usage(DOWNLOAD_DIR).free),
        free_p=round(100 - disk_usage(DOWNLOAD_DIR).percent, 1),
    )
    msg += BotTheme("Ram", ram=virtual_memory().percent)
    msg += BotTheme("uptime", uptime=get_readable_time(time() - bot_start_time))
    msg += BotTheme("DL", DL=get_readable_file_size(dl_speed))
    msg += BotTheme("UL", UL=get_readable_file_size(up_speed))
    return msg, button
