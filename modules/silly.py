# -*- coding: ISO-8859-15 -*-

from core.Uusipuu import UusipuuModule
import random, time
from core.tdiff import *

class Module(UusipuuModule):
    
    def cmd_noppa(self, user, target, params):
        self.log('ok noppaa heitet��n!!')
        self.chanmsg('%s!' % random.choice((
            'ykk�nen',
            'kakkonen',
            'kolmonen',
            'nelonen',
            'vitonen',
            'kutonen')))

# vim: set et sw=4:
