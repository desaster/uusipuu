# -*- coding: ISO-8859-15 -*-

from core.Uusipuu import UusipuuModule
from core import meminfo
from twisted.internet import reactor
import locale

class Module(UusipuuModule):

    def cmd_mem(self, user, channel, params):
        mem = locale.format('%.*f', (0, float(meminfo.memory())), True)
        self.chanmsg('I\'m using %s bytes of memory' % mem)

    def cmd_die(self, user, replyto, params):
        if self.bot.is_admin(user):
            reactor.stop()

    def cmd_raw(self, user, replyto, params):
        if self.bot.is_admin(user):
            self.bot.sendLine(params.strip())

    def cmd_userbase(self, user, replyto, params):
        users = []
        for c in self.bot.channels:
            for u in self.bot.channels[c]['users']:
                if users.count(u) == 0:
                    users.append(u)
        self.chanmsg('I am serving %d users' % (len(users) - 1))

    def cmd_ignore(self, user, replyto, params):
        nick = params.strip().lower()

        if not self.bot.is_admin(user):
            return

        if not len(nick):
            self.chanmsg('Ignure wat?')
            return

        if nick not in self.bot.ignorenicks:
            self.bot.ignorenicks.append(nick)

        self.chanmsg('Fine.')

    def cmd_unignore(self, user, replyto, params):
        nick = params.strip().lower()

        if not self.bot.is_admin(user):
            return

        if not len(nick):
            self.chanmsg('Unigorn wat?')
            return

        if nick in self.bot.ignorenicks:
            self.bot.ignorenicks.remove(nick)

        self.chanmsg('Fine.')
