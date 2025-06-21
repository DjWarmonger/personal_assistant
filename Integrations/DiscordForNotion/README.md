# Discord for Notion Integration

A Discord bot that connects to a Notion Agent via Cloudflare Tunnel, allowing users to interact with Notion content through Discord messages.

## Architecture Overview

```
Discord User → Discord Bot → Cloudflare Tunnel → Notion Agent (Docker) → Notion API
```

## Prerequisites

1. **Docker Desktop** - Must be running on Windows
2. **Cloudflare Account** - With existing tunnel setup
3. **Notion Integration** - API tokens configured
4. **Discord Bot** - Application and bot token (TODO)

## Quick Start

### 1. Environment Setup
# TODO: Copy from NotionAgent/.env

Create `.env` file in this directory:
```bash
# Notion API Configuration
NOTION_TOKEN=your_notion_integration_token
NOTION_DATABASE_ID=your_database_id

# Langfuse Configuration (optional)
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_HOST=https://cloud.langfuse.com

# Discord Bot Configuration (TODO)
DISCORD_TOKEN=your_discord_bot_token
# TODO: Verify if GUILD_ID is needed
DISCORD_GUILD_ID=your_discord_server_id
```

### 2. Launch Services

**From project root directory:**

```bash
# Start Notion Agent container
docker compose -f Integrations/DiscordForNotion/docker_compose.yml up -d

# Start Cloudflare Tunnel
cloudflared tunnel --origincert "F:\Programowanie\n8n\cloudflared\cert.pem" --config "Integrations/DiscordForNotion/cloudflared/config.yml" run
```

### 3. Verify Setup

Check all services are running:

```bash
# Check Docker container status
docker ps

# Check container logs
docker logs notion-rest-server

# Test health endpoint locally
curl http://localhost:8000/health

# Test via Cloudflare tunnel
curl https://n8n.tzsmartsolutions.com/health
```

## Service Details

### Notion Agent (Docker Container)

- **Container Name**: `notion-agent`
- **Local Port**: `8080` (mapped from container port 8000)
- **Health Check**: `GET /health`
- **Main Endpoint**: `POST /api/v1/process`

**Key Features:**
- REST API for Notion operations
- Block caching system
- Favorites management
- Context-aware responses

### Cloudflare Tunnel

- **Tunnel ID**: `e1439cb6-fd4e-4c3b-9bbb-c5dbc1f5273c`
- **Domain**: `n8n.tzsmartsolutions.com`
- **Certificate**: `F:\Programowanie\n8n\cloudflared\cert.pem`

**Routing Rules:**
- `/notion/*` → Notion Agent
- `/health` → Health check
- `/*` → Default fallback

## Testing Guide

### 1. Container Health Check

```bash
# Check if container is running
docker ps | grep notion-agent

# View container logs
docker logs notion-agent

# Test local endpoint
curl -X GET http://localhost:8080/health
# Expected: {"status": "ok"}
```

### 2. Cloudflare Tunnel Validation

```bash
# Validate configuration
cloudflared tunnel --origincert "F:\Programowanie\n8n\cloudflared\cert.pem" --config "Integrations/DiscordForNotion/cloudflared/config.yml" ingress validate

# Test routing rules
cloudflared tunnel --origincert "F:\Programowanie\n8n\cloudflared\cert.pem" --config "Integrations/DiscordForNotion/cloudflared/config.yml" ingress rule https://n8n.tzsmartsolutions.com/health

# Test public endpoint
curl https://n8n.tzsmartsolutions.com/health
# Expected: {"status": "ok"}
```

### 3. Notion Agent API Test

```bash
# Test Notion query endpoint
curl -X POST https://n8n.tzsmartsolutions.com/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{"input": "What pages do I have?"}'
```

## Troubleshooting

### Common Issues

1. **Docker Desktop not running**
   ```
   Error: error during connect: Head "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/_ping"
   Solution: Start Docker Desktop and wait for it to initialize
   ```

2. **Container build fails**
   ```bash
   # Clean rebuild
   docker compose -f Integrations/DiscordForNotion/docker_compose.yml down
   docker build --no-cache -f Agents/NotionAgent/Dockerfile -t notion-rest-server .
   ```

3. **Cloudflare tunnel connection issues**
   ```bash
   # Check tunnel status
   cloudflared tunnel --origincert "F:\Programowanie\n8n\cloudflared\cert.pem" list
   
   # Verify config
   cloudflared tunnel --origincert "F:\Programowanie\n8n\cloudflared\cert.pem" --config "Integrations/DiscordForNotion/cloudflared/config.yml" ingress validate
   ```

4. **Health check fails**
   - Verify container is running: `docker ps`
   - Check logs: `docker logs notion-agent`
   - Test local port: `curl http://localhost:8080/health`

### Log Locations

- **Container logs**: `docker logs notion-agent`
- **Persistent logs**: `./logs/` directory (mounted volume)
- **Cloudflare logs**: `/etc/cloudflared/cloudflared.log` (in tunnel config)

## Development Notes

### File Structure
```
Integrations/DiscordForNotion/
├── README.md                 # This file
├── docker_compose.yml        # Container orchestration
├── .env                      # Environment variables
├── bot.py                    # Discord bot (TODO)
├── cloudflared/
│   ├── config.yml           # Tunnel configuration
│   └── e1439cb6-...json     # Tunnel credentials
└── .notes/
    └── cloudflare_cheatsheet.md  # Command reference
```

### Current Status

- ✅ **Notion Agent**: Containerized and running
- ✅ **Cloudflare Tunnel**: Configured and tested
- ✅ **HTTPS Endpoint**: Working (`https://n8n.tzsmartsolutions.com`)
- 🔄 **Discord Bot**: Not implemented yet
- 🔄 **Full Integration**: Pending Discord bot completion

### Next Steps

1. Create Discord application and bot
2. Implement Discord message handling
3. Add error handling and rate limiting
4. Test end-to-end Discord ↔ Notion flow

## API Reference

### Health Check
```http
GET /health
Response: {"status": "ok"}
```

### Notion Query
```http
POST /api/v1/process
Content-Type: application/json

{
  "input": "Your question about Notion content"
}
```

## Security Considerations

- Tunnel credentials are stored locally
- Environment variables contain sensitive tokens
- Public endpoint requires proper authentication (TODO)
- Rate limiting should be implemented for production use 