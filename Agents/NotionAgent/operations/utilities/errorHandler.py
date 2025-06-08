from typing import Dict, Any


class ErrorHandler:
	"""
	Utility class for handling and formatting errors from Notion API responses.
	Centralizes error processing logic for consistent error handling across the system.
	"""

	@staticmethod
	def format_http_error(status_code: int, response_data: Dict[str, Any]) -> str:
		"""
		Format HTTP error responses into user-friendly error messages.
		
		Args:
			status_code: HTTP status code from the response
			response_data: Response data dictionary from the API
			
		Returns:
			Formatted error message string
		"""
		cleaned_data = ErrorHandler.clean_error_message(response_data.copy())
		message = cleaned_data.get('message', 'Unknown error')
		return f"HTTP {status_code}: {message}"


	@staticmethod
	def clean_error_message(message: Dict[str, Any]) -> Dict[str, Any]:
		"""
		Clean error messages from Notion API responses by removing unnecessary fields.
		
		Args:
			message: Error response dictionary from Notion API
			
		Returns:
			Cleaned error message dictionary
		"""
		# Create a copy to avoid modifying the original
		cleaned_message = message.copy()
		
		# Remove standard Notion API metadata fields that aren't useful for error display
		fields_to_remove = ["object", "request_id"]
		
		for field in fields_to_remove:
			if field in cleaned_message:
				del cleaned_message[field]

		return cleaned_message


	@staticmethod
	def extract_error_details(response_data: Dict[str, Any]) -> Dict[str, Any]:
		"""
		Extract relevant error details from Notion API error responses.
		
		Args:
			response_data: Full error response from Notion API
			
		Returns:
			Dictionary containing extracted error details
		"""
		details = {}
		
		# Extract common error fields
		if 'code' in response_data:
			details['code'] = response_data['code']
		
		if 'message' in response_data:
			details['message'] = response_data['message']
		
		return details
 