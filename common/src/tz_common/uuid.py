import uuid as py_uuid
import re
from typing import Optional, Union, Any
from pydantic.v1 import BaseModel, Field, validator

# Standard 8-4-4-4-12 pattern with optional hyphens
UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$', re.IGNORECASE)

# Pattern for validating fully normalized UUIDs (32 chars, no hyphens)
NORMALIZED_UUID_PATTERN = re.compile(r'^[0-9a-f]{32}$', re.IGNORECASE)


class CustomUUID(BaseModel):
	"""A custom UUID implementation that handles different UUID formats.
	The normal form of UUID has no hyphens and is lowercase."""
	
	value: str = Field(..., description="UUID value in normalized form (no hyphens, lowercase)")
	
	class Config:
		# Allow creating the model by calling the class directly with the UUID string
		arbitrary_types_allowed = True
	
	@validator('value')
	def validate_and_normalize_uuid(cls, v):
		"""Validates and normalizes the UUID value.
		Accepts formatted UUIDs with hyphens or continuous form without hyphens."""
		if not v:
			raise ValueError("UUID cannot be empty")
		
		# Normalize input
		cleaned = v.replace("-", "").lower()
		
		# Standard UUID length check
		if len(cleaned) != 32:
			raise ValueError(f"Invalid UUID length: {v}")
		
		# Verify it's a valid hex string
		if not NORMALIZED_UUID_PATTERN.match(cleaned):
			raise ValueError(f"Invalid UUID format (must be hex chars): {v}")
		
		# Return the normalized form
		return cleaned
	
	def __str__(self) -> str:
		"""Return the normalized UUID string (no hyphens, lowercase)"""
		return self.value
	
	def __eq__(self, other) -> bool:
		"""Compare UUIDs"""
		if isinstance(other, CustomUUID):
			return self.value == other.value
		elif isinstance(other, str):
			# For string comparison, normalize the input first
			clean_other = other.replace("-", "").lower()
			return self.value == clean_other
		return False
	
	def __hash__(self) -> int:
		"""Allow using UUIDs as dictionary keys"""
		return hash(self.value)
	
	@classmethod
	def __get_validators__(cls):
		yield cls.validate_custom_uuid_for_pydantic

	@classmethod
	def validate_custom_uuid_for_pydantic(cls, value: Any) -> 'CustomUUID':
		if isinstance(value, cls):
			return value
		if isinstance(value, str):
			# cls.from_string already handles validation and normalization
			return cls.from_string(value)
		raise TypeError(f'String or CustomUUID required to make a CustomUUID, got {type(value)}')
	
	@classmethod
	def uuid1(cls) -> 'CustomUUID':
		"""Generate a new UUID1 (based on host ID and current time)"""
		# Create the UUID and normalize it
		uuid_str = str(py_uuid.uuid1())
		return cls(value=uuid_str.replace("-", "").lower())
	
	@classmethod
	def from_string(cls, uuid_input: Union[str, 'CustomUUID']) -> 'CustomUUID':
		"""Create a CustomUUID from a string in any valid format or from an existing CustomUUID instance.
		
		Accepts:
		- Formatted UUIDs with hyphens (8-4-4-4-12): '1029efeb-6676-8044-88d6-c61da2eb04b9'
		- Continuous form without hyphens: '1029efeb6676804488d6c61da2eb04b9'
		- Mixed case: '1029EFEB-6676-8044-88D6-C61DA2EB04B9'
		- An existing CustomUUID object.
		
		Returns a normalized UUID (lowercase, no hyphens).
		"""
		# Use direct type check for robustness against potential isinstance issues with reloaded modules
		if type(uuid_input) is cls:
			return uuid_input 
		
		if isinstance(uuid_input, str):
			if not uuid_input: # Check after ensuring it's a string
				raise ValueError("UUID string cannot be empty")
				
			# Pre-normalize by removing hyphens and converting to lowercase
			cleaned = uuid_input.replace("-", "").lower()
			
			# Check standard length
			if len(cleaned) != 32:
				raise ValueError(f"Invalid UUID length: {uuid_input}")
			
			# Validate it's a hex string
			if not NORMALIZED_UUID_PATTERN.match(cleaned):
				raise ValueError(f"Invalid UUID format (must be hex chars): {uuid_input}")
			
			return cls(value=cleaned) # Use the constructor which will re-validate via pydantic validator
		
		raise TypeError(f"Input must be a string or CustomUUID, got {type(uuid_input)}")
	
	@classmethod
	def validate(cls, uuid_str: Any) -> bool:
		"""Validate if a string is a valid UUID"""
		if not uuid_str:
			return False
		
		if isinstance(uuid_str, int):
			return False
		
		if not isinstance(uuid_str, str):
			return False
		
		# Convert to normalized form and check length and format
		cleaned = uuid_str.replace("-", "").lower()
		if len(cleaned) == 32 and NORMALIZED_UUID_PATTERN.match(cleaned):
			return True
		
		return False
	
	def to_formatted(self) -> str:
		"""Convert to 8-4-4-4-12 format with hyphens"""
		return f"{self.value[:8]}-{self.value[8:12]}-{self.value[12:16]}-{self.value[16:20]}-{self.value[20:]}"
	
	def to_python_uuid(self) -> py_uuid.UUID:
		"""Convert to Python's UUID object (requires formatted version)"""
		return py_uuid.UUID(self.to_formatted()) 