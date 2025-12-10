import json
import datetime
import asyncio
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
import os


API_TOKEN = "8584072836:AAGVmKIZbK7adIlSkHvKXB6qWubhWki3jYU"
FORUM_CHAT_ID = -1003464424140

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

(
    MAIN_MENU, FAQ_CATEGORIES, FAQ_QUESTIONS, FAQ_ANSWER, SUPPORT_WAITING,
    FORM_NAME, FORM_SURNAME, FORM_BIRTHYEAR, FORM_CITY, FORM_SOURCE,
    FORM_FAMILY_STATUS, FORM_HAS_ATTESTAT, FORM_SPECIALTY, FORM_WHY_JOIN,
    FORM_PHONE, FORM_CONFIRM,
    SCHOOL_MENU, SCHOOL_FORM_NAME, SCHOOL_FORM_SCHOOL, SCHOOL_FORM_CLASS,
    SCHOOL_FORM_PHONE, SCHOOL_FORM_SOCIAL, SCHOOL_FORM_CONFIRM
) = range(23)

def get_google_sheet():
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        if not os.path.exists("service_account.json"):
            return None
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
        client = gspread.authorize(creds)
        return client.open("Шымкент колледжі – өтініштер").sheet1
    except Exception as e:
        return None

def get_school_sheet():
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        if not os.path.exists("service_account.json"):
            return None
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
        client = gspread.authorize(creds)
        return client.open("Шымкент колледжі – мектеп оқушылары").sheet1
    except Exception as e:
        return None

def has_main_application(user_id):
    sheet = get_google_sheet()
    if not sheet:
        return False
    try:
        ids = sheet.col_values(11) 
        return str(user_id) in ids
    except:
        return False

def has_school_application(user_id):
    sheet = get_school_sheet()
    if not sheet:
        return False
    try:
        ids = sheet.col_values(7)
        return str(user_id) in ids
    except:
        return False

def load_faq():
    try:
        with open("faq.json", "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except Exception as e:
        return {}

def load_dialogs():
    try:
        with open("dialogs.json", "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        return {}

def save_dialogs(dialogs):
    try:
        with open("dialogs.json", "w", encoding="utf-8") as f:
            json.dump(dialogs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        pass

def is_dialog_active(user_id):
    return any(d.get("user_id") == user_id for d in load_dialogs().values())

def get_dialog_by_user(user_id):
    for tid, data in load_dialogs().items():
        if data.get("user_id") == user_id:
            return {"topic_id": tid, **data}
    return None

def get_dialog_by_topic(topic_id):
    dialogs = load_dialogs()
    if str(topic_id) in dialogs:
        return {"topic_id": str(topic_id), **dialogs[str(topic_id)]}
    return Nones

def save_dialog(topic_id, user_id):
    dialogs = load_dialogs()
    now_iso = datetime.datetime.now().isoformat()
    dialogs[str(topic_id)] = {
        "user_id": user_id,
        "started_at": now_iso,
        "last_activity": now_iso
    }
    save_dialogs(dialogs)

def update_dialog_activity(topic_id):
    dialogs = load_dialogs()
    tid = str(topic_id)
    if tid in dialogs:
        dialogs[tid]["last_activity"] = datetime.datetime.now().isoformat()
        save_dialogs(dialogs)

async def close_dialog(topic_id, context):
    dialogs = load_dialogs()
    tid = str(topic_id)
    if tid in dialogs:
        user_id = dialogs[tid]["user_id"]
        try:
            await context.bot.send_message(
                chat_id=FORUM_CHAT_ID,
                message_thread_id=int(tid),
                text=f"<b>Диалог жабылды.</b> Пайдаланушы хабарлама жібере алмайды.",
                parse_mode="HTML"
            )
            await context.bot.close_forum_topic(chat_id=FORUM_CHAT_ID, message_thread_id=int(tid))
        except Exception as e:
            pass

        del dialogs[tid]
        save_dialogs(dialogs)
        return user_id
    return None

def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("Жылдам жауаптар")],
        [KeyboardButton("Оператормен байланысу")],
        [KeyboardButton("Өтініш қалдыру")],
        [KeyboardButton("Мектеп оқушылары үшін")]
    ], resize_keyboard=True)

