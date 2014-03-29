#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-

# doing execfile() on this file will alter the current interpreter's
# environment so you can import libraries in the virtualenv
#activate_this_file = "env2/bin/activate_this.py"
#execfile(activate_this_file, dict(__file__=activate_this_file))

from core import Uusipuu, Web
from twisted.internet import reactor
from twisted.web import server
from twisted.python import log
import ConfigParser, locale
import sys

if __name__ == '__main__':
    log.startLogging(sys.stdout)
    log.addObserver(log.FileLogObserver(file("log/uusipuu.log", "a")).emit)

    cfg = ConfigParser.ConfigParser()
    cfg.read('./uusipuu.cfg')

    locale.setlocale(locale.LC_ALL, 'en_US.ISO-8859-1')

    # create factory protocol and application
    f = Uusipuu.UusipuuFactory(cfg)

    # connect factory to this host and port
    reactor.connectTCP(
        cfg.get('Server', 'server'),
        cfg.getint('Server', 'port'),
        f, 30)

    # Web server
    f.web = Web.Web(cfg)
    site = server.Site(f.web)
    reactor.listenTCP(int(cfg.get('Web', 'port')), site)

    # run bot
    reactor.run()

# vim: set et sw=4:
