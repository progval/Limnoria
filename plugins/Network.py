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
Various network-related commands.
"""

__revision__ = "$Id$"

import plugins

import sets
import socket
import telnetlib

import utils
import ircutils
import privmsgs
import callbacks


class Network(callbacks.Privmsg):
    threaded = True
    def dns(self, irc, msg, args):
        """<host|ip>

        Returns the ip of <host> or the reverse DNS hostname of <ip>.
        """
        host = privmsgs.getArgs(args)
        if utils.isIP(host):
            hostname = socket.getfqdn(host)
            if hostname == host:
                irc.reply('Host not found.')
            else:
                irc.reply(hostname)
        else:
            try:
                ip = socket.gethostbyname(host)
                if ip == '64.94.110.11': # Verisign sucks!
                    irc.reply('Host not found.')
                else:
                    irc.reply(ip)
            except socket.error:
                irc.reply('Host not found.')

    _tlds = sets.Set(['com', 'net', 'edu'])
    def whois(self, irc, msg, args):
        """<domain>

        Returns WHOIS information on the registration of <domain>.  <domain>
        must be in tlds .com, .net, or .edu.
        """
        domain = privmsgs.getArgs(args)
        if '.' not in domain or domain.split('.')[-1] not in self._tlds:
            irc.error('<domain> must be in .com, .net, or .edu.')
            return
        elif len(domain.split('.')) != 2:
            irc.error('<domain> must be a domain, not a hostname.')
            return
        t = telnetlib.Telnet('rs.internic.net', 43)
        t.write(domain)
        t.write('\n')
        s = t.read_all()
        for line in s.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith('Registrar'):
                registrar = line.split()[-1].capitalize()
            elif line.startswith('Referral'):
                url = line.split()[-1]
            elif line.startswith('Updated'):
                updated = line.split()[-1]
            elif line.startswith('Creation'):
                created = line.split()[-1]
            elif line.startswith('Expiration'):
                expires = line.split()[-1]
            elif line.startswith('Status'):
                status = line.split()[-1].lower()
        try:
            s = '%s <%s> is %s; registered %s, updated %s, expires %s.' % \
                (domain, url, status, created, updated, expires)
            irc.reply(s)
        except NameError, e:
            irc.error('I couldn\'t find such a domain.')
        

Class = Network

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
