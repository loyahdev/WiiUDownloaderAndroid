#!/usr/bin/env python3

# usage: wiiu_titlekeys.py

import json
import sys
from urllib.request import Request, urlopen

keys_url = 'http://vault.titlekeys.ovh/json'
keys_filename = 'titlekeys.json'
keys_cemu = 'keys.txt'

print("Generating key lists from {} structure...".format(keys_url, keys_filename))
request = Request(keys_url)
request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)')
response = urlopen(request).read()
keys_json_raw = json.loads(response)

# Formatted JSON structure
keys_json_formatted = json.dumps(keys_json_raw, indent=4)
with open(keys_filename, "w") as f:
    f.write(keys_json_formatted)
print("  Formatted json: " + keys_filename)

if '--cemu' in sys.argv:
    # CEMU key list
    title_key_list = []

    for title in keys_json_raw:
        if title["titleKey"]:
            if title["name"]:
                title_key_list.append(title["titleKey"].upper() + ' # ' + title["name"].replace('\n',''))
            else:
                title_key_list.append(title["titleKey"].upper())
    with open(keys_cemu, "w") as f:
        f.write('\n'.join(map(str, title_key_list)))
    print("  CEMU key list with all known keys: " + keys_cemu)

#keys_json_formatted = keys_json_formatted.encode('utf-8').decode('unicode-escape')
