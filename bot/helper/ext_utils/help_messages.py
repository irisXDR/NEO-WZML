# This file is a part of NEO-WZML (github.com/irisXDR/NEO-WZML)

mirror = """<b>✦ MIRROR COMMAND</b>

<b>Basic Usage:</b>
• <code>/cmd link</code> - Mirror a direct link
• <code>/cmd</code> (reply to file/link) - Mirror replied content

<b>Common Arguments:</b>
• <code>-n filename</code> - Rename the file
• <code>-e</code> or <code>-e password</code> - Extract archives
• <code>-z</code> or <code>-z password</code> - Zip files before upload
• <code>-zim</code> - Zip only images into one archive
• <code>-up destination</code> - Custom upload location (supports <code>|topic_id</code>)

<b>Examples:</b>
<code>/mirror https://example.com/file.zip</code>
<code>/mirror link -n NewName -z</code>
<code>/mirror link -e password123 -up gdrive:</code>

<b>Note:</b> Commands starting with <b>qb</b> are for torrents only."""

yt = """<b>✦ YT-DLP COMMAND</b>

<b>Basic Usage:</b>
• <code>/cmd link</code> - Download video/audio
• <code>/cmd</code> (reply to link) - Download replied link

<b>Common Arguments:</b>
• <code>-n name</code> - Custom filename
• <code>-z password</code> - Zip after download
• <code>-zim</code> - Zip only images into one archive
• <code>-s</code> - Show quality selection menu
• <code>-opt {json}</code> - Custom yt-dlp options

<b>Examples:</b>
<code>/ytdl https://youtube.com/watch?v=xxx</code>
<code>/ytdl link -n "My Video" -s</code>
<code>/ytdl link -opt {"format": "bestaudio"}</code>

<b>Resources:</b>
• <a href='https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md'>Supported Sites</a>
• <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L212'>All Options</a>"""

clone = """<b>✦ CLONE COMMAND</b>

<b>Supported Sources:</b>
• Google Drive links
• GDTot, FilePress, FileBee, AppDrive, GDFlix links
• Rclone paths

<b>Basic Usage:</b>
• <code>/clone gdrive_link</code> - Clone to default destination
• <code>/clone rcl</code> - Interactive remote selection

<b>Arguments:</b>
• <code>-up destination</code> - Custom upload path
• <code>-sync</code> - Use rclone sync method

<b>Examples:</b>
<code>/clone https://drive.google.com/file/d/xxx</code>
<code>/clone remote:path -up gdrive:</code>
<code>/clone rcl -up rcl -sync</code>"""

new_name = """<b>✦ RENAME FILE</b>: <code>-n</code>

<b>Usage:</b>
<code>/cmd link -n new filename</code>

<b>Examples:</b>
<code>/mirror link -n Movie.2024.1080p</code>
<code>/ytdl link -n "My Downloaded Video"</code>

<b>Note:</b> Does not work with torrents (torrent name is fixed)."""

multi_link = """<b>✦ MULTI-LINK DOWNLOAD</b>: <code>-i</code>

<b>Usage:</b> Reply to the first link/file with:
<code>/cmd -i NUMBER</code>

<b>How it works:</b>
• Downloads NUMBER of consecutive messages
• Each link is processed as a separate task

<b>Example:</b>
<code>/mirror -i 5</code> (downloads next 5 links/files)"""

same_dir = """<b>✦ SAME DIRECTORY</b>: <code>-m</code>

<b>Purpose:</b> Group multiple files into one folder before upload.

<b>Usage:</b>
<code>/cmd link -m FolderName</code>
<code>/cmd -i 10 -m FolderName</code> (multi-link)
<code>/cmd -b -m FolderName</code> (bulk)

<b>With Bulk (-b):</b>
You can assign different folders per link:
<code>
link1 -m Folder1
link2 -m Folder1
link3 -m Folder2
link4
</code>
• link1 + link2 → uploaded from Folder1
• link3 → uploaded from Folder2
• link4 → uploaded normally (no folder)"""

thumb = """<b>✦ CUSTOM THUMBNAIL</b>: <code>-t</code>

<b>Usage:</b>
<code>/cmd link -t image-url</code>
<code>/cmd link -t tg_message_link</code>
<code>/cmd link -t none</code>

<b>Options:</b>
• <code>image-url</code> - Direct image URL (jpg, png, webp, etc.)
• <code>tg_message_link</code> - Link to a photo/document message
• <code>none</code> - Upload without thumbnail

<b>Example:</b>
<code>/leech link -t https://t.me/channel/123</code>
<code>/leech link -t https://example.com/thumb.jpg</code>"""

split_size = """<b>✦ SPLIT SIZE</b>: <code>-sp</code>

<b>Purpose:</b> Override default split size for large files.

<b>Usage:</b>
<code>/cmd link -sp SIZE</code>

<b>Format:</b>
• <code>500mb</code> or <code>2gb</code> - With unit
• <code>4000000000</code> - Bytes (no unit)

<b>Examples:</b>
<code>/leech link -sp 1gb</code>
<code>/leech link -sp 500mb</code>

<b>Note:</b> Only <code>mb</code> and <code>gb</code> units supported."""

upload = """<b>✦ UPLOAD DESTINATION</b>: <code>-up</code>

<b>Interactive Selection:</b>
• <code>-up rcl</code> - Select Rclone remote via buttons
• <code>-up gdl</code> - Select GDrive folder via buttons

<b>Direct Paths:</b>
• <code>-up remote:folder</code> - Rclone path
• <code>-up GDRIVE_ID</code> - Google Drive folder ID
• <code>-up gd</code> - Use default GDRIVE_ID
• <code>-up rc</code> - Use default RCLONE_PATH
• <code>-up tbx</code> - Upload to your TeraBox account (terabox.txt cookie)
• <code>-up tbx:/Folder</code> - TeraBox upload into a specific folder

<b>Telegram (Leech only):</b>
• <code>-up @channel</code> or <code>-up chat_id</code>
• <code>-up pm</code> - Send to private message
• <code>-up chat_id|topic_id</code> - Send to specific forum topic
• <code>-up @channel|123</code> - Channel by username, thread ID 123

<b>Topic Syntax:</b>
Works for any Telegram destination in leech mode.
Format: <code>chat_id|topic_id</code> (pipe separator, no spaces).
• <code>/leech link -up -100123456789|55</code> - Chat ID with topic 55
• <code>/leech link -up @mychannel|42</code> - Username with topic 42
Topics only apply to forum/supergroup chats with topics enabled.

<b>Upload Method Prefixes:</b>
• <code>b:</code> - Force bot session
• <code>u:</code> - Force user session
• <code>h:</code> - Hybrid (auto-select by size)

<b>User Config Prefixes:</b>
• <code>mrcc:</code> - User's rclone config
• <code>mtp:</code> - User's token.pickle

<b>GDrive Auth Prefixes:</b>
• <code>tp:</code> - Use token.pickle
• <code>sa:</code> - Use service account

<b>Examples:</b>
<code>/mirror link -up gdrive:Movies/2024</code>
<code>/leech link -up b:@mychannel</code>
<code>/leech link -up @mychannel|123</code>
<code>/mirror link -up mtp:GDRIVE_ID</code>"""

