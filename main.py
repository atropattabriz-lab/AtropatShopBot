import logging
import pandas as pd
import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# -----------------------------
# تنظیمات اصلی
# -----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
ADMIN_USERNAME = "@Dadgar1987"
STORE_NAME = "فروشگاه لوازم خانگی آتروپات"
PAYMENT_LINK = "https://zarinp.al/atropatshop.ir"
PHONE_NUMBER = "09305069257"

# -----------------------------
# بارگذاری فایل محصولات
# -----------------------------
PRODUCT_FILE = "data/products.xlsx"

def load_products():
    if not os.path.exists(PRODUCT_FILE):
        return pd.DataFrame()
        df = pd.read_excel(PRODUCT_FILE, engine="openpyxl")
        
    df = df.rename(columns={
        "product_id": "id",
        "product_name": "title",
        "price": "price",
        "image_url": "image_url",
        "product_url": "url",
        "inventory": "inventory",
    })
    return df

PRODUCTS = load_products()

# -----------------------------
# شروع
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"به {STORE_NAME} خوش آمدید.\n"
        f"در خدمت شما هستیم.\n\n"
        f"برای جستجوی محصول کافیست نام آن را ارسال کنید."
    )
    await update.message.reply_text(text)

# -----------------------------
# هندل پیام‌های متنی
# -----------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()

    # جستجو در محصولات
    results = PRODUCTS[PRODUCTS["title"].str.contains(user_text, case=False, na=False)]

    if results.empty:
        await update.message.reply_text("محصولی یافت نشد. لطفاً نام دقیق‌تری وارد کنید.")
        return

    for _, row in results.iterrows():
        title = row["title"]
        price = row["price"]
        image = row.get("image_url", None)

        keyboard = [
            [InlineKeyboardButton("🛒 خرید", callback_data=f"buy_{row['id']}")],
            [InlineKeyboardButton("📞 تماس با پشتیبانی", url=f"tel:{PHONE_NUMBER}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if image and str(image).startswith("http"):
            try:
                await update.message.reply_photo(photo=image, caption=f"{title}\nقیمت: {price:,} تومان", reply_markup=reply_markup)
            except:
                await update.message.reply_text(f"{title}\nقیمت: {price:,} تومان", reply_markup=reply_markup)
        else:
            await update.message.reply_text(f"{title}\nقیمت: {price:,} تومان", reply_markup=reply_markup)

# -----------------------------
# خرید محصول
# -----------------------------
async def buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_id = query.data.split("_")[1]
    product = PRODUCTS[PRODUCTS["id"] == int(product_id)].iloc[0]

    title = product["title"]
    price = product["price"]

    keyboard = [
        [InlineKeyboardButton("پرداخت امن زرین‌پال", url=PAYMENT_LINK)],
        [InlineKeyboardButton("ارسال شماره برای ثبت سفارش", callback_data=f"sendphone_{product_id}")]
    ]

    await query.edit_message_text(
        f"محصول انتخابی:\n{title}\nقیمت: {price:,} تومان\n\n"
        f"لطفاً یک گزینه انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# -----------------------------
# درخواست شماره مشتری
# -----------------------------
async def request_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_id = query.data.split("_")[1]
    context.user_data["waiting_phone"] = product_id

    await query.edit_message_text("لطفاً شماره تلفن خود را ارسال نمایید:")

async def save_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "waiting_phone" not in context.user_data:
        return

    phone = update.message.text
    product_id = context.user_data.pop("waiting_phone", None)

    product = PRODUCTS[PRODUCTS["id"] == int(product_id)].iloc[0]

    title = product["title"]
    price = product["price"]

    # ارسال سفارش برای ادمین
    admin_text = (
        "📌 سفارش جدید دریافت شد:\n\n"
        f"مشتری: {update.message.from_user.full_name}\n"
        f"شماره تماس: {phone}\n"
        f"محصول: {title}\n"
        f"قیمت: {price:,} تومان\n"
    )

    await update.message.bot.send_message(chat_id=ADMIN_USERNAME, text=admin_text)

    await update.message.reply_text(
        "شماره تماس شما دریافت شد.\n"
        "کارشناسان ما در اسرع وقت با شما تماس خواهند گرفت."
    )

# -----------------------------
# اجرای ربات
# -----------------------------
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(buy_product, pattern="^buy_"))
    application.add_handler(CallbackQueryHandler(request_phone, pattern="^sendphone_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_phone))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == "__main__":
    main()
  
