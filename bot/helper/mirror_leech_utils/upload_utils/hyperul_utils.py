# This file is a part of NEO-WZML (github.com/irisXDR/NEO-WZML)
#
# HyperUpload raw helpers: pre-upload file bytes with helper bot clients
# (client.save_file) so several files climb to Telegram in parallel, then
# post each message near-instantly with messages.SendMedia. Posting stays
# strictly sequential in the uploader, so series episodes and split parts
# always land in order while the heavy byte transfer runs concurrently.

from mimetypes import guess_type
from os import path as ospath

from pyrogram import raw
from pyrogram.session.internals import MsgId

from bot import LOGGER


def guess_mime(path, default="application/octet-stream"):
    return guess_type(path)[0] or default


async def parse_caption(client, caption):
    if not caption:
        return "", None
    try:
        parsed = await client.parser.parse(caption)
        return parsed.get("message") or "", parsed.get("entities") or None
    except Exception as e:
        LOGGER.warning(f"HyperUL caption parse failed, sending raw text: {e}")
        return caption, None


def build_uploaded_media(
    kind,
    uploaded_file,
    file_path,
    thumb_file=None,
    duration=0,
    width=0,
    height=0,
    performer=None,
    title=None,
):
    """Build a raw InputMedia* from a pre-uploaded InputFile."""
    if kind == "photo":
        return raw.types.InputMediaUploadedPhoto(file=uploaded_file)

    file_name = ospath.basename(file_path)
    attributes = [raw.types.DocumentAttributeFilename(file_name=file_name)]
    force_file = False

    if kind == "video":
        attributes.append(
            raw.types.DocumentAttributeVideo(
                duration=duration,
                w=width or 480,
                h=height or 320,
                supports_streaming=True,
            )
        )
        mime = guess_mime(file_path, "video/mp4")
    elif kind == "audio":
        attributes.append(
            raw.types.DocumentAttributeAudio(
                duration=duration,
                performer=performer,
                title=title,
            )
        )
        mime = guess_mime(file_path, "audio/mpeg")
    else:
        force_file = True
        mime = guess_mime(file_path)

    return raw.types.InputMediaUploadedDocument(
        file=uploaded_file,
        mime_type=mime,
        attributes=attributes,
        thumb=thumb_file,
        force_file=force_file,
    )


async def raw_send_media(
    client,
    chat_id,
    media,
    caption,
    reply_to_id=None,
    thread_id=None,
):
    """Send a pre-uploaded media via raw SendMedia; return the full
    pyrogram Message (fetched back so all downstream code — links,
    media groups, copy_message — keeps working unchanged)."""
    peer = await client.resolve_peer(chat_id)
    text, entities = await parse_caption(client, caption)

    reply_to = None
    if reply_to_id or thread_id:
        try:
            reply_to = raw.types.InputReplyToMessage(
                reply_to_msg_id=reply_to_id or thread_id,
                top_msg_id=thread_id if reply_to_id else None,
            )
        except Exception:
            reply_to = None

    r = await client.invoke(
        raw.functions.messages.SendMedia(
            peer=peer,
            media=media,
            message=text,
            random_id=MsgId(),
            entities=entities,
            silent=True,
            reply_to=reply_to,
        )
    )

    msg_id = None
    for update in r.updates:
        if isinstance(
            update,
            (raw.types.UpdateNewMessage, raw.types.UpdateNewChannelMessage),
        ):
            msg_id = update.message.id
            break
        if isinstance(update, raw.types.UpdateMessageID):
            msg_id = update.id

    if msg_id is None:
        raise ValueError("HyperUL: SendMedia returned no message id")

    return await client.get_messages(chat_id=chat_id, message_ids=msg_id)


def tgram_engine_version():
    """Detect which pyrogram-compatible library is installed so the
    status engine tag is truthful (wzgram ships as module `pyrogram`)."""
    from importlib.metadata import version as pkg_version, PackageNotFoundError

    for dist, label in (("wzgram", "wzgram"), ("pyroblack", "Pyro")):
        try:
            return f"{label} v{pkg_version(dist)}"
        except PackageNotFoundError:
            continue
    from pyrogram import __version__ as pyrover

    return f"Pyro v{pyrover}"
