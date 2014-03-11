#!/usr/bin/env python
# -*- coding: ISO-8859-15 -*-

from core import Uusipuu, Web
from twisted.internet import reactor
from twisted.web import server
import ConfigParser, locale

if __name__ == '__main__':
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
