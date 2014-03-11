#!/usr/bin/env python
#
# Configuration is saved in UTF-8 but loaded as ISO-8859-1
#

from xml.dom import minidom

def save(conf):

    doc = minidom.getDOMImplementation().createDocument(None, 'data', None)
    top = doc.documentElement

    def iitems(stuff):
        items = []

        for item in stuff:
            e = doc.createElement('item')

            if type(stuff) == dict:
                value = stuff[item]
                e.setAttribute('name',
                    item.decode('ISO-8859-1').encode('UTF-8'))
            elif type(stuff) == list:
                value = item

            if type(value) == dict:
                e.setAttribute('type', 'dict')
                for item in iitems(value):
                    e.appendChild(item)
            elif type(value) == list:
                e.setAttribute('type', 'list')
                for item in iitems(value):
                    e.appendChild(item)
            elif type(value) in (unicode, str):
                e.setAttribute('type', 'str')
                e.appendChild(doc.createTextNode(
                    value.decode('ISO-8859-1').encode('UTF-8')))
            elif type(value) in (long, int):
                e.setAttribute('type', 'int')
                e.setAttribute('value', str(value))
            elif type(value) == float:
                e.setAttribute('type', 'float')
                e.setAttribute('value', str(value))
            else:
                print 'Warning: unhandled type: %s' % repr(type(value))
                continue

            items.append(e)

        return items

    for item in iitems(conf):
        top.appendChild(item)

    xml = doc.toprettyxml('  ', '\r\n')
    doc.unlink()

    return xml

def load(xml):

    doc = minidom.parseString(xml)
    top = doc.firstChild
    data = {}

    def iitems(node):
        itype = node.getAttribute('type')
        if itype == 'dict':
            value = {}
            for item in node.childNodes:
                if item.nodeType != item.ELEMENT_NODE or \
                        item.nodeName != 'item':
                    continue
                name = item.getAttribute('name')
                value[name.encode('ISO-8859-1')] = iitems(item)
        elif itype == 'list':
            value = []
            for item in node.childNodes:
                if item.nodeType != item.ELEMENT_NODE or \
                        item.nodeName != 'item':
                    continue
                value.append(iitems(item))
        elif itype in ('int', 'long'):
            value = int(node.getAttribute('value'))
        elif itype == 'float':
            value = float(node.getAttribute('value'))
        elif itype == 'str':
            value = unicode()
            for text in node.childNodes:
                if text.nodeType != text.TEXT_NODE:
                    continue
                value += text.data
            value = value.encode('ISO-8859-1').strip()
        else:
            print 'Warning: unhandled type: %s' % \
                    repr(node.getAttribute('type'))
            value = False

        return value

    for node in top.childNodes:
        if node.nodeType != node.ELEMENT_NODE or node.nodeName != 'item':
            continue
        data[node.getAttribute('name')] = iitems(node)

    doc.unlink()

    return data

# vim: set sw=4 et:
