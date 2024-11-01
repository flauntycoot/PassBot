import os
import ssl
import logging
from dotenv import load_dotenv
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import smtplib
from email.mime.text import MIMEText

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загружаем переменные из .env файла
load_dotenv()

# Переменные из .env
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
EMAIL_LOGIN = os.getenv('EMAIL_LOGIN')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')
CORPORATE_PASSWORD = os.getenv('CORPORATE_PASSWORD')

# Этапы диалога
PASSWORD, ORDER_PASS, CAR_DETAILS = range(3)

# Функция для отправки email с логами
def send_email(subject, body):
    try:
        logger.info("Начало отправки email")
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_LOGIN
        msg['To'] = RECIPIENT_EMAIL

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.mail.ru", 465, context=context) as server:
            logger.info("Подключение к SMTP-серверу")
            server.login(EMAIL_LOGIN, EMAIL_PASSWORD)
            logger.info("Аутентификация на SMTP-сервере прошла успешно")
            server.sendmail(EMAIL_LOGIN, RECIPIENT_EMAIL, msg.as_string())
            logger.info("Письмо успешно отправлено на %s", RECIPIENT_EMAIL)
    except smtplib.SMTPAuthenticationError as e:
        logger.error("Ошибка аутентификации: Проверьте логин и пароль приложения. %s", e)
    except smtplib.SMTPException as e:
        logger.error("Ошибка при отправке письма: %s", e)
    except Exception as e:
        logger.error("Произошла непредвиденная ошибка: %s", e)

# Стартовая функция
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Пользователь %s начал взаимодействие с ботом", update.effective_user.username)
    await update.message.reply_text("Введите корпоративный пароль для доступа к боту.")
    return PASSWORD

# Проверка пароля
async def verify_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == CORPORATE_PASSWORD:
        logger.info("Пользователь %s ввел верный пароль", update.effective_user.username)
        await update.message.reply_text(
            "Пароль верен. Нажмите на кнопку 'Заказать пропуск'.",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Заказать пропуск")]], resize_keyboard=True)
        )
        return ORDER_PASS
    else:
        logger.warning("Пользователь %s ввел неверный пароль", update.effective_user.username)
        await update.message.reply_text("Неверный пароль. Попробуйте снова.")
        return PASSWORD

# Обработка нажатия на кнопку "Заказать пропуск"
async def order_pass(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Пользователь %s выбрал 'Заказать пропуск'", update.effective_user.username)
    await update.message.reply_text("Введите марку и номер машины.")
    return CAR_DETAILS

# Отправка информации о машине на почту
async def car_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    car_info = update.message.text
    subject = "Запрос на пропуск"
    logger.info("Отправка данных машины на email для пользователя %s", update.effective_user.username)
    send_email(subject, car_info)
    await update.message.reply_text("Запрос на пропуск отправлен на КПП.")
    return ConversationHandler.END

# Обработка команды отмены
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Пользователь %s отменил процесс", update.effective_user.username)
    await update.message.reply_text("Процесс отменен. Введите /start для нового запроса.")
    return ConversationHandler.END

# Основная функция для запуска бота
def main():
    logger.info("Запуск Telegram бота")
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Настройка диалогов
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_password)],
            ORDER_PASS: [MessageHandler(filters.Regex('^Заказать пропуск$'), order_pass)],
            CAR_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, car_details)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)

    # Запуск бота
    application.run_polling()
    logger.info("Telegram бот завершил работу")

if __name__ == '__main__':
    main()
