============================
Using Supybot's utils module
============================
Supybot provides a wealth of utilities for plugin writers in the supybot.utils
module, this tutorial describes these utilities and shows you how to use them.

str.py
======
The Format Function
-------------------

The supybot.utils.str module provides a bunch of utility functions for
handling string values. This section contains a quick rundown of all of the
functions available, along with descriptions of the arguments they take. First
and foremost is the format function, which provides a lot of capability in
just one function that uses string-formatting style to accomplish a lot. So
much so that it gets its own section in this tutorial. All other functions
will be in other sections. format takes several arguments - first, the format
string (using the format characters described below), and then after that,
each individual item to be formatted. Do not attempt to use the % operator to
do the formatting because that will fall back on the normal string formatting
operator. The format function uses the following string formatting characters.

* % - literal ``%``
* i - integer
* s - string
* f - float
* r - repr
* b - form of the verb ``to be`` (takes an int)
* h - form of the verb ``to have`` (takes an int)
* L - commaAndify (takes a list of strings or a tuple of ([strings], and))
* p - pluralize (takes a string)
* q - quoted (takes a string)
* n - n items (takes a 2-tuple of (n, item) or a 3-tuple of (n, between, item))
* t - time, formatted (takes an int)
* u - url, wrapped in braces

Here are a few examples to help elaborate on the above descriptions::

  >>> format("Error %q has been reported %n.  For more information, see %u.",
             "AttributeError", (5, "time"), "http://supybot.com")

  'Error "AttributeError" has been reported 5 times.  For more information,
   see <http://supybot.com>.'

  >>> i = 4
  >>> format("There %b %n at this time.  You are only allowed %n at any given
              time", i, (i, "active", "thread"), (5, "active", "thread"))
  'There are 4 active threads at this time.  You are only allowed 5 active
   threads at any given time'

  >>> i = 1
  >>> format("There %b %n at this time.  You are only allowed %n at any given
              time", i, (i, "active", "thread"), (5, "active", "thread"))
   'There is 1 active thread at this time.  You are only allowed 5 active
    threads at any given time'

  >>> ops = ["foo", "bar", "baz"]
  >>> format("The following %n %h the %s capability: %L", (len(ops), "user"),
              len(ops), "op", ops)
  'The following 3 users have the op capability: foo, bar, and baz'

As you can see, you can combine all sorts of combinations of formatting
strings into one. In fact, that was the major motivation behind format. We
have specific functions that you can use individually for each of those
formatting types, but it became much easier just to use special formatting
chars and the format function than concatenating a bunch of strings that were
the result of other utils.str functions.

The Other Functions
-------------------

These are the functions that can't be handled by format. They are sorted in
what I perceive to be the general order of usefulness (and I'm leaving the
ones covered by format for the next section).

* ellipsisify(s, n) - Returns a shortened version of a string. Produces up to
  the first n chars at the nearest word boundary.

  - s: the string to be shortened
  - n: the number of characters to shorten it to

* perlReToPythonRe(s) - Converts a Perl-style regexp (e.g., "/abcd/i" or
  "m/abcd/i") to an actual Python regexp (an re object)

  - s: the regexp string

* perlReToReplacer(s) - converts a perl-style replacement regexp (eg,
  "s/foo/bar/g") to a Python function that performs such a replacement

  - s: the regexp string

* dqrepr(s) - Returns a repr() of s guaranteed to be in double quotes.
  (Double Quote Repr)

  - s: the string to be double-quote repr()'ed

* toBool(s) - Determines whether or not a string means True or False and
  returns the appropriate boolean value. True is any of "true", "on",
  "enable", "enabled", or "1". False is any of "false", "off", "disable",
  "disabled", or "0".

  - s: the string to determine the boolean value for

* rsplit(s, sep=None, maxsplit=-1) - functionally the same as str.split in the
  Python standard library except splitting from the right instead of the left.
  Python 2.4 has str.rsplit (which this function defers to for those versions
  >= 2.4), but Python 2.3 did not.

  - s: the string to be split
  - sep: the separator to split on, defaults to whitespace
  - maxsplit: the maximum number of splits to perform, -1 splits all possible
    splits.

* normalizeWhitespace(s) - reduces all multi-spaces in a string to a single
  space

  - s: the string to normalize

* depluralize(s) - the opposite of pluralize

  - s: the string to depluralize

* unCommaThe(s) - Takes a string of the form "foo, the" and turns it into "the
  foo"

  - s: string, the

* distance(s, t) - computes the levenshtein distance (or "edit distance")
  between two strings

  - s: the first string
  - t: the second string

* soundex(s, length=4) - computes the soundex for a given string

  - s: the string to compute the soundex for
  - length: the length of the soundex to generate

* matchCase(s1, s2) - Matches the case of the first string in the second
  string.

  - s1: the first string
  - s2: the string which will be made to match the case of the first

The Commands Format Already Covers
----------------------------------

These commands aren't necessary because you can achieve them more easily by
using the format command, but they exist if you decide you want to use them
anyway though it is greatly discouraged for general use.

* commaAndify(seq, comma=",", And="and") - transforms a list of items into a
  comma separated list with an "and" preceding the last element. For example,
  ["foo", "bar", "baz"] becomes "foo, bar, and baz". Is smart enough to
  convert two-element lists to just "item1 and item2" as well.

  - seq: the sequence of items (don't have to be strings, but need to be
    'str()'-able)
  - comma: the character to use to separate the list
  - And: the word to use before the last element

* pluralize(s) - Returns the plural of a string. Put any exceptions to the
  general English rules of pluralization in the plurals dictionary in
  supybot.utils.str.

  - s: the string to pluralize

* nItems(n, item, between=None) - returns a string that describes a given
  number of an item (with any string between the actual number and the item
  itself), handles pluralization with the pluralize function above. Note that
  the arguments here are in a different order since between is optional.

  - n: the number of items
  - item: the type of item
  - between: the optional string that goes between the number and the type of
    item

* quoted(s) - Returns the string surrounded by double-quotes.

  - s: the string to quote

* be(i) - Returns the proper form of the verb "to be" based on the number
  provided (be(1) is "is", be(anything else) is "are")

  - i: the number of things that "be"

* has(i) - Returns the proper form of the verb "to have" based on the number
  provided (has(1) is "has", has(anything else) is "have")

  - i: the number of things that "has"

structures.py
=============
Intro
-----

This module provides a number of useful data structures that aren't found in
the standard Python library. For the most part they were created as needed for
the bot and plugins themselves, but they were created in such a way as to be
of general use for anyone who needs a data structure that performs a like
duty. As usual in this document, I'll try and order these in order of
usefulness, starting with the most useful.

The queue classes
-----------------

The structures module provides two general-purpose queue classes for you to
use. The "queue" class is a robust full-featured queue that scales up to
larger sized queues. The "smallqueue" class is for queues that will contain
fewer (less than 1000 or so) items. Both offer the same common interface,
which consists of:

* a constructor which will optionally accept a sequence to start the queue off
  with
* enqueue(item) - adds an item to the back of the queue
* dequeue() - removes (and returns) the item from the front of the queue
* peek() - returns the item from the front of the queue without removing it
* reset() - empties the queue entirely

In addition to these general-use queue classes, there are two other more
specialized queue classes as well. The first is the "TimeoutQueue" which holds
a queue of items until they reach a certain age and then they are removed from
the queue. It features the following:

* TimeoutQueue(timeout, queue=None) - you must specify the timeout (in
  seconds) in the constructor. Note that you can also optionally pass it a
  queue which uses any implementation you wish to use whether it be one of the
  above (queue or smallqueue) or if it's some custom queue you create that
  implements the same interface. If you don't pass it a queue instance to use,
  it will build its own using smallqueue.

  - reset(), enqueue(item), dequeue() - all same as above queue classes
  - setTimeout(secs) - allows you to change the timeout value

And for the final queue class, there's the "MaxLengthQueue" class. As you may
have guessed, it's a queue that is capped at a certain specified length. It
features the following:

* MaxLengthQueue(length, seq=()) - the constructor naturally requires that you
  set the max length and it allows you to optionally pass in a sequence to be
  used as the starting queue. The underlying implementation is actually the
  queue from before.

  - enqueue(item) - adds an item onto the back of the queue and if it would
    push it over the max length, it dequeues the item on the front (it does
    not return this item to you)
  - all the standard methods from the queue class are inherited for this class

The Other Structures
--------------------

The most useful of the other structures is actually very similar to the
"MaxLengthQueue". It's the "RingBuffer", which is essentially a MaxLengthQueue
which fills up to its maximum size and then circularly replaces the old
contents as new entries are added instead of dequeuing.  It features the
following:

* RingBuffer(size, seq=()) - as with the MaxLengthQueue you specify the size
  of the RingBuffer and optionally give it a sequence.

  - append(item) - adds item to the end of the buffer, pushing out an item
    from the front if necessary
  - reset() - empties out the buffer entirely
  - resize(i) - shrinks/expands the RingBuffer to the size provided
  - extend(seq) - append the items from the provided sequence onto the end of
    the RingBuffer

The next data structure is the TwoWayDictionary, which as the name implies is
a dictionary in which key-value pairs have mappings going both directions. It
features the following:

* TwoWayDictionary(seq=(), \**kwargs) - Takes an optional sequence of (key,
  value) pairs as well as any key=value pairs specified in the constructor as
  initial values for the two-way dict.

  - other than that, no extra features that a normal Python dict doesn't
    already offer with the exception that any (key, val) pair added to the
    dict is also added as (val, key) as well, so the mapping goes both ways.
    Elements are still accessed the same way you always do with Python
    'dict's.

There is also a MultiSet class available, but it's very unlikely that it will
serve your purpose, so I won't go into it here. The curious coder can go check
the source and see what it's all about if they wish (it's only used once in our
code, in the Relay plugin).

web.py
======
The web portion of Supybot's utils module is mainly used for retrieving data
from websites but it also has some utility functions pertaining to HTML and
email text as well. The functions in web are listed below, once again in order
of usefulness.

* getUrl(url, size=None, headers=None) - gets the data at the URL provided and
  returns it as one large string

  - url: the location of the data to be retrieved or a urllib2.Request object
    to be used in the retrieval
  - size: the maximum number of bytes to retrieve, defaults to None, meaning
    that it is to try to retrieve all data
  - headers: a dictionary mapping header types to header data

* getUrlFd(url, headers=None) - returns a file-like object for a url

  - url: the location of the data to be retrieved or a urllib2.Request object
    to be used in the retrieval
  - headers: a dictionary mapping header types to header data

* htmlToText(s, tagReplace=" ") - strips out all tags in a string of HTML,
  replacing them with the specified character

  - s: the HTML text to strip the tags out of
  - tagReplace: the string to replace tags with

* strError(e) - pretty-printer for web exceptions, returns a descriptive
  string given a web-related exception

  - e: the exception to pretty-print

* mungeEmail(s) - a naive e-mail obfuscation function, replaces "@" with "AT"
  and "." with "DOT"

  - s: the e-mail address to obfuscate

* getDomain(url) - returns the domain of a URL
  - url: the URL in question

The Best of the Rest
====================
Intro
-----

Rather than document each of the remaining portions of the supybot.utils
module, I've elected to just pick out the choice bits from specific parts and
document those instead. Here they are, broken out by module name.

supybot.utils.file - file utilities
-----------------------------------

* touch(filename) - updates the access time of a file by opening it for
  writing and immediately closing it

* mktemp(suffix="") - creates a decent random string, suitable for a temporary
  filename with the given suffix, if provided

* the AtomicFile class - used for files that need to be atomically written,
  i.e., if there's a failure the original file remains unmodified. For more
  info consult file.py in src/utils

supybot.utils.gen - general utilities
-------------------------------------

* timeElapsed(elapsed, [lots of optional args]) - given the number of seconds
  elapsed, returns a string with the English description of the amount of time
  passed, consult gen.py in src/utils for the exact argument list and
  documentation if you feel you could use this function.

* exnToString(e) - improved exception-to-string function. Provides nicer
  output than a simple str(e).

* InsensitivePreservingDict class - a dict class that is case-insensitive when
  accessing keys

supybot.utils.iter - iterable utilities
---------------------------------------

* len(iterable) - returns the length of a given iterable

* groupby(key, iterable) - equivalent to the itertools.groupby function
  available as of Python 2.4. Provided for backwards compatibility.

* any(p, iterable) - Returns true if any element in the iterable satisfies the
  predicate p

* all(p, iterable) - Returns true if all elements in the iterable satisfy the
  predicate p

* choice(iterable) - Returns a random element from the iterable