def school_menu_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("Өтініш қалдыру")],
        [KeyboardButton("Артқа")]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Сәлеметсіз бе! Мен Шымкент көлік колледжінің виртуалды көмекшісімін. Кез келген сұрақты шешуге көмектесемін 🙂\n\n"
        "Қосымша ақпарат алу үшін колледж әкімшілігіне хабарласыңыз: 8 (7252) 92-11-99, shtkkazatk@mail.ru",
        reply_markup=main_keyboard()
    )
    return MAIN_MENU

async def stop_dialog_user(user_id, context):
    dialog = get_dialog_by_user(user_id)
    if dialog:
        closed_user_id = await close_dialog(dialog["topic_id"], context)
        if closed_user_id:
            await context.bot.send_message(
                closed_user_id,
                "Диалог аяқталды. Рақмет! Енді сіз негізгі мәзірдесіз.",
                reply_markup=main_keyboard()
            )
            return True
    return False

async def stop_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == FORUM_CHAT_ID and update.message.message_thread_id:
        topic_id = update.message.message_thread_id
        dialog = get_dialog_by_topic(topic_id)

        if dialog:
            user_id = await close_dialog(topic_id, context)
            if user_id:
                await context.bot.send_message(
                    user_id,
                    "Оператор диалогты жапты. Рақмет! Енді сіз негізгі мәзірдесіз.",
                    reply_markup=main_keyboard()
                )
            await update.message.reply_text("✅ Қолданушымен диалог аяқталды.", message_thread_id=topic_id)
        else:
            await update.message.reply_text("Белсенді диалог жоқ.", message_thread_id=topic_id)
        return
    else:
        success = await stop_dialog_user(update.effective_user.id, context)
        if not success:
            await update.message.reply_text("Белсенді диалог жоқ.", reply_markup=main_keyboard())

    return MAIN_MENU

async def cancel_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Өтініш толтыру тоқтатылды.", reply_markup=main_keyboard())
    context.user_data.clear()
    return MAIN_MENU

async def faq_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_dialog_active(update.effective_user.id):
        await update.message.reply_text("Белсенді диалог бар. /stop_dialog арқылы жабыңыз.")
        return SUPPORT_WAITING

    faq = load_faq()
    if not faq:
        await update.message.reply_text("FAQ табылмады.")
        return MAIN_MENU

    keyboard = [[KeyboardButton(f"{i+1}. {cat}")] for i, cat in enumerate(faq.keys())]
    keyboard.append([KeyboardButton("Бастапқы мәзірге оралу")])
    text = "<b>Санатты таңдаңыз:</b>\n\n" + "\n".join(f"{i+1}. {cat}" for i, cat in enumerate(faq.keys()))
    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode="HTML")
    return FAQ_CATEGORIES

async def faq_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Бастапқы мәзірге оралу":
        return await start(update, context)

    if update.message.text == "Артқа":
        return await faq_categories(update, context)

    faq = load_faq()
    category = update.message.text.split(". ", 1)[1] if ". " in update.message.text else update.message.text

    if update.message.text in ["Оператормен байланысу", "Өтініш қалдыру"]:
        return await start(update, context)

    if category not in faq:
        await update.message.reply_text("Санатты тізімнен таңдаңыз.")
        return FAQ_CATEGORIES

    context.user_data["current_category"] = category
    questions = list(faq[category].keys())
    keyboard = [[KeyboardButton(f"{i+1}. {q}")] for i, q in enumerate(questions)]
    keyboard.append([KeyboardButton("Артқа")])
    text = "<b>Сұрақты таңдаңыз:</b>\n\n" + "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True), parse_mode="HTML")
    return FAQ_QUESTIONS

