# -*- coding: ISO-8859-15 -*-

import md5, time
from xml.dom import minidom
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.web import client
from core.Uusipuu import UusipuuModule

class Module(UusipuuModule):

    def startup(self):
        if 'feeds' not in self.config or \
                type(self.config['feeds']) != type({}):
            self.config['feeds'] = {}

        self.items = {}
        for feed in self.config['feeds']:
            self.items[feed] = []
            self.query_feed(feed)

    def cmd_rssreset51515(self, user, replyto, params):
        name = params.strip()
        for feed in self.items:
            for item in self.items[feed][:]:
                if item['title'] == name:
                    self.items[feed].remove(item)
                    self.chanmsg('Ok, removing an item')
                    return
        self.chanmsg('No items found :(')

    def cmd_rss(self, user, replyto, params):
        pieces = params.strip().split(' ', 1)

        if not len(pieces) or not len(pieces[0]):
            self.chanmsg('Usage: !rss <add|remove|list|refresh> [...]')
            return

        if pieces[0].strip() in \
                ('add', 'remove', 'latest', 'refresh', 'list', 'addfilter',
                'removefilter'):
            mname = 'do_' + pieces[0].strip()
            params = ''
            if len(pieces) >= 2:
                params = pieces[1].strip()
            if hasattr(self, mname):
                getattr(self, mname)(user, params)

    def do_add(self, user, params):
        pieces = params.split()

        if len(pieces) < 2:
            self.chanmsg('Usage !rss add <name> <url>')
            return

        feed, url = pieces[0:2]

        interval = 180
        if len(pieces) == 3:
            interval = int(pieces[2])
        if interval < 120:
            interval = 120

        if feed in self.config['feeds']:
            self.chanmsg('Feed already exists: %s' % feed)
            return

        self.items[feed] = []
        self.config['feeds'][feed] = {
            'url':      url,
            'interval': interval,
            }
        self.save()
        self.chanmsg('Feed %s successfully added' % feed)
        self.query_feed(feed)

    def do_addfilter(self, user, params):
        pieces = params.split(' ', 1)
        if len(pieces) != 2:
            self.chanmsg('Usage !rss addfilter <feed> <string>')
            return
        feed, filter = pieces

        if feed not in self.config['feeds']:
            self.chanmsg('No such feed found')
            return

        self.config['feeds'][feed]['filter'] = filter
        self.save()
        self.chanmsg('Filter added for %s' % feed)

    def do_removefilter(self, user, feed):
        if feed not in self.config['feeds']:
            self.chanmsg('No such feed found')
            return

        if 'filter' in self.config['feeds'][feed]:
            del self.config['feeds'][feed]['filter']

        self.save()
        self.chanmsg('Filter removed from %s' % feed)

    def do_remove(self, user, feed):
        if not feed:
            self.chanmsg('Usage !rss remove <feed>')
            return

        if feed not in self.config['feeds']:
            self.chanmsg('Feed not found: %s' % feed)

        if 'feed_%s' % feed in self.scheduled:
            self.scheduled['feed_%s' % feed].cancel()
            del self.scheduled['feed_%s' % feed]

        del self.config['feeds'][feed]
        self.save()
        self.chanmsg('Feed %s successfully removed' % feed)

    def do_list(self, user, params):
        if not len(self.config['feeds']):
            self.chanmsg('No feeds found')
            return

        l = []
        for feed in self.config['feeds']:
            filter = ''
            if 'filter' in self.config['feeds'][feed]:
                filter = '{%s}' % self.config['feeds'][feed]['filter']
            l.append('%s(%s)[%s]%s' % \
                (feed,
                self.config['feeds'][feed]['interval'],
                self.config['feeds'][feed]['url'],
                filter))
        self.chanmsg(' '.join(l))

    def do_latest(self, user, feed):
        if not feed:
            self.chanmsg('Usage: !rss latest <name>')
            return

        if feed not in self.config['feeds']:
            self.chanmsg('No such feed found')
            return

        if feed not in self.items:
            self.chanmsg('No items found')
            return

        count = 0
        for item in self.items[feed]:
            self.chanmsg('%s %s' % (str(item['title']), str(item['link'])))
            count += 1
            if count == 3:
                break

    def do_refresh(self, user, feed):
        if not feed:
            self.chanmsg('Usage: !rss refresh <name>')
            return

        if feed not in self.config['feeds']:
            self.chanmsg('No such feed found')
            return

        if 'feed_%s' % feed in self.scheduled:
            self.scheduled['feed_%s' % feed].cancel()
            del self.scheduled['feed_%s' % feed]

        self.query_feed(feed)

    @inlineCallbacks
    def query_feed(self, feed):
        url = self.config['feeds'][feed]['url']
        interval = self.config['feeds'][feed]['interval']

        filter = None
        if 'filter' in self.config['feeds'][feed]:
            filter = self.config['feeds'][feed]['filter']

        try:
            data = yield client.getPage(url)
        except:
            self.log('I failed at checking %s' % feed)
            self.scheduled['feed_%s' % feed] = \
                reactor.callLater(interval, self.query_feed, feed)
            return

        try:
            dom = minidom.parseString(data)
        except:
            self.log('XML parse failed (%s)' % feed)
            self.scheduled['feed_%s' % feed] = \
                reactor.callLater(interval, self.query_feed, feed)
            return

        first = False
        if not len(self.items[feed]):
            first = True

        items = dom.getElementsByTagName('item')
        for item in items:
            titleorig = item.getElementsByTagName(
                'title')[0].childNodes[0].nodeValue.encode('UTF-8')
            try:
                title = titleorig.decode('UTF-8').encode('ISO-8859-1')
            except:
                title = titleorig

            link = item.getElementsByTagName(
                'link')[0].childNodes
            if len(link):
                link = link[0].nodeValue
            else:
                link = ''
            link = self.bot.factory.web.urlstorage.addURL(link)

            description = item.getElementsByTagName('description')
            if description:
                description = description[0].childNodes[0].nodeValue
            else:
                description = ''

            guid = item.getElementsByTagName('guid')
            if guid:
                guid = guid[0].childNodes[0].nodeValue
            else:
                guid = md5.md5(title).hexdigest()

            if filter and not (title.lower().count(filter.lower()) or \
                    description.count(filter.lower())):
                continue

            if guid not in [x['guid'] for x in self.items[feed]]:
                # Yes, we now keep every item we've ever seen (in this session)
                # to prevent excess flood when certain rss feeds (devblog)
                # fuck up
                self.items[feed].append({
                    'guid':             guid,
                    'title':            title,
                    'link':             link,
                    'found':            time.time(),
                    })
                if not first:
                    self.log('I would like to announce on %s: %s' % \
                        (feed, guid))
                    self.chanmsg('[%s] %s %s' % (feed, str(title), str(link)))

        self.scheduled['feed_%s' % feed] = \
            reactor.callLater(interval, self.query_feed, feed)

# vim: set et sw=4:
