#!/usr/bin/env python

from fix import *

import xml.sax.handler

import ircdb

class UsersHandler(xml.sax.handler.ContentHandler):
    def startElement(self, name, attrs):
        if name == 'user':
            self.u = ircdb.IrcUser(ignore=attrs.getValue('ignore'),
                                   password=attrs.getValue('password'),
                                   auth=(float(attrs.getValue('authtime')),
                                         attrs.getValue('authmask')))
            self.name = attrs.getValue('name')
            self.startTag = name

    def characters(self, content):
        self.chars += content

    def endElement(self, name):
        assert name == self.startTag
        self.startTag = ''
        if name == 'capability':
            self.u.addCapability(self.chars.strip())
        elif name == 'hostmask':
            self.u.addHostmask(self.chars.strip())
        elif name == 'user':
            #ircdb.users.setUser(self.name, self.u)
            self.users[self.name] = self.u
            self.name = ''
            self.u = None
        self.chars = ''
