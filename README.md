# plum-probe
A tool to manage Plum LightPads without the iOS app

Dependencies:

Python 2.7.10 (Python 3.x untested)
Requests (pip install requests)

First you must initialize the local cache:
python plum-probe.py --init --username PLUM_ACCOUNT_EMAIL_ADDRESS --password YOUR_PASSWORD

If that works, you can take the logical load IDs printed out during init (or with --list) and control it --(on/off/dim/status). 
See the help: python plum-probe.py --help

You can print the local cache with python plum-probe.py --list

-If you add/remove/change the layout of your lightpads, you should reinitialize the local cache.
-You must allocate static IPs or use static DHCP to give your LightPads fixed IPs in order to avoid periodic reinitializations. The local IPs of your Plum dimmers are cached once detected to ensure minimum latency when sending commands.

OpenHAB binding here: https://github.com/mikenemat/org.openhab.binding.plum

It took me a lot of work to reverse engineer this. Please share credit if you reuse the code.
