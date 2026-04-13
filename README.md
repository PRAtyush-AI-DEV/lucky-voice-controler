# Lucky — Windows Voice Controller

"Lucky" is a Python-based offline voice-controlled virtual assistant for Windows 10/11. It uses `openWakeWord` for local wake-word detection, `Vosk` for offline Speech-to-Text inference (English and Hindi), and fuzzy matching for executing local system commands.

## Features
- **Offline & Private:** All voice recognition runs locally. No data is sent to the cloud.
- **Bilingual:** Understands commands in both English and Hindi/Hinglish.
- **System Control:** Lock/Unlock PC securely, Volume/Brightness adjustments, Media playback control.
- **Application Control:** Open and close regular Windows applications.
- **System Tray Integration:** Silent background operation.

## Installation

### Prerequisites
- Python 3.10+
- A working Microphone

### 1. Install Dependencies
```bash
git clone <your-repo-url>
cd "lucky voice controler"
pip install -r requirements.txt
```

### 2. Download Vosk Models
Since Vosk runs offline, you need to download the acoustic models:
1. Go to [Vosk Models](https://alphacephei.com/vosk/models).
2. Download English (`vosk-model-small-en-us-0.15`) and Hindi (`vosk-model-hi-0.22`).
3. Extract the downloaded zips and place their folders inside the `models/` directory in this project.
Your folder structure should look like:
```text
lucky/
  models/
    vosk-model-hi-0.22/
    vosk-model-small-en-us-0.15/
```

### 3. First-Time Setup
Run the setup wizard:
```bash
python main.py --setup
```
This will generate `config.json` and prompt you to establish your secure Windows PIN/Password used for unlocking your screen. It is encrypted locally using the `cryptography` module.

## Usage

Start Lucky normally:
```bash
python main.py
```
A system tray icon (a green "L") will appear. You can right-click it to access **Lucky Settings** or pause the engine.

### Voice Commands
Say *"Lucky"* (or your configured wake word) to wake the assistant. A beep will play indicating it's listening. 

Examples:
- **"Lucky, laptop lock karo"** -> Locks Windows.
- **"Lucky, unlock karo"** -> Uses your secure PIN to unlock on the lock screen.
- **"Lucky, chrome kholo"** -> Opens Google Chrome.
- **"Lucky, spotify band karo"** -> Closes Spotify.
- **"Lucky, volume badha do"** -> Increases system volume.

## Custom Wake Word Training
By default, Lucky uses the built-in `openWakeWord` models. To train a custom "Lucky" model:
1. `pip install openwakeword[train]`
2. Follow openWakeword guidelines to generate synthetic training audio for "lucky" using TTS (gTTS or Piper).
3. Run `python -m openwakeword.train --wake_word "lucky"`
4. Copy the generated `.tflite` file to `models/lucky.tflite`.
The tool will automatically prioritize `models/lucky.tflite` if it exists.

## Troubleshooting
- **No Mic Detected:** Check Windows Privacy Settings (Microphone access).
- **Not Listening / Model Error:** Verify that your `models/` folder contains the correctly named Vosk models as defined in `config.json`.
- **Playsound/Alarm Error:** Ensure you don't have older conflicting libraries (Lucky uses `winsound` as a robust Windows alternative).