async def faq_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Артқа":
        return await faq_questions(update, context)

    category = context.user_data.get("current_category")
    faq = load_faq()
    question = update.message.text.split(". ", 1)[1] if ". " in update.message.text else update.message.text

    if category in faq and question in faq[category]:
        answer = faq[category][question]
        await update.message.reply_text(f"<b>{answer}</b>", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Артқа")]], resize_keyboard=True), parse_mode="HTML")
        return FAQ_ANSWER

    await update.message.reply_text("Сұрақты тізімнен таңдаңыз.")
    return FAQ_QUESTIONS

async def back_from_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Артқа":
        return await faq_questions(update, context)

    return FAQ_ANSWER

async def send_delayed_messages(topic_id, user_id, context):
    messages = [
        (225, "Сіздің өтінішіңіз өңделуде. Оператор жақын арада жауап береді."),
        (550, "Сіз әлі күтудесіз бе? Біздің операторлар сіздің сұрағыңызды қарастыруда."),
        (1100, "Операторлар бос емес болуы мүмкін. Өтінеміз, тағы біраз күтіңіз."),
        (1650, "Күту уақыты ұзарды. Егер сіз күтуді тоқтатқыңыз келсе, /stop_dialog командасын қолданыңыз."),
    ]

    start_time = datetime.datetime.now()

    for delay, msg in messages:
        time_to_wait = (start_time + datetime.timedelta(seconds=delay)) - datetime.datetime.now()
        if time_to_wait.total_seconds() > 0:
            await asyncio.sleep(time_to_wait.total_seconds())

        if str(topic_id) not in load_dialogs():
            return

        try:
            await context.bot.send_message(user_id, msg)
        except Exception as e:
            pass

async def close_dialog_after_timeout(topic_id, context):
    await asyncio.sleep(900)
    if str(topic_id) in load_dialogs():
        user_id = await close_dialog(topic_id, context)
        if user_id:
            try:
                await context.bot.send_message(user_id, "Белсенділік болмағандықтан диалог жабылды.", reply_markup=main_keyboard())
            except:
                pass

async def start_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "Оператормен байланысу":
        return MAIN_MENU

    user_id = update.effective_user.id
    if is_dialog_active(user_id):
        await update.message.reply_text("Белсенді диалог бар. Оператордың жауабын күтіңіз.")
        return SUPPORT_WAITING

    username = update.effective_user.username or f"ID_{user_id}"
    try:
        topic = await context.bot.create_forum_topic(
            chat_id=FORUM_CHAT_ID,
            name=f"Өтініш @{username} (ID:{user_id})"
        )
        topic_id = topic.message_thread_id

        save_dialog(topic_id, user_id)

        first_message_text = f"<b>Жаңа өтініш!</b>\n\nПайдаланушы (TG ID): @{username}\nID: <code>{user_id}</code>\n\nОператорды күтуде..."

        await context.bot.send_message(
            chat_id=FORUM_CHAT_ID,
            message_thread_id=topic_id,
            text=first_message_text,
            parse_mode="HTML"
        )

        await update.message.reply_text(
            "Хабарламаңыз операторға жіберілді. Жауап күтіңіз.\n\n"
            "Диалогты аяқтау үшін /stop_dialog командасын қолданыңыз.",
            reply_markup=ReplyKeyboardRemove()
        )

        asyncio.create_task(send_delayed_messages(topic_id, user_id, context))
        asyncio.create_task(close_dialog_after_timeout(topic_id, context))

        return SUPPORT_WAITING
    except Exception as e:
        await update.message.reply_text(
            "Техникалық қате: форум тобына қосыла алмадым. "
            "Операторға тікелей хабарласыңыз немесе кейін қайталаңыз.",
            reply_markup=main_keyboard()
        )
        return MAIN_MENU

async def handle_main_menu_in_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Жылдам жауаптар":
        await stop_dialog_user(update.effective_user.id, context)
        return await faq_categories(update, context)
    elif text == "Өтініш қалдыру":
        await stop_dialog_user(update.effective_user.id, context)
        return await start_form(update, context)
    else:
        return await forward_to_support(update, context)


async def forward_to_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dialog = get_dialog_by_user(update.effective_user.id)
    if not dialog:
        await update.message.reply_text("Диалог жабылды.", reply_markup=main_keyboard())
        return await start(update, context)

    topic_id = dialog["topic_id"]
    try:
        await context.bot.copy_message(
            chat_id=FORUM_CHAT_ID,
            message_thread_id=int(topic_id),
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
            caption=f"Пайдаланушы: {update.message.caption or update.message.text or 'Медиа файл'}"
        )
        update_dialog_activity(topic_id)
    except Exception as e:
        await update.message.reply_text("Хабарламаны жіберуде қате пайда болды.")

    return SUPPORT_WAITING

async def handle_operator_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != FORUM_CHAT_ID:
        return

    topic_id = update.message.message_thread_id
    if not topic_id:
        return

    topic_id_str = str(topic_id)
    dialogs = load_dialogs()

    if topic_id_str in dialogs:
        user_id = dialogs[topic_id_str]["user_id"]
        try:
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=FORUM_CHAT_ID,
                message_id=update.message.message_id
            )
            update_dialog_activity(topic_id_str)
        except Exception as e:
            pass
    else:
        pass

