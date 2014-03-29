from core.Uusipuu import UusipuuModule
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks
from twisted.web import client
from xml.dom import minidom
from core.tdiff import *
import urllib
import locale
import time
import md5

class EVEApi(object):
    def __init__(self):
        self.cache = {}

    def query(self, page, params):
        print 'api_query %s' % (page,)
        if self.is_cached(page, params):
            d = defer.maybeDeferred(self.query_cache, page, params)
        else:
            d = self.query_api(page, params)
            d.addCallback(self.setcache, page, params)
        return d

    def is_cached(self, page, params):
        h = '%s%s%s' % (page, params['keyID'], params['vCode'])
        h = md5.md5(h).hexdigest()
        if h in self.cache:
            if time.time() > self.cache[h]['expires']:
                return False
            return True
        return False

    def parse_expires(self, data):
        try:
            dom = minidom.parseString(data)
        except Exception as e:
            print 'XML parse failed! (%s)' % (e,)
            return None
        if not dom:
            return None
        cachedUntil = dom.getElementsByTagName('cachedUntil')
        if not cachedUntil:
            return None

        cachedUntil = cachedUntil[0].childNodes[0].nodeValue
        #print 'cachedUntil: %s' % (cachedUntil,)
        cachedUntil = time.mktime(time.strptime(
            cachedUntil, '%Y-%m-%d %H:%M:%S'))

        currentTime = dom.getElementsByTagName('currentTime')
        currentTime = currentTime[0].childNodes[0].nodeValue
        #print 'currentTime: %s' % (currentTime,)
        currentTime = time.mktime(time.strptime(
            currentTime, '%Y-%m-%d %H:%M:%S'))

        tdif = cachedUntil - currentTime
        return time.time() + tdif

    def setcache(self, data, page, params):
        h = '%s%s%s' % (page, params['keyID'], params['vCode'])
        h = md5.md5(h).hexdigest()
        print 'Storing in cache %s' % (h,)
        expires = self.parse_expires(data)
        if not expires:
            print 'Not caching %s' % (h,)
            return data
        self.cache[h] = {
            'data': data,
            'expires': expires,
            }
        return data

    def query_api(self, page, params):
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        return client.getPage(
            'https://api.eveonline.com%s' % page,
            headers = headers, postdata = urllib.urlencode(params))

    def query_cache(self, page, params):
        h = '%s%s%s' % (page, params['keyID'], params['vCode'])
        h = md5.md5(h).hexdigest()
        return self.cache[h]['data']

class Module(UusipuuModule):

    def startup(self):
        self.db_open('evedb', 'evedb.sqlite')
        if 'characters' not in self.config:
            self.config['characters'] = {}
        if 'aliases' not in self.config:
            self.config['aliases'] = {}
        self.api = EVEApi()

    def shutdown(self):
        self.db_close('evedb')

    def privmsg(self, user, target, msg):
        nick = user.split('!', 1)[0]
        params = msg.split(' ', 1)
        if target == self.bot.nickname and len(params):
            args = ''
            if len(params) > 1: args = params[1]
            mname = 'cmd_' + params[0].lstrip('!')
            if hasattr(self, mname):
                getattr(self, mname)(user, nick, args)

    def findtype(self, key):
        if key.isdigit():
            sql = 'SELECT typeName, typeID, groupID FROM invTypes' + \
                ' WHERE typeID = ?'
        else:
            sql = 'SELECT typeName, typeID, groupID FROM invTypes' + \
                ' WHERE typeName = ?'
        return self.db.runQuery(sql, (key,))

    def getitemattrs(self, id):
        sql = """
        SELECT
            dt.attributeName AS key,
            IFNULL(valueInt, valueFloat) as value
        FROM
            invTypes AS i,
            dgmTypeAttributes AS d,
            dgmAttributeTypes AS dt
        WHERE
            i.typeID = ?
            AND i.typeID = d.typeID
            AND d.attributeID = dt.attributeID
        """
        return self.db.runQuery(sql, (int(id),))

    def getattrname(self, id):
        sql = """
        SELECT
            dt.attributeName
        FROM
            dgmAttributeTypes AS dt
        WHERE
            dt.attributeID =?
        """
        return self.db.runQuery(sql, (id,))

    @inlineCallbacks
    def cmd_foo(self, user, replyto, args):
        data = yield self.findtype("Deimos")
        self.chanmsg('foo: %s' % (data,))

    def findchar(self, name):
        return [x for x in self.config['characters'] \
            if x.strip().lower() == name.strip().lower()]

    def findchars(self, key):
        chars = []
        for alias in [x for x in self.config['aliases'] \
                if x.lower() == key.lower()]:
            for c in self.config['aliases'][alias]:
                chars.extend(self.findchar(c))
        if not len(chars):
            chars = self.findchar(key)
        if not len(chars):
            for alias in [x for x in self.config['aliases'] \
                    if x.lower().count(key.lower())]:
                for c in self.config['aliases'][alias]:
                    chars.extend(self.findchar(c))
                break
        if not len(chars):
            chars = [x for x in self.config['characters'] \
                if x.lower().count(key.lower())]
        self.log('Request for \'%s\' found %s' % (key, repr(chars)))
        return chars

    def findalias(self, name):
        return [x for x in self.config['aliases'] \
            if x.strip().lower() == name.strip().lower()]

    def parseXML(self, data):
        """Parses an XML result from Eve API"""

        if hasattr(data, 'getErrorMessage'): # exceptions
            return False, data.getErrorMessage()

        try:
            dom = minidom.parseString(data)
        except Exception as e:
            self.log('XML parse failed (%s)' % (e,))
            return False, 'XML parse failed: (%s)' % (e,)

        eveapi = dom.getElementsByTagName('eveapi')
        if not eveapi:
            self.log("No <eveapi> tag found!")
            return False, "Strange response!"
        if eveapi[0].getAttribute("version") != "2":
            self.log("Not a version 2 eveapi response!")
            return False, "Not a version 2 eveapi response!"

        errors = dom.getElementsByTagName('error')
        if errors:
            self.log('API Error: %s' % errors[0].childNodes[0].nodeValue)
            return False, '%s' % errors[0].childNodes[0].nodeValue

        return True, dom

    def parseXMLs(self, entries):
        results = []
        for entry in entries:
            if not entry:
                results.append(entry)
            results.append(self.parseXML(entry[1]))
        return results

    def error(self, error, user):
        nick = user.split('!', 1)[0]
        if hasattr(error, 'getErrorMessage'): # exceptions
            error = error.getErrorMessage()
        self.log('Error: %s (%s)' % (error, user))
        self.bot.msg(nick, str('Error: %s' % error))

    def cmd_cache(self, user, replyto, args):
        for i in self.api.cache:
            self.chanmsg('%s: %s' % (
                i,
                stdiff(self.api.cache[i]['expires'] - time.time())))

    def query_characters(self, userid, apikey):
        return self.api.query('/account/Characters.xml.aspx', {
            'keyID': userid,
            'vCode': apikey,
            })

    def query_skill(self, userid, apikey, charid):
        return self.api.query('/char/SkillInTraining.xml.aspx', {
            'keyID': userid,
            'vCode': apikey,
            'characterID': charid,
            })

    def query_charsheet(self, userid, apikey, charid):
        return self.api.query('/char/CharacterSheet.xml.aspx', {
            'keyID': userid,
            'vCode': apikey,
            'characterID': charid,
            })

    def query_charinfo(self, userid, apikey, charid):
        return self.api.query('/eve/CharacterInfo.xml.aspx', {
            'keyID': userid,
            'vCode': apikey,
            'characterID': charid,
            })

    def query_standings(self, userid, apikey, charid):
        return self.api.query('/char/Standings.xml.aspx', {
            'keyID': userid,
            'vCode': apikey,
            'characterID': charid,
            })

    def query_corp_standings(self, userid, apikey, charid):
        return self.api.query('/corp/Standings.xml.aspx', {
            'keyID': userid,
            'vCode': apikey,
            'characterID': charid,
            })

    def parsecharsheet(self, dom):
        """
        Parse a character sheet and return attributes & skills
        """

        attributes = {}

        # Collect base attributes
        tag = dom.getElementsByTagName('attributes')
        for child in tag[0].childNodes:
            if child.nodeType != child.ELEMENT_NODE:
                continue
            attributes[child.tagName] = int(child.childNodes[0].nodeValue)

        # Collect implant effects
        enhancers = {}
        tag = dom.getElementsByTagName('attributeEnhancers')
        for child1 in tag[0].childNodes:
            if child1.nodeType != child1.ELEMENT_NODE:
                continue
            for child2 in child1.childNodes:
                if child2.nodeType != child2.ELEMENT_NODE or \
                        child2.tagName != 'augmentatorValue':
                    continue
                # chop the 'Bonus' part
                attributes[child1.tagName[:-5]] += \
                    int(child2.childNodes[0].nodeValue)

        # Collect the skills
        skills = {}
        rowsets = dom.getElementsByTagName('rowset')
        for rowset in rowsets:
            if rowset.getAttribute('name') != 'skills':
                continue
            rows = rowset.getElementsByTagName('row')
            for row in rows:
                skills[int(row.getAttribute('typeID'))] = {
                    'skillpoints':  int(row.getAttribute('skillpoints')),
                    'level':        int(row.getAttribute('level')),
                }

        # Apply basic and advanced learning skills
        #learning = 0
        #for skill in skills:
        #    if skill in (3377, 12376): # Analytical Mind, Logic
        #        attributes['intelligence'] += int(skills[skill]['level'])
        #    if skill in (3379, 12387): # Spatial Awareness, Clarity
        #        attributes['perception'] += int(skills[skill]['level'])
        #    if skill in (3378, 12385): # Install Recall, Eidetic Memory
        #        attributes['memory'] += int(skills[skill]['level'])
        #    if skill in (3376, 12383): # Empathy, Presence
        #        attributes['charisma'] += int(skills[skill]['level'])
        #    if skill in (3375, 12386): # Iron Will, Focus
        #        attributes['willpower'] += int(skills[skill]['level'])
        #    if skill == 3374:
        #        learning += int(skills[skill]['level'])

        # Apply the learning skill
        #for attribute in attributes:
        #    attributes[attribute] = \
        #        attributes[attribute] * (1 + (0.02 * learning))

        return (attributes, skills)

    def cmd_delchar(self, user, replyto, args):
        nick = user.split('!', 1)[0]
        if replyto == self.channel:
            self.chanmsg(
                '%s: That command is only available through /msg' % nick)
            return
        pieces = args.split(' ', 2)

        if len(pieces) != 3:
            self.bot.msg(nick, 'Usage: delchar' + \
                ' <Key ID> <Verification Code> <Character Name>')
            self.bot.msg(nick,
                'Check your api key at' + \
                ' https://community.eveonline.com/support/api-key/')
            return

        userid = pieces[0].strip()
        apikey = pieces[1].strip()
        name = pieces[2].strip()

        char = self.findchar(name)
        if not char:
            self.bot.msg(nick,
                'Character "%s" not found on %s!' % \
                (name, self.channel))
            return

        char = self.config['characters'][char[0]]

        if char['apikey'] != apikey or char['userid'] != userid:
            self.bot.msg(replyto, 'Invalid keyID or vCode!')
            return

        del self.config['characters'][name]
        self.save()
        self.bot.msg(replyto, 'Ok!')

    def cmd_addchar(self, user, replyto, args):
        nick = user.split('!', 1)[0]
        if replyto == self.channel:
            self.chanmsg(
                '%s: That command is only available through /msg' % nick)
            return
        pieces = args.split(' ', 2)

        if len(pieces) != 3:
            self.bot.msg(nick, 'Usage: addchar' + \
                ' <Key ID> <Verification Code> <Character Name>')
            self.bot.msg(nick,
                'Generate your api key at' + \
                ' https://community.eveonline.com/support/api-key/')
            return

        char = {
            'userid':   pieces[0].strip(),
            'apikey':   pieces[1].strip(),
            'name':     pieces[2].strip(),
            }

        if self.findchar(char['name']):
            self.bot.msg(nick,
                'Character "%s" already exists for %s' % \
                (char['name'], self.channel))
            return
        if self.findalias(char['name']):
            self.bot.msg(nick,
                'An alias called "%s" exists already' % \
                char['name'])
            return

        d = self.query_characters(char['userid'], char['apikey'])
        d.addCallback(self.parseXML)
        d.addCallback(self.finish_addchar, user, replyto, char)
        d.addErrback(self.error, user)

    def finish_addchar(self, data, user, replyto, char):
        # See if XML parse was successful
        if not data[0]:
            self.error(data[1], user)
            return

        rows = data[1].getElementsByTagName('row')
        if not len(rows):
            self.error('No "row" tags found in the XML output', user)
            return

        found = False
        clist = []
        for row in rows:
            clist.append(row.getAttribute('name'))
            if row.getAttribute('name').lower() == char['name'].lower():
                found = True
                name = row.getAttribute('name')
                charid = row.getAttribute('characterID')
                break

        if not found:
            self.error('Couldn\'t find "%s" in the list (%s)' % \
                    (char['name'], ', '.join(clist)), user)
            return

        self.config['characters'][name] = {
            'apikey':   char['apikey'],
            'userid':   char['userid'],
            'charid':   charid,
            }
        self.save()

        self.log('Character "%s" successfully added' % name)
        self.bot.msg(replyto,
            'Your character "%s" was successfully added for %s' % \
            (str(name), self.channel))

    def cmd_delalias(self, user, replyto, args):
        nick = user.split('!', 1)[0]

        if not len(args):
            self.bot.msg(replyto, 'Usage: delalias <Alias>')
            return

        alias = self.findalias(args)
        if not alias:
            self.bot.msg(replyto, 'No alias matching "%s" found' % args)
            return

        del self.config['aliases'][alias[0]]
        self.save()

        self.bot.msg(replyto,
            'Alias "%s" successfully deleted' % str(alias[0]))

    def cmd_alias(self, user, replyto, args):
        nick = user.split('!', 1)[0]
        pieces = args.split(' ', 1)

        if len(pieces) < 2:
            self.bot.msg(replyto, 'Usage: alias <Alias> <Character Name>, ...')
            self.bot.msg(replyto, 'Multiple characters can be specified ' + \
                'by separating them with a comma.')
            return

        alias = pieces[0].strip()
        chars = [x.strip() for x in pieces[1].split(',')]

        if self.findchar(alias):
            self.bot.msg(replyto, ('Can\'t add the alias "%s" because ' + \
                'a character by that name exists') % alias)
            return

        if self.findalias(alias):
            self.bot.msg(replyto, ('Can\'t add the alias "%s" because ' + \
                'an alias by that name already exists for %s') % \
                (alias, self.channel))
            return

        for char in chars:
            if not self.findchar(char):
                self.bot.msg(replyto,
                    'Can\'t find a character named "%s"' % char)
                return

        self.config['aliases'][alias] = chars
        self.save()
        self.bot.msg(replyto, 'Alias "%s" successfully added' % alias)

    def cmd_isk(self, user, replyto, params):
        char = params.strip()
        nick = user.split('!', 1)[0]
        if not len(char):
            char = nick

        # In this command we will only allow one result from the partial
        # character search, so let's not use findchars()
        chars = []
        for alias in [x for x in self.config['aliases'] \
                if x.lower() == char.lower()]:
            for c in self.config['aliases'][alias]:
                chars.extend(self.findchar(c))
        if not len(chars):
            chars = self.findchar(char)
        if not len(chars):
            chars = [x for x in self.config['characters'] \
                if x.lower().count(char.lower())]
            if len(chars):
                chars = [chars[0]]
        if not len(chars):
            for alias in [x for x in self.config['aliases'] \
                    if x.lower().count(char.lower())]:
                for c in self.config['aliases'][alias]:
                    chars.extend(self.findchar(c))
                char = str(alias)
                break

        if not len(chars):
            self.bot.msg(replyto, 'No characters found matching "%s"' % char)
            return

        dl = []
        for c in chars:
            dl.append(self.query_charsheet(
                self.config['characters'][c]['userid'],
                self.config['characters'][c]['apikey'],
                self.config['characters'][c]['charid']))
        dl = defer.DeferredList(dl, consumeErrors = True)
        dl.addCallback(self.parseXMLs)
        dl.addCallback(self.show_isk, user, replyto, char)

    def show_isk(self, results, user, replyto, char):
        isk, chars = 0, []
        for result in results:
            if not result[0]:
                self.error(result[1], user)
                continue
            balance = result[1].getElementsByTagName('balance')
            name = result[1].getElementsByTagName('name')
            if not balance or not name:
                self.log('"balance" or "name" tag not found (%s)' % char)
                continue
            add = float(balance[0].childNodes[0].nodeValue)
            chars.append(str(name[0].childNodes[0].nodeValue))

            self.log('Adding %s ISK to total balance for %s' % \
                (locale.format('%.*f', (2, float(add)), True), char))
            isk += add

        isk_nice = locale.format('%.*f', (2, float(isk)), True)
        if not len(chars):
            self.bot.msg(replyto, 'All %d ISK queries failed (%s)' % \
                (len(results), char))
        elif len(chars) > 1:
            self.bot.msg(replyto, '%s has %s ISK (%s)' % \
                (char, isk_nice, ', '.join(chars)))
        else:
            self.bot.msg(replyto, '%s has %s ISK' % (chars[0], isk_nice))

    def cmd_skill(self, user, replyto, params):
        char = params.strip()
        nick = user.split('!', 1)[0]

        if not len(char):
            char = nick

        chars = self.findchars(char)
        if not len(chars):
            self.bot.msg(replyto, 'No characters found matching "%s"' % char)
            return

        if len(chars) > 4:
            self.bot.msg(replyto, ('Too many characters found (%d),' + \
                ' please be more specific') % len(chars))
            return

        skills = []
        for char in chars:
            d1 = self.query_skill(
                self.config['characters'][char]['userid'],
                self.config['characters'][char]['apikey'],
                self.config['characters'][char]['charid'])
            d2 = self.query_charsheet(
                self.config['characters'][char]['userid'],
                self.config['characters'][char]['apikey'],
                self.config['characters'][char]['charid'])
            dl = defer.DeferredList([d1, d2], consumeErrors = True)
            dl.addCallback(self.parseXMLs)
            dl.addCallback(self.show_skill, user, replyto, char)

    @inlineCallbacks
    def show_skill(self, data, user, replyto, char):

        if not data[0][0]:
            self.error(data[0][1], user)
            return

        if not data[1][0]:
            self.error(data[1][1], user)
            return

        tdom, cdom = data[0][1], data[1][1]

        # training

        tr = tdom.getElementsByTagName(
            'skillInTraining')[0].childNodes[0]

        training = int(tdom.getElementsByTagName(
            'skillInTraining')[0].childNodes[0].nodeValue)
        if not training:
            self.bot.msg(replyto, 'No skill training for %s!' % str(char))
            return

        endstamp = time.mktime(time.strptime(tdom.getElementsByTagName(
            'trainingEndTime')[0].childNodes[0].nodeValue,
            '%Y-%m-%d %H:%M:%S'))
        currentstamp = time.mktime(time.strptime(tdom.getElementsByTagName(
            'currentTime')[0].childNodes[0].nodeValue,
            '%Y-%m-%d %H:%M:%S'))
        
        level = tdom.getElementsByTagName(
            'trainingToLevel')[0].childNodes[0].nodeValue
        level = ['0', 'I', 'II', 'III', 'IV', 'V', 'VI'][int(level)]
        skilltype = tdom.getElementsByTagName(
            'trainingTypeID')[0].childNodes[0].nodeValue

        try:
            print 'findtype', skilltype
            skill = yield self.findtype(skilltype)
        except Exception as e:
            self.error('SQL query failed %s (%s)' % (skilltype, e), user)
            return

        if currentstamp > endstamp:
            self.bot.msg(replyto, '%s %s finished! (%s)' %
                (skill[0]['typeName'], level, str(char)))
            return

        if time.daylight and False:
            adjend = endstamp - time.altzone
        else:
            adjend = endstamp - time.timezone

        if time.strftime('%d.%m.%Y', \
                time.localtime(adjend)) == time.strftime('%d.%m.%Y'):
            timestr = time.strftime('%k:%M', time.localtime(adjend)).strip()
        elif time.strftime('%Y') == time.strftime('%Y'):
            timestr = '%s %s' % \
                (time.strftime('%d.%m.', time.localtime(adjend)),
                time.strftime('%k:%M', time.localtime(adjend)).strip())
        else:
            timestr = '%s %s' % \
                (time.strftime('%d.%m.%Y', time.localtime(adjend)),
                time.strftime('%k:%M', time.localtime(adjend)).strip())

        # charsheet, attributes

        attributes, skills = self.parsecharsheet(cdom)

        attrs = {}
        try:
            rows = yield self.getitemattrs(skilltype)
        except Exception as e:
            self.error('SQL query failed #1 (%s)' % (e,), user)
            return
        for row in rows:
            attrs[row['key']] = row['value']

        try:
            primary = yield self.getattrname(attrs['primaryAttribute'])
            primary = primary[0]['attributeName']
            secondary = yield self.getattrname(attrs['secondaryAttribute'])
            secondary = secondary[0]['attributeName']
        except Exception as e:
            self.error('SQL query failed #2 (%s)' % (e,), user)
            return
        sph = (attributes[primary] + (attributes[secondary] / 2)) * 60

        # ...

        msg = '%s %s %s (%s) %s %d SP/h' % \
            (skill[0]['typeName'],
            level,
            stdiff(endstamp - currentstamp),
            str(char),
            timestr,
            sph)
        self.bot.msg(replyto, str(msg))

    def cmd_sp(self, user, replyto, params):
        char = params.strip()
        nick = user.split('!', 1)[0]

        if not len(char):
            char = nick

        chars = self.findchars(char)
        if not len(chars):
            self.bot.msg(replyto, 'No characters found matching "%s"' % char)
            return

        if len(chars) > 3:
            self.bot.msg(replyto, ('Too many characters found (%d),' + \
                ' please be more specific') % len(chars))
            return

        for char in chars:
            d1 = self.query_charinfo(
                self.config['characters'][char]['userid'],
                self.config['characters'][char]['apikey'],
                self.config['characters'][char]['charid'])
            d2 = self.query_charsheet(
                self.config['characters'][char]['userid'],
                self.config['characters'][char]['apikey'],
                self.config['characters'][char]['charid'])
            dl = defer.DeferredList([d1, d2], consumeErrors = True)
            dl.addCallback(self.parseXMLs)
            dl.addCallback(self.show_sp, user, replyto, char)

    def show_sp(self, data, user, replyto, char):
        for i in range(0, 1):
            if not data[i][0]:
                self.error(data[i][1], user)
                return

        idom, cdom = data[0][1], data[1][1]

        clone = cdom.getElementsByTagName('cloneSkillPoints')
        clone = int(clone[0].childNodes[0].nodeValue)

        sp = idom.getElementsByTagName('skillPoints')
        sp = int(sp[0].childNodes[0].nodeValue)

        upg = ""
        if int(clone) < int(sp):
            upg = ", upgrade needed!"

        self.bot.msg(replyto, 
            '%s has %s sp (%s clone%s)' % \
            (str(char), locale.format('%.*f', (0, int(sp)), True),
            locale.format('%.*f', (0, int(clone)), True), str(upg)))

    def cmd_secstatus(self, user, replyto, params):
        char = params.strip()
        nick = user.split('!', 1)[0]

        if not len(char):
            char = nick

        chars = self.findchars(char)
        if not len(chars):
            self.bot.msg(replyto, 'No characters found matching "%s"' % char)
            return

        if len(chars) > 4:
            self.bot.msg(replyto, ('Too many characters found (%d),' + \
                ' please be more specific') % len(chars))
            return

        skills = []
        for char in chars:
            d = self.query_charinfo(
                self.config['characters'][char]['userid'],
                self.config['characters'][char]['apikey'],
                self.config['characters'][char]['charid'])
            d.addCallback(self.parseXML)
            d.addCallback(self.show_secstatus, user, replyto, char)
            d.addErrback(self.error, user)

    def show_secstatus(self, data, user, replyto, char):
        if not data[0]:
            self.error(data[1], user)
            return

        dom = data[1]

        result = dom.getElementsByTagName('result')
        if not result:
            self.log('"result" tag not found (%s)' % char)
            self.bot.msg(replyto,
                'Couldn\'t fetch character sheet for %s' % char)
            return

        s = result[0].getElementsByTagName('securityStatus')
        s = s[0].childNodes[0].nodeValue
        s = float(s)

        if s > -2.0:
            can = 'can enter 1.0'
        elif s > -2.5:
            can = 'can enter 0.9'
        elif s > -3.0:
            can = 'can enter 0.8'
        elif s > -3.5:
            can = 'can enter 0.7'
        elif s > -4.0:
            can = 'can enter 0.6'
        elif s > -4.5:
            can = 'can enter 0.5'
        elif s > -5.0:
            can = 'can\'t enter high-sec'
        elif s == -10.0:
            can = 'true pirate, YARR'
        else:
            can = 'outlaw, kill on sight'

        self.bot.msg(replyto, '%s has a security status of %s (%s)' % \
                (str(char), locale.format('%.*f', (2, s), True), can))

    def cmd_corp(self, user, replyto, params):
        char = params.strip()
        nick = user.split('!', 1)[0]

        if not len(char):
            char = nick

        chars = self.findchars(char)
        if not len(chars):
            self.bot.msg(replyto, 'No characters found matching "%s"' % char)
            return

        if len(chars) > 3:
            self.bot.msg(replyto, ('Too many characters found (%d),' + \
                ' please be more specific') % len(chars))
            return

        for char in chars:
            d = self.query_charinfo(
                self.config['characters'][char]['userid'],
                self.config['characters'][char]['apikey'],
                self.config['characters'][char]['charid'])
            d.addCallback(self.parseXML)
            d.addCallback(self.show_corp, user, replyto, char)
            d.addErrback(self.error, user)

    def show_corp(self, data, user, replyto, char):
        if not data[0]:
            self.error(data[1], user)
            return
        dom = data[1]

        name = dom.getElementsByTagName('characterName')
        name = name[0].childNodes[0].nodeValue

        corp = dom.getElementsByTagName('corporation')
        corp = corp[0].childNodes[0].nodeValue

        alliance = dom.getElementsByTagName('alliance')
        alliance = alliance[0].childNodes[0].nodeValue

        msg = '%s is a member of %s <%s>' % \
            (name, corp, alliance)
        self.bot.msg(replyto, str(msg))

# vim: set et sw=4: