# -*- coding: ISO-8859-15 -*-

from twisted.web import client
from twisted.internet.defer import inlineCallbacks
from core.Uusipuu import UusipuuModule
import urllib, simplejson

class Module(UusipuuModule):
    
    def startup(self):
        self.log('google.py loaded')

    @inlineCallbacks
    def cmd_google(self, user, target, params):
        self.log('Querying google for "%s"' % params)

        data = yield client.getPage(
            'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&%s' % 
            urllib.urlencode({'q': params.strip()}))

        json = simplejson.loads(data)
        results = json['responseData']['results']
        if not results:
            self.log('No results found matching "%s"' % keyword)
            self.chanmsg('No results found matching "%s"' % keyword)
            return

        self.chanmsg('%s: %s' % \
                (results[0]['titleNoFormatting'].encode('utf-8'),
                 results[0]['url'].encode('utf-8')))

# vim: set et sw=4:
