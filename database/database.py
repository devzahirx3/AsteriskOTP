
# BASIC
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from uuid import uuid4
from dotenv import load_dotenv
from bson.objectid import ObjectId
import asyncio
import os
import traceback

# ENV
load_dotenv()
mongo_url = os.getenv('MONGO_URL')
db_name = os.getenv('DB_NAME')

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
    if 'sip_trunks' not in collections:
        await db.create_collection('sip_trunks')
        print("SIP trunks collection created.")
    else:
        print("SIP trunks collection already exists.")
    

loop = asyncio.get_event_loop()
loop.run_until_complete(init_db())

users_collection = db['users']
keys_collection = db['keys']
custom_string_collection = db['custom_strings']
sip_trunks_collection = db['sip_trunks']

# USERS
# Create User
async def create_user(telegram_id, username, referrer=None):
    users_collection = db['users']

    # Construct the user_data dictionary using the passed variables
    user_data = {
        "_id": telegram_id,
        "username": username,
        "subscription": {
            "status": "free",
            "start_date": "N/A",
            "end_date": "N/A",
            "key_id": None
        },
        "referrer": referrer
    }

    result = await users_collection.insert_one(user_data)
    return result.inserted_id

# Update user by ID
async def update_user(telegram_user_id, status=None, start_date=None, end_date=None, key_id=None):
    update_data_user = {}

    if status is not None:
        update_data_user["subscription.status"] = status
    if start_date is not None:
        update_data_user["subscription.start_date"] = start_date
    if end_date is not None:
        update_data_user["subscription.end_date"] = end_date
    if key_id is not None:
        update_data_user["subscription.key_id"] = key_id

    users_collection = db['users']
    if update_data_user:
        result = await users_collection.update_one({"_id": telegram_user_id}, {"$set": update_data_user})
        return result.modified_count > 0
    else:
        return False

# Fetch user by ID
async def fetch_user(telegram_user_id, username, referrer=None):
    users_collection = db['users']
    user_document = await users_collection.find_one({"_id": telegram_user_id})
    
    if user_document is None:
        # User not found, create a new one
        new_user_id = await create_user(telegram_user_id, username, referrer)
        
        # Fetch the newly created user document
        user_document = await users_collection.find_one({"_id": new_user_id})
        
    return user_document

# Delete User
async def delete_user(telegram_user_id):
    users_collection = db['users']
    result = await users_collection.delete_one({"_id": telegram_user_id})
    return result.deleted_count > 0

# Update user usage
async def update_user_usage(telegram_user_id, stat_type, additional_usage_count=None, additional_usage_times=None):
    update_data_usage = {}

    if additional_usage_count is not None:
        update_data_usage[f"statistics.{stat_type}.usage_count"] = {"$inc": additional_usage_count}

    if additional_usage_times is not None:
        update_data_usage[f"statistics.{stat_type}.usages"] = {"$push": {"$each": additional_usage_times}}

    users_collection = db['users']
    update_operations = {}
    if update_data_usage:
        for key, value in update_data_usage.items():
            update_operations["$set" if isinstance(value, dict) and "$inc" not in value else "$inc" if "$inc" in value else "$push"] = {key: value}
        
        result = await users_collection.update_one({"_id": telegram_user_id}, update_operations)
        return result.modified_count > 0
    else:
        return False

# Fetch user usage
async def fetch_user_usage(telegram_user_id, target_date: datetime):
    # Assuming that your MongoDB usage collection is named 'usages'
    usages_collection = db['usages']
    
    # Define the start and end of the day in UTC
    start_of_day = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
    end_of_day = start_of_day + timedelta(days=1)
    
    print(f"start time {start_of_day}")
    print(f"end time {end_of_day}")
    
    # Query for the number of usage documents for the user and day
    usage_count = await usages_collection.count_documents({
        'userid': str(telegram_user_id), 
        'start_time': {'$gte': start_of_day, '$lt': end_of_day}
    })
    
    return usage_count

