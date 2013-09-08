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
        self.tryBuildConfig()
        self.microLog = {}
        self.modulestate = {}
        
        self.moduleref = {'normal links':self.showNormalLinks,
                            'secret links':self.showSecretLinks,
                            'mod info':self.showModInfo,
                            'language filter':self.languageKicker,
                            'spam filter':self.spamFilter,
                            'news':self.news,
                            'choose':self.choose}   
        
        self.bot = pythonircbot.Bot(self.config['SERVER']['botName'])
        self.bot.connect(self.config['SERVER']['server'], verbose = True)
        
        os.system("title {} on {} in channels: {}".format(self.config['SERVER']['botName'], self.config['SERVER']['server'], self.config['SERVER']['channels'].replace(',', ', ')))
        
        time.sleep(int(self.config['SERVER']['timeout']))
        
        self.bot.sendMsg('NickServ','IDENTIFY ' + self.config['SERVER']['password'])
        
        for channel in self.confListParser(self.config['SERVER']['channels']):
            self.bot.joinChannel(channel)
            print(self.bot._channels)
        
        self.microLog = {}
        self.microSwearLog = {}
        
        self.bot.addMsgHandler(self.help)
        
        self.bot.waitForDisconnect()
        
        
    def tryBuildConfig(self):
        '''Attempts to find the config file. Will load if found or build a default if not found.'''
        
        if not os.path.exists(self.configfile):
            print('Building Default settings.ini file...')
            
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
                                    'Choose':'False'}
            
            self.config['KICK/BAN Settings'] = {'Number of repeat messages before kick': '5',
                                           'Number of kicks before channel ban': '5',
                                           'Naughty words':'fuck,cunt,shit,faggot, f4gg0t,f4ggot,f4g,dick,d1ck,d1ckhead,dickhead,cocksucker,pussy,motherfucker,muthafucker,muthafucka,fucker,fucking,fuckin,fuckhead,fuckface'}
            
            self.config['Keyword Links'] = {'source':'http://snaiperskaya.github.io/Snaibot',
                                       'snaibot':'I was built by snaiperskaya for the good of all mankind...'}
            
            self.config['Mod Links'] = {'modname':'*link to mod*,*mod version*'}
            
            self.config['Secret Links'] = {'secret':'These links will not show up in .commands and will only send via query.'}
            
            self.config['NEWS'] = {'News Item':'*Insert Useful News Here*'}
            
            with open(self.configfile, 'w') as confile:
                self.config.write(confile)
            print('Basic settings.ini file built. Please configure and restart bot...')
        else:
            print('Config File found!')
            self.config.read(self.configfile)
            
            
    def confListParser(self, configList):
        '''Micro function to convert a comma-separated String into a usable list. Used for parsing lists entered into settings file.'''
        
        l = configList.strip(' ').split(',')
        return l
    
    
    def opsListBuilder(self, channel):
        '''Scans the channel and returns a set containing all people with elevated privledges in the channel specified. Currently includes those with Voice, but this may be spun off in future to accommodate new features.'''
        
        namelist = set()
        namelist.update(self.bot.getVoices(channel))
        namelist.update(self.bot.getHops(channel))
        namelist.update(self.bot.getOps(channel))
        namelist.update(self.bot.getAops(channel))
        namelist.update(self.bot.getOwner(channel))
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
        testmsg = msg.lower()
        modules = self.config['Modules']
        if testmsg == '.help' or testmsg == '.commands' or testmsg == '.options':
            toSend = '.commands'
            
            if modules['News'].lower() == 'true':
                toSend = toSend + ', .news'
                
            if modules['Mod Info'].lower() == 'true':
                toSend = toSend + ', .mods'  
                
            if modules['Normal Links'].lower() == 'true':
                for i in self.config.options('Keyword Links'):
                    toSend = toSend + ', .' + i
                    
            if modules['Choose'].lower() == 'true':
                toSend = toSend + ', .choose'             
            
            self.bot.sendMsg(channel, nick + ": " + toSend)            
    

    def news(self, msg, channel, nick, client, msgMatch):
        '''Module and reading and editing latest news story. Edit only available to OP/Voice+.'''
        
        testmsg = msg.lower()
        if testmsg.split()[0] == '.news':
            try:
                if testmsg.split()[1] == 'edit':
                    tryOPVoice = self.opsListBuilder(channel)
                    if nick in tryOPVoice:
                        news = ''
                        for i in msg.split()[2:]:
                            news = news + ' ' + i
                        self.config['NEWS']['News Item'] = news[1:]
                        with open(self.configfile, 'w') as configfile:
                            self.config.write(configfile)
                        self.bot.sendMsg(channel, 'News Updated in Config!')
                            
                    else:
                        self.bot.sendMsg(channel, self.config['NEWS']['News Item'])
            except:
                self.bot.sendMsg(channel, self.config['NEWS']['News Item'])        
        

    def showNormalLinks(self, msg, channel, nick, client, msgMatch):
        '''Parses list for links from Keyword Links and returns them to chat if found.'''
        
        testmsg = msg.lower()
        try:
            if testmsg[0] == '.':
                    toSend = self.config['Keyword Links'][testmsg[1:]]
                    self.bot.sendMsg(channel, nick + ": " + toSend)
        except:
            return


    def showSecretLinks(self, msg, channel, nick, client, msgMatch):
        '''Parses list for links from Secret Links and sends them directly to nick in query if found.'''
        
        testmsg = msg.lower()
        try:
            toSend = self.config['Secret Links'][testmsg[1:]]
            self.bot.sendMsg(nick, nick + ": " + toSend)
            self.bot.sendMsg(nick, "Shhh... It's a seekrit!")
        except:
            return        


    def showModInfo(self, msg, channel, nick, client, msgMatch):
        '''Parses msgs for mod-related commands and returns the appropriate info.'''
        
        testmsg = msg.lower().split(' ')
        
        try:
            if testmsg[0] == '.mod' or testmsg[0] == '.mods':
                toSend = ''
                modlist = []
                for i in self.config.options('Mod Links'):
                    modlist.append(i)
                modlist.sort()
                numsends = len(modlist) / 20
                count = 1
                place = 0
                while count < numsends:
                    toSend = modlist[place]
                    for i in modlist[place + 1:place + 19]:
                        toSend = toSend + ', .' + i
                    self.bot.sendMsg(nick,toSend)
                    place = place + 20
                    count = count + 1
                toSend = modlist[place]
                try:
                    for i in modlist[place + 1:]:
                        toSend = toSend + ', .' + i
                except:
                    pass
                self.bot.sendMsg(nick,toSend)
                
            elif testmsg[0][0] == '.':
                    
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
        
        testmsg = msg.lower()
        if testmsg[:7] == '.choose':
            try:
                toParse = testmsg[7:].rstrip().lstrip()
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
            
            tryOPVoice = self.opsListBuilder(channel)
            
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
            
            tryOPVoice = self.opsListBuilder(channel)
            
            if nick not in tryOPVoice:    
                
                msg = msg.lower()
                msg = msg.strip('.,!?/@#$^:;*&()\\')
                words = self.confListParser(self.config['KICK/BAN Settings']['Naughty words'])
                msglist = msg.split()
                
                numTilKick = 1
                numTilBan = int(self.config['KICK/BAN Settings']['number of kicks before channel ban'])    
                
                for i in words:
                    if i in msglist:
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
                            self.bot.kickUser(channel, nick, 'Swearing (bot)')
                            self.microSwearLog[channel][client][0] = numTilKick - 1
                            self.microSwearLog[channel][client][1] = self.microSwearLog[channel][client][1] + 1
                            
                        else:
                            self.microSwearLog[channel][client][0] = self.microSwearLog[channel][client][0] + 1
                            
                        break