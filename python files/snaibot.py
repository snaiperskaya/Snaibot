#!python3

#    snaibot, Python 3-based IRC utility bot
#    Copyright (C) 2013  C.S.Putnam
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


__author__ = 'C.S.Putnam'
__version__ = '3.0'

import pythonircbot
import configparser
import os
import time
import random


class snaibot():
    def __init__(self, configfile):
        '''Initializes snaibot object. Requires only the filename for a settings.ini file in the same folder, which it will either read from (if found) or build (if not found). Default settings.ini file will not be sufficient to run bot program and will require configuration.'''
        
        self.config = configparser.ConfigParser()
        self.configfile = configfile
        self.tryBuildConfig(True)
        self.microLog = {}
        self.modulestate = {}
        
        self.moduleref = {'normal links':self.showNormalLinks,
                            'secret links':self.showSecretLinks,
                            'mod info':self.showModInfo,
                            'language filter':self.languageKicker,
                            'spam filter':self.spamFilter,
                            'news':self.news,
                            'choose':self.choose,
                            'admin':self.remoteAdmin,
                            'wiki':self.searchWiki}
                            #'listening':'',
                            #'speech':''}        
        
        self.bot = pythonircbot.Bot(self.config['SERVER']['botName'], self.config['SERVER']['password'])
        self.bot.connect(self.config['SERVER']['server'], verbose = True)
        
        os.system("title {} on {} in channels: {}".format(self.config['SERVER']['botName'], self.config['SERVER']['server'], self.config['SERVER']['channels'].replace(',', ', ')))
        
        time.sleep(int(self.config['SERVER']['timeout']))
        
        for channel in self.confListParser(self.config['SERVER']['channels']):
            self.bot.joinChannel(channel)
            print(self.bot._channels)
        
        self.microLog = {}
        self.microSwearLog = {}
        
        self.updateModules()
        
        self.bot.addMsgHandler(self.help)
        
        self.bot.waitForDisconnect()
        
        
    def getTestMsg(self, nick, msg):
        '''New function to allow parsing of msg from IRC bot for gameserver. Takes a msg and original sending nick and attempts to parse out a message and nick from a CraftIRC bot. Returns a tuple of (nick, lowermsg, origmsg)'''
        
        try:
            splitnick = msg.split('> ')
            newnick = splitnick[0][1:]
            newmsg = splitnick[1]
        except:
            newnick = nick
            newmsg = msg
        return (newnick, newmsg.lower(), newmsg)
        
        
    def tryBuildConfig(self, firstRun = False):
        '''Attempts to find the config file. Will load if found or build a default if not found.'''
        
        if firstRun == True:
            self.config['SERVER'] = {'botName': 'snaibot',
                                    'server': '',
                                    'channels': '',
                                    'password':'',
                                    'timeout':'10'}
                
            self.config['Modules'] = {'Normal Links':'False',
                                    'Secret Links':'False',
                                    'Mod Info':'False',
                                    'Language Filter':'False',
                                    'Spam Filter':'False',
                                    'News':'False',
                                    'Choose':'False',
                                    'Admin':'False',
                                    'Wiki':'False'}
            
            self.config['KICK/BAN Settings'] = {'Number of repeat messages before kick': '5',
                                           'Number of kicks before channel ban': '5',
                                           'Naughty words':'fuck,cunt,shit,faggot, f4gg0t,f4ggot,f4g,dick,d1ck,d1ckhead,dickhead,cocksucker,pussy,motherfucker,muthafucker,muthafucka,fucker,fucking,fuckin,fuckhead,fuckface'}
            
            self.config['Keyword Links'] = {'source':'https://github.com/snaiperskaya/Snaibot/',
                                       'snaibot':'I was built by snaiperskaya for the good of all mankind...'}
            
            self.config['Mod Links'] = {'modname':'*link to mod*,*mod version*'}
            
            self.config['Secret Links'] = {'secret':'These links will not show up in .commands and will only send via query.'}
            
            self.config['NEWS'] = {'News Item':'*Insert Useful News Here*'}
            
            self.config['Admin'] = {'Admin Nicks':'snaiperskaya'}
        
        if not os.path.exists(self.configfile):
            print('Building Default settings.ini file...')
                      
            with open(self.configfile, 'w') as confile:
                self.config.write(confile)
                confile.close()
            print('Basic settings.ini file built. Please configure and restart bot...')
            
        else:
            self.config.remove_section('Mod Links')
            self.config.remove_section('Keyword Links')
            self.config.remove_section('Secret Links')
            self.config.read(self.configfile)
            if firstRun == True:
                with open(self.configfile, 'w') as confile:
                    self.config.write(confile)
                    confile.close()
            print('Config File found and updated!')
            
            
    def confListParser(self, configList):
        '''Micro function to convert a comma-separated String into a usable list. Used for parsing lists entered into settings file.'''
        
        l = configList.replace(' ','').split(',')
        return l
    
    def opsListBuilder(self, channel, level = 'o'):
        '''Scans the channel and returns a set containing all people with elevated privledges in the channel specified. Level allows specification of minimum priledge level to include. Default will be "o" (OPS+), but other options will be "v" (Voice+), "h" (HOPS+), "a" (AOPS+), and "own" (Owner only). Note that some servers only consider some of these (some only use OP and Voice, in which case use of "h" would still only include Voice).'''
        lev = level.lower()
        namelist = set()
        if lev not in ['own','a','o','h','v']:
            lev = 'o' #conditional to force OP+ if level unrecognized
        
        if lev == 'v':
            namelist.update(self.bot.getVoices(channel))
            namelist.update(self.bot.getHops(channel))
            namelist.update(self.bot.getOps(channel))
            namelist.update(self.bot.getAops(channel))
            namelist.update(self.bot.getOwner(channel))
        elif lev == 'h':
            namelist.update(self.bot.getHops(channel))
            namelist.update(self.bot.getOps(channel))
            namelist.update(self.bot.getAops(channel))
            namelist.update(self.bot.getOwner(channel))
        elif lev == 'o':
            namelist.update(self.bot.getOps(channel))
            namelist.update(self.bot.getAops(channel))
            namelist.update(self.bot.getOwner(channel))
        elif lev == 'a':
            namelist.update(self.bot.getAops(channel))
            namelist.update(self.bot.getOwner(channel))
        elif lev == 'own':
            namelist.update(self.bot.getOwner(channel))
        
        print(namelist)
        return namelist    
    
    
    def updateModules(self):
        '''NEW TO SNAIBOT 3.0: This will form the backbone of the new modular design. This will update the settings from the config and attempt to turn on or off modules based on those settings. If a module is not properly marked as true or false in the config, it will set it to false automatically.'''
        
        self.tryBuildConfig()
        
        modules = self.config['Modules']
        
        for module in self.moduleref.keys():
            if modules[module].lower() == 'true' or modules[module].lower() == 'false':
                if modules[module].lower() == 'true':
                    try:
                        test = self.modulestate[module]
                    except:
                        self.modulestate[module] = self.bot.addMsgHandler(self.moduleref[module])
                elif modules[module].lower() == 'false':
                    try:
                        self.bot.removeMsgHandler(self.modulestate.pop(module))
                    except:
                        pass
            else:
                self.config['Modules'][module] = 'False'
                with open(self.configfile, 'w') as configfile:
                    self.config.write(configfile)
                    configfile.close()

    def stripped(self, x):
        '''Helper function for the language filter. Strips extra-extraneous characters from string x and returns it.'''
        return "".join([i for i in x if ord(i) in range(32, 127)])
                         
    """
    FUNCTIONS FOR MSG HANDLERS. (All must contain arguements for self, msg, channel, nick, client, msgMatch)
    """
    
    
    def echo(self, msg, channel, nick, client, msgMatch):
        '''Simple parser for testing purposes. Will repeat msg with nick and client into chat.'''
        
        msg = msg + " was said by: " + nick + " on " + client
        self.bot.sendMsg(channel, msg)
        
        
    def help(self, msg, channel, nick, client, msgMatch):
        '''Builds help command based on loaded modules. This will always run regardless of other modules loaded.'''
        
        self.updateModules()
        parsemsg = self.getTestMsg(nick, msg)
        nick = parsemsg[0]
        testmsg = parsemsg[1]
        msg = parsemsg[2]
        modules = self.config['Modules']
        if testmsg == '.help' or testmsg == '.commands' or testmsg == '.options' or testmsg == '*commands'or testmsg == '*options' or testmsg == '*help':
            toSend = '*commands, *help'
            
            if modules['News'].lower() == 'true':
                toSend = toSend + ', *news'
                
            if modules['Mod Info'].lower() == 'true':
                toSend = toSend + ', *mods'
                
            if modules['Normal Links'].lower() == 'true':
                for i in self.config.options('Keyword Links'):
                    toSend = toSend + ', *' + i
                    
            if modules['Choose'].lower() == 'true':
                toSend = toSend + ', *choose <opt1;opt2;etc>'
                
            if modules['Wiki'].lower() == 'true':
                toSend = toSend + ', *ftbwiki <searchterm>'            
            
            self.bot.sendMsg(channel, nick + ": " + toSend)            
    

    def news(self, msg, channel, nick, client, msgMatch):
        '''Module and reading and editing latest news story. Edit only available to OP+.'''
        
        parsemsg = self.getTestMsg(nick, msg)
        nick = parsemsg[0]
        testmsg = parsemsg[1]
        msg = parsemsg[2]
        if testmsg.split(' ')[0] == '*news':
            try:
                if testmsg.split(' ')[1] == 'edit':
                    tryOPVoice = self.opsListBuilder(channel)
                    if nick in tryOPVoice:
                        news = ''
                        for i in msg.split(' ')[2:]:
                            news = news + ' ' + i
                        self.config['NEWS']['News Item'] = news[1:]
                        with open(self.configfile, 'w') as configfile:
                            self.config.write(configfile)
                            configfile.close()
                        self.bot.sendMsg(channel, 'News Updated in Config!')
                            
                    else:
                        self.bot.sendMsg(channel, self.config['NEWS']['News Item'])
            except:
                self.bot.sendMsg(channel, self.config.get('NEWS','News Item'))        
        

    def showNormalLinks(self, msg, channel, nick, client, msgMatch):
        '''Parses list for links from Keyword Links and returns them to chat if found.'''
        
        parsemsg = self.getTestMsg(nick, msg)
        nick = parsemsg[0]
        testmsg = parsemsg[1]
        msg = parsemsg[2]
        try:
            if testmsg[0] == '*':
                    toSend = self.config['Keyword Links'][testmsg[1:]]
                    self.bot.sendMsg(channel, nick + ": " + toSend)
        except:
            return


    def showSecretLinks(self, msg, channel, nick, client, msgMatch):
        '''Parses list for links from Secret Links and sends them directly to nick in query if found.'''
        
        parsemsg = self.getTestMsg(nick, msg)
        nick = parsemsg[0]
        testmsg = parsemsg[1]
        msg = parsemsg[2]
        try:
            toSend = self.config['Secret Links'][testmsg[1:]]
            self.bot.sendMsg(nick, nick + ": " + toSend)
            self.bot.sendMsg(nick, "Shhh... It's a seekrit!")
        except:
            return        


    def showModInfo(self, msg, channel, nick, client, msgMatch):
        '''Parses msgs for mod-related commands and returns the appropriate info.'''
        
        parsemsg = self.getTestMsg(nick, msg)
        nick = parsemsg[0]
        testmsg = parsemsg[1].split(' ')
        msg = parsemsg[2]        
        
        try:
            if testmsg[0] == '*mod' or testmsg[0] == '*mods':
                toSend = ''
                modlist = []
                for i in self.config.options('Mod Links'):
                    modlist.append(i)
                modlist.sort()
                numsends = len(modlist) / 20
                count = 1
                place = 0
                while count < numsends:
                    toSend = '*' + modlist[place]
                    for i in modlist[place + 1:place + 19]:
                        toSend = toSend + ', *' + i
                    self.bot.sendMsg(nick,toSend)
                    place = place + 20
                    count = count + 1
                toSend = '*' + modlist[place]
                try:
                    for i in modlist[place + 1:]:
                        toSend = toSend + ', *' + i
                except:
                    pass
                self.bot.sendMsg(nick,toSend)
                
            elif testmsg[0][0] == '*':
                    
                    try:
                        toSend = self.config['Mod Links'][testmsg[0][1:]]
                        toSend = toSend.strip(' ').split(',')
                        try:
                            if testmsg[1] == 'show':
                                self.bot.sendMsg(channel, nick + ": " + toSend[0] + ' - Current server version is: ' + toSend[1])
                            else:
                                self.bot.sendMsg(nick, nick + ": " + toSend[0] + ' - Current server version is: ' + toSend[1])
                        except:
                            self.bot.sendMsg(nick, nick + ": " + toSend[0] + ' - Current server version is: ' + toSend[1])
                    except:
                        return
        except:
            return        

    def choose(self, msg, channel, nick, client, msgMatch):
        '''Takes a string of arguments from chat that are ;-separated and picks one at random.'''
        
        parsemsg = self.getTestMsg(nick, msg)
        nick = parsemsg[0]
        testmsg = parsemsg[1]
        msg = parsemsg[2]
        if testmsg[:7] == '*choose':
            try:
                toParse = msg[7:].rstrip().lstrip()
                parList = toParse.split(';')
                final = []
                for item in parList:
                    final.append(item.rstrip().lstrip())
                toSend = random.choice(final)
                self.bot.sendMsg(channel, nick + ": I think you should pick...    " + toSend)
            except:
                pass


    def spamFilter(self, msg, channel, nick, client, msgMatch):
        '''Parses chat and weeds out repeat lines from a nick as *spam*. Kicks and bans can be issued by an OP'd bot at intervals specified in config. Will ignore OP or Voiced nicks.'''
        
        if channel.upper() in self.bot._channels:
            
            tryOPVoice = self.opsListBuilder(channel,'v')
            
            if nick not in tryOPVoice:
                
                msg = msg.lower()
            
                numTilKick = int(self.config['KICK/BAN Settings']['number of repeat messages before kick']) - 1
                numTilBan = int(self.config['KICK/BAN Settings']['number of kicks before channel ban'])
                
                if channel not in self.microLog:
                    self.microLog[channel] = {client:[msg, 1, 0]}
                    
                elif client not in self.microLog[channel]:
                    self.microLog[channel][client] = [msg, 1, 0]
                    
                elif self.microLog[channel][client][0] == msg and self.microLog[channel][client][1] >= numTilKick and self.microLog[channel][client][2] >= (numTilBan - 1):
                    self.bot.banUser(channel, client)
                    self.bot.kickUser(channel, nick, 'Spamming (bot)')
                    self.microLog[channel][client][1] = numTilKick - 1
                    self.microLog[channel][client][2] = 0
                    
                elif self.microLog[channel][client][0] == msg and self.microLog[channel][client][1] >= numTilKick:
                    self.bot.kickUser(channel, nick, 'Spamming (bot)')
                    self.microLog[channel][client][1] = numTilKick - 1
                    self.microLog[channel][client][2] = self.microLog[channel][client][2] + 1
                    
                elif self.microLog[channel][client][0] == msg:
                    self.microLog[channel][client][1] = self.microLog[channel][client][1] + 1
                    
                else:
                    self.microLog[channel][client][0] = msg
                    self.microLog[channel][client][1] = 1


    def languageKicker(self, msg, channel, nick, client, msgMatch):
        '''Module to parse language in chat and log usage of "bad words" (as defined in config). Kicks and Bans based on config file.'''
        
        if channel.upper() in self.bot._channels:
            
            tryOPVoice = self.opsListBuilder(channel,'v')
            
            if nick not in tryOPVoice:    
                
                msg = msg.lower()
                msg = self.stripped(msg)
                msg = msg.strip('.,!?/@#$^:;*&()\\ -_')
                
                words = self.confListParser(self.config['KICK/BAN Settings']['Naughty words'])
                #msglist = msg.split()
                
                numTilKick = 1
                numTilBan = int(self.config['KICK/BAN Settings']['number of kicks before channel ban'])    
                
                for i in words:
                    if i in msg:
                        if channel not in self.microSwearLog:
                            self.microSwearLog[channel] = {client:[1, 0]}
                            self.bot.sendMsg(channel, nick + ": Please watch your language...")
                            
                        elif client not in self.microSwearLog[channel]:
                            self.microSwearLog[channel][client] = [1, 0]
                            self.bot.sendMsg(channel, nick + ": Please watch your language...")
                            
                        elif self.microSwearLog[channel][client][0] >= numTilKick and self.microSwearLog[channel][client][1] >= numTilBan:
                            self.bot.banUser(channel, client)
                            self.bot.kickUser(channel, nick, 'Swearing (bot)')
                            self.microSwearLog[channel][client][0] = numTilKick - 1
                            self.microSwearLog[channel][client][1] = 0
                            
                        elif self.microSwearLog[channel][client][0] >= numTilKick:
                            self.bot.sendMsg(channel, nick + ": Please watch your language...")
                            self.bot.kickUser(channel, nick, 'Swearing (bot)')
                            self.microSwearLog[channel][client][0] = numTilKick - 1
                            self.microSwearLog[channel][client][1] = self.microSwearLog[channel][client][1] + 1
                            
                        else:
                            self.microSwearLog[channel][client][0] = self.microSwearLog[channel][client][0] + 1
                            self.bot.sendMsg(channel, nick + ": Please watch your language...")
                            
                        break
                    
    def remoteAdmin(self, msg, channel, nick, client, msgMatch):
        '''Module to allow command-based administration via chat from those either registered as admins in the config or those with OP+'''
        
        parsemsg = self.getTestMsg(nick, msg)
        nick = parsemsg[0]
        testmsg = parsemsg[1]
        msg = parsemsg[2]
        configAdmin = self.confListParser(self.config['Admin']['Admin Nicks'])
        try:
            if channel.upper() in self.bot._channels:
                chanOPList = self.opsListBuilder(channel)
                if self.bot._nick in chanOPList:
                    if nick in configAdmin or nick in chanOPList:
                        if testmsg == '*admin':
                            self.bot.sendMsg(nick, 'The following administrative commands are available in {}: Set modes (*v <nick>, *h <nick>, *o <nick>), Un-set Modes (*dv <nick>, *dh <nick>, *do <nick>), *kick <nick>, *join <channel>, *leave <channel>, *identify'.format(channel))     
                        elif testmsg == '*identify':
                            self.bot.verifyNick(self.config['SERVER']['password'])
                        elif testmsg.split()[0] == '*join':
                            chan = testmsg.split()[1]
                            if chan[0] == '#':
                                self.bot.joinChannel(chan)
                            else:
                                self.bot.sendMsg(nick, 'Not a valid channel...')
                        elif testmsg.split()[0] == '*leave':
                            chan = testmsg.split()[1]
                            if chan[0] == '#':
                                self.bot.partChannel(chan)
                            else:
                                self.bot.sendMsg(nick, 'Not a valid channel...')
                        elif testmsg.split()[0] == '*kick':
                            self.bot.kickUser(channel, testmsg.split()[1], 'Requested by {}'.format(nick))
                        elif testmsg.split()[0] == '*v':
                            self.bot.setMode(channel, testmsg.split()[1], 'v')
                        elif testmsg.split()[0] == '*h':
                            self.bot.setMode(channel, testmsg.split()[1], 'h')
                        elif testmsg.split()[0] == '*o':
                            self.bot.setMode(channel, testmsg.split()[1], 'o')
                        elif testmsg.split()[0] == '*dv':
                            self.bot.unsetMode(channel, testmsg.split()[1], 'v')
                        elif testmsg.split()[0] == '*dh':
                            self.bot.unsetMode(channel, testmsg.split()[1], 'h')
                        elif testmsg.split()[0] == '*do':
                            self.bot.unsetMode(channel, testmsg.split()[1], 'o')                        
                            
                else:
                    if testmsg == '*admin':
                        self.bot.sendMsg(nick, 'Bot not OPed in {}! The following administrative commands are available: *join <channel>, *leave <channel>, *identify'.format(channel))
                    elif testmsg == '*identify':
                        self.bot.verifyNick(self.config['SERVER']['password'])
                    elif testmsg.split()[0] == '*join':
                        chan = testmsg.split()[1]
                        if chan[0] == '#':
                            self.bot.joinChannel(chan)
                        else:
                            self.bot.sendMsg(nick, 'Not a valid channel...')
                    elif testmsg.split()[0] == '*leave':
                        chan = testmsg.split()[1]
                        if chan[0] == '#':
                            self.bot.partChannel(chan)
                        else:
                            self.bot.sendMsg(nick, 'Not a valid channel...')                 
            
            else:
                if nick in configAdmin:
                    if testmsg == '*admin':
                        self.bot.sendMsg(nick, 'The following administrative commands are available: *join <channel>, *leave <channel>, *identify')
                    elif testmsg == '*identify':
                        self.bot.verifyNick(self.config['SERVER']['password'])
                    elif testmsg.split()[0] == '*join':
                        chan = testmsg.split()[1]
                        if chan[0] == '#':
                            self.bot.joinChannel(chan)
                        else:
                            self.bot.sendMsg(nick, 'Not a valid channel...')
                    elif testmsg.split()[0] == '*leave':
                        chan = testmsg.split()[1]
                        if chan[0] == '#':
                            self.bot.partChannel(chan)
                        else:
                            self.bot.sendMsg(nick, 'Not a valid channel...')
                            
        except:
            pass
        
    def searchWiki(self, msg, channel, nick, client, msgMatch):
        '''Module allows for searching FTBWiki.org for articles. Bot is largely used for a Minecraft Community, so this was extremely helpful as a resource.'''
        parsemsg = self.getTestMsg(nick, msg)
        nick = parsemsg[0]
        testmsg = parsemsg[1]
        msg = parsemsg[2]
        if testmsg[:8] == '*ftbwiki':
            toParse = msg[8:].rstrip().lstrip()
            parList = toParse.split(' ')
            if parList[0] != '':
                term1 = parList.pop(0)
                term1 = term1[:1].upper() + term1[1:]
                searchTerm = term1
                instantURL = term1
                for i in parList:
                    term = i
                    term = term[:1].upper() + term[1:]
                    searchTerm = searchTerm + '+' + term
                    instantURL = instantURL + '_' + term
                searchURL = 'http://ftbwiki.org/index.php?search=' + searchTerm
                fullURL = 'http://ftbwiki.org/' + instantURL
                self.bot.sendMsg(channel, nick + ": Try this link: " + fullURL + ' or click here for full search results: ' + searchURL + '&fulltext=1')