# Check User subscription
async def check_subscription_status(telegram_user_id, username):
    # Fetch the user document
    user_document = await fetch_user(telegram_user_id, username)
    
    # Check the subscription status
    subscription_status = user_document.get('subscription', {}).get('status', 'free')
    end_date_str = user_document.get('subscription', {}).get('end_date', 'N/A')

    # If the status is 'paid', also check if the subscription has expired
    if subscription_status == 'paid' and end_date_str != 'N/A':
        # Convert the end_date string to a datetime object
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        today = datetime.now()

        # Check if the subscription has expired
        if end_date < today:
            # Update the user's status to 'free'
            await update_user(telegram_user_id, status='free')
            
            # Return False since the subscription has expired
            return False

    # Return True if the user has a paid subscription, False otherwise
    return subscription_status == 'paid'


# KEYS
# Create Key
async def create_key(key, validity_period, referrer=None):
    # Construct the key_data dictionary
    key_data = {
        "_id": ObjectId(),
        "key": key,
        "status": "active",  # active / redeemed
        "validity_period": validity_period,
        "referrer": referrer  # referrer field added
    }

    result = await keys_collection.insert_one(key_data)
    return result.inserted_id

# Update key by key value
async def update_key(key_value, status=None, validity_period=None):
    update_data = {}
    if status is not None:
        update_data["status"] = status
        if status == "redeemed":
            update_data["redeemed_timestamp"] = datetime.utcnow()
    if validity_period is not None:
        update_data["validity_period"] = validity_period

    if update_data:
        result = await keys_collection.update_one({"key": key_value}, {"$set": update_data})
        return result.modified_count > 0
    else:
        return False

# Fetch key by key value
async def fetch_key(key_value):
    key_document = await keys_collection.find_one({"key": key_value})
    return key_document

# Delete Key
async def delete_key(key_value):
    result = await keys_collection.delete_one({"key": key_value})
    return result.deleted_count > 0

# Fetch key referrer info
async def fetch_key_referrer(referrer):
    # 1. Total Keys
    total_keys = await keys_collection.count_documents({"referrer": referrer})

    # 2. % of keys that were used and 3. amount of keys that were used
    redeemed_keys_count = await keys_collection.count_documents({"referrer": referrer, "status": "redeemed"})
    if total_keys > 0:
        percentage_used = (redeemed_keys_count / total_keys) * 100
    else:
        percentage_used = 0

    # 4. Amount of keys that haven't been used
    unused_keys_count = total_keys - redeemed_keys_count

    # A list of how many keys were used per day for the last 14 days
    keys_used_per_day = []
    for i in range(14):
        day_start = datetime.utcnow() - timedelta(days=(14-i))
        day_end = day_start + timedelta(days=1)
        daily_redeemed_count = await keys_collection.count_documents({
            "referrer": referrer,
            "status": "redeemed",
            "redeemed_timestamp": {"$gte": day_start, "$lt": day_end}
        })
        keys_used_per_day.append(daily_redeemed_count)

    # Compile all the data into a single dictionary to return
    info = {
        "total_keys": total_keys,
        "percentage_used": percentage_used,
        "redeemed_keys_count": redeemed_keys_count,
        "unused_keys_count": unused_keys_count,
        "keys_used_per_day": keys_used_per_day
    }

    return info



# CUSTOM SCRIPT
# Create new script
async def add_custom_script(telegram_user_id, script_name, on_call_answer, grab_code, waiting_line, success_line, repeat_line, gender, language):
    script_id = str(uuid4())  # Generate a unique ID for the script
    script_data = {
        "script_id": script_id,
        "script_name": script_name,
        "on_call_answer": on_call_answer,
        "grab_code": grab_code,
        "waiting_line": waiting_line,
        "success_line": success_line,
        "repeat_line": repeat_line,
        "gender": gender,
        "language": language
    }
    result = await users_collection.update_one(
        {"_id": telegram_user_id},
        {"$push": {"custom_scripts": script_data}}
    )
    return result.modified_count > 0, script_id

