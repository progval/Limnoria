================
Style Guidelines
================

**Note:** Code not following these style guidelines fastidiously is likely
(*very* likely) not to be accepted into the Supybot core.

* Read :pep:`8` (Guido's Style Guide) and know that we use almost all the
  same style guidelines.

* Maximum line length is 79 characters.  78 is a safer bet, though.
  This is **NON-NEGOTIABLE**.  Your code will not be accepted while you are
  violating this guidline.

* Identation is 4 spaces per level.  No tabs.  This also is
  **NON-NEGOTIABLE**.  Your code, again, will *never* be accepted while you
  have literal tabs in it.

* Single quotes are used for all string literals that aren't docstrings.
  They're just easier to type.

* Triple double quotes (``"""``) are always used for docstrings.

* Raw strings (``r''`` or ``r""``) should be used for regular expressions.

* Spaces go around all operators (except around ``=`` in default arguments to
  functions) and after all commas (unless doing so keeps a line within the 79
  character limit).

* Functions calls should look like ``foo(bar(baz(x), y))``.  They should
  not look like ``foo (bar (baz (x), y))``, or like ``foo(bar(baz(x), y) )``
  or like anything else.  I hate extraneous spaces.

* Class names are StudlyCaps.  Method and function names are camelCaps
  (StudlyCaps with an initial lowercase letter).  If variable and attribute
  names can maintain readability without being camelCaps, then they should be
  entirely in lowercase, otherwise they should also use camelCaps.  Plugin
  names are StudlyCaps.

* Imports should always happen at the top of the module, one import per line
  (so if imports need to be added or removed later, it can be done easily).

* Unless absolutely required by some external force, imports should be ordered
  by the string length of the module imported.  I just think it looks
  prettier.

* A blank line should be between all consecutive method declarations in a
  class definition.  Two blank lines should be between all consecutive class
  definitions in a file.  Comments are even better than blank lines for
  separating classes.

* Database filenames should generally begin with the name of the plugin and
  the extension should be 'db'.  plugins.DBHandler does this already.

* Whenever creating a file descriptor or socket, keep a reference around and
  be sure to close it.  There should be no code like this::

    s = urllib2.urlopen('url').read()

  Instead, do this::

    fd = urllib2.urlopen('url')
    try:
        s = fd.read()
    finally:
        fd.close()

  This is to be sure the bot doesn't leak file descriptors.

* All plugin files should include a docstring decsribing what the plugin does.
  This docstring will be returned when the user is configuring the plugin.
  All plugin classes should also include a docstring describing how to do
  things with the plugin; this docstring will be returned when the user
  requests help on a plugin name.

* Method docstrings in classes deriving from callbacks.Privmsg should include
  an argument list as their first line, and after that a blank line followed
  by a longer description of what the command does.  The argument list is used
  by the ``syntax`` command, and the longer description is used by the
  ``help`` command.

* Whenever joining more than two strings, use string interpolation, not
  addition::

    s = x + y + z # Bad.
    s = '%s%s%s' % (x, y, z) # Good.
    s = ''.join([x, y, z]) # Best, but not as general.

  This has to do with efficiency; the intermediate string x+y is made (and
  thus copied) before x+y+z is made, so it's less efficient.  People who use
  string concatenation in a for loop will be swiftly kicked in the head.

* When writing strings that have formatting characters in them, don't use
  anything but ``%s`` unless you absolutely must.  In particular, ``%d`` should never
  be used, it's less general than ``%s`` and serves no useful purpose.  If you got
  the ``%d`` wrong, you'll get an exception that says, "foo instance can't be
  converted to an integer." But if you use ``%s``, you'll get to see your nice
  little foo instance, if it doesn't convert to a string cleanly, and if it
  does convert cleanly, you'll get to see what you expect to see.  Basically,
  ``%d`` just sucks.

* As a corrolary to the above, note that sometimes ``%f`` is used, but on when
  floats need to be formatted, e.g., ``%.2f``.

* Use the log module to its fullest; when you need to print some values to
  debug, use self.log.debug to do so, and leave those statements in the code
  (commented out) so they can later be re-enabled.  Remember that once code is
  buggy, it tends to have more bugs, and you'll probably need those print
  statements again.

* While on the topic of logs, note that we do not use % (i.e., str.__mod__)
  with logged strings; we simple pass the format parameters as additional
  arguments.  The reason is simple: the logging module supports it, and it's
  cleaner (fewer tokens/glyphs) to read.

* While still on the topic of logs, it's also important to pick the
  appropriate log level for given information.

  * DEBUG:  Appropriate to tell a programmer *how* we're doing something
    (i.e., debugging printfs, basically).  If you're trying to figure out why
    your code doesn't work, DEBUG is the new printf -- use that, and leave the
    statements in your code.

  * INFO:   Appropriate to tell a user *what* we're doing, when what we're
    doing isn't important for the user to pay attention to.  A user who likes
    to keep up with things should enjoy watching our logging at the INFO
    level; it shouldn't be too low-level, but it should give enough
    information that it keeps him relatively interested at peak times.

  * WARNING:  Appropriate to tell a user when we're doing something that he
    really ought to pay attention to.  Users should see WARNING and think,
    "Hmm, should I tell the Supybot developers about this?"  Later, he should
    decide not to, but it should give the user a moment to pause and think
    about what's actually happening with his bot.

  * ERROR:    Appropriate to tell a user when something has gone wrong.
    Uncaught exceptions are ERRORs.  Conditions that we absolutely want to
    hear about should be errors.  Things that should *scare* the user should
    be errors.

  * CRITICAL: Not really appropriate.  I can think of no absolutely critical
    issue yet encountered in Supybot; the only possible thing I can imagine is
    to notify the user that the partition on which Supybot is running has
    filled up.  That would be a CRITICAL condition, but it would also be hard
    to log :)


* All plugins should have test cases written for them.  Even if it doesn't
  actually test anything but just exists, it's good to have the test there so
  there's a place to add more tests later (and so we can be sure that all
  plugins are adequately documented; PluginTestCase checks that every command
  has documentation)

* All uses of eval() that expect to get integrated in Supybot must be approved
  by jemfinch, no exceptions.  Chances are, it won't be accepted.  Have you
  looked at utils.safeEval?

* SQL table names should be all-lowercase and include underscores to separate
  words.  This is because SQL itself is case-insensitive.  This doesn't
  change, however the fact that variable/member names should be camel case.

* SQL statements in code should put SQL words in ALL CAPS::

    """SELECT quote FROM quotes ORDER BY random() LIMIT 1"""

  This makes SQL significantly easier to read.

* Common variable names

  - L => an arbitrary list.

  - t => an arbitrary tuple.

  - x => an arbitrary float.

  - s => an arbitrary string.

  - f => an arbitrary function.

  - p => an arbitrary predicate.

  - i,n => an arbitrary integer.

  - cb => an arbitrary callback.

  - db => a database handle.

  - fd => a file-like object.

  - msg => an ircmsgs.IrcMsg object.

  - irc => an irclib.Irc object (or proxy)

  - nick => a string that is an IRC nick.

  - channel => a string that is an IRC channel.

  - hostmask => a string that is a user's IRC prefix.

  When the semantic functionality (that is, the "meaning" of a variable is
  obvious from context), one of these names should be used.  This just makes it
  easier for people reading our code to know what a variable represents
  without scouring the surrounding code.

* Multiple variable assignments should always be surrounded with parentheses
  -- i.e., if you're using the partition function, then your assignment
  statement should look like::

    (good, bad) = partition(p, L)

  The parentheses make it obvious that you're doing a multiple assignment, and
  that's important because I hate reading code and wondering where a variable
  came from.
