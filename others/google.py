"""Python wrapper for Google web APIs

This module allows you to access Google's web APIs through SOAP,
to do things like search Google and get the results programmatically.
Described here:
  http://www.google.com/apis/

You need a Google-provided license key to use these services.
Follow the link above to get one.  These functions will look in
several places (in this order) for the license key:
- the "license_key" argument of each function
- the module-level LICENSE_KEY variable (call setLicense once to set it)
- an environment variable called GOOGLE_LICENSE_KEY
- a file called ".googlekey" in the current directory
- a file called "googlekey.txt" in the current directory
- a file called ".googlekey" in your home directory
- a file called "googlekey.txt" in your home directory
- a file called ".googlekey" in the same directory as google.py
- a file called "googlekey.txt" in the same directory as google.py

Sample usage:
>>> import google
>>> google.setLicense('...') # must get your own key!
>>> data = google.doGoogleSearch('python')
>>> data.meta.searchTime
0.043221000000000002
>>> data.results[0].URL
'http://www.python.org/'
>>> data.results[0].title
'<b>Python</b> Language Website'

See documentation of SearchResultsMetaData and SearchResult classes
for other available attributes.
"""

__author__ = "Mark Pilgrim (f8dy@diveintomark.org)"
__version__ = "0.5.2"
__cvsversion__ = "$Revision$"[11:-2]
__date__ = "$Date$"[7:-2]
__copyright__ = "Copyright (c) 2002 Mark Pilgrim"
__license__ = "Python"
__credits__ = """David Ascher, for the install script
Erik Max Francis, for the command line interface
Michael Twomey, for HTTP proxy support"""

import SOAP
import os, sys, getopt

LICENSE_KEY = None
HTTP_PROXY = None

# don't touch the rest of these constants
class NoLicenseKey(Exception): pass
_url = 'http://api.google.com/search/beta2'
_namespace = 'urn:GoogleSearch'
_false = SOAP.booleanType(0)
_true = SOAP.booleanType(1)
_googlefile1 = ".googlekey"
_googlefile2 = "googlekey.txt"
_licenseLocations = (
    (lambda key: key, 'passed to the function in license_key variable'),
    (lambda key: LICENSE_KEY, 'module-level LICENSE_KEY variable (call setLicense to set it)'),
    (lambda key: os.environ.get('GOOGLE_LICENSE_KEY', None), 'an environment variable called GOOGLE_LICENSE_KEY'),
    (lambda key: _contentsOf(os.getcwd(), _googlefile1), '%s in the current directory' % _googlefile1),
    (lambda key: _contentsOf(os.getcwd(), _googlefile2), '%s in the current directory' % _googlefile2),
    (lambda key: _contentsOf(os.environ.get('HOME', ''), _googlefile1), '%s in your home directory' % _googlefile1),
    (lambda key: _contentsOf(os.environ.get('HOME', ''), _googlefile2), '%s in your home directory' % _googlefile2),
    (lambda key: _contentsOf(_getScriptDir(), _googlefile1), '%s in the google.py directory' % _googlefile1),
    (lambda key: _contentsOf(_getScriptDir(), _googlefile2), '%s in the google.py directory' % _googlefile2)
    )

## administrative functions
def version():
    print """PyGoogle %(__version__)s
%(__copyright__)s
released %(__date__)s

Thanks to:
%(__credits__)s""" % globals()

def usage():
    program = os.path.basename(sys.argv[0])
    print """Usage: %(program)s [options] [querytype] query

options:
  -k, --key= <license key> Google license key (see important note below)
  -1, -l, --lucky          show only first hit
  -m, --meta               show meta information
  -r, --reverse            show results in reverse order
  -x, --proxy= <url>       use HTTP proxy
  -h, --help               print this help
  -v, --version            print version and copyright information
  -t, --test               run test queries

querytype:
  -s, --search= <query>    search (default)
  -c, --cache= <url>       retrieve cached page
  -p, --spelling= <word>   check spelling

IMPORTANT NOTE: all Google functions require a valid license key;
visit http://www.google.com/apis/ to get one.  %(program)s will look in
these places (in order) and use the first license key it finds:
  * the key specified on the command line""" % vars()
    for get, location in _licenseLocations[2:]:
        print "  *", location

## utility functions
def setLicense(license_key):
    """set license key"""
    global LICENSE_KEY
    LICENSE_KEY = license_key

def getLicense(license_key = None):
    """get license key

    license key can come from any number of locations;
    see module docs for search order"""
    for get, location in _licenseLocations:
        rc = get(license_key)
        if rc: return rc
    usage()
    raise NoLicenseKey, 'get a license key at http://www.google.com/apis/'

def setProxy(http_proxy):
    """set HTTP proxy"""
    global HTTP_PROXY
    HTTP_PROXY = http_proxy

def getProxy(http_proxy = None):
    """get HTTP proxy"""
    return http_proxy or HTTP_PROXY

def _contentsOf(dirname, filename):
    filename = os.path.join(dirname, filename)
    if not os.path.exists(filename): return None
    fsock = open(filename)
    contents = fsock.read()
    fsock.close()
    return contents

def _getScriptDir():
    if __name__ == '__main__':
        return os.path.abspath(os.path.dirname(sys.argv[0]))
    else:
        return os.path.abspath(os.path.dirname(sys.modules[__name__].__file__))

def _marshalBoolean(value):
    if value:
        return _true
    else:
        return _false

## output formatters
def makeFormatter(outputFormat):
    classname = "%sOutputFormatter" % outputFormat.capitalize()
    return globals()[classname]()

def output(results, params):
    formatter = makeFormatter(params.get("outputFormat", "text"))
    outputmethod = getattr(formatter, params["func"])
    outputmethod(results, params)

class OutputFormatter:
    def boil(self, data):
        if type(data) == type(u""):
            return data.encode("ISO-8859-1", "replace")
        else:
            return data

class TextOutputFormatter(OutputFormatter):
    def common(self, data, params):
        if params.get("showMeta", 0):
            meta = data.meta
            for category in meta.directoryCategories:
                print "directoryCategory: %s" % self.boil(category["fullViewableName"])
            for attr in [node for node in dir(meta) if node <> "directoryCategories" and node[:2] <> '__']:
                print "%s:" % attr, self.boil(getattr(meta, attr))

    def doGoogleSearch(self, data, params):
        results = data.results
        if params.get("feelingLucky", 0):
            results = results[:1]
        if params.get("reverseOrder", 0):
            results.reverse()
        for result in results:
            for attr in dir(result):
                if attr == "directoryCategory":
                    print "directoryCategory:", self.boil(result.directoryCategory["fullViewableName"])
                elif attr[:2] <> '__':
                    print "%s:" % attr, self.boil(getattr(result, attr))
            print
        self.common(data, params)

    def doGetCachedPage(self, data, params):
        print data
        self.common(data, params)

    doSpellingSuggestion = doGetCachedPage

## search results classes
class _SearchBase:
    def __init__(self, params):
        for k, v in params.items():
            if isinstance(v, SOAP.structType):
                v = v._asdict
            try:
                if isinstance(v[0], SOAP.structType):
                    v = [node._asdict for node in v]
            except:
                pass
            self.__dict__[str(k)] = v

class SearchResultsMetaData(_SearchBase):
    """metadata of search query results

    Available attributes:
    documentFiltering - flag indicates whether duplicate page filtering was perfomed in this search
    searchComments - human-readable informational message (example: "'the' is a very common word
        and was not included in your search")
    estimatedTotalResultsCount - estimated total number of results for this query
    estimateIsExact - flag indicates whether estimatedTotalResultsCount is an exact value
    searchQuery - search string that initiated this search
    startIndex - index of first result returned (zero-based)
    endIndex - index of last result returned (zero-based)
    searchTips - human-readable informational message on how to use Google bette
    directoryCategories - list of dictionaries like this:
        {'fullViewableName': Open Directory category,
         'specialEncoding': encoding scheme of this directory category}
    searchTime - total search time, in seconds
    """
    pass

class SearchResult(_SearchBase):
    """search result

    Available attributes:
    URL - URL
    title - title (HTML)
    snippet - snippet showing query context (HTML)
    cachedSize - size of cached version of this result, (KB)
    relatedInformationPresent - flag indicates that the "related:" keyword is supported for this URL
    hostName: When filtering occurs, a maximum of two results from any given host is returned.
        When this occurs, the second resultElement that comes from that host contains
        the host name in this parameter.
    directoryCategory: dictionary like this:
        {'fullViewableName': Open Directory category,
         'specialEncoding': encoding scheme of this directory category}
    directoryTitle: Open Directory title of this result (or blank)
    summary - Open Directory summary for this result (or blank)
    """
    pass

class SearchReturnValue:
    """complete search results for a single query

    Available attributes:
    meta - SearchResultsMetaData
    results - list of SearchResult
    """
    def __init__(self, metadata, results):
        self.meta = metadata
        self.results = results

## main functions
def doGoogleSearch(q, start=0, maxResults=10, filter=1, restrict='',
                   safeSearch=0, language='', inputencoding='', outputencoding='',
                   license_key = None, http_proxy = None):
    """search Google

    You need a license key to call this function; see
    http://www.google.com/apis/ to get one.  Then you can either pass it to
    this function every time, or set it globally; see the module docs for details.

    Parameters:
    q - search string.  Anything you could type at google.com, you can pass here.
        See http://www.google.com/help/features.html for examples of advanced features.
    start (optional) - zero-based index of first desired result (for paging through
        multiple pages of results)
    maxResults (optional) - maximum number of results, currently capped at 10
    filter (optional) - set to 1 to filter out similar results, set to 0 to see everything
    restrict (optional) - restrict results by country or topic.  Examples:
        Ukraine - search only sites located in Ukraine
        linux - search Linux sites only
        mac - search Mac sites only
        bsd - search FreeBSD sites only
        See the APIs_reference.html file in the SDK (http://www.google.com/apis/download.html)
        for more advanced examples and a full list of country codes and topics.
    safeSearch (optional) - set to 1 to filter results with SafeSearch (no adult material)
    language (optional) - restricts search to documents in one or more languages.  Example:
        lang_en - only return pages in English
        lang_fr - only return pages in French
        See the APIs_reference.html file in the SDK (http://www.google.com/apis/download.html)
        for more advanced examples and a full list of language codes.
    inputencoding (optional) - sets the character encoding of q parameter
    outputencoding (optional) - sets the character encoding of the returned results
        See the APIs_reference.html file in the SDK (http://www.google.com/apis/download.html)
        for a full list of encodings.
    http_proxy (optional) - address of HTTP proxy to use for sending and receiving SOAP messages

    Returns: SearchReturnValue
    .meta - SearchMetaData
    .results - list of SearchResult
    See documentation of these individual classes for list of available attributes
    """
    http_proxy = getProxy(http_proxy)
    remoteserver = SOAP.SOAPProxy(_url, namespace=_namespace, http_proxy=http_proxy)
    license_key = getLicense(license_key)
    filter = _marshalBoolean(filter)
    safeSearch = _marshalBoolean(safeSearch)
    data = remoteserver.doGoogleSearch(license_key, q, start, maxResults, filter, restrict,
                                       safeSearch, language, inputencoding, outputencoding)
    metadata = data._asdict
    del metadata["resultElements"]
    metadata = SearchResultsMetaData(metadata)
    results = [SearchResult(node._asdict) for node in data.resultElements]
    return SearchReturnValue(metadata, results)

def doGetCachedPage(url, license_key = None, http_proxy = None):
    """get page from Google cache

    You need a license key to call this function; see
    http://www.google.com/apis/ to get one.  Then you can either pass it to
    this function every time, or set it globally; see the module docs for details.

    Parameters:
    url - address of page to get
    license_key (optional) - Google license key
    http_proxy (optional) - address of HTTP proxy to use for sending and receiving SOAP messages

    Returns: string, text of cached page
    """
    http_proxy = getProxy(http_proxy)
    remoteserver = SOAP.SOAPProxy(_url, namespace=_namespace, http_proxy=http_proxy)
    license_key = getLicense(license_key)
    return remoteserver.doGetCachedPage(license_key, url)

def doSpellingSuggestion(phrase, license_key = None, http_proxy = None):
    """get spelling suggestions from Google

    You need a license key to call this function; see
    http://www.google.com/apis/ to get one.  Then you can either pass it to
    this function every time, or set it globally; see the module docs for details.

    Parameters:
    phrase - word or phrase to spell-check
    http_proxy (optional) - address of HTTP proxy to use for sending and receiving SOAP messages

    Returns: text of suggested replacement, or None
    """
    http_proxy = getProxy(http_proxy)
    remoteserver = SOAP.SOAPProxy(_url, namespace=_namespace, http_proxy=http_proxy)
    license_key = getLicense(license_key)
    return remoteserver.doSpellingSuggestion(license_key, phrase)

## functional test suite (see googletest.py for unit test suite)
def test():
    try:
        getLicense(None)
    except NoLicenseKey:
        return
    print "Searching for Python at google.com..."
    data = doGoogleSearch("Python")
    output(data, {"func": "doGoogleSearch"})

    print "\nSearching for 5 _French_ pages about Python, encoded in ISO-8859-1..."
    data = doGoogleSearch("Python", language='lang_fr', outputencoding='ISO-8859-1', maxResults=5)
    output(data, {"func": "doGoogleSearch"})

    phrase = "Pyhton programming languager"
    print "\nTesting spelling suggetions for '%s'..." % phrase
    data = doSpellingSuggestion(phrase)
    output(data, {"func": "doSpellingSuggestion"})

## main driver for command-line use
def main(argv):
    if not argv:
        usage()
        return
    q = None
    func = None
    http_proxy = None
    license_key = None
    feelingLucky = 0
    showMeta = 0
    reverseOrder = 0
    runTest = 0
    outputFormat = "text"
    try:
        opts, args = getopt.getopt(argv, "s:c:p:k:lmrx:hvt1",
            ["search=", "cache=", "spelling=", "key=", "lucky", "meta", "reverse", "proxy=", "help", "version", "test"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-s", "--search"):
            q = arg
            func = "doGoogleSearch"
        elif opt in ("-c", "--cache"):
            q = arg
            func = "doGetCachedPage"
        elif opt in ("-p", "--spelling"):
            q = arg
            func = "doSpellingSuggestion"
        elif opt in ("-k", "--key"):
            license_key = arg
        elif opt in ("-l", "-1", "--lucky"):
            feelingLucky = 1
        elif opt in ("-m", "--meta"):
            showMeta = 1
        elif opt in ("-r", "--reverse"):
            reverseOrder = 1
        elif opt in ("-x", "--proxy"):
            http_proxy = arg
        elif opt in ("-h", "--help"):
            usage()
        elif opt in ("-v", "--version"):
            version()
        elif opt in ("-t", "--test"):
            runTest = 1
    if runTest:
        setLicense(license_key)
        setProxy(http_proxy)
        test()
    if args and not q:
        q = args[0]
        func = "doGoogleSearch"
    if func:
        results = globals()[func](q, http_proxy=http_proxy, license_key=license_key)
        output(results, locals())

if __name__ == '__main__':
    main(sys.argv[1:])
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
