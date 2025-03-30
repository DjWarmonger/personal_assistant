# JsonAgent Launch Guide

## Quick Start

To run JsonAgent scripts correctly, always execute them from the project root directory:

```bash
# Navigate to project root
cd /path/to/PersonalAssistant

# Run JsonAgent command line tool
python Agents/JsonAgent/launcher/commandLine.py -i path/to/input.json
```

## Common Examples

1. Process a JSON file:
```bash
python Agents/JsonAgent/launcher/commandLine.py -i Agents/JsonAgent/Agent/testFiles/runeStones.json
```

2. Save processed output:
```bash
python Agents/JsonAgent/launcher/commandLine.py -i input.json -o output.json
```

3. Custom prompt:
```bash
python Agents/JsonAgent/launcher/commandLine.py -i input.json -p "Analyze this JSON structure"
```

## Troubleshooting

If you encounter `ModuleNotFoundError: No module named 'tz_common'`:
1. Ensure you're in the project root directory
2. Check that the `common` directory exists in your project root
3. Run the script using the full path from project root

## Project Structure
```
PersonalAssistant/
├── common/
│   └── tz_common/
└── Agents/
    └── JsonAgent/
        ├── launcher/
        │   └── commandLine.py
        └── Agent/
            └── testFiles/
                └── runeStones.json
```

For more detailed information about Python imports and path resolution, see `python_import_guidelines.md`. 