dump_select = """<b>✦ DUMP SELECTION</b>: <code>-ud</code>

<b>Purpose:</b> Select custom LDUMP channel(s) when leeching. Max 3 per task.

<b>Single Dump:</b>
<code>/leech link -ud Movies</code> - Send to "Movies" dump only

<b>Multi-Select (comma-separated, max 3):</b>
<code>/leech link -ud Movies,Anime</code> - Send to both dumps
<code>/leech link -ud all</code> - Send to ALL configured dumps

<b>Interactive Selection:</b>
• If no <code>-ud</code> specified and multiple dumps exist: checkbox UI (max 3)
• Click dumps to toggle selection on/off
• "Select All" selects all dumps (no cap)
• "Done" confirms, "Cancel" aborts
• Timeout (60s) uses ALL dumps if nothing selected

<b>Behavior:</b>
• If only 1 dump configured: Auto-selects that dump
• Dump names are case-insensitive
• Duplicate names are silently deduplicated

<b>Note:</b> Configure dumps in /usetting → Leech Settings → Leech Dump
Use DUMP_MODE toggle to temporarily enable/disable dumping."""

user_download = """<b>✦ USER DOWNLOAD</b>

<b>Purpose:</b> Control which credentials to use for GDrive downloads.

<b>Prefixes:</b>
• <code>tp:</code> - Use owner's token.pickle
• <code>sa:</code> - Use service account
• <code>mtp:</code> - Use your uploaded token.pickle
• <code>mrcc:</code> - Use your rclone config

<b>Examples:</b>
<code>/mirror tp:gdrive_link</code> - Download with owner token
<code>/mirror sa:gdrive_id</code> - Download with service account
<code>/mirror mtp:gdrive_link</code> - Download with your token
<code>/mirror mrcc:remote:path</code> - Download with your rclone"""

rcf = """<b>✦ RCLONE FLAGS</b>: <code>-rcf</code>

<b>Usage:</b>
<code>/cmd link -rcf flag:value|flag|flag:value</code>

<b>Format:</b> Pipe-separated key:value pairs

<b>Examples:</b>
<code>/mirror link -rcf --buffer-size:8M</code>
<code>/mirror link -rcf --drive-starred-only|--fast-list</code>
<code>/clone rcl -rcf --transfers:4|--checkers:8</code>

<b>Note:</b> Overrides all flags except <code>--exclude</code>

<b>Reference:</b> <a href='https://rclone.org/flags/'>All Rclone Flags</a>"""

bulk = """<b>✦ BULK DOWNLOAD</b>: <code>-b</code>

<b>Usage:</b> Reply to a text message or file containing links:
<code>/cmd -b</code>

<b>Link File Format:</b> One link per line with optional arguments:
<code>
link1 -n NewName1 -up remote1:
link2 -z -up remote2:
link3 -e password
</code>

<b>Global Arguments:</b>
Arguments with the command apply to ALL links:
<code>/cmd -b -z -up remote:</code> (zip all, same destination)

<b>Range Selection:</b>
• <code>-b start:end</code> - Process links from start to end
• <code>-b :5</code> - First 5 links only
• <code>-b 3:</code> - From link 3 onwards

<b>Example:</b>
<code>/mirror -b 1:10</code> (process links 1-10 only)"""

rlone_dl = """<b>✦ RCLONE DOWNLOAD</b>

<b>Usage:</b> Use rclone paths like direct links:
<code>/cmd remote:path/file.iso</code>
<code>/cmd rcl</code> (interactive selection)

<b>Web file selection:</b>
With <code>/cmd rcl</code>, pick a remote + folder, then a <b>web selector</b>
opens (when a public <code>BASE_URL</code> is set) to tick exactly which files to
download. Pick a single file to grab just that one.

<b>User Config:</b>
Add <code>mrcc:</code> prefix to use your uploaded rclone config:
<code>/cmd mrcc:remote:path/file</code>

<b>Examples:</b>
<code>/mirror gdrive:Movies/movie.mkv</code>
<code>/mirror rcl</code> (select via buttons)
<code>/mirror mrcc:mydrive:backup/</code>"""

terabox_dl = """<b>✦ TERABOX (own account)</b>

<b>Usage:</b> Browse your own TeraBox cloud and pick what to grab:
<code>/leech tbx</code> (interactive selection)
<code>/mirror tbx</code> (interactive selection)

Opens the <b>web file selector</b> (when a public <code>BASE_URL</code> is set):
your whole account is listed as a tickable folder tree — choose files, then
press <b>Done Selecting</b> to start. Without a BASE_URL it falls back to a
Telegram button menu.

<b>Note:</b> needs your <code>terabox.txt</code> cookie (User Settings → Private
Files, or the owner's global one). For public share links just paste the URL
directly (no <code>tbx</code> needed)."""

extract_zip = """<b>✦ EXTRACT / ZIP</b>: <code>-e</code> <code>-z</code>

<b>Extract Archives:</b>
• <code>-e</code> - Extract archive
• <code>-e password</code> - Extract with password

<b>Zip Files:</b>
• <code>-z</code> - Zip before upload
• <code>-z password</code> - Password-protected zip
• <code>-zim</code> / <code>-zipimages</code> - Zip only images; keep other files normal

<b>Both Together:</b>
<code>/cmd link -e -z</code> (extract first, then zip result)
<code>/cmd link -e pass1 -z pass2</code> (extract with pass1, zip with pass2)

<b>Examples:</b>
<code>/mirror link -e</code>
<code>/mirror link -z mypassword</code>
<code>/mirror link -e oldpass -z newpass</code>

<b>Note:</b> When using both, extraction happens first."""

join = """<b>✦ JOIN SPLIT FILES</b>: <code>-j</code>

<b>Purpose:</b> Merge split archive parts (like .001, .002, etc.)

<b>Usage:</b>
<code>/cmd link -j</code>
<code>/cmd -i 3 -j -m folder</code> (multi-link + join + same dir)
<code>/cmd -b -j -m folder</code> (bulk + join + same dir)

<b>Note:</b> Join runs BEFORE extract and zip operations.

<b>Tip:</b> Usually combined with <code>-m</code> (same directory) to group split files."""

merge_video = """<b>✦ MERGE VIDEOS</b>: <code>-mv</code>

<b>Purpose:</b> Merge all video files in a folder into a single .mkv file using ffmpeg concat (stream copy, no re-encode).

<b>Usage:</b>
<code>/cmd link -mv</code>
<code>/cmd link -m folder -mv</code>

<b>Examples:</b>
<code>/leech link -mv</code>
<code>/mirror link -mv</code>

<b>Note:</b> Runs after join but before extract. Original video files are removed after successful merge."""

