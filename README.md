# steam-wishlist-demos
A simple Python-based GUI-tool, to keep track of demos for games on my Steam wishlist.

Receiving the wishlist "apps" is quick, but the Steam API for getting app-details (including info about demos) is rate-limited to 200 requests per 5 minutes, so fetching this info is currently very slow (1.5 secs per request).

Previously fetched data is stored in a simple text-file `demos_installed.txt` (with a backup-file `demos_installed-backup.txt`).

Requirements (tested with) :
* Python 3.13
* FreeSimpleGUI 5.2
* requests 2.32
