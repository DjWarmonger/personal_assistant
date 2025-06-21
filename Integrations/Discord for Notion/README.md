# Discord -> Notion Agent Communication

A Docker-based system that enables Discord users to interact with a Notion Agent through chat commands. The system uses Cloudflare Tunnel to expose the Notion Agent securely to the internet.

## Architecture

```
Discord User → Discord Bot → Notion Agent ← Cloudflare Tunnel ← Internet
```

### Components

1. **Discord Bot** - Python bot using discord.py that handles Discord commands
2. **Notion Agent** - Service that processes queries and interacts with Notion (placeholder)
3. **Cloudflare Tunnel** - Secure tunnel to expose the Notion Agent publicly

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose
- Discord Bot Token
- Cloudflare account with a configured tunnel
- Notion API credentials (for the agent)

### 2. Configuration

1. **Copy environment file:**
   ```bash
   cp env.example .env
   ```

2. **Edit `.env` with your credentials:**
   - `DISCORD_TOKEN`: Your Discord bot token
   - `NOTION_API_KEY`: Your Notion integration API key
   - `NOTION_DATABASE_ID`: Target Notion database ID
   - `TUNNEL_ID`: Your Cloudflare tunnel ID
   - `TUNNEL_DOMAIN`: Your domain configured with Cloudflare

3. **Update Cloudflare configuration:**
   - Edit `cloudflared/config.yml`
   - Replace `YOUR_TUNNEL_ID_HERE` with your actual tunnel ID
   - Replace `YOUR_DOMAIN_HERE` with your domain
   - Place your tunnel credentials file in `cloudflared/`

### 3. Setup Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the bot token to your `.env` file
5. In "OAuth2 > URL Generator":
   - Select scope: `bot`
   - Select permissions: `Send Messages`, `Read Messages`, `Use Slash Commands`
6. Use the generated URL to add the bot to your server

### 4. Setup Cloudflare Tunnel

1. **Install cloudflared:**
   ```bash
   # On macOS
   brew install cloudflared
   
   # On Windows/Linux - download from Cloudflare
   ```

2. **Login and create tunnel:**
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create discord-notion-agent
   cloudflared tunnel route dns discord-notion-agent your-domain.com
   ```

3. **Copy tunnel credentials:**
   ```bash
   # Copy the generated .json file to cloudflared/ directory
   cp ~/.cloudflared/your-tunnel-id.json ./cloudflared/
   ```

### 5. Deploy

```bash
# Build and start all services
docker compose up -d

# Check logs
docker compose logs -f

# Stop services
docker compose down
```

## Usage

Once deployed, you can interact with the bot on Discord:

- `!ask What are my tasks for today?` - Ask the Notion Agent a question
- `!health` - Check if the Notion Agent is responding
- `!help` - Show available commands

## Configuration Details

### Docker Compose Services

- **discord-bot**: Discord bot container
- **notion-agent**: Notion Agent service (placeholder)
- **cloudflared**: Cloudflare tunnel service

### Cloudflare Tunnel Configuration

The tunnel configuration includes:
- Webhook endpoint exemption (`/webhook/*`) to avoid Cloudflare Access issues
- Main agent endpoint routing
- Health check endpoint
- Required catch-all rule to prevent container restart issues

### Avoiding Previous Issues

This configuration addresses several known issues:
1. **No service dependencies** for cloudflared to prevent startup issues
2. **Catch-all ingress rule** required as the last rule
3. **Webhook path exemption** to avoid 401 Unauthorized errors
4. **Proper service routing** to the correct backend service

## Development

### Notion Agent Placeholder

The Notion Agent service is currently a placeholder. To implement:

1. Create your Notion Agent implementation
2. Update the `notion-agent` service in `docker-compose.yml`:
   ```yaml
   notion-agent:
     build:
       context: ./notion-agent
       dockerfile: Dockerfile
     # ... rest of configuration
   ```
3. Ensure your agent exposes:
   - `POST /query` - Main query endpoint
   - `GET /health` - Health check endpoint

### API Contract

The Discord bot expects the Notion Agent to implement:

**POST /query**
```json
{
  "query": "user question",
  "user_id": "discord_user_id",
  "timestamp": 1234567890
}
```

**Response:**
```json
{
  "answer": "agent response",
  "status": "success"
}
```

**GET /health**
```json
{
  "status": "healthy",
  "timestamp": 1234567890
}
```

## Troubleshooting

### Common Issues

1. **Cloudflared container restarting:**
   - Check that the catch-all rule is present and last in config.yml
   - Verify tunnel ID and credentials file path

2. **Discord bot not responding:**
   - Check Discord token validity
   - Verify bot permissions on the server
   - Check container logs: `docker compose logs discord-bot`

3. **Notion Agent unreachable:**
   - Verify the agent service is running
   - Check network connectivity between containers
   - Test health endpoint: `docker compose exec discord-bot curl http://notion-agent:8080/health`

### Logs

```bash
# View all logs
docker compose logs

# View specific service logs
docker compose logs discord-bot
docker compose logs notion-agent
docker compose logs cloudflared

# Follow logs in real-time
docker compose logs -f
```

## Security Considerations

- Keep your `.env` file secure and never commit it to version control
- The Discord bot runs as a non-root user for security
- Cloudflare Tunnel provides secure access without exposing ports directly
- Consider implementing rate limiting and authentication for production use

## Next Steps

1. Implement the actual Notion Agent service
2. Add slash commands support for better UX
3. Implement user authentication and authorization
4. Add logging and monitoring
5. Consider deployment to a VPS or cloud platform for 24/7 availability 