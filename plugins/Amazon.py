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

__revision__ = "$Id$"

import getopt
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
        

class Amazon(callbacks.Privmsg):
    threaded = True

    def _genResults(self, reply, attribs, items, url):
        results = {}
        res = []
        if isinstance(items, amazon.Bag):
            items = [items]
        for item in items:
            try:
                for k,v in attribs.iteritems():
                    results[v] = getattr(item, k, 'unknown')
                    if isinstance(results[v], amazon.Bag):
                        results[v] = getattr(results[v], k[:-1], 'unknown')
                    if not isinstance(results[v], basestring):
                        results[v] = utils.commaAndify(results[v])
                if not url:
                    results['url'] = ''
                else:
                    results['url'] = ' <%s>' % results['url']
                s = reply % results
                s.encode('utf-8')
                res.append(str(s))
            except amazon.AmazonError, e:
                self.log.warning(str(e))
            except UnicodeEncodeError, e:
                self.log.warning(str(e))
        return res

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
        """[--url] <isbn>

        Returns the book matching the given ISBN number. If --url is
        specified, a link to amazon.com's page for the book will also be
        returned.
        """
        opts = ['url']
        (optlist, rest) = getopt.getopt(args, '', opts)
        url = False
        for (option, argument) in optlist:
            option = option.lstrip('-')
            if option == 'url':
                url = True
        isbn = privmsgs.getArgs(rest)
        isbn = isbn.replace('-', '').replace(' ', '')
        attribs = {'ProductName' : 'title',
                   'Manufacturer' : 'publisher',
                   'Authors' : 'author',
                   'URL' : 'url'
                  }
        s = '"%(title)s", written by %(author)s; published by '\
            '%(publisher)s%(url)s'
        try:
            book = amazon.searchByKeyword(isbn)
            res = self._genResults(s, attribs, book, url)
            if res:
                irc.reply(msg, utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.error(msg, 'No book was found with that ISBN.')

    def asin(self, irc, msg, args):
        """[--url] <asin>

        Returns the item matching the given ASIN number. If --url is
        specified, a link to amazon.com's page for the item will also be
        returned.
        """
        opts = ['url']
        (optlist, rest) = getopt.getopt(args, '', opts)
        url = False
        for (option, argument) in optlist:
            option = option.lstrip('-')
            if option == 'url':
                url = True
        asin = privmsgs.getArgs(rest)
        asin = asin.replace('-', '').replace(' ', '')
        attribs = {'ProductName' : 'title',
                   'URL' : 'url'
                  }
        s = '"%(title)s"%(url)s'
        try:
            item = amazon.searchByASIN(asin)
            res = self._genResults(s, attribs, item, url)
            if res:
                irc.reply(msg, utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.error(msg, 'No item was found with that ASIN.')

    def upc(self, irc, msg, args):
        """[--url] <upc>

        Returns the item matching the given UPC number.  If --url is
        specified, a link to amazon.com's page for the item will also be
        returned.  Only items in the following categories may be found via upc
        search: music, classical, software, dvd, video, vhs, electronics,
        pc-hardware, and photo.
        """
        opts = ['url']
        (optlist, rest) = getopt.getopt(args, '', opts)
        url = False
        for (option, argument) in optlist:
            option = option.lstrip('-')
            if option == 'url':
                url = True
        upc = privmsgs.getArgs(rest)
        upc = upc.replace('-', '').replace(' ', '')
        attribs = {'ProductName' : 'title',
                   'Manufacturer' : 'manufacturer',
                   'URL' : 'url'
                  }
        s = '"%(title)s" %(manufacturer)s%(url)s'
        try:
            item = amazon.searchByUPC(upc)
            res = self._genResults(s, attribs, item, url)
            if res:
                irc.reply(msg, utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.error(msg, 'No item was found with that UPC.')

    def author(self, irc, msg, args):
        """[--url] <author>

        Returns a list of books written by the given author. If --url is
        specified, a link to amazon.com's page for the book will also be
        returned.
        """
        opts = ['url']
        (optlist, rest) = getopt.getopt(args, '', opts)
        url = False
        for (option, argument) in optlist:
            option = option.lstrip('-')
            if option == 'url':
                url = True
        author = privmsgs.getArgs(rest)
        attribs = {'ProductName' : 'title',
                   'Manufacturer' : 'publisher',
                   'Authors' : 'author',
                   'URL' : 'url'
                  }
        s = '"%(title)s", written by %(author)s; published by '\
            '%(publisher)s%(url)s'
        try:
            books = amazon.searchByAuthor(author)
            res = self._genResults(s, attribs, books, url)
            if res:
                irc.reply(msg, utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.error(msg, 'No books were found by that author.')

# FIXME: Until I get a *good* list of categories (ones that actually work),
#        these commands will remain unavailable
    '''
    _textToNode = {'dvds':'130', 'magazines':'599872', 'music':'301668',
                   'software':'491286', 'vhs':'404272', 'kitchen':'491864',
                   'video games':'471280', 'toys':'491290', 'camera':'502394',
                   'outdoor':'468250', 'computers':'565118', 'tools':'468240',
                   'electronics':'172282'
                  }
    def categories(self, irc, msg, args):
        """takes no arguments

        Returns a list of valid categories to use with the bestsellers
        commands.
        """
        cats = self._textToNode.keys()
        cats.sort()
        irc.reply(msg, utils.commaAndify(cats))

    def bestsellers(self, irc, msg, args):
        """[--url] <category>

        Returns a list of best selling items in <category>. The 'categories'
        command will return a list of the available categores.  If --url
        is specified, a link to amazon.com's page for the item will also be
        returned.
        """
        opts = ['url']
        (optlist, rest) = getopt.getopt(args, '', opts)
        url = False
        for (option, argument) in optlist:
            option = option.lstrip('-')
            if option == 'url':
                url = True
        category = privmsgs.getArgs(rest).lower()
        if category not in self._textToNode:
            irc.error(msg, 'An invalid category was specified. The categories'
                           ' command will return a list of valid categories')
            return
        category = self._textToNode[category]
        attribs = {'ProductName' : 'title',
                   'Manufacturer' : 'publisher',
                   'URL' : 'url'
                  }
        s = '"%(title)s", from %(publisher)s.%(url)s'
        try:
            #self.log.warning(category)
            items = amazon.browseBestSellers(category)
            #self.log.warning(items)
            res = self._genResults(s, attribs, items, url)
            if res:
                irc.reply(msg, utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.error(msg, 'No items were found on that best seller list.')
    '''


    def artist(self, irc, msg, args):
        """[--url] [--{music,classical}] <artist>

        Returns a list of items by the given artist. If --url is specified, a
        link to amazon.com's page for the match will also be returned. The
        search defaults to using --music.
        """
        products = ['music', 'classical']
        opts = ['url']
        (optlist, rest) = getopt.getopt(args, '', products + opts)
        url = False
        product = ''
        for (option, argument) in optlist:
            option = option.lstrip('-')
            if option == 'url':
                url = True
            if option in products:
                product = option
        product = product or 'music'
        artist = privmsgs.getArgs(rest)
        attribs = {'ProductName' : 'title',
                   'Manufacturer' : 'publisher',
                   'Artists' : 'artist',
                   'Media' : 'media',
                   'URL' : 'url'
                  }
        s = '"%(title)s" (%(media)s), by %(artist)s; published by '\
            '%(publisher)s%(url)s'
        try:
            items = amazon.searchByArtist(artist, product_line=product)
            res = self._genResults(s, attribs, items, url)
            if res:
                irc.reply(msg, utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.error(msg, 'No items were found by that artist.')

    def actor(self, irc, msg, args):
        """[--url] [--{dvd,vhs,video}] <actor>

        Returns a list of items starring the given actor. If --url is
        specified, a link to amazon.com's page for the match will also be
        returned. The search defaults to using --dvd.
        """
        products = ['dvd', 'video', 'vhs']
        opts = ['url']
        (optlist, rest) = getopt.getopt(args, '', products + opts)
        url = False
        product = ''
        for (option, argument) in optlist:
            option = option.lstrip('-')
            if option == 'url':
                url = True
            if option in products:
                product = option
        product = product or 'dvd'
        actor = privmsgs.getArgs(rest)
        attribs = {'ProductName' : 'title',
                   'Manufacturer' : 'publisher',
                   'MpaaRating' : 'mpaa',
                   'Media' : 'media',
                   'ReleaseDate' : 'date',
                   'URL' : 'url'
                  }
        s = '"%(title)s" (%(media)s), rated %(mpaa)s; released '\
            '%(date)s; published by %(publisher)s%(url)s'
        try:
            items = amazon.searchByActor(actor, product_line=product)
            res = self._genResults(s, attribs, items, url)
            if res:
                irc.reply(msg, utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.error(msg, 'No items were found starring that actor.')

    def director(self, irc, msg, args):
        """[--url] [--{dvd,vhs,video}] <director>

        Returns a list of items by the given director. If --url is
        specified, a link to amazon.com's page for the match will also be
        returned. The search defaults to using --dvd.
        """
        products = ['dvd', 'video', 'vhs']
        opts = ['url']
        (optlist, rest) = getopt.getopt(args, '', products + opts)
        url = False
        product = ''
        for (option, argument) in optlist:
            option = option.lstrip('-')
            if option == 'url':
                url = True
            if option in products:
                product = option
        product = product or 'dvd'
        director = privmsgs.getArgs(rest)
        attribs = {'ProductName' : 'title',
                   'Manufacturer' : 'publisher',
                   'MpaaRating' : 'mpaa',
                   'Media' : 'media',
                   'ReleaseDate' : 'date',
                   'URL' : 'url'
                  }
        s = '"%(title)s" (%(media)s), rated %(mpaa)s; released '\
            '%(date)s; published by %(publisher)s%(url)s'
        try:
            items = amazon.searchByDirector(director, product_line=product)
            res = self._genResults(s, attribs, items, url)
            if res:
                irc.reply(msg, utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.error(msg, 'No items were found by that director.')

    def manufacturer(self, irc, msg, args):
        """ [--url] \
        [--{pc-hardware,kitchen,electronics,videogames,software,photo}] \
        <manufacturer>

        Returns a list of items by the given manufacturer. If --url is
        specified, a link to amazon.com's page for the match will also be
        returned. The search defaults to using --pc-hardware.
        """
        products = ['electronics', 'kitchen', 'videogames', 'software',
                    'photo', 'pc-hardware']
        opts = ['url']
        (optlist, rest) = getopt.getopt(args, '', products + opts)
        url = False
        product = ''
        for (option, argument) in optlist:
            option = option.lstrip('-')
            if option == 'url':
                url = True
            if option in products:
                product = option
        product = product or 'pc-hardware'
        manufacturer = privmsgs.getArgs(rest)
        attribs = {'ProductName' : 'title',
                   'URL' : 'url'
                  }
        s = '"%(title)s"%(url)s'
        try:
            items = amazon.searchByManufacturer(manufacturer,
                                                product_line=product)
            res = self._genResults(s, attribs, items, url)
            if res:
                irc.reply(msg, utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.error(msg, 'No items were found by that manufacturer.')

Class = Amazon

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
