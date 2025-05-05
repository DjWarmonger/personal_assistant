import marimo

__generated_with = "0.9.14"
app = marimo.App(width="full")


@app.cell
def __():
    import marimo as mo
    return (mo,)


@app.cell
def __():
    import glob
    import os
    from datetime import datetime
    from tz_common import LogLevel

    LOG_LEVELS = {name : value for name, value in LogLevel.__members__.items()}
    return LOG_LEVELS, LogLevel, datetime, glob, os


@app.cell
def __(datetime, glob, os):
    def get_log_files():
        logs = glob.glob("logs/*.log")
        # Sort by modification time, newest first
        logs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return [os.path.basename(f) for f in logs]

    def format_timestamp(filename):
        # Extract timestamp from filename format YYYYMMDD_HHMMSS
        try:
            timestamp = datetime.strptime(filename.split('.')[0], "%Y%m%d_%H%M%S")
            return timestamp.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return filename

    def read_log_file(filepath):
        # Try different encodings
        encodings = ['utf-8', 'cp1250', 'iso-8859-1', 'cp1252']

        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue

        # If all encodings fail, try reading with errors='replace'
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    return format_timestamp, get_log_files, read_log_file


@app.cell
def __(LOG_LEVELS, format_timestamp, get_log_files, mo):
    log_files = get_log_files()

    # Create options with formatted timestamps
    options = {f"{format_timestamp(f)}": f for f in log_files}

    log_selector = mo.ui.dropdown(
        options=options,
        label="Select log file",
        value=format_timestamp(log_files[0]) if log_files else None,
        full_width=True
    )

    # Add severity filter
    severity_filter = mo.ui.multiselect(
        options=list(LOG_LEVELS.keys()),
        value=list(LOG_LEVELS.keys()),  # All selected by default
        label="Filter by severity",
        full_width=True
    )

    mo.hstack([log_selector, severity_filter])
    return log_files, log_selector, options, severity_filter


@app.cell
def __(log_selector, mo, read_log_file, severity_filter):
    if not log_selector.value:
        mo.md("No log files found")

        tabs = mo.ui.tabs(
        {
            "Full Log": "",
            "By Timestamp": ""
        })
    else:
        content = read_log_file(f"logs/{log_selector.value}")

        # Split into lines
        lines = content.split('\n')

        # Filter lines by severity
        filtered_lines = []
        for i, line in enumerate(lines):
            if not any(c.isprintable() for c in line):  # Skip lines with no printable chars
                continue
            if " - " in line:
                parts = line.split(" - ")
                if len(parts) >= 2:
                    severity = parts[1].strip()
                    if any(level in severity for level in severity_filter.value):
                        filtered_lines.append((i + 1, line))
            else:
                # Include lines that don't match the timestamp pattern if previous line was included
                if filtered_lines:
                    filtered_lines.append((i + 1, line))

        # Format lines with numbers
        numbered_lines = [f"{line_num:4d} | {line}" for line_num, line in filtered_lines]

        # Create collapsible sections based on timestamps
        sections = {}
        current_time = None
        current_lines = []

        for _, line in filtered_lines:
            if " - " in line:  # Look for timestamp separator
                # Extract just the time portion (HH:MM:SS) from the timestamp
                full_timestamp = line.split(" - ")[0]
                time_only = full_timestamp.split()[1]  # Get just the time part
                # Round down to seconds by truncating milliseconds if present
                time_rounded = time_only.split(',')[0]
                if time_rounded != current_time:
                    if current_time and current_lines:
                        sections[current_time] = "\n".join(current_lines)
                    current_time = time_rounded
                    current_lines = []
            current_lines.append(line)

        if current_time and current_lines:
            sections[current_time] = "\n".join(current_lines)

        # Create tabs for different views
        tabs = mo.ui.tabs(
        {
            "Full Log": mo.md("\n\n\n" + '\n\n'.join(numbered_lines) + "\n"),
            "By Timestamp": mo.accordion(
                {time: mo.md(f"```\n{content}\n```") 
                 for time, content in sections.items()}
            )
        })

    tabs
    return (
        content,
        current_lines,
        current_time,
        filtered_lines,
        full_timestamp,
        i,
        line,
        lines,
        numbered_lines,
        parts,
        sections,
        severity,
        tabs,
        time_only,
        time_rounded,
    )


if __name__ == "__main__":
    app.run()
