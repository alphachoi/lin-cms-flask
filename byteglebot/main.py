import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)



def start(update, context):
    update.message.reply_text('Hi!')

def help(update, context):
    update.message.reply_text('Help!')

def echo(update, context):
    update.message.reply_text(update.message.text)

def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)

if __name__ == '__main__':
    updater = Updater('1852005171:AAFJsBm_vngp8aqoXFSbQrkJpTpRrL77RFE', use_context=True)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))

    dispatcher.add_handler(MessageHandler(Filters.text, echo))

    dispatcher.add_error_handler(error)

    updater.start_polling()
    updater.idle()