tg_links = """<b>✦ TELEGRAM LINKS</b>

<b>Supported Formats:</b>
• Public: <code>https://t.me/channel_name/message_id</code>
• Private: <code>tg://openmessage?user_id=xxx&message_id=xxx</code>
• Supergroup: <code>https://t.me/c/channel_id/message_id</code>

<b>Range Download:</b>
• <code>https://t.me/channel/100-150</code> (messages 100 to 150)
• <code>tg://openmessage?user_id=xxx&message_id=555-560</code>

<b>Usage:</b>
<code>/cmd tg_link</code>
Reply to range link with <code>/cmd</code>

<b>Note:</b> Private channels require USER_SESSION_STRING to be configured."""

sample_video = """<b>✦ SAMPLE VIDEO</b>: <code>-sv</code>

<b>Purpose:</b> Create a short preview clip from videos.

<b>Usage:</b>
<code>/cmd link -sv</code> (default: 60s sample, 4s parts)
<code>/cmd link -sv duration:part</code>

<b>Format:</b> <code>-sv sample_duration:part_duration</code>

<b>Examples:</b>
<code>/mirror link -sv</code> (default values)
<code>/mirror link -sv 90:5</code> (90s sample, 5s parts)
<code>/mirror link -sv :3</code> (default duration, 3s parts)
<code>/mirror link -sv 120</code> (120s sample, default parts)"""

screenshot = """<b>✦ SCREENSHOTS</b>: <code>-ss</code>

<b>Purpose:</b> Generate screenshot images from videos.

<b>Usage:</b>
<code>/cmd link -ss</code> (default: 10 screenshots)
<code>/cmd link -ss NUMBER</code>

<b>Examples:</b>
<code>/mirror link -ss</code> (10 screenshots)
<code>/mirror link -ss 6</code> (6 screenshots)
<code>/mirror link -ss 20</code> (20 screenshots)"""

seed = """<b>✦ TORRENT SEEDING</b>: <code>-d</code>

<b>Purpose:</b> Control seeding ratio and time after torrent download.

<b>Usage:</b>
<code>/cmd link -d ratio:time</code>

<b>Format:</b>
• <code>ratio</code> - Seed until this upload/download ratio
• <code>time</code> - Seed for this many minutes

<b>Examples:</b>
<code>/qbmirror magnet -d 1.0:60</code> (ratio 1.0 OR 60 minutes)
<code>/qbmirror magnet -d 0.5</code> (ratio 0.5 only)
<code>/qbmirror magnet -d :30</code> (30 minutes only)"""

zip_arg = """<b>✦ ZIP FILES</b>: <code>-z</code>

<b>Usage:</b>
<code>/cmd link -z</code> (zip without password)
<code>/cmd link -z password</code> (password-protected zip)

<b>Examples:</b>
<code>/mirror link -z</code>
<code>/mirror link -z mySecretPass</code>"""

zip_images = """<b>✦ ZIP IMAGES ONLY</b>: <code>-zim</code> <code>-zipimage</code> <code>-zipimages</code>

<b>Purpose:</b> Move image files from the download tree into one ZIP archive while leaving videos and other files uploaded normally.

<b>Usage:</b>
<code>/cmd link -zim</code>
<code>/cmd link -s -zim</code> (works after torrent/Mega file selection)

<b>Behavior:</b>
• Images in folders/subfolders are preserved inside <code>Images.zip</code>
• Videos and other non-image files remain in their original folders
• If <code>-z</code> is also used, the normal full ZIP takes precedence"""

qual = """<b>✦ QUALITY SELECTION</b>: <code>-s</code>

<b>Purpose:</b> Show quality selection menu for yt-dlp downloads.

<b>When to use:</b>
• Override default quality from YT_DLP_OPTIONS
• Select specific quality for individual links
• Works with multi-link feature

<b>Usage:</b>
<code>/ytdl link -s</code>

<b>Example:</b>
<code>/ytdl https://youtube.com/watch?v=xxx -s</code>"""

yt_opt = """<b>✦ YT-DLP OPTIONS</b>: <code>-opt</code>

<b>Purpose:</b> Pass custom yt-dlp options as JSON dictionary.

<b>Usage:</b>
<code>/cmd link -opt {json_options}</code>

<b>Common Options:</b>
• <code>"format": "bestaudio"</code> - Audio only
• <code>"writesubtitles": true</code> - Download subtitles
• <code>"playliststart": 1, "playlistend": 10</code> - Playlist range

<b>Example:</b>
<code>/ytdl link -opt {"format": "bestvideo+bestaudio", "writesubtitles": true}</code>

<b>Resources:</b>
• <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>All Options Reference</a>"""

convert_media = """<b>✦ CONVERT MEDIA</b>: <code>-ca</code> <code>-cv</code>

<b>Audio Conversion:</b> <code>-ca FORMAT</code>
<b>Video Conversion:</b> <code>-cv FORMAT</code>

<b>Basic Usage:</b>
<code>/cmd link -ca mp3</code> (all audio → mp3)
<code>/cmd link -cv mp4</code> (all video → mp4)
<code>/cmd link -ca mp3 -cv mp4</code> (both)

<b>Advanced - Include Only:</b>
<code>/cmd link -ca mp3 + flac ogg</code> (only flac,ogg → mp3)

<b>Advanced - Exclude:</b>
<code>/cmd link -cv mkv - webm flv</code> (all except webm,flv → mkv)"""

force_start = """<b>✦ FORCE START</b>: <code>-f</code> <code>-fd</code> <code>-fu</code>

<b>Purpose:</b> Bypass queue limits and start task immediately.

<b>Options:</b>
• <code>-f</code> - Force both download and upload
• <code>-fd</code> - Force download only
• <code>-fu</code> - Force upload (start upload immediately after download)

<b>Examples:</b>
<code>/mirror link -f</code>
<code>/mirror link -fd</code>
<code>/leech link -fu</code>"""

gdrive = """<b>✦ GDRIVE OPERATIONS</b>

<b>Basic Usage:</b>
<code>/cmd gdrive_link</code>
<code>/cmd gdrive_id -up destination</code>

<b>Authentication Prefixes:</b>
• <code>tp:</code> - Use token.pickle
• <code>sa:</code> - Use service account
• <code>mtp:</code> - Use your uploaded token

<b>Interactive Selection:</b>
<code>/cmd gdl</code> - Select via buttons

<b>Examples:</b>
<code>/clone https://drive.google.com/file/d/xxx</code>
<code>/mirror tp:gdrive_id -up gd</code>
<code>/clone mtp:gdrive_id -up mtp:dest_id</code>"""

rclone_cl = """<b>✦ RCLONE OPERATIONS</b>

<b>Basic Usage:</b>
<code>/cmd rclone_path</code>
<code>/cmd rcl</code> (interactive selection)

<b>User Config:</b>
<code>/cmd mrcc:remote:path</code> (use your config)

<b>With Flags:</b>
<code>/cmd path -rcf flag:value|flag:value</code>

<b>Examples:</b>
<code>/clone remote:folder -up remote2:backup</code>
<code>/mirror rcl -up rcl</code>
<code>/clone mrcc:gdrive:files -up mrcc:onedrive:backup</code>"""