async def start_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "Өтініш қалдыру":
        return MAIN_MENU

    if is_dialog_active(update.effective_user.id):
        await update.message.reply_text("Белсенді диалог бар. /stop_dialog арқылы жабыңыз.")
        return SUPPORT_WAITING

    if has_main_application(update.effective_user.id):
        await update.message.reply_text(
            "Сіз бұл бөлімде өтінішті бір рет қана қалдыра аласыз.\nБіз сізбен міндетті түрде хабарласамыз!",
            reply_markup=main_keyboard()
        )
        return MAIN_MENU

    await update.message.reply_text(
        "<b>Оқуға өтініш қалдыру</b>\n\n"
        "Біз сізге тез хабарласуымыз үшін сұрақтарға жауап беріңіз.\n\n"
        "Өтінішті кез келген уақытта <b>/cancel</b> деп тоқтата аласыз.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )
    await update.message.reply_text("<b>1/10.</b> Атыңызды жазыңыз (тек қазақ/орыс әріптері):", parse_mode="HTML")
    return FORM_NAME

async def form_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("<b>2/10.</b> Тегіңізді жазыңыз:", parse_mode="HTML")
    return FORM_SURNAME

async def form_surname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["surname"] = update.message.text.strip()
    await update.message.reply_text("<b>3/10.</b> Туған жылыңызды 4 санмен енгізіңіз (мысалы: 2009):", parse_mode="HTML")
    return FORM_BIRTHYEAR

async def form_birthyear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit() or len(text) != 4 or int(text) < 1950 or int(text) > datetime.date.today().year:
        await update.message.reply_text("Қате формат. Жылды тек 4 санмен енгізіңіз (мысалы: 2009):")
        return FORM_BIRTHYEAR
    context.user_data["birthyear"] = text
    await update.message.reply_text("<b>4/10.</b> Қай қала/ауданнансыз?", parse_mode="HTML")
    return FORM_CITY

async def form_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["city"] = update.message.text.strip()
    await update.message.reply_text("<b>5/10.</b> Біз туралы қайдан естідіңіз (мысалы: Instagram, достар)?", parse_mode="HTML")
    return FORM_SOURCE

async def form_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["source"] = update.message.text.strip()
    keyboard = ReplyKeyboardMarkup([["Үйленгенмін", "Үйленбегенмін"]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("<b>6/10.</b> Отбасы жағдайыңыз?", reply_markup=keyboard, parse_mode="HTML")
    return FORM_FAMILY_STATUS

async def form_family_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["family_status"] = update.message.text
    keyboard = ReplyKeyboardMarkup([["Иә, 9 немесе 11 сынып аттестаты бар"], ["Жоқ, аттестат жоқ"]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("<b>7/10.</b> Сізде 9 немесе 11 сыныптың <b>аттестаты</b> бар ма?", reply_markup=keyboard, parse_mode="HTML")
    return FORM_HAS_ATTESTAT

async def form_has_attestat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["has_attestat"] = update.message.text
    await update.message.reply_text("<b>8/10.</b> Қай мамандық бойынша оқығыңыз келеді? (толық атауын жазыңыз)\n\nМамандықтар:\n1303000 – Теміржол көлігіндегі автоматика, телемеханика және қозғалысты басқару.\n1203000 – Теміржол көлігіндегі тасымалдауды ұйымдастыру және қозғалысты басқару\n1306000 – Радиоэлектроника және байланыс (түрлері бойынша)\n1409000 – Теміржолдар салу, жол және жол шаруашылығы\n1108000 – Теміржолдардың жылжымалы құрамын пайдалану, жөндеу және техникалық қызмет көрсету (түрлері бойынша)\n0904000 – Теміржолдардың электр техникалық жүйелерін электрмен жабдықтау, пайдалану, техникалық қызмет көрсету және жөндеу", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    return FORM_SPECIALTY

async def form_specialty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["specialty"] = update.message.text.strip()
    await update.message.reply_text("<b>9/10.</b> Неге біздің колледжді таңдадыңыз?", parse_mode="HTML")
    return FORM_WHY_JOIN

async def form_why_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["why_join"] = update.message.text.strip()
    await update.message.reply_text("<b>10/10.</b> Байланыс телефоныңызды енгізіңіз (мысалы: +7 (771) - 777- 77 - 77):", parse_mode="HTML")
    return FORM_PHONE

async def form_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text.strip()

    data = context.user_data
    text = (
        "✅ <b>Өтініштің алдын ала қарау:</b>\n\n"
        f"1. Аты-жөні: {data['name']} {data['surname']}\n"
        f"2. Туған жылы: {data['birthyear']}\n"
        f"3. Қала: {data['city']}\n"
        f"4. Қайдан естіді: {data['source']}\n"
        f"5. Отбасы: {data['family_status']}\n"
        f"6. Аттестат: {data['has_attestat']}\n"
        f"7. Мамандық: {data['specialty']}\n"
        f"8. Себебі: {data['why_join']}\n"
        f"9. 📞 Телефон: {data['phone']}\n\n"
        "Барлығы дұрыс па? Жіберуді растаңыз."
    )
    keyboard = ReplyKeyboardMarkup([["Иә, жіберу", "Жоқ, қайта толтыру"]], resize_keyboard=True)
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
    return FORM_CONFIRM

async def form_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "Иә" not in update.message.text and "жіберу" not in update.message.text.lower():
        await update.message.reply_text("Өтініш жойылды.", reply_markup=main_keyboard())
        context.user_data.clear()
        return MAIN_MENU

    sheet = get_google_sheet()
    if not sheet:
        await update.message.reply_text("Google Sheets қолжетімсіз. Операторға хабарласыңыз.")
        return MAIN_MENU

    data = context.user_data
    row = [
        datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
        f"{data['name']} {data['surname']}", data['birthyear'], data['city'], data['source'],
        data['family_status'], data['has_attestat'], data['specialty'],
        data['why_join'], data['phone'],
        update.effective_user.id, update.effective_user.username or "-"
    ]
    try:
        sheet.append_row(row)
        await update.message.reply_text("🎉 Өтінішіңіз сәтті қабылданды! Жақын арада хабарласамыз.\nРақмет!", reply_markup=main_keyboard())
    except Exception as e:
        await update.message.reply_text("Техникалық қате. Өтініш сақталмады. Қолмен жіберу үшін /start.")

    context.user_data.clear()
    return MAIN_MENU

async def school_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "Мектеп оқушылары үшін":
        return MAIN_MENU
    await update.message.reply_text(
        "Мектеп оқушыларына арналған бөлім\n\nСіз колледжге түсу туралы ақпарат ала аласыз немесе өтініш қалдыра аласыз.",
        reply_markup=school_menu_keyboard()
    )
    return SCHOOL_MENU

async def school_start_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Артқа":
        await update.message.reply_text("Басты мәзірге оралдыңыз.", reply_markup=main_keyboard())
        return MAIN_MENU

    if update.message.text != "Өтініш қалдыру":
        return SCHOOL_MENU

    if is_dialog_active(update.effective_user.id):
        await update.message.reply_text("Белсенді диалог бар. /stop_dialog арқылы жабыңыз.")
        return SCHOOL_MENU

    if has_school_application(update.effective_user.id):
        await update.message.reply_text(
            "Сіз бұл бөлімде өтінішті бір рет қана қалдыра аласыз.\nБіз сізбен міндетті түрде хабарласамыз!",
            reply_markup=main_keyboard()
        )
        return MAIN_MENU

    await update.message.reply_text(
        "Мектеп оқушысы ретінде өтініш қалдыру\n\nАты-жөніңізді жазыңыз:\n\nМысалы : Жалгас Нурхан Нуркенович.",
        reply_markup=ReplyKeyboardRemove()
    )
    return SCHOOL_FORM_NAME

async def school_form_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["school_name"] = update.message.text.strip()
    await update.message.reply_text("Мектебіңіздің толық атауын жазыңыз:")
    return SCHOOL_FORM_SCHOOL

async def school_form_school(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["school_school"] = update.message.text.strip()
    await update.message.reply_text("Қай сыныпта оқисыз? (мысалы: 9 «А»):")
    return SCHOOL_FORM_CLASS

async def school_form_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["school_class"] = update.message.text.strip()
    await update.message.reply_text("Байланыс нөміріңіз (мысалы: +7 (771) - 777- 77 - 77):")
    return SCHOOL_FORM_PHONE

async def school_form_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["school_phone"] = update.message.text.strip()
    await update.message.reply_text("Әлеуметтік желідегі парақшаңыз (Instagram, TikTok сілтемесі):")
    return SCHOOL_FORM_SOCIAL

async def school_form_social(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["school_social"] = update.message.text.strip()
    data = context.user_data
    text = (
        "<b>Өтінішті тексеріңіз:</b>\n\n"
        f"Аты-жөні: {data['school_name']}\n"
        f"Мектебі: {data['school_school']}\n"
        f"Сыныбы: {data['school_class']}\n"
        f"Телефон: {data['school_phone']}\n"
        f"Әлеуметтік желі: {data['school_social']}\n\n"
        "Барлығы дұрыс па?"
    )
    keyboard = ReplyKeyboardMarkup([["Иә, жіберу", "Жоқ, қайта толтыру"]], resize_keyboard=True)
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
    return SCHOOL_FORM_CONFIRM

async def school_form_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "Иә" not in update.message.text and "жіберу" not in update.message.text.lower():
        await update.message.reply_text("Өтініш жойылды.", reply_markup=main_keyboard())
        context.user_data.clear()
        return MAIN_MENU

    sheet = get_school_sheet()
    if not sheet:
        await update.message.reply_text("Техникалық қате. Өтініш сақталмады.")
        return MAIN_MENU

    data = context.user_data
    row = [
        datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
        data["school_name"],
        data["school_school"],
        data["school_class"],
        data["school_phone"],
        data["school_social"],
        update.effective_user.id,
        update.effective_user.username or "-"
    ]
    try:
        sheet.append_row(row)
        await update.message.reply_text(
            "Өтінішіңіз сәтті қабылданды!\nБіз сізбен жақын арада хабарласамыз.\nРақмет!",
            reply_markup=main_keyboard()
        )
    except Exception as e:
        await update.message.reply_text("Қате. Өтініш сақталмады.")

    context.user_data.clear()
    return MAIN_MENU

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text("Қате пайда болды. Кейін қайталаңыз.")
        except:
            pass

def main():
    app = Application.builder().token(API_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                MessageHandler(filters.Text(["Жылдам жауаптар"]), faq_categories),
                MessageHandler(filters.Text(["Оператормен байланысу"]), start_support),
                MessageHandler(filters.Text(["Өтініш қалдыру"]), start_form),
                MessageHandler(filters.Text(["Мектеп оқушылары үшін"]), school_menu),
            ],
            SCHOOL_MENU: [
                MessageHandler(filters.Text(["Өтініш қалдыру"]), school_start_form),
                MessageHandler(filters.Text(["Артқа"]), start),
            ],
            SCHOOL_FORM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, school_form_name)],
            SCHOOL_FORM_SCHOOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, school_form_school)],
            SCHOOL_FORM_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, school_form_class)],
            SCHOOL_FORM_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, school_form_phone)],
            SCHOOL_FORM_SOCIAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, school_form_social)],
            SCHOOL_FORM_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, school_form_confirm)],
            FAQ_CATEGORIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, faq_questions)],
            FAQ_QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, faq_answer)],
            FAQ_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, back_from_answer)],
            SUPPORT_WAITING: [
                MessageHandler(filters.Text(["Жылдам жауаптар", "Өтініш қалдыру"]), handle_main_menu_in_support),
                MessageHandler(filters.TEXT & ~filters.COMMAND, forward_to_support)
            ],
            FORM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_name)],
            FORM_SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_surname)],
            FORM_BIRTHYEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_birthyear)],
            FORM_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_city)],
            FORM_SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_source)],
            FORM_FAMILY_STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_family_status)],
            FORM_HAS_ATTESTAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_has_attestat)],
            FORM_SPECIALTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_specialty)],
            FORM_WHY_JOIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_why_join)],
            FORM_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_phone)],
            FORM_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_confirm)],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("cancel", cancel_form),
            CommandHandler("stop_dialog", stop_dialog),
        ],
        per_user=True
    )

    app.add_handler(conv)

    app.add_handler(MessageHandler(
        filters.Chat(FORUM_CHAT_ID) & ~filters.COMMAND & filters.UpdateType.MESSAGE,
        handle_operator_reply
    ))

    app.add_handler(CommandHandler("stop_dialog", stop_dialog, filters=filters.Chat(FORUM_CHAT_ID)))

    app.add_error_handler(error_handler)
    logger.info("Бот іске қосылды...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
