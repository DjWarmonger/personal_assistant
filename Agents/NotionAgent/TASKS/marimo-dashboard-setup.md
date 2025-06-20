# Marimo Dashboard Setup

> Location: `Agents/NotionAgent/TASKS/marimo-dashboard-setup.md`

---

## Overview
The NotionAgent includes a marimo-based dashboard for interactive development and monitoring. This dashboard provides a web-based interface for managing and visualizing NotionAgent operations.

---

## Prerequisites
- UV environment must be activated (`.venv_uv_services`)
- All NotionAgent dependencies installed via UV

---

## Running the Dashboard

### Development Mode (Recommended)
Shows all cells and code for development and debugging:

```bash
# Activate UV environment first
.\.venv_uv_services\Scripts\activate

# Run dashboard in development mode
marimo edit Agents/NotionAgent/launcher/dashboard.py
```

**Expected Output:**
```
Update available 0.9.8 → 0.14.0
Run pip install --upgrade marimo to upgrade.
        Edit dashboard.py in your browser 📝
        URL: http://127.0.0.1:2718?access_token=PTDHJo2tV0G_CZ59YL8MgQ
Block cache saved to disk
Saved BlockCache
```

### Production Mode
Runs the dashboard as an app with production UI only:

```bash
# Activate UV environment first
.\.venv_uv_services\Scripts\activate

# Run dashboard in app mode
marimo run Agents/NotionAgent/launcher/dashboard.py
```

---

## Access
- **URL**: http://127.0.0.1:2718
- **Port**: 2718 (default marimo port)
- **Access Token**: Generated automatically and displayed in terminal output

---

## Troubleshooting

### Marimo Version Warning
If you see an update warning:
```
Update available 0.9.8 → 0.14.0
Run pip install --upgrade marimo to upgrade.
```

You can upgrade marimo within the UV environment:
```bash
.\.venv_uv_services\Scripts\activate
pip install --upgrade marimo
```

### Port Already in Use
If port 2718 is occupied, marimo will automatically find another available port and display it in the terminal output.

### Block Cache Messages
The messages "Block cache saved to disk" and "Saved BlockCache" are normal operations indicating the dashboard is properly managing the NotionAgent cache system.

---

## Notes
- The dashboard automatically initializes the block cache system
- All changes made through the dashboard are persistent
- Use development mode for debugging and code exploration
- Use production mode for clean user interface without code visibility 