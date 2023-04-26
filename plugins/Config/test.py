###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2009, James McCoy
# Copyright (c) 2010-2022, Valentin Lorentz
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

import random

from supybot.test import *
import supybot.conf as conf
import supybot.registry as registry

_letters = 'abcdefghijklmnopqrstuvwxyz'
def random_string():
    return ''.join(random.choice(_letters) for _ in range(16))

class Fruit(registry.OnlySomeStrings):
    validStrings = ('Apple', 'Orange')

group = conf.registerGroup(conf.supybot.plugins.Config, 'test')
conf.registerGlobalValue(group, 'fruit',
    Fruit('Orange', '''Must be a fruit'''))


class ConfigTestCase(ChannelPluginTestCase):
    # We add utilities so there's something in supybot.plugins.
    plugins = ('Config', 'User', 'Utilities', 'Web')

    prefix1 = 'somethingElse!user@host1.tld'
    prefix2 = 'EvensomethingElse!user@host2.tld'
    prefix3 = 'Completely!Different@host3.tld__no_testcap__'

    def testGet(self):
        self.assertNotRegexp('config get supybot.reply', r'registry\.Group')
        self.assertResponse('config supybot.protocols.irc.throttleTime', '0.0')

    def testSetOnlysomestrings(self):
        self.assertResponse('config supybot.plugins.Config.test.fruit Apple',
                            'The operation succeeded.')
        self.assertResponse('config supybot.plugins.Config.test.fruit orange',
                            'The operation succeeded.')
        self.assertResponse('config supybot.plugins.Config.test.fruit Tomatoe',
                            "Error: Valid values include 'Apple' and "
                            "'Orange', not 'Tomatoe'.")


    def testList(self):
        self.assertError('config list asldfkj')
        self.assertError('config list supybot.asdfkjsldf')
        self.assertNotError('config list supybot')
        self.assertRegexp('config list supybot.replies', ', #:errorOwner, ')
        self.assertRegexp('config list supybot', r'@plugins.*@replies.*@reply')

    def testListExcludes(self):
        """Checks that 'config list' excludes pseudo-children of
        network-specific and channel-specific variables."""
        self.assertNotError(
            'config channel #zpojfejf supybot.replies.error foo')
        self.assertRegexp('config list supybot.replies.error',
                          "There don't seem to be any values")

    def testHelp(self):
        self.assertError('config help alsdkfj')
        self.assertError('config help supybot.alsdkfj')
        self.assertNotError('config help supybot') # We tell the user to list.
        self.assertNotError('config help supybot.plugins')
        self.assertNotError('config help supybot.replies.success')
        self.assertNotError('config help replies.success')

    def testHelpDoesNotAssertionError(self):
        self.assertNotRegexp('config help ' # Cont'd.
                             'supybot.commands.defaultPlugins.help',
                             'AssertionError')

    def testHelpExhaustively(self):
        L = conf.supybot.getValues(getChildren=True)
        for (name, v) in L:
            self.assertNotError('config help %s' % name)

    def testSearch(self):
        self.assertRegexp(
            'config search chars', 'supybot.reply.whenAddressedBy.chars')
        self.assertNotError('config channel reply.whenAddressedBy.chars @')
        self.assertNotRegexp('config search chars', self.channel)

    def testSearchHelp(self):
        self.assertRegexp(
            'config searchhelp "what prefix characters"',
            'supybot.reply.whenAddressedBy.chars')
        self.assertNotError('config channel reply.whenAddressedBy.chars @')
        self.assertNotRegexp(
            'config searchhelp "what prefix characters"', self.channel)

    def testSearchValues(self):
        self.assertResponse(
            'config searchvalues @@@',
            'There were no matching configuration variables.')
        self.assertNotError('config channel reply.whenAddressedBy.strings @@@')
        self.assertResponse(
            'config searchvalues @@@',
            r'supybot.reply.whenAddressedBy.strings.#test and '
            r'supybot.reply.whenAddressedBy.strings.\:test.#test')

    def testReload(self):
        old_password = 'pjfoizjoifjfoii_old'
        new_password = 'pjfoizjoifjfoii_new'
        with conf.supybot.networks.test.password.context(old_password):
            self.assertResponse('config conf.supybot.networks.test.password',
                                old_password)
            filename = conf.supybot.directories.conf.dirize('Config_testReload.conf')
            registry.close(conf.supybot, filename)

            content = open(filename).read()
            assert old_password in content
            open(filename, 'wt').write(content.replace(old_password,
                                                       new_password))

            registry.open_registry(filename)
            self.assertResponse('config conf.supybot.networks.test.password',
                                new_password)

    def testDefault(self):
        self.assertNotError('config default '
                            'supybot.replies.genericNoCapability')

    def testConfigErrors(self):
        self.assertRegexp('config supybot.replies.', 'not a valid')
        self.assertRegexp('config supybot.repl', 'not a valid')
        self.assertRegexp('config supybot.reply.withNickPrefix 123',
                          'True or False.*, not \'123\'.')
        self.assertRegexp('config supybot.replies foo', 'settable')

    def testReadOnly(self):
        old_plugins_dirs = conf.supybot.directories.plugins()
        try:
            self.assertResponse('config supybot.commands.allowShell', 'True')
            self.assertNotError('config supybot.directories.plugins dir1')
            self.assertNotError('config supybot.commands.allowShell True')
            self.assertResponse('config supybot.commands.allowShell', 'True')
            self.assertResponse('config supybot.directories.plugins', 'dir1')

            self.assertNotError('config supybot.commands.allowShell False')
            self.assertResponse('config supybot.commands.allowShell', 'False')

            self.assertRegexp('config supybot.directories.plugins dir2',
                    'Error.*not writeable')
            self.assertResponse('config supybot.directories.plugins', 'dir1')
            self.assertRegexp('config supybot.commands.allowShell True',
                    'Error.*not writeable')
            self.assertResponse('config supybot.commands.allowShell', 'False')

            self.assertRegexp('config commands.allowShell True',
                    'Error.*not writeable')
            self.assertResponse('config supybot.commands.allowShell', 'False')

            self.assertRegexp('config COMMANDS.ALLOWSHELL True',
                    'Error.*not writeable')
            self.assertResponse('config supybot.commands.allowShell', 'False')
        finally:
            conf.supybot.commands.allowShell.setValue(True)
            conf.supybot.directories.plugins.setValue(old_plugins_dirs)

    def testOpEditable(self):
        var_name = 'testOpEditable' + random_string()
        conf.registerChannelValue(conf.supybot.plugins.Config, var_name,
                registry.Integer(0, 'help'))
        self.assertNotError('register bar passwd', frm=self.prefix3,
                private=True)
        self.assertRegexp('whoami', 'bar', frm=self.prefix3)
        ircdb.users.getUser('bar').addCapability(self.channel + ',op')

        self.assertRegexp('config plugins.Config.%s 1' % var_name,
                '^Completely: Error: ',
                frm=self.prefix3)
        self.assertResponse('config plugins.Config.%s' % var_name,
                'Global: 0; #test @ test: 0')

        self.assertNotRegexp('config channel plugins.Config.%s 1' % var_name,
                '^Completely: Error: ',
                frm=self.prefix3)
        self.assertResponse('config plugins.Config.%s' % var_name,
                'Global: 0; #test @ test: 1')

    def testOpNonEditable(self):
        var_name = 'testOpNonEditable' + random_string()
        conf.registerChannelValue(conf.supybot.plugins.Config, var_name,
                registry.Integer(0, 'help'), opSettable=False)
        self.assertNotError('register bar passwd', frm=self.prefix3,
                private=True)
        self.assertRegexp('whoami', 'bar', frm=self.prefix3)
        ircdb.users.getUser('bar').addCapability(self.channel + ',op')

        self.assertRegexp('config plugins.Config.%s 1' % var_name,
                '^Completely: Error: ',
                frm=self.prefix3)
        self.assertResponse('config plugins.Config.%s' % var_name,
                'Global: 0; #test @ test: 0')

        self.assertRegexp('config channel plugins.Config.%s 1' % var_name,
                '^Completely: Error: ',
                frm=self.prefix3)
        self.assertResponse('config plugins.Config.%s' % var_name,
                'Global: 0; #test @ test: 0')

        self.assertNotRegexp('config channel plugins.Config.%s 1' % var_name,
                '^Completely: Error: ')
        self.assertResponse('config plugins.Config.%s' % var_name,
                'Global: 0; #test @ test: 1')

    def testChannel(self):
        try:
            conf.supybot.reply.whenAddressedBy.strings.get(':test').unregister(self.channel)
            conf.supybot.reply.whenAddressedBy.strings.unregister(':test')
            conf.supybot.reply.whenAddressedBy.strings.unregister(self.channel)
        except:
            pass

        self.assertResponse('config reply.whenAddressedBy.strings ^',
                'The operation succeeded.')
        self.assertResponse('config channel reply.whenAddressedBy.strings @',
                'The operation succeeded.')
        self.assertResponse('config channel reply.whenAddressedBy.strings', '@')
        self.assertNotError('config channel reply.whenAddressedBy.strings $')
        self.assertResponse('config channel #testchan1 reply.whenAddressedBy.strings', '^')
        self.assertResponse('config channel #testchan2 reply.whenAddressedBy.strings', '^')
        self.assertNotError('config channel #testchan1,#testchan2 reply.whenAddressedBy.strings .')
        self.assertResponse('config channel reply.whenAddressedBy.strings', '$')
        self.assertResponse('config channel #testchan1 reply.whenAddressedBy.strings', '.')
        self.assertResponse('config channel #testchan2 reply.whenAddressedBy.strings', '.')

    def testNetwork(self):
        getTestIrc('testnet1')
        getTestIrc('testnet2')
        self.assertResponse('config reply.whenAddressedBy.strings ^',
                'The operation succeeded.')
        self.assertResponse('config network reply.whenAddressedBy.strings @',
                'The operation succeeded.')
        self.assertResponse('config network reply.whenAddressedBy.strings', '@')
        self.assertNotError('config network reply.whenAddressedBy.strings $')
        self.assertResponse('config network testnet1 reply.whenAddressedBy.strings', '^')
        self.assertResponse('config network testnet2 reply.whenAddressedBy.strings', '^')
        self.assertResponse('config network reply.whenAddressedBy.strings', '$')
        self.assertResponse('config network testnet1 reply.whenAddressedBy.strings', '^')
        self.assertResponse('config network testnet2 reply.whenAddressedBy.strings', '^')

        self.assertNotError('config network testnet1 reply.whenAddressedBy.strings =')
        self.assertResponse('config network testnet1 reply.whenAddressedBy.strings', '=')
        self.assertResponse('config network testnet2 reply.whenAddressedBy.strings', '^')

    def testChannelNetwork(self):
        irc = self.irc
        irc1 = getTestIrc('testnet1')
        irc2 = getTestIrc('testnet2')
        irc3 = getTestIrc('testnet3')
        conf.supybot.reply.whenAddressedBy.strings.get('#test')._wasSet = False
        # 1. Set global
        self.assertResponse('config reply.whenAddressedBy.strings ^',
                'The operation succeeded.')

        # 2. Set for current net + #testchan1
        self.assertResponse('config channel #testchan1 reply.whenAddressedBy.strings @',
                'The operation succeeded.')

        # Exact match for #2:
        self.assertResponse('config channel #testchan1 reply.whenAddressedBy.strings', '@')

        # 3: Set for #testchan1 for all nets:
        self.assertNotError('config channel * #testchan1 reply.whenAddressedBy.strings $')

        # Still exact match for #2:
        self.assertResponse('config channel #testchan1 reply.whenAddressedBy.strings', '@')

        # Inherit from *:
        self.assertResponse('config channel testnet1 #testchan1 reply.whenAddressedBy.strings', '$')
        self.assertResponse('config channel testnet2 #testchan1 reply.whenAddressedBy.strings', '$')

        # 4: Set for testnet1 for #testchan1 and #testchan2:
        self.assertNotError('config channel testnet1 #testchan1,#testchan2 reply.whenAddressedBy.strings .')

        # 5: Set for testnet2 for #testchan1:
        self.assertNotError('config channel testnet2 #testchan1 reply.whenAddressedBy.strings :')

        # Inherit from global value (nothing was set of current net or current
        # chan):
        (old_channel, self.channel) = (self.channel, '#iejofjfozifk')
        try:
            self.assertResponse('config channel reply.whenAddressedBy.strings', '^')
        finally:
            self.channel = old_channel

        # Still exact match for #2:
        self.assertResponse('config channel #testchan1 reply.whenAddressedBy.strings', '@')
        self.assertResponse('config channel %s #testchan1 reply.whenAddressedBy.strings' % irc.network, '@')

        # Exact match for #4:
        self.assertResponse('config channel testnet1 #testchan1 reply.whenAddressedBy.strings', '.')
        self.assertResponse('config channel testnet1 #testchan2 reply.whenAddressedBy.strings', '.')

        # Inherit from #5, which set for #testchan1 on all nets
        self.assertResponse('config channel testnet3 #testchan1 reply.whenAddressedBy.strings', ':')

    def testChannelInheritance(self):
        try:
            conf.supybot.reply.whenAddressedBy.strings.get(':test').unregister(self.channel)
            conf.supybot.reply.whenAddressedBy.strings.unregister(':test')
            conf.supybot.reply.whenAddressedBy.strings.unregister(self.channel)
        except:
            pass

        self.assertResponse('config reply.whenAddressedBy.strings ^',
            'The operation succeeded.')
        self.assertResponse('config reply.whenAddressedBy.strings',
            'Global: ^; #test @ test: ^')
        self.assertResponse('config channel reply.whenAddressedBy.strings', '^')
        self.assertTrue(
            conf.supybot.reply.whenAddressedBy.strings._wasSet)
        self.assertFalse(
            conf.supybot.reply.whenAddressedBy.strings.get(self.channel)._wasSet)

        # Parent changes, child follows
        self.assertResponse('config reply.whenAddressedBy.strings @',
            'The operation succeeded.')
        self.assertResponse('config reply.whenAddressedBy.strings',
            'Global: @; #test @ test: @')
        self.assertResponse('config channel reply.whenAddressedBy.strings', '@')
        self.assertTrue(
            conf.supybot.reply.whenAddressedBy.strings._wasSet)
        self.assertFalse(
            conf.supybot.reply.whenAddressedBy.strings.get(self.channel)._wasSet)

        # Child changes, parent keeps its value
        self.assertResponse('config channel reply.whenAddressedBy.strings $',
            'The operation succeeded.')
        self.assertResponse('config reply.whenAddressedBy.strings',
            'Global: @; #test @ test: $')
        self.assertResponse('config channel reply.whenAddressedBy.strings', '$')
        self.assertTrue(
            conf.supybot.reply.whenAddressedBy.strings._wasSet)
        self.assertTrue(
            conf.supybot.reply.whenAddressedBy.strings.get(self.channel)._wasSet)

        # Parent changes, child keeps its value
        self.assertResponse('config reply.whenAddressedBy.strings .',
            'The operation succeeded.')
        self.assertResponse('config reply.whenAddressedBy.strings',
            'Global: .; #test @ test: $')
        self.assertResponse('config channel reply.whenAddressedBy.strings', '$')
        self.assertTrue(
            conf.supybot.reply.whenAddressedBy.strings._wasSet)
        self.assertTrue(
            conf.supybot.reply.whenAddressedBy.strings.get(self.channel)._wasSet)

    def testResetChannel(self):
        try:
            conf.supybot.reply.whenAddressedBy.strings.get(':test').unregister(self.channel)
            conf.supybot.reply.whenAddressedBy.strings.unregister(':test')
            conf.supybot.reply.whenAddressedBy.strings.unregister(self.channel)
        except:
            pass

        self.assertResponse('config reply.whenAddressedBy.strings ^',
            'The operation succeeded.')
        self.assertResponse('config reply.whenAddressedBy.strings',
            'Global: ^; #test @ test: ^')
        self.assertResponse('config channel reply.whenAddressedBy.strings', '^')
        self.assertTrue(
            conf.supybot.reply.whenAddressedBy.strings._wasSet)
        self.assertFalse(
            conf.supybot.reply.whenAddressedBy.strings.get(self.channel)._wasSet)

        # Child changes, parent keeps its value
        self.assertResponse('config channel reply.whenAddressedBy.strings $',
            'The operation succeeded.')
        self.assertResponse('config reply.whenAddressedBy.strings',
            'Global: ^; #test @ test: $')
        self.assertResponse('config channel reply.whenAddressedBy.strings', '$')
        self.assertTrue(
            conf.supybot.reply.whenAddressedBy.strings._wasSet)
        self.assertTrue(
            conf.supybot.reply.whenAddressedBy.strings.get(self.channel)._wasSet)

        # Reset child
        self.assertResponse('config reset channel reply.whenAddressedBy.strings',
            'The operation succeeded.')
        self.assertResponse('config reply.whenAddressedBy.strings',
            'Global: ^; #test @ test: ^')
        self.assertResponse('config channel reply.whenAddressedBy.strings', '^')
        self.assertTrue(
            conf.supybot.reply.whenAddressedBy.strings._wasSet)
        self.assertFalse(
            conf.supybot.reply.whenAddressedBy.strings.get(self.channel)._wasSet)

        # Parent changes, child follows
        self.assertResponse('config reply.whenAddressedBy.strings .',
            'The operation succeeded.')
        self.assertResponse('config reply.whenAddressedBy.strings',
            'Global: .; #test @ test: .')
        self.assertResponse('config channel reply.whenAddressedBy.strings', '.')
        self.assertTrue(
            conf.supybot.reply.whenAddressedBy.strings._wasSet)
        self.assertFalse(
            conf.supybot.reply.whenAddressedBy.strings.get(self.channel)._wasSet)

    def testResetNetwork(self):
        try:
            conf.supybot.reply.whenAddressedBy.strings.unregister(':test')
        except:
            pass

        self.assertResponse('config reply.whenAddressedBy.strings ^',
            'The operation succeeded.')
        self.assertResponse('config reply.whenAddressedBy.strings',
            'Global: ^; #test @ test: ^')
        self.assertResponse('config network reply.whenAddressedBy.strings', '^')
        self.assertTrue(
            conf.supybot.reply.whenAddressedBy.strings._wasSet)
        self.assertFalse(
            conf.supybot.reply.whenAddressedBy.strings.get(':test')._wasSet)

        # Child changes, parent keeps its value
        self.assertResponse('config network reply.whenAddressedBy.strings $',
            'The operation succeeded.')
        self.assertResponse('config reply.whenAddressedBy.strings',
            'Global: ^; #test @ test: $')
        self.assertResponse('config network reply.whenAddressedBy.strings', '$')
        self.assertTrue(
            conf.supybot.reply.whenAddressedBy.strings._wasSet)
        self.assertTrue(
            conf.supybot.reply.whenAddressedBy.strings.get(':test')._wasSet)

        # Reset child
        self.assertResponse('config reset network reply.whenAddressedBy.strings',
            'The operation succeeded.')
        self.assertResponse('config reply.whenAddressedBy.strings',
            'Global: ^; #test @ test: ^')
        self.assertResponse('config network reply.whenAddressedBy.strings', '^')
        self.assertTrue(
            conf.supybot.reply.whenAddressedBy.strings._wasSet)
        self.assertFalse(
            conf.supybot.reply.whenAddressedBy.strings.get(':test')._wasSet)

        # Parent changes, child follows
        self.assertResponse('config reply.whenAddressedBy.strings .',
            'The operation succeeded.')
        self.assertResponse('config reply.whenAddressedBy.strings',
            'Global: .; #test @ test: .')
        self.assertResponse('config network reply.whenAddressedBy.strings', '.')
        self.assertTrue(
            conf.supybot.reply.whenAddressedBy.strings._wasSet)
        self.assertFalse(
            conf.supybot.reply.whenAddressedBy.strings.get(':test')._wasSet)

    def testResetRegexpChannel(self):
        """Specifically tests resetting a Regexp value, as they have an extra
        internal state that needs to be reset; see the comment in plugin.py"""
        self.assertResponse(
            'config plugins.Web.nonSnarfingRegexp',
            'Global:  ; #test @ test:  '
        )
        self.assertResponse(
            'config plugins.Web.nonSnarfingRegexp m/foo/',
            'The operation succeeded.'
        )
        self.assertResponse(
            'config channel plugins.Web.nonSnarfingRegexp m/bar/',
            'The operation succeeded.'
        )
        self.assertResponse(
            'config plugins.Web.nonSnarfingRegexp',
            'Global: m/foo/; #test @ test: m/bar/'
        )
        self.assertResponse(
            'config reset channel plugins.Web.nonSnarfingRegexp',
            'The operation succeeded.'
        )
        self.assertResponse('config plugins.Web.nonSnarfingRegexp',
            'Global: m/foo/; #test @ test: m/foo/'
        )
        self.assertResponse(
            'config plugins.Web.nonSnarfingRegexp ""',
            'The operation succeeded.'
        )
        self.assertResponse(
            'config plugins.Web.nonSnarfingRegexp',
            'Global:  ; #test @ test:  '
        )

    def testResetRegexpNetwork(self):
        """Specifically tests resetting a Regexp value, as they have an extra
        internal state that needs to be reset; see the comment in plugin.py"""
        self.assertResponse(
            'config plugins.Web.nonSnarfingRegexp',
            'Global:  ; #test @ test:  '
        )
        self.assertResponse(
            'config plugins.Web.nonSnarfingRegexp m/foo/',
            'The operation succeeded.'
        )
        self.assertResponse(
            'config network plugins.Web.nonSnarfingRegexp m/bar/',
            'The operation succeeded.'
        )
        self.assertResponse(
            'config plugins.Web.nonSnarfingRegexp',
            'Global: m/foo/; #test @ test: m/bar/'
        )
        self.assertResponse(
            'config reset network plugins.Web.nonSnarfingRegexp',
            'The operation succeeded.'
        )
        self.assertResponse('config plugins.Web.nonSnarfingRegexp',
            'Global: m/foo/; #test @ test: m/foo/'
        )
        self.assertResponse(
            'config plugins.Web.nonSnarfingRegexp ""',
            'The operation succeeded.'
        )
        self.assertResponse(
            'config plugins.Web.nonSnarfingRegexp',
            'Global:  ; #test @ test:  '
        )



# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

