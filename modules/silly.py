# -*- coding: ISO-8859-15 -*-

from core.Uusipuu import UusipuuModule
import random, time
from core.tdiff import *

class Module(UusipuuModule):
    
    def cmd_noppa(self, user, target, params):
        self.log('ok noppaa heitetään!!')
        self.chanmsg('%s!' % random.choice((
            'ykkönen',
            'kakkonen',
            'kolmonen',
            'nelonen',
            'vitonen',
            'kutonen')))

# vim: set et sw=4:
