import pytest

from operations.utilities.errorHandler import ErrorHandler


class TestErrorHandler:
	"""Test suite for ErrorHandler utility class."""

	def test_format_http_error_basic(self):
		"""Test format_http_error with basic error response."""
		status_code = 404
		response_data = {
			"object": "error",
			"status": 404,
			"code": "object_not_found",
			"message": "Could not find page with ID: 123",
			"request_id": "abc-123"
		}
		
		result = ErrorHandler.format_http_error(status_code, response_data)
		expected = "HTTP 404: Could not find page with ID: 123"
		assert result == expected

	def test_format_http_error_no_message(self):
		"""Test format_http_error when response has no message field."""
		status_code = 500
		response_data = {
			"object": "error",
			"status": 500,
			"request_id": "abc-123"
		}
		
		result = ErrorHandler.format_http_error(status_code, response_data)
		expected = "HTTP 500: Unknown error"
		assert result == expected

	def test_format_http_error_empty_response(self):
		"""Test format_http_error with empty response data."""
		status_code = 400
		response_data = {}
		
		result = ErrorHandler.format_http_error(status_code, response_data)
		expected = "HTTP 400: Unknown error"
		assert result == expected

	def test_clean_error_message_removes_metadata(self):
		"""Test clean_error_message removes object and request_id fields."""
		message = {
			"object": "error",
			"status": 404,
			"code": "object_not_found",
			"message": "Could not find page",
			"request_id": "abc-123"
		}
		
		result = ErrorHandler.clean_error_message(message)
		expected = {
			"status": 404,
			"code": "object_not_found",
			"message": "Could not find page"
		}
		assert result == expected

	def test_clean_error_message_preserves_original(self):
		"""Test clean_error_message doesn't modify the original message."""
		original_message = {
			"object": "error",
			"message": "Test error",
			"request_id": "abc-123"
		}
		original_copy = original_message.copy()
		
		result = ErrorHandler.clean_error_message(original_message)
		
		# Original should be unchanged
		assert original_message == original_copy
		# Result should be cleaned
		assert "object" not in result
		assert "request_id" not in result
		assert result["message"] == "Test error"

	def test_clean_error_message_no_metadata_fields(self):
		"""Test clean_error_message when no metadata fields are present."""
		message = {
			"status": 400,
			"code": "validation_error",
			"message": "Invalid request"
		}
		
		result = ErrorHandler.clean_error_message(message)
		assert result == message

	def test_clean_error_message_empty_dict(self):
		"""Test clean_error_message with empty dictionary."""
		message = {}
		result = ErrorHandler.clean_error_message(message)
		assert result == {}

	def test_extract_error_details_complete(self):
		"""Test extract_error_details with complete error response."""
		response_data = {
			"object": "error",
			"status": 400,
			"code": "validation_error",
			"message": "Invalid property value",
			"request_id": "abc-123"
		}
		
		result = ErrorHandler.extract_error_details(response_data)
		expected = {
			"code": "validation_error",
			"message": "Invalid property value",
		}
		assert result == expected

	def test_extract_error_details_minimal(self):
		"""Test extract_error_details with minimal error response."""
		response_data = {
			"message": "Something went wrong"
		}
		
		result = ErrorHandler.extract_error_details(response_data)
		expected = {
			"message": "Something went wrong"
		}
		assert result == expected

	def test_extract_error_details_empty(self):
		"""Test extract_error_details with empty response."""
		response_data = {}
		result = ErrorHandler.extract_error_details(response_data)
		assert result == {}

 