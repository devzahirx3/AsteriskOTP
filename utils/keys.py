import secrets
import string
from database.database import fetch_key, update_key, fetch_user, update_user
from datetime import datetime, timedelta
import os

admin_group = os.getenv('ADMIN_GROUP_ID')

# GEN KEY
def generate_key():
    characters = string.ascii_letters + string.digits
    key = "MasterOTP-"
    for _ in range(4):
        segment = ''.join(secrets.choice(characters) for _ in range(4))
        key += segment.upper() + '-'
    key = key[:-1]
    return key

# ADD KEY
async def process_key(telegram_user_id, username, key_value):
    key_document = await fetch_key(key_value)
    
    # Default return values
    original_key_status = "bad"
    validity_period = 0
    key_seller = None

    if key_document is not None:
        original_key_status = key_document.get("status", "Status field not found")

        if original_key_status == "active":
            await update_key(key_value, status="redeemed", validity_period=None)

            # Fetch or create the user
            user_document = await fetch_user(telegram_user_id, username)

            # Calculate the new end_date based on validity
            validity_period = key_document.get("validity_period", 0)
            key_seller = key_document.get("referrer", None)
            current_end_date = user_document.get("subscription", {}).get("end_date", datetime.now())
            
            if current_end_date == "N/A":
                current_end_date = datetime.now()
            else:
                current_end_date = datetime.strptime(current_end_date, "%Y-%m-%d")

            # Check if current_end_date is in the past
            if current_end_date < datetime.now():
                current_end_date = datetime.now()

            new_end_date = current_end_date + timedelta(days=validity_period)
            new_end_date_str = new_end_date.strftime("%Y-%m-%d")

            # Update the user to "paid", extend end_date, and add key_id
            await update_user(
                telegram_user_id, 
                status="paid", 
                start_date=None, 
                end_date=new_end_date_str, 
                key_id=key_value
            )

    return original_key_status, validity_period, key_seller




