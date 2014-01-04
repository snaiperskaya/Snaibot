SNAIBOT

Snaibot is a Python 3.0 IRC bot build on top of the PythonIRCBot library originally made by Milan Boers for Python 2.X. This library was updated to 3.0 and resulting bugs have been patched.

Snaibot currently has the following features available:

	- Spam Filter
	- Language Filter
	- Link Providing (Both public and secret)
	- Show MC Mod info
	- "Choose"
	- News Item
	- In-IRC Basic Administration
	- YouTube Video Info for Links Posted to Chat
	
All run from a config file, which can be live-updated to turn modules on and off and items like links can be added to or modified without pulling the bot down.


To Use:

	1) Copy both files in "Python Files" to the directory of you choosing.
	2) Create a new Python file importing snaibot and with "x = snaibot.snaibot('name of configfile.ini')" in a Python main method.
	3) Run once and close.
	4) Open the config file generated under the name you specified and change all the settings to your choosing
	5) Run and enjoy! Multiple bots can be run in this method with multiple unique configs (Bots may be only on one server each)
	
	
Requirements:
	Python 3.0 must be installed (3.3 recommended. 2.7.X may work, but this is untested and unsupported)
	
	
*Limited documentation available in "docs" folder in form of pydocs of classes in snaibot and pythonircbot