# AsteriskOTPBot  
*Asterisk SIP Telegram OTP Bot — for educational use only.*

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)  
[![Made by DevZahir](https://img.shields.io/badge/Made%20by-DevZahir.com-blueviolet)](https://devzahir.com)

---

## 📌 Overview

**AsteriskOTPBot** is an advanced Telegram bot designed to automate One-Time Password (OTP) delivery through voice calls using **Asterisk PBX** and **VoIP SIP lines**. It leverages SIP call routing to place OTP verification calls, integrating Telegram commands for user interaction.

> ⚠️ **Important:** This project is intended strictly for **educational and research purposes**. Usage in production or unauthorized environments is discouraged.

### Key Features

- Seamless integration between Telegram bot and Asterisk PBX  
- Automated VoIP SIP call logic for OTP delivery  
- Intelligent fallback mechanism when primary SIP routes are blocked (`c=a` SDP logic)  
- Configurable environment variables for flexible deployment  
- Planned integration of an automated payment and top-up system for usage management  

---

## ⚙️ Architecture & Workflow

### System Components

- **Telegram Bot:** Handles user commands and OTP requests  
- **Asterisk PBX Server:** Manages SIP calls and telephony workflows  
- **MongoDB:** Stores user data, usage stats, and system state  
- **FastAPI Server:** Bridges Asterisk ARI events and bot logic  
- **Azure TTS (optional):** Text-to-speech service to generate OTP voice prompts  

### How It Works Step-by-Step

1. **OTP Request:** User sends a command to the Telegram bot requesting an OTP call.  
2. **Call Initiation:** The bot triggers the FastAPI server, which instructs Asterisk to place a call via a configured SIP line.  
3. **Fallback Logic:** If the primary SIP line is blocked or fails, Asterisk automatically attempts the next available SIP plug using the `c=a` SDP attribute fallback logic.  
4. **OTP Delivery:** Once the call connects, Azure TTS (if configured) reads out the OTP or the system plays the prerecorded OTP message.  
5. **Completion:** The OTP delivery status is sent back to the user through Telegram.

---

## 🚀 Installation & Setup

### Prerequisites

- A running **Asterisk PBX** instance with configured SIP trunks  
- Telegram Bot token (from BotFather)  
- MongoDB database  
- Optional: Azure Speech Services subscription for TTS  
- Python 3.9+ environment  

### Configuration

1. Clone this repository:

    ```bash
    git clone https://github.com/DevZahir/AsteriskOTPBot.git
    cd AsteriskOTPBot
    ```

2. Create a `.env` file in the project root with the following variables:

    ```env
    # === GENERAL ===

    # DATABASE
    MONGO_URL=""            # MongoDB connection string
    DB_NAME=""              # Database name

    # FASTAPI SERVER
    WS_URL="ws://localhost:8088/ari/events?api_key=username:password&app=hello-1"  # Asterisk ARI WebSocket URL
    SERVER_PORT="8000"      # FastAPI server port

    # TELEGRAM BOT
    BOT_TOKEN=""            # Telegram bot token
    ADMIN_GROUP_ID=""       # Telegram group ID for admin notifications (e.g., low credit alerts)
    CHAT_GROUP_ID=""        # Telegram group where bot will interact with users
    ADMINS=""               # Comma-separated Telegram user IDs with admin privileges
    SHOP_LINK=""            # URL to top-up or purchase page (planned feature)

    # ASTERISK
    MAX_DAILY_USAGE="700"   # Maximum allowed daily OTP calls
    ARI_USERNAME="asterisk" # Asterisk ARI username
    ARI_PASSWORD="asterisk" # Asterisk ARI password

    # AZURE TTS (optional)
    SUBSCRIPTION_KEY=""     # Azure Speech Services subscription key
    AZURE_REGION=""         # Azure region identifier
    VOICE_NAME=""           # Name of the Azure TTS voice to use
    ```

3. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Run the FastAPI server and Telegram bot as per the included instructions or scripts.

---

## 🛠 Usage

This bot enforces subscription-based access, usage limits, and advanced call fallback logic automatically to prevent abuse and provide a smooth user experience.

### User Commands

- `/start [referrer]`  
  Initializes interaction, registers the user, and optionally tracks referral codes. Displays main menu with commands and purchase links.

- `/purchase`  
  Displays subscription purchase options with payment links. Users can buy keys to activate access.

- `/redeem {key}`  
  Activates a subscription key. The bot validates key status (active, redeemed, invalid) and notifies both user and admin group on success or failure.

- `/checktime`  
  Shows the user their remaining subscription time. If no active subscription, prompts them to purchase.

- `/call`  
  Initiates a SIP call using the specified code (e.g., Paypal, Venmo). This triggers the OTP delivery through Asterisk SIP lines.

- `/cvv`, `/crypto`, `/amazon`, `/email`, `/bank`, `/live`  
  Specialized commands for advanced OTP capture or scripts during calls.

- `/createscript`, `/scripts`, `/script`, `/customcall`  
  Commands for users to manage and use custom call scripts.

### Admin Commands

- `/generate {days} [referrer]`  
  Create a new subscription key valid for the specified number of days, optionally linked to a referrer.

- `/deletekey {key}`  
  Delete an existing subscription key.

- `/bulkcreatekey {amount} {days} [referrer]`  
  Generate multiple subscription keys in bulk.

- `/keystat`  
  Shows statistics about keys (partial code provided).

### Subscription & Usage Enforcement

- All users must redeem valid subscription keys to use call commands.
- Usage stats and limits are tracked per user in MongoDB.
- The bot automatically prevents users exceeding the configured max daily usage (e.g., `MAX_DAILY_USAGE=700`).
- Admins receive notifications about key redemptions and system alerts in the admin group.
- Calls are made through Asterisk with automatic fallback between SIP lines (`c=a` logic) to ensure successful OTP delivery.

---

## 🔜 Planned Features

- **Automated payment gateway integration** to allow users to top-up their credits directly via the bot.  
- Enhanced analytics dashboard for usage monitoring.  
- Multi-language TTS support via Azure.  
- User-friendly web interface for managing SIP lines and settings.

---

## 🤝 Contributing

Contributions are welcome! Please submit issues or pull requests on GitHub.  
For support or inquiries, reach out via [DevZahir.com](https://devzahir.com#contact).

If you find this project useful, please consider supporting me:

[![Buy Me a Coffee](https://devzahir.com/_next/image?url=https%3A%2F%2Fi.ibb.co%2FDXwdPKd%2Fbmc-qr.png&w=384&q=75)](https://www.buymeacoffee.com/DevZahir)  

**🔗 [Buy Me a Coffee](https://www.buymeacoffee.com/DevZahir)**

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
