from typing import Optional, Dict, Any, List
import json
import re

from tz_common.logs import log
from tz_common.aitoolbox import AIToolbox
from langfuse.callback import CallbackHandler
from ..blocks.blockHolder import BlockHolder, FilteringOptions


class CaptionGenerator:
	"""
	Core service responsible for generating captions using OpenAI API.
	Extracts meaningful text from blocks and generates concise captions.
	"""

	def __init__(self, block_holder: BlockHolder, langfuse_handler: Optional[CallbackHandler] = None):
		"""
		Initialize the caption generator.
		
		Args:
			block_holder: BlockHolder instance for content filtering
			langfuse_handler: Optional langfuse handler for tracking API calls
		"""
		# Create AIToolbox with shared langfuse handler
		self.ai_toolbox = AIToolbox(
			user_id="Notion Agent Caption Generator",
			langfuse_handler=langfuse_handler
		)
		self.block_holder = block_holder
		
		# Configuration
		self.model = "gpt-4o-mini"
		self.temperature = 0.0
		self.max_tokens = 50


	async def generate_caption_async(self, block_content: Dict[str, Any], block_type: str) -> Optional[str]:
		"""
		Generate a caption for a block asynchronously.
		
		Args:
			block_content: The block content dictionary
			block_type: Type of the block (page, block, database)
			
		Returns:
			Generated caption string or None if generation fails/not applicable
		"""
		try:
			# Extract meaningful text content
			text_content = self._extract_text_content(block_content)
			
			# Skip if no meaningful content
			if not text_content or len(text_content.strip()) < 3:
				log.debug(f"Skipping caption generation for {block_type}: insufficient text content")
				return None
			
			# For very short text (3 words or less), reuse it directly
			word_count = len(text_content.strip().split())
			if word_count <= 3:
				log.debug(f"Reusing short text for {block_type}: {text_content.strip()}")
				return text_content.strip()
			
			# Create prompt for caption generation
			prompt = self._create_caption_prompt(text_content, block_type)
			system_prompt = self._create_system_prompt()
			
			# Generate caption (no retries - captions are optional and disposable)
			try:
				response = self.ai_toolbox.send_openai_request(
					message=prompt,
					system_prompt=system_prompt,
					temperature=self.temperature,
					model=self.model,
					max_tokens=self.max_tokens,
					json_format=True
				)
				
				# Parse JSON response
				response_data = json.loads(response)
				caption = response_data.get("caption", "")
				
				# Clean and validate caption
				cleaned_caption = self._clean_caption(caption)
				if cleaned_caption:
					log.debug(f"Generated caption for {block_type}: {cleaned_caption}")
					return cleaned_caption
				else:
					log.debug(f"Generated empty caption for {block_type}")
					return None
					
			except Exception as e:
				log.error(f"Caption generation failed for {block_type}: {e}")
				return None
			
		except Exception as e:
			log.error(f"Caption generation failed for {block_type}: {e}")
			return None


	def _extract_text_content(self, block_content: Dict[str, Any]) -> str:
		"""
		Extract meaningful text from block content using BlockHolder filtering.
		
		Args:
			block_content: The block content dictionary
			
		Returns:
			Extracted text content as string
		"""
		try:
			# Create a copy to avoid modifying original
			content_copy = block_content.copy()
			
			# Apply minimal filtering to keep only meaningful content
			# Remove metadata, timestamps, and system fields but keep text content
			filtered_content = self.block_holder.apply_filters(
				content_copy, 
				[FilteringOptions.METADATA, FilteringOptions.TIMESTAMPS, FilteringOptions.SYSTEM_FIELDS]
			)
			
			# Extract text from various block types
			text_parts = []
			
			# Extract title (for pages/databases)
			if "title" in filtered_content:
				title_text = self._extract_rich_text(filtered_content["title"])
				if title_text:
					text_parts.append(title_text)
			
			# Extract from properties (for pages/databases)
			if "properties" in filtered_content:
				props_text = self._extract_from_properties(filtered_content["properties"])
				if props_text:
					text_parts.append(props_text)
			
			# Extract from block-specific content
			block_text = self._extract_from_block_content(filtered_content)
			if block_text:
				text_parts.append(block_text)
			
			# Extract from any remaining text fields
			remaining_text = self._extract_remaining_text(filtered_content)
			if remaining_text:
				text_parts.append(remaining_text)
			
			# Combine all text parts
			combined_text = " ".join(text_parts).strip()
			
			# Limit length to avoid very long content
			if len(combined_text) > 500:
				combined_text = combined_text[:500] + "..."
			
			return combined_text
			
		except Exception as e:
			log.error(f"Text extraction failed: {e}")
			return ""


	def _extract_rich_text(self, rich_text_array: List[Dict[str, Any]]) -> str:
		"""Extract plain text from Notion rich text array."""
		if not isinstance(rich_text_array, list):
			return ""
		
		text_parts = []
		for item in rich_text_array:
			if isinstance(item, dict) and "text" in item:
				if isinstance(item["text"], dict) and "content" in item["text"]:
					text_parts.append(item["text"]["content"])
			elif isinstance(item, dict) and "plain_text" in item:
				text_parts.append(item["plain_text"])
		
		# Join and clean up extra spaces
		combined = "".join(text_parts).strip()
		# Replace multiple spaces with single space
		return re.sub(r'\s+', ' ', combined)


	def _extract_from_properties(self, properties: Dict[str, Any]) -> str:
		"""Extract text from page/database properties."""
		text_parts = []
		
		for prop_name, prop_value in properties.items():
			if not isinstance(prop_value, dict):
				continue
			
			prop_type = prop_value.get("type", "")
			
			# Extract from different property types
			if prop_type == "title" and "title" in prop_value:
				title_text = self._extract_rich_text(prop_value["title"])
				if title_text:
					text_parts.append(title_text)
			
			elif prop_type == "rich_text" and "rich_text" in prop_value:
				rich_text = self._extract_rich_text(prop_value["rich_text"])
				if rich_text:
					text_parts.append(rich_text)
			
			elif prop_type == "select" and "select" in prop_value:
				if prop_value["select"] and "name" in prop_value["select"]:
					text_parts.append(prop_value["select"]["name"])
			
			elif prop_type == "multi_select" and "multi_select" in prop_value:
				for item in prop_value["multi_select"]:
					if isinstance(item, dict) and "name" in item:
						text_parts.append(item["name"])
		
		return " ".join(text_parts).strip()


	def _extract_from_block_content(self, content: Dict[str, Any]) -> str:
		"""Extract text from block-specific content fields."""
		text_parts = []
		block_type = content.get("type", "")
		
		# Extract based on block type
		if block_type in content:
			block_data = content[block_type]
			if isinstance(block_data, dict):
				
				# Rich text blocks (paragraph, heading, etc.)
				if "rich_text" in block_data:
					rich_text = self._extract_rich_text(block_data["rich_text"])
					if rich_text:
						text_parts.append(rich_text)
				
				# Code blocks
				elif "code" in block_data and isinstance(block_data["code"], dict):
					if "rich_text" in block_data["code"]:
						code_text = self._extract_rich_text(block_data["code"]["rich_text"])
						if code_text:
							text_parts.append(f"Code: {code_text[:100]}")
				
				# Quote blocks
				elif "quote" in block_data and isinstance(block_data["quote"], dict):
					if "rich_text" in block_data["quote"]:
						quote_text = self._extract_rich_text(block_data["quote"]["rich_text"])
						if quote_text:
							text_parts.append(f"Quote: {quote_text}")
				
				# Callout blocks
				elif "callout" in block_data and isinstance(block_data["callout"], dict):
					if "rich_text" in block_data["callout"]:
						callout_text = self._extract_rich_text(block_data["callout"]["rich_text"])
						if callout_text:
							text_parts.append(callout_text)
		
		return " ".join(text_parts).strip()


	def _extract_remaining_text(self, content: Dict[str, Any]) -> str:
		"""Extract any remaining text from other fields."""
		text_parts = []
		
		# Look for common text fields
		text_fields = ["content", "text", "description", "name"]
		
		for field in text_fields:
			if field in content:
				value = content[field]
				if isinstance(value, str) and value.strip():
					text_parts.append(value.strip())
				elif isinstance(value, list):
					# Handle rich text arrays
					rich_text = self._extract_rich_text(value)
					if rich_text:
						text_parts.append(rich_text)
		
		return " ".join(text_parts).strip()


	def _create_caption_prompt(self, text_content: str, block_type: str) -> str:
		"""
		Create an optimized prompt for caption generation.
		
		Args:
			text_content: Extracted text content
			block_type: Type of the block
			
		Returns:
			Formatted prompt string
		"""
		return f"""Generate a very short caption (1-5 words max) for this {block_type} content:

{text_content}

The caption should be:
- Extremely concise (1-5 words maximum)
- Descriptive of the main topic or purpose
- Suitable as a brief label for tree navigation
- Professional and clear

Examples:
- "Meeting Notes" for meeting content
- "Project Plan" for planning content  
- "Code Snippet" for code blocks
- "Task List" for todo items

Return your response as JSON with this format:
{{"caption": "your caption here"}}"""


	def _create_system_prompt(self) -> str:
		"""Create the system prompt for caption generation."""
		return """You are a helpful assistant that creates very short, descriptive captions for content blocks. 

Your captions should be:
- Extremely brief (1-5 words maximum)
- Descriptive and meaningful
- Suitable as labels for content navigation
- Professional and clear
- No quotes or unnecessary punctuation

Focus on the main topic, purpose, or type of content. Always respond with valid JSON."""


	def _clean_caption(self, caption: str) -> Optional[str]:
		"""
		Clean and validate the generated caption.
		
		Args:
			caption: Raw caption from AI
			
		Returns:
			Cleaned caption or None if invalid
		"""
		if not caption:
			return None
		
		# Clean the caption
		cleaned = caption.strip()
		
		# Remove quotes if present
		if cleaned.startswith('"') and cleaned.endswith('"'):
			cleaned = cleaned[1:-1].strip()
		if cleaned.startswith("'") and cleaned.endswith("'"):
			cleaned = cleaned[1:-1].strip()
		
		# Remove trailing punctuation
		while cleaned and cleaned[-1] in '.!?:;,':
			cleaned = cleaned[:-1].strip()
		
		# Validate length (should be short)
		if len(cleaned) > 50:  # Too long
			return None
		
		if len(cleaned) < 1:  # Too short
			return None
		
		# Check for reasonable content (not just special characters)
		if not any(c.isalnum() for c in cleaned):
			return None
		
		return cleaned 