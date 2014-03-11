# -*- coding: ISO-8859-15 -*-

def tdiff(seconds):
    t = seconds
    days = int(t / (24 * 60 * 60))
    t -= (days * 24 * 60 * 60)
    hours = int(t / (60 * 60))
    t -= (hours * 60 * 60)
    minutes = int(t / 60)
    t -= (minutes * 60)

    if int(t) == 1:
        s = '%d sekunti' % int(t)
    else:
        s = '%d sekuntia' % int(t)

    if minutes == 1:
        s = '%d minuutti %s' % (minutes, s)
    elif minutes > 1:
        s = '%d minuuttia %s' % (minutes, s)

    if hours == 1:
        s = '%d tunti %s' % (hours, s)
    elif hours > 1:
        s = '%d tuntia %s' % (hours, s)

    if days == 1:
        s = '%d päivä %s' % (days, s)
    elif days > 1:
        s = '%d päivää %s' % (days, s)
    return s

def stdiff(seconds):
    t = seconds
    days = int(t / (24 * 60 * 60))
    t -= (days * 24 * 60 * 60)
    hours = int(t / (60 * 60))
    t -= (hours * 60 * 60)
    minutes = int(t / 60)
    t -= (minutes * 60)

    s = '%ds' % int(t)
    if minutes >= 1: s = '%dm %s' % (minutes, s)
    if hours >= 1: s = '%dh %s' % (hours, s)
    if days >= 1: s = '%dd %s' % (days, s)
    return s

# vim: set et sw=4:
