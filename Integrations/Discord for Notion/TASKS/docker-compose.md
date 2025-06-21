##### 3.3 Uruchomienie bota w Dockerze

```dockerfile
# bot.Dockerfile
FROM python:3.11-slim
WORKDIR /bot
COPY bot.py requirements.txt ./
RUN pip install -r requirements.txt
CMD ["python", "bot.py"]
```

`requirements.txt`:

```
discord.py>=2.4.0
httpx>=0.27
```

---

#### 4. docker-compose (agent + bot + cloudflared)

```yaml
services:
  agent:
    build: .
    container_name: agent
    ports: ["8080:8080"]

  cloudflared:
    image: cloudflare/cloudflared:latest
    command: tunnel run agent-tunnel
    restart: unless-stopped
    volumes:
      - ~/.cloudflared:/home/nonroot/.cloudflared
    network_mode: "host"   # bo tunel łączy się z localhost:8080

  discord-bot:
    build:
      context: .
      dockerfile: bot.Dockerfile
    environment:
      DISCORD_TOKEN: "${DISCORD_TOKEN}"
      AGENT_URL: "https://agent.example.com"
```

> **Tip:** W pliku `.env` trzymaj `DISCORD_TOKEN` i inne sekrety (docker-compose ładuje je automatycznie).

---

#### 5. Testy

1. `docker compose up -d`
2. Na Discordzie:

   ```
   !ask Jak się masz?
   ```

   Bot powinien odpisać tym, co zwróci twój endpoint.

---
