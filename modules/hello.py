# Hello World

from core.Uusipuu import UusipuuModule

class Module(UusipuuModule):

    def startup(self):
        message = self.bot.factory.cfg.get('Hello', 'message')
        self.chanmsg(message)

    def shutdown(self):
        self.chanmsg('Good bye, cruel world :(')

    def cmd_hello(self, user, replyto, params):
        nick = user.split('!', 1)[0]
        self.chanmsg('Hi, %s' % nick)

        self.config['example'] = 42
        self.save()

# vim: set et sw=4:
