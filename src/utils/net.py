###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2011, 2013, James McCoy
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
Simple utility modules.
"""

import re
import ssl
import socket
import hashlib
import contextlib

from .web import _ipAddr, _domain

emailRe = re.compile(r"^\S+@(%s|%s)$" % (_domain, _ipAddr), re.I)

def getAddressFromHostname(host, port=None, attempt=0):
    addrinfo = socket.getaddrinfo(host, port)
    addresses = []
    for (family, socktype, proto, canonname, sockaddr) in addrinfo:
        if sockaddr[0] not in addresses:
            addresses.append(sockaddr[0])
    return addresses[attempt % len(addresses)]

def getSocket(host, port=None, socks_proxy=None, vhost=None, vhostv6=None):
    """Returns a socket of the correct AF_INET type (v4 or v6) in order to
    communicate with host.
    """
    if not socks_proxy:
        addrinfo = socket.getaddrinfo(host, port)
        host = addrinfo[0][4][0]
    if socks_proxy:
        import socks
        s = socks.socksocket()
        hostname, port = socks_proxy.rsplit(':', 1)
        s.setproxy(socks.PROXY_TYPE_SOCKS5, hostname, int(port),
                rdns=True)
        return s
    if isIPV4(host):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if vhost:
            s.bind((vhost, 0))
        return s
    elif isIPV6(host):
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        if vhostv6:
            s.bind((vhostv6, 0))
        return s
    else:
        raise socket.error('Something wonky happened.')

def isSocketAddress(s):
    if ':' in s:
        host, port = s.rsplit(':', 1)
        try:
            int(port)
            sock = getSocket(host, port)
            return True
        except (ValueError, socket.error):
            pass
    return False

def isIP(s):
    """Returns whether or not a given string is an IP address.

    >>> isIP('255.255.255.255')
    1

    >>> isIP('::1')
    0
    """
    return isIPV4(s) or isIPV6(s)

def isIPV4(s):
    """Returns whether or not a given string is an IPV4 address.

    >>> isIPV4('255.255.255.255')
    1

    >>> isIPV4('abc.abc.abc.abc')
    0
    """
    if set(s) - set('0123456789.'):
        # inet_aton ignores trailing data after the first valid IP address
        return False
    try:
        return bool(socket.inet_aton(str(s)))
    except socket.error:
        return False

def bruteIsIPV6(s):
    if s.count('::') <= 1:
        L = s.split(':')
        if len(L) <= 8:
            for x in L:
                if x:
                    try:
                        int(x, 16)
                    except ValueError:
                        return False
            return True
    return False

def isIPV6(s):
    """Returns whether or not a given string is an IPV6 address."""
    try:
        if hasattr(socket, 'inet_pton'):
            return bool(socket.inet_pton(socket.AF_INET6, s))
        else:
            return bruteIsIPV6(s)
    except socket.error:
        try:
            socket.inet_pton(socket.AF_INET6, '::')
        except socket.error:
            # We gotta fake it.
            return bruteIsIPV6(s)
        return False


normalize_fingerprint = lambda fp: fp.replace(':', '').lower()

FINGERPRINT_ALGORITHMS = ('md5', 'sha1', 'sha224', 'sha256', 'sha384',
        'sha512')
def check_certificate_fingerprint(conn, trusted_fingerprints):
    trusted_fingerprints = set(normalize_fingerprint(fp)
            for fp in trusted_fingerprints)
    cert = conn.getpeercert(binary_form=True)
    for algorithm in FINGERPRINT_ALGORITHMS:
        h = hashlib.new(algorithm)
        h.update(cert)
        if h.hexdigest() in trusted_fingerprints:
            return
    raise ssl.CertificateError('No matching fingerprint.')

@contextlib.contextmanager
def _prefix_ssl_error(prefix):
    try:
        yield
    except ssl.SSLError as e:
        raise ssl.SSLError(
            e.args[0], '%s failed: %s' % (prefix, e.args[1]), *e.args[2:]) \
            from None

def ssl_wrap_socket(conn, hostname, logger, certfile=None,
        trusted_fingerprints=None, verify=True, ca_file=None,
        **kwargs):
    with _prefix_ssl_error('creating SSL context'):
        context = ssl.create_default_context(**kwargs)

    if ca_file:
        with _prefix_ssl_error('loading CA certificate'):
            context.load_verify_locations(cafile=ca_file)
    elif trusted_fingerprints or not verify:
        # Do not use Certification Authorities
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    if certfile:
        with _prefix_ssl_error('loading client certfile'):
            context.load_cert_chain(certfile)

    with _prefix_ssl_error('establishing TLS connection'):
        conn = context.wrap_socket(conn, server_hostname=hostname)

    if trusted_fingerprints:
        check_certificate_fingerprint(conn, trusted_fingerprints)

    return conn

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
