@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ===============================================
echo SMARTLIBRARY - CHAY WEB CHO NHIEU THIET BI
echo ===============================================
echo.
echo Dia chi IPv4 cua may nay:
ipconfig | findstr /C:"IPv4 Address" /C:"IPv4 Address. . ." /C:"Địa chỉ IPv4"
echo.
echo May khac cung Wi-Fi/LAN mo: http://IP_MAY_NAY:8501
echo Neu Windows hoi Firewall, hay chon Allow access.
echo.
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
pause
