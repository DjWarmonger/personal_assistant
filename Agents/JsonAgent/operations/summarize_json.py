import json

# TODO: Add version of json which shows something like (...) or (123 more objects)

def summarize_json_text(data, current_depth=0, max_depth=3, indent=""):
    """
    Recursively creates a plain-text summary of a JSON-like structure.
    
    Args:
      data: The JSON object (dict, list, or primitive)
      current_depth: Current recursion level.
      max_depth: Maximum depth for detailed summary.
      indent: String used for indentation.
    
    Returns:
      A plain-text summary string.
    """
    if current_depth >= max_depth:
        if isinstance(data, dict):
            return f"Object with {len(data)} keys"
        elif isinstance(data, list):
            return f"Array with {len(data)} items"
        else:
            return str(data)
    
    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            type_str = type(value).__name__
            summary = summarize_json_text(value, current_depth + 1, max_depth, indent + "  ")
            lines.append(f"{indent}{key} ({type_str}): {summary}")
        return "\n".join(lines)
    
    elif isinstance(data, list):
        if not data:
            return "Empty array"
        # If all items are primitives, show count and sample.
        if all(not isinstance(item, (dict, list)) for item in data):
            return f"Array of {len(data)} items, sample: {data[0]}"
        else:
            element_summary = summarize_json_text(data[0], current_depth + 1, max_depth, indent + "  ")
            return f"Array of {len(data)} items, first element:\n{indent}  {element_summary}"
    
    else:
        return str(data)


def adaptive_summarize_text(data, target_size, min_depth=1, max_depth=10, pretty_output=False):
    """
    Finds the deepest summary (largest max_depth) that results in a text output
    below the target_size (in characters). Returns both the summary and the depth used.
    
    Args:
      data: The JSON object.
      target_size: Maximum allowed size of the summary in characters.
      min_depth: Minimum allowed depth.
      max_depth: Maximum allowed depth.
      pretty_output: When True, formats the output with indentation and structure
                     to improve human readability.
    
    Returns:
      A tuple (summary_string, used_depth).
    """
    for d in range(max_depth, min_depth - 1, -1):
        summary = summarize_json_text(data, current_depth=0, max_depth=d)
        if len(summary) <= target_size:
            if pretty_output:
                return format_summary_for_humans(summary), d
            return summary, d
    
    # If even the shallowest summary is too long, return it.
    summary = summarize_json_text(data, current_depth=0, max_depth=min_depth)
    if pretty_output:
        return format_summary_for_humans(summary), min_depth
    return summary, min_depth


def format_summary_for_humans(summary_text):
    """
    Formats a plain text JSON summary to be more human-readable with proper
    multi-line output.
    
    Args:
      summary_text: The plain text summary to format.
    
    Returns:
      A formatted string with better visual structure and tab indentation.
    """
    lines = summary_text.split('\n')
    formatted_lines = []
    
    for line in lines:
        # Count leading spaces to determine depth
        leading_spaces = len(line) - len(line.lstrip())
        
        # Calculate indentation level (convert spaces to tabs)
        indent_level = leading_spaces // 2
        
        if ':' in line:
            key_part, value_part = line.split(':', 1)
            
            # Style for keys
            key = key_part.strip()
            
            # Handle different depth levels with appropriate prefixes
            if indent_level == 0:
                # Root level items
                prefix = "● "
                formatted_line = f"{prefix}{key}:{value_part}"
            else:
                # Nested items with tree structure
                prefix = "└─ "
                tab_indent = "\t" * (indent_level - 1)
                formatted_line = f"{tab_indent}{prefix}{key}:{value_part}"
        else:
            # For lines without key-value structure (like array elements)
            tab_indent = "\t" * indent_level
            formatted_line = f"{tab_indent}{line.strip()}"
        
        formatted_lines.append(formatted_line)
    
    # Join with newlines to create proper multi-line output
    return "\n".join(formatted_lines)


