from core import meminfo
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.enterprise import adbapi
import time, re, traceback, os, classloader, config, gc
import MySQLdb.cursors
import sqlite3

class UusipuuModule(object):
    
    def __init__(self, bot, channel):
        self.bot = bot
        self.channel = channel.lower()
        self.name = self.__module__.split('.')[-1]
        self.scheduled = {}
        chanconf = self.bot.config[channel.lower()]
        if self.name not in chanconf:
            chanconf[self.name] = {}
        self.config = chanconf[self.name]
        self.startup()

    def shutdown(self):
        pass

    def startup(self):
        pass

    def privmsg(self, user, target, msg):
        pass

    def _shutdown(self):
        self.log('Shutting down')
        for s in self.scheduled:
            if type(self.scheduled[s]) == type([]):
                l = self.scheduled[s]
            else:
                l = [self.scheduled[s]]
            for i in l:
                if i.called:
                    continue
                self.log('Unscheduling %s' % repr(i))
                i.cancel()
        self.shutdown()

    def _privmsg(self, user, target, msg):
        pieces = msg.strip().split(' ', 1)
        if target == self.channel and len(msg.strip()) and \
                pieces[0][0] == '!':
            mname = 'cmd_' + pieces[0][1:]
            if hasattr(self, mname):
                params = ''
                if len(pieces) > 1: params = pieces[1]
                getattr(self, mname)(user, target, params)
        self.privmsg(user, target, msg)

    def save(self):
        self.bot.save()

    def chanmsg(self, msg):
        self.bot.msg(self.channel, msg)

    def log(self, msg):
        self.bot.log(msg, '%s:%s' % (self.name, self.channel))

    # This is stupid, modules can now only have 1 db connection
    def db_open(self, name, dbfile):
        if not self.bot.dbs.has_key(name):
            self.bot.dbs[name] = {}
            self.log('Opening new adbapi ConnectionPool %s' % name)
            mem = self.bot.memstart()
            #self.bot.dbs[name]['db'] = adbapi.ConnectionPool("MySQLdb",
            #    host = self.bot.factory.cfg.get('MySQL', 'server'),
            #    db = self.bot.factory.cfg.get('MySQL', name),
            #    user = self.bot.factory.cfg.get('MySQL', 'user'),
            #    passwd = self.bot.factory.cfg.get('MySQL', 'password'),
            #    cursorclass = MySQLdb.cursors.DictCursor,
            #    cp_min = 1,
            #    cp_max = 1,
            #    cp_reconnect = True)
            def setRowFactory(connection):
                connection.row_factory = sqlite3.Row
            self.bot.dbs[name]['db'] = adbapi.ConnectionPool(
                "sqlite3",
                dbfile,
                check_same_thread=False,
                cp_openfun=setRowFactory)
            self.bot.memend(mem)
            self.bot.dbs[name]['refs'] = []
        self.bot.dbs[name]['refs'].append('%s_%s' % (self.channel, self.name))
        self.db = self.bot.dbs[name]['db']

    def db_close(self, name):
        mem = self.bot.memstart()
        self.bot.dbs[name]['refs'].remove('%s_%s' % (self.channel, self.name))
        if not len(self.bot.dbs[name]['refs']):
            print dir(self.bot.dbs[name]['db'])
            self.bot.dbs[name]['db'].close()
            del self.db
            del self.bot.dbs[name]
        self.bot.memend(mem)

class Uusipuu(irc.IRCClient):

    def memstart(self):
        return meminfo.memory()

    def memend(self, mem_before):
        mem_after = meminfo.memory()

        if mem_after > mem_before:
            mem_msg = 'Memory increased by %d bytes.' % \
                (mem_after - mem_before)
        elif mem_after < mem_before:
            mem_msg = 'Memory decreased by %d bytes.' % \
                (mem_before - mem_after)
        else:
            mem_msg = 'Memory didn\'t change.'
        print mem_msg

    def log(self, msg, realm = 'core'):
        output = '[%s] (%s) %s' % (time.strftime('%T'), realm, msg)
        print output
        f = file('uusipuu.log', 'a')
        f.write('%s\n' % output)
        f.close()

    def save(self):
        mem = self.memstart()
        s = config.save(self.config)
        if s:
            cfg_file = os.path.join(
                self.factory.cfg.get('General', 'data_path'),
                'config.xml')
            f = file(cfg_file, 'w')
            f.write(s)
            f.close()
        self.memend(mem)

    def is_admin(self, hostmask):
        re_admin = re.compile(self.factory.cfg.get('Server', 'admin'))
        if re_admin.match(hostmask):
            return True
        return False

    def connectionMade(self):
        self.nickname = self.factory.nickname
        self.realname = self.factory.realname
        self.versionName = self.factory.versionName
        self.versionNum = self.factory.versionNum
        self.sourceURL = self.factory.sourceURL
        if self.factory.cfg.has_option('Server', 'password'):
            self.password = self.factory.cfg.get('Server', 'password')
        irc.IRCClient.connectionMade(self)
        self.log('connected at %s' % \
            time.asctime(time.localtime(time.time())))
        self.channels = {}
        self.ignorenicks = []

    def signedOn(self):
        self.channels = {}
        self.config = {}
        self.dbs = {}

        cfg_file = os.path.join(
            self.factory.cfg.get('General', 'data_path'),
            'config.xml')
        if os.path.exists(cfg_file):
            f = file(cfg_file)
            self.config = config.load(f.read())
            f.close()

        if 'onload' not in self.config:
            self.config['onload'] = {}
        if 'channels' not in self.config['onload']:
            self.config['onload']['channels'] = {}

        for channel in self.config['onload']['channels'].keys():
            print 'I would like to join %s' % channel
            self.join(channel)

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        self.log('disconnected at %s' % \
            time.asctime(time.localtime(time.time())))

    # callbacks for events

    def privmsg(self, user, target, msg):
        nick = user.split('!', 1)[0]
        target = target.lower()
        pieces = msg.split(' ', 1)

        if nick.lower() in self.ignorenicks:
            return

        if target == self.nickname:
            # non-channel commands
            mname = 'cmd_' + pieces[0].lstrip('!')
            if hasattr(self, mname):
                params = ''
                if len(pieces) > 1: params = pieces[1]
                getattr(self, mname)(user, params)
            # channel commands
            for channel in self.channels:
                for module in self.channels[channel]['modules']:
                    if 'users' not in self.channels[channel]:
                        continue
                    if nick.lower() in [x.lower() for x in
                            self.channels[channel]['users']]:
                        module._privmsg(user, target, msg)
        elif self.channels.has_key(target):
            for module in self.channels[target]['modules']:
                module._privmsg(user, target, msg)

    def cmd_join(self, user, params):
        nick = user.split('!', 1)[0]
        channel = params.lower().strip()

        self.msg(nick, 'Ok, I will try joining %s' % channel)
        self.join(channel)

    def cmd_part(self, user, params):
        nick = user.split('!', 1)[0]
        channel = params.lower().strip()

        self.msg(nick, 'Ok, I will try leaving %s' % channel)
        self.part(channel)

    def action(self, user, channel, msg):
        nick = user.split('!', 1)[0]
        self.log('* %s %s' % (nick, msg))

    def joined(self, c):
        channel = c.lower()
        self.log('I have joined %s' % channel)
        if channel not in self.channels:
            self.channels[channel] = {}
        self.channels[channel]['users'] = [self.nickname]
        self.channels[channel]['modules'] = []

        if channel not in self.config:
            self.config[channel] = {}

        if channel not in self.config['onload']['channels']:
            self.config['onload']['channels'][channel] = {}
            self.save()

        if 'modules' not in self.config['onload']['channels'][channel]:
            self.config['onload']['channels'][channel]['modules'] = \
                ['disp', 'dmod']

        for module in self.config['onload']['channels'][channel]['modules']:
            if module not in self.config[channel]:
                self.config[channel][module] = {}
            try:
                c = classloader._get_class('modules.%s.Module' % module)
                m = c(self, channel)
                self.channels[channel]['modules'].append(m)
            except:
                traceback.print_exc()

    def userJoined(self, nick, channel):
        self.log('%s has joined %s' % (nick, channel))
        self.channels[channel.lower()]['users'].append(nick)

    def left(self, c):
        channel = c.lower()
        self.log('I have left %s' % channel)
        self.channels[channel]['users'] = []
        if channel in self.channels:
            del self.config['onload']['channels'][channel]
            self.save()
        
        if channel in self.config:
            for name in self.config[channel]:
                print 'I would like to unload %s for %s' % (name, channel)
                for module in self.channels[channel]['modules'][:]:
                    if module.name == name:
                        module._shutdown()
                        self.channels[channel]['modules'].remove(module)


    def userLeft(self, nick, channel):
        self.log('%s has left %s' % (nick, channel))
        self.channels[channel.lower()]['users'].remove(nick)

    def userQuit(self, nick, reason):
        self.log('%s has quit irc (%s)' % (nick, reason))
        for channel in self.channels:
            if self.channels[channel.lower()]['users'].count(nick):
                self.channels[channel.lower()]['users'].remove(nick)

    def nickChanged(self, new_nick):
        self.log('I am now known as %s' % (new_nick))
        self.nickname = new_nick
        for channel in self.channels:
            self.channels[channel.lower()]['users'].remove(self.nickname)
            self.channels[channel.lower()]['users'].append(new_nick)

    def userRenamed(self, old_nick, new_nick):
        self.log('%s is now known as %s' % (old_nick, new_nick))
        for channel in self.channels:
            if self.channels[channel.lower()]['users'].count(old_nick):
                self.channels[channel.lower()]['users'].remove(old_nick)
                self.channels[channel.lower()]['users'].append(new_nick)

    def kickedFrom(self, channel, kicker, message):
        self.log('I have been kicked from %s by %s (%s)' % \
            (channel, kicker, message))
        self.channels[channel.lower()]['users'] = []

    def userKicked(self, kicked, channel, kicker, message):
        self.log('%s has been kicked from %s by %s (%s)' % \
            (kicked, channel, kicker, message))
        self.channels[channel.lower()]['users'].remove(kicked)

    def irc_RPL_NAMREPLY(self, prefix, params):
        channel = params[2]
        names = params[3].split()
        for nick in [x.lstrip('@+%~') for x in names]:
            if not self.channels[channel.lower()]['users'].count(nick):
                self.channels[channel.lower()]['users'].append(nick)

class UusipuuFactory(protocol.ClientFactory):

    # the class of the protocol to build
    protocol = Uusipuu

    def __init__(self, cfg):
        self.nickname = cfg.get('Server', 'nick')
        self.realname = cfg.get('Server', 'realname')
        self.versionName = 'uusipuu'
        self.versionNum = '2.0'
        self.sourceURL = 'http://www.rpg.fi/uusipuu/'
        self.cfg = cfg

    def clientConnectionLost(self, connector, reason):
        print 'Connection lost, reconnecting in 5 seconds'
        reactor.callLater(10, connector.connect)

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed, reconnecting in 5 seconds'
        reactor.callLater(10, connector.connect)

# vim: set et sw=4:
