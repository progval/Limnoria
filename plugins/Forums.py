#!/usr/bin/env python

from baseplugin import *

import re
import urllib2

import ircmsgs
import ircutils
import callbacks

htmlStripper = re.compile(r'<[^>]+>')
def stripHtml(s):
    return htmlStripper.sub('', s)

class Forums(callbacks.PrivmsgRegexp):
    threaded = True
    _ggThread = re.compile(r'from thread &quot;<b>(.*?)</b>&quot;')
    _ggGroup = re.compile(r'Newsgroups: <a.*?>(.*?)</a>')
    def googlegroups(self, irc, msg, match):
        r"http://groups.google.com/[^\s]+"
        request = urllib2.Request(match.group(0), headers=\
          {'User-agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT 4.0)'})
        fd = urllib2.urlopen(request)
        text = fd.read()
        mThread = self._ggThread.search(text)
        mGroup = self._ggGroup.search(text)
        if mThread and mGroup:
            irc.queueMsg(ircmsgs.privmsg(ircutils.reply(msg),
              'Google Groups: %s, %s' % (mGroup.group(1), mThread.group(1))))
        else:
            irc.queueMsg(ircmsgs.privmsg(msg.args[0],
              'That doesn\'t appear to be a proper Google Groups page.'))

    gkPlayer = re.compile(r"popd\('(Rating[^']+)'\).*?>([^<]+)<")
    def gameknot(self, irc, msg, match):
        r"http://(?:www\.)?gameknot.com/chess.pl\?bd=\d+&r=\d+"
        fd = urllib2.urlopen(match.group(0))
        s = fd.read()
        try:
            ((wRating, wName), (bRating, bName)) = self.gkPlayer.findall(s)
            wRating = wRating.replace('<br>', ' ')
            bRating = bRating.replace('<br>', ' ')
            wRating = wRating.replace('Wins', '; Wins')
            bRating = bRating.replace('Wins', '; Wins ')
            irc.queueMsg(ircmsgs.privmsg(msg.args[0],
              '%s (%s) vs. %s (%s)' % (wName, wRating, bName, bRating)))
            
        except ValueError:
            irc.queueMsg(ircmsgs.privmsg(msg.args[0],
              'That doesn\'t appear to be a proper Gameknot game.'))


Class = Forums