transmission = """<b>✦ UPLOAD SESSION</b>: <code>-hl</code> <code>-ut</code> <code>-bt</code>

<b>Purpose:</b> Control which Telegram session uploads your files.

<b>Options:</b>
• <code>-bt</code> - Upload via bot session (default, ≤2GB)
• <code>-ut</code> - Upload via user session (for larger files)
• <code>-hl</code> - Hybrid (auto-select by file size)

<b>Examples:</b>
<code>/leech link -bt</code>
<code>/leech link -ut</code>
<code>/leech link -hl</code>"""

thumbnail_layout = """<b>✦ THUMBNAIL LAYOUT</b>: <code>-tl</code>

<b>Purpose:</b> Create grid thumbnail from multiple video frames.

<b>Usage:</b>
<code>/cmd link -tl WIDTHxHEIGHT</code>

<b>Examples:</b>
<code>/leech link -tl 2x2</code> (4 frames in 2×2 grid)
<code>/leech link -tl 3x3</code> (9 frames in 3×3 grid)
<code>/leech link -tl 4x2</code> (8 frames in 4×2 grid)"""

leech_as = """<b>✦ UPLOAD TYPE</b>: <code>-doc</code> <code>-med</code>

<b>Purpose:</b> Override default upload type for this task.

<b>Options:</b>
• <code>-doc</code> - Upload as document (preserves filename)
• <code>-med</code> - Upload as media (streamable)

<b>Examples:</b>
<code>/leech link -doc</code>
<code>/leech link -med</code>"""

ffmpeg_cmds = """<b>✦ FFMPEG COMMANDS</b>: <code>-ff</code>

<b>Purpose:</b> Apply FFmpeg processing to files before upload.

<b>Usage:</b>
<code>/cmd link -ff preset_name</code>
<code>/cmd link -ff ["-i mltb.video -c copy mltb.mkv"]</code>

<b>File Patterns (mltb.*):</b>
• <code>mltb.mkv</code> - Match only .mkv files
• <code>mltb.video</code> - Match all video files
• <code>mltb.audio</code> - Match all audio files
• <code>mltb</code> - Output same extension as input

<b>Special Flag:</b>
• Add <code>-del</code> to delete originals after processing

<b>Preset Example:</b>
If bot has preset: <code>{"subtitle": ["-i mltb.mkv -c copy -c:s srt mltb.mkv"]}</code>
Use: <code>/mirror link -ff subtitle</code>

<b>Custom Example:</b>
<code>/mirror link -ff ["-i mltb.m4a -c:a libmp3lame mltb.mp3", "-del"]</code>"""

metadata = """<b>Metadata</b>: -meta

Apply custom metadata to media files using pipe (|) separator.

<b>Format:</b> key=value|key2=value2|key3=value3

<b>Dynamic Variables:</b>
• <code>{filename}</code> - Original filename
• <code>{basename}</code> - Filename without extension  
• <code>{extension}</code> - File extension
• <code>{audiolang}</code> - Audio language (auto-detected or English)
• <code>{sublang}</code> - Subtitle language (auto-detected or none)
• <code>{year}</code> - Year extracted from filename

<b>Per-Stream Metadata:</b>
Set different metadata for audio/video/subtitle streams in User Settings > FFmpeg Settings:
• <b>Audio Metadata:</b> Applied to each audio stream
• <b>Video Metadata:</b> Applied to video streams  
• <b>Subtitle Metadata:</b> Applied to subtitle streams

<b>Examples:</b>
<code>/mirror link -meta title=My Movie|artist={audiolang} Version</code>
<code>/yt link -meta album={basename}|year={year}|genre=Action</code>

<b>Escape Pipes:</b> Use <code>\\|</code> to include literal pipe in values:
<code>title=Movie \\| Director's Cut</code>

<b>User Settings Example:</b>
• Audio Metadata: <code>language={audiolang}|title=Audio Track</code>
• Video Metadata: <code>title={basename}|year={year}</code>
• Subtitle Metadata: <code>language={sublang}|title=Subtitles</code>"""

YT_HELP_DICT = {
    "main": yt,
    "New-Name": f"{new_name}\nNote: Don't add file extension",
    "Zip": zip_arg,
    "Zip-Images": zip_images,
    "Quality": qual,
    "Options": yt_opt,
    "Multi-Link": multi_link,
    "Same-Directory": same_dir,
    "Thumb": thumb,
    "Split-Size": split_size,
    "Upload-Destination": upload,
    "Rclone-Flags": rcf,
    "Bulk": bulk,
    "Sample-Video": sample_video,
    "Screenshot": screenshot,
    "Convert-Media": convert_media,
    "Force-Start": force_start,

    "TG-Transmission": transmission,
    "Thumb-Layout": thumbnail_layout,
    "Leech-Type": leech_as,
    "FFmpeg-Cmds": ffmpeg_cmds,
    "Metadata": metadata,
    "Merge-Video": merge_video,
}

MIRROR_HELP_DICT = {
    "main": mirror,
    "New-Name": new_name,
    "DL-Auth": "<b>Direct link authorization</b>: -au -ap\n\n/cmd link -au username -ap password",
    "Headers": "<b>Direct link custom headers</b>: -h\n\n/cmd link -h key: value key1: value1",
    "Extract/Zip": extract_zip,
    "Zip-Images": zip_images,
    "Select-Files": "<b>Bittorrent/JDownloader File Selection</b>: -s\n\n/cmd link -s or by replying to file/link",
    "Torrent-Seed": seed,
    "Multi-Link": multi_link,
    "Same-Directory": same_dir,
    "Thumb": thumb,
    "Split-Size": split_size,
    "Upload-Destination": upload,
    "Dump-Select": dump_select,
    "Rclone-Flags": rcf,
    "Bulk": bulk,
    "Join": join,
    "Merge-Video": merge_video,
    "Rclone-DL": rlone_dl,
    "Terabox-DL": terabox_dl,
    "Tg-Links": tg_links,
    "Sample-Video": sample_video,
    "Screenshot": screenshot,
    "Convert-Media": convert_media,
    "Force-Start": force_start,
    "User-Download": user_download,

    "TG-Transmission": transmission,
    "Thumb-Layout": thumbnail_layout,
    "Leech-Type": leech_as,
    "FFmpeg-Cmds": ffmpeg_cmds,
    "Metadata": metadata,
    "Merge-Video": merge_video,
}

CLONE_HELP_DICT = {
    "main": clone,
    "Multi-Link": multi_link,
    "Bulk": bulk,
    "Gdrive": gdrive,
    "Rclone": rclone_cl,
}

