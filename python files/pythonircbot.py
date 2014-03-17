#!python3

#    This version is a heavy re-write and port from Python 2 -> Python 3 by
#    snaiperskaya (C.S.Putnam) for use with the snaibot moderation bot.
#    This will be distributed alongside snaibot.py to enable it's features
#    However, the license and author on this will remain unchanged and also
#    be made available.


#    pythonircbot, module used to easily create IRC bots in Python
#    Copyright (C) 2012  Milan Boers
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Easily create IRC bots in Python

Module providing an easy interface to create IRC bots.
Uses regexes in combination with an event-like system
to handle messages, and abstracts many IRC commands.
"""

__author__ = 'Milan Boers'
__version__ = '2.0'

import socket
import threading
import re
import copy
import time
import queue

class _PyEvent(object):
	"""Own internal event implementation"""
	def __init__(self, *args, **kwargs):
		super(_PyEvent, self).__init__(*args, **kwargs)
		
		self.subscribers = []
	
	def emit(self, *args, **kwargs):
		for subscriber in self.subscribers:
			subscriber(*args, **kwargs)
	
	def connect(self, func):
		self.subscribers.append(func)

class _SuperSocket(object):
	"""Socket with flooding control"""
	def __init__(self, sleepTime, maxItems, verbose=True, *args, **kwargs):
		super(_SuperSocket, self).__init__(*args, **kwargs)
		
		self._sleepTime = sleepTime
		self._maxItems = maxItems
		self._verbose = verbose
		self._messageQueue = queue.Queue(self._maxItems)
		self._quit = False
		
		self._shutdownEvent = _PyEvent()
		
		self._s = socket.socket()
	
	def _senderThread(self):
		while not self._quit:
			# Block until item is available (might not happen when disconnected, then this thread is a zombie)
			try:
				data = self._messageQueue.get(True, 5)
				data = data + "\r\n"
				self._s.send(data.encode())
				if self._verbose:
					print("SENT: ", data)
				time.sleep(self._sleepTime)
			except queue.Empty:
				pass
			except:
				self._die()
	
	def _connect(self, host, port):
		# Try to connect over and over until it worked
		try:
			if self._verbose:
				print("NOTE:\tTrying to connect...")
			self._s.connect((host, port))
			# Start the sender thread
			t = threading.Thread(target=self._senderThread)
			t.daemon = True
			t.start()
		except:
			time.sleep(5)
			self._connect(host, port)
	
	def _send(self, data):
		try:
			self._messageQueue.put(data, False)
		except queue.Full:
			if self._verbose:
				print("NOTE:\tMessage queue full.")
	
	def _recv(self):
		try:
			data = self._s.recv(4096)
			data = data.decode(errors='ignore')
			if not data:
				self._die()
			else:
				data = data.rstrip('\r\n')
				return data
		except socket.error:
			self._die()
	
	def _close(self):
		self._s.close()
	
	def _die(self):
		if self._verbose:
			print("NOTE:\tSocket dead. Going to reconnect.")
		self._quit = True
		self._shutdownEvent.emit()

class _BotReceiveThread(threading.Thread):
	"""Thread in which the bot handles received messages"""
	def __init__(self, bot, verbose=True, *args, **kwargs):
		super(_BotReceiveThread, self).__init__(*args, **kwargs)
		
		self._bot = bot
		self._verbose = verbose
		self._quit = False
		
		# Event to fire when the thread wants to stop
		self._shutdownEvent = threading.Event()
		# Event to fire when channel was joined
		self._joinedEvent = _PyEvent()
		# Event to fire when channel was parted
		self._partedEvent = _PyEvent()
		# Event to fire when the list of names has been updated
		self._updateNames = _PyEvent()
		# Event to fire when the channel topic has changed
		self._updateTopic = _PyEvent()
		# Event to fire when a user mode was set
		self._userModeSet = _PyEvent()
		# Event to fire when a user mode was unset
		self._userModeUnset = _PyEvent()
	
	def run(self):
		while not self._quit:
			try:
				lines = self._bot._s._recv().splitlines()
			except AttributeError:
				self._die()
			
			for line in lines:
				if self._verbose:
					try:
						print("RECV: ", line)
					except:
						print("Error processing character")
				
				if self._privMsg(line):
					continue
				if self._joinChannel(line):
					continue
				if self._partChannel(line):
					continue
				if self._pong(line):
					continue
				if self._quitM(line):
					continue
				if self._modeset(line):
					continue
				if self._modeunset(line):
					continue
				if self._names(line):
					continue
				#if self._topic(line):
					#continue
	
	def _die(self):
		self._quit = True
		self._shutdownEvent.set()
	
	def _joinChannel(self, line):
		matchJoin = re.compile('^:(.*)!(.*) JOIN :(.*)').search(line)
		if matchJoin:
			print("Channel Join Detected")
			self._joinedEvent.emit(matchJoin.group(1), matchJoin.group(3))
			nick = matchJoin.group(1)
			client = matchJoin.group(2)
			channel = matchJoin.group(3)			
			if nick != self._bot._nick:
				with self._bot._responseFunctionsLock:
					_joinResponseFunctions = copy.copy(self._bot._joinResponseFunctions)
				
				for func in _joinResponseFunctions:
					if func['thread']:
						t = threading.Thread(target=func['func'], args=(nick, client, channel))
						t.start()
					else:
						func(nick, client, channel)
				
				# Return a string, just to make sure it doesn't return None
				return "continue"			
	
	def _partChannel(self, line):
		matchPart = re.compile('^:(.*)!(.*) PART (.*)').search(line)
		if matchPart:
			print("Channel Part Detected")
			self._partedEvent.emit(matchPart.group(1), matchPart.group(3))
			nick = matchPart.group(1)
			client = matchPart.group(2)
			channel = matchPart.group(3)			
			if nick != self._bot._nick:
				with self._bot._responseFunctionsLock:
					_partResponseFunctions = copy.copy(self._bot._partResponseFunctions)
				
				for func in _partResponseFunctions:
					if func['thread']:
						t = threading.Thread(target=func['func'], args=(nick, client, channel))
						t.start()
					else:
						func(nick, client, channel)
				
				# Return a string, just to make sure it doesn't return None
				return "continue"			
	
	def _quitM(self, line):
		matchQuit = re.compile('^:{}!.* QUIT :'.format(self._bot._nick)).search(line)
		if matchQuit:
			self._die()
	
	def _names(self, line):
		matchNames = re.compile('^:.* 353 {} .* (.*) :(.*)'.format(self._bot._nick)).search(line)
		if matchNames:
			# Names list
			channel = matchNames.group(1)
			names = matchNames.group(2)
			
			ownerSet = set()
			aopsSet = set()
			opsSet = set()
			hopsSet = set()
			voicesSet = set()
			namesSet = set()
			
			names = names.split(' ')
			for name in names:
				if name[0] == '@':
					opsSet.add(name[1:])
					namesSet.add(name[1:])
				elif name[0] == '&':
					aopsSet.add(name[1:])
					namesSet.add(name[1:])
				elif name[0] == '~':
					ownerSet.add(name[1:])
					namesSet.add(name[1:])
				elif name[0] == '%':
					hopsSet.add(name[1:])
					namesSet.add(name[1:])				
				elif name[0] == '+':
					voicesSet.add(name[1:])
					namesSet.add(name[1:])
				else:
					namesSet.add(name)
			
			self._updateNames.emit(channel, namesSet, opsSet, voicesSet, ownerSet, aopsSet, hopsSet)
	
	def _topic(self, line):
		matchTopic = re.compile('^:.* 332 {} (.*) :(.*)'.format(self._bot._nick)).search(line)
		if matchTopic:
			channel = matchTopic.group(1)
			topic = matchTopic.group(2)
			
			self._updateTopic.emit(channel, topic)
	
	def _privMsg(self, line):
		matchPrivmsg = re.compile('^:(.*)!(.*) PRIVMSG (.*) :(.*)').search(line)
		if matchPrivmsg:
			# Privmsg
			nick = matchPrivmsg.group(1)
			client = matchPrivmsg.group(2)
			channel = matchPrivmsg.group(3)
			rmsg = matchPrivmsg.group(4)
			
			with self._bot._responseFunctionsLock:
				_msgResponseFunctions = copy.copy(self._bot._msgResponseFunctions)
			
			for func in _msgResponseFunctions:
				if func['thread']:
					t = threading.Thread(target=func['func'], args=(rmsg, nick, client, channel))
					t.start()
				else:
					func(rmsg, nick, client, channel)
			
			# Return a string, just to make sure it doesn't return None
			return "continue"
	
	def _pong(self, line):
		matchPing = re.compile('^PING :(.*)').search(line)
		if matchPing:
			# Ping
			self._bot._s._send("PONG {}".format(matchPing.group(1)))
			return "continue"
	
	def _modeset(self, line):
		matchModeset = re.compile('^:.* MODE (.*) \+([A-Za-z]) (.*)$').search(line)
		if matchModeset:
			channel = matchModeset.group(1)
			mode = matchModeset.group(2)
			nick = matchModeset.group(3)
			self._userModeSet.emit(channel, nick, mode)
			return "continue"
	
	def _modeunset(self, line):
		matchModeunset = re.compile('^:.* MODE (.*) -([A-Za-z]) (.*)$').search(line)
		if matchModeunset:
			channel = matchModeunset.group(1)
			mode = matchModeunset.group(2)
			nick = matchModeunset.group(3)
			self._userModeUnset.emit(channel, nick, mode)
			return "continue"

class Bot(object):
	def __init__(self, nickname, password=''):
		"""
		Creates bot with nick as nickname
		
		Arguments:
		- nickname: Nickname of the bot
		"""
		self._nick = nickname
		self._pass = password
		
		self._connected = False
		self._connecting = False
		
		self._disconnectEvent = threading.Event()
		
		self._msgResponseFunctions = []
		self._joinResponseFunctions = []
		self._partResponseFunctions = []
		self._responseFunctionsLock = threading.Lock()
	
	def connect(self, host, port=6667, verbose=True, sleepTime=0.8, maxItems=10, channels=[]):
		"""
		Connects the bot to a server. Every bot can connect to only one server.
		If you want your bot to be on multiple servers, create multiple Bot objects.
		
		Arguments:
		- host: Hostname of the server
		- port: Port the server listens to
		- verbose: If True, prints all the received and sent data
		- sleepTime: Minimum time in seconds between two sent messages (used for flood control)
		- maxItems: Maximum items in the queue. Queue is emptied after this amount is reached. 0 means unlimited. (used for flood control)
		- channels: Channels to immediately join
		"""
		if self._connected:
			if self._verbose:
				print("NOTE:\tAlready connected. Can't connect twice.")
		elif self._connecting:
			if self._verbose:
				print("NOTE:\tAlready trying to connect.")
		else:
			self._connecting = True
			
			self._verbose = verbose
			self._host = host
			self._port = port
			self._sleepTime = sleepTime
			self._maxItems = maxItems
			self._modes = dict()
			
			self._channels = dict()
			for channel in channels:
				self._channels[channel.upper()] = dict()
			
			self._s = _SuperSocket(self._sleepTime, self._maxItems, self._verbose)
			self._s._shutdownEvent.connect(self.reconnect)
			self._s._connect(self._host, self._port)
			self._connected = True
			
			self.rename(self._nick)
			self._s._send("USER {} {} {} :{}".format(self._nick, self._nick, self._nick, self._nick))
			
			# Run the main loop in another thread
			self._receiveThread = _BotReceiveThread(self, self._verbose)
			self._receiveThread.daemon = True
			self._receiveThread._joinedEvent.connect(self._joinedChannel)
			self._receiveThread._partedEvent.connect(self._partedChannel)
			self._receiveThread._updateNames.connect(self._updateNames)
			self._receiveThread._updateTopic.connect(self._updateTopic)
			self._receiveThread._userModeSet.connect(self._userModeSet)
			self._receiveThread._userModeUnset.connect(self._userModeUnset)
			self._receiveThread.start()
			
			#Pause then verify Nick
			time.sleep(5)
			self.verifyNick(self._pass)
			
			# Join initial channels
			for channel in channels:
				self.joinChannel(channel)
			
			self._connecting = False
	
	def disconnect(self, message=''):
		"""
		Disconnects the bot from the server.
		
		Arguments:
		- message: Message to show when quitting.
		"""
		self._s._send("QUIT :{}".format(message))
		# Wait for the thread to be finished
		self._receiveThread._shutdownEvent.wait(5)
		self._s._quit = True
		self._connected = False
		# Fire disconnected event
		self._disconnectEvent.set()
	
	def reconnect(self, message='', rejoin=True):
		"""
		Reconnects the bot to the server. Note that this does not reconnect to channels.
		
		Arguments:
		- message: Message to show when quitting.
		- rejoin: Rejoin channels
		"""
		self._s._send("QUIT :{}".format(message))
		# Wait for the thread to be finished
		self._receiveThread._shutdownEvent.wait(5)
		self._s._quit = True
		self._connected = False
		# Connect again
		if rejoin:
			chanlist = list(self._channels.keys())
			self.connect(self._host, self._port, self._verbose, self._sleepTime, self._maxItems)
			for channel in chanlist:
				self.joinChannel(channel)
			
		else:
			self.connect(self._host, self._port, self._verbose, self._sleepTime, self._maxItems)
	
	def getModes(self, channel):
		"""
		Returns the current modes of the bot in the channel.
		
		Arguments:
		- channel: channel you want the modes of
		"""
		if channel.upper() in self._modes:
			return self._modes[channel.upper()]
		else:
			return set()
	
	"""
	IRC commands
	"""
	def verifyNick(self, password):
		"""
		Sends password to NickServ to verify nickname.
		
		Arguments:
		- password: specifies password to send to NickServ, defaults to self._pass.
		"""
		self.sendMsg("NickServ", "IDENTIFY {}".format(password))
		self._pass = password
	
	def rename(self, nickname):
		"""
		Renames the bot.
		
		Arguments:
		- nickname: New nickname of the bot
		"""
		self._s._send("NICK {}".format(nickname))
		self._nick = nickname
	
	def joinChannel(self, channel):
		"""
		Joins a channel.
		
		Arguments:
		- channel: Channel name
		"""
		self._s._send("JOIN {}".format(channel))
		self._channels[channel.upper()] = dict()
	
	def _joinedChannel(self, nick, channel):
		if nick == self._nick:
			self._channels[channel.upper()] = dict()
		else:
			self._channels[channel.upper()]['names'].add(nick)
	
	def partChannel(self, channel):
		"""
		Parts a channel.
		
		Arguments:
		- channel: Channel name
		"""
		self._s._send("PART {}".format(channel))
	
	def _partedChannel(self, nick, channel):
		if nick == self._nick:
			del self._channels[channel.upper()]
		else:
			self._channels[channel.upper()]['names'].remove(nick)
	
	def setAway(self, message=''):
		"""
		Sets the bot to away.
		
		Arguments:
		- message: Away message
		"""
		self._s._send("AWAY :{}".format(message))
	
	def setBack(self):
		"""
		Sets the bot to back (after previously having been set to away).
		"""
		self._s._send("AWAY ")
	
	def kickUser(self, channel, client, message=''):
		"""
		Kick a client from the channel.
		
		Arguments:
		- channel: Channel the client should be kicked from.
		- client: Client to be kicked.
		- message: Message to kick user with.
		"""
		self._s._send("KICK {} {} :{}".format(channel, client, message))
		
	def banUser(self, channel, client):
		"""
		Ban client from channel
		
		Arguments:
		- channel: Channel the client should be banned from.
		- client: Client to be banned.
		"""
		clientname = client.split('@')
		hostmask = "*!*@" + clientname[1]
		self._s._send("MODE {} +b {}".format(channel, hostmask))
	
	def setMode(self, channel, target, flag):
		"""
		Sets a user/channel flag.
		
		Arguments:
		- target: Channel or nickname of user to set the flag of
		- flag: Flag (and optional arguments) to set
		"""
		self._s._send("MODE {} +{} {}".format(channel, flag, target))
	
	def unsetMode(self, channel, target, flag):
		"""
		Unsets a user/channel flag.
		
		Arguments:
		- target: Channel or nickname of user to set the flag of
		- flag: Flag (and optional arguments) to set
		"""
		self._s._send("MODE {} -{} {}".format(channel, flag, target))
	
	def inviteUser(self, nickname, channel):
		"""
		Invite user to a channel.
		
		Arguments:
		- nickname: Nickname of user to invite.
		- channel: Channel to invite user to.
		"""
		self._s._send("INVITE {} {}".format(nickname, channel))
	
	def sendMsg(self, target, message):
		"""
		Send a message to a channel or user.
		
		Arguments:
		- target: Nickname or channel name to send message to.
		- message: Message to send.
		"""
		self._s._send("PRIVMSG {} :{}".format(target, message))
	
	def sendNotice(self, target, message):
		"""
		Send a notice to a channel or user.
		
		Arguments:
		- target: Nickname or channel name to send notice to.
		- message: Message to send.
		"""
		self._s._send("NOTICE {} :{}".format(target, message))
	
	def setChannelTopic(self, channel, topic):
		"""
		Sets the topic of the channel.
		
		Arguments:
		- channel: Channel name.
		- topic: Message to change the topic to.
		"""
		self._s._send("TOPIC {} :{}".format(channel, topic))
	
	def getNames(self, channel):
		"""
		Gets the nicknames of all users in a channel.
		
		Arguments:
		- channel: Channel name.
		"""
		try:
			return self._channels[channel.upper()]['names']
		except KeyError:
			if self._verbose:
				print("NOTE:\tNames of unjoined/unexisting channel requested.")
	
	def _updateNames(self, channel, namesSet, opsSet, voicesSet, ownerSet, aopsSet, hopsSet):
		self._channels[channel.upper()]['names'] = namesSet
		self._channels[channel.upper()]['ops'] = opsSet
		self._channels[channel.upper()]['voices'] = voicesSet
		self._channels[channel.upper()]['owner'] = ownerSet
		self._channels[channel.upper()]['aops'] = aopsSet
		self._channels[channel.upper()]['hops'] = hopsSet		
	
	def _userModeSet(self, channel, nick, mode):
		if mode == 'o':
			self._channels[channel.upper()]['ops'].add(nick)
		elif mode == 'h':
			self._channels[channel.upper()]['hops'].add(nick)			
		elif mode == 'a':
			self._channels[channel.upper()]['aops'].add(nick)
		elif mode == 'qo':
			self._channels[channel.upper()]['owner'].add(nick)
		elif mode == 'v':
			self._channels[channel.upper()]['voices'].add(nick)
		if nick == self._nick:
			if not channel.upper() in self._modes:
				self._modes[channel.upper()] = set()
			self._modes[channel.upper()].add(mode)
	
	def _userModeUnset(self, channel, nick, mode):
		if mode == 'o':
			self._channels[channel.upper()]['ops'].remove(nick)
		elif mode == 'h':
			self._channels[channel.upper()]['hops'].remove(nick)			
		elif mode == 'a':
			self._channels[channel.upper()]['aops'].remove(nick)
		elif mode == 'qo':
			self._channels[channel.upper()]['owner'].remove(nick)
		elif mode == 'v':
			self._channels[channel.upper()]['voices'].remove(nick)
		if nick == self._nick:
			self._modes[channel.upper()].remove(mode)

	def getOps(self, channel):
		"""
		Gets the nicknames of all the ops in a channel.
		
		Arguments:
		- channel: Channel name.
		"""
		
		try:
			return self._channels[channel.upper()]['ops']
		except KeyError:
			if self._verbose:
				print("NOTE:\tOps of unjoined/unexisting channel requested.")
				
	def getOwner(self, channel):
		"""
		Gets the nicknames of all the Owners in a channel.
		
		Arguments:
		- channel: Channel name.
		"""
		
		try:
			return self._channels[channel.upper()]['owner']
		except KeyError:
			if self._verbose:
				print("NOTE:\tOwner of unjoined/unexisting channel requested.")
				
	def getAops(self, channel):
		"""
		Gets the nicknames of all the aops in a channel.
		
		Arguments:
		- channel: Channel name.
		"""
		
		try:
			return self._channels[channel.upper()]['aops']
		except KeyError:
			if self._verbose:
				print("NOTE:\taops of unjoined/unexisting channel requested.")
	
	def getHops(self, channel):
		"""
		Gets the nicknames of all the hops in a channel.
		
		Arguments:
		- channel: Channel name.
		"""
		
		try:
			return self._channels[channel.upper()]['hops']
		except KeyError:
			if self._verbose:
				print("NOTE:\thops of unjoined/unexisting channel requested.")
	
	def getVoices(self, channel):
		"""
		Gets the nicknames of all the voices in a channel.
		
		Arguments:
		- channel: Channel name.
		"""
		
		try:
			return self._channels[channel.upper()]['voices']
		except KeyError:
			if self._verbose:
				print("NOTE:\tVoices of unjoined/unexisting channel requested.")
	
	def getTopic(self, channel):
		"""
		Gets the topic of a channel.
		
		Arguments:
		- channel: Channel name.
		"""
		try:
			return self._channels[channel.upper()]['topic']
		except KeyError:
			if self._verbose:
				print("NOTE:\tTopic of unjoined/unexisting channel requested.")
	
	def _updateTopic(self, channel, topic):
		self._channels[channel.upper()]['topic'] = topic
	
	def addMsgHandler(self, function, message=".*", channel='.*', nickname='.*', client='.*', messageFlags=0, channelFlags=0, nicknameFlags=0, clientFlags=0, thread=True):
		"""
		Adds a function to the list of functions that should be executed on every received message.
		Please keep in mind that the functions are all executed concurrently.
		Returns a function that can be used to remove the handler again with removeMsgHandler().
		
		Arguments:
		- function: The function that should be called
		- message: Regex that should match the message. If it does not, the function will not be called.
		- channel: Regex that should match the channel. If it does not, the function will not be called.
		- nickname: Regex that should match the nickname. If it does not, the function will not be called.
		- client: Regex that should match the client. If it does not, the function will not be called.
		- messageFlags: Flags for the message regex, as documented here: http://docs.python.org/library/re.html#re.compile
		- channelFlags: Flags for the channel regex, as documented here: http://docs.python.org/library/re.html#re.compile
		- nicknameFlags: Flags for the nickname regex, as documented here: http://docs.python.org/library/re.html#re.compile
		- clientFlags: Flags for the client regex, as documented here: http://docs.python.org/library/re.html#re.compile
		- thread: Execute function in seperate thread
		
		The function should have 5 arguments:
		- message: The first argument will be the message that was received.
		- channel: The second argument will be the channel the message was sent to. This will be the same as nickname when this was a private message.
		- nickname: The third argument will be the nickname of the user who sent the message.
		- client: The fourth argument will be the client of the user who sent this message.
		- message match: Match object (http://docs.python.org/library/re.html#match-objects) of the regex applied to the message.
		"""
		with self._responseFunctionsLock:
			responseFunction = lambda rmsg, rnick, rclient, rchannel: self._msgResponseFunction(function, rmsg, rnick, rclient, rchannel, message, channel, nickname, client, messageFlags, channelFlags, nicknameFlags, clientFlags)
			responseFunctionDict = {
				'func': responseFunction,
				'thread': thread
			}
			self._msgResponseFunctions.append(responseFunctionDict)
			return responseFunctionDict
	
	def removeMsgHandler(self, responseFunction):
		"""
		Remove a function from the list of functions that should be executed on every received message.
		
		Arguments:
		responseFunction: Function that is returned by addMsgHandler()
		"""
		with self._responseFunctionsLock:
			self._msgResponseFunctions.remove(responseFunction)


	def addJoinHandler(self, function, channel='.*', nickname='.*', client='.*', channelFlags=0, nicknameFlags=0, clientFlags=0, thread=True):
		"""
		Adds a function to the list of functions that should be executed on every received message.
		Please keep in mind that the functions are all executed concurrently.
		Returns a function that can be used to remove the handler again with removeJoinHandler().
		
		Arguments:
		- function: The function that should be called
		- channel: Regex that should match the channel. If it does not, the function will not be called.
		- nickname: Regex that should match the nickname. If it does not, the function will not be called.
		- client: Regex that should match the client. If it does not, the function will not be called.
		- channelFlags: Flags for the channel regex, as documented here: http://docs.python.org/library/re.html#re.compile
		- nicknameFlags: Flags for the nickname regex, as documented here: http://docs.python.org/library/re.html#re.compile
		- clientFlags: Flags for the client regex, as documented here: http://docs.python.org/library/re.html#re.compile
		- thread: Execute function in seperate thread
		
		The function should have 5 arguments:
		- channel: The second argument will be the channel the message was sent to. This will be the same as nickname when this was a private message.
		- nickname: The third argument will be the nickname of the user who sent the message.
		- client: The fourth argument will be the client of the user who sent this message.
		"""
		with self._responseFunctionsLock:
			responseFunction = lambda rnick, rclient, rchannel: self._joinResponseFunction(function, rnick, rclient, rchannel, channel, nickname, client, channelFlags, nicknameFlags, clientFlags)
			responseFunctionDict = {
				'func': responseFunction,
				'thread': thread
			}
			self._joinResponseFunctions.append(responseFunctionDict)
			return responseFunctionDict
	
	def removeJoinHandler(self, responseFunction):
		"""
		Remove a function from the list of functions that should be executed on every join.
		
		Arguments:
		responseFunction: Function that is returned by addJoinHandler()
		"""
		with self._responseFunctionsLock:
			self._joinResponseFunctions.remove(responseFunction)

	def addPartHandler(self, function, channel='.*', nickname='.*', client='.*', channelFlags=0, nicknameFlags=0, clientFlags=0, thread=True):
		"""
		Adds a function to the list of functions that should be executed on every channel Part.
		Please keep in mind that the functions are all executed concurrently.
		Returns a function that can be used to remove the handler again with removePartHandler().
		
		Arguments:
		- function: The function that should be called
		- channel: Regex that should match the channel. If it does not, the function will not be called.
		- nickname: Regex that should match the nickname. If it does not, the function will not be called.
		- client: Regex that should match the client. If it does not, the function will not be called.
		- channelFlags: Flags for the channel regex, as documented here: http://docs.python.org/library/re.html#re.compile
		- nicknameFlags: Flags for the nickname regex, as documented here: http://docs.python.org/library/re.html#re.compile
		- clientFlags: Flags for the client regex, as documented here: http://docs.python.org/library/re.html#re.compile
		- thread: Execute function in seperate thread
		
		The function should have 5 arguments:
		- channel: The second argument will be the channel the message was sent to. This will be the same as nickname when this was a private message.
		- nickname: The third argument will be the nickname of the user who sent the message.
		- client: The fourth argument will be the client of the user who sent this message.
		"""
		with self._responseFunctionsLock:
			responseFunction = lambda rnick, rclient, rchannel: self._partResponseFunction(function, rnick, rclient, rchannel, channel, nickname, client, channelFlags, nicknameFlags, clientFlags)
			responseFunctionDict = {
				'func': responseFunction,
				'thread': thread
			}
			self._partResponseFunctions.append(responseFunctionDict)
			return responseFunctionDict
	
	def removePartHandler(self, responseFunction):
		"""
		Remove a function from the list of functions that should be executed on every part.
		
		Arguments:
		responseFunction: Function that is returned by addPartHandler()
		"""
		with self._responseFunctionsLock:
			self._partResponseFunctions.remove(responseFunction)

	def waitForDisconnect(self):
		"""
		Blocks until the bot has disconnected.
		"""
		self._disconnectEvent.wait()
	
	"""
	Internal functions
	"""
	
	def _msgResponseFunction(self, function, msg, nick, client, channel, msgConstraint, channelsConstraint, nicksConstraint, clientsConstraint, msgFlags, channelFlags, nickFlags, clientFlags):
		channelsMatch = re.compile(channelsConstraint, channelFlags).search(channel)
		if not channelsMatch:
			return
		nicksMatch = re.compile(nicksConstraint, nickFlags).search(nick)
		if not nicksMatch:
			return
		clientsMatch = re.compile(clientsConstraint, clientFlags).search(client)
		if not clientsMatch:
			return
		msgMatch = re.compile(msgConstraint, msgFlags).search(msg)
		if not msgMatch:
			return
		
		# If this was a private message, the channel is my own nick
		if channel == self._nick:
			# Set the channel to the other's nick
			channel = nick
		
		function(msg, channel, nick, client, msgMatch)

	def _joinResponseFunction(self, function, nick, client, channel, channelsConstraint, nicksConstraint, clientsConstraint, channelFlags, nickFlags, clientFlags):
		channelsMatch = re.compile(channelsConstraint, channelFlags).search(channel)
		if not channelsMatch:
			return
		nicksMatch = re.compile(nicksConstraint, nickFlags).search(nick)
		if not nicksMatch:
			return
		clientsMatch = re.compile(clientsConstraint, clientFlags).search(client)
		if not clientsMatch:
			return
		function(channel, nick, client)

	def _partResponseFunction(self, function, nick, client, channel, channelsConstraint, nicksConstraint, clientsConstraint, channelFlags, nickFlags, clientFlags):
		channelsMatch = re.compile(channelsConstraint, channelFlags).search(channel)
		if not channelsMatch:
			return
		nicksMatch = re.compile(nicksConstraint, nickFlags).search(nick)
		if not nicksMatch:
			return
		clientsMatch = re.compile(clientsConstraint, clientFlags).search(client)
		if not clientsMatch:
			return		
		function(channel, nick, client)
