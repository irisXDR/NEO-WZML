# This file is a part of NEO-WZML (github.com/irisXDR/NEO-WZML)

from pyrogram.filters import command, private, regex
from pyrogram.handlers import CallbackQueryHandler, EditedMessageHandler, MessageHandler
from pyrogram.types import BotCommand

from bot import bot_loop
from bot.core.config_manager import Config
from bot.helper.ext_utils.help_messages import get_bot_commands
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.modules import *
from bot.core.tg_client import TgClient


def add_handlers():
    TgClient.bot.add_handler(
        MessageHandler(
            authorize,
            filters=command(BotCommands.AuthorizeCommand, case_sensitive=True)
            & CustomFilters.sudo,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            unauthorize,
            filters=command(BotCommands.UnAuthorizeCommand, case_sensitive=True)
            & CustomFilters.sudo,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            add_sudo,
            filters=command(BotCommands.AddSudoCommand, case_sensitive=True)
            & CustomFilters.sudo,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            remove_sudo,
            filters=command(BotCommands.RmSudoCommand, case_sensitive=True)
            & CustomFilters.sudo,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            sudolist,
            filters=command(BotCommands.SudoListCommand, case_sensitive=True)
            & CustomFilters.sudo,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            send_bot_settings,
            filters=command(BotCommands.BotSetCommand, case_sensitive=True)
            & CustomFilters.sudo,
        )
    )
    TgClient.bot.add_handler(
        CallbackQueryHandler(
            edit_bot_settings, filters=regex("^botset") & CustomFilters.sudo
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            cancel,
            filters=regex(rf"^/{BotCommands.CancelTaskCommand[1]}?(?:_\w+).*$")
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            cancel_all_buttons,
            filters=command(BotCommands.CancelAllCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        CallbackQueryHandler(cancel_all_update, filters=regex("^canall"))
    )
    TgClient.bot.add_handler(
        CallbackQueryHandler(cancel_multi, filters=regex("^stopm"))
    )
    TgClient.bot.add_handler(
        MessageHandler(
            clone_node,
            filters=command(BotCommands.CloneCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            aioexecute,
            filters=command(BotCommands.AExecCommand, case_sensitive=True)
            & CustomFilters.sudo,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            execute,
            filters=command(BotCommands.ExecCommand, case_sensitive=True)
            & CustomFilters.sudo,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            clear,
            filters=command(BotCommands.ClearLocalsCommand, case_sensitive=True)
            & CustomFilters.sudo,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            select,
            filters=regex(rf"^/{BotCommands.SelectCommand[1]}_(\w+)")
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        CallbackQueryHandler(confirm_selection, filters=regex("^sel"))
    )
    TgClient.bot.add_handler(
        MessageHandler(
            remove_from_queue,
            filters=command(BotCommands.ForceStartCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            count_node,
            filters=command(BotCommands.CountCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            delete_file,
            filters=command(BotCommands.DeleteCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            gdclean_node,
            filters=command(BotCommands.GDCleanCommand, case_sensitive=True)
            & CustomFilters.owner,
        )
    )
    TgClient.bot.add_handler(CallbackQueryHandler(gdclean_callback, filters=regex("^gdclean")))
    TgClient.bot.add_handler(
        MessageHandler(
            gdrive_search,
            filters=command(BotCommands.ListCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        CallbackQueryHandler(select_type, filters=regex("^list_types"))
    )
    TgClient.bot.add_handler(CallbackQueryHandler(arg_usage, filters=regex("^help")))
    TgClient.bot.add_handler(
        MessageHandler(
            mirror,
            filters=command(BotCommands.MirrorCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            qb_mirror,
            filters=command(BotCommands.QbMirrorCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            jd_mirror,
            filters=command(BotCommands.JdMirrorCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            leech,
            filters=command(BotCommands.LeechCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            qb_leech,
            filters=command(BotCommands.QbLeechCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            jd_leech,
            filters=command(BotCommands.JdLeechCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )

    TgClient.bot.add_handler(
        MessageHandler(
            uphoster,
            filters=command(BotCommands.UpHosterCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            get_rss_menu,
            filters=command(BotCommands.RssCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(CallbackQueryHandler(rss_listener, filters=regex("^rss")))
    TgClient.bot.add_handler(
        MessageHandler(
            run_shell,
            filters=command(BotCommands.ShellCommand, case_sensitive=True)
            & CustomFilters.sudo,
        )
    )
    TgClient.bot.add_handler(
        EditedMessageHandler(
            run_shell,
            filters=command(BotCommands.ShellCommand, case_sensitive=True)
            & CustomFilters.owner,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            start, filters=command(BotCommands.StartCommand, case_sensitive=True)
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            login, filters=command(BotCommands.LoginCommand, case_sensitive=True)
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            log,
            filters=command(BotCommands.LogCommand, case_sensitive=True)
            & CustomFilters.sudo,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            restart_bot,
            filters=command(BotCommands.RestartCommand, case_sensitive=True)
            & CustomFilters.sudo,
        )
    )
    TgClient.bot.add_handler(
        CallbackQueryHandler(
            confirm_restart, filters=regex("^botrestart") & CustomFilters.sudo
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            restart_sessions,
            filters=command(BotCommands.RestartSessionsCommand, case_sensitive=True)
            & CustomFilters.sudo,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            ping,
            filters=command(BotCommands.PingCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            bot_help,
            filters=command(BotCommands.HelpCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            mediainfo,
            filters=command(BotCommands.MediaInfoCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )

    TgClient.bot.add_handler(
        MessageHandler(
            bot_stats,
            filters=command(BotCommands.StatsCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            task_status,
            filters=command(BotCommands.StatusCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        CallbackQueryHandler(status_pages, filters=regex("^status"))
    )
    TgClient.bot.add_handler(CallbackQueryHandler(stats_pages, filters=regex("^stats")))
    TgClient.bot.add_handler(CallbackQueryHandler(log_cb, filters=regex("^log")))
    TgClient.bot.add_handler(CallbackQueryHandler(start_cb, filters=regex("^start")))
    TgClient.bot.add_handler(
        MessageHandler(
            torrent_search,
            filters=command(BotCommands.SearchCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        CallbackQueryHandler(torrent_search_update, filters=regex("^torser"))
    )
    TgClient.bot.add_handler(
        MessageHandler(
            get_users_settings,
            filters=command(BotCommands.UsersCommand, case_sensitive=True)
            & CustomFilters.sudo,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            send_user_settings,
            filters=command(BotCommands.UserSetCommand, case_sensitive=True)
            & (private | CustomFilters.authorized),
        )
    )
    TgClient.bot.add_handler(
        CallbackQueryHandler(edit_user_settings, filters=regex("^userset"))
    )
    TgClient.bot.add_handler(
        MessageHandler(
            ytdl,
            filters=command(BotCommands.YtdlCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(
        MessageHandler(
            ytdl_leech,
            filters=command(BotCommands.YtdlLeechCommand, case_sensitive=True)
            & CustomFilters.authorized,
        )
    )
    TgClient.bot.add_handler(save_handler)
    TgClient.bot.add_handler(
        MessageHandler(
            speedtest,
            filters=command(BotCommands.SpeedTestCommand, case_sensitive=True)
            & CustomFilters.sudo,
        )
    )
    if Config.SET_COMMANDS:
        def insert_at(d, k, v, i):
            return dict(list(d.items())[:i] + [(k, v)] + list(d.items())[i:])

        bot_commands = get_bot_commands()

        if Config.JD_EMAIL and Config.JD_PASS:
            jd_mirror_pos = 3
            if Config.SHOW_EXTRA_CMDS:
                jd_mirror_pos = 6
            
            bot_commands = insert_at(
                bot_commands,
                "JdMirror",
                "[link/file] Mirror to Upload Destination using JDownloader",
                jd_mirror_pos,
            )
            if Config.SHOW_EXTRA_CMDS:
                bot_commands = insert_at(
                    bot_commands,
                    "JdZipMirror",
                    "[link/file] JDownloader Mirror and compress to zip",
                    jd_mirror_pos + 1,
                )
                bot_commands = insert_at(
                    bot_commands,
                    "JdUnzipMirror",
                    "[link/file] JDownloader Mirror and extract archive",
                    jd_mirror_pos + 2,
                )
            
            jd_leech_pos = 12
            if Config.SHOW_EXTRA_CMDS:
                jd_leech_pos = 21
            
            bot_commands = insert_at(
                bot_commands,
                "JdLeech",
                "[link/file] Leech files to Upload to Telegram using JDownloader",
                jd_leech_pos,
            )
            if Config.SHOW_EXTRA_CMDS:
                bot_commands = insert_at(
                    bot_commands,
                    "JdZipLeech",
                    "[link/file] JDownloader Leech and compress to zip",
                    jd_leech_pos + 1,
                )
                bot_commands = insert_at(
                    bot_commands,
                    "JdUnzipLeech",
                    "[link/file] JDownloader Leech and extract archive",
                    jd_leech_pos + 2,
                )

        if Config.LOGIN_PASS:
            bot_commands = insert_at(
                bot_commands, "Login", "[password] Login to Bot", 14
            )

        telegram_commands = []

        for cmd, description in bot_commands.items():
            cmds = getattr(BotCommands, f"{cmd}Command", None)
            if cmds is not None:
                telegram_commands.append(
                    BotCommand(
                        cmds[0] if isinstance(cmds, list) else cmds,
                        description,
                    )
                )
            elif Config.SHOW_EXTRA_CMDS and cmd in {
                "ZipMirror", "UnzipMirror", "QbZipMirror", "QbUnzipMirror",
                "JdZipMirror", "JdUnzipMirror",
                "ZipUpHoster", "UnzipUpHoster",
                "ZipLeech", "UnzipLeech", "QbZipLeech", "QbUnzipLeech",
                "JdZipLeech", "JdUnzipLeech",
            }:
                telegram_commands.append(
                    BotCommand(f"{cmd.lower()}{Config.CMD_SUFFIX}", description)
                )

        bot_loop.create_task(TgClient.bot.set_bot_commands(telegram_commands))
