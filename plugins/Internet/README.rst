.. _plugin-Internet:

Documentation for the Internet plugin for Supybot
=================================================

Purpose
-------
This plugin provides commands to transform domains into IP addresses and IP addresses to domains.
It can also search WHOIS information and return hexips.

Usage
-----
Provides commands to query DNS, search WHOIS databases,
and convert IPs to hex.

Commands
--------
dns <host|ip>
  Returns the ip of <host> or the reverse DNS hostname of <ip>.

hexip <ip>
  Returns the hexadecimal IP for that IP.

whois <domain>
  Returns WHOIS information on the registration of <domain>.

Configuration
-------------
supybot.plugins.Internet.public
  This config variable defaults to "True", is not network-specific, and is  not channel-specific.

  Determines whether this plugin is publicly visible.

