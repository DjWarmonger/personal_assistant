import json

def summarize_json(data, depth=0, max_depth=3):
    """
    Recursively summarize a JSON object up to max_depth.
    Beyond max_depth, it returns a simple summary.
    """
    if depth >= max_depth:
        if isinstance(data, dict):
            return f"Object with {len(data)} keys"
        elif isinstance(data, list):
            return f"Array with {len(data)} items"
        else:
            return data

    if isinstance(data, dict):
        summary = {}
        for key, value in data.items():
            summary[key] = {
                "type": type(value).__name__,
                "summary": summarize_json(value, depth + 1, max_depth)
            }
        return summary
    elif isinstance(data, list):
        if not data:
            return "Empty Array"
        # If all items are primitives, show a count and a sample.
        if all(not isinstance(item, (dict, list)) for item in data):
            return f"Array of {len(data)} items, sample: {data[0]}"
        else:
            element_summary = summarize_json(data[0], depth + 1, max_depth)
            return {"type": "array", "length": len(data), "element_summary": element_summary}
    else:
        return data

def adaptive_summarize(data, target_size, min_depth=1, max_depth=10):
    """
    Adjusts the summarization depth so that the resulting JSON summary,
    when converted to string, is at most target_size characters.
    
    It returns the summary and the depth used.
    """
    for d in range(max_depth, min_depth - 1, -1):
        summary = summarize_json(data, max_depth=d)
        summary_str = json.dumps(summary)
        if len(summary_str) <= target_size:
            return summary, d
    # If even the shallowest summary is too large, return that.
    return summarize_json(data, max_depth=min_depth), min_depth


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


if __name__ == "__main__":
    # Example JSON structure.
    example_json = {
        "users": [
            {"name": "Alice", "age": 30, "email": "alice@example.com"},
            {"name": "Bob", "age": 25, "email": "bob@example.com"}
        ],
        "settings": {
            "theme": "dark",
            "notifications": {"email": True, "sms": False}
        },
        "version": 1.0,
        "data": {str(i): {"value": i, "details": list(range(i))} for i in range(5)}
    }
    
    target_characters = 300  # target size in characters for the summary
    summary_text, used_depth = adaptive_summarize_text(example_json, target_characters, min_depth=1, max_depth=6)
    
    print(f"Adaptive Summary (using depth {used_depth}):\n")
    print(summary_text)
    print(f"\nSummary length: {len(summary_text)} characters")
