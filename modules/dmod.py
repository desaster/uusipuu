# -*- coding: ISO-8859-15 -*-

# Dynamic module handling

from core.Uusipuu import UusipuuModule, classloader
from core import meminfo
import traceback

class Module(UusipuuModule):
    
    def cmd_modules(self, user, channel, params):
        if not self.bot.is_admin(user):
            return False

        self.chanmsg('Modules for this channel: %s' %
            ', '.join([x.name for x in
                self.bot.channels[self.channel]['modules']]))

    def cmd_unload(self, user, channel, params):
        nick = user.split('!', 1)[0]
        name = params.strip()

        if not self.bot.is_admin(user):
            return False

        if name == self.name:
            self.chanmsg('I don\'t wanna unload myself!')
            return False

        mods = self.bot.config['onload']['channels'][channel]['modules']
        if name in mods:
            mods.remove(name)
            self.bot.save()

        for module in self.bot.channels[channel]['modules'][:]:
            if module.name == name:
                module._shutdown()
                self.bot.channels[channel]['modules'].remove(module)
                self.chanmsg('Module %s has been unloaded' % module.name)
                return True


        self.chanmsg('Module %s not found' % name)
        return False
    
    def cmd_load(self, user, channel, params):
        if not self.bot.is_admin(user):
            return False

        nick = user.split('!', 1)[0]
        name = params.strip()

        modules = [x.name for x in self.bot.channels[channel]['modules']]
        if modules.count(name):
            self.chanmsg('Module %s already running' % name)
            return False

        try:
            c = classloader._get_class('modules.%s.Module' % name)
        except:
            self.chanmsg('Module %s not found' % name)
            return False

        m = c(self.bot, channel)
        self.bot.channels[channel]['modules'].append(m)
        self.bot.config['onload']['channels'][channel]['modules'].append(name)
        self.bot.save()
        self.chanmsg('Module %s has been loaded' % name)
        return True

    def cmd_reload(self, user, target, params):
        if not self.bot.is_admin(user):
            return False

        self.log('Will reload all modules')

        mem_before = meminfo.memory()

        memory, names, failed, total = {}, [], 0, 0
        for channel in self.bot.channels:
            memory[channel] = []
            for module in self.bot.channels[channel]['modules'][:]:
                if module.name == self.name:
                    continue
                memory[channel].append(module.name)
                if not names.count(module.name):
                    names.append(module.name)
                module._shutdown()
                self.bot.channels[channel]['modules'].remove(module)

        for name in names:
            self.log('Reloading module %s' % name)
            m = __import__('%s' % name, globals(), locals(), ['*'])
            total += 1
            try:
                reload(m)
            except:
                traceback.print_exc()
                failed += 1

        onload = self.bot.config['onload']
        for channel in onload['channels']:
            for module in onload['channels'][channel]['modules']:
                if module == self.name:
                    continue
                total += 1
                try:
                    c = classloader._get_class('modules.%s.Module' % module)
                    m = c(self.bot, channel)
                    self.bot.channels[channel]['modules'].append(m)
                except:
                    traceback.print_exc()
                    failed += 1

        mem_after = meminfo.memory()

        if mem_after > mem_before:
            mem_msg = 'Memory increased by %d bytes.' % \
                (mem_after - mem_before)
        elif mem_after < mem_before:
            mem_msg = 'Memory decreased by %d bytes.' % \
                (mem_before - mem_after)
        else:
            mem_msg = 'Memory didn\'t change.'

        self.log('Reloading modules finished. %s' % mem_msg)
        self.chanmsg('Reload done. %s' % mem_msg)

# vim: set et sw=4:
