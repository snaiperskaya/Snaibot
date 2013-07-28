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
__version__ = '0.5'

import pythonircbot
import configparser
import os
import time

global config
global microLog

def tryBuildConfig():
    if not os.path.exists('settings.ini'):
        print('Building Default settings.ini file...')
        config['SERVER'] = {'botName': '', 'server': '',
                            'channels': ''}
        config['KICK/BAN Settings'] = {'Number of repeat messages before kick': '5',
                                       'Number of kicks before channel ban': '3',
                                       'Naughty words':''}
        with open('settings.ini', 'w') as configfile:
            config.write(configfile)
        print('Basic settings.ini file built. Please configure and restart bot...')
    else:
        print('Config File settings.ini found!')
        
        
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
        
            numTilKick = int(config['KICK/BAN Settings']['number of repeat messages before kick'])
            numTilBan = int(config['KICK/BAN Settings']['number of kicks before channel ban'])
            
            if channel not in microLog:
                microLog[channel] = {client:[msg, 1, 0]}
                
            elif client not in microLog[channel]:
                microLog[channel][client] = [msg, 1, 0]
                
            elif microLog[channel][client][0] == msg and microLog[channel][client][1] >= numTilKick and microLog[channel][client][2] >= (numTilBan - 1):
                snaibot.setMode(channel, client, "b")
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
    return



if __name__ == '__main__':
    
    config = configparser.ConfigParser()
    
    tryBuildConfig()
    config.read('settings.ini')
    
    if config['SERVER']['server'] == '':
        print('ERROR: Please check your settings.ini file...')
    
    snaibot = pythonircbot.Bot(config['SERVER']['botName'])
    snaibot.connect(config['SERVER']['server'], verbose = True)
    
    time.sleep(10)
    
    for channel in confListParser(config['SERVER']['channels']):
        snaibot.joinChannel(channel)
    
    microLog = {}
    
    #snaibot.addMsgHandler(echo)
    snaibot.addMsgHandler(spamFilter)
    
    snaibot.waitForDisconnect()