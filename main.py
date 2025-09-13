import os
import json
import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from flask import Flask, request, render_template, jsonify, send_from_directory
from threading import Thread

# ==================== CONFIGURATION (Aapki Info Add Kar Di Gayi Hai) ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8258019586:AAFbBhyw12cTMMeddK3MUz8-N9y6uGXNnVk") 
ADMIN_ID = int(os.environ.get('ADMIN_ID', 6296600925))
BOT_USERNAME = os.environ.get('BOT_USERNAME', "OnlyEducationvideos_bot") # Yahan apne bot ka username daalein (bina @ ke)

# Reward aur Withdrawal ki settings
AD_REWARD = 0.0002
MIN_WITHDRAWAL = 5.0

# Extra Earning Link
EXTRA_EARNING_URL = "https://t.me/EagleEyeSignals_bot/AdCash"

# Yeh URL Railway deploy hone ke baad khud set karega
RAILWAY_URL = os.environ.get('RAILWAY_STATIC_URL')

# ==================== INITIALIZATION ====================
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ==================== DATA MANAGEMENT ====================
def load_users():
    try:
        with open('users.json', 'r') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_users(users_data):
    with open('users.json', 'w') as f: json.dump(users_data, f, indent=4)

def get_user_data(user_id):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {
            "balance": 0.0,
            "binance_uid": None,
            "referrals": 0,
            "referred_by": None
        }
        save_users(users)
    return users[user_id_str]

def update_user_data(user_id, data):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str not in users:
        # Agar user mojood nahin hai, toh pehle usko banayein
        get_user_data(user_id)
        users = load_users() # users ko dobara load karein
    users[user_id_str].update(data)
    save_users(users)

# ==================== KEYBOARD MENUS ====================
def main_menu(user_id):
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    # Ad Viewer Mini App ka URL, jismein user ki ID bhi hogi
    ad_viewer_url = f"https://{RAILWAY_URL}/ad_viewer?user_id={user_id}" if RAILWAY_URL else f"http://127.0.0.1:5000/ad_viewer?user_id={user_id}"
    
    # Ad Buttons
    btn1 = InlineKeyboardButton("Claim AdCash 1", web_app=WebAppInfo(url=ad_viewer_url))
    btn2 = InlineKeyboardButton("Claim AdCash 2", web_app=WebAppInfo(url=ad_viewer_url))
    btn3 = InlineKeyboardButton("Claim AdCash 3", web_app=WebAppInfo(url=ad_viewer_url))
    btn4 = InlineKeyboardButton("Claim AdCash 4", web_app=WebAppInfo(url=ad_viewer_url))
    keyboard.add(btn1, btn2, btn3, btn4)

    # Doosre Buttons
    keyboard.row(
        InlineKeyboardButton("💰 Balance", callback_data="check_balance"),
        InlineKeyboardButton("💵 Withdrawal", callback_data="withdrawal")
    )
    keyboard.row(
        InlineKeyboardButton("📤 Share & Earn", callback_data="referral"),
        InlineKeyboardButton("⚙️ Settings", callback_data="settings")
    )
    keyboard.row(
        InlineKeyboardButton("🤑 Extra Earning", web_app=WebAppInfo(url=EXTRA_EARNING_URL))
    )
    return keyboard

def settings_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("📝 Set/Update Binance UID", callback_data="set_binance"))
    keyboard.row(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu"))
    return keyboard

# ==================== TELEGRAM BOT HANDLERS ====================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    get_user_data(user_id) # User ko register karein
    
    # Referral System
    try:
        ref_id = int(message.text.split()[1])
        if ref_id != user_id:
            user_data = get_user_data(user_id)
            if user_data.get("referred_by") is None:
                update_user_data(user_id, {"referred_by": ref_id})
                
                referrer_data = get_user_data(ref_id)
                referrer_data["referrals"] = referrer_data.get("referrals", 0) + 1
                update_user_data(ref_id, referrer_data)
                bot.send_message(ref_id, "🎉 A new user has joined using your referral link!")
    except (IndexError, ValueError):
        pass # Koi referral nahin hai

    welcome_text = "👋 Welcome! Claim rewards by clicking the buttons below."
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(user_id))

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    user = get_user_data(user_id)
    
    if call.data == "main_menu":
        bot.edit_message_text("Main Menu:", call.message.chat.id, call.message.message_id, reply_markup=main_menu(user_id))

    elif call.data == "check_balance":
        bot.answer_callback_query(call.id, f"Your Balance: {user['balance']:.4f} USDT", show_alert=True)

    elif call.data == "settings":
        uid_status = user.get("binance_uid", "Not Set")
        bot.edit_message_text(f"⚙️ Settings\n\nYour current Binance UID: <b>{uid_status}</b>", call.message.chat.id, call.message.message_id, reply_markup=settings_menu(), parse_mode="HTML")

    elif call.data == "set_binance":
        msg = bot.send_message(call.message.chat.id, "Please send your Binance UID (Pay ID).")
        bot.register_next_step_handler(msg, process_binance_uid)

    elif call.data == "withdrawal":
        if user['balance'] < MIN_WITHDRAWAL:
            bot.answer_callback_query(call.id, f"❌ Minimum withdrawal is {MIN_WITHDRAWAL} USDT.", show_alert=True)
        elif not user.get('binance_uid'):
            bot.answer_callback_query(call.id, "❌ Please set your Binance UID in Settings first.", show_alert=True)
        else:
            request_msg = f"💸 WITHDRAWAL REQUEST\nUser ID: {user_id}\nUsername: @{call.from_user.username}\nAmount: {user['balance']:.4f} USDT\nBinance UID: {user['binance_uid']}"
            bot.send_message(ADMIN_ID, request_msg)
            bot.answer_callback_query(call.id, "✅ Withdrawal request sent! It will be processed soon.", show_alert=True)

    elif call.data == "referral":
        ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        ref_count = user.get("referrals", 0)
        ref_text = f"📤 Share this link with your friends!\n\nYou have invited <b>{ref_count}</b> users.\n\n🔗 Your referral link:\n<code>{ref_link}</code>"
        bot.edit_message_text(ref_text, call.message.chat.id, call.message.message_id, reply_markup=main_menu(user_id), parse_mode="HTML")

def process_binance_uid(message):
    user_id = message.from_user.id
    uid = message.text.strip()
    if uid.isdigit():
        update_user_data(user_id, {'binance_uid': uid})
        bot.send_message(message.chat.id, f"✅ Your Binance UID has been updated to: {uid}", reply_markup=main_menu(user_id))
    else:
        bot.send_message(message.chat.id, "❌ Invalid UID. Please send numbers only.", reply_markup=main_menu(user_id))

# ==================== FLASK WEB SERVER & API ====================
@app.route('/ad_viewer')
def ad_viewer():
    user_id = request.args.get('user_id')
    return render_template('ad_viewer.html', user_id=user_id)

@app.route('/api/claim-reward', methods=['POST'])
def claim_reward():
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'User ID is missing'}), 400
    
    try:
        user = get_user_data(user_id)
        new_balance = user.get('balance', 0.0) + AD_REWARD
        update_user_data(user_id, {'balance': new_balance})
        return jsonify({'status': 'success', 'new_balance': new_balance})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== MAIN EXECUTION ====================
def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    print("Bot is starting...")
    # Zaroori folders banayein agar mojood nahin hain
    if not os.path.exists('templates'):
        os.makedirs('templates')
        
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    
    print("Bot polling started...")
    bot.polling(none_stop=True)
