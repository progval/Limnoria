#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

"""
Does various (well, only one at the moment :)) things with the Internet Movie
Database.
"""

deprecated = True

__revision__ = "$Id$"

import plugins

from itertools import imap

import IMDb

import utils
import privmsgs
import callbacks


def configure(onStart):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    conf.registerPlugin('Movies', True)

class Movies(callbacks.Privmsg):
    threaded = True
    def _formatMovie(self, movie):
        title = utils.unCommaThe(movie.title())
        genres = utils.commaAndify(imap(str.lower, movie.genres()))
        s = '"%s" (%s) belongs to the %s %s.  ' \
            'It\'s been rated %s out of 10.  ' \
            'More information is available at <%s>' % \
            (title, movie.year(), genres,
             utils.pluralize('genre', len(movie.genres())),
             movie.rating(), movie.url)
        return s
        
    def imdb(self, irc, msg, args):
        """<movie title>

        Returns the IMDB information on the movie given.
        """
        movieTitle = privmsgs.getArgs(args)
        db = IMDb.IMDb()
        movies = db.search(movieTitle)
        if len(movies) == 0:
            irc.reply('No movies matched that title.')
        elif len(movies) == 1:
            movie = movies[0]
            if 'Name?' in movie.url:
                s = '"%s" is apparently a person.  ' \
                    'More information is available at <%s>' % \
                    (movie.title(), movie.url)
                irc.reply(s)
            else:
                irc.reply(self._formatMovie(movie))
        elif len(movies) > 20:
            s = 'More than 20 movies matched, please narrow your search.'
            irc.reply(s)
        else:
            for movie in movies:
                title = movie.title().lower()
                if utils.unCommaThe(title) == movieTitle.lower():
                    irc.reply(self._formatMovie(movie))
                    return
            titles = ['%s (%s)' % \
                      (utils.unCommaThe(movie.title()), movie.year())
                      for movie in movies]
            irc.reply('Matches: ' + utils.commaAndify(titles))


Class = Movies


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
