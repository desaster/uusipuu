from core.Uusipuu import UusipuuModule
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks
from twisted.web import client
from xml.dom import minidom
import locale

class Module(UusipuuModule):

    def startup(self):
        self.db_open('evedb', 'data/db/evedb.sqlite')

    def shutdown(self):
        self.db_close('evedb')

    def findtypebyname(self, key):
        sql = 'SELECT typeName, typeID, groupID, ' + \
            'CASE WHEN typeName = ? THEN 1 ELSE 0 END AS typeOrder ' + \
            'FROM invTypes ' + \
            'WHERE typeName LIKE ? ' + \
            'ORDER BY typeOrder ASC LIMIT 1 ' + \
            'COLLATE NOCASE';
        return self.db.runQuery(sql, (key, '%' + key + '%'))

    def findregion(self, key):
        sql = 'SELECT regionID, regionName FROM mapRegions' + \
            ' WHERE regionName LIKE ? COLLATE NOCASE'
        param = '%' + key + '%'
        return self.db.runQuery(sql, (param,))

    @inlineCallbacks
    def cmd_market(self, user, replyto, params):
        if not len(params.strip()):
            self.bot.msg(replyto, 'Usage: !market item, region')
            return

        pieces = params.strip().split(',')
        item, region = pieces[0], None
        if len(pieces) > 1:
            region = pieces[1].strip()

        result = yield self.findtypebyname(item)
        if not len(result):
            self.bot.msg(replyto, 'Unknown item :(')
            self.log('Item not found [%s]' % (item,))
            return
        type_id = result[0]['typeID']
        type_id = int(type_id)
        item = str(result[0]['typeName'])

        url = 'http://api.eve-central.com/api/marketstat?typeid=%d' % \
            (type_id,)

        if region:
            result = yield self.findregion(region)
            if not len(result):
                self.bot.msg(replyto, 'Unknown region :(')
                self.log('Region not found [%s]' % (region,))
                return
            region = str(result[0]['regionName'])
            region_id = result[0]['regionID']
            region_id = int(region_id)
            url += '&regionlimit=%d' % (region_id,)

        result = yield client.getPage(url)
        print result

        #print 'Consider searching market for %d' % (type_id,)

        try:
            dom = minidom.parseString(result)
        except:
            self.bot.msg(replyto, 'XML parse failed :(')
            self.log('XML parse failed (%s)' % item)
            return
        if not dom.getElementsByTagName('marketstat'):
            self.bot.msg(replyto, 'No market data found in the result :(')
            self.log('No market data found in the result (%s)' % item)
            return

        buy_volume = sell_volume = 0
        buy_price = sell_price = 0

        buy = dom.getElementsByTagName('buy')[0]

        buy_volume = buy.getElementsByTagName('volume')
        buy_volume = buy_volume[0].childNodes[0].nodeValue
        buy_volume = int(buy_volume)

        buy_price = buy.getElementsByTagName('max')
        buy_price = buy_price[0].childNodes[0].nodeValue
        buy_price = float(buy_price)

        sell = dom.getElementsByTagName('sell')[0]

        sell_volume = sell.getElementsByTagName('volume')
        sell_volume = sell_volume[0].childNodes[0].nodeValue
        sell_volume = int(sell_volume)

        sell_price = sell.getElementsByTagName('min')
        sell_price = sell_price[0].childNodes[0].nodeValue
        sell_price = float(sell_price)

        locale.setlocale(locale.LC_ALL, '.'.join(locale.getdefaultlocale()))

        if not region:
            region = 'Global'

        msg = '%s (%s): Buy %s, Sell %s' % \
            (item, region,
            locale.format('%.*f', (2, buy_price), True),
            locale.format('%.*f', (2, sell_price), True))
        self.bot.msg(replyto, msg)
        self.log('%s' % msg)

        dom.unlink()

# vim: set et sw=4:
