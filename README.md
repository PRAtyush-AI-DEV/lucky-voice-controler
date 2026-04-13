# 🎤 Lucky Voice Controller

An AI-powered voice assistant built in Python that allows you to control your Windows system using natural voice commands in both **Hindi** and **English**.

---

## 🚀 Key Features

*   🎙️ **Bilingual Support**: Seamlessly switch between Hindi and English commands.
*   🤖 **Gemini AI Integration**: Natural language chat and advanced web search macros.
*   📁 **File & Folder Management**: Create folders, open deep-linked directories, and manage your workspace.
*   🌐 **Browser Intelligence**: Open websites, perform searches, and automate browser tasks with macros.
*   🖥️ **System Automation**: Control volume, brightness, WiFi, Bluetooth, and system power states (Lock, Sleep, Shutdown).
*   🔔 **Smart Reminders**: Set alarms, timers, and reminders with voice notifications.
*   ⚡ **Offline Speech Core**: Uses the VOSK engine for fast, private, and offline speech recognition.
*   🔐 **Security First**: Integrated password protection for dangerous system operations and unauthorized access.

---

## 📂 Project Structure

```
lucky-voice-controller/
│── actions/          # Command execution modules (System, Browser, Apps, etc.)
│── assets/           # Sounds, icons, and UI media
│── models/           # VOSK offline voice models
│── tests/            # Automated test suites
│── main.py           # Application Entry Point & Tray Controller
│── intent_parser.py  # NLP logic & Devanagari phonetic mapping
│── speech_to_text.py # Audio capture & VOSK integration
│── speaker.py        # Text-to-Speech & response logic
│── config.json       # User preferences & app/folder aliases
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository
```bash
git clone https://github.com/PRAtyush-AI-DEV/lucky-voice-controler.git
cd lucky-voice-controler
```

### 2️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 3️⃣ Configure Voice Models ⚠️
Download the VOSK models for Hindi and English to ensure offline performance:
*   [Hindi Model](https://alphacephei.com/vosk/models) (vosk-model-hi-0.22)
*   [English Model](https://alphacephei.com/vosk/models) (vosk-model-small-en-us-0.15)

Place them in the `/models/` directory as specified in `config.json`.

---

## 🎯 Example Commands

| Category | Commands (Hindi / English) |
| :--- | :--- |
| **Apps** | "Chrome kholo" / "Open Notepad" |
| **System** | "Laptop lock karo" / "Increase volume" |
| **AI** | "Gemini par search karo aaj ka mausam" / "Explain gravity" |
| **Folders** | "Naya folder banao projects" / "Recycle bin kholo" |
| **Misc** | "5 minute ka timer lagao" / "Take a screenshot" |

---

## 🧠 Customization
You can easily add your own application shortcuts or folder paths by editing the `app_aliases` section in `config.json`:
```json
"app_aliases": {
  "work": "C:/Users/Name/Projects/Work",
  "editor": "code.exe"
}
```

---

## 🤝 Contributing
Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

---

## 👨‍💻 Author
**Pratyush Upadhyay**  
[GitHub Profile](https://github.com/PRAtyush-AI-DEV)

---

## ⭐ Support
Give a ⭐ if this project helped you!

---

## ⚡ Disclaimer
This project is for educational and personal use. Use system-level commands responsibly.