RSS_HELP_MESSAGE = """
Use this format to add feed url:
Title1 link (required)
Title2 link -c cmd -inf xx -exf xx
Title3 link -c cmd -d ratio:time -z password

-c command -up mrcc:remote:path/subdir -rcf --buffer-size:8M|key|key:value
-inf For included words filter.
-exf For excluded words filter.
-stv true or false (sensitive filter)

Example: Title https://www.rss-url.com -inf 1080 or 720 or 144p|mkv or mp4|hevc -exf flv or web|xxx
This filter will parse links that its titles contain `(1080 or 720 or 144p) and (mkv or mp4) and hevc` and doesn't contain (flv or web) and xxx words. You can add whatever you want.

Another example: -inf  1080  or 720p|.web. or .webrip.|hvec or x264. This will parse titles that contain ( 1080  or 720p) and (.web. or .webrip.) and (hvec or x264). I have added space before and after 1080 to avoid wrong matching. If this `10805695` number in title it will match 1080 if added 1080 without spaces after it.

Filter Notes:
1. | means and.
2. Add `or` between similar keys, you can add it between qualities or between extensions, so don't add filter like this f: 1080|mp4 or 720|web because this will parse 1080 and (mp4 or 720) and web ... not (1080 and mp4) or (720 and web).
3. You can add `or` and `|` as much as you want.
4. Take a look at the title if it has a static special character after or before the qualities or extensions or whatever and use them in the filter to avoid wrong match.
Timeout: 60 sec.
"""

PASSWORD_ERROR_MESSAGE = """
<b>This link requires a password!</b>
- Insert <b>::</b> after the link and write the password after the sign.

<b>Example:</b> link::my password
"""


def get_bot_commands():
    from bot.core.plugin_manager import get_plugin_manager
    from bot.core.config_manager import Config

    commands = {}

    commands["Mirror"] = "[link/file] Mirror to Upload Destination"
    if Config.SHOW_EXTRA_CMDS:
        commands["ZipMirror"] = "[link/file] Mirror and compress to zip"
        commands["UnzipMirror"] = "[link/file] Mirror and extract archive"

    commands["QbMirror"] = "[magnet/torrent] Mirror to Upload Destination using qbit"
    if Config.SHOW_EXTRA_CMDS:
        commands["QbZipMirror"] = "[magnet/torrent] QBit Mirror and compress to zip"
        commands["QbUnzipMirror"] = "[magnet/torrent] QBit Mirror and extract archive"

    commands["Ytdl"] = "[link] Mirror YouTube, m3u8, Social Media and yt-dlp supported urls"

    commands["UpHoster"] = "[link/file] Upload to DDL Servers"
    if Config.SHOW_EXTRA_CMDS:
        commands["ZipUpHoster"] = "[link/file] Compress to zip and upload to DDL Servers"
        commands["UnzipUpHoster"] = "[link/file] Extract and upload to DDL Servers"

    commands["Leech"] = "[link/file] Leech files to Upload to Telegram"
    if Config.SHOW_EXTRA_CMDS:
        commands["ZipLeech"] = "[link/file] Leech and compress to zip"
        commands["UnzipLeech"] = "[link/file] Leech and extract archive"

    commands["QbLeech"] = "[magnet/torrent] Leech files to Upload to Telegram using qbit"
    if Config.SHOW_EXTRA_CMDS:
        commands["QbZipLeech"] = "[magnet/torrent] QBit Leech and compress to zip"
        commands["QbUnzipLeech"] = "[magnet/torrent] QBit Leech and extract archive"

    commands["YtdlLeech"] = "[link] Leech YouTube, m3u8, Social Media and yt-dlp supported urls"

    commands["Clone"] = "[link] Clone files/folders to GDrive"
    commands["GDClean"] = "[OWNER] [link] Clean/Trash all files in a GDrive folder"
    commands["UserSet"] = "User personal settings"
    commands["ForceStart"] = "[gid/reply] Force start from queued task"
    commands["Count"] = "[link] Count no. of files/folders in GDrive"
    commands["List"] = "[query] Search any Text which is available in GDrive"
    commands["Search"] = "[query] Search torrents via Qbit Plugins"
    commands["MediaInfo"] = "[reply/link] Get MediaInfo of the Target Media"
    commands["Select"] = "[gid/reply] Select files for Aria2, Qbit Tasks"
    commands["Ping"] = "Ping Bot to test Response Speed"
    commands["Status"] = "[id/me] Tasks Status of Bot"
    commands["Stats"] = "Bot, OS, Repo & System full Statistics"
    commands["Rss"] = "User RSS Management Settings"
    commands["CancelAll"] = "Cancel all Tasks on the Bot"
    commands["Help"] = "Detailed help usage of NEO-WZML"
    commands["BotSet"] = "[SUDO] Bot Management Settings"
    commands["Log"] = "[SUDO] Get Bot Logs for Internal Working"
    commands["Restart"] = "[SUDO] Reboot bot"
    commands["RestartSessions"] = "[SUDO] Reboot User Sessions"

    plugin_manager = get_plugin_manager()
    if plugin_manager:
        for plugin_info in plugin_manager.list_plugins():
            if plugin_info.enabled and plugin_info.commands:
                for cmd in plugin_info.commands:
                    if cmd == "speedtest":
                        commands["SpeedTest"] = "Check Bot Speed using Speedtest.com"

    return commands


