#!/usr/bin/env python3
"""
Discord Bot for Notion Agent Communication
Handles Discord commands and forwards them to the Notion Agent service
"""

import os
import asyncio
import logging
from typing import Optional
import httpx
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# TODO: Reuse logs from tz_common?

# Configure logging
logging.basicConfig(
	level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
	format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.getenv("DISCORD_TOKEN")
NOTION_AGENT_URL = os.getenv("NOTION_AGENT_URL", "http://notion-agent:8080")

# TODO: Consider using direct messages with no prefix
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")

if not TOKEN:
	logger.error("DISCORD_TOKEN environment variable is required")
	exit(1)

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

class NotionAgentClient:
	"""HTTP client for communicating with Notion Agent"""
	
	def __init__(self, base_url: str):
		self.base_url = base_url.rstrip('/')
		self.timeout = httpx.Timeout(30.0)
	
	async def send_query(self, query: str, user_id: str = None) -> dict:
		"""Send a query to the Notion Agent and return the response"""
		payload = {
			"query": query,
			"user_id": user_id,
			"timestamp": asyncio.get_event_loop().time()
		}
		
		async with httpx.AsyncClient(timeout=self.timeout) as client:
			try:
				response = await client.post(
					f"{self.base_url}/query",
					json=payload,
					headers={"Content-Type": "application/json"}
				)
				response.raise_for_status()
				return response.json()
			except httpx.TimeoutException:
				logger.error("Timeout when contacting Notion Agent")
				return {"error": "Request timed out", "answer": "⏰ Request timed out. Please try again."}
			except httpx.HTTPStatusError as e:
				logger.error(f"HTTP error {e.response.status_code} from Notion Agent")
				return {"error": f"HTTP {e.response.status_code}", "answer": "❌ Service temporarily unavailable"}
			except Exception as e:
				logger.error(f"Unexpected error: {e}")
				return {"error": str(e), "answer": "❌ An unexpected error occurred"}

# Initialize Notion Agent client
notion_client = NotionAgentClient(NOTION_AGENT_URL)

@bot.event
async def on_ready():
	"""Called when the bot is ready"""
	logger.info(f"✅ Bot logged in as {bot.user} (ID: {bot.user.id})")
	logger.info(f"🔗 Connected to Notion Agent at: {NOTION_AGENT_URL}")

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
	"""Handle command errors"""
	if isinstance(error, commands.CommandNotFound):
		return  # Ignore unknown commands
	
	logger.error(f"Command error in {ctx.command}: {error}")
	await ctx.reply("❌ An error occurred while processing your command.")

@bot.command(name="ask", help="Ask a question to the Notion Agent")
async def ask_notion(ctx: commands.Context, *, question: str):
	"""
	Forward a question to the Notion Agent and return the response
	Usage: !ask What are my tasks for today?
	"""
	if not question.strip():
		await ctx.reply("❓ Please provide a question to ask the Notion Agent.")
		return
	
	# Show typing indicator
	await ctx.trigger_typing()
	
	try:
		# Send query to Notion Agent
		response = await notion_client.send_query(
			query=question,
			user_id=str(ctx.author.id)
		)
		
		answer = response.get("answer", "❌ No response from Notion Agent")
		
		# Discord message limit is 2000 characters
		if len(answer) > 1900:
			answer = answer[:1900] + "…\n\n*Response truncated due to length limit*"
		
		await ctx.reply(answer)
		logger.info(f"Processed query from {ctx.author} (ID: {ctx.author.id})")
		
	except Exception as e:
		logger.error(f"Error processing ask command: {e}")
		await ctx.reply("❌ Failed to communicate with Notion Agent. Please try again later.")

@bot.command(name="health", help="Check the health of the Notion Agent")
async def health_check(ctx: commands.Context):
	"""Check if the Notion Agent is responding"""
	await ctx.trigger_typing()
	
	try:
		async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
			response = await client.get(f"{NOTION_AGENT_URL}/health")
			if response.status_code == 200:
				await ctx.reply("✅ Notion Agent is healthy and responding")
			else:
				await ctx.reply(f"⚠️ Notion Agent responded with status {response.status_code}")
	except Exception as e:
		logger.error(f"Health check failed: {e}")
		await ctx.reply("❌ Notion Agent is not responding")

@bot.command(name="help", help="Show available commands")
async def help_command(ctx: commands.Context):
	"""Show help information"""
	embed = discord.Embed(
		title="Discord -> Notion Agent Bot",
		description="Available commands:",
		color=0x0099ff
	)
	
	embed.add_field(
		name=f"{COMMAND_PREFIX}ask <question>",
		value="Ask a question to the Notion Agent",
		inline=False
	)
	embed.add_field(
		name=f"{COMMAND_PREFIX}health",
		value="Check Notion Agent health status",
		inline=False
	)
	embed.add_field(
		name=f"{COMMAND_PREFIX}help",
		value="Show this help message",
		inline=False
	)
	
	await ctx.reply(embed=embed)

if __name__ == "__main__":
	try:
		bot.run(TOKEN)
	except Exception as e:
		logger.error(f"Failed to start bot: {e}")
		exit(1) 