"""A lexical analyzer class for simple shell-like syntaxes."""

# Module and documentation by Eric S. Raymond, 21 Dec 1998
# Input stacking and error message cleanup added by ESR, March 2000
# push_source() and pop_source() made explicit by ESR, January 2001.

import os.path
import sys

from .utils import minisix

__all__ = ["shlex"]

class shlex:
    "A lexical analyzer class for simple shell-like syntaxes."
    def __init__(self, instream=None, infile=None):
        if instream is not None:
            self.instream = instream
            self.infile = infile
        else:
            self.instream = sys.stdin
            self.infile = None
        self.commenters = '#'
        self.whitespace = ' \t\r\n'
        self.separators = self.whitespace
        self.quotes = '\'"'
        self.state = ' '
        self.pushback = []
        self.lineno = 1
        self.debug = 0
        self.token = ''
        self.backslash = False
        self.filestack = []
        self.source = None
        if self.debug:
            print('shlex: reading from %s, line %d' \
                  % (self.instream, self.lineno))

    def push_token(self, tok):
        "Push a token onto the stack popped by the get_token method"
        if self.debug >= 1:
            print("shlex: pushing token " + repr(tok))
        self.pushback = [tok] + self.pushback

    def push_source(self, newstream, newfile=None):
        "Push an input source onto the lexer's input source stack."
        self.filestack.insert(0, (self.infile, self.instream, self.lineno))
        self.infile = newfile
        self.instream = newstream
        self.lineno = 1
        if self.debug:
            if newfile is not None:
                print('shlex: pushing to file %s' % (self.infile,))
            else:
                print('shlex: pushing to stream %s' % (self.instream,))

    def pop_source(self):
        "Pop the input source stack."
        self.instream.close()
        (self.infile, self.instream, self.lineno) = self.filestack[0]
        self.filestack = self.filestack[1:]
        if self.debug:
            print('shlex: popping to %s, line %d' \
                  % (self.instream, self.lineno))
        self.state = ' '

    def get_token(self):
        "Get a token from the input stream (or from stack if it's nonempty)"
        if self.pushback:
            tok = self.pushback[0]
            self.pushback = self.pushback[1:]
            if self.debug >= 1:
                print("shlex: popping token " + repr(tok))
            return tok
        # No pushback.  Get a token.
        raw = self.read_token()
        # Handle inclusions
        while raw == self.source:
            spec = self.sourcehook(self.read_token())
            if spec:
                (newfile, newstream) = spec
                self.push_source(newstream, newfile)
            raw = self.get_token()
        # Maybe we got EOF instead?
        while raw == "":
            if len(self.filestack) == 0:
                return ""
            else:
                self.pop_source()
                raw = self.get_token()
         # Neither inclusion nor EOF
        if self.debug >= 1:
            if raw:
                print("shlex: token=" + repr(raw))
            else:
                print("shlex: token=EOF")
        return raw

    def read_token(self):
        "Read a token from the input stream (no pushback or inclusions)"
        while True:
            nextchar = self.instream.read(1)
            if nextchar == '\n':
                self.lineno = self.lineno + 1
            if self.debug >= 3:
                print("shlex: in state", repr(self.state), \
                      "I see character:", repr(nextchar))
            if self.state is None:
                self.token = ''        # past end of file
                break
            elif self.state == ' ':
                if not nextchar:
                    self.state = None  # end of file
                    break
                elif nextchar in self.whitespace:
                    if self.debug >= 2:
                        print("shlex: I see whitespace in whitespace state")
                    if self.token:
                        break   # emit current token
                    else:
                        continue
                elif nextchar in self.commenters:
                    self.instream.readline()
                    self.lineno = self.lineno + 1
                elif nextchar not in self.separators:
                    self.token = nextchar
                    self.state = 'a'
                elif nextchar in self.quotes:
                    self.token = nextchar
                    self.state = nextchar
                else:
                    self.token = nextchar
                    if self.token:
                        break   # emit current token
                    else:
                        continue
            elif self.state in self.quotes:
                self.token = self.token + nextchar
                if nextchar == '\\':
                    if self.backslash:
                        self.backslash = False
                    else:
                        self.backslash = True
                else:
                    if not self.backslash and nextchar == self.state:
                        self.state = ' '
                        break
                    elif self.backslash:
                        self.backslash = False
                    elif not nextchar:      # end of file
                        if self.debug >= 2:
                            print("shlex: I see EOF in quotes state")
                        # XXX what error should be raised here?
                        raise ValueError("No closing quotation")
            elif self.state == 'a':
                if not nextchar:
                    self.state = None   # end of file
                    break
                elif nextchar in self.whitespace:
                    if self.debug >= 2:
                        print("shlex: I see whitespace in word state")
                    self.state = ' '
                    if self.token:
                        break   # emit current token
                    else:
                        continue
                elif nextchar in self.commenters:
                    self.instream.readline()
                    self.lineno = self.lineno + 1
                elif nextchar not in self.separators or nextchar in self.quotes:
                    self.token = self.token + nextchar
                else:
                    self.pushback = [nextchar] + self.pushback
                    if self.debug >= 2:
                        print("shlex: I see punctuation in word state")
                    self.state = ' '
                    if self.token:
                        break   # emit current token
                    else:
                        continue
        result = self.token
        self.token = ''
        if self.debug > 1:
            if result:
                print("shlex: raw token=" + repr(result))
            else:
                print("shlex: raw token=EOF")
        return result

    def sourcehook(self, newfile):
        "Hook called on a filename to be sourced."
        if newfile[0] == '"':
            newfile = newfile[1:-1]
        # This implements cpp-like semantics for relative-path inclusion.
        if isinstance(self.infile, minisix.string_types) and not os.path.isabs(newfile):
            newfile = os.path.join(os.path.dirname(self.infile), newfile)
        return (newfile, open(newfile, "r"))

    def error_leader(self, infile=None, lineno=None):
        "Emit a C-compiler-like, Emacs-friendly error-message leader."
        if infile is None:
            infile = self.infile
        if lineno is None:
            lineno = self.lineno
        return "\"%s\", line %d: " % (infile, lineno)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        lexer = shlex()
    else:
        file = sys.argv[1]
        with open(file) as fd:
            lexer = shlex(fd, file)
    while True:
        tt = lexer.get_token()
        if tt:
            print("Token: " + repr(tt))
        else:
            break
