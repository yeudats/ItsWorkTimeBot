import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask, request, Response

load_dotenv()
TOKEN = os.environ["TELEGRAM_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 8080))

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("TELEGRAM_TOKEN או WEBHOOK_URL לא מוגדרים ב-env!")

google_creds = os.environ["GOOGLE_CREDENTIALS"]
if google_creds:
    creds_obj = json.loads(google_creds)
    with open("credentials.json", "w", encoding="utf-8") as f:
        json.dump(creds_obj, f)

enter_datetime = ''
exit_datetime = ''

def get_month_sheet(client, month_name="גליון בסיס"):
    workbook = client.open("יהודה צבע שעות עבודה")
    try:
        sheet = workbook.worksheet(month_name)
        return sheet
    except gspread.exceptions.WorksheetNotFound:
        base_sheet = workbook.worksheet("גליון בסיס")
        new_sheet = base_sheet.duplicate(new_sheet_name=month_name)
        return new_sheet

def get_sheet(month_name):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)
    return client, get_month_sheet(client, month_name)

def entrance_button():
    keyboard = [[InlineKeyboardButton("כניסה לעבודה", callback_data="enter")]]
    return InlineKeyboardMarkup(keyboard)

def exit_button():
    keyboard = [[InlineKeyboardButton("יציאה מהעבודה", callback_data="exit")]]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("לחץ לרישום כניסה", reply_markup=entrance_button())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global enter_datetime, exit_datetime
    query = update.callback_query
    await query.answer()

    if query.data == "enter":
        enter_datetime = datetime.now(ZoneInfo("Asia/Jerusalem"))
        client, sheet = get_sheet(enter_datetime.strftime("%m-%Y"))
        rows = sheet.get_all_values()
        new_row_index = len(rows) + 1
        sheet.update_cell(new_row_index, 1, enter_datetime.strftime('%d.%m.%Y'))
        sheet.update_cell(new_row_index, 2, enter_datetime.strftime('%H:%M'))
        await query.edit_message_text(
            f"בוצעה כניסה בשעה {enter_datetime.strftime('%H:%M')}",
            reply_markup=exit_button()
        )
    elif query.data == "exit":
        if not enter_datetime:
            await query.edit_message_text("שגיאה: אין כניסה רשומה")
            return
        exit_datetime = datetime.now(ZoneInfo("Asia/Jerusalem"))
        client, sheet = get_sheet(enter_datetime.strftime("%m-%Y"))
        total_delta = exit_datetime - enter_datetime
        total_minutes = int(total_delta.total_seconds() // 60)
        decimal_hours = round(total_minutes / 60, 2)
        rows = sheet.get_all_values()
        sheet.update_cell(len(rows), 3, exit_datetime.strftime("%H:%M"))
        sheet.update_cell(len(rows), 4, decimal_hours)
        await query.edit_message_text(
            f'בוצעה כניסה בשעה {enter_datetime.strftime("%H:%M")}'
            f'\nבוצעה יציאה בשעה {exit_datetime.strftime("%H:%M")}'
            f'\nסה"כ שעות עבודה: {decimal_hours}',
            reply_markup=entrance_button()
        )
        enter_datetime = ''
        exit_datetime = ''


# ---- Flask app ----
flask_app = Flask(__name__)
telegram_app = ApplicationBuilder().token(TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(button_handler))

@flask_app.route("/", methods=["GET"])
def keepalive():
    return "Bot is running!", 200

@flask_app.route(f"/", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    telegram_app.update_queue.put(update)
    return Response("ok", status=200)

def main():
    # קבע Webhook
    telegram_app.bot.set_webhook(WEBHOOK_URL)
    # הרץ Flask על אותו פורט
    flask_app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
