import json
import datetime
import asyncio
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройки
API_TOKEN = '8296355603:AAG1cxea5g-oTPBmxCN5_mEUlR2Uofo8p20'  # Токен бота
FORUM_CHAT_ID = -1002612779922  # ID группы с форумом

# Состояния
MAIN_MENU, FAQ_CATEGORIES, FAQ_QUESTIONS, FAQ_ANSWER, SUPPORT_WAITING = range(5)

# Загрузка и сохранение данных
def load_faq():
    try:
        with open('faq.json', 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                logger.error("FAQ файлы бос")
                return {}
            return json.loads(content)
    except FileNotFoundError:
        logger.error("FAQ файлы табылмады")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"FAQ файлының синтаксисі дұрыс емес: {e}")
        return {}
    except Exception as e:
        logger.error(f"FAQ файлы оқылғанда қате пайда болды: {e}")
        return {}

def load_dialogs():
    try:
        with open('dialogs.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_dialogs(dialogs):
    try:
        with open('dialogs.json', 'w', encoding='utf-8') as f:
            json.dump(dialogs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"dialogs.json сақтау кезінде қате пайда болды: {e}")

# Проверка активных диалогов
def is_dialog_active(user_id):
    dialogs = load_dialogs()
    active = any(d['user_id'] == user_id for d in dialogs.values())
    logger.info(f"user_id {user_id} үшін белсенді диалогты тексеру: {active}")
    return active

def get_dialog_by_user(user_id):
    dialogs = load_dialogs()
    for topic_id, data in dialogs.items():
        if data['user_id'] == user_id:
            return {'topic_id': topic_id, **data}
    return None

def save_dialog(topic_id, user_id, started_at):
    dialogs = load_dialogs()
    dialogs[str(topic_id)] = {
        'user_id': user_id,
        'started_at': started_at,
        'last_activity': started_at
    }
    save_dialogs(dialogs)
    logger.info(f"Диалог сақталды: topic_id={topic_id}, user_id={user_id}")

def update_dialog_activity(topic_id):
    dialogs = load_dialogs()
    if topic_id in dialogs:
        dialogs[topic_id]['last_activity'] = datetime.datetime.now().isoformat()
        save_dialogs(dialogs)
        logger.info(f"Диалогтың белсенді уақыты жаңартылды: {topic_id}")

async def close_dialog(topic_id, context: ContextTypes.DEFAULT_TYPE):
    dialogs = load_dialogs()
    if topic_id in dialogs:
        user_id = dialogs[topic_id]['user_id']
        try:
            await context.bot.close_forum_topic(
                chat_id=FORUM_CHAT_ID,
                message_thread_id=int(topic_id)
            )
            logger.info(f"Форумдағы тақырып жабылды: topic_id={topic_id}")
        except Exception as e:
            logger.error(f"Тақырыпты жабу кезінде қате пайда болды: {e}")
        del dialogs[topic_id]
        save_dialogs(dialogs)
        logger.info(f"Диалог жабылды: {topic_id}")
        return user_id
    return None

def reset_dialogs_for_user(user_id):
    dialogs = load_dialogs()
    dialogs = {k: v for k, v in dialogs.items() if v['user_id'] != user_id}
    save_dialogs(dialogs)
    logger.info(f"Пайдаланушы {user_id} үшін барлық диалогтар қалпына келтірілді")

# Главное меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пайдаланушы {update.effective_user.id} /start командасын алды")
    context.user_data.clear()
    reset_dialogs_for_user(update.effective_user.id)
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("Жылдам жауаптар")], [KeyboardButton("Оператормен байланысу")]],
        resize_keyboard=True,
    )
    await update.message.reply_text(
        "<b>Сәлеметсіз бе! Мен Шымкент көлік колледжінің виртуалды көмекшісімін. Кез келген сұрақты шешуге көмектесемін 🙂</b>\n\n"
        "<b>Қосымша ақпарат алу үшін колледж әкімшілігіне хабарласыңыз: 8 (7252) 92-11-99, shtkkazatk@mail.ru</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    return MAIN_MENU

# Команда /stop_dialog
async def stop_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    dialog = get_dialog_by_user(user_id)
    if dialog:
        topic_id = dialog['topic_id']
        user_id = await close_dialog(topic_id, context)
        if user_id:
            keyboard = ReplyKeyboardMarkup(
                [[KeyboardButton("Жылдам жауаптар")], [KeyboardButton("Оператормен байланысу")]],
                resize_keyboard=True,
            )
            await update.message.reply_text(
                "<b>Диалог аяқталды. Жұмысыңыз үшін рақмет!</b>",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        return MAIN_MENU
    else:
        await update.message.reply_text(
            "<b>Сізде белсенді диалог жоқ.</b>",
            parse_mode="HTML"
        )
        return await start(update, context)

# FAQ: Категории
async def faq_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пайдаланушы {update.effective_user.id} FAQ сұрауын алды: {update.message.text}")
    if is_dialog_active(update.effective_user.id):
        await update.message.reply_text(
            "<b>Сізде белсенді өтініш бар. Оператордың жауабын күтіңіз немесе /stop_dialog командасымен диалогты аяқтаңыз.</b>",
            parse_mode="HTML"
        )
        return MAIN_MENU
    if update.message.text != "Жылдам жауаптар":
        await update.message.reply_text(
            "<b>Навигация үшін түймелерді пайдаланыңыз.</b>",
            parse_mode="HTML"
        )
        return MAIN_MENU

    faq = load_faq()
    if not faq:
        await update.message.reply_text(
            "<b>FAQ табылмады. Кейінірек қайталап көріңіз.</b>",
            parse_mode="HTML"
        )
        return MAIN_MENU

    keyboard = [[KeyboardButton(f"{i+1}. {category}")] for i, category in enumerate(faq.keys())]
    keyboard.append([KeyboardButton("Бастапқы мәзірге оралу")])
    keyboard = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Формируем текстовый список категорий
    categories_text = "\n".join(f"{i+1}. {category}" for i, category in enumerate(faq.keys()))
    await update.message.reply_text(
        f"<b>Санатты таңдаңыз:</b>\n\n{categories_text}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    return FAQ_CATEGORIES

# FAQ: Вопросы
async def faq_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пайдаланушы {update.effective_user.id} санатты таңдады: {update.message.text}")
    if is_dialog_active(update.effective_user.id):
        await update.message.reply_text(
            "<b>Сізде белсенді өтініш бар. Оператордың жауабын күтіңіз немесе /stop_dialog командасымен диалогты аяқтаңыз.</b>",
            parse_mode="HTML"
        )
        return MAIN_MENU
    faq = load_faq()
    selected = update.message.text

    category = selected.split('. ', 1)[1] if '. ' in selected else selected

    if category == "Бастапқы мәзірге оралу":
        return await start(update, context)
    if category in faq:
        context.user_data['current_category'] = category
        keyboard = [[KeyboardButton(f"{i+1}. {question}")] for i, question in enumerate(faq[category].keys())]
        keyboard.append([KeyboardButton("Артқа")])
        keyboard = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        # Формируем текстовый список вопросов
        questions_text = "\n".join(f"{i+1}. {question}" for i, question in enumerate(faq[category].keys()))
        await update.message.reply_text(
            f"<b>Қызықтыратын сұрақты таңдаңыз:</b>\n\n{questions_text}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return FAQ_QUESTIONS
    await update.message.reply_text(
        "<b>Тізімнен санатты таңдаңыз.</b>",
        parse_mode="HTML"
    )
    return FAQ_CATEGORIES

# FAQ: Ответ
async def faq_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пайдаланушы {update.effective_user.id} сұрақты таңдады: {update.message.text}")
    if is_dialog_active(update.effective_user.id):
        await update.message.reply_text(
            "<b>Сізде белсенді өтініш бар. Оператордың жауабын күтіңіз немесе /stop_dialog командасымен диалогты аяқтаңыз.</b>",
            parse_mode="HTML"
        )
        return MAIN_MENU
    category = context.user_data.get('current_category')
    faq = load_faq()
    selected = update.message.text

    question = selected.split('. ', 1)[1] if '. ' in selected else selected

    if question == "Артқа":
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton(f"{i+1}. {q}")] for i, q in enumerate(faq[category].keys())] +
            [[KeyboardButton("Бастапқы мәзірге оралу")]],
            resize_keyboard=True,
        )
        questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(faq[category].keys()))
        await update.message.reply_text(
            f"<b>Қызықтыратын сұрақты таңдаңыз:</b>\n\n{questions_text}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return FAQ_QUESTIONS
    if question == "Бастапқы мәзірге оралу":
        return await start(update, context)
    if category in faq and question in faq[category]:
        answer = faq[category][question]
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("Артқа")]],
            resize_keyboard=True,
        )
        await update.message.reply_text(
            f"<b>{answer}</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return FAQ_ANSWER
    await update.message.reply_text(
        "<b>Тізімнен сұрақты таңдаңыз.</b>",
        parse_mode="HTML"
    )
    return FAQ_QUESTIONS

# Возврат из ответа
async def back_from_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пайдаланушы {update.effective_user.id} жауаптан қайтады: {update.message.text}")
    if is_dialog_active(update.effective_user.id):
        await update.message.reply_text(
            "<b>Сізде белсенді өтініш бар. Оператордың жауабын күтіңіз немесе /stop_dialog командасымен диалогты аяқтаңыз.</b>",
            parse_mode="HTML"
        )
        return MAIN_MENU
    if update.message.text == "Артқа":
        category = context.user_data.get('current_category')
        faq = load_faq()
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton(f"{i+1}. {q}")] for i, q in enumerate(faq[category].keys())] +
            [[KeyboardButton("Бастапқы мәзірге оралу")]],
            resize_keyboard=True,
        )
        questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(faq[category].keys()))
        await update.message.reply_text(
            f"<b>Қызықтыратын сұрақты таңдаңыз:</b>\n\n{questions_text}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return FAQ_QUESTIONS
    if update.message.text == "Бастапқы мәзірге оралу":
        return await start(update, context)
    await update.message.reply_text(
        "<b>Навигация үшін түймелерді пайдаланыңыз.</b>",
        parse_mode="HTML"
    )
    return FAQ_ANSWER

# Отложенные ответы при ожидании оператора
async def send_delayed_messages(topic_id, user_id, context: ContextTypes.DEFAULT_TYPE):
    delays = [
        (60, "<b>Сіздің өтінішіңіз өңделуде. Оператор жақын арада жауап береді.</b>"),
        (180, "<b>Әлі де жауап күтудесіз бе? Біз сіздің сұрағыңызды қарастырудамыз. Табандылығыңыз үшін рақмет!</b>"),
        (300, "<b>Операторлар қазір бос емес болуы мүмкін. Тағы біраз күтіңіз немесе /stop_dialog командасымен диалогты аяқтаңыз.</b>")
    ]
    for delay, message in delays:
        await asyncio.sleep(delay)
        dialogs = load_dialogs()
        if topic_id not in dialogs:
            return
        try:
            await context.bot.send_message(
                user_id,
                message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Пайдаланушыға {user_id} отложенное хабарлама жіберу кезінде қате пайда болды: {e}")

# Связь с оператором
async def start_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пайдаланушы {update.effective_user.id} оператормен байланысу сұрауын жіберді")
    if is_dialog_active(update.effective_user.id):
        await update.message.reply_text(
            "<b>Сізде белсенді өтініш бар. Оператордың жауабын күтіңіз немесе /stop_dialog командасымен диалогты аяқтаңыз.</b>",
            parse_mode="HTML"
        )
        return MAIN_MENU
    if update.message.text != "Оператормен байланысу":
        await update.message.reply_text(
            "<b>Навигация үшін түймелерді пайдаланыңыз.</b>",
            parse_mode="HTML"
        )
        return MAIN_MENU
    username = update.effective_user.username
    unique_number = f"@{username}" if username else f"ID{update.effective_user.id}"
    try:
        topic_response = await context.bot.create_forum_topic(
            chat_id=FORUM_CHAT_ID,
            name=f"Өтініш #{unique_number}",
        )
        topic_id = topic_response.message_thread_id
        logger.info(f"Форумда тақырып жасалды: topic_id={topic_id}, name=Өтініш #{unique_number}")
        if topic_id is None:
            logger.error(f"#{unique_number} өтініші үшін topic_id алу мүмкін болмады. Форум параметрлерін тексеріңіз.")
            await update.message.reply_text(
                "<b>Қате: тақырып жасау мүмкін болмады. Форум режимі қосылғанын және боттың әкімші құқықтары бар екенін тексеріңіз.</b>",
                parse_mode="HTML"
            )
            return await start(update, context)
        
        save_dialog(str(topic_id), update.effective_user.id, datetime.datetime.now().isoformat())
        await update.message.reply_text(
            "<b>Сіздің хабарламаңыз операторға жіберілді. Жауапты күтіңіз.</b>",
            parse_mode="HTML"
        )
        asyncio.create_task(send_delayed_messages(str(topic_id), update.effective_user.id, context))
        asyncio.create_task(close_dialog_after_timeout(str(topic_id), update.effective_user.id, context, 900))
        return SUPPORT_WAITING
    except Exception as e:
        logger.error(f"Форумда тақырып жасау кезінде қате пайда болды: {e}")
        await update.message.reply_text(
            "<b>Өтініш жасау кезінде қате пайда болды. Боттың топқа қосылғанын, әкімші құқықтары бар екенін және форум режимі қосылғанын тексеріңіз.</b>",
            parse_mode="HTML"
        )
        return await start(update, context)

# Пересылка сообщения оператору
async def forward_to_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пайдаланушы {update.effective_user.id} хабарламасын жіберді: {update.message.text}")
    dialog = get_dialog_by_user(update.effective_user.id)
    if dialog:
        topic_id = dialog['topic_id']
        try:
            await context.bot.send_message(
                chat_id=FORUM_CHAT_ID,
                text=update.message.text,
                message_thread_id=int(topic_id),
            )
           
            return SUPPORT_WAITING
        except Exception as e:
            logger.error(f"Форумға хабарлама жіберу кезінде қате пайда болды: {e}")
            await update.message.reply_text(
                "<b>Хабарлама жіберу кезінде қате пайда болды. Қайтадан бастаңыз.</b>",
                parse_mode="HTML"
            )
            return await start(update, context)
    await update.message.reply_text(
        "<b>Диалог чат операторымен жабылды.</b>",
        parse_mode="HTML"
    )
    return await start(update, context)

# Обработка ответа оператора
async def handle_operator_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Форумда оператордың жауабы алынды: chat_id={update.message.chat_id}, thread_id={update.message.message_thread_id}")
    if update.message.chat_id == FORUM_CHAT_ID and update.message.reply_to_message:
        topic_id = str(update.message.message_thread_id)
        dialogs = load_dialogs()
        if topic_id in dialogs:
            user_id = dialogs[topic_id]['user_id']
            try:
                await context.bot.send_message(
                    user_id,
                    f"<b>{update.message.text}</b>",
                    parse_mode="HTML"
                )
                update_dialog_activity(topic_id)
            except Exception as e:
                logger.error(f"Пайдаланушыға {user_id} жауап жіберу кезінде қате пайда болды: {e}")

# Автоматическое закрытие диалога при неактивности
async def close_dialog_after_timeout(topic_id, user_id, context, timeout):
    while True:
        await asyncio.sleep(60)
        dialogs = load_dialogs()
        if topic_id not in dialogs:
            return
        last_activity = datetime.datetime.fromisoformat(dialogs[topic_id]['last_activity'])
        if (datetime.datetime.now() - last_activity).total_seconds() >= timeout:
            user_id = await close_dialog(topic_id, context)
            if user_id:
                keyboard = ReplyKeyboardMarkup(
                    [[KeyboardButton("Жылдам жауаптар")], [KeyboardButton("Оператормен байланысу")]],
                    resize_keyboard=True,
                )
                try:
                    await context.bot.send_message(
                        user_id,
                        "<b>Жауап болмағандықтан өтініш жабылды.</b>",
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Пайдаланушыға {user_id} диалогты жабу туралы хабарлама жіберу кезінде қате пайда болды: {e}")
                return

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text(
            "<b>Қате пайда болды. Кейінірек қайталап көріңіз немесе оператормен байланысыңыз.</b>",
            parse_mode="HTML"
        )

# Настройка бота
def main():
    app = Application.builder().token(API_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop_dialog", stop_dialog))
    app.add_error_handler(error_handler)

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Text(["Жылдам жауаптар", "Оператормен байланысу"]), faq_categories),
        ],
        states={
            MAIN_MENU: [
                MessageHandler(filters.Text(["Жылдам жауаптар"]), faq_categories),
                MessageHandler(filters.Text(["Оператормен байланысу"]), start_support),
            ],
            FAQ_CATEGORIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, faq_questions)],
            FAQ_QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, faq_answer)],
            FAQ_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, back_from_answer)],
            SUPPORT_WAITING: [MessageHandler(filters.TEXT & ~filters.COMMAND, forward_to_support)],
        },
        fallbacks=[CommandHandler("start", start), CommandHandler("stop_dialog", stop_dialog)],
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.Chat(FORUM_CHAT_ID) & filters.REPLY, handle_operator_reply))

    logger.info("Ботты іске қосу...")
    app.run_polling()

if __name__ == '__main__':
    main()