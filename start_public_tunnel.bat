@echo off
echo ========================================================
echo Generating Free Instant Public HTTPS URL for AgriBot OS
echo ========================================================
echo Connecting secure OpenSSH tunnel to local port 8000...
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -R 80:127.0.0.1:8000 nokey@localhost.run
pause
