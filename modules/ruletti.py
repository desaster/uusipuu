# -*- coding: ISO-8859-15 -*-

from twisted.internet import reactor
from core.Uusipuu import UusipuuModule
import random

class Module(UusipuuModule):
    
    def startup(self):
        self.scheduled['unban'] = []

    def cmd_ruletti(self, user, target, params):
        nick = user.split('!', 1)[0]
        if random.choice(range(0, 6)) < 3:
            self.bot.mode(self.channel, True, 'b %s!*@*' % nick)
            self.bot.kick(self.channel, nick, 'naps!')
            self.log('%s - Nyt napsahti!' % nick)
            d = reactor.callLater(5, self.unban, nick)
            self.scheduled['unban'].append(d)
        else:
            self.chanmsg('%s: klik!' % nick)
            self.log('%s - Klik!' % nick)
    
    def unban(self, nick):
        self.bot.mode(self.channel, False, 'b %s!*@*' % nick)

# vim: set et sw=4:
