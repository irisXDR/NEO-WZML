# This file is a part of NEO-WZML (github.com/irisXDR/NEO-WZML)

from asyncio import Lock, Semaphore, create_task, gather, sleep
from logging import getLogger
from os import path as ospath, walk
from re import match as re_match, sub as re_sub
from time import time

from aioshutil import rmtree
from natsort import natsorted
from PIL import Image
from pyrogram import StopTransmission
from pyrogram.errors import (
    BadRequest,
    ChannelInvalid,
    ChatAdminRequired,
    ChatWriteForbidden,
    FloodWait,
    PeerIdInvalid,
    RPCError,
)

try:
    from pyrogram.errors import FloodPremiumWait
except ImportError:
    FloodPremiumWait = FloodWait
from aiofiles.os import (
    path as aiopath,
    remove,
    rename,
)
from pyrogram.types import (
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
)
from bot.core.config_manager import Config
from bot.core.tg_client import TgClient
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.files_utils import check_strict_file_mode, get_base_name, is_archive
from bot.helper.ext_utils.status_utils import get_readable_file_size, get_readable_time
from bot.helper.telegram_helper.message_utils import send_message
from bot.helper.ext_utils.media_utils import (
    get_audio_thumbnail,
    get_document_type,
    get_media_info,
    get_multiple_frames_thumbnail,
    get_video_thumbnail,
    get_md5_hash,
)
from bot.helper.telegram_helper.message_utils import delete_message
from bot.helper.mirror_leech_utils.upload_utils.hyperul_utils import (
    build_uploaded_media,
    raw_send_media,
)

LOGGER = getLogger(__name__)


class CancelledUpload(BaseException):
    pass


