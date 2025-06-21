
#### 3. Bot Discord

##### 3.1 Rejestracja

1. W Discord **Developer Portal → New Application**.
2. **Bot → Add Bot → Reset Token** (zapisz do `.env`).
3. **OAuth2 / URL Generator**: scope `bot`, uprawnienia `Send Messages`, `Read Messages`.
4. Dodaj bota na swój serwer przez wygenerowany link.

##### 3.2 Kod bota (Python + discord.py)

```python
# bot.py
import os, asyncio, httpx
import discord
from discord.ext import commands
TOKEN = os.getenv("DISCORD_TOKEN")
AGENT_URL = os.getenv("AGENT_URL", "https://agent.example.com")

intents = discord.Intents.default()
intents.message_content = True          # konieczne do odczytu treści

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Zalogowano jako {bot.user}")

@bot.command(name="ask")
async def ask_agent(ctx: commands.Context, *, question: str):
    """Przekazuje pytanie do Agenta i zwraca odpowiedź"""
    await ctx.trigger_typing()
    async with httpx.AsyncClient(timeout=20.0, verify=True) as client:
        r = await client.post(AGENT_URL, json={"query": question})
        r.raise_for_status()
    answer = r.json().get("answer", "❌ Brak odpowiedzi")
    # Discord ogranicza do 2000 znaków
    if len(answer) > 1900:
        answer = answer[:1900] + "…"
    await ctx.reply(answer)

if __name__ == "__main__":
    bot.run(TOKEN)
```

