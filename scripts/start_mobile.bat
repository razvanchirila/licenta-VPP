@echo off
REM Aplicatia Flutter in Chrome. Cheia WeatherAPI se da la build:
REM   start_mobile.bat --dart-define=WEATHER_API_KEY=cheia_ta
cd /d "%~dp0..\mobile"
flutter run -d chrome --dart-define=API_URL=http://127.0.0.1:8000/api %*
