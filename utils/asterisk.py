from telegram.ext import ContextTypes
from telegram import Update
import httpx
import os
import re
import traceback
from dotenv import load_dotenv
import subprocess
import asyncio
import phonenumbers

from database.database import save_calldetails, upsert_sip_trunk, check_sip_trunk_exists, fetch_sip_trunk
load_dotenv()

# TG
admin_group = os.getenv('ADMIN_GROUP_ID')

# ARI
ari_username = os.getenv('ARI_USERNAME')
ari_password = os.getenv('ARI_PASSWORD')

class AsteriskManager:
    class NoMoreCredentials(Exception):
        """Raised when there are no more credentials to switch to."""
        pass

    PJSIP_CONFIG_PATH = "/etc/asterisk/pjsip.conf"

    def __init__(self, credentials):
        if not credentials:
            raise ValueError("Credentials list cannot be empty.")
        
        self.credentials = credentials
        self.current_index = 0
        self.set_current_values()

        # On initialization, update the pjsip config and reload
        self.update_pjsip_config_and_reload()

        # Save the SIP trunks to the database
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.save_sip_trunks_to_db())

    def set_current_values(self):
        """Set the current values based on the current index."""
        current_cred = self.credentials[self.current_index]
        self._sip_trunk_server_ip = current_cred['sip_trunk_server_ip']
        self._trunk_number = current_cred['trunk_number']
        self._trunk_password = current_cred['trunk_password']
        self._call_destination = current_cred['call_destination']
        self._max_outbound_calls = current_cred.get('max_outbound_calls', 1)

    def update_pjsip_config_and_reload(self):
        """Update the pjsip.conf file with all the credentials and reload."""
        config_content = """
; Define transport
[transport-udp]
type=transport
protocol=udp
bind=0.0.0.0
"""
        for cred in self.credentials:
            print(f"ADDING TRUNK {cred['trunk_number']}")
            trunk_config = f"""
; Endpoint for {cred['trunk_number']}
[{cred['trunk_number']}]
type=endpoint
context=outbound
disallow=all
allow=ulaw
aors={cred['trunk_number']}
auth={cred['trunk_number']}-auth
outbound_auth={cred['trunk_number']}-auth
from_domain={cred['sip_trunk_server_ip']}

; Authentication for {cred['trunk_number']}
[{cred['trunk_number']}-auth]
type=auth
auth_type=userpass
username={cred['trunk_number']}
password={cred['trunk_password']}

; AOR for {cred['trunk_number']}
[{cred['trunk_number']}]
type=aor
contact=sip:{cred['sip_trunk_server_ip']}

; Registration for {cred['trunk_number']}
[{cred['trunk_number']}-reg]
type=registration
outbound_auth={cred['trunk_number']}-auth
server_uri=sip:{cred['sip_trunk_server_ip']}
client_uri=sip:{cred['trunk_number']}@{cred['sip_trunk_server_ip']}
"""
            config_content += trunk_config
        
        with open(self.PJSIP_CONFIG_PATH, 'w') as f:
            f.write(config_content)
        
        self.reload_asterisk()


    def reload_asterisk(self):
        """Reload the pjsip module in Asterisk."""
        try:
            subprocess.run(["asterisk", "-rx", "module reload res_pjsip.so"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error reloading Asterisk: {e}")

    async def save_sip_trunks_to_db(self):
        """Save the SIP trunks to the database if they don't exist."""
        for cred in self.credentials:
            trunk_number = cred['trunk_number']
            if not await check_sip_trunk_exists(trunk_number):
                await upsert_sip_trunk(trunk_number)
                
    def get_current_values(self):
        """Retrieve the current SIP trunk server IP, trunk number, and trunk password."""
        return self._sip_trunk_server_ip, self._trunk_number, self._trunk_password, self._call_destination


credentials = [
    {
        "sip_trunk_server_ip": "gw1.sip.us",
        "trunk_number": "5244664336", #works
        "trunk_password": "x3vedfteyguwhpp4", 
        "call_destination": "US",
        "max_outbound_calls": 1,
    },
    {
        "sip_trunk_server_ip": "gw1.sip.us",
        "trunk_number": "5236388596", #works
        "trunk_password": "2p5gezxhhf4vdv5f", 
        "call_destination": "US",
        "max_outbound_calls": 1,
    },
    {
        "sip_trunk_server_ip": "gw1.sip.us",
        "trunk_number": "5279229429", #works
        "trunk_password": "cm2v8395z6xug4bp", 
        "call_destination": "US",
        "max_outbound_calls": 1,
    },
    {
        "sip_trunk_server_ip": "gw1.sip.us",
        "trunk_number": "5277896669", #works
        "trunk_password": "xe42v8mthqk32sdh", 
        "call_destination": "US",
        "max_outbound_calls": 1,
    },
    {
        "sip_trunk_server_ip": "gw1.sip.us",
        "trunk_number": "5238532668", #works
        "trunk_password": "nn7r6zwby97rn3gm", 
        "call_destination": "US",
        "max_outbound_calls": 1,
    },
    {
        "sip_trunk_server_ip": "gw1.sip.us",
        "trunk_number": "5252248672", #works
        "trunk_password": "9rnwx8h5rtkgs3uh", 
        "call_destination": "US",
        "max_outbound_calls": 1,
    },
    {
        "sip_trunk_server_ip": "gw1.sip.us",
        "trunk_number": "5276994674", #works
        "trunk_password": "u3zysrbtchqtav74", 
        "call_destination": "US",
        "max_outbound_calls": 1,
    },
]

manager = AsteriskManager(credentials)


class AllTrunksBanned(Exception):
    """Raised when all SIP trunks are banned."""
    pass

async def select_available_trunk(manager: AsteriskManager):
    # Fetch active trunks
    not_banned_trunks = []
    for cred in manager.credentials:
        trunk_number = cred['trunk_number']
        if await fetch_sip_trunk(trunk_number) != 'banned':
            not_banned_trunks.append(cred)

    # Error if all banned
    if not not_banned_trunks:
        raise AllTrunksBanned("All SIP trunks are banned.")

    # Find available trunk
    for cred in not_banned_trunks:
        active_calls = await get_active_calls_per_trunk(cred['trunk_number'])
        if active_calls < cred.get('max_outbound_calls', 1):
            return cred['trunk_number']

    # If none that fit
    return None

async def get_active_calls() -> list:
    """
    Fetches the active channels.
    :return: A list of active channels.
    """
    auth = httpx.BasicAuth(ari_username, ari_password)
    async with httpx.AsyncClient(auth=auth) as client:
        response = await client.get(f"http://localhost:8088/ari/channels")
        response.raise_for_status()
        channels = response.json()
        return channels

async def get_active_calls_per_trunk(trunk_number) -> int:
    """
    Determines how many active calls are being made with a specific trunk number.
    :param trunk_number: The trunk number to check.
    :return: The number of active calls for the trunk.
    """
    channels = await get_active_calls()
    # Filter the channels by the trunk_number
    active_calls = [channel for channel in channels if trunk_number in channel.get('name', '')]
    return len(active_calls)

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


async def create_call(update: Update, context: ContextTypes.DEFAULT_TYPE, call_details, queue_position):
    if hasattr(update, "callback_query") and update.callback_query:
        message = update.callback_query.message
    else:
        message = update.message
        
    try:
        if not re.match(r'^1[2-9]\d{2}[2-9]\d{2}\d{4}$', call_details['number']):
            await message.reply_text(f"❌ Please only call US & Canada numbers!")
            return True
        
        if call_details['spoof'] == "?":
            # Get Country Code
            parsed_number = phonenumbers.parse(f"+{call_details['number']}", "US")
            country_code = phonenumbers.region_code_for_number(parsed_number)
            
            # Generate number
            example_number = phonenumbers.example_number(country_code)
            spoof_number = phonenumbers.format_number(example_number, phonenumbers.PhoneNumberFormat.E164)
            
            call_details['spoof'] = spoof_number
        
        # CHECK HOW MANY CALLS
        try:
            available_trunk = await select_available_trunk(manager)
            print("AVAILABLE TRUNK")
            print(available_trunk)
            if not available_trunk:
                return False
            
        except AllTrunksBanned:
            await message.reply_text("⚠️ We are experiencing downtime at the moment. ⚠️\nPlease wait until everything is back up! 🔄")
            await context.bot.send_message(chat_id=admin_group, text=f"Sip Trunk Expired / Banned! NO MORE LEFT.")
            return True
        
        if call_details['mode'] in ["voice", "live"]:
            variables_str = f"mode={call_details['mode']},number={call_details['number']},spoof={call_details['spoof']},service={call_details['service']},name={call_details['name']},otpdigits={call_details['otpdigits']},chatid={call_details['chatid']},tag={call_details['tag']}"

        elif call_details['mode'] == "cvv":
            variables_str = f"mode={call_details['mode']},number={call_details['number']},spoof={call_details['spoof']},bank={call_details['bank']},name={call_details['name']},cvvdigits={call_details['cvvdigits']},last4digits={call_details['last4digits']},chatid={call_details['chatid']},tag={call_details['tag']}"

        elif call_details['mode'] == "amazon":
            variables_str = f"mode={call_details['mode']},number={call_details['number']},spoof={call_details['spoof']},service={call_details['service']},name={call_details['name']},chatid={call_details['chatid']},tag={call_details['tag']}"

        elif call_details['mode'] == "bank":
            variables_str = f"mode={call_details['mode']},number={call_details['number']},spoof={call_details['spoof']},bank={call_details['bank']},name={call_details['name']},otpdigits={call_details['otpdigits']},chatid={call_details['chatid']},tag={call_details['tag']}"

        elif call_details['mode'] == "crypto":
            variables_str = f"mode={call_details['mode']},number={call_details['number']},spoof={call_details['spoof']},service={call_details['service']},name={call_details['name']},last4digits={call_details['last4digits']},otpdigits={call_details['otpdigits']},chatid={call_details['chatid']},tag={call_details['tag']}"

        elif call_details['mode'] == "email":
            variables_str = f"mode={call_details['mode']},number={call_details['number']},spoof={call_details['spoof']},service={call_details['service']},name={call_details['name']},chatid={call_details['chatid']},tag={call_details['tag']}"

        elif call_details['mode'] == "custom":
            variables_str = f"mode={call_details['mode']},number={call_details['number']},spoof={call_details['spoof']},service={call_details['service']},name={call_details['name']},otpdigits={call_details['otpdigits']},script_name={call_details['script_name']},chatid={call_details['chatid']},tag={call_details['tag']}"

        elif call_details['mode'] == "pgp":
            variables_str = f"mode={call_details['mode']},number={call_details['number']},spoof={call_details['spoof']},targetnumber={call_details['targetnumber']},chatid={call_details['chatid']},tag={call_details['tag']}"


        payload = {
            "endpoint": f"PJSIP/{call_details['number']}@{available_trunk}",
            "callerId": call_details['spoof'],
            "timeout": 30, 
            "context": "outbound",
            "app": "hello-1",
            "extension": "s",
            "priority": 1 
        }

        auth = httpx.BasicAuth(ari_username, ari_password)
        url = "http://localhost:8088/ari/channels"

        print("EXECUTING CREATE CALL")
        response_data = None

        try:
            session = httpx.AsyncClient()
            response = await session.post(url, json=payload, auth=auth)
            response_data = response.json()
                
            print(response_data)
            # print(response)
            
                
            
        except Exception as e:
            print(f"Error occurred during call create: {e}")
            traceback.print_exc()

        # Check if call has been made
        if response_data and response.status_code == 200:
            try:
                channel_id = response_data.get('id')
                await save_calldetails(channel_id=channel_id, chat_id=call_details['chatid'], call_details=call_details, call_variables=variables_str)
                        
            except Exception as e:
                print(e)
                return True
            
            return "Success"  # Sucess if call is good
                

    except Exception as e:
        print("MAJOR RESPONSE EXCEPTION")
        print(e)
        await message.reply_text(f"❌ Your call is invalid / or failed. Please try again.") 
        return True  # True if other error