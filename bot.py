import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================== تنظیمات ==================
TOKEN = "8316972674:AAEBoRd9E9REhEbNB9cyfMN8hzvP_9j92Io"
ADMIN_ID = 513162757  # ← اینجا آیدی تلگرام خودتو بزار

TOTAL_QUESTIONS = 5

# ================== دیتابیس ==================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

# جدول کاربران
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    score INTEGER
)
""")

# جدول لغات
cursor.execute("""
CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    english TEXT,
    persian TEXT
)
""")

conn.commit()

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n"
        "به ربات تمرین لغت خوش اومدی!\n\n"
        "/quiz شروع آزمون\n"
        "/leaderboard جدول رتبه‌بندی"
    )

# ================== افزودن لغت (ادمین) ==================
async def addword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ فقط ادمین اجازه داره!")
        return

    if not context.args:
        await update.message.reply_text(
            "فرمت درست:\n/addword english=persian"
        )
        return

    try:
        data = context.args[0]
        english, persian = data.split("=")

        cursor.execute(
            "INSERT INTO words (english, persian) VALUES (?, ?)",
            (english.strip(), persian.strip())
        )
        conn.commit()

        await update.message.reply_text("✅ لغت با موفقیت اضافه شد!")

    except:
        await update.message.reply_text(
            "❌ فرمت اشتباهه!\nمثال:\n/addword computer=کامپیوتر"
        )

# ================== QUIZ ==================
async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["score"] = 0
    context.user_data["question_count"] = 0
    context.user_data["used_words"] = []

    await send_question(update, context)

# ================== ارسال سوال ==================
async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if context.user_data["question_count"] >= TOTAL_QUESTIONS:
        user_id = update.effective_user.id
        name = update.effective_user.first_name
        score = context.user_data["score"]

        cursor.execute(
            "SELECT score FROM users WHERE user_id = ?",
            (user_id,)
        )
        result = cursor.fetchone()

        if result:
            old_score = result[0]

            if score > old_score:
                cursor.execute(
                    "UPDATE users SET score = ?, name = ? WHERE user_id = ?",
                    (score, name, user_id)
                )
                conn.commit()
                await update.effective_message.reply_text(
                    f"🎉 رکورد جدیدت ثبت شد!\nامتیاز: {score}"
                )
            else:
                await update.effective_message.reply_text(
                    f"امتیازت: {score}\n\n🏆 بهترین رکوردت هنوز {old_score} هست!"
                )
        else:
            cursor.execute(
                "INSERT INTO users (user_id, name, score) VALUES (?, ?, ?)",
                (user_id, name, score)
            )
            conn.commit()
            await update.effective_message.reply_text(
                f"🎉 اولین رکوردت ثبت شد!\nامتیاز: {score}"
            )

        return

    cursor.execute("SELECT english, persian FROM words")
    all_words = cursor.fetchall()

    if len(all_words) < 4:
        await update.effective_message.reply_text(
            "❗ حداقل ۴ لغت در دیتابیس لازم است.\n"
            "ادمین باید با /addword لغت اضافه کند."
        )
        return

    unused_words = [
        w for w in all_words
        if w[0] not in context.user_data["used_words"]
    ]

    word_pair = random.choice(unused_words)
    word = word_pair[0]
    correct_answer = word_pair[1]

    context.user_data["used_words"].append(word)

    wrong_answers = random.sample(
        [w[1] for w in all_words if w[0] != word],
        3
    )

    options = wrong_answers + [correct_answer]
    random.shuffle(options)

    keyboard = [
        [InlineKeyboardButton(opt, callback_data=opt)]
        for opt in options
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data["correct_answer"] = correct_answer
    context.user_data["question_count"] += 1

    await update.effective_message.reply_text(
        f"معنی کلمه '{word}' چیست؟",
        reply_markup=reply_markup
    )

# ================== دکمه‌ها ==================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected = query.data
    correct = context.user_data["correct_answer"]

    if selected == correct:
        context.user_data["score"] += 1
        await query.edit_message_text("✅ درست بود!")
    else:
        await query.edit_message_text(f"❌ اشتباه بود!\nجواب درست: {correct}")

    await send_question(update, context)

# ================== لیدربورد ==================
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute(
        "SELECT name, score FROM users ORDER BY score DESC LIMIT 5"
    )
    top_users = cursor.fetchall()

    if not top_users:
        await update.message.reply_text("هنوز کسی آزمون نداده 😄")
        return

    text = "🏆 جدول رتبه‌بندی:\n\n"

    for i, (name, score) in enumerate(top_users, start=1):
        text += f"{i}. {name} — {score} امتیاز\n"

    await update.message.reply_text(text)

# ================== اجرا ==================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("quiz", quiz))
app.add_handler(CommandHandler("leaderboard", leaderboard))
app.add_handler(CommandHandler("addword", addword))
app.add_handler(CallbackQueryHandler(button))

print("ربات در حال اجراست...")
app.run_polling()
