# This file is a part of NEO-WZML (github.com/irisXDR/NEO-WZML)

from pyrogram import Client, enums
from asyncio import Lock, gather
from inspect import signature
from cryptography.fernet import Fernet, InvalidToken

from bot import LOGGER, bot_cache
from bot.core.config_manager import Config


class TgClient:
    _lock = Lock()
    _hlock = Lock()

    bot = None
    user = None
    helper_bots = {}
    helper_loads = {}

    BNAME = ""
    ID = 0
    IS_PREMIUM_USER = False
    MAX_SPLIT_SIZE = 2097152000

    @classmethod
    def neoTgClient(cls, *args, max_concurrent_transmissions=3, **kwargs):
        kwargs["api_id"] = Config.TELEGRAM_API
        kwargs["api_hash"] = Config.TELEGRAM_HASH
        kwargs["proxy"] = Config.TG_PROXY
        kwargs["parse_mode"] = enums.ParseMode.HTML
        kwargs["in_memory"] = True
        for param, value in {
            "max_concurrent_transmissions": max_concurrent_transmissions,
            "skip_updates": False,
        }.items():
            if param in signature(Client.__init__).parameters:
                kwargs[param] = value
        return Client(*args, **kwargs)

    @classmethod
    async def start_hclient(cls, no, b_token):
        try:
            hbot = await cls.neoTgClient(
                f"NEO-WZML-HBot{no}",
                bot_token=b_token,
                no_updates=True,
                # helper bots carry Hyper transfers: allow more parallel
                # chunk streams per client for higher throughput
                max_concurrent_transmissions=Config.HYPER_THREADS or 8,
            ).start()
            LOGGER.info(f"Helper Bot [@{hbot.me.username}] Started!")
            cls.helper_bots[no], cls.helper_loads[no] = hbot, 0
        except Exception as e:
            LOGGER.error(f"Failed to start helper bot {no} from HELPER_TOKENS. {e}")
            cls.helper_bots.pop(no, None)

    @classmethod
    async def start_helper_bots(cls):
        if not Config.HELPER_TOKENS:
            return
        LOGGER.info("Generating helper client from HELPER_TOKENS")
        async with cls._hlock:
            await gather(
                *(
                    cls.start_hclient(no, b_token)
                    for no, b_token in enumerate(Config.HELPER_TOKENS.split(), start=1)
                )
            )

    @classmethod
    async def start_bot(cls):
        LOGGER.info("Generating client from BOT_TOKEN")
        cls.ID = Config.BOT_TOKEN.split(":", 1)[0]
        cls.bot = cls.neoTgClient(
            f"NEO-WZML-Bot{cls.ID}",
            bot_token=Config.BOT_TOKEN,
            workdir="/usr/src/app",
        )
        await cls.bot.start()
        cls.BNAME = cls.bot.me.username
        cls.ID = Config.BOT_TOKEN.split(":", 1)[0]
        LOGGER.info(f"NEO-WZML Bot : [@{cls.BNAME}] Started!")

    @classmethod
    async def start_user(cls):
        if Config.USER_SESSION_STRING:
            LOGGER.info("Generating client from USER_SESSION_STRING")
            try:
                session_string = Config.USER_SESSION_STRING

                if session_string.startswith("Fencrypted:"):
                    decrypt_key = cls._get_decrypt_key()
                    if decrypt_key is None:
                        LOGGER.error("No decryption key provided for USER_SESSION_STRING")
                        cls.IS_PREMIUM_USER = False
                        cls.user = None
                        return

                    try:
                        fernet = Fernet(decrypt_key)
                        encrypted_data = session_string[len("Fencrypted:"):]
                        session_string = fernet.decrypt(encrypted_data.encode()).decode()
                        LOGGER.info("Successfully decrypted USER_SESSION_STRING")
                    except InvalidToken:
                        LOGGER.error("Failed to decrypt USER_SESSION_STRING - Invalid key")
                        cls.IS_PREMIUM_USER = False
                        cls.user = None
                        return

                cls.user = cls.neoTgClient(
                    "NEO-WZML-User",
                    session_string=session_string,
                    sleep_threshold=60,
                    no_updates=True,
                )
                await cls.user.start()
                cls.IS_PREMIUM_USER = cls.user.me.is_premium
                if cls.IS_PREMIUM_USER:
                    cls.MAX_SPLIT_SIZE = 4194304000
                uname = cls.user.me.username or cls.user.me.first_name
                LOGGER.info(f"NEO-WZML User : [{uname}] Started!")
            except Exception as e:
                LOGGER.error(f"Failed to start client from USER_SESSION_STRING. {e}")
                cls.IS_PREMIUM_USER = False
                cls.user = None

    @classmethod
    def _get_decrypt_key(cls):
        from os import getenv

        if env_key := getenv("SESSION_DECRYPT_KEY", ""):
            return env_key.encode() if isinstance(env_key, str) else env_key

        if cache_key := bot_cache.get("decrypt_key"):
            return cache_key.encode() if isinstance(cache_key, str) else cache_key

        return None

    @classmethod
    async def stop(cls):
        async with cls._lock:
            if cls.bot:
                await cls.bot.stop()
                cls.bot = None
            if cls.user:
                await cls.user.stop()
                cls.user = None
            if cls.helper_bots:
                await gather(*[h_bot.stop() for h_bot in cls.helper_bots.values()])
                cls.helper_bots = {}
            LOGGER.info("All Client(s) stopped")

    @classmethod
    async def reload(cls):
        async with cls._lock:
            await cls.bot.restart()
            if cls.user:
                await cls.user.restart()
            if cls.helper_bots:
                await gather(*[h_bot.restart() for h_bot in cls.helper_bots.values()])
            LOGGER.info("All Client(s) restarted")
