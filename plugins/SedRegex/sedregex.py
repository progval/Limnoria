#!/usr/bin/env python3

import functools
import re

@functools.lru_cache
def makeSedRegex(delimiters=''):
    delimiters = delimiters or r"^\w\s"

    return re.compile(
        # This part matches an optional nick followed by ":" or ",", used to direct replacement
        # at a particular user.
        r"^(?:(?P<nick>.+?)[:,] )?"

        # Match and save the delimiter (any one symbol) as a named group
        fr"s(?P<delim>[{delimiters}])"

        # Match the pattern to replace, which can be any string up to the first instance of the
        # delimiter
        r"(?P<pattern>(?:(?!(?P=delim)).)*)(?P=delim)"

        # Ditto with the replacement
        r"(?P<replacement>(?:(?!(?P=delim)).)*)"

        # Optional final delimiter plus flags at the end
        r"(?:(?P=delim)(?P<flags>[a-z]*))?"
    )

if __name__ == '__main__':
    print("This is the full regex used by the plugin; paste it into your favourite regex tester "
          "for debugging:")
    print(makeSedRegex())