def truncated_json_format(data, current_depth=0, max_depth=3, indent="", max_array_items=3, max_object_props=5, format_output=True):
    """
    Creates a JSON-like summary with truncation indicators for large collections.
    
    Args:
        data: The JSON object (dict, list, or primitive)
        current_depth: Current recursion level
        max_depth: Maximum depth for detailed summary
        indent: String used for indentation
        max_array_items: Maximum number of array items to show before truncating
        max_object_props: Maximum number of object properties to show before truncating
        format_output: When True, formats the output with indentation for readability.
                When False, produces a compact unformatted string.
    
    Returns:
        A JSON-formatted string with truncation indicators
    """
    if current_depth >= max_depth:
        if isinstance(data, dict):
            return f"{{{len(data)} properties...}}"
        elif isinstance(data, list):
            return f"[{len(data)} items...]"
        else:
            return json.dumps(data)
    
    if isinstance(data, dict):
        if not data:
            return "{}"
            
        result = "{\n" if format_output else "{"
        items = list(data.items())
        
        # Show only max_object_props items
        for i, (key, value) in enumerate(items[:max_object_props]):
            next_indent = indent + "\t" if format_output else ""
            value_str = truncated_json_format(
                value, current_depth + 1, max_depth, next_indent, 
                max_array_items, max_object_props, format_output
            )
            
            # Add comma if not the last item or if we have remaining items
            trailing_comma = "," if i < min(max_object_props, len(items)) - 1 or len(items) > max_object_props else ""
            
            if format_output:
                result += f"{next_indent}\"{key}\": {value_str}{trailing_comma}\n"
            else:
                result += f"\"{key}\":{value_str}{trailing_comma}"
        
        # Add truncation indicator if needed
        remaining = len(data) - max_object_props
        if remaining > 0:
            if format_output:
                result += f"{indent}\t({remaining} more properties...)\n"
            else:
                result += f"({remaining} more properties...)"
            
        result += f"{indent}}}" if format_output else "}"
        return result
    
    elif isinstance(data, list):
        if not data:
            return "[]"
            
        result = "[\n" if format_output else "["
        
        # For lists, show limited number of items
        for i, item in enumerate(data[:max_array_items]):
            next_indent = indent + "\t" if format_output else ""
            item_str = truncated_json_format(
                item, current_depth + 1, max_depth, next_indent,
                max_array_items, max_object_props, format_output
            )
            
            # Add comma if not the last item or if we have remaining items
            trailing_comma = "," if i < min(max_array_items, len(data)) - 1 or len(data) > max_array_items else ""
            
            if format_output:
                result += f"{next_indent}{item_str}{trailing_comma}\n"
            else:
                result += f"{item_str}{trailing_comma}"
        
        # Add truncation indicator if needed
        remaining = len(data) - max_array_items
        if remaining > 0:
            if format_output:
                result += f"{indent}\t({remaining} more items...)\n"
            else:
                result += f"({remaining} more items...)"
            
        result += f"{indent}]" if format_output else "]"
        return result
    
    else:
        # For primitives, use JSON serialization
        return json.dumps(data)


def adaptive_truncated_json(data, target_size, min_depth=1, max_depth=10, 
                           max_array_items=3, max_object_props=5):
    """
    Creates an adaptive truncated JSON representation that fits within target size.
    
    Args:
        data: The JSON object
        target_size: Maximum size in characters
        min_depth: Minimum depth to show
        max_depth: Maximum depth to consider
        max_array_items: Maximum array items to show before truncating
        max_object_props: Maximum object properties to show before truncating
        
    Returns:
        A tuple (formatted_json, used_depth)
    """
    for d in range(max_depth, min_depth - 1, -1):
        formatted = truncated_json_format(
            data, current_depth=0, max_depth=d, 
            max_array_items=max_array_items, max_object_props=max_object_props
        )
        
        if len(formatted) <= target_size:
            return formatted, d
    
    # If even the shallowest summary is too long, return it
    formatted = truncated_json_format(
        data, current_depth=0, max_depth=min_depth,
        max_array_items=max_array_items, max_object_props=max_object_props
    )
    
    return formatted, min_depth


def summarize_json_first_item(data, current_depth=0, max_depth=3, indent="", max_object_props=5, format_output=True):
	"""
	Creates a JSON-like summary with only the first item of any array shown (max_array_items=1).
	Other arguments are the same as truncated_json_format, except max_array_items is always 1.
	"""
	return truncated_json_format(
		data,
		current_depth=current_depth,
		max_depth=max_depth,
		indent=indent,
		max_array_items=1,
		max_object_props=max_object_props,
		format_output=format_output
	)


if __name__ == "__main__":
    # Example JSON structure.
    example_json = {
        "users": [
            {"name": "Alice", "age": 30, "email": "alice@example.com"},
            {"name": "Bob", "age": 25, "email": "bob@example.com"},
            {"name": "Charlie", "age": 35, "email": "charlie@example.com"},
            {"name": "David", "age": 40, "email": "david@example.com"},
            {"name": "Eve", "age": 28, "email": "eve@example.com"}
        ],
        "settings": {
            "theme": "dark",
            "notifications": {"email": True, "sms": False},
            "preferences": {
                "language": "en",
                "timezone": "UTC",
                "display": {
                    "mode": "compact",
                    "colors": ["blue", "green", "red"],
                    "layout": "grid"
                }
            }
        },
        "version": 1.0,
        "data": {str(i): {"value": i, "details": list(range(i))} for i in range(10)}
    }
    
    # Standard summary example
    target_characters = 300  # target size in characters for the summary
    summary_text, used_depth = adaptive_summarize_text(example_json, target_characters, min_depth=1, max_depth=6)
    
    print("Standard Summary:")
    print(summary_text)
    print(f"\nSummary length: {len(summary_text)} characters (depth {used_depth})")
    
    # Truncated summary example
    print("\n\nTruncated Summary:")
    truncated_text, trunc_depth = adaptive_truncated_json(
        example_json, 
        target_size=400,
        max_array_items=3,  # Show 3 items from arrays (default)
        max_object_props=4   # Show 4 properties from objects
    )
    
    print(truncated_text)
    print(f"\nTruncated summary length: {len(truncated_text)} characters (depth {trunc_depth})")