class TelegramUploader:
    def __init__(self, listener, path):
        self._last_uploaded = 0
        self._processed_bytes = 0
        self._listener = listener
        self._path = path
        self._client = None
        self._upload_chat_id = 0
        self._reply_to_id = 0
        self._start_time = time()
        self._total_files = 0
        self._thumb = self._listener.thumb or f"thumbnails/{listener.user_id}.jpg"
        self._msgs_dict = {}
        self._corrupted = 0
        self._is_corrupted = False
        self._media_dict = {"videos": {}, "documents": {}}
        self._last_msg_in_group = False
        self._up_path = ""
        self._lprefix = ""
        self._lsuffix = ""
        self._lcaption = ""
        self._lfont = ""
        self._bot_pm = False
        self._media_group = False
        self._is_private = False
        self._sent_msg = None
        self._log_msg = None
        self._user_session = False
        self._prm_media = False
        self._error = ""
        self._auto_thumb_enabled = (
            not self._listener.thumb and
            self._listener.user_dict.get("AUTO_THUMBNAIL", False)
        )
        self._auto_thumb_path = None
        # HyperUpload: HELPER_TOKENS bots pre-upload several files in
        # parallel (aggregate speed scales with bot count) while a single
        # sender posts them strictly in natural sort order, so series
        # episodes and split parts always land in sequence.
        self._hyper_ul = bool(
            Config.USE_HYPER and TgClient.helper_bots and listener.up_dest
        )
        self._helper_index = None
        self._prep_lock = Lock()
        self._is_log_del = False

    def _check_cancelled(self):
        if self._listener.is_cancelled:
            raise CancelledUpload()

    async def _upload_progress(self, current, _):
        if self._listener.is_cancelled:
            if self._client:
                self._client.stop_transmission()
            elif self._user_session:
                TgClient.user.stop_transmission()
            else:
                self._listener.client.stop_transmission()
        chunk_size = current - self._last_uploaded
        self._last_uploaded = current
        self._processed_bytes += chunk_size

    async def _user_settings(self):
        settings_map = {
            "BOT_PM": ("_bot_pm", False),
            "LEECH_PREFIX": ("_lprefix", ""),
            "LEECH_SUFFIX": ("_lsuffix", ""),
            "LEECH_CAPTION": ("_lcaption", ""),
            "LEECH_FONT": ("_lfont", ""),
            "LEECH_CAPTION_STYLE": ("_lcaption_style", ""),
        }

        for key, (attr, default) in settings_map.items():
            setattr(
                self,
                attr,
                self._listener.user_dict.get(key) or getattr(Config, key, default),
            )

        self._media_group = False

        if isinstance(self._lcaption, dict):
            self._lcaption = self._lcaption.get("text", "")

        if self._thumb is not None and self._thumb != "none" and not await aiopath.exists(self._thumb):
            self._thumb = None

    async def _msg_to_reply(self):
        if self._listener.up_dest:
            msg_link = (
                self._listener.message.link if self._listener.is_super_chat else ""
            )
            msg = f"""<blockquote><b><i>Leech Started</i></b></blockquote>

 • <b>User:</b> {self._listener.user.mention} (#ID{self._listener.user_id}){f"\n • <b>Message Link:</b> <a href='{msg_link}'>Click Here</a>" if msg_link else ""}
 • <b>Source:</b> <a href='{self._listener.source_url}'>Click Here</a>"""
            try:
                self._log_msg = await TgClient.bot.send_message(
                    chat_id=self._listener.up_dest,
                    text=msg,
                    disable_web_page_preview=True,
                    message_thread_id=self._listener.chat_thread_id,
                    disable_notification=True,
                )
                self._sent_msg = self._log_msg
                self._upload_chat_id = self._log_msg.chat.id
                self._reply_to_id = self._log_msg.id
                self._is_private = self._log_msg.chat.type.name == "PRIVATE"
                if self._listener.leech_dest:
                    try:
                        leech_dest = self._listener.leech_dest
                        if not isinstance(leech_dest, int):
                            if leech_dest.lstrip("-").isdigit():
                                leech_dest = int(leech_dest)
                        await TgClient.bot.copy_message(
                            chat_id=leech_dest,
                            from_chat_id=self._log_msg.chat.id,
                            message_id=self._log_msg.id,
                            message_thread_id=self._listener.leech_dest_thread_id,
                        )
                    except Exception as e:
                        if not self._listener.is_cancelled:
                            LOGGER.error(
                                f"Failed to copy 'Leech Started' message to {self._listener.leech_dest}: {e}"
                            )
                            await send_message(
                                self._listener.user_id,
                                f"Failed to send 'Leech Started' message to {self._listener.leech_dest}\n{e}",
                            )
            except Exception as e:
                await self._cleanup_auto_thumb()
                await self._listener.on_upload_error(str(e))
                return False

        else:
            self._sent_msg = self._listener.message
            self._upload_chat_id = self._listener.message.chat.id
            self._reply_to_id = self._listener.message.id
        return True

    async def _switching_client(self):
        if self._prm_media and TgClient.IS_PREMIUM_USER:
            self._user_session = True
            self._client = TgClient.user
            self._helper_index = None
        elif self._hyper_ul and not self._prm_media:
            # Pick the least-loaded helper bot for this file
            self._user_session = False
            self._helper_index = min(
                TgClient.helper_loads, key=TgClient.helper_loads.get
            )
            self._client = TgClient.helper_bots[self._helper_index]
        else:
            self._user_session = False
            self._client = self._listener.client
            self._helper_index = None

    async def _prepare_file(self, pre_file_, dirpath):
        cap_file_ = file_ = pre_file_

        cap_mono = cap_file_
        if self._lcaption:
            self._lcaption = re_sub(
                r"(\\\||\\\{|\\\}|\\s)",
                lambda m: {r"\|": "%%", r"\{": "&%&", r"\}": "$%$", r"\s": " "}[
                    m.group(0)
                ],
                self._lcaption,
            )

            import re as regex
            split_pattern = regex.compile(r'\|(?=[^|]*?:[^|]*?(?::\d+)?(?:\||$))')
            parts = split_pattern.split(self._lcaption)
            parts[0] = re_sub(
                r"\{([^}]+)\}", lambda m: f"{{{m.group(1).lower()}}}", parts[0]
            )
            up_path = ospath.join(dirpath, pre_file_)

            is_video, is_audio, is_image = await get_document_type(up_path)

            video_placeholders = ['{quality}', '{languages}', '{duration}', '{subtitles}']
            has_video_placeholders = any(ph in parts[0] for ph in video_placeholders)

            template_to_format = parts[0]
            if not is_video and has_video_placeholders:
                lines = template_to_format.split('\n')
                filtered_lines = []
                for line in lines:
                    if not any(ph in line for ph in video_placeholders):
                        filtered_lines.append(line)
                template_to_format = '\n'.join(filtered_lines)

            if is_video:
                dur, qual, lang, subs = await get_media_info(up_path, True)
            else:
                dur, qual, lang, subs = 0, "", "", ""

            cap_mono = template_to_format.format(
                filename=file_,
                size=get_readable_file_size(await aiopath.getsize(up_path)),
                duration=get_readable_time(dur),
                quality=qual,
                languages=lang,
                subtitles=subs,
                md5_hash=await sync_to_async(get_md5_hash, up_path),
                mime_type=self._listener.file_details.get("mime_type", "text/plain"),
                prefilename=self._listener.file_details.get("filename", ""),
                precaption=self._listener.file_details.get("caption", ""),
            )

            if not is_video and has_video_placeholders:

                import re as html_regex

                tag_pattern = html_regex.compile(r'<(/)?(\w+)(?:\s[^>]*)?(\s*/)?>')
                tag_stack = []

                for match in tag_pattern.finditer(cap_mono):
                    is_closing = match.group(1) == '/'
                    tag_name = match.group(2).lower()
                    is_self_closing = match.group(3) is not None

                    if is_self_closing:
                        continue
                    elif is_closing:
                        if tag_stack and tag_stack[-1] == tag_name:
                            tag_stack.pop()
                        else:
                            cap_mono = cap_mono[:match.start()] + cap_mono[match.end():]
                    else:
                        tag_stack.append(tag_name)

                while tag_stack:
                    tag = tag_stack.pop()
                    cap_mono += f'</{tag}>'

                cap_mono = re_sub(r'\n\s*\n\s*\n+', '\n\n', cap_mono)
                cap_mono = cap_mono.strip()

            for part in parts[1:]:
                args = part.split(":")
                cap_mono = cap_mono.replace(
                    args[0],
                    args[1] if len(args) > 1 else "",
                    int(args[2]) if len(args) == 3 else -1,
                )
            cap_mono = re_sub(
                r"%%|&%&|\$%\$",
                lambda m: {"%%": "|", "&%&": "{", "$%$": "}"}[m.group()],
                cap_mono,
            )

            from bot.helper.ext_utils.bot_utils import has_html_tags
            has_html = has_html_tags(cap_mono)

            if self._lcaption_style and not has_html:
                from bot.helper.ext_utils.bot_utils import apply_caption_style
                cap_mono = apply_caption_style(cap_mono, self._lcaption_style)

        else:
            if self._lcaption_style:
                from bot.helper.ext_utils.bot_utils import apply_caption_style
                cap_mono = apply_caption_style(cap_mono, self._lcaption_style)
            elif Config.LEECH_FONT:
                cap_mono = f"<{Config.LEECH_FONT}>{cap_file_}</{Config.LEECH_FONT}>"
            else:
                cap_mono = cap_file_

        if len(file_) > 255:
            if is_archive(file_):
                name = get_base_name(file_)
                ext = file_.split(name, 1)[1]
            elif match := re_match(r".+(?=\..+\.0*\d+$)|.+(?=\.part\d+\..+$)", file_):
                name = match.group(0)
                ext = file_.split(name, 1)[1]
            elif len(fsplit := ospath.splitext(file_)) > 1:
                name = fsplit[0]
                ext = fsplit[1]
            else:
                name = file_
                ext = ""
            name = name[: 255 - len(ext)]
            file_ = f"{name}{ext}"

        if pre_file_ != file_:
            new_path = ospath.join(dirpath, file_)
            await rename(self._up_path, new_path)
            self._up_path = new_path

        return cap_mono

    def _get_input_media(self, subkey, key):
        rlist = []
        for msg in self._media_dict[key][subkey]:
            if key == "videos":
                input_media = InputMediaVideo(
                    media=msg.video.file_id, caption=msg.caption
                )
            else:
                input_media = InputMediaDocument(
                    media=msg.document.file_id, caption=msg.caption
                )
            rlist.append(input_media)
        return rlist

    async def _send_screenshots(self, dirpath, outputs):
        inputs = [
            InputMediaPhoto(ospath.join(dirpath, p), p.rsplit("/", 1)[-1])
            for p in outputs
        ]
        ss_client = self._client or self._listener.client
        for i in range(0, len(inputs), 10):
            batch = inputs[i : i + 10]
            if Config.BOT_PM:
                while True:
                    if self._listener.is_cancelled:
                        return
                    try:
                        await TgClient.bot.send_media_group(
                            chat_id=self._listener.user_id,
                            media=batch,
                            disable_notification=True,
                        )
                        break
                    except (FloodWait, FloodPremiumWait) as f:
                        LOGGER.warning(str(f))
                        await sleep(f.value * 1.3)
            msgs_list = await ss_client.send_media_group(
                chat_id=self._upload_chat_id,
                reply_to_message_id=self._reply_to_id,
                media=batch,
                disable_notification=True,
            )
            self._sent_msg = msgs_list[-1]
            self._reply_to_id = self._sent_msg.id

    async def _send_media_group(self, subkey, key, msgs):
        fetch_client = self._client or self._listener.client
        for index, msg in enumerate(msgs):
            msgs[index] = await fetch_client.get_messages(
                chat_id=msg[0], message_ids=msg[1]
            )
        first_msg = msgs[0]
        reply_to = first_msg.reply_to_message_id or self._reply_to_id
        msgs_list = await fetch_client.send_media_group(
            chat_id=self._upload_chat_id,
            reply_to_message_id=reply_to,
            media=self._get_input_media(subkey, key),
            disable_notification=True,
        )
        for msg in msgs:
            if msg.link in self._msgs_dict:
                del self._msgs_dict[msg.link]
            await delete_message(msg)
        del self._media_dict[key][subkey]
        if self._listener.is_super_chat or self._listener.up_dest:
            for m in msgs_list:
                self._msgs_dict[m.link] = m.caption
        self._sent_msg = msgs_list[-1]
        self._reply_to_id = self._sent_msg.id

    async def _copy_media(self):
        if (
            not self._bot_pm
            or not self._sent_msg
            or self._listener.is_cancelled
        ):
            return

        chat_id = self._listener.user_id
        from_chat_id = self._upload_chat_id
        message_id = self._sent_msg.id
        if from_chat_id == chat_id:
            return

        reply_to_message_id = self._listener.pm_msg.id if self._listener.pm_msg else None
        file_name = ospath.basename(self._up_path) if self._up_path else ""

        last_err = None
        flood_waits = 0
        total_wait = 0.0
        max_flood_waits = 10
        max_total_wait = 30 * 60
        for attempt in range(1, 7):
            if self._listener.is_cancelled:
                return
            try:
                await TgClient.bot.copy_message(
                    chat_id=chat_id,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                    reply_to_message_id=reply_to_message_id,
                )
                return
            except (FloodWait, FloodPremiumWait) as f:
                last_err = f
                delay = f.value * 1.3
                flood_waits += 1
                total_wait += delay
                LOGGER.warning(
                    f"FloodWait while copying to BotPM (attempt {attempt}/6): {f}"
                )
                await sleep(delay)
                if flood_waits >= max_flood_waits or total_wait >= max_total_wait:
                    break
            except BadRequest as e:
                last_err = e
                error_msg = str(e).lower()

                if reply_to_message_id is not None and any(x in error_msg for x in ["reply", "thread", "message to reply"]):
                    LOGGER.warning(
                        "BotPM copy failed with reply_to_message_id="
                        f"{reply_to_message_id}. Retrying without it: {e}"
                    )
                    reply_to_message_id = None
                    continue

                if any(x in error_msg for x in [
                    "can't copy",
                    "message not found",
                    "message to copy not found",
                    "message identifier is invalid"
                ]):
                    if attempt < 6:
                        backoff = min(2 ** attempt, 10)
                        LOGGER.warning(
                            f"BotPM copy: Message not accessible yet (attempt {attempt}/6). "
                            f"Possible propagation delay. Retrying after {backoff}s..."
                        )
                        await sleep(backoff)
                        continue
                    break

                break
            except RPCError as e:
                last_err = e
                backoff = min(2 ** (attempt - 1), 8)
                LOGGER.warning(
                    f"RPCError while copying to BotPM (attempt {attempt}/6): {e}"
                )
                await sleep(backoff)
            except Exception as e:
                last_err = e
                break

        if not self._listener.is_cancelled and last_err is not None:
            LOGGER.error(
                "Failed To Send in BotPM after retries: "
                f"{last_err} | user_id={chat_id} "
                f"from_chat_id={from_chat_id} message_id={message_id} file={file_name}"
            )

    async def upload(self):
        await self._user_settings()
        res = await self._msg_to_reply()
        if not res:
            return
        self._is_log_del = False
        items = []
        for dirpath, _, files in natsorted(await sync_to_async(walk, self._path)):
            if dirpath.strip().endswith("/yt-dlp-thumb"):
                continue
            if dirpath.strip().endswith("_mltbss"):
                await self._send_screenshots(dirpath, files)
                await rmtree(dirpath, ignore_errors=True)
                continue
            for file_ in natsorted(files):
                items.append((dirpath, file_))

        if self._hyper_ul and len(items) > 1:
            # HyperUpload: helper bots pre-upload several files at once;
            # a single sender then posts them strictly in natsorted order,
            # so series episodes and split parts always stay in sequence.
            await self._hyper_pipeline(items)
        else:
            await self._upload_items(items)
        if self._listener.is_cancelled:
            return
        for key, value in list(self._media_dict.items()):
            for subkey, msgs in list(value.items()):
                if len(msgs) > 1:
                    try:
                        await self._send_media_group(subkey, key, msgs)
                    except Exception as e:
                        LOGGER.info(
                            f"While sending media group at the end of task. Error: {e}"
                        )
        if self._total_files == 0:
            await self._cleanup_auto_thumb()
            await self._listener.on_upload_error(
                "No files to upload. This may be because Strict Mode is enabled (only videos ≥ 100MB are allowed) "
                "or because all files match the Excluded Extensions."
            )
            return
        if self._total_files <= self._corrupted:
            await self._cleanup_auto_thumb()
            await self._listener.on_upload_error(
                f"Files Corrupted or unable to upload. {self._error or 'Check logs!'}"
            )
            return
        LOGGER.info(f"Leech Completed: {self._listener.name}")
        await self._cleanup_auto_thumb()
        await self._listener.on_upload_complete(
            None, self._msgs_dict, self._total_files, self._corrupted
        )
        return


    async def _upload_items(self, items):
        for dirpath, file_ in items:
            self._error = ""
            self._up_path = f_path = ospath.join(dirpath, file_)
            if not await aiopath.exists(self._up_path):
                LOGGER.error(f"{self._up_path} not exists! Continue uploading!")
                continue
            try:
                f_size = await aiopath.getsize(self._up_path)

                is_allowed, reason = await check_strict_file_mode(self._up_path, file_)
                if not is_allowed:
                    LOGGER.info(f"STRICT_FILE_MODE: Skipping {reason}: {self._up_path}")
                    await remove(self._up_path)
                    continue
                else:
                    if Config.STRICT_FILE_MODE:
                        LOGGER.info(f"STRICT_FILE_MODE: Uploading video {file_} ({f_size / (1024*1024):.2f}MB)")

                self._total_files += 1

                self._prm_media = True if f_size > 2097152000 else False

                max_size = 4194304000 if (self._prm_media and TgClient.IS_PREMIUM_USER) else 2097152000
                if f_size > max_size:
                    raise ValueError(
                        f"File {self._up_path} ({f_size} bytes) exceeds max "
                        f"{max_size} bytes. File should have been split during download."
                    )

                await self._switching_client()

                if f_size == 0:
                    LOGGER.error(
                        f"{self._up_path} size is zero, telegram don't upload zero size files"
                    )
                    self._corrupted += 1
                    continue
                if self._listener.is_cancelled:
                    return
                await self._user_settings()
                cap_mono = await self._prepare_file(file_, dirpath)
                if self._last_msg_in_group:
                    group_lists = [
                        x for v in self._media_dict.values() for x in v.keys()
                    ]
                    match = re_match(r".+(?=\.0*\d+$)|.+(?=\.part\d+\..+$)", f_path)
                    if not match or match and match.group(0) not in group_lists:
                        for key, value in list(self._media_dict.items()):
                            for subkey, msgs in list(value.items()):
                                if len(msgs) > 1:
                                    await self._send_media_group(subkey, key, msgs)
                self._last_msg_in_group = False
                self._last_uploaded = 0
                if self._helper_index is not None:
                    TgClient.helper_loads[self._helper_index] += 1
                try:
                    await self._upload_file(cap_mono, file_, f_path)
                finally:
                    if self._helper_index is not None:
                        TgClient.helper_loads[self._helper_index] -= 1
                if self._log_msg and not self._is_log_del and Config.CLEAN_LOG_MSG:
                    await delete_message(self._log_msg)
                    self._is_log_del = True
                if self._listener.is_cancelled:
                    return
                if (
                    not self._is_corrupted
                    and (self._listener.is_super_chat or self._listener.up_dest)
                    and self._sent_msg is not None
                    and hasattr(self._sent_msg, "chat")
                    and self._sent_msg.chat is not None
                    and hasattr(self._sent_msg, "link")
                ):
                    self._msgs_dict[self._sent_msg.link] = file_
                if self._helper_index is None:
                    # flood-avoid delay for single-client uploads;
                    # HyperUpload rotates helper bots instead
                    await sleep(1)
            except CancelledUpload:
                return
            except Exception as err:
                LOGGER.error(f"{err}. Path: {self._up_path}", exc_info=True)
                self._error = str(err)
                self._corrupted += 1
                if self._listener.is_cancelled:
                    return
            if not self._listener.is_cancelled and await aiopath.exists(
                self._up_path
            ):
                await remove(self._up_path)

    async def _hyper_pipeline(self, items):
        """Parallel HyperUpload: helper bots pre-upload up to `slots`
        files concurrently while a single in-order sender posts each
        finished file, so aggregate speed scales with HELPER_TOKENS but
        series episodes and split parts never post out of order."""
        slots = len(TgClient.helper_bots)
        if Config.HYPER_THREADS:
            slots = min(slots, Config.HYPER_THREADS)
        slots = max(1, min(slots, 8))
        sem = Semaphore(slots)

        async def prefetch(dirpath, file_):
            async with sem:
                if self._listener.is_cancelled:
                    return None
                try:
                    return await self._hyper_prefetch(dirpath, file_)
                except Exception as e:
                    LOGGER.error(f"HyperUL prefetch failed: {e}", exc_info=True)
                    self._error = str(e)
                    self._corrupted += 1
                    return None

        # tasks acquire the semaphore in creation order, so earlier
        # episodes always get upload slots first
        tasks = [create_task(prefetch(d, f)) for d, f in items]
        try:
            for task in tasks:
                res = await task
                if self._listener.is_cancelled:
                    return
                if res is None:
                    continue
                try:
                    await self._hyper_send(res)
                except CancelledUpload:
                    return
        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()
            await gather(*tasks, return_exceptions=True)

    def _hyper_progress(self, client):
        state = {"last": 0}

        async def progress(current, _):
            if self._listener.is_cancelled:
                client.stop_transmission()
            self._processed_bytes += current - state["last"]
            state["last"] = current

        return progress

    async def _hyper_media_meta(self, file_):
        """Detect media kind and prepare thumb/dimensions for the current
        self._up_path (mirrors the classic _upload_file prep)."""
        thumb = self._thumb
        if thumb is not None and thumb != "none" and not await aiopath.exists(thumb):
            thumb = None
        is_video, is_audio, is_image = await get_document_type(self._up_path)
        meta = {
            "duration": 0,
            "width": 0,
            "height": 0,
            "performer": None,
            "title": None,
        }

        if not is_image and thumb is None:
            file_name = ospath.splitext(file_)[0]
            thumb_path = f"{self._path}/yt-dlp-thumb/{file_name}.jpg"
            if await aiopath.isfile(thumb_path):
                thumb = thumb_path
            elif await aiopath.isfile(thumb_path.replace("/yt-dlp-thumb", "")):
                thumb = thumb_path.replace("/yt-dlp-thumb", "")
            elif is_audio and not is_video:
                thumb = await get_audio_thumbnail(self._up_path)

        if self._listener.as_doc or (not is_video and not is_audio and not is_image):
            kind = "document"
            if is_video and thumb is None:
                thumb = await get_video_thumbnail(self._up_path, None)
        elif is_video:
            kind = "video"
            meta["duration"] = (await get_media_info(self._up_path))[0]
            if self._auto_thumb_enabled and thumb is None:
                from bot.helper.thumbnail_utils import ThumbnailFetcher

                self._auto_thumb_path = await ThumbnailFetcher.fetch_thumbnail(
                    ospath.basename(self._up_path), self._listener.user_id
                )
                if self._auto_thumb_path:
                    thumb = self._auto_thumb_path
            if thumb is None and self._listener.thumbnail_layout:
                thumb = await get_multiple_frames_thumbnail(
                    self._up_path,
                    self._listener.thumbnail_layout,
                    self._listener.screen_shots,
                )
            if thumb is None:
                thumb = await get_video_thumbnail(self._up_path, meta["duration"])
            if thumb is not None and thumb != "none":
                with Image.open(thumb) as img:
                    meta["width"], meta["height"] = img.size
            else:
                meta["width"], meta["height"] = 480, 320
        elif is_audio:
            kind = "audio"
            meta["duration"], meta["performer"], meta["title"] = await get_media_info(
                self._up_path
            )
        else:
            kind = "photo"

        if thumb == "none":
            thumb = None
        meta["kind"] = kind
        meta["thumb"] = thumb
        return meta

    async def _hyper_prefetch(self, dirpath, file_):
        """Prep one file and pre-upload its bytes with the least-loaded
        helper bot. Returns None to skip the file, or a dict for the
        in-order sender."""
        f_path = ospath.join(dirpath, file_)
        async with self._prep_lock:
            if self._listener.is_cancelled:
                return None
            self._error = ""
            self._up_path = f_path
            if not await aiopath.exists(self._up_path):
                LOGGER.error(f"{self._up_path} not exists! Continue uploading!")
                return None
            try:
                f_size = await aiopath.getsize(self._up_path)
                is_allowed, reason = await check_strict_file_mode(
                    self._up_path, file_
                )
                if not is_allowed:
                    LOGGER.info(
                        f"STRICT_FILE_MODE: Skipping {reason}: {self._up_path}"
                    )
                    await remove(self._up_path)
                    return None
                self._total_files += 1
                if f_size == 0:
                    LOGGER.error(
                        f"{self._up_path} size is zero, telegram don't upload zero size files"
                    )
                    self._corrupted += 1
                    return None
                prm = f_size > 2097152000
                max_size = (
                    4194304000 if (prm and TgClient.IS_PREMIUM_USER) else 2097152000
                )
                if f_size > max_size:
                    raise ValueError(
                        f"File {self._up_path} ({f_size} bytes) exceeds max "
                        f"{max_size} bytes. File should have been split during download."
                    )
                await self._user_settings()
                cap_mono = await self._prepare_file(file_, dirpath)
                up_path = self._up_path
                base = {
                    "cap": cap_mono,
                    "file": file_,
                    "path": up_path,
                    "f_path": f_path,
                }
                if prm:
                    # >2GB needs the premium user session; the sender
                    # falls back to the classic upload for this file
                    return {"mode": "classic", **base}
                meta = await self._hyper_media_meta(file_)
            except Exception as err:
                LOGGER.error(f"{err}. Path: {self._up_path}", exc_info=True)
                self._error = str(err)
                self._corrupted += 1
                return None

        # heavy byte transfer runs outside the lock, in parallel
        if not await aiopath.exists(up_path):
            LOGGER.error(
                f"HyperUL: file vanished before pre-upload, episode will be "
                f"missing from the sequence: {up_path}"
            )
            self._corrupted += 1
            return None
        index = min(TgClient.helper_loads, key=TgClient.helper_loads.get)
        client = TgClient.helper_bots[index]
        TgClient.helper_loads[index] += 1
        try:
            uploaded = None
            for attempt in range(3):
                if self._listener.is_cancelled:
                    return None
                try:
                    uploaded = await client.save_file(
                        up_path, progress=self._hyper_progress(client)
                    )
                    break
                except (FloodWait, FloodPremiumWait) as f:
                    LOGGER.warning(f"HyperUL save_file: {f}")
                    await sleep(f.value + 1)
                except StopTransmission:
                    return None
                except Exception as e:
                    if attempt == 2:
                        raise
                    LOGGER.warning(f"HyperUL save_file retry {attempt + 1}: {e}")
                    await sleep((attempt + 1) * 2)
            if uploaded is None:
                # pre-upload failed; keep order via classic re-upload
                return {"mode": "classic", **base}
            thumb_file = None
            if meta["thumb"]:
                try:
                    thumb_file = await client.save_file(meta["thumb"])
                except Exception as e:
                    LOGGER.warning(f"HyperUL thumb save failed: {e}")
            return {
                "mode": "hyper",
                "index": index,
                "client": client,
                "uploaded": uploaded,
                "thumb_file": thumb_file,
                "meta": meta,
                **base,
            }
        except Exception as err:
            LOGGER.warning(
                f"HyperUL pre-upload failed ({err}); will re-upload classically: {file_}"
            )
            return {"mode": "classic", **base}
        finally:
            TgClient.helper_loads[index] -= 1

    async def _hyper_send(self, res):
        """Ordered sender: posts one pre-uploaded file (or classic-uploads
        it as fallback), then runs the usual post-send bookkeeping.

        NOTE: prefetch workers mutate self._up_path under _prep_lock while
        this sender runs, so this method must only use its local up_path;
        touching self._up_path outside _prep_lock deletes/uploads the
        wrong (upcoming) file and silently drops episodes."""
        file_, f_path = res["file"], res["f_path"]
        up_path = res["path"]
        self._is_corrupted = False
        try:
            if self._last_msg_in_group:
                group_lists = [
                    x for v in self._media_dict.values() for x in v.keys()
                ]
                match = re_match(r".+(?=\.0*\d+$)|.+(?=\.part\d+\..+$)", f_path)
                if not match or match and match.group(0) not in group_lists:
                    for key, value in list(self._media_dict.items()):
                        for subkey, msgs in list(value.items()):
                            if len(msgs) > 1:
                                await self._send_media_group(subkey, key, msgs)
            self._last_msg_in_group = False

            if res["mode"] == "classic":
                # _upload_file works on self._up_path, which prefetch
                # workers also mutate — hold _prep_lock for the whole
                # classic upload so they can't swap it mid-transfer
                async with self._prep_lock:
                    self._up_path = up_path
                    f_size = await aiopath.getsize(up_path)
                    self._prm_media = f_size > 2097152000
                    await self._switching_client()
                    self._last_uploaded = 0
                    if self._helper_index is not None:
                        TgClient.helper_loads[self._helper_index] += 1
                    try:
                        await self._upload_file(res["cap"], file_, f_path)
                    finally:
                        if self._helper_index is not None:
                            TgClient.helper_loads[self._helper_index] -= 1
            else:
                client = res["client"]
                self._client = client
                meta = res["meta"]
                media = build_uploaded_media(
                    meta["kind"],
                    res["uploaded"],
                    up_path,
                    thumb_file=res["thumb_file"],
                    duration=meta["duration"],
                    width=meta["width"],
                    height=meta["height"],
                    performer=meta["performer"],
                    title=meta["title"],
                )
                sent = None
                last_exc = None
                for attempt in range(3):
                    if self._listener.is_cancelled:
                        raise CancelledUpload()
                    try:
                        sent = await raw_send_media(
                            client,
                            self._upload_chat_id,
                            media,
                            res["cap"],
                            reply_to_id=self._reply_to_id,
                        )
                        break
                    except (FloodWait, FloodPremiumWait) as f:
                        LOGGER.warning(f"HyperUL send: {f}")
                        await sleep(f.value + 1)
                    except Exception as e:
                        last_exc = e
                        break
                if sent is None:
                    LOGGER.warning(
                        f"HyperUL raw send failed ({last_exc}); re-uploading classically: {file_}"
                    )
                    async with self._prep_lock:
                        self._up_path = up_path
                        await self._switching_client()
                        self._last_uploaded = 0
                        await self._upload_file(res["cap"], file_, f_path)
                else:
                    self._sent_msg = sent
                    self._reply_to_id = sent.id
                    await self._post_send_actions(f_path)
                th = meta.get("thumb")
                if self._thumb is None and th and await aiopath.exists(th):
                    await remove(th)

            if self._log_msg and not self._is_log_del and Config.CLEAN_LOG_MSG:
                await delete_message(self._log_msg)
                self._is_log_del = True
            if self._listener.is_cancelled:
                return
            if (
                not self._is_corrupted
                and (self._listener.is_super_chat or self._listener.up_dest)
                and self._sent_msg is not None
                and hasattr(self._sent_msg, "chat")
                and self._sent_msg.chat is not None
                and hasattr(self._sent_msg, "link")
            ):
                self._msgs_dict[self._sent_msg.link] = file_
        except CancelledUpload:
            raise
        except Exception as err:
            LOGGER.error(f"{err}. Path: {up_path}", exc_info=True)
            self._error = str(err)
            self._corrupted += 1
        # clean up THIS file only — self._up_path may already point to a
        # later file being prepped by a prefetch worker
        if not self._listener.is_cancelled and await aiopath.exists(up_path):
            await remove(up_path)

    async def _cleanup_auto_thumb(self):
        if self._auto_thumb_path:
            from bot.helper.thumbnail_utils import ThumbnailFetcher
            await ThumbnailFetcher.cleanup_thumbnail(self._auto_thumb_path)
            self._auto_thumb_path = None

    async def _send_with_floodwait_retry(self, send_method, **kwargs):
        base_processed = self._processed_bytes

        try:
            from pyrogram.errors import SlowmodeWait as _SlowmodeWait
        except ImportError:
            _SlowmodeWait = FloodWait

        wait_exc_types = (FloodWait, FloodPremiumWait, _SlowmodeWait)

        for attempt in range(3):
            self._last_uploaded = 0

            try:
                result = await send_method(**kwargs)
                if result:
                    return result
                if attempt < 2:
                    self._check_cancelled()
                    self._processed_bytes = base_processed
                    await sleep(2 ** attempt)
            except wait_exc_types as f:
                if attempt == 2:
                    raise
                self._check_cancelled()
                LOGGER.warning(str(f))
                await sleep(getattr(f, "value", 5) + 1)
                self._check_cancelled()
                self._processed_bytes = base_processed

        raise RuntimeError("send_* returned None after 3 attempts")

    async def _upload_file(self, cap_mono, file, o_path, force_document=False):
        if self._client is None:
            raise ValueError("Upload client not initialized -- _switching_client was not called")
        if not self._upload_chat_id:
            raise ValueError("Upload chat ID not set -- _msg_to_reply was not called")
        self._check_cancelled()
        if not await aiopath.exists(self._up_path):
            self._check_cancelled()
            raise FileNotFoundError(self._up_path)

        if (
            self._thumb is not None
            and not await aiopath.exists(self._thumb)
            and self._thumb != "none"
        ):
            self._thumb = None
        thumb = self._thumb
        self._is_corrupted = False
        try:
            self._check_cancelled()
            is_video, is_audio, is_image = await get_document_type(self._up_path)

            if not is_image and thumb is None:
                file_name = ospath.splitext(file)[0]
                thumb_path = f"{self._path}/yt-dlp-thumb/{file_name}.jpg"
                if await aiopath.isfile(thumb_path):
                    thumb = thumb_path
                elif await aiopath.isfile(thumb_path.replace("/yt-dlp-thumb", "")):
                    thumb = thumb_path.replace("/yt-dlp-thumb", "")
                elif is_audio and not is_video:
                    thumb = await get_audio_thumbnail(self._up_path)

            if (
                self._listener.as_doc
                or force_document
                or (not is_video and not is_audio and not is_image)
            ):
                key = "documents"
                if is_video and thumb is None:
                    thumb = await get_video_thumbnail(self._up_path, None)

                self._check_cancelled()
                if thumb == "none":
                    thumb = None
                self._sent_msg = await self._send_with_floodwait_retry(
                    self._client.send_document,
                    chat_id=self._upload_chat_id,
                    reply_to_message_id=self._reply_to_id,
                    document=self._up_path,
                    thumb=thumb,
                    caption=cap_mono,
                    disable_notification=True,
                    progress=self._upload_progress,
                )
                self._check_cancelled()
                if not self._sent_msg:
                    self._check_cancelled()
                    raise RuntimeError("Telegram upload returned no message")
                self._reply_to_id = self._sent_msg.id
            elif is_video:
                key = "videos"
                self._check_cancelled()
                duration = (await get_media_info(self._up_path))[0]

                if self._auto_thumb_enabled and thumb is None:
                    from bot.helper.thumbnail_utils import ThumbnailFetcher

                    filename = ospath.basename(self._up_path)
                    LOGGER.info(f"Attempting auto-thumbnail for: {filename}")

                    self._auto_thumb_path = await ThumbnailFetcher.fetch_thumbnail(
                        filename, self._listener.user_id
                    )
                    if self._auto_thumb_path:
                        thumb = self._auto_thumb_path
                        LOGGER.info(f"Using auto-fetched thumbnail: {thumb}")

                if thumb is None and self._listener.thumbnail_layout:
                    thumb = await get_multiple_frames_thumbnail(
                        self._up_path,
                        self._listener.thumbnail_layout,
                        self._listener.screen_shots,
                    )
                if thumb is None:
                    thumb = await get_video_thumbnail(self._up_path, duration)
                if thumb is not None and thumb != "none":
                    with Image.open(thumb) as img:
                        width, height = img.size
                else:
                    width = 480
                    height = 320
                self._check_cancelled()
                if thumb == "none":
                    thumb = None
                self._sent_msg = await self._send_with_floodwait_retry(
                    self._client.send_video,
                    chat_id=self._upload_chat_id,
                    reply_to_message_id=self._reply_to_id,
                    video=self._up_path,
                    caption=cap_mono,
                    duration=duration,
                    width=width,
                    height=height,
                    thumb=thumb,
                    supports_streaming=True,
                    disable_notification=True,
                    progress=self._upload_progress,
                )
                self._check_cancelled()
                if not self._sent_msg:
                    self._check_cancelled()
                    raise RuntimeError("Telegram upload returned no message")
                self._reply_to_id = self._sent_msg.id
            elif is_audio:
                key = "audios"
                self._check_cancelled()
                duration, artist, title = await get_media_info(self._up_path)
                self._check_cancelled()
                if thumb == "none":
                    thumb = None
                self._sent_msg = await self._send_with_floodwait_retry(
                    self._client.send_audio,
                    chat_id=self._upload_chat_id,
                    reply_to_message_id=self._reply_to_id,
                    audio=self._up_path,
                    caption=cap_mono,
                    duration=duration,
                    performer=artist,
                    title=title,
                    thumb=thumb,
                    disable_notification=True,
                    progress=self._upload_progress,
                )
                self._check_cancelled()
                if not self._sent_msg:
                    self._check_cancelled()
                    raise RuntimeError("Telegram upload returned no message")
                self._reply_to_id = self._sent_msg.id
            else:
                key = "photos"
                self._check_cancelled()
                self._sent_msg = await self._send_with_floodwait_retry(
                    self._client.send_photo,
                    chat_id=self._upload_chat_id,
                    reply_to_message_id=self._reply_to_id,
                    photo=self._up_path,
                    caption=cap_mono,
                    disable_notification=True,
                    progress=self._upload_progress,
                )
                self._check_cancelled()
                if not self._sent_msg:
                    self._check_cancelled()
                    raise RuntimeError("Telegram upload returned no message")
                self._reply_to_id = self._sent_msg.id

            await self._post_send_actions(o_path)

            if (
                self._thumb is None
                and thumb is not None
                and await aiopath.exists(thumb)
            ):
                await remove(thumb)
        except CancelledUpload:
            raise
        except FileNotFoundError:
            self._check_cancelled()
            raise
        except (
            PeerIdInvalid,
            ChannelInvalid,
            ChatWriteForbidden,
            ChatAdminRequired,
        ) as err:
            if self._helper_index is not None and self._hyper_ul:
                # Helper bot can't post in this chat (not admin/member).
                # Disable HyperUpload for this task and retry with the
                # default client so the upload keeps its sequence.
                LOGGER.warning(
                    f"HyperUpload: helper bot can't post in chat "
                    f"{self._upload_chat_id} ({err}). Falling back to default client."
                )
                self._hyper_ul = False
                self._user_session = False
                self._client = self._listener.client
                return await self._upload_file(cap_mono, file, o_path, force_document)
            raise
        except Exception as err:
            if (
                self._thumb is None
                and thumb is not None
                and await aiopath.exists(thumb)
            ):
                await remove(thumb)
            err_type = "RPCError: " if isinstance(err, RPCError) else ""
            LOGGER.error(f"{err_type}{err}. Path: {self._up_path}", exc_info=True)
            if isinstance(err, BadRequest) and key != "documents":
                LOGGER.error(f"Retrying As Document. Path: {self._up_path}")
                return await self._upload_file(cap_mono, file, o_path, True)
            raise err

    async def _post_send_actions(self, o_path):
        if (
            not self._listener.is_cancelled
            and self._media_group
            and (self._sent_msg.video or self._sent_msg.document)
        ):
            key = "documents" if self._sent_msg.document else "videos"
            if match := re_match(r".+(?=\.0*\d+$)|.+(?=\.part\d+\..+$)", o_path):
                pname = match.group(0)
                if pname in self._media_dict[key].keys():
                    self._media_dict[key][pname].append(
                        [self._upload_chat_id, self._sent_msg.id]
                    )
                else:
                    self._media_dict[key][pname] = [
                        [self._upload_chat_id, self._sent_msg.id]
                    ]
                msgs = self._media_dict[key][pname]
                if len(msgs) == 10:
                    await self._send_media_group(pname, key, msgs)
                else:
                    self._last_msg_in_group = True

        if self._sent_msg:
            await sleep(0.6)
            await self._copy_media()
            if self._listener.leech_dest:
                try:
                    leech_dest = self._listener.leech_dest
                    if not isinstance(leech_dest, int):
                        if leech_dest.lstrip("-").isdigit():
                            leech_dest = int(leech_dest)
                    await TgClient.bot.copy_message(
                        chat_id=leech_dest,
                        from_chat_id=self._upload_chat_id,
                        message_id=self._sent_msg.id,
                        message_thread_id=self._listener.leech_dest_thread_id,
                    )
                except Exception as e:
                    if not self._listener.is_cancelled:
                        LOGGER.error(
                            f"Failed to forward to {self._listener.leech_dest}: {e}"
                        )
                        await send_message(
                            self._listener.user_id,
                            f"Failed to forward to {self._listener.leech_dest}\n{e}",
                        )

            selected_dumps = self._listener.selected_dumps
            ldumps = self._listener.user_dict.get("LDUMP", {})

            if selected_dumps is not None:
                if isinstance(selected_dumps, list):
                    dumps_to_forward = {f"dump_{i}": d for i, d in enumerate(selected_dumps)}
                else:
                    dumps_to_forward = {"selected": selected_dumps}
            elif ldumps:
                dumps_to_forward = ldumps
            else:
                dumps_to_forward = {}
            
            for dump_name, dump_chat in dumps_to_forward.items():
                try:
                    dump_thread_id = None
                    if not isinstance(dump_chat, int):
                        if str(dump_chat).lower() == "pm":
                            dump_chat = self._listener.user_id
                        elif "|" in str(dump_chat):
                            parts = str(dump_chat).split("|", 1)
                            dump_chat = parts[0]
                            if parts[1].lstrip("-").isdigit():
                                dump_thread_id = int(parts[1])
                            if dump_chat.lstrip("-").isdigit():
                                dump_chat = int(dump_chat)
                        elif str(dump_chat).lstrip("-").isdigit():
                            dump_chat = int(dump_chat)

                    if (dump_chat, dump_thread_id) == (self._upload_chat_id, self._listener.chat_thread_id):
                        continue
                    if self._listener.leech_dest:
                        leech_dest_comp = self._listener.leech_dest
                        if not isinstance(leech_dest_comp, int):
                            if leech_dest_comp.lstrip("-").isdigit():
                                leech_dest_comp = int(leech_dest_comp)
                        if (dump_chat, dump_thread_id) == (leech_dest_comp, self._listener.leech_dest_thread_id):
                            continue

                    await TgClient.bot.copy_message(
                        chat_id=dump_chat,
                        from_chat_id=self._upload_chat_id,
                        message_id=self._sent_msg.id,
                        message_thread_id=dump_thread_id,
                    )
                except Exception as e:
                    if not self._listener.is_cancelled:
                        LOGGER.error(
                            f"Failed to forward to LDUMP '{dump_name}' ({dump_chat}): {e}"
                        )


    @property
    def hyper(self):
        return self._hyper_ul

    @property
    def speed(self):
        try:
            return self._processed_bytes / (time() - self._start_time)
        except ZeroDivisionError:
            return 0

    @property
    def processed_bytes(self):
        return self._processed_bytes

    async def cancel_task(self):
        self._listener.is_cancelled = True
        await self._cleanup_auto_thumb()
        await self._listener.on_upload_error("your upload has been stopped!")
