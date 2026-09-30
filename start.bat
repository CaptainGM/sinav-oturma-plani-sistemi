@echo off
setlocal

rem --- MongoDB baglanti bilgileri ---
rem MongoDB bir Windows servisi olarak calisir, ayrica baslatmaya gerek yoktur.
set MONGO_URI=mongodb://localhost:27017
set MONGO_DB_NAME=sinav_takvimi_db

rem --- Varsayilan admin girisi: admin@kocaeli.edu.tr / admin123 ---
rem (degistirmek isterseniz asagidaki iki satirin basindaki "rem "i silin)
rem set ADMIN_EMAIL=admin@example.edu.tr
rem set ADMIN_PASSWORD=your_secure_password

rem --- E-posta bildirimi (istege bagli; kullanmiyorsaniz bos birakin) ---
rem set SMTP_HOST=smtp.gmail.com
rem set SMTP_PORT=587
rem set SMTP_USER=your_account@gmail.com
rem set SMTP_PASSWORD=your_app_password

cd /d "%~dp0"
python main.py

echo.
echo Uygulama kapandi.
pause
