import ssl
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# Настройки логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Параметры бота и почты
TELEGRAM_TOKEN = '7772743241:AAFJbbrt_BTpLc8b-b4ISOPyzeYnV9PKvfQ'
EMAIL_LOGIN = 'glebnonstop@mail.ru'
EMAIL_PASSWORD = '05e7GXnbLx0QupCXe17E'
RECIPIENT_EMAIL = 'Inbox@rika-e.bizml.ru'
CORPORATE_PASSWORD = '3232'
ADMIN_PASSWORD = '1268'

# Хранение ролей пользователей
ADMIN_ROLE = "admin"
USER_ROLE = "user"
user_roles = {}
ADMIN_ID = None  # ID админа, будет установлен при первой авторизации админа

# Этапы диалога
PASSWORD, ORDER_PASS, CAR_DETAILS = range(3)

def log_request(user, request):
    """Функция для логирования запросов в файл"""
    with open("history.txt", "a") as file:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file.write(f"{timestamp}.{user}.{request}\n")

def save_user(user_id, username, role):
    """Функция для сохранения пользователей в файл"""
    with open("users.txt", "a") as file:
        file.write(f"{user_id},{username},{role}\n")

def send_email(subject, body):
    """Функция для отправки email и возвращения статуса отправки"""
    try:
        logger.info("Начало отправки email")
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_LOGIN
        msg['To'] = RECIPIENT_EMAIL

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.mail.ru", 465, context=context, timeout=10) as server:
            logger.info("Подключение к SMTP-серверу")
            server.login(EMAIL_LOGIN, EMAIL_PASSWORD)
            server.sendmail(EMAIL_LOGIN, RECIPIENT_EMAIL, msg.as_string())
            logger.info("Письмо успешно отправлено на %s", RECIPIENT_EMAIL)
        return True
    except Exception as e:
        logger.error("Ошибка при отправке письма: %s", e)
        return False

async def report_error(user, error_message):
    """Функция для отправки сообщений об ошибках админу"""
    if ADMIN_ID:
        await application.bot.send_message(ADMIN_ID, f"Ошибка у пользователя {user}: {error_message}")

# Стартовая функция
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Пользователь %s начал взаимодействие с ботом", update.effective_user.username)
    await update.message.reply_text("Введите корпоративный пароль для доступа к боту.")
    return PASSWORD

# Проверка пароля
async def verify_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global ADMIN_ID
    user_id = update.effective_user.id
    username = update.effective_user.username
    if update.message.text == CORPORATE_PASSWORD:
        user_roles[user_id] = USER_ROLE
        save_user(user_id, username, USER_ROLE)
        await update.message.reply_text("Пароль верен. Нажмите на кнопку 'Заказать пропуск'.",
                                        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Заказать пропуск")]], resize_keyboard=True))
        return ORDER_PASS
    elif update.message.text == ADMIN_PASSWORD:
        user_roles[user_id] = ADMIN_ROLE
        ADMIN_ID = user_id  # Установка ID администратора
        save_user(user_id, username, ADMIN_ROLE)
        await update.message.reply_text("Вы вошли как администратор.",
                                        reply_markup=ReplyKeyboardMarkup([
                                            [KeyboardButton("Заказать пропуск")],
                                            [KeyboardButton("История"), KeyboardButton("Пользователи")]
                                        ], resize_keyboard=True))
        return ORDER_PASS
    else:
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
    success = send_email(subject, car_info)
    if success:
        log_request(update.effective_user.username, car_info)
        await update.message.reply_text("Запрос на пропуск отправлен на КПП.")
    else:
        await update.message.reply_text("Произошла ошибка при отправке запроса. Попробуйте еще раз.")
        await report_error(update.effective_user.username, "Ошибка отправки письма")
    return ORDER_PASS

# Обработка кнопки 'История'
async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    MAX_MESSAGE_LENGTH = 4096  # Максимальная длина сообщения в Telegram

    if user_roles.get(user_id) == ADMIN_ROLE:  # Только администратор может просматривать историю
        try:
            with open("history.txt", "r", encoding="utf-8") as file:
                history = file.read()
            
            if not history.strip():
                await update.message.reply_text("История запросов пуста.")
                return

            # Разбиваем историю на части длиной не более MAX_MESSAGE_LENGTH
            history_parts = [history[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(history), MAX_MESSAGE_LENGTH)]
            
            for part in history_parts:
                await update.message.reply_text(part)

        except Exception as e:
            logger.error("Ошибка при чтении истории: %s", e)
            await update.message.reply_text("Не удалось загрузить историю.")
    else:
        await update.message.reply_text("У вас нет доступа к истории.")


# Обработка кнопки 'Пользователи'
async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_roles.get(user_id) == ADMIN_ROLE:  # Только администратор может просматривать список пользователей
        try:
            with open("users.txt", "r") as file:
                users = file.read()
            if users:
                await update.message.reply_text(f"Список пользователей:\n{users}")
            else:
                await update.message.reply_text("Список пользователей пуст.")
        except Exception as e:
            logger.error("Ошибка при чтении списка пользователей: %s", e)
            await update.message.reply_text("Не удалось загрузить список пользователей.")
    else:
        await update.message.reply_text("У вас нет доступа к списку пользователей.")

# Обработка команды отмены
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Пользователь %s отменил процесс", update.effective_user.username)
    await update.message.reply_text("Процесс отменен. Введите /start для нового запроса.")
    return ConversationHandler.END

# Основная функция для запуска бота
def main():
    logger.info("Запуск Telegram бота")
    global application
    application = Application.builder() \
        .token(TELEGRAM_TOKEN) \
        .read_timeout(60) \  # Увеличиваем таймаут чтения
        .connect_timeout(60) \  # Увеличиваем таймаут подключения
        .build()

    # Настройка диалогов
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_password)],
            ORDER_PASS: [
                MessageHandler(filters.Regex('^Заказать пропуск$'), order_pass),
                MessageHandler(filters.Regex('^История$'), show_history),
                MessageHandler(filters.Regex('^Пользователи$'), show_users),
            ],
            CAR_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, car_details)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Добавление обработчиков
    application.add_handler(conv_handler)

    # Запуск бота
    application.run_polling()
    logger.info("Telegram бот завершил работу")
