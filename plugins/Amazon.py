###
# Copyright (c) 2002-2004, Jeremiah Fincher
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
Amazon module, to use Amazon's Web Services.
"""

import supybot

__revision__ = "$Id$"
__author__ = supybot.authors.jamessan

import getopt

import amazon

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.privmsgs as privmsgs
import supybot.registry as registry
import supybot.callbacks as callbacks


def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    output('To use Amazon\'s Web Services, you must have a license key.')
    if yn('Do you have a license key?'):
        key = anything('What is it?')

        conf.registerPlugin('Amazon', True)
        conf.supybot.plugins.Amazon.licenseKey.set(key)
    else:
        output("""You'll need to get a key before you can use this plugin.
                  You can apply for a key at
                  http://www.amazon.com/webservices/""")

class Region(registry.OnlySomeStrings):
    validStrings = ('us', 'uk', 'de', 'jp')

class LicenseKey(registry.String):
    def set(self, s):
        # In case we decide we need to recover
        original = getattr(self, 'value', self._default)
        registry.String.set(self, s)
        if self.value:
            amazon.setLicense(self.value)

conf.registerPlugin('Amazon')
conf.registerChannelValue(conf.supybot.plugins.Amazon, 'bold',
    registry.Boolean(True, """Determines whether the results are bolded."""))
conf.registerGlobalValue(conf.supybot.plugins.Amazon, 'licenseKey',
    LicenseKey('', """Sets the license key for using Amazon Web Services.
    Must be set before any other commands in the plugin are used.""",
    private=True))
conf.registerChannelValue(conf.supybot.plugins.Amazon, 'linkSnarfer',
    registry.Boolean(False, """Determines whether the bot will reply to
    Amazon.com URLs in the channel with a description of the item at the
    URL."""))
conf.registerChannelValue(conf.supybot.plugins.Amazon, 'region', Region('us',
    """Determines the region that will be used when performing searches."""))

