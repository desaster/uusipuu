# -*- coding: ISO-8859-15 -*-

from twisted.internet import reactor
from core.Uusipuu import UusipuuModule
from glob import glob
import random

class Module(UusipuuModule):

    def startup(self):
        self.scheduled = None
        self.running = 0
        self.current_question = {}
        self.points = {}
        self.read_questions()

    def read_questions(self):
        # load questions
        self.questions = []
        counter = 0
        self.log('Will read questions')
        for txt in glob('data/trivia/*.txt'):
            f = file(txt)
            for line in f.xreadlines():
                entry = {}
                pieces = line.strip().split('/')[1:]
                if len(pieces) < 3: continue
                entry['category'] = pieces[0]
                entry['answers'] = [x.strip().lower() for x in pieces[1:-2]]
                entry['question'] = pieces[-1]
                self.questions.append(entry)
                counter += 1
            f.close()

        random.shuffle(self.questions)
        self.log('Questions read: %d' % counter)

    def shutdown(self):
        self.cancel_scheduled()

    def cmd_trivia(self, user, target, params):
        nick = user.split('!', 1)[0]
        if self.running:
            return
        self.running = 1
        self.points = {}
        self.chanmsg('Trivia started by %s!' % nick)
        self.scheduled = reactor.callLater(5, self.ask_question)

    def cmd_stop(self, user, target, params):
        nick = user.split('!', 1)[0]
        if not self.running:
            self.log('trivia not running!')
            return
        self.running = 0
        self.cancel_scheduled()
        self.chanmsg('Trivia stopped by %s!' % nick)
        if len(self.points):
            points = []
            for player in self.points.keys():
                points.append('%s: %d' % (player, self.points[player]))
            self.chanmsg('Final scores: %s' % ', '.join(points))

    def privmsg(self, user, target, msg):
        nick = user.split('!', 1)[0]
        if self.running and len(self.current_question):
            if msg.strip().lower() in self.current_question['answers']:
                self.cancel_scheduled()
                self.chanmsg(
                    'Congratulations %s! The correct answer was %s' % \
                    (nick, msg))
                self.current_question = {}
                if not self.points.has_key(nick):
                    self.points[nick] = 1
                else:
                    self.points[nick] += 1
                self.scheduled = reactor.callLater(3, self.ask_question)

    def cancel_scheduled(self):
        if self.scheduled and self.scheduled.active():
            self.scheduled.cancel()
        self.scheduled = None

    def ask_question(self):
        if not self.running:
            return
        self.cancel_scheduled()
        self.current_question = self.questions.pop(0)
        self.chanmsg('%s: %s' % (self.current_question['category'],
            self.current_question['question']))
        self.log('Asking question: %s' % self.current_question['question'])

        self.scheduled = reactor.callLater(20, self.hint)

    def hint(self):
        self.cancel_scheduled()

        answer = random.choice(self.current_question['answers'])
        aidlen = len(answer)/3
        if not aidlen:
            aidlen = 1
        if len(answer) <= 1:
            aidlen = 0
        aid = answer[:aidlen]
        aid = aid + ''.join([['_',' '][c == ' '] for c in answer[aidlen:]])

        self.chanmsg('Here\'s a hint! %s' % aid)
        self.log('Giving a hint: %s' % aid)
        self.scheduled = reactor.callLater(15, self.time_up)

    def time_up(self):
        if not self.running:
            return
        self.cancel_scheduled()
        #self.bot.msg(self.channel,
        #    'Time\'s up! The correct answer would have been: %s' % \
        #    self.current_question['answers'][0])
        self.chanmsg('Time\'s up!')
        self.current_question = {}
        self.scheduled = reactor.callLater(5, self.ask_question)

# vim: set et sw=4:
