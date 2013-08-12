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
__version__ = '1.0'

import pythonircbot
import configparser
import os
import time

global config
global microLog
global microLogSwear
global microLogFlood

def tryBuildConfig():
    if not os.path.exists('settings.ini'):
        print('Building Default settings.ini file...')
        
        config['SERVER'] = {'botName': '',
                            'server': '',
                            'channels': '',
                            'password':''}
        
        config['KICK/BAN Settings'] = {'Number of repeat messages before kick': '5',
                                       'Number of kicks before channel ban': '3',
                                       'Naughty words':'fuck,cunt,shit,faggot, f4gg0t,f4ggot,f4g,dick,d1ck,d1ckhead,dickhead,cocksucker,pussy,motherfucker,muthafucker,muthafucka,fucker,fucking,fuckin,fuckhead,fuckface'}
        
        config['Keyword Links'] = {'wiki':'http://ftbwiki.org/Feed_The_Beast_Wiki',
                                   'forum':'http://ftbforums.org/',
                                   'forums':'http://ftbforums.org/',
                                   'style':'http://ftbwiki.org/Feed_The_Beast_Wiki:Style_Guide',
                                   'rules':'http://ftbwiki.org/Feed_The_Beast_Wiki:Policy',
                                   'ftb':'http://goo.gl/j8Fn2b',
                                   'server':'http://ftbforums.org/topic/555-server-details/',
                                   'changes':'http://ftbwiki.org/Special:RecentChanges',
                                   'reddit':'http://www.reddit.com/r/feedthebeast/',
                                   'nocache':'http://nocache.ftbwiki.org/Special:UserLogin',
                                   'vote':'http://ftbwiki.org/Feed_The_Beast_Wiki:Votes_for_Featured_Articles',
                                   'snaibot':'I was built by snaiperskaya for the good of all mankind... and ostPavel.... Yeah...'}
        
        config['NEWS'] = {'News Item':'*Insert Useful News Here*'}
        
        with open('settings.ini', 'w') as configfile:
            config.write(configfile)
        print('Basic settings.ini file built. Please configure and restart bot...')
    else:
        print('Config File settings.ini found!')
        config.read('settings.ini')
        
        
def confListParser(configList):
    l = configList.strip(' ').split(',')
    return l


def opsListBuilder(channel):
    namelist = set()
    namelist.update(snaibot.getVoices(channel))
    namelist.update(snaibot.getHops(channel))
    namelist.update(snaibot.getOps(channel))
    namelist.update(snaibot.getAops(channel))
    namelist.update(snaibot.getOwner(channel))
    return namelist


def echo(msg, channel, nick, client, msgMatch):
    msg = msg + " was said by: " + nick + " on " + client
    snaibot.sendMsg(channel, msg)
    
    
def spamFilter(msg, channel, nick, client, msgMatch):
    
    if channel.upper() in snaibot._channels:
        
        tryOPVoice = opsListBuilder(channel)
        
        if nick not in tryOPVoice:
            
            msg = msg.lower()
        
            numTilKick = int(config['KICK/BAN Settings']['number of repeat messages before kick']) - 1
            numTilBan = int(config['KICK/BAN Settings']['number of kicks before channel ban'])
            
            if channel not in microLog:
                microLog[channel] = {client:[msg, 1, 0]}
                
            elif client not in microLog[channel]:
                microLog[channel][client] = [msg, 1, 0]
                
            elif microLog[channel][client][0] == msg and microLog[channel][client][1] >= numTilKick and microLog[channel][client][2] >= (numTilBan - 1):
                snaibot.banUser(channel, client)
                snaibot.kickUser(channel, nick, 'Spamming (bot)')
                microLog[channel][client][1] = numTilKick - 1
                microLog[channel][client][2] = 0
                
            elif microLog[channel][client][0] == msg and microLog[channel][client][1] >= numTilKick:
                snaibot.kickUser(channel, nick, 'Spamming (bot)')
                microLog[channel][client][1] = numTilKick - 1
                microLog[channel][client][2] = microLog[channel][client][2] + 1
                
            elif microLog[channel][client][0] == msg:
                microLog[channel][client][1] = microLog[channel][client][1] + 1
                
            else:
                microLog[channel][client][0] = msg
                microLog[channel][client][1] = 1
            

def languageKicker(msg, channel, nick, client, msgMatch):
    
    if channel.upper() in snaibot._channels:
        
        tryOPVoice = opsListBuilder(channel)
        
        if nick not in tryOPVoice:    
            
            msg = msg.lower()
            msg = msg.strip('.,!?/@#$^:;*&()\\')
            words = confListParser(config['KICK/BAN Settings']['Naughty words'])
            msglist = msg.split()
            
            numTilKick = 1
            numTilBan = int(config['KICK/BAN Settings']['number of kicks before channel ban'])    
            
            for i in words:
                if i in msglist:
                    if channel not in microLogSwear:
                        microLogSwear[channel] = {client:[1, 0]}
                        snaibot.sendMsg(channel, nick + ": Please watch your language...")
                        
                    elif client not in microLogSwear[channel]:
                        microLogSwear[channel][client] = [1, 0]
                        snaibot.sendMsg(channel, nick + ": Please watch your language...")
                        
                    elif microLogSwear[channel][client][0] >= numTilKick and microLogSwear[channel][client][1] >= numTilBan:
                        snaibot.banUser(channel, client)
                        snaibot.kickUser(channel, nick, 'Swearing (bot)')
                        microLogSwear[channel][client][0] = numTilKick - 1
                        microLogSwear[channel][client][1] = 0
                        
                    elif microLogSwear[channel][client][0] >= numTilKick:
                        snaibot.kickUser(channel, nick, 'Swearing (bot)')
                        microLogSwear[channel][client][0] = numTilKick - 1
                        microLogSwear[channel][client][1] = microLogSwear[channel][client][1] + 1
                        
                    else:
                        microLogSwear[channel][client][0] = microLogSwear[channel][client][0] + 1
                        
                    break
    
    
def showMeLinks(msg, channel, nick, client, msgMatch):
    
    tryBuildConfig()
    
    testmsg = msg.lower()
    try:
        if testmsg == '.help' or testmsg == '.commands' or testmsg == '.options':
            toSend = '.help, .commands, .options, .news'
            for i in config.options('Keyword Links'):
                toSend = toSend + ', .' + i
            snaibot.sendMsg(channel, nick + ": " + toSend)
        
        elif testmsg.split()[0] == '.news':
            try:
                if testmsg.split()[1] == 'edit':
                    tryOPVoice = opsListBuilder(channel)
                    if nick in tryOPVoice:
                        news = ''
                        for i in msg.split()[2:]:
                            news = news + ' ' + i
                        config['NEWS']['News Item'] = news[1:]
                        with open('settings.ini', 'w') as configfile:
                            config.write(configfile)
                        snaibot.sendMsg(channel, 'News Updated in Config!')
                            
                    else:
                        snaibot.sendMsg(channel, config['NEWS']['News Item'])
            except:
                snaibot.sendMsg(channel, config['NEWS']['News Item'])
        
        elif testmsg[0] == '.':
            
            try:
                toSend = config['Keyword Links'][msg[1:]]
                snaibot.sendMsg(channel, nick + ": " + toSend)
                
            except:
                return
    except:
        return


if __name__ == '__main__':
    
    config = configparser.ConfigParser()
    
    tryBuildConfig()
    
    if config['SERVER']['server'] == '':
        print('ERROR: Please check your settings.ini file...')
    
    snaibot = pythonircbot.Bot(config['SERVER']['botName'])
    snaibot.connect(config['SERVER']['server'], verbose = True)
    
    os.system("title {} on {} in channels: {}".format(config['SERVER']['botName'], config['SERVER']['server'], config['SERVER']['channels'].replace(',', ', ')))
    
    time.sleep(20)
    
    snaibot.sendMsg('NickServ','IDENTIFY ' + config['SERVER']['password'])
    
    for channel in confListParser(config['SERVER']['channels']):
        snaibot.joinChannel(channel)
        print(snaibot._channels)
    
    microLog = {}
    microLogSwear = {}
    microLogFlood = {}
    
    #snaibot.addMsgHandler(echo)
    snaibot.addMsgHandler(spamFilter)
    snaibot.addMsgHandler(languageKicker)
    snaibot.addMsgHandler(showMeLinks)
    
    snaibot.waitForDisconnect()