class Amazon(callbacks.PrivmsgCommandAndRegexp):
    threaded = True
    callBefore = ['URL']
    regexps = ['amzSnarfer']
    def __init__(self):
        self.__parent = super(Amazon, self)
        self.__parent.__init__()

    def callCommand(self, name, irc, msg, *L, **kwargs):
        try:
            self.__parent.callCommand(name, irc, msg, *L, **kwargs)
        except amazon.NoLicenseKey, e:
            irc.error('You must have a free Amazon web services license key '
                      'in order to use this command.  You can get one at '
                      '<http://www.amazon.com/webservices>.  Once you have '
                      'one, you can set it with the command '
                      '"config supybot.plugins.Amazon.licensekey <key>".')

    def _genResults(self, reply, attribs, items, url, bold):
        results = {}
        res = []
        bold_item = 'title'
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
                if bold_item in results:
                    if bold:
                        results[bold_item] = ircutils.bold(results[bold_item])
                    else:
                        results[bold_item] = '"%s"' % results[bold_item]
                if not url:
                    results['url'] = ''
                else:
                    results['url'] = ' <%s>' % results['url']
                s = reply % results
                if isinstance(s, unicode):
                    s = s.encode('utf-8')
                res.append(str(s))
            except amazon.AmazonError, e:
                self.log.warning(str(e))
            except UnicodeEncodeError, e:
                self.log.warning(str(e))
        return res

    def isbn(self, irc, msg, args, optlist, isbn):
        """[--url] <isbn>

        Returns the book matching the given ISBN number. If --url is
        specified, a link to amazon.com's page for the book will also be
        returned.
        """
        url = False
        for (option, argument) in optlist:
            if option == 'url':
                url = True
        isbn = isbn.replace('-', '').replace(' ', '')
        attribs = {'ProductName' : 'title',
                   'Manufacturer' : 'publisher',
                   'Authors' : 'author',
                   'OurPrice' : 'price',
                   'URL' : 'url'
                  }
        s = '%(title)s, written by %(author)s; published by ' \
            '%(publisher)s; price: %(price)s%(url)s'
        channel = msg.args[0]
        bold = self.registryValue('bold', channel)
        region = self.registryValue('region', channel)
        try:
            book = amazon.searchByKeyword(isbn, locale=region)
            res = self._genResults(s, attribs, book, url, bold)
            if res:
                irc.reply(utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.reply('No book was found with that ISBN.')
    isbn = wrap(isbn, [getopts({'url':''}), 'text'])

    def books(self, irc, msg, args, optlist, keyword):
        """[--url] <keywords>

        Returns the books matching the given <keywords> search. If --url is
        specified, a link to amazon.com's page for the book will also be
        returned.
        """
        url = False
        for (option, _) in optlist:
            if option == 'url':
                url = True
        attribs = {'ProductName' : 'title',
                   'Manufacturer' : 'publisher',
                   'Authors' : 'author',
                   'OurPrice' : 'price',
                   'URL' : 'url'
                  }
        s = '%(title)s, written by %(author)s; published by ' \
            '%(publisher)s; price: %(price)s%(url)s'
        channel = msg.args[0]
        region = self.registryValue('region', channel)
        bold = self.registryValue('bold', channel)
        try:
            books = amazon.searchByKeyword(keyword, locale=region)
            res = self._genResults(s, attribs, books, url, bold)
            if res:
                irc.reply(utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.reply('No books were found with that keyword search.')
    books = wrap(books, [getopts({'url':''}), 'text'])

    def videos(self, irc, msg, args, optlist, keyword):
        """[--url] [--{dvd,vhs}] <keywords>

        Returns the videos matching the given <keyword> search. If --url is
        specified, a link to amazon.com's page for the video will also be
        returned.  Search defaults to using --dvd.
        """
        url = False
        product = 'dvd'
        for (option, _) in optlist:
            if option == 'url':
                url = True
            else:
                product = option
        attribs = {'ProductName' : 'title',
                   'Manufacturer' : 'publisher',
                   'MpaaRating' : 'mpaa',
                   'Media' : 'media',
                   'ReleaseDate' : 'date',
                   'OurPrice' : 'price',
                   'URL' : 'url'
                  }
        s = '%(title)s (%(media)s), rated %(mpaa)s; released ' \
            '%(date)s; published by %(publisher)s; price: %(price)s%(url)s'
        channel = msg.args[0]
        region = self.registryValue('region', channel)
        bold = self.registryValue('bold', channel)
        try:
            videos = amazon.searchByKeyword(keyword, product_line=product,
                                            locale=region)
            res = self._genResults(s, attribs, videos, url, bold)
            if res:
                irc.reply(utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.reply('No videos were found with that keyword search.')
    videos = wrap(videos, [getopts({'url':'', 'dvd':'', 'vhs':''}), 'text'])

    def asin(self, irc, msg, args, optlist, asin):
        """[--url] <asin>

        Returns the item matching the given ASIN number. If --url is
        specified, a link to amazon.com's page for the item will also be
        returned.
        """
        url = False
        for (option, _) in optlist:
            if option == 'url':
                url = True
        asin = asin.replace('-', '').replace(' ', '')
        attribs = {'ProductName' : 'title',
                   'OurPrice' : 'price',
                   'URL' : 'url'
                  }
        s = '%(title)s; price: %(price)s%(url)s'
        channel = msg.args[0]
        region = self.registryValue('region', channel)
        bold = self.registryValue('bold', channel)
        try:
            item = amazon.searchByASIN(asin, locale=region)
            res = self._genResults(s, attribs, item, url, bold)
            if res:
                irc.reply(utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.reply('No item was found with that ASIN.')
    asin = wrap(asin, [getopts({'url':''}), 'text'])

    def upc(self, irc, msg, args, optlist, upc):
        """[--url] <upc>

        Returns the item matching the given UPC number.  If --url is
        specified, a link to amazon.com's page for the item will also be
        returned.  Only items in the following categories may be found via upc
        search: music, classical, software, dvd, video, vhs, electronics,
        pc-hardware, and photo.
        """
        url = False
        for (option, _) in optlist:
            if option == 'url':
                url = True
        upc = upc.replace('-', '').replace(' ', '')
        attribs = {'ProductName' : 'title',
                   'Manufacturer' : 'manufacturer',
                   'OurPrice' : 'price',
                   'URL' : 'url'
                  }
        s = '%(title)s %(manufacturer)s; price: %(price)s%(url)s'
        channel = msg.args[0]
        region = self.registryValue('region', channel)
        bold = self.registryValue('bold', channel)
        try:
            item = amazon.searchByUPC(upc, locale=region)
            res = self._genResults(s, attribs, item, url, bold)
            if res:
                irc.reply(utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.reply('No item was found with that UPC.')
    upc = wrap(upc, [getopts({'url':''}), 'text'])

    def author(self, irc, msg, args, optlist, author):
        """[--url] <author>

        Returns a list of books written by the given author. If --url is
        specified, a link to amazon.com's page for the book will also be
        returned.
        """
        url = False
        for (option, argument) in optlist:
            if option == 'url':
                url = True
        attribs = {'ProductName' : 'title',
                   'Manufacturer' : 'publisher',
                   'Authors' : 'author',
                   'OurPrice' : 'price',
                   'URL' : 'url'
                  }
        s = '%(title)s, written by %(author)s; published by ' \
            '%(publisher)s; price: %(price)s%(url)s'
        channel = msg.args[0]
        region = self.registryValue('region', channel)
        bold = self.registryValue('bold', channel)
        try:
            books = amazon.searchByAuthor(author, locale=region)
            res = self._genResults(s, attribs, books, url, bold)
            if res:
                irc.reply(utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.reply('No books were found by that author.')
    author = wrap(author, [getopts({'url':''}), 'text'])

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
        irc.reply(utils.commaAndify(cats))
    categories = wrap(categories)

    def bestsellers(self, irc, msg, args, optlist, category):
        """[--url] <category>

        Returns a list of best selling items in <category>. The 'categories'
        command will return a list of the available categories.  If --url
        is specified, a link to amazon.com's page for the item will also be
        returned.
        """
        url = False
        for (option, _) in optlist:
            if option == 'url':
                url = True
        if category not in self._textToNode:
            irc.error('An invalid category was specified. The categories'
                           ' command will return a list of valid categories')
            return
        category = self._textToNode[category]
        attribs = {'ProductName' : 'title',
                   'Manufacturer' : 'publisher',
                   'URL' : 'url'
                  }
        s = '"%(title)s", from %(publisher)s.%(url)s'
        channel = msg.args[0]
        region = self.registryValue('region', channel)
        bold = self.registryValue('bold', channel)
        try:
            items = amazon.browseBestSellers(category, locale=region)
            res = self._genResults(s, attribs, items, url, bold)
            if res:
                irc.reply(utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.reply('No items were found on that best seller list.')
    bestsellers = wrap(bestsellers, [getopts({'url':''}), rest('lowered')])
    '''


    def artist(self, irc, msg, args, optlist, artist):
        """[--url] [--{music,classical}] <artist>

        Returns a list of items by the given artist. If --url is specified, a
        link to amazon.com's page for the match will also be returned. The
        search defaults to using --music.
        """
        url = False
        product = None
        for (option, _) in optlist:
            if option == 'url':
                url = True
            else:
                product = option
        product = product or 'music'
        attribs = {'ProductName' : 'title',
                   'Manufacturer' : 'publisher',
                   'Artists' : 'artist',
                   'Media' : 'media',
                   'OurPrice' : 'price',
                   'URL' : 'url'
                  }
        s = '%(title)s (%(media)s), by %(artist)s; published by ' \
            '%(publisher)s; price: %(price)s%(url)s'
        channel = msg.args[0]
        region = self.registryValue('region', channel)
        bold = self.registryValue('bold', channel)
        try:
            items = amazon.searchByArtist(artist, product_line=product,
                                          locale=region)
            res = self._genResults(s, attribs, items, url, bold)
            if res:
                irc.reply(utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.reply('No items were found by that artist.')
    artist = wrap(artist, [getopts({'music':'', 'classical':'', 'url':''}),
                           'text'])

    def actor(self, irc, msg, args, optlist, actor):
        """[--url] [--{dvd,vhs,video}] <actor>

        Returns a list of items starring the given actor. If --url is
        specified, a link to amazon.com's page for the match will also be
        returned. The search defaults to using --dvd.
        """
        url = False
        product = ''
        for (option, _) in optlist:
            if option == 'url':
                url = True
            else:
                product = option
        product = product or 'dvd'
        attribs = {'ProductName' : 'title',
                   'Manufacturer' : 'publisher',
                   'MpaaRating' : 'mpaa',
                   'Media' : 'media',
                   'ReleaseDate' : 'date',
                   'OurPrice' : 'price',
                   'URL' : 'url'
                  }
        s = '%(title)s (%(media)s), rated %(mpaa)s; released ' \
            '%(date)s; published by %(publisher)s; price: %(price)s%(url)s'
        channel = msg.args[0]
        region = self.registryValue('region', channel)
        bold = self.registryValue('bold', channel)
        try:
            items = amazon.searchByActor(actor, product_line=product,
                                         locale=region)
            res = self._genResults(s, attribs, items, url, bold)
            if res:
                irc.reply(utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.reply('No items were found starring that actor.')
    actor = wrap(actor, [getopts({'dvd': '', 'video': '', 'vhs':'', 'url':''}),
                         'text'])

    def director(self, irc, msg, args, optlist, director):
        """[--url] [--{dvd,vhs,video}] <director>

        Returns a list of items by the given director. If --url is
        specified, a link to amazon.com's page for the match will also be
        returned. The search defaults to using --dvd.
        """
        url = False
        product = None
        for (option, _) in optlist:
            if option == 'url':
                url = True
            else:
                product = option
        product = product or 'dvd'
        attribs = {'ProductName' : 'title',
                   'Manufacturer' : 'publisher',
                   'MpaaRating' : 'mpaa',
                   'Media' : 'media',
                   'ReleaseDate' : 'date',
                   'OurPrice' : 'price',
                   'URL' : 'url'
                  }
        s = '%(title)s (%(media)s), rated %(mpaa)s; released ' \
            '%(date)s; published by %(publisher)s; price: %(price)s%(url)s'
        channel = msg.args[0]
        region = self.registryValue('region', channel)
        bold = self.registryValue('bold', channel)
        try:
            items = amazon.searchByDirector(director, product_line=product,
                                            locale=region)
            res = self._genResults(s, attribs, items, url, bold)
            if res:
                irc.reply(utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.reply('No items were found by that director.')
    director = wrap(director, [getopts({'dvd': '', 'video': '', 'vhs': '',
                                        'url': ''}),
                               'text'])

    def manufacturer(self, irc, msg, args, optlist, manufacturer):
        """ [--url] \
        [--{pc-hardware,kitchen,electronics,videogames,software,photo}] \
        <manufacturer>

        Returns a list of items by the given manufacturer. If --url is
        specified, a link to amazon.com's page for the match will also be
        returned. The search defaults to using --pc-hardware.
        """
        url = False
        product = None
        for (option, _) in optlist:
            if option == 'url':
                url = True
            else:
                product = option
        product = product or 'pc-hardware'
        attribs = {'ProductName' : 'title',
                   'OurPrice' : 'price',
                   'URL' : 'url'
                  }
        s = '%(title)s; price: %(price)s%(url)s'
        channel = msg.args[0]
        region = self.registryValue('region', channel)
        bold = self.registryValue('bold', channel)
        try:
            items = amazon.searchByManufacturer(manufacturer,
                                                product_line=product,
                                                locale=region)
            res = self._genResults(s, attribs, items, url, bold)
            if res:
                irc.reply(utils.commaAndify(res))
                return
        except amazon.AmazonError, e:
            pass
        irc.reply('No items were found by that manufacturer.')
    manufacturer = wrap(manufacturer,
                        [getopts({'url':'', 'electronics':'', 'kitchen':'',
                                  'videogames':'', 'software':'', 'photo':'',
                                  'pc-hardware':'',
                                 }),
                         'text'])

    def amzSnarfer(self, irc, msg, match):
        r"http://www.amazon.com/exec/obidos/(?:tg/detail/-/|ASIN/)([^/]+)"
        if not self.registryValue('linkSnarfer', msg.args[0]):
            return
        match = match.group(1)
        attribs = {'ProductName' : 'title',
                   'Manufacturer' : 'publisher',
                   'Authors' : 'author',
                   'MpaaRating' : 'mpaa',
                   'Media' : 'media',
                   'ReleaseDate' : 'date',
                   'OurPrice' : 'price',
                   'Artists' : 'artist',
                  }
        s = '%(title)s; %(artist)s; %(author)s; %(mpaa)s; %(media)s; '\
            '%(date)s; %(publisher)s; price: %(price)s'
        channel = msg.args[0]
        region = self.registryValue('region', channel)
        bold = self.registryValue('bold', channel)
        try:
            item = amazon.searchByASIN(match, locale=region)
            res = self._genResults(s, attribs, item, False, bold)
            if res:
                res = utils.commaAndify(res)
                res = res.replace('; unknown', '')
                res = res.replace('; price: unknown', '')
                irc.reply(res, prefixName=False)
                return
        except amazon.AmazonError, e:
            pass
        self.log.debug('No item was found with that ASIN.')
    amzSnarfer = urlSnarfer(amzSnarfer)

Class = Amazon

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
