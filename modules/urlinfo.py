from twisted.web.client import getPage
from twisted.internet.defer import inlineCallbacks
from core.Uusipuu import UusipuuModule

import re
import lxml.html

class Module(UusipuuModule):
    
    def startup(self):
        self.log('urlinfo.py loaded')

    def privmsg(self, user, target, msg):
        if target != self.channel:
            return

        urls = self.parse_urls(msg)
        if not len(urls):
            return

        re_youtube = re.compile(
            '^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$')
        for url in urls:
            if re_youtube.match(url):
                d = getPage(url)
                d.addCallback(self.show_youtube)

    def show_youtube(self, output):
        if output is None or not len(output):
            print('Received empty youtube data!')
            return
        data = self.parse_youtube(output)

        print('Title: %s' % (repr(data['title'])))
        self.chanmsg(data['title'].encode('ISO-8859-1'))

    def parse_youtube(self, output):
        foo = lxml.html.fromstring(output)
        title = None

        for result in foo.iterfind('.//meta'):
            prop = result.get('property')
            if prop is None:
                continue
            if prop != 'og:title':
                continue
            title = result.get('content')
            break

        if not title:
            return None

        return {
            'title':    title,
            }

    def parse_urls(self, s):
        # TODO: http://www.google.com/asdasd)
        re_url = re.compile(
            '(https?:\/\/(?:www\.|(?!www))[^\s\.]+\.[^\s]{2,}|www\.[^\s]+\.[^\s]{2,})')
        matches = re_url.findall(s)
        ret = []
        for match in matches:
            if match is None:
                continue
            if not match.startswith('http'):
                ret.append('http://' + match)
            else:
                ret.append(match)
        return ret
