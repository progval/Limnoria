# This module is part of the Pyndex project and is Copyright 2003 Amir
# Bakhtiar (amir@divmod.org). This is free software; you can redistribute
# it and/or modify it under the terms of version 2.1 of the GNU Lesser
# General Public License as published by the Free Software Foundation.

import string

class Splitter(object):
    """Split plain text into words" utility class
    Adapted from David Mertz's article in IBM developerWorks
    Needs work to handle international characters, etc"""

##    __slots__ = ['stemmer', 'porter', 'stopwording', 'word_only', 'nonword',
##                 'nondigits', 'alpha', 'ident', 'tokens', 'position']
    

    stopWords = {'and': 1, 'be': 1, 'to': 1, 'that': 1, 'into': 1,
                 'it': 1, 'but': 1, 'as': 1, 'are': 1, 'they': 1,
                 'in': 1, 'not': 1, 'such': 1, 'with': 1, 'by': 1,
                 'is': 1, 'if': 1, 'a': 1, 'on': 1, 'for': 1,
                 'no': 1, 'these': 1, 'of': 1, 'there': 1,
                 'this': 1, 'will': 1, 'their': 1, 's': 1, 't': 1,
                 'then': 1, 'the': 1, 'was': 1, 'or': 1, 'at': 1}

    yes = string.lowercase + string.digits + '' # throw in any extras
    nonword = ''
    for i in range(0,255):
        if chr(i) not in yes:
            nonword += chr(i)

    word_only = string.maketrans(nonword, " " * len(nonword))
    
    nondigits = string.join(map(chr, range(0,48)) + map(chr, range(58,255)), '')
    alpha = string.join(map(chr, range(65,91)) + map(chr, range(97,123)), '')
    ident = string.join(map(chr, range(256)), '')

    def close(self):
        # Lupy support
        pass

    def tokenStream(self, fieldName, file, casesensitive=False):
        """Split text/plain string into a list of words
        """
        self.tokens = self.split(file.read())
        self.position = 0
        return self

    def next(self):
        if self.position >= len(self.tokens):
            return None
        res = Token(self.tokens[self.position])
        self.position += 1
        return res
     
    def split(self, text, casesensitive=0):
        # Speedup trick: attributes into local scope
        word_only = self.word_only
        ident = self.ident
        alpha = self.alpha
        nondigits = self.nondigits

        # Let's adjust case if not case-sensitive
        if not casesensitive: text = string.lower(text)

        # Split the raw text
        allwords = text.translate(word_only).split()  # Let's strip funny byte values

        # Finally, let's skip some words not worth indexing
        words = []
        for word in allwords:
            if len(word) > 32: continue         # too long (probably gibberish)

            # Identify common patterns in non-word data (binary, UU/MIME, etc)
            num_nonalpha = len(word.translate(ident, alpha))
            numdigits    = len(word.translate(ident, nondigits))
            if numdigits > len(word)-2:         # almost all digits
                if numdigits > 5:               # too many digits is gibberish
                    continue                    # a moderate number is year/zipcode/etc
            elif num_nonalpha*2 > len(word):    # too much scattered nonalpha = gibberish
                continue

            word = word.translate(word_only)    # Let's strip funny byte values
            subwords = word.split()             # maybe embedded non-alphanumeric
            for subword in subwords:            # ...so we might have subwords
                if len(subword) <= 1: continue  # too short a subword
                words.append(subword)
            
        return words                

class Token:
    def __init__(self, trmText):
        self.trmText = trmText

    def termText(self):
        return self.trmText

