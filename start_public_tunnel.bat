@echo off
echo ========================================================
echo Generating Free Instant Public HTTPS URL for AgriBot OS
echo ========================================================

:tunnel_loop
echo [%time%] Connecting secure OpenSSH tunnel to local port 8000...
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -R 80:127.0.0.1:8000 nokey@localhost.run
echo [%time%] Tunnel disconnected. Reconnecting in 3 seconds...
timeout /t 3 /nobreak >nul
goto tunnel_loop

