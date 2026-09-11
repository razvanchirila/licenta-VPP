@echo off
REM Aplicatia Flutter in Chrome. Cheia WeatherAPI se da la build:
REM   start_mobile.bat --dart-define=WEATHER_API_KEY=cheia_ta
cd /d "%~dp0..\mobile"
flutter run -d chrome %*