# Fetch all user scripts
async def fetch_custom_scripts(telegram_user_id):
    user_document = await users_collection.find_one({"_id": telegram_user_id})
    custom_scripts = user_document.get("custom_scripts", [])
    script_names = [script['script_name'] for script in custom_scripts]
    return script_names

# Fetch single User Script
async def fetch_user_script(telegram_user_id, script_name):
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

# Delete single User Script
async def delete_custom_script(telegram_user_id, script_name):
    user_document = await users_collection.find_one({"_id": telegram_user_id})
    custom_scripts = user_document.get("custom_scripts", [])

    new_custom_scripts = [script for script in custom_scripts if script['script_name'] != script_name]

    if len(new_custom_scripts) == len(custom_scripts):
        return False  # No script was deleted

    result = await users_collection.update_one({"_id": telegram_user_id}, {"$set": {"custom_scripts": new_custom_scripts}})
    return result.modified_count > 0


# ROUTES
# Save user calldetails
async def save_calldetails(channel_id=None, chat_id=None, payload_string=None, otpdigits=None, call_details=None, call_variables=None, dtmf_status=None, dtmf_digits=None, current_playback_id=None, is_dial_ran=None):
    unique_id = float(channel_id)
    
    
    # Create dict
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
            updated_record = {k: details[k] if details[k] is not None else existing_record[k] for k in details}
            await custom_string_collection.replace_one({"_id": unique_id}, updated_record)
        else:
            # Insert the new record
            await custom_string_collection.insert_one(details)
        
        return unique_id

    except Exception as e:
        print("Error while inserting/updating MongoDB:", e)
    
# Fetch user calldetails
async def fetch_calldetails(channel_id=None, chat_id=None):
    details_document = None
    print(f"Channel IDDD: {channel_id}")
    
    try:
        details_document = await custom_string_collection.find_one({"_id": float(channel_id)})
    except ValueError:
        print(f"Error: {channel_id} cannot be converted to float!")
        traceback.print_exc()  # Print detailed traceback
        return None
    
    if not details_document:
        return None

    return details_document

# Delete user calldetails
async def delete_calldetails(chat_id):
    result = await custom_string_collection.delete_one({"_id": chat_id})
    
    return result.deleted_count > 0

# Delete all calldetails
async def delete_all_calldetails():
    result = await custom_string_collection.delete_many({})
    return result.deleted_count


# SIP TRUNKS
# Create/Update SIP Trunk
async def upsert_sip_trunk(trunk_number, status="active"):
    result = await sip_trunks_collection.update_one(
        {"_id": trunk_number},
        {"$set": {"status": status}},
        upsert=True
    )
    return result.matched_count > 0 or result.upserted_id is not None

# Check if SIP exists
async def check_sip_trunk_exists(trunk_number):
    count = await sip_trunks_collection.count_documents({"_id": trunk_number})
    return count > 0

# Fetch Sip Trunk
async def fetch_sip_trunk(trunk_number):
    trunk = await sip_trunks_collection.find_one({"_id": trunk_number})
    return trunk.get('status') if trunk else None


# LISTS
# List Users
async def list_users(filter=None, skip=0, limit=10):
    users_collection = db['users']
    users = await users_collection.find(filter).skip(skip).limit(limit).to_list(length=limit)
    return users

# List Keys
async def list_keys(filter=None, skip=0, limit=10):
    keys_collection = db['keys']
    keys = await keys_collection.find(filter).skip(skip).limit(limit).to_list(length=limit)
    return keys

# Count Users
async def count_users(filter=None):
    users_collection = db['users']
    count = await users_collection.count_documents(filter)
    return count

# Count Keys
async def count_keys(filter=None):
    keys_collection = db['keys']
    count = await keys_collection.count_documents(filter)
    return count