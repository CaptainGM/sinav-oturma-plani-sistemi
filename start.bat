@echo off
setlocal

set MYSQL_DIR=C:\Users\sahin\mysql-server

rem --- MySQL sunucusu calismiyorsa baslat ---
netstat -an | findstr ":3306" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo MySQL sunucusu baslatiliyor...
    start "MySQL Server" /min "%MYSQL_DIR%\bin\mysqld.exe" --defaults-file="%MYSQL_DIR%\my.ini"
    timeout /t 5 /nobreak >nul
) else (
    echo MySQL sunucusu zaten calisiyor.
)

rem --- Veritabani baglanti bilgileri ---
set DB_HOST=localhost
set DB_USER=root
set DB_PASSWORD=
set DB_NAME=sinav_takvimi_db

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
