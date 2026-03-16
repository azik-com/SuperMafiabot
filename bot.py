# =============================================
#  MAFIA BOT — Asosiy fayl
#  python-telegram-bot v20+
#  pip install python-telegram-bot
# =============================================
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)
from config import BOT_TOKEN
from handlers import (
    cmd_start,
    cmd_help,
    cmd_newgame,
    cmd_join,
    cmd_start_game,
    cmd_cancel_game,
    cmd_players,
    callback_handler,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Buyruqlar
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("newgame", cmd_newgame))
    app.add_handler(CommandHandler("join", cmd_join))
    app.add_handler(CommandHandler("start_game", cmd_start_game))
    app.add_handler(CommandHandler("cancel_game", cmd_cancel_game))
    app.add_handler(CommandHandler("players", cmd_players))

    # Inline tugmalar
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("🎭 Mafia Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
