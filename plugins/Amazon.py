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
Amazon module, to use Amazon's Web Services.  Currently only does ISBN lookups.
"""

import plugins

import amazon

import conf
import utils
import privmsgs
import callbacks


def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    print 'To use Amazon\'s Web Services, you must have a license key.'
    if yn('Do you have a license key?') == 'y':
        key = anything('What is it?')

        onStart.append('load Amazon')
        onStart.append('amazon licensekey %s' % key)
    else:
        print 'You\'ll need to get a key before you can use this plugin.'
        print 'You can apply for a key at http://www.amazon.com/webservices'
        

example = utils.wrapLines("""
<jemfinch> @list Amazon
<supybot> licensekey, isbn
<jemfinch> (licensekey is used to set the license key to access Amazon's web services.  We won't show that here, for obvious reasons.)
<jemfinch> @isbn 0-8050-3906-6
<supybot> "Winning With the French (Openings)", written by Wolfgang Uhlmann; published by Henry Holt & Company, Inc..
<jemfinch> @isbn 0805039066
<supybot> "Winning With the French (Openings)", written by Wolfgang Uhlmann; published by Henry Holt & Company, Inc.. 
""")

class Amazon(callbacks.Privmsg):
    threaded = True
    def licensekey(self, irc, msg, args):
        """<key>

        Sets the license key for using Amazon Web Services.  Must be set before
        any other commands in this module are used.
        """
        key = privmsgs.getArgs(args)
        amazon.setLicense(key)
        irc.reply(msg, conf.replySuccess)
    licensekey = privmsgs.checkCapability(licensekey, 'admin')

    def isbn(self, irc, msg, args):
        """<isbn>

        Returns the book matching the given ISBN number.
        """
        isbn = privmsgs.getArgs(args)
        isbn = isbn.replace('-', '').replace(' ', '')
        try:
            book = amazon.searchByKeyword(isbn)
            title = book.ProductName
            publisher = book.Manufacturer
            if isinstance(book.Authors.Author, basestring):
                author = book.Authors.Author
            else:
                author = utils.commaAndify(book.Authors.Author)
            s = '"%s", written by %s; published by %s.' % \
                 (title,          author,          publisher)
            irc.reply(msg, str(s))
        except amazon.AmazonError, e:
            irc.reply(msg, 'No book was found with that ISBN.')


Class = Amazon

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