def get_help_string(user_id=None, is_sudo=False):
    from bot.helper.telegram_helper.bot_commands import BotCommands
    from bot.core.config_manager import Config

    is_owner = user_id == Config.OWNER_ID if user_id else False
    has_admin_access = is_sudo or is_owner

    download_commands = {
        "Mirror": {
            "desc": "Download files from direct links, magnets, or torrents to your cloud storage (GDrive/Rclone)",
            "usage": "/mirror <link> or reply to a file/link",
            "examples": ["/mirror https://example.com/file.zip", "/mirror magnet:?xt=urn:btih:..."],
        },
        "QbMirror": {
            "desc": "Download torrents using qBittorrent engine with better seeding and selection support",
            "usage": "/qbmirror <magnet/torrent_link>",
            "examples": ["/qbmirror magnet:?xt=urn:btih:..."],
        },
        "JdMirror": {
            "desc": "Download files using JDownloader for premium host support and captcha solving",
            "usage": "/jdmirror <link>",
            "examples": ["/jdmirror https://rapidgator.net/file/..."],
        },
        "Ytdl": {
            "desc": "Download videos from YouTube, Instagram, Twitter, TikTok and 1000+ sites using yt-dlp",
            "usage": "/ytdl <video_url>",
            "examples": ["/ytdl https://youtube.com/watch?v=...", "/ytdl https://twitter.com/user/status/..."],
        },
        "Clone": {
            "desc": "Copy files/folders from one Google Drive to another, or from supported link shorteners",
            "usage": "/clone <gdrive_link>",
            "examples": ["/clone https://drive.google.com/file/d/.../view"],
        },
        "GDClean": {
            "desc": "Delete or trash all files within a Google Drive folder. Owner only. Folder itself is not deleted.",
            "usage": "/gdclean [link] or reply to a GDrive link",
            "examples": ["/gdclean", "/gdclean https://drive.google.com/drive/folders/..."],
        },
    }

    leech_commands = {
        "Leech": {
            "desc": "Download and upload files directly to Telegram chat or dump channel",
            "usage": "/leech <link> or reply to a file/link",
            "examples": ["/leech https://example.com/file.zip", "/leech -up @mychannel"],
        },
        "QbLeech": {
            "desc": "Download torrents with qBittorrent and upload to Telegram",
            "usage": "/qbleech <magnet/torrent_link>",
            "examples": ["/qbleech magnet:?xt=urn:btih:..."],
        },
        "JdLeech": {
            "desc": "Download with JDownloader and upload to Telegram (premium host support)",
            "usage": "/jdleech <link>",
            "examples": ["/jdleech https://rapidgator.net/file/..."],
        },
        "YtdlLeech": {
            "desc": "Download videos with yt-dlp and upload to Telegram",
            "usage": "/ytdlleech <video_url>",
            "examples": ["/ytdlleech https://youtube.com/watch?v=..."],
        },
        "UpHoster": {
            "desc": "Upload files to DDL hosting services (Gofile, PixelDrain, BuzzHeavier)",
            "usage": "/uphoster <link> or reply to a file",
            "examples": ["/uphoster https://example.com/file.zip"],
        },
    }

    utility_commands = {
        "Status": {
            "desc": "View all active downloads/uploads with progress, speed, and ETA",
            "usage": "/status or /status me (your tasks only)",
            "examples": ["/status", "/status me"],
        },
        "Stats": {
            "desc": "Display bot statistics including system resources, uptime, and usage info",
            "usage": "/stats",
            "examples": ["/stats"],
        },
        "Ping": {
            "desc": "Check bot response time and connectivity",
            "usage": "/ping",
            "examples": ["/ping"],
        },
        "List": {
            "desc": "Search for files across all connected Google Drives",
            "usage": "/list <search_query>",
            "examples": ["/list Ubuntu ISO", "/list movie name 2024"],
        },
        "Search": {
            "desc": "Search for torrents across multiple torrent sites using qBittorrent plugins",
            "usage": "/search <query>",
            "examples": ["/search linux distro", "/search movie 1080p"],
        },
        "Count": {
            "desc": "Count files and folders in a Google Drive link and show total size",
            "usage": "/count <gdrive_link>",
            "examples": ["/count https://drive.google.com/drive/folders/..."],
        },
        "MediaInfo": {
            "desc": "Get detailed technical information about a media file (codec, resolution, bitrate, etc.)",
            "usage": "/mediainfo <link> or reply to media file",
            "examples": ["/mediainfo https://example.com/video.mkv"],
        },
        "Select": {
            "desc": "Select specific files to download from torrents (skip unwanted files)",
            "usage": "/select <gid> or reply to task message",
            "examples": ["/select abc123"],
        },
        "CancelTask": {
            "desc": "Cancel an active download/upload task",
            "usage": "/cancel <gid> or reply to task message",
            "examples": ["/cancel abc123"],
        },
        "ForceStart": {
            "desc": "Force start a queued task immediately (bypass queue limits)",
            "usage": "/forcestart <gid> or reply to task message",
            "examples": ["/forcestart abc123"],
        },
        "CancelAll": {
            "desc": "Cancel all active tasks (your tasks only, or all if admin)",
            "usage": "/cancelall or /cancelall <status>",
            "examples": ["/cancelall", "/cancelall downloading"],
        },
    }

    settings_commands = {
        "UserSet": {
            "desc": "Configure your personal settings: thumbnails, captions, upload destinations, and more",
            "usage": "/usettings",
            "examples": ["/usettings"],
        },
        "Rss": {
            "desc": "Manage RSS feeds for automatic downloads when new content is published",
            "usage": "/rss",
            "examples": ["/rss"],
        },
        "Help": {
            "desc": "Display this help menu with all available commands and their descriptions",
            "usage": "/help",
            "examples": ["/help"],
        },
    }

    admin_commands = {
        "BotSet": {
            "desc": "Configure bot-wide settings: limits, APIs, upload destinations, and system options",
            "usage": "/bsetting",
            "examples": ["/bsetting"],
        },
        "Log": {
            "desc": "Get bot log files for debugging errors and monitoring activity",
            "usage": "/log",
            "examples": ["/log"],
        },
        "Restart": {
            "desc": "Restart the bot and apply any pending updates from the repository",
            "usage": "/restart",
            "examples": ["/restart"],
        },
        "RestartSessions": {
            "desc": "Restart Telegram user sessions without full bot restart",
            "usage": "/restartses",
            "examples": ["/restartses"],
        },
        "Authorize": {
            "desc": "Authorize a user or chat to use the bot",
            "usage": "/authorize <user_id/chat_id> or reply to user",
            "examples": ["/authorize 123456789", "/authorize -100123456789"],
        },
        "UnAuthorize": {
            "desc": "Remove bot access from a user or chat",
            "usage": "/unauthorize <user_id/chat_id>",
            "examples": ["/unauthorize 123456789"],
        },
        "Users": {
            "desc": "View all user settings and authorized users list",
            "usage": "/users",
            "examples": ["/users"],
        },
        "AddSudo": {
            "desc": "Grant sudo (admin) privileges to a user",
            "usage": "/addsudo <user_id> or reply to user",
            "examples": ["/addsudo 123456789"],
        },
        "RmSudo": {
            "desc": "Remove sudo privileges from a user",
            "usage": "/rmsudo <user_id>",
            "examples": ["/rmsudo 123456789"],
        },
        "SudoList": {
            "desc": "List all sudo users with their names and IDs",
            "usage": "/sudolist",
            "examples": ["/sudolist"],
        },
        "Delete": {
            "desc": "Delete files/folders from Google Drive",
            "usage": "/delete <gdrive_link>",
            "examples": ["/delete https://drive.google.com/file/d/..."],
        },
        "Shell": {
            "desc": "Execute shell commands on the server (Owner Only)",
            "usage": "/shell <command>",
            "examples": ["/shell ls -la"],
        },
        "Exec": {
            "desc": "Execute Python code synchronously (Owner Only)",
            "usage": "/exec <python_code>",
            "examples": ["/exec print('Hello')"],
        },
        "AExec": {
            "desc": "Execute Python code asynchronously (Owner Only)",
            "usage": "/aexec <async_python_code>",
            "examples": ["/aexec await some_async_function()"],
        },
    }

    commands = BotCommands.get_commands()

    def format_category(title, emoji, cmd_dict):
        lines = [f"\n<b>{emoji} {title}</b>"]
        for key, info in cmd_dict.items():
            cmd_attr = getattr(BotCommands, f"{key}Command", None)
            if not cmd_attr or key not in commands:
                continue
            if isinstance(cmd_attr, list):
                cmd_str = f"/{cmd_attr[0]}"
            else:
                cmd_str = f"/{cmd_attr}"
            lines.append(f"  • <code>{cmd_str}</code>: {info['desc']}")
        return "\n".join(lines) if len(lines) > 1 else ""

    help_text = ["<b>✦ Bot Command Reference</b>", ""]
    help_text.append("<i>Use any command without arguments for detailed usage info.</i>")

    download_section = format_category("DOWNLOAD TO CLOUD", "➤", download_commands)
    if download_section:
        help_text.append(download_section)
    
    leech_section = format_category("LEECH TO TELEGRAM", "➤", leech_commands)
    if leech_section:
        help_text.append(leech_section)
    
    utility_section = format_category("UTILITIES", "➤", utility_commands)
    if utility_section:
        help_text.append(utility_section)
    
    settings_section = format_category("SETTINGS", "➤", settings_commands)
    if settings_section:
        help_text.append(settings_section)
    
    if has_admin_access:
        admin_section = format_category("ADMINISTRATION", "➤", admin_commands)
        if admin_section:
            help_text.append(admin_section)
    
    help_text.append("")
    help_text.append("<i>Tip: Most commands support arguments like -n (rename), -z (zip), -zim (zip images), -e (extract). Use the command alone to see all options.</i>")
    
    return "\n".join(help_text)


