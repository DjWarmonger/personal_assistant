# User Setup Guide - Discord for Notion Integration

## Prerequisites
- Docker Desktop installed and running
- Cloudflare account
- Discord account with server admin permissions

## Step 1: Cloudflare Tunnel Setup

### 1.1 Install Cloudflare Tunnel
```bash
# macOS
brew install cloudflared

# Windows/Linux - download binary from Cloudflare
```

### 1.2 Login to Cloudflare
```bash
cloudflared tunnel login
```
This will open your browser - authenticate with your Cloudflare account.

### 1.3 Create and Configure Tunnel
```bash
# Create tunnel
cloudflared tunnel create agent-tunnel

# Route DNS (replace with your domain)
cloudflared tunnel route dns agent-tunnel agent.yourdomain.com
```

### 1.4 Create Configuration File
Create `~/.cloudflared/config.yml`:
```yaml
tunnel: agent-tunnel
credentials-file: /home/you/.cloudflared/agent-tunnel.json
ingress:
  - hostname: agent.yourdomain.com
    service: http://localhost:8080
  - service: http_status:404
```

### 1.5 Start Tunnel
```bash
cloudflared tunnel run agent-tunnel
```

## Step 2: Discord Bot Setup

### 2.1 Create Discord Application
1. Go to Discord Developer Portal (https://discord.com/developers/applications)
2. Click "New Application"
3. Give it a name and create

### 2.2 Create Bot
1. Go to "Bot" section
2. Click "Add Bot"
3. Click "Reset Token" and save the token securely
4. Enable "Message Content Intent" if needed

### 2.3 Generate Invite Link
1. Go to "OAuth2" → "URL Generator"
2. Select scope: `bot`
3. Select permissions: `Send Messages`, `Read Messages`
4. Copy generated URL and add bot to your Discord server

### 2.4 Create Environment File
Create `.env` file in the project directory:
```env
DISCORD_TOKEN=your_bot_token_here
AGENT_URL=https://agent.yourdomain.com
```

## Step 3: Launch Services

### 3.1 Build and Start Docker Containers
```bash
# From the Integrations/Discord for Notion directory
docker compose up -d
```

### 3.2 Verify Services
```bash
# Check container status
docker ps

# Check logs
docker logs discord-notion-bot
docker logs notion-agent
docker logs discord-notion-cloudflared
```

## Step 4: Test Integration

### 4.1 Test in Discord
In your Discord server, try:
```
!ask How are you?
```

The bot should respond with output from your Notion Agent.

### 4.2 Verify External Access
Test your public endpoint:
```bash
curl https://agent.yourdomain.com/health
```

## Troubleshooting Commands

### Check Service Status
```bash
# View all containers
docker ps -a

# Check specific service logs
docker logs -f discord-notion-bot
docker logs -f notion-agent
```

### Restart Services
```bash
# Restart all services
docker compose restart

# Restart specific service
docker compose restart discord-bot
```

### Stop Services
```bash
# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v
```

## Configuration Notes

- Replace `agent.yourdomain.com` with your actual domain
- Keep your Discord bot token secure in the `.env` file
- The Notion Agent runs on internal port 8000, exposed externally on 8080
- Cloudflare tunnel provides HTTPS termination automatically 