# Search for all objects that match pattern

clear && python commandLine.py -i ../Agent/testFiles/1mm.json -I -p "Search for all zones and return their sizes"

Result: Failed to find anything for path `zones.*.size`

## Follow up questions

* are there any objects "zone" in this file?

> Yes, there are several objects labeled as "zone" in the current document. Here are the details of the zones along with their sizes:       

1. **Zone 1**
   - Type: Treasure
   - Size: 9

2. **Zone 2**
   - Type: Treasure
   - Size: 9

...

# Replace objects based on formula, save to file at given path

clear && python commandLine.py -i ../Agent/testFiles/1mm.json -I -p "Find all rmg objecs and change their zoneLimit to 1" -o 1mm_output.json