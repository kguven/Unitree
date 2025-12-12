# Habibot Service Installation Guide

This guide explains how to set up the systemd service to automatically start Habibot on the Unitree robot at boot.

## Installation Steps

### 1. Edit the Service File

Open `habibot.service` and verify the following values:

```bash
# Get GEMINI_API_KEY from your .env file and enter it here
Environment="GEMINI_API_KEY=your_api_key_here"

# Check the project path (default: /home/unitree/Unitree)
WorkingDirectory=/home/unitree/Unitree
ExecStart=/usr/bin/python3 /home/unitree/Unitree/main.py
```

### 2. Copy the Service File

```bash
# Copy service file to systemd directory
sudo cp habibot.service /etc/systemd/system/

# Set file permissions
sudo chmod 644 /etc/systemd/system/habibot.service
```

### 3. Enable and Start the Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start automatically at boot
sudo systemctl enable habibot.service

# Start the service immediately
sudo systemctl start habibot.service
```

## Service Management

### Check Status
```bash
sudo systemctl status habibot.service
```

### View Logs
```bash
# All logs
sudo journalctl -u habibot.service

# Last 50 lines
sudo journalctl -u habibot.service -n 50

# Live follow
sudo journalctl -u habibot.service -f
```

### Stop Service
```bash
sudo systemctl stop habibot.service
```

### Restart Service
```bash
sudo systemctl restart habibot.service
```

### Disable Auto-start at Boot
```bash
sudo systemctl disable habibot.service
```

## Troubleshooting

### If Service Won't Start

1. **Check logs:**
   ```bash
   sudo journalctl -u habibot.service -n 100
   ```

2. **Check Python path:**
   ```bash
   which python3
   # Compare output with ExecStart in service file
   ```

3. **Check file permissions:**
   ```bash
   ls -la /home/unitree/Unitree/main.py
   # unitree user must have read permission
   ```

4. **Check environment variables:**
   - Add GEMINI_API_KEY from `.env` file to service file
   - Or use the `.env` file directly by modifying the service file:
   
   ```ini
   [Service]
   EnvironmentFile=/home/unitree/Unitree/.env
   ```

### Manual Test

Test manually before installing the service:

```bash
cd /home/unitree/Unitree
python3 main.py
```

## Notes

- Service automatically restarts 10 seconds after failure
- All output is logged to systemd journal
- Starts after network and sound systems are ready
- Runs as `unitree` user
