import os
import io
import base64
from typing import Optional, Callable
from PIL import Image # TODO: Install pillow
import requests

from tz_common import log

class TZUtils:

	# TODO: Set working directory

	def resize_image(self, image_data: bytes) -> bytes:
			
		img = Image.open(io.BytesIO(image_data))
		
		# Convert to RGB mode if image is in palette mode
		if img.mode in ('RGBA', 'P'):
			img = img.convert('RGB')
		
		# Calculate resize ratio to get max dimension of 1024
		width, height = img.size
		max_dim = max(width, height)
		if max_dim > 1024:
			ratio = 1024 / max_dim
			new_size = (int(width * ratio), int(height * ratio))
			img = img.resize(new_size, Image.Resampling.LANCZOS)
		
		# Convert back to bytes
		img_byte_arr = io.BytesIO()
		img.save(img_byte_arr, format='JPEG')
		return img_byte_arr.getvalue()


	def load_images(self, files : list[str], image_dir: Optional[str] = None) -> dict[str, str]:

		if image_dir is not None:
			# Get all images in directory
			files = os.listdir(image_dir)
			# Add full path to filenames
			files = [os.path.join(image_dir, f) for f in files]

		images = {}
		
		for filepath in files:
			if filepath.lower().endswith((".jpg", ".png")):
				with open(filepath, "rb") as f:
					image_data = f.read()
					filename = os.path.basename(filepath)
					images[filename] = self.resize_image(image_data)
					
		log.debug(f"Found {len(images)} images in {image_dir}")
		
		# Create dictionary with encoded images
		encoded_images = {}
		for name, image_data in images.items():
			encoded = base64.b64encode(image_data).decode('utf-8')
			encoded_images[name] = encoded
				
		return encoded_images
	
	# TODO: Move debug utils to separate class
	# TODO: How about Marimo
	# TODO: How about GUI?
	def show_images(self, images: dict[str, str]):

		# Display images in a grid window
		import tkinter as tk
		from PIL import Image, ImageTk
		import io
		import base64
		import math

		# Create main window
		root = tk.Tk()
		root.title("Images")

		# Calculate grid dimensions
		num_images = len(images)
		grid_size = math.ceil(math.sqrt(num_images))
		
		# Create and display images
		for idx, (filename, img_data) in enumerate(images.items()):

			# TODO: Handle case when image is not base64 encoded
			# Convert base64 to bytes then to PIL Image
			img_bytes = base64.b64decode(img_data)
			img = Image.open(io.BytesIO(img_bytes))
			
			# Resize for display
			img.thumbnail((300, 300))
			
			# Convert to PhotoImage
			photo = ImageTk.PhotoImage(img)
			
			# Create label with image
			label = tk.Label(root, image=photo)
			label.image = photo  # Keep reference
			
			# Calculate grid position
			row = idx // grid_size
			col = idx % grid_size
			label.grid(row=row, column=col, padx=5, pady=5)
			
			# Add filename label
			name_label = tk.Label(root, text=filename)
			name_label.grid(row=row+1, column=col)

		root.mainloop()
	

	def download_url(self, url: str, directory_path: str) -> str:

		response = requests.get(url)

		if response.status_code != 200:
			log.error(f"Failed to download URL {url}: {response.status_code}", response.text)
			return None
		else:
			log.debug(f"Downloaded URL: {url}")

		filename = os.path.join(directory_path, url.split("/")[-1])
		with open(filename, "wb") as f:
			f.write(response.content)

		return response.content
	

	def execute_once(self, func: Callable, filename: str) -> any:
		"""
		Execute a function only once and store the result in a file.
		"""

		if os.path.exists(filename):
			with open(filename, "r") as f:
				return f.read()
			
		else:
			result = func()
			with open(filename, "w") as f:
				f.write(str(result))

		return result

