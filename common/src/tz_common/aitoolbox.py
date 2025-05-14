import os
import time
import asyncio
from typing import Optional

from dotenv import load_dotenv

# FIXME: Use llamaparse or drop it
#from llama_parse import LlamaParse
#from llama_index.core import SimpleDirectoryReader, Document
#from llama_index.readers.pdf_marker import PDFMarkerReader

from langfuse.decorators import observe, langfuse_context
from langfuse.openai import openai

from tz_common import log

class AIToolbox:

	def __init__(self, user_id="test", session_id=None):

		load_dotenv(override=True)

		self.openai_api_key = os.getenv("OPENAI_API_KEY")

		self.user_id = user_id

		if session_id is None:
			self.session_id = time.strftime("%Y-%m-%d_%H-%M-%S")

		# TODO: Set once globally
		"""
		langfuse_context.update_current_trace(
			session_id=self.session_id,
			user_id=self.user_id
		)
		"""


	# TODO: Opcjonalna wersja observe przełączana flagą
	@observe()
	def send_openai_request(self, message: str, system_prompt: str = None, temperature: float = 0.0, model: str = "gpt-4o-mini", json_format: bool = False, max_tokens: int = 1024) -> str:

		langfuse_context.update_current_trace(
			session_id=self.session_id,
			user_id=self.user_id
		)
		messages=[]

		if system_prompt is not None:
			messages.append({"role": "system", "content": system_prompt})

		messages.append({"role": "user", "content": message})

		#TODO: handle possible errors in communication

		return openai.chat.completions.create(
			model=model, 
			messages=messages,
			temperature=temperature,
			max_tokens=max_tokens,
			response_format={"type": "json_object"} if json_format else None
		).choices[0].message.content


	@observe()
	async def send_openai_requests(self, messages: dict[str, str], system_prompt: str = None, temperature: float = 0.0, model: str = "gpt-4o-mini", json_format: bool = False) -> dict[str, str]:

		langfuse_context.update_current_trace(
			session_id=self.session_id,
			user_id=self.user_id
		)

		body = {
			"role": "system",
			"content": system_prompt
		} if system_prompt is not None else {}

		@observe()
		async def get_completion(name: str, message: str) -> tuple[str, str]:
			response = await asyncio.to_thread(openai.chat.completions.create,
				model=model,
				messages=[
					body,
					{
						"role": "user", 
						"content": message
					}
				] if body else [
					{
						"role": "user", 
						"content": message
					}
				],
				temperature=temperature,
				max_tokens=1024,
				response_format={"type": "json_object"} if json_format else None
			)
			return (name, response.choices[0].message.content)

		tasks = [get_completion(name, message) for name, message in messages.items()]
		results = await asyncio.gather(*tasks)
		return dict(results)


	@observe(capture_input=False)
	def send_openai_request_with_image(self, image: str | list[str], prompt: str) -> str:
		
		langfuse_context.update_current_trace(
			session_id=self.session_id,
			user_id=self.user_id
		)

		content = [
					{
						"type": "text",
						"text": prompt
					}
		]
		
		# Ensure base64 string starts with data URI scheme
		if isinstance(image, list):
			for img in image:
				if not img.startswith('data:image/'):
					img_content = f"data:image/jpeg;base64,{img}"
				else:
					img_content = img
				content.append({
					"type": "image_url",
					"image_url": {
						"url": img_content
					}
				})
		else:
			img_content = f"data:image/jpeg;base64,{image}" if not image.startswith('data:image/') else image
			content.append({
				"type": "image_url",
				"image_url": {
					"url": img_content
				}
			})

		response = openai.chat.completions.create(
			#model="gpt-4o-mini",
			model="gpt-4o",
			temperature=0.0,
			messages=[
				{
					"role": "user", 
					"content": content
				}
			],
			max_tokens=1024
		)
		log.ai("OpenAI response:", response.choices[0].message.content)

		return response.choices[0].message.content

	# FIXME: Change interface so "await" is not needed outside this function

	# Dict is not serializable
	@observe(capture_input=False, capture_output=False)
	async def get_images_descriptions(self, images: dict[str, str], prompt: str | dict[str, str]) -> dict[str, str]:

		# TODO: variant which accepts simple list of images
		log.debug(f"Getting descriptions for images:", prompt)

		langfuse_context.update_current_trace(
			session_id=self.session_id,
			user_id=self.user_id
		)

		@observe()
		async def get_description(name: str, image: str, unique_prompt: str = None) -> tuple[str, str]:
			description = await asyncio.to_thread(self.send_openai_request_with_image, image, unique_prompt if unique_prompt else prompt)
			return (name, description)
		
		# Create list of coroutines, each returning (name, description) tuple
		tasks = []
		if isinstance(prompt, str):
			tasks = [get_description(name, image) for name, image in images.items()]
		else:
			if len(prompt) != len(images):
				log.error("Number of prompts and images does not match")
				return{}
			if isinstance(prompt, dict):
				for name, image in images.items():
					tasks.append(get_description(name, image, prompt[name]))

		# Gather results and convert list of tuples to dictionary
		results = await asyncio.gather(*tasks)
		return dict(results)

	# FIXME: LangFuse doesn't track image generation cost
	# TODO: Should do since 3.0 version
	@observe()
	def generate_image(self, prompt: str,
						size: str = "1024x1024",
						model: str = "dall-e-3",
						n: int = 1,
						save_path: str = None,
						api_key: Optional[str] = None) -> Optional[str]:

		# TODO: Consider using different API providers

		langfuse_context.update_current_trace(
			session_id=self.session_id,
			user_id=self.user_id
		)
		
		headers = {
			"Authorization": f"Bearer {self.openai_api_key}",
			"Content-Type": "application/json"
		}
		
		payload = {
			"model": model,
			"prompt": prompt,
			"n": n,
			"size": size,
			"response_format": "url"
		}
		
		api_response = requests.post(
			"https://api.openai.com/v1/images/generations",
			headers=headers,
			json=payload
		)

		# 1 dall-e-3 prompt -> 0.04 USD
		
		if api_response.status_code != 200:
			log.error(f"Failed to generate image: {api_response.status_code}")
			log.common(api_response.text)
			return None
			
		image_url = api_response.json()["data"][0]["url"]
		log.flow(f"Generated image URL:", image_url)
		
		# Download and save image only if save_path is provided
		if save_path is not None:

			if save_path == "":
				timestamp = int(time.time())
				save_path = f"{model}_{timestamp}.png"

			# Download the image
			image_response = requests.get(image_url)
			
			if image_response.status_code != 200:
				log.error(f"Failed to download image: {image_response.status_code}")
				return None

			with open(save_path, "wb") as f:
				f.write(image_response.content)
			
			log.flow(f"Image saved as ", save_path)

		return image_url


	@observe()
	async def transcribe_audio(self, audio_files: dict[str, bytes]) -> dict[str, str]:

		log.debug(f"Transcribing audio files")

		langfuse_context.update_current_trace(
			session_id=self.session_id,
			user_id=self.user_id
		)

		@observe()
		async def get_transcription(name: str, audio: bytes) -> tuple[str, str]:
			transcription = await asyncio.to_thread(
				openai.audio.transcriptions.create,
				model="whisper-1",
				file=audio
			)
			log.ai(f"Transcribed {name}:", transcription.text)
			return (name, transcription.text)

		# Create list of coroutines, each returning (name, transcription) tuple 
		tasks = [get_transcription(name, audio) for name, audio in audio_files.items()]
		# Gather results and convert list of tuples to dictionary
		results = await asyncio.gather(*tasks)
		return dict(results)

	@observe(capture_output=False)
	def get_embedding(self, text: str, model: str = "text-embedding-3-large") -> list[float]:

		langfuse_context.update_current_trace(
			session_id=self.session_id,
			user_id=self.user_id
		)

		response = openai.embeddings.create(input=text, model=model)
		return response.data[0].embedding
	
	# TODO: Try text-embedding-ada-002

	@observe(capture_input=False, capture_output=False)
	async def get_embeddings(self, texts: dict[str, str], model: str = "text-embedding-3-large", max_concurrent: int = 16) -> dict[str, list[float]]:

		langfuse_context.update_current_trace(
			session_id=self.session_id,
			user_id=self.user_id
		)

		semaphore = asyncio.Semaphore(max_concurrent)

		async def get_embedding_task(name: str, text: str) -> tuple[str, list[float]]:
			async with semaphore:
				embedding = await asyncio.to_thread(self.get_embedding, text, model)
				return (name, embedding)

		tasks = [get_embedding_task(name, text) for name, text in texts.items()]
		results = await asyncio.gather(*tasks)
		return dict(results)


	def get_openai_api_key(self) -> str:
		
		if not self.openai_api_key:
			log.error("OpenAI API key not found in environment variables")
			raise ValueError("OpenAI API key not found in environment variables")

		return self.openai_api_key


	def split_paragraphs(self, text: str | list[str], chunk_length: int = 1000) -> list[str]:

		"""Split text into paragraphs based on double newlines.

		Args:
			text (str): Input text to split

		Returns:
			list[str]: List of paragraphs
		"""
		# Split on double newlines and filter out empty strings
		paragraphs = []
		if isinstance(text, str):
			paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
		else:
			paragraphs = [p.strip() for p in text if p.strip()]
		
		# Join consecutive paragraphs until they exceed chunk length
		joined = []
		current = ""
		
		for p in paragraphs:
			if len(current) + len(p) < chunk_length:
				current = current + "\n\n" + p if current else p
			else:
				joined.append(current)
				current = p
				
		if current:
			joined.append(current)
			
		return joined

"""

	@observe(capture_output=False)
	def convert_to_markdown(self, path: str | list[str], langs : list[str]= None) -> list[Document]:

		parser = LlamaParse(
			result_type="markdown"  # "markdown" and "text" are available
		)
		input_files = [path] if isinstance(path, str) else path

		# TODO: Handle other file types

		# SimpleDirectoryReader
		# https://docs.llamaindex.ai/en/stable/module_guides/loading/simpledirectoryreader/#simpledirectoryreader

		file_extractor = {".pdf": parser}

		documents = SimpleDirectoryReader(input_files=input_files, file_extractor=file_extractor).load_data()

		reader = PDFMarkerReader()
		if langs is not None:
			documents = reader.load_data(file = path, langs = langs)
		else:
			documents = reader.load_data(file = path)

		# TODO: What does it return?
		return documents

"""