config_descriptions = {
    "BOT_TOKEN": "The Telegram Bot Token that you got from @BotFather",
    "OWNER_ID": "Your Telegram numeric User ID (not username)",
    "TELEGRAM_API": "Telegram API ID from my.telegram.org for user session features",
    "TELEGRAM_HASH": "Telegram API Hash from my.telegram.org for user sessions",
    "USER_SESSION_STRING": "Pyrogram session string for user account features (files >2GB, RSS). Generate using: python3 generate_string_session.py",
    "DATABASE_URL": "MongoDB connection string for persistent storage",
    "DEFAULT_LANG": "Default language for bot messages",

    "AUTHORIZED_CHATS": "User/Chat IDs that can use the bot. Space-separated",
    "SUDO_USERS": "User IDs with admin privileges. Space-separated",
    "HELPER_TOKENS": "Helper bot tokens for Hyper transfers. Space-separated",
    "USE_HYPER": "Use helper bots for accelerated Telegram download/upload. Needs HELPER_TOKENS + LEECH_DUMP_CHAT",
    "EXCEP_CHATS": "Chat IDs where logging is disabled",
    "FORCE_SUB_IDS": "Chat IDs users must subscribe to before using the bot",

    "GDRIVE_ID": "Default Google Drive folder/Team Drive ID for mirror uploads",
    "INDEX_URL": "Index URL for browsing GDrive files",
    "IS_TEAM_DRIVE": "Set True if GDRIVE_ID is a Shared/Team Drive",
    "STOP_DUPLICATE": "Check if file/folder already exists in Drive before uploading",
    "USE_SERVICE_ACCOUNTS": "Use Service Account JSON files for GDrive uploads",
    "GD_DESP": "Description text added to files uploaded to Google Drive",
    "USER_TD_MODE": "Allow users to upload to their own Team Drives",
    "USER_TD_SA": "Service Account email for User TD Mode",
    "JIODRIVE_TOKEN": "JioDrive token for JioDrive link bypass",
    "GDTOT_CRYPT": "GDTot crypt cookie for GDTot link bypass",

    "RCLONE_PATH": "Default Rclone remote:path for mirror uploads",
    "RCLONE_FLAGS": "Additional Rclone flags for all transfers",
    "RCLONE_SERVE_URL": "Public URL where Rclone serve is accessible",
    "RCLONE_SERVE_PORT": "Port for Rclone HTTP serve",
    "RCLONE_SERVE_USER": "Username for Rclone serve HTTP authentication",
    "RCLONE_SERVE_PASS": "Password for Rclone serve HTTP authentication",

    "AS_DOCUMENT": "Upload files as documents instead of streamable media",
    "LEECH_SPLIT_SIZE": "Maximum file size before splitting (in bytes)",
    "EQUAL_SPLITS": "Split files into equal-sized parts instead of max-size parts",
    "MEDIA_GROUP": "Group split file parts as media album in Telegram",
    "LEECH_PREFIX": "Text added BEFORE every leeched filename",
    "LEECH_SUFFIX": "Text added AFTER every leeched filename",
    "LEECH_CAPTION": "Custom caption for leeched files",
    "LEECH_FONT": "Apply font style to leeched filenames",
    "CAP_FONT": "Font style for LEECH_CAPTION text",
    "LEECH_NAME_SWAP": "Regex patterns to modify leeched filenames",
    "LEECH_DUMP_CHAT": "Chat/Channel ID where leeched files are uploaded",

    "DEFAULT_UPLOAD": "Default upload destination: gd (GDrive), rc (Rclone), or tbx (TeraBox)",
    "MIRROR_PREFIX": "Text added BEFORE every mirrored filename",
    "MIRROR_SUFFIX": "Text added AFTER every mirrored filename",
    "MIRROR_NAME_SWAP": "Regex patterns to modify mirrored filenames",
    "MIRROR_LOG_ID": "Chat ID(s) for mirror activity logs",
    "UPLOAD_PATHS": "Default upload paths for destinations",
    "LINKS_LOG_ID": "Chat ID where source links are logged",

    "TORRENT_LIMIT": "Max torrent download size in GB",
    "DIRECT_LIMIT": "Max direct link download size in GB",
    "MEGA_LIMIT": "Max Mega.nz download size in GB",
    "TERABOX_LIMIT": "Max Terabox download size in GB",
    "GDRIVE_LIMIT": "Max Google Drive download/upload size in GB",
    "RCLONE_LIMIT": "Max Rclone download/upload size in GB. 0 = no limit",
    "CLONE_LIMIT": "Max Google Drive clone size in GB",
    "LEECH_LIMIT": "Max leech size in GB (any source)",
    "JD_LIMIT": "Max JDownloader download size in GB",
    "YTDLP_LIMIT": "Max yt-dlp download size in GB",
    "PLAYLIST_LIMIT": "Max number of videos from playlist. 0 = no limit",
    "EXTRACT_LIMIT": "Max size for extraction operations in GB. 0 = no limit",
    "ARCHIVE_LIMIT": "Max size for archive/zip operations in GB. 0 = no limit",
    "STORAGE_LIMIT": "Minimum free disk space required before starting tasks (GB). 0 = disabled",

    "DAILY_TASK_LIMIT": "Max number of tasks a user can run per day. 0 = unlimited",
    "DAILY_MIRROR_LIMIT": "Max total mirror size per user per day (GB). 0 = unlimited",
    "DAILY_LEECH_LIMIT": "Max total leech size per user per day (GB). 0 = unlimited",
    "USER_MAX_TASKS": "Max concurrent tasks per user. 0 = unlimited",
    "USER_TIME_INTERVAL": "Cooldown between tasks for same user (seconds). 0 = no cooldown",
    "UNIVERSAL_MAX_TASKS": "Max concurrent tasks per user across ALL bots sharing this database. 0 = disabled (only per-bot limit applies)",

    "BOT_MAX_TASKS": "Max total concurrent tasks (downloads + uploads)",
    "QUEUE_ALL": "Max parallel tasks (download + upload combined)",
    "QUEUE_DOWNLOAD": "Max parallel download tasks",
    "QUEUE_UPLOAD": "Max parallel upload tasks",

    "TORRENT_TIMEOUT": "Timeout for dead/stalled torrents in seconds. 0 = no timeout",
    "DISABLE_TORRENTS": "Disable all torrent commands (mirror, qbmirror, leech, qbleech)",
    "DISABLE_SEED": "Disable torrent seeding after download completes",
    "SEARCH_PLUGINS": "List of qBittorrent search plugin URLs (github raw links)",
    "SEARCH_API_LINK": "Torrent search API URL (Torrent API or similar)",
    "SEARCH_LIMIT": "Max results per site from torrent search. 0 = API default",

    "JD_MODE": "Enable JDownloader for premium host support. Requires JD_EMAIL and JD_PASS",
    "JD_EMAIL": "my.jdownloader.org account email for JDownloader sync",
    "JD_PASS": "my.jdownloader.org account password for JDownloader sync",
    "MEGA_ENABLED": "Enable Mega.nz downloads",
    "MEGA_EMAIL": "Mega.nz premium account email for higher limits",
    "MEGA_PASSWORD": "Mega.nz premium account password",
    "TERABOX_ENABLED": "Enable Terabox downloads (teraboxSDK). Auth via a terabox.txt cookie export (Private Files).",
    "TERABOX_UPLOAD_PATH": "Default folder in the TeraBox account for `-up tbx` uploads (e.g. /NEO-WZML). Empty = account root.",

    "DEBRID_LINK_API": "Debrid-Link.com API key for 172+ premium host support",
    "REAL_DEBRID_API": "Real-Debrid.com API key for torrent cache and premium hosts",
    "FILELION_API": "FileLion API key for premium link generation",
    "PROTECTED_API": "Protected/Securedown API key for premium links",
    "INSTADL_API": "InstaDL API key for Instagram video downloads",

    "GOFILE_API": "Gofile.io API token for file uploads",
    "GOFILE_FOLDER_ID": "Gofile folder ID to organize uploads. Leave empty for root",
    "PIXELDRAIN_KEY": "PixelDrain API key for file uploads",
    "BUZZHEAVIER_API": "BuzzHeavier account ID (API token) for uploads",
    "STREAMWISH_API": "StreamWish API key for video hosting uploads",

    "BASE_URL": "Public URL where bot web server is accessible. Used for torrent file selection UI",
    "BASE_URL_PORT": "Port for web server. Must match BASE_URL port",
    "WEB_PINCODE": "Require PIN verification before torrent file selection in web UI",

    "RSS_CHAT": "Chat ID where RSS feed items are posted. Use -100 prefix for channels",
    "RSS_DELAY": "Time between RSS feed checks in seconds. Minimum recommended: 600 (10 min)",
    "RSS_SIZE_LIMIT": "Max size for RSS auto-downloads in GB. 0 = no limit",

    "STATUS_LIMIT": "Max number of tasks shown per status message page",
    "STATUS_UPDATE_INTERVAL": "Seconds between status message updates",
    "BOT_THEME": "Visual theme for bot messages. Available themes in bot/helper/themes/",
    "TIMEZONE": "Timezone for timestamps in messages. Format: Region/City",
    "SHOW_CLOUD_LINK": "Show cloud storage link button in status messages",
    "SHOW_MEDIAINFO": "Show MediaInfo button for leeched video files",
    "SOURCE_LINK": "Show source link button (magnet/direct link) in status",
    "SAVE_MSG": "Add 'Save Message' button to bot responses",
    "DISABLE_DRIVE_LINK": "Hide Google Drive link button from status messages",
    "SCREENSHOTS_MODE": "Enable -ss argument for generating video screenshots",

    "DISABLE_LEECH": "Completely disable all leech commands",
    "DISABLE_BULK": "Disable bulk download feature (-b argument)",
    "DISABLE_MULTI": "Disable multi-link download feature (-i argument)",
    "DISABLE_FF_MODE": "Disable FFmpeg processing commands (-ff argument)",
    "BOT_PM": "Send task completion messages to user's PM in addition to group",
    "DELETE_LINKS": "Delete the source message (link/magnet) when task starts",
    "CLEAN_LOG_MSG": "Delete task start notification in leech log and bot PM",
    "SAFE_MODE": "Hide task name, source link, and index link from status for privacy",
    "STRICT_AUTH_MODE": "Enable strict authorization - only owner/sudo/explicitly authorized chats can use bot",
    "STRICT_FILE_MODE": "Enable file filtering - only allow video files >= 100MB",
    "SHOW_EXTRA_CMDS": "Enable shortcut commands like /unzip, /zip instead of -e, -z",
    "INCOMPLETE_TASK_NOTIFIER": "Resume and notify about incomplete tasks after bot restart. Requires DATABASE_URL",

    "FFMPEG_CMDS": "Preset FFmpeg command lists for media processing. Dict format: {\"preset_name\": [\"cmd1\", \"cmd2\"]}",
    "THUMBNAIL_LAYOUT": "Grid layout for video thumbnail generation. Format: WIDTHxHEIGHT. Example: 3x3",
    "EXCLUDED_EXTENSIONS": "File extensions to skip during upload/clone. Space-separated without dots",
    "MEDIA_STORE": "Store media info cache for faster repeated access",
    "YT_DLP_OPTIONS": "Default yt-dlp options as JSON dict. See yt-dlp documentation",

    "AUTHOR_NAME": "Author name shown on Telegraph pages",
    "AUTHOR_URL": "URL linked to author name on Telegraph",

    "LOGIN_PASS": "Global password to bypass token verification system",
    "VERIFY_TIMEOUT": "Timeout for link verification challenges in seconds. 0 = no verification",
    "TG_PROXY": "Proxy for Telegram connections (user session)",

    "UPSTREAM_REPO": "GitHub repository URL for bot auto-updates",
    "UPSTREAM_BRANCH": "Git branch to pull updates from. Default: master",
    "AUTO_UPDATE": "Run git reset to UPSTREAM_REPO on startup. Keep False for custom Docker builds",
    "UPDATE_PKGS": "Auto-install new Python requirements on restart",
    "UPGRADE_PACKAGES": "Upgrade system packages on bot restart. May cause instability",
    "SET_COMMANDS": "Automatically set bot commands in Telegram on startup",
    "CMD_SUFFIX": "Suffix added to all bot commands. Useful for multi-instance",

    "HYPER_THREADS": "Parallel transfer threads per helper client for Hyper download/upload. 0 = auto-detect",
    "HYDRA_IP": "Hydra download accelerator server IP. Leave empty if not using Hydra",
    "HYDRA_API_KEY": "API key for Hydra download accelerator authentication",

    "USER_TRANSMISSION": "Deprecated - per-file automatic client selection is now used",
}
