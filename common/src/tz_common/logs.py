import os
import time
from pathlib import Path
from termcolor import colored
import logging
from datetime import datetime
import string
from enum import IntEnum

# TODO: Add warn level?

class LogLevel(IntEnum):
	FLOW = 5
	DEBUG = 10
	COMMON = 15
	USER = 20
	AI = 25
	KNOWLEDGE = 30
	ERROR = 35

LEVEL_COLORS = {
	LogLevel.FLOW: 'yellow',
	LogLevel.DEBUG: 'magenta',
	LogLevel.COMMON: 'white',
	LogLevel.USER: 'green',
	LogLevel.AI: 'light_blue',
	LogLevel.KNOWLEDGE: 'blue',
	LogLevel.ERROR: 'red'
}

class Log:
	def __init__(self, log_dir: str = 'logs'):
		# Create logs directory if it doesn't exist
		if not os.path.exists(log_dir):
			os.makedirs(log_dir)

		self.logger = logging.getLogger('CustomLogger')
		self.logger.propagate = False  # Do not log to default logger
		self.set_log_level(LogLevel.DEBUG)
		
		self.log_filename = f'{log_dir}/{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
		self.file_handler = logging.FileHandler(self.log_filename)
		self.file_handler.setLevel(logging.DEBUG)
		formatter = logging.Formatter('%(asctime)s - %(levelname)-10s - %(message)s')
		self.file_handler.setFormatter(formatter)
		self.logger.handlers.clear() 
		self.logger.addHandler(self.file_handler)

		# Add custom levels to the logger
		for level in LogLevel:
			logging.addLevelName(level.value, level.name)

	def _filter_printable(self, text: str) -> str:
		return ''.join(char for char in str(text) if self._is_valid_char(char))

	def _is_valid_char(self, char: str) -> bool:
		# TODO: Handle other languages
		return (char.isprintable() and ord(char) < 128) or char in 'ąćęłńóśźżĄĆĘŁŃÓŚŹŻ\n\t'

	def _filter_printable_pair(self, colored_text: str, plaintext: str) -> tuple[str, str]:
		return self._filter_printable(str(colored_text)), self._filter_printable(str(plaintext))

	def _print_log(self, colored_text: str, plaintext: str, level: LogLevel):
		colored_text = self._filter_printable(colored_text)
		plaintext = self._filter_printable(plaintext)
		self.logger.log(level.value, colored_text + plaintext)
		
		if self.logger.level <= level.value:
			color = LEVEL_COLORS[level]
			print(colored(colored_text, color) + plaintext)

	def user_silent(self, colored_text: str):
		"""
		User input or request. # TODO: Explain what's for?
		"""
		colored_text = self._filter_printable(colored_text)
		self.logger.log(LogLevel.USER.value, colored_text)
		return str(colored_text)

	def user(self, colored_text: str, plaintext: str = ""):
		"""
		User input or request.
		"""
		self._print_log(colored_text, plaintext, LogLevel.USER)
		return str(colored_text) + str(plaintext)

	def error(self, colored_text: str, plaintext: str = ""):
		self._print_log(colored_text, plaintext, LogLevel.ERROR)
		return str(colored_text) + str(plaintext)

	def knowledge(self, colored_text: str, plaintext: str = ""):
		"""
		Used for internal AI knowlege, permanent or temporary
		"""
		self._print_log(colored_text, plaintext, LogLevel.KNOWLEDGE)
		return str(colored_text) + str(plaintext)
	
	def ai(self, colored_text: str, plaintext: str = ""):
		"""
		Reply from chatbots to user. User can be another AI or human.
		"""
		self._print_log(colored_text, plaintext, LogLevel.AI)
		return str(colored_text) + str(plaintext)
	
	def flow(self, colored_text: str, plaintext: str = ""):
		"""
		Flow of the program, main steps and actions. Entering new functions or graph states.
		"""
		self._print_log(colored_text, plaintext, LogLevel.FLOW)
		return str(colored_text) + str(plaintext)
	
	def debug(self, colored_text: str, plaintext: str = ""):
		self._print_log(colored_text, plaintext, LogLevel.DEBUG)
		return str(colored_text) + str(plaintext)
	
	def common(self, colored_text: str, plaintext: str = ""):
		"""
		Large blocks of text, for instance web page content or config files.
		"""
		self._print_log(colored_text, plaintext, LogLevel.COMMON)
		return str(colored_text) + str(plaintext)


	def __del__(self):
		self._remove_old_log_files()

	def _remove_old_log_files(self):
		current_time = time.time()
		ninety_days_in_seconds = 90 * 24 * 60 * 60
		log_directory = Path(self.log_filename).parent

		for file in log_directory.glob('*.log'):
			file_age = current_time - os.path.getmtime(file)
			if file_age > ninety_days_in_seconds:
				try:
					os.remove(file)
				except Exception as e:
					print(f"Error removing old log file {file}: {e}")

	def set_log_level(self, level: LogLevel):
		self.logger.setLevel(level.value)


	def set_file_log_level(self, level: LogLevel):
		"""Set the minimum log level for file output separately from console output"""
		self.file_handler.setLevel(level.value)


log = Log()
