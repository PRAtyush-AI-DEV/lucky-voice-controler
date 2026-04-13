@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================
echo Lucky - Quick Test Suite
echo ============================================
echo.

echo [1/3] Running unit tests...
python -m unittest -v
if errorlevel 1 (
  echo.
  echo Unit tests FAILED.
  echo.
  if not defined NO_PAUSE pause
  exit /b 1
)

echo.
echo [2/3] Config + environment sanity...
python -c "import os, json, pathlib; c=json.load(open('config.json','r',encoding='utf-8')); print('mode=', c.get('mode')); print('wake_word=', c.get('wake_word')); print('language=', c.get('language')); print('run_on_startup=', c.get('run_on_startup')); print('instant_ack=', c.get('instant_ack', True)); print('has_gemini_key_in_config=', bool((c.get('gemini_api_key','') or '').strip())); print('has_GEMINI_API_KEY_env=', bool((os.getenv('GEMINI_API_KEY','') or '').strip()));"

echo.
echo [3/3] Models + basic filesystem checks...
python -c "import json, os, sys; c=json.load(open('config.json','r',encoding='utf-8')); paths=[c.get('vosk_model_path_en',''), c.get('vosk_model_path_hi','')]; print('models:'); [print(' -',p,'=>',('OK' if os.path.isdir(p) else 'MISSING')) for p in paths]; sys.exit(1 if any((not os.path.isdir(p)) for p in paths) else 0)"
if errorlevel 1 (
  echo.
  echo One or more Vosk model folders are missing.
  echo Please download models into the models\ folder as per README.md
  echo.
  if not defined NO_PAUSE pause
  exit /b 1
)

echo.
echo All checks PASSED.
echo.
if not defined NO_PAUSE pause
exit /b 0

