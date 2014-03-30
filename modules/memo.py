# -*- coding: ISO-8859-15 -*-

from core.Uusipuu import UusipuuModule
import random, time

class Module(UusipuuModule):
    
    def startup(self):
        if 'memo' not in self.config:
            self.config['memo'] = {}

    def privmsg(self, user, target, msg):
        if target != self.channel:
            return

        pieces = msg.strip().split(' ', 1)
        if len(pieces) != 2:
            return

        cmd = pieces[0].strip()
        params = pieces[1].strip()

        if cmd == '??':
            self.meta_show(user, params)
        elif cmd == '?!':
            self.meta_searchkey(user, params.strip())
        elif cmd == '?#':
            self.meta_searchvalue(user, params.strip())

    def cmd_memo(self, user, target, params):
        pieces = params.strip().split(' ', 1)
        if len(pieces) != 2:
            self.chanmsg('Insufficient parameters')
            return

        cmd = pieces[0].strip()
        params = pieces[1].strip()

        if cmd == 'add':
            self.meta_addmemo(user, params)
        elif cmd in ['del', 'delete', 'remove']:
            self.meta_delmemo(user, params)
        elif cmd == 'show':
            self.meta_show(user, params)
        elif cmd == 'info':
            self.meta_info(user, params)
        elif cmd in ['search', 'searchkey', 'sk']:
            self.meta_searchkey(user, params.strip())
        elif cmd in ['searchvalue', 'sv']:
            self.meta_searchvalue(user, params.strip())

    def meta_show(self, user, key):
        self.do_show(user, key)

    def meta_info(self, user, key):
        self.do_show(user, key)
        self.do_info(user, key)

    def meta_searchkey(self, user, key):
        nick = user.split('!', 1)[0]

        keys = [x for x in self.config['memo'] if x.count(key)]
        if not keys:
            self.chanmsg('No keys found matching "%s"' % (key))
            return
        self.do_show(user, random.choice(keys))

    def meta_searchvalue(self, user, value):
        nick = user.split('!', 1)[0]

        keys = [x for x in self.config['memo'] \
                if self.config['memo'][x]['value'].count(value)]
        if not keys:
            self.chanmsg('No values found matching "%s"' % (value))
            return
        self.do_show(user, random.choice(keys))

    def do_show(self, user, key):
        nick = user.split('!', 1)[0]

        if key not in self.config['memo']:
            self.chanmsg('Entry not found (%s)' % key)
            return ()

        self.chanmsg('%s: %s' % (key, str(self.config['memo'][key]['value'])))

    def do_info(self, user, key):
        if key not in self.config['memo']:
            return
        self.chanmsg('%s created by %s [%s]' % (key,
            self.config['memo'][key]['user'],
            time.ctime(self.config['memo'][key]['added'])))

    def meta_addmemo(self, user, params):
        nick = user.split('!', 1)[0]
        pieces = params.strip().split(' ', 1)

        if len(pieces) < 2:
            self.chanmsg('Insufficient parameters')
            return

        key, value = pieces[0].strip(), pieces[1].strip()

        if key in self.config['memo']:
            self.chanmsg('%s: An entry by that name already exists' % nick)
            return

        self.config['memo'][key] = {
                'value':        value,
                'user':         user,
                'added':        int(time.time()),
                }
        self.save()

        self.chanmsg('Memo entry "%s" successfully added' % (str(key)))

    def meta_delmemo(self, user, params):
        nick = user.split('!', 1)[0]
        pieces = params.strip().split(' ', 1)

        key = pieces[0].strip()

        if key not in self.config['memo']:
            self.chanmsg('Entry not found (%s)' % key)
            return

        del self.config['memo'][key]
        self.save()

        self.chanmsg('Memo entry "%s" successfully removed' % (key))

# vim: set et sw=4:
