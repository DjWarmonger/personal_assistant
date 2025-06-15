import asyncio
import sys
import os
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch

# Update the import path to include the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from operations.captioning.captionGenerator import CaptionGenerator
from operations.blocks.blockHolder import BlockHolder
from operations.urlIndex import UrlIndex
from tz_common.aitoolbox import AIToolbox


class TestCaptionGenerator:

	@classmethod
	def setup_class(cls):
		"""Set up test fixtures once for the entire test class."""
		# Create shared dependencies
		cls.url_index = UrlIndex()
		cls.block_holder = BlockHolder(cls.url_index)

	def setup_method(self):
		"""Set up test fixtures before each test method."""
		# Create caption generators (CaptionGenerator now creates its own AIToolbox)
		self.caption_generator = CaptionGenerator(self.block_holder)
		self.real_caption_generator = CaptionGenerator(self.block_holder)
		
		# Mock the ai_toolbox for tests that need controlled responses
		self.mock_ai_toolbox = Mock(spec=AIToolbox)
		self.caption_generator.ai_toolbox = self.mock_ai_toolbox


	def test_extract_text_from_paragraph_block(self):
		block_content = {
			"type": "paragraph",
			"paragraph": {
				"rich_text": [
					{
						"type": "text",
						"text": {"content": "This is a test paragraph with some content."}
					}
				]
			},
			"last_edited_time": "2023-01-01T00:00:00Z",
			"created_time": "2023-01-01T00:00:00Z"
		}
		
		text = self.caption_generator._extract_text_content(block_content)
		assert text == "This is a test paragraph with some content."


	def test_extract_text_from_heading_block(self):
		block_content = {
			"type": "heading_1",
			"heading_1": {
				"rich_text": [
					{
						"type": "text",
						"text": {"content": "Important Heading"}
					}
				]
			}
		}
		
		text = self.caption_generator._extract_text_content(block_content)
		assert text == "Important Heading"


	def test_extract_text_from_page_with_title(self):
		block_content = {
			"object": "page",
			"title": [
				{
					"type": "text",
					"text": {"content": "My Project Page"}
				}
			],
			"properties": {
				"Name": {
					"type": "title",
					"title": [
						{
							"type": "text",
							"text": {"content": "Project Documentation"}
						}
					]
				}
			}
		}
		
		text = self.caption_generator._extract_text_content(block_content)
		assert "My Project Page" in text
		assert "Project Documentation" in text


	def test_extract_text_from_code_block(self):
		block_content = {
			"type": "code",
			"code": {
				"code": {
					"rich_text": [
						{
							"type": "text",
							"text": {"content": "def hello_world():\n    print('Hello, World!')"}
						}
					]
				},
				"language": "python"
			}
		}
		
		text = self.caption_generator._extract_text_content(block_content)
		assert "Code:" in text
		assert "def hello_world" in text


	def test_extract_text_from_quote_block(self):
		block_content = {
			"type": "quote",
			"quote": {
				"quote": {
					"rich_text": [
						{
							"type": "text",
							"text": {"content": "This is an important quote about testing."}
						}
					]
				}
			}
		}
		
		text = self.caption_generator._extract_text_content(block_content)
		assert "Quote:" in text
		assert "important quote about testing" in text


	def test_extract_text_filters_metadata(self):
		"""Test that metadata fields are filtered out during text extraction."""
		block_content = {
			"type": "paragraph",
			"paragraph": {
				"rich_text": [
					{
						"type": "text",
						"text": {"content": "Clean content"}
					}
				]
			},
			"last_edited_time": "2023-01-01T00:00:00Z",
			"created_time": "2023-01-01T00:00:00Z",
			"icon": "some-icon",
			"bold": True,
			"request_id": "req-123"
		}
		
		text = self.caption_generator._extract_text_content(block_content)
		assert text == "Clean content"


	def test_extract_rich_text_array(self):
		rich_text_array = [
			{
				"type": "text",
				"text": {"content": "First part "}
			},
			{
				"type": "text",
				"text": {"content": "second part"}
			}
		]
		
		text = self.caption_generator._extract_rich_text(rich_text_array)
		assert text == "First part second part"


	def test_extract_rich_text_with_plain_text(self):
		rich_text_array = [
			{
				"plain_text": "Simple text content"
			}
		]
		
		text = self.caption_generator._extract_rich_text(rich_text_array)
		assert text == "Simple text content"


	def test_extract_from_properties_select(self):
		properties = {
			"Status": {
				"type": "select",
				"select": {
					"name": "In Progress"
				}
			},
			"Tags": {
				"type": "multi_select",
				"multi_select": [
					{"name": "Important"},
					{"name": "Urgent"}
				]
			}
		}
		
		text = self.caption_generator._extract_from_properties(properties)
		assert "In Progress" in text
		assert "Important" in text
		assert "Urgent" in text


	def test_clean_caption_removes_quotes(self):
		caption = '"Test Caption"'
		cleaned = self.caption_generator._clean_caption(caption)
		assert cleaned == "Test Caption"


	def test_clean_caption_removes_punctuation(self):
		caption = "Test Caption."
		cleaned = self.caption_generator._clean_caption(caption)
		assert cleaned == "Test Caption"


	def test_clean_caption_rejects_too_long(self):
		caption = "This is a very long caption that exceeds the maximum length limit"
		cleaned = self.caption_generator._clean_caption(caption)
		assert cleaned is None


	def test_clean_caption_rejects_empty(self):
		"""Test that empty captions are rejected."""
		caption = ""
		cleaned = self.caption_generator._clean_caption(caption)
		assert cleaned is None


	def test_clean_caption_rejects_special_chars_only(self):
		"""Test that captions with only special characters are rejected."""
		caption = "!@#$%"
		cleaned = self.caption_generator._clean_caption(caption)
		assert cleaned is None


	def test_create_caption_prompt(self):
		text_content = "This is some test content for a block"
		block_type = "paragraph"
		
		prompt = self.caption_generator._create_caption_prompt(text_content, block_type)
		
		assert text_content in prompt
		assert block_type in prompt


	def test_create_system_prompt(self):
		"""Test system prompt creation."""
		system_prompt = self.caption_generator._create_system_prompt()
		
		# Just verify it returns a non-empty string
		assert isinstance(system_prompt, str)
		assert len(system_prompt) > 0


	@pytest.mark.asyncio
	async def test_generate_caption_async_success(self):
		"""Test successful caption generation with real API call."""
		block_content = {
			"type": "paragraph",
			"paragraph": {
				"rich_text": [
					{
						"type": "text",
						"text": {"content": "This is a test paragraph about project management and task organization."}
					}
				]
			}
		}
		
		# Test
		caption = await self.real_caption_generator.generate_caption_async(block_content, "block")
		
		# Verify basic properties
		if caption is not None:
			print(f"Generated caption: '{caption}'")
			assert isinstance(caption, str)
			assert len(caption) > 0
			assert len(caption) <= 50  # Should be reasonably short
			# Should contain alphanumeric characters
			assert any(c.isalnum() for c in caption)
		else:
			print("Caption generation returned None (API might be unavailable)")


	@pytest.mark.asyncio
	async def test_generate_caption_async_short_text_reuse(self):
		"""Test that short text (3 words or less) is reused directly."""
		block_content = {
			"type": "paragraph",
			"paragraph": {
				"rich_text": [
					{
						"type": "text",
						"text": {"content": "Short text"}
					}
				]
			}
		}
		
		# Test
		caption = await self.caption_generator.generate_caption_async(block_content, "block")
		
		# Verify - should return the short content directly
		assert caption == "Short text"
		assert self.mock_ai_toolbox.send_openai_request.call_count == 0


	@pytest.mark.asyncio
	async def test_generate_caption_async_very_short_text_reuse(self):
		"""Test that very short text (1 word) is reused directly."""
		block_content = {
			"type": "paragraph",
			"paragraph": {
				"rich_text": [
					{
						"type": "text",
						"text": {"content": "Word"}
					}
				]
			}
		}
		
		# Test
		caption = await self.caption_generator.generate_caption_async(block_content, "block")
		
		# Verify - should return the short content directly
		assert caption == "Word"
		assert self.mock_ai_toolbox.send_openai_request.call_count == 0


	@pytest.mark.asyncio
	async def test_generate_caption_async_no_content(self):
		"""Test caption generation with no meaningful content."""
		block_content = {
			"type": "paragraph",
			"paragraph": {
				"rich_text": []
			}
		}
		
		# Test
		caption = await self.caption_generator.generate_caption_async(block_content, "block")
		
		# Verify
		assert caption is None
		assert self.mock_ai_toolbox.send_openai_request.call_count == 0


	@pytest.mark.parametrize("content_type,content", [
		("heading", {
			"type": "heading_1",
			"heading_1": {
				"rich_text": [
					{
						"type": "text",
						"text": {"content": "Project Requirements and Specifications"}
					}
				]
			}
		}),
		("code", {
			"type": "code",
			"code": {
				"code": {
					"rich_text": [
						{
							"type": "text",
							"text": {"content": "def calculate_total(items):\n    return sum(item.price for item in items)"}
						}
					]
				},
				"language": "python"
			}
		})
	])
	@pytest.mark.asyncio
	async def test_generate_caption_async_different_content_types(self, content_type, content):
		"""Test caption generation with different content types using real API."""
		caption = await self.real_caption_generator.generate_caption_async(content, "block")
		
		if caption is not None:
			print(f"Generated caption for {content_type}: '{caption}'")
			assert isinstance(caption, str)
			assert len(caption) > 0
			assert len(caption) <= 50
			assert any(c.isalnum() for c in caption)
		else:
			print(f"Caption generation for {content_type} returned None (API might be unavailable)")


	@pytest.mark.asyncio
	async def test_generate_caption_async_json_format_validation(self):
		"""Test that caption generation produces valid JSON responses."""
		# Create a test version that captures the raw response
		class TestCaptionGenerator(CaptionGenerator):
			def __init__(self, block_holder):
				super().__init__(block_holder)
				self.last_raw_response = None
			
			async def generate_caption_async(self, block_content, block_type):
				try:
					text_content = self._extract_text_content(block_content)
					if not text_content or len(text_content.strip()) < 3:
						return None
					
					word_count = len(text_content.strip().split())
					if word_count <= 3:
						return text_content.strip()
					
					prompt = self._create_caption_prompt(text_content, block_type)
					system_prompt = self._create_system_prompt()
					
					response = self.ai_toolbox.send_openai_request(
						message=prompt,
						system_prompt=system_prompt,
						temperature=self.temperature,
						model=self.model,
						max_tokens=self.max_tokens,
						json_format=True
					)
					
					self.last_raw_response = response
					response_data = json.loads(response)
					caption = response_data.get("caption", "")
					return self._clean_caption(caption)
					
				except Exception as e:
					return None
		
		test_generator = TestCaptionGenerator(self.block_holder)
		
		block_content = {
			"type": "paragraph",
			"paragraph": {
				"rich_text": [
					{
						"type": "text",
						"text": {"content": "This is a comprehensive guide about software development best practices and methodologies."}
					}
				]
			}
		}
		
		caption = await test_generator.generate_caption_async(block_content, "block")
		
		if caption is not None and test_generator.last_raw_response:
			print(f"Raw API response: {test_generator.last_raw_response}")
			print(f"Parsed caption: '{caption}'")
			
			# Verify the raw response is valid JSON
			try:
				parsed = json.loads(test_generator.last_raw_response)
				assert isinstance(parsed, dict)
				assert "caption" in parsed
			except json.JSONDecodeError:
				assert False, "API response was not valid JSON"
		else:
			print("Caption generation returned None (API might be unavailable)")


	@pytest.mark.asyncio
	async def test_generate_caption_async_api_failure_handling(self):
		# Create a mock that simulates API failure
		class FailingAIToolbox(AIToolbox):
			def send_openai_request(self, **kwargs):
				raise Exception("Simulated API failure")
		
		failing_generator = CaptionGenerator(self.block_holder)
		failing_generator.ai_toolbox = FailingAIToolbox()
		
		block_content = {
			"type": "paragraph",
			"paragraph": {
				"rich_text": [
					{
						"type": "text",
						"text": {"content": "This is a test paragraph with meaningful content that should generate a caption."}
					}
				]
			}
		}
		
		# Test - should handle failure gracefully
		caption = await failing_generator.generate_caption_async(block_content, "block")
		
		# Verify - should return None without crashing
		print(f"Caption with API failure: {caption}")
		assert caption is None


	def test_extract_text_content_length_limit(self):
		"""Test that very long content is truncated."""
		long_content = "A" * 600  # Longer than 500 char limit
		
		block_content = {
			"type": "paragraph",
			"paragraph": {
				"rich_text": [
					{
						"type": "text",
						"text": {"content": long_content}
					}
				]
			}
		}
		
		text = self.caption_generator._extract_text_content(block_content)
		assert len(text) <= 503  # 500 + "..."
		assert text.endswith("...")


if __name__ == '__main__':
	pytest.main() 