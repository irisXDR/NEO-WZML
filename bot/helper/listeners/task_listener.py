# This file is a part of NEO-WZML (github.com/irisXDR/NEO-WZML)

from asyncio import gather, sleep
from datetime import datetime
from html import escape
from pytz import timezone
from time import time
from mimetypes import guess_type
from contextlib import suppress
from os import path as ospath

from aiofiles.os import listdir, makedirs, remove, path as aiopath
from aioshutil import move
from requests import utils as rutils

from bot import (
    intervals,
    task_dict,
    task_dict_lock,
    LOGGER,
    non_queued_up,
    non_queued_dl,
    queued_up,
    queued_dl,
    queue_dict_lock,
    same_directory_lock,
    DOWNLOAD_DIR,
)
from bot.modules.metadata import apply_metadata_title
from bot.helper.common import TaskConfig
from bot.core.tg_client import TgClient
from bot.core.config_manager import Config
from bot.core.torrent_manager import TorrentManager
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.links_utils import encode_slink
from bot.helper.ext_utils.db_handler import database
from bot.helper.ext_utils.files_utils import (
    clean_download,
    clean_target,
    create_recursive_symlink,
    get_path_size,
    join_files,
    remove_excluded_files,
    move_and_merge,
)
from bot.helper.ext_utils.links_utils import is_gdrive_id
from bot.helper.ext_utils.status_utils import get_readable_file_size, get_readable_time
from bot.helper.ext_utils.task_manager import check_running_tasks, start_from_queued
from bot.helper.mirror_leech_utils.uphoster_utils.gofile_utils.upload import GoFileUpload
from bot.helper.mirror_leech_utils.uphoster_utils.buzzheavier_utils.upload import (
    BuzzHeavierUpload,
)
from bot.helper.mirror_leech_utils.uphoster_utils.pixeldrain_utils.upload import (
    PixelDrainUpload,
)
from bot.helper.mirror_leech_utils.uphoster_utils.multi_upload import MultiUphosterUpload
from bot.helper.mirror_leech_utils.gdrive_utils.upload import GoogleDriveUpload
from bot.helper.mirror_leech_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.mirror_leech_utils.upload_utils.terabox_upload import TeraboxUpload
from bot.helper.mirror_leech_utils.status_utils.uphoster_status import UphosterStatus
from bot.helper.mirror_leech_utils.status_utils.gdrive_status import (
    GoogleDriveStatus,
)
from bot.helper.mirror_leech_utils.status_utils.terabox_upload_status import (
    TeraboxUploadStatus,
)
from bot.helper.mirror_leech_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_leech_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.mirror_leech_utils.status_utils.telegram_status import TelegramStatus
from bot.helper.mirror_leech_utils.upload_utils.telegram_uploader import TelegramUploader
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.themes import BotTheme
from bot.helper.telegram_helper.message_utils import (
    delete_message,
    delete_status,
    send_message,
    update_status_message,
)


class TaskListener(TaskConfig):
    def __init__(self):
        super().__init__()

    async def clean(self):
        with suppress(Exception):
            if st := intervals["status"]:
                for intvl in list(st.values()):
                    intvl.cancel()
            intervals["status"].clear()
            await gather(TorrentManager.aria2.purgeDownloadResult(), delete_status())

    def clear(self):
        self.subname = ""
        self.subsize = 0
        self.files_to_proceed = []
        self.proceed_count = 0
        self.progress = True

    async def remove_from_same_dir(self):
        async with task_dict_lock:
            if (
                self.folder_name
                and self.same_dir
                and self.mid in self.same_dir[self.folder_name]["tasks"]
            ):
                self.same_dir[self.folder_name]["tasks"].remove(self.mid)
                self.same_dir[self.folder_name]["total"] -= 1

    async def send_processing(self):
        if self.processing_msg is not None or self.multi > 1:
            return
        with suppress(Exception):
            self.processing_msg = await send_message(
                self.message, "<b>Processing...</b>"
            )

    async def remove_processing(self):
        msg = self.processing_msg
        self.processing_msg = None
        if msg and not isinstance(msg, str):
            with suppress(Exception):
                await delete_message(msg)

    async def on_download_start(self):
        await self.remove_processing()
        mode_name = "Leech" if self.is_leech else "Mirror"
        if Config.LINKS_LOG_ID:
            dispTime = datetime.now(timezone(Config.TIMEZONE)).strftime("%d/%m/%y, %I:%M:%S %p")
            await send_message(
                Config.LINKS_LOG_ID,
                BotTheme("LINKS_START", Mode=mode_name, Tag=self.tag)
                + BotTheme("LINKS_SOURCE", On=dispTime, Source=f"<a href='{self.source_url}'>Click Here</a>"),
            )
        if self.bot_pm and self.is_super_chat:
            self.pm_msg = await send_message(
                self.user_id,
                BotTheme("PM_START", msg_link=self.source_url),
            )
            if isinstance(self.pm_msg, str):
                buttons = ButtonMaker()
                buttons.url_button(
                    "Start Bot", f"https://t.me/{TgClient.BNAME}?start=start"
                )
                await self.on_download_error(
                    "Bot isn't started in PM to receive file(s)!", buttons.build_menu(1)
                )
                return
        if (
            self.is_super_chat
            and Config.INCOMPLETE_TASK_NOTIFIER
            and Config.DATABASE_URL
        ):
            await database.add_incomplete_task(
                self.message.chat.id, self.message.link, self.tag
            )

    async def on_download_complete(self):
        await sleep(2)
        if self.is_cancelled:
            return
        multi_links = False
        if (
            self.folder_name
            and self.same_dir
            and self.mid in self.same_dir[self.folder_name]["tasks"]
        ):
            async with same_directory_lock:
                while True:
                    async with task_dict_lock:
                        if self.mid not in self.same_dir[self.folder_name]["tasks"]:
                            return
                        if (
                            self.same_dir[self.folder_name]["total"] <= 1
                            or len(self.same_dir[self.folder_name]["tasks"]) > 1
                        ):
                            if self.same_dir[self.folder_name]["total"] > 1:
                                self.same_dir[self.folder_name]["tasks"].remove(
                                    self.mid
                                )
                                self.same_dir[self.folder_name]["total"] -= 1
                                spath = f"{self.dir}{self.folder_name}"
                                des_id = list(self.same_dir[self.folder_name]["tasks"])[
                                    0
                                ]
                                des_path = f"{DOWNLOAD_DIR}{des_id}{self.folder_name}"
                                LOGGER.info(f"Moving files from {self.mid} to {des_id}")
                                await move_and_merge(spath, des_path, self.mid)
                                multi_links = True
                            break
                    await sleep(1)
        async with task_dict_lock:
            if self.is_cancelled:
                return
            if self.mid not in task_dict:
                return
            download = task_dict[self.mid]
            self.name = download.name()
            gid = download.gid()

        if not (self.is_torrent or self.is_qbit):
            self.seed = False

        if multi_links:
            self.seed = False
            await self.on_upload_error(
                f"{self.name} Downloaded!\n\nWaiting for other tasks to finish..."
            )
            return
        elif self.same_dir:
            self.seed = False

        if self.folder_name:
            self.name = self.folder_name.strip("/").split("/", 1)[0]

        if not await aiopath.exists(f"{self.dir}/{self.name}"):
            try:
                files = await listdir(self.dir)
                if not files:
                    LOGGER.warning(
                        f"task_listener: download dir {self.dir} is empty; "
                        "skipping name fix-up"
                    )
                    raise FileNotFoundError(self.dir)
                actual_name = files[-1]
                if actual_name == "yt-dlp-thumb" and len(files) > 1:
                    # Pick first non-thumb entry
                    other = next(
                        (f for f in files if f != "yt-dlp-thumb"),
                        actual_name,
                    )
                    actual_name = other

                # Treat multiple selected files in task root as one folder
                root_entries = [f for f in files if f != "yt-dlp-thumb"]
                if self.select and len(root_entries) > 1:
                    selection_name = self.name.strip("/") or "Selected Files"
                    selection_path = f"{self.dir}/{selection_name}"
                    await makedirs(selection_path, exist_ok=True)
                    for entry in root_entries:
                        if entry == selection_name:
                            continue
                        await move(f"{self.dir}/{entry}", f"{selection_path}/{entry}")
                    self.name = selection_name
                    LOGGER.info(
                        f"Staged selected files into folder for post-processing: {self.name}"
                    )
                    actual_name = self.name
                
                LOGGER.debug(f"Custom name check: custom_name={getattr(self, 'custom_name', False)}, self.name={self.name}, actual_name={actual_name}")

                if getattr(self, 'custom_name', False) and actual_name != self.name:
                    from aiofiles.os import rename as aiorename
                    old_path = f"{self.dir}/{actual_name}"
                    new_path = f"{self.dir}/{self.name}"

                    if await aiopath.isfile(old_path):
                        old_ext = ospath.splitext(actual_name)[1]
                        new_ext = ospath.splitext(self.name)[1]
                        if not new_ext and old_ext:
                            self.name = f"{self.name}{old_ext}"
                            new_path = f"{self.dir}/{self.name}"
                    
                    await aiorename(old_path, new_path)
                    LOGGER.info(f"Renamed to custom name: {actual_name} -> {self.name}")
                else:
                    LOGGER.debug(f"Using actual name: {actual_name}")
                    self.name = actual_name
            except Exception as e:
                LOGGER.error(f"Error in custom name rename: {e}")
                await self.on_upload_error(str(e))
                return

        dl_path = f"{self.dir}/{self.name}"
        self.size = await get_path_size(dl_path)
        self.is_file = await aiopath.isfile(dl_path)

        if self.seed:
            up_dir = self.up_dir = f"{self.dir}10000"
            up_path = f"{self.up_dir}/{self.name}"
            await create_recursive_symlink(self.dir, self.up_dir)
            LOGGER.info(f"Shortcut created: {dl_path} -> {up_path}")
        else:
            up_dir = self.dir
            up_path = dl_path

        await remove_excluded_files(
            self.up_dir or self.dir,
            self.get_excluded_extensions_for_download(),
        )

        async with queue_dict_lock:
            if self.mid in non_queued_dl:
                non_queued_dl.remove(self.mid)
        await start_from_queued()

        if self.join and not self.is_file:
            await join_files(up_path)

        if self.merge_video and not self.is_file:
            up_path = await self.proceed_merge(up_path, gid)
            if self.is_cancelled:
                return
            self.is_file = await aiopath.isfile(up_path)
            self.name = up_path.replace(f"{up_dir}/", "").split("/", 1)[0]
            self.size = await get_path_size(up_dir)
            self.clear()

        if self.extract:
            up_path = await self.proceed_extract(up_path, gid)
            if self.is_cancelled:
                return
            self.is_file = await aiopath.isfile(up_path)
            self.name = up_path.replace(f"{up_dir}/", "").split("/", 1)[0]
            self.size = await get_path_size(up_dir)
            self.clear()
            await remove_excluded_files(
                up_dir,
                self.get_excluded_extensions_for_download(),
            )

        if self.ffmpeg_cmds:
            up_path = await self.proceed_ffmpeg(
                up_path,
                gid,
            )
            if self.is_cancelled:
                return
            self.is_file = await aiopath.isfile(up_path)
            self.name = up_path.replace(f"{up_dir}/", "").split("/", 1)[0]
            self.size = await get_path_size(up_dir)
            self.clear()

        if (
            (hasattr(self, "metadata_dict") and self.metadata_dict)
            or (hasattr(self, "audio_metadata_dict") and self.audio_metadata_dict)
            or (hasattr(self, "video_metadata_dict") and self.video_metadata_dict)
        ):
            up_path = await apply_metadata_title(
                self,
                up_path,
                gid,
                getattr(self, "metadata_dict", {}),
                getattr(self, "audio_metadata_dict", {}),
                getattr(self, "video_metadata_dict", {}),
            )
            if self.is_cancelled:
                return

            self.name = up_path.replace(f"{up_dir.rstrip('/')}/", "").split("/", 1)[0]
            self.size = await get_path_size(up_path)
            self.clear()

        if self.is_leech and self.is_file:
            fname = ospath.basename(up_path)
            self.file_details["filename"] = fname
            self.file_details["mime_type"] = (guess_type(fname))[
                0
            ] or "application/octet-stream"

        from bot.helper.ext_utils.filename_utils import format_filename
        from aiofiles.os import rename as aiorename
        from os import walk
        from natsort import natsorted
        from bot.helper.ext_utils.bot_utils import sync_to_async

        has_mirror_settings = self.mirror_prefix or self.mirror_suffix or self.mirror_name_swap
        has_leech_settings = self.leech_prefix or self.leech_suffix or self.leech_name_swap

        if self.custom_name and self.is_file:
            LOGGER.info(f"Skipping filename modifications - user provided custom name via -n for single file")
        elif self.custom_name and not self.is_file:
            if self.is_leech:
                LOGGER.info(f"Custom name used for folder - applying modifications to files inside (leech mode)")
                if has_leech_settings:
                    walked = await sync_to_async(walk, up_path, topdown=True)
                    for dirpath, _, files in walked:
                        for file in natsorted(files):
                            old_path = ospath.join(dirpath, file)
                            new_name = await format_filename(file, self.user_dict, self.is_leech)

                            if new_name != file and new_name:
                                new_path = ospath.join(dirpath, new_name)
                                await aiorename(old_path, new_path)
                                LOGGER.debug(f"Renamed: {file} -> {new_name}")
            else:
                LOGGER.info(f"Custom name used for folder - keeping folder name, applying modifications to files inside (mirror mode)")
                if has_mirror_settings:
                    walked = await sync_to_async(walk, up_path, topdown=True)
                    for dirpath, _, files in walked:
                        for file in natsorted(files):
                            old_path = ospath.join(dirpath, file)
                            new_name = await format_filename(file, self.user_dict, self.is_leech)

                            if new_name != file and new_name:
                                new_path = ospath.join(dirpath, new_name)
                                await aiorename(old_path, new_path)
                                LOGGER.debug(f"Renamed: {file} -> {new_name}")
        elif (not self.is_leech and has_mirror_settings) or (self.is_leech and has_leech_settings):
            if self.is_file:
                original_name = ospath.basename(up_path)
                new_name = await format_filename(original_name, self.user_dict, self.is_leech)

                if new_name != original_name and new_name:
                    new_path = ospath.join(ospath.dirname(up_path), new_name)
                    await aiorename(up_path, new_path)
                    up_path = new_path
                    LOGGER.info(f"Renamed {'leech' if self.is_leech else 'mirror'} file: {original_name} -> {new_name}")
            else:
                folder_name = ospath.basename(up_path)
                new_folder_name = await format_filename(folder_name, self.user_dict, self.is_leech)
                
                if new_folder_name != folder_name and new_folder_name:
                    new_up_path = ospath.join(ospath.dirname(up_path), new_folder_name)
                    await aiorename(up_path, new_up_path)
                    LOGGER.info(f"Renamed folder: {folder_name} -> {new_folder_name}")
                    up_path = new_up_path

                walked = await sync_to_async(walk, up_path, topdown=True)
                for dirpath, _, files in walked:
                    for file in natsorted(files):
                        old_path = ospath.join(dirpath, file)
                        new_name = await format_filename(file, self.user_dict, self.is_leech)

                        if new_name != file and new_name:
                            new_path = ospath.join(dirpath, new_name)
                            await aiorename(old_path, new_path)
                            LOGGER.debug(f"Renamed: {file} -> {new_name}")
                        elif new_name != file:
                            LOGGER.debug(f"Skipped rename (empty result): {file}")

            self.is_file = await aiopath.isfile(up_path)
            self.name = up_path.replace(f"{up_dir}/", "").split("/", 1)[0]



        if self.screen_shots:
            up_path = await self.generate_screenshots(up_path)
            if self.is_cancelled:
                return
            self.is_file = await aiopath.isfile(up_path)
            self.name = up_path.replace(f"{up_dir}/", "").split("/", 1)[0]
            self.size = await get_path_size(up_dir)

        if self.convert_audio or self.convert_video:
            up_path = await self.convert_media(
                up_path,
                gid,
            )
            if self.is_cancelled:
                return
            self.is_file = await aiopath.isfile(up_path)
            self.name = up_path.replace(f"{up_dir}/", "").split("/", 1)[0]
            self.size = await get_path_size(up_dir)
            self.clear()

        if self.sample_video:
            up_path = await self.generate_sample_video(up_path, gid)
            if self.is_cancelled:
                return
            self.is_file = await aiopath.isfile(up_path)
            self.name = up_path.replace(f"{up_dir}/", "").split("/", 1)[0]
            self.size = await get_path_size(up_dir)
            self.clear()

        if self.zip_images and not self.compress:
            up_path = await self.proceed_zip_images(up_path, gid)
            if self.is_cancelled:
                return
            self.is_file = await aiopath.isfile(up_path)
            self.name = up_path.replace(f"{up_dir}/", "").split("/", 1)[0]
            self.size = await get_path_size(up_dir)
            self.clear()

        if self.compress:
            up_path = await self.proceed_compress(
                up_path,
                gid,
            )
            self.is_file = await aiopath.isfile(up_path)
            if self.is_cancelled:
                return
            self.clear()

        self.name = up_path.replace(f"{up_dir}/", "").split("/", 1)[0]
        self.size = await get_path_size(up_dir)

        if self.is_leech and not self.compress:
            await self.proceed_split(up_path, gid)
            if self.is_cancelled:
                return
            self.clear()

        self.subproc = None

        add_to_queue, event = await check_running_tasks(self, "up")
        await start_from_queued()
        if add_to_queue:
            LOGGER.info(f"Added to Queue/Upload: {self.name}")
            async with task_dict_lock:
                task_dict[self.mid] = QueueStatus(self, gid, "Up")
            await event.wait()
            if self.is_cancelled:
                return
            LOGGER.info(f"Start from Queued/Upload: {self.name}")

        self.size = await get_path_size(up_dir)

        if self.is_leech:
            tg = TelegramUploader(self, up_dir)
            async with task_dict_lock:
                task_dict[self.mid] = TelegramStatus(self, tg, gid, "up", tg.hyper)
            await gather(
                update_status_message(self.message.chat.id),
                tg.upload(),
            )
            del tg
        elif self.is_uphoster:
            LOGGER.info(f"Uphoster Upload Name: {self.name}")
            uphoster_service = self.user_dict.get("UPHOSTER_SERVICE", "gofile")
            services = uphoster_service.split(",")
            ddl = MultiUphosterUpload(self, up_path, services)
            async with task_dict_lock:
                task_dict[self.mid] = UphosterStatus(self, ddl, gid, "up")
            await gather(
                update_status_message(self.message.chat.id),
                ddl.upload(),
            )
            del ddl
        elif getattr(self, "is_terabox_upload", False):
            tbx = TeraboxUpload(self, up_path)
            async with task_dict_lock:
                task_dict[self.mid] = TeraboxUploadStatus(self, tbx, gid, "up")
            await gather(
                update_status_message(self.message.chat.id),
                tbx.upload(),
            )
            del tbx
        elif is_gdrive_id(self.up_dest):
            LOGGER.info(f"Gdrive Upload Name: {self.name}")
            drive = GoogleDriveUpload(self, up_path)
            async with task_dict_lock:
                task_dict[self.mid] = GoogleDriveStatus(self, drive, gid, "up")
            await gather(
                update_status_message(self.message.chat.id),
                sync_to_async(drive.upload),
            )
            del drive
        else:
            LOGGER.info(f"Rclone Upload Name: {self.name}")
            RCTransfer = RcloneTransferHelper(self)
            async with task_dict_lock:
                task_dict[self.mid] = RcloneStatus(self, RCTransfer, gid, "up")
            await gather(
                update_status_message(self.message.chat.id),
                RCTransfer.upload(up_path),
            )
            del RCTransfer
        return

    async def _send_mega_skipped_breakdown(self):
        """Send a complete per-file breakdown of MEGA-skipped files."""
        mega_skipped = getattr(self, "mega_skipped_files", None)
        if not mega_skipped:
            return

        from collections import defaultdict

        by_reason = defaultdict(list)
        for fname, reason in mega_skipped:
            by_reason[reason].append(fname)

        MAX_CHUNK_BYTES = 3800
        chunks = []
        current = ""

        for reason, fnames in by_reason.items():
            n_total = len(fnames)
            header = f"⚠️ <b>{escape(reason)} ({n_total}):</b>\n"
            if (
                current
                and len(current.encode("utf-8")) + len(header.encode("utf-8"))
                > MAX_CHUNK_BYTES
            ):
                chunks.append(current)
                current = ""
            current += header
            for i, fn in enumerate(fnames, 1):
                line = f"  {i}. <code>{escape(fn)}</code>\n"
                if (
                    len(current.encode("utf-8")) + len(line.encode("utf-8"))
                    > MAX_CHUNK_BYTES
                ):
                    chunks.append(current)
                    remaining = n_total - i + 1
                    current = (
                        f"⚠️ <b>{escape(reason)} "
                        f"(cont., {remaining} more):</b>\n"
                    )
                current += line

        if current:
            chunks.append(current)

        send_to_mirror_log = (
            not self.is_leech and getattr(Config, "MIRROR_LOG_ID", "")
        )

        for chunk in chunks:
            if not (self.bot_pm and self.is_super_chat):
                await send_message(self.user_id, chunk)
            if self.is_super_chat:
                await send_message(self.message, chunk)
            if send_to_mirror_log:
                await send_message(Config.MIRROR_LOG_ID, chunk)
            await sleep(0.3)

    async def on_upload_complete(
        self, link, files, folders, mime_type, rclone_path="", dir_id=""
    ):
        if (
            self.is_super_chat
            and Config.INCOMPLETE_TASK_NOTIFIER
            and Config.DATABASE_URL
        ):
            await database.rm_complete_task(self.message.link)
        msg = BotTheme("NAME", Name=escape(self.name))
        msg += BotTheme("SIZE", Size=get_readable_file_size(self.size))
        try:
            elapsed = time() - self.message.date.timestamp()
        except AttributeError:
            elapsed = 0
        msg += BotTheme("ELAPSE", Time=get_readable_time(elapsed))
        msg += BotTheme("MODE", Mode=f"{self.mode[0]} - {self.mode[1]}")
        LOGGER.info(f"Task Done: {self.name}")
        if self.is_leech:
            msg += BotTheme("L_TOTAL_FILES", Files=folders)
            if mime_type != 0:
                msg += BotTheme("L_CORRUPTED_FILES", Corrupt=mime_type)
            msg += BotTheme("L_CC", Tag=self.tag)

            if not files and not self.is_super_chat:
                await send_message(self.message, msg)
            else:
                msg += "✦ <b><u>Files List :</u></b>\n"
                fmsg = ""
                for index, (link, name) in enumerate(files.items(), start=1):
                    chat_id, msg_id = link.split("/")[-2:]
                    fmsg += f"{index}. <a href='{link}'>{name}</a>"
                    fmsg += "\n"
                    if len(fmsg.encode() + msg.encode()) > 4000:
                        if not (self.bot_pm and self.is_super_chat):
                            await send_message(self.user_id, msg + fmsg)
                        if self.is_super_chat:
                            group_msg = msg + fmsg
                            if self.bot_pm:
                                group_msg = group_msg.replace("✦ <b><u>Files List :</u></b>\n", "✦ <b><u>Action Performed :</u></b>\n➜ <i>File(s) have been Sent to Bot PM (Private)</i>\n\n✦ <b><u>Files List :</u></b>\n")
                            await send_message(self.message, group_msg)
                        await sleep(1)
                        fmsg = ""
                if fmsg != "":
                    if not (self.bot_pm and self.is_super_chat):
                        await send_message(self.user_id, msg + fmsg)
                    if self.is_super_chat:
                        group_msg = msg + fmsg
                        if self.bot_pm:
                            group_msg = group_msg.replace("✦ <b><u>Files List :</u></b>\n", "✦ <b><u>Action Performed :</u></b>\n➜ <i>File(s) have been Sent to Bot PM (Private)</i>\n\n✦ <b><u>Files List :</u></b>\n")
                        await send_message(self.message, group_msg)
        else:
            msg += BotTheme("M_TYPE", Mimetype=mime_type)
            if mime_type == "Folder":
                msg += BotTheme("M_SUBFOLD", Folder=folders)
                msg += BotTheme("TOTAL_FILES", Files=files)

            multi_link_msg = ""
            multi_links = []
            if isinstance(link, dict):
                for service, result in link.items():
                    if "error" in result:
                        multi_link_msg += (
                            f"{service.capitalize()}: Error - {result['error']}\n"
                        )
                    elif result.get("link"):
                        multi_links.append(
                            (f"{service.capitalize()} Link", result["link"])
                        )
                multi_link_msg = multi_link_msg.strip()
                link = None

            if (
                link
                or rclone_path
                and Config.RCLONE_SERVE_URL
                and not self.private_link
                or multi_links
            ):
                buttons = ButtonMaker()
                show_drive_link = Config.SHOW_CLOUD_LINK and (
                    not Config.DISABLE_DRIVE_LINK or self.user_id == Config.OWNER_ID
                )
                if link and show_drive_link:
                    buttons.url_button("☁️ Cloud Link", link)
                elif multi_links:
                    for name, url in multi_links:
                        buttons.url_button(name, url)
                else:
                    msg += f"\n\nPath: <code>{rclone_path}</code>"
                if rclone_path and Config.RCLONE_SERVE_URL and not self.private_link:
                    remote, rpath = rclone_path.split(":", 1)
                    url_path = rutils.quote(f"{rpath}")
                    share_url = f"{Config.RCLONE_SERVE_URL}/{remote}/{url_path}"
                    if mime_type == "Folder":
                        share_url += "/"
                    buttons.url_button("🔗 Rclone Link", share_url)
                if not rclone_path and dir_id:
                    INDEX_URL = ""
                    if self.private_link:
                        INDEX_URL = self.user_dict.get("INDEX_URL", "") or ""
                    elif Config.INDEX_URL:
                        INDEX_URL = Config.INDEX_URL
                    if INDEX_URL and self.name:
                        safe_name = rutils.quote(self.name.strip("/"))
                        share_url = f"{INDEX_URL}/{safe_name}"
                        if mime_type == "Folder":
                            share_url += "/"
                        buttons.url_button("⚡ Index Link", share_url)
                        if mime_type.startswith(("image", "video", "audio")):
                            share_urls = f"{share_url}?a=view"
                            buttons.url_button("🌐 View Link", share_urls)

                if Config.SAVE_MSG:
                    save_target = "pm"
                    if self.user_dict.get("SAVE_MODE", False) and self.user_dict.get("LDUMP"):
                        ldumps = self.user_dict.get("LDUMP") or {}
                        for value in ldumps.values():
                            candidate = f"save {value}".encode("utf-8")
                            if len(candidate) <= 64:
                                save_target = value
                                break
                    buttons.data_button("💾 Save", f"save {save_target}")

                if Config.SOURCE_LINK and self.source_url:
                    buttons.url_button("🔗 Source", self.source_url)

                if Config.SHOW_MEDIAINFO and mime_type and mime_type != 0:
                    if mime_type.startswith(("video", "audio")):
                        buttons.data_button("🎬 MediaInfo", f"mediainfo {self.mid}")

                button = buttons.build_menu(2)
            else:
                if not multi_link_msg:
                    msg += f"\n\n • Path: <code>{rclone_path}</code>"
                button = None
            msg += f"\n\n • <b>Task By:</b> {self.tag}\n\n"
            group_msg = (
                msg + "✦ <b><u>Action Performed :</u></b>\n"
                "➜ <i>Cloud link(s) have been sent to User PM</i>\n\n"
            )

            if multi_link_msg:
                group_msg += multi_link_msg + "\n"
                msg += multi_link_msg + "\n"

            if self.bot_pm and self.is_super_chat:
                await send_message(self.user_id, msg, button)

            if hasattr(Config, "MIRROR_LOG_ID") and Config.MIRROR_LOG_ID:
                await send_message(Config.MIRROR_LOG_ID, msg, button)

            await send_message(self.message, group_msg, button)

        await self._send_mega_skipped_breakdown()

        if self.seed:
            await clean_target(self.up_dir)
            async with queue_dict_lock:
                if self.mid in non_queued_up:
                    non_queued_up.remove(self.mid)
            await start_from_queued()
            return


        await clean_download(self.dir)
        async with task_dict_lock:
            if self.mid in task_dict:
                del task_dict[self.mid]
            count = len(task_dict)
        await database.remove_shared_task(
            self.mid, TgClient.ID, user_id=self.user_id
        )
        if count == 0:
            await self.clean()
        else:
            await update_status_message(self.message.chat.id)

        async with queue_dict_lock:
            if self.mid in non_queued_up:
                non_queued_up.remove(self.mid)

        await start_from_queued()

    async def on_download_error(self, error, button=None, is_limit=False):
        await self.remove_processing()
        async with task_dict_lock:
            if self.mid in task_dict:
                del task_dict[self.mid]
            count = len(task_dict)
        await database.remove_shared_task(
            self.mid, TgClient.ID, user_id=self.user_id
        )
        await self.remove_from_same_dir()

        error_str = str(error)
        friendly_error = self._beautify_error(error_str)
        
        msg = (
            f"""<i><b>Limit Breached!</b></i>
 • <b>Task Size:</b> {get_readable_file_size(self.size)}
 • <b>Mode:</b> {self.mode[0]} - {self.mode[1]}

{error}"""
            if is_limit
            else f"""<i><b>Download Stopped!</b></i>
• <b>Task for:</b> {self.tag}

• <b>Due To:</b> {escape(friendly_error)}
• <b>Mode:</b> {self.mode[0]} - {self.mode[1]}
• <b>Elapsed:</b> {get_readable_time(time() - self.message.date.timestamp())}"""
        )

        await send_message(self.message, msg, button)
        await self._send_mega_skipped_breakdown()

        if count == 0:
            await self.clean()
        else:
            await update_status_message(self.message.chat.id)

        if (
            self.is_super_chat
            and Config.INCOMPLETE_TASK_NOTIFIER
            and Config.DATABASE_URL
        ):
            await database.rm_complete_task(self.message.link)

        async with queue_dict_lock:
            if self.mid in queued_dl:
                queued_dl[self.mid].set()
                del queued_dl[self.mid]
            if self.mid in queued_up:
                queued_up[self.mid].set()
                del queued_up[self.mid]
            if self.mid in non_queued_dl:
                non_queued_dl.remove(self.mid)
            if self.mid in non_queued_up:
                non_queued_up.remove(self.mid)

        await start_from_queued()
        await sleep(3)
        await clean_download(self.dir)
        if self.up_dir:
            await clean_download(self.up_dir)
        if self.thumb and await aiopath.exists(self.thumb):
            await remove(self.thumb)
    
    def _beautify_error(self, error: str) -> str:
        error_lower = error.lower()

        friendly_indicators = [
            "storage reserve", "insufficient disk space", "use other bots",
            "no enough space", "not enough space",
            
            "stopped by user", "cancelled by user", "task was cancelled",
            "canceled by user", "download cancelled by user",
            "file already being downloaded",
            "task have been removed from queue",
            "task already cancelled or removed",
            
            "please try again", "please check", "server may be",
            "link may be", "connection failed", "unable to connect",
            
            "download quota exceeded", "rate limit exceeded",
            "google drive api", "google-imposed restriction",
            "insufficient permissions", "access denied",
            "wait 12-24 hours", "wait a few minutes",
            "file not found or access denied",
            "account may not have permission",
            
            "mega.nz downloads are currently disabled",
            "requesttemperror", "transfertemperror",
            
            "jdownloader is currently disabled",
            
            "torrents are disabled", "torrent and magnet downloads are disabled",
            "dead torrent", "torrent already added",
            "seeding stopped with ratio",
            
            "no enough space for this torrent",
            
            "no video available to download from this playlist",
            
            "no document in the replied message",
            "use supergroup",
            
            "all files are failed to download",
            "there is nothing to download",
            
            "rclonedownload jsonload",
            
            "internal error occurred",
            "this is not an active task",
            "bot owner", "currently disabled",
            
            "⚠️", "❌", "✅", "📁", "🔗",
        ]
        if any(x in error_lower for x in friendly_indicators):
            if len(error) > 500:
                return error[:500] + "..."
            return error

        if any(x in error_lower for x in ["network is unreachable", "errno 101", "errno 111", "connection refused"]):
            return "Network connection failed. Server may be down or unreachable."
        if any(x in error_lower for x in ["max retries exceeded", "connectionerror", "newconnectionerror", "httpsconnectionpool", "httpconnectionpool"]):
            return "Unable to connect to server. Please try again later."
        if any(x in error_lower for x in ["timed out", "timeouterror", "read timed out", "connect timed out"]):
            return "Connection timed out. Server is not responding."
        if any(x in error_lower for x in ["ssl:", "certificate verify", "handshake failed", "sslcertverificationerror"]):
            return "Secure connection failed. SSL/Certificate error."
        if any(x in error_lower for x in ["name or service not known", "nodename nor servname", "getaddrinfo failed", "gaierror"]):
            return "Server not found. Check if the URL is correct."
        if "reset by peer" in error_lower or "connection reset" in error_lower:
            return "Connection was interrupted. Please try again."
        if "too many redirects" in error_lower or "exceeded 30 redirects" in error_lower:
            return "Too many redirects. The link might be broken."

        if "403" in error and ("http" in error_lower or "forbidden" in error_lower):
            return "Access denied. Link may require login or is geo-restricted."
        if "404" in error and ("http" in error_lower or "not found" in error_lower):
            return "File not found. The link may be expired or invalid."
        if "401" in error and ("http" in error_lower or "unauthorized" in error_lower):
            return "Authentication required. Please check credentials."
        if any(x in error for x in ["500", "502", "503", "504"]) and "http" in error_lower:
            return "Server error. Please try again later."
        if ("429" in error or "rate limit" in error_lower) and "http" in error_lower:
            return "Too many requests. Please wait and try again."

        if "quota exceeded" in error_lower or "userratelimitexceeded" in error_lower:
            return "Storage quota exceeded."
        if "permission denied" in error_lower and "errno" in error_lower:
            return "Permission denied. Cannot access the file."
        if ("no such file" in error_lower or "filenotfounderror" in error_lower) and "errno" in error_lower:
            return "File not found on server."

        if "torrent already added" in error_lower or "already added by" in error_lower:
            return "This torrent is already being downloaded."
        if "dead torrent" in error_lower:
            return "Dead torrent - no seeders available."

        if len(error) > 200:
            return error[:200] + "..."
        return error

    async def on_upload_error(self, error):
        async with task_dict_lock:
            if self.mid in task_dict:
                del task_dict[self.mid]
            count = len(task_dict)
        await database.remove_shared_task(
            self.mid, TgClient.ID, user_id=self.user_id
        )
        
        friendly_error = self._beautify_error(str(error))

        msg = f"""<i><b>Upload Stopped!</b></i>
• <b>Task for:</b> {self.tag}

• <b>Due To:</b> {escape(friendly_error)}
• <b>Mode:</b> {self.mode[0]} - {self.mode[1]}
• <b>Elapsed:</b> {get_readable_time(time() - self.message.date.timestamp())}"""
        await send_message(self.message, msg)
        if count == 0:
            await self.clean()
        else:
            await update_status_message(self.message.chat.id)

        if (
            self.is_super_chat
            and Config.INCOMPLETE_TASK_NOTIFIER
            and Config.DATABASE_URL
        ):
            await database.rm_complete_task(self.message.link)

        async with queue_dict_lock:
            if self.mid in queued_dl:
                queued_dl[self.mid].set()
                del queued_dl[self.mid]
            if self.mid in queued_up:
                queued_up[self.mid].set()
                del queued_up[self.mid]
            if self.mid in non_queued_dl:
                non_queued_dl.remove(self.mid)
            if self.mid in non_queued_up:
                non_queued_up.remove(self.mid)

        await start_from_queued()
        await sleep(3)
        await clean_download(self.dir)
        if self.up_dir:
            await clean_download(self.up_dir)
        if self.thumb and await aiopath.exists(self.thumb):
            await remove(self.thumb)
