from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import logging
from bot_utils.commands import start, redeem, checktime, createkey, bulkcreatekey, deletekey, createscript, scripts, script_info, delete_script, purchase, cancel
from bot_utils.commands import call, cvv, amazon, bank, crypto, live, email, customcall, process_queue, keystat, pgp
from bot_utils.handler import handler

# DATABASE
import database.database

# ENV
import os
from dotenv import load_dotenv
load_dotenv()

telegram_bot_token = os.getenv('BOT_TOKEN')


# LOGGER
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)



app = ApplicationBuilder().token(telegram_bot_token).build()

# BASIC FUNCTION
app.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("redeem", redeem, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("checktime", checktime, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("purchase", purchase)) # GROUP TOO
app.add_handler(CommandHandler("createkey", createkey, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("bulkcreatekey", bulkcreatekey, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("deletekey", deletekey, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("keystat", keystat, filters=filters.ChatType.PRIVATE))

# CUSTOM
app.add_handler(CommandHandler("createscript", createscript))
app.add_handler(MessageHandler((filters.TEXT & ~filters.COMMAND) & filters.ChatType.PRIVATE, createscript))
app.add_handler(CallbackQueryHandler(handler))
app.add_handler(CallbackQueryHandler(createscript))

app.add_handler(CommandHandler("scripts", scripts, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("script", script_info, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("deletescript", delete_script, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("cancel", cancel, filters=filters.ChatType.PRIVATE))

# MODULES
app.add_handler(CommandHandler("call", call, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("customcall", customcall, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("cvv", cvv, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("amazon", amazon, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("bank", bank, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("crypto", crypto, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("live", live, filters=filters.ChatType.PRIVATE))
app.add_handler(CommandHandler("email", email, filters=filters.ChatType.PRIVATE))
#app.add_handler(CommandHandler("pgp", pgp, filters=filters.ChatType.PRIVATE))

job_queue = app.job_queue
job_queue.run_once(process_queue, 1, job_kwargs={"misfire_grace_time": None})

app.run_polling()



