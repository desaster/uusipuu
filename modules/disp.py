# Display & Log channel activity

from core.Uusipuu import UusipuuModule
import random

class Module(UusipuuModule):

    def privmsg(self, user, target, msg):
        nick = user.split('!', 1)[0]

        if target == self.channel:
            self.log('<%s> %s' % (nick, msg))
        else:
            self.log('*%s* %s' % (nick, msg))

        UusipuuModule.privmsg(self, user, target, msg)

# vim: set et sw=4:
