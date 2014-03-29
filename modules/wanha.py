# -*- coding: ISO-8859-15 -*-

from twisted.internet.defer import inlineCallbacks
from core.Uusipuu import UusipuuModule
from core.tdiff import tdiff
import random, re, time
import MySQLdb


## FIXME ## 
## Use Deferredlist to prevent spam !!!!!!!1

class Module(UusipuuModule):

    def startup(self):
        self.db_open('botdb', 'wanha.sqlite')
        self.initdb()

        self.wanhat = [
            'wANAH',
            'wanha',
            'AWNNHAWWA',
            'wanha!!!11',
            'Wan..',
            'w... an.. ha',
            'WNHA',
            'WANHA :/(',
            'On muuten vanha urli',
            'Olen nähnyt tuon internet-osoitteen ennenkin',
            'Vanha',
            'VANHA OSOITE',
            ]

    def initdb(self):
        sql = "CREATE TABLE IF NOT EXISTS urls (" + \
            "id INTEGER PRIMARY KEY AUTOINCREMENT, " + \
            "channel TEXT, " + \
            "url TEXT, " + \
            "user TEXT, " + \
            "added INTEGER)"
        self.db.runQuery(sql)
        # finish whenever..

    def shutdown(self):
        self.db_close('botdb')

    def privmsg(self, user, target, msg):
        if target != self.channel:
            return

        match = re.compile('http:[^ ][^ ]*').findall(msg)
        if match:
            for url in match:
                sql = 'SELECT * FROM urls' + \
                    ' WHERE channel = ?' + \
                    ' AND url = ? LIMIT 1'
                d = self.db.runQuery(sql, (self.channel, url))
                d.addCallback(self.checkurl, url, user)
                d.addErrback(self.sqlerror)

    def checkurl(self, rows, url, user):
        nick = str(user.split('!', 1)[0])

        if not len(rows):
            sql = 'INSERT INTO urls' + \
                ' (channel, url, user, added)' + \
                ' VALUES (?, ?, ?, ?)'
            d = self.db.runQuery(sql,
                (self.channel, url, user, time.time()))
            d.addErrback(self.sqlerror)
            return

        if nick.lower() == rows[0]['user'].split('!')[0].lower():
            return

        orig = str(rows[0]['user'].split('!', 1)[0])
        added = int(rows[0]['added'])
        msg = '%s: %s. %s sanoi tuon jo %s sitten' % (
            nick,
            random.choice(self.wanhat),
            orig,
            tdiff(time.time() - added))
        self.chanmsg(msg)

    def sqlerror(self, error):
        self.log('SQL Error: %s' % error.value)
        print error

# vim: set et sw=4:
