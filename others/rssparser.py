#!/usr/bin/python
"""Ultra-liberal RSS parser

Visit http://diveintomark.org/projects/rss_parser/ for the latest version

Handles RSS 0.9x and RSS 1.0 feeds

RSS 0.9x elements:
- title, link, description, webMaster, managingEditor, language
  copyright, lastBuildDate, pubDate

RSS 1.0 elements:
- dc:rights, dc:language, dc:creator, dc:date, dc:subject,
  content:encoded

Things it handles that choke other RSS parsers:
- bastard combinations of RSS 0.9x and RSS 1.0 (most Movable Type feeds)
- illegal XML characters (most Radio feeds)
- naked and/or invalid HTML in description (The Register)
- content:encoded in item element (Aaron Swartz)
- guid in item element (Scripting News)
- fullitem in item element (Jon Udell)
- non-standard namespaces (BitWorking)

Requires Python 2.2 or later
"""

__author__ = "Mark Pilgrim (f8dy@diveintomark.org)"
__copyright__ = "Copyright 2002, Mark Pilgrim"
__contributors__ = ["Jason Diamond (jason@injektilo.org)"]
__license__ = "GPL"
__history__ = """
1.0 - 9/27/2002 - MAP - fixed namespace processing on prefixed RSS 2.0 elements,
  added Simon Fell's test suite
1.1 - 9/29/2002 - MAP - fixed infinite loop on incomplete CDATA sections
2.0 - 10/19/2002
  JD - use inchannel to watch out for image and textinput elements which can
  also contain title, link, and description elements
  JD - check for isPermaLink="false" attribute on guid elements
  JD - replaced openAnything with open_resource supporting ETag and
  If-Modified-Since request headers
  JD - parse now accepts etag, modified, agent, and referrer optional
  arguments
  JD - modified parse to return a dictionary instead of a tuple so that any
  etag or modified information can be returned and cached by the caller
2.0.1 - 10/21/2002 - MAP - changed parse() so that if we don't get anything
  because of etag/modified, return the old etag/modified to the caller to
  indicate why nothing is being returned
2.0.2 - 10/21/2002 - JB - added the inchannel to the if statement, otherwise its
  useless.  Fixes the problem JD was addressing by adding it.
2.1 - 11/14/2002 - MAP - added gzip support
2.2 - 1/27/2003 - MAP - added attribute support, admin:generatorAgent.
  start_admingeneratoragent is an example of how to handle elements with
  only attributes, no content.
"""

try:
    import timeoutsocket # http://www.timo-tasi.org/python/timeoutsocket.py
    timeoutsocket.setDefaultSocketTimeout(10)
except ImportError:
    pass
import cgi, re, sgmllib, string, StringIO, urllib, gzip
sgmllib.tagfind = re.compile('[a-zA-Z][-_.:a-zA-Z0-9]*')

def decodeEntities(data):
    data = data or ''
    data = data.replace('&lt;', '<')
    data = data.replace('&gt;', '>')
    data = data.replace('&quot;', '"')
    data = data.replace('&apos;', "'")
    data = data.replace('&amp;', '&')
    return data

class RSSParser(sgmllib.SGMLParser):
    namespaces = {"http://backend.userland.com/rss": "",
                  "http://backend.userland.com/rss2": "",
                  "http://purl.org/rss/1.0/": "",
                  "http://purl.org/rss/1.0/modules/textinput/": "ti",
                  "http://purl.org/rss/1.0/modules/company/": "co",
                  "http://purl.org/rss/1.0/modules/syndication/": "sy",
                  "http://purl.org/dc/elements/1.1/": "dc",
                  "http://webns.net/mvcb/": "admin"}

    def reset(self):
        self.channel = {}
        self.items = []
        self.elementstack = []
        self.inchannel = 0
        self.initem = 0
        self.namespacemap = {}
        sgmllib.SGMLParser.reset(self)

    def push(self, element, expectingText):
        self.elementstack.append([element, expectingText, []])

    def pop(self, element):
        if not self.elementstack: return
        if self.elementstack[-1][0] != element: return
        element, expectingText, pieces = self.elementstack.pop()
        if not expectingText: return
        output = "".join(pieces)
        output = decodeEntities(output)
        if self.initem:
            self.items[-1][element] = output
        elif self.inchannel:
            self.channel[element] = output

    def _addNamespaces(self, attrs):
        for prefix, value in attrs:
            if not prefix.startswith("xmlns:"): continue
            prefix = prefix[6:]
            if self.namespaces.has_key(value):
                self.namespacemap[prefix] = self.namespaces[value]

    def _mapToStandardPrefix(self, name):
        colonpos = name.find(':')
        if colonpos <> -1:
            prefix = name[:colonpos]
            suffix = name[colonpos+1:]
            prefix = self.namespacemap.get(prefix, prefix)
            name = prefix + ':' + suffix
        return name

    def _getAttribute(self, attrs, name):
        value = [v for k, v in attrs if self._mapToStandardPrefix(k) == name]
        if value:
            value = value[0]
        else:
            value = None
        return value

    def start_channel(self, attrs):
        self.push('channel', 0)
        self.inchannel = 1

    def end_channel(self):
        self.pop('channel')
        self.inchannel = 0

    def start_item(self, attrs):
        self.items.append({})
        self.push('item', 0)
        self.initem = 1

    def end_item(self):
        self.pop('item')
        self.initem = 0

    def start_dc_language(self, attrs):
        self.push('language', 1)
    start_language = start_dc_language

    def end_dc_language(self):
        self.pop('language')
    end_language = end_dc_language

    def start_dc_creator(self, attrs):
        self.push('creator', 1)
    start_managingeditor = start_dc_creator
    start_webmaster = start_dc_creator

    def end_dc_creator(self):
        self.pop('creator')
    end_managingeditor = end_dc_creator
    end_webmaster = end_dc_creator

    def start_dc_rights(self, attrs):
        self.push('rights', 1)
    start_copyright = start_dc_rights

    def end_dc_rights(self):
        self.pop('rights')
    end_copyright = end_dc_rights

    def start_dc_date(self, attrs):
        self.push('date', 1)
    start_lastbuilddate = start_dc_date
    start_pubdate = start_dc_date

    def end_dc_date(self):
        self.pop('date')
    end_lastbuilddate = end_dc_date
    end_pubdate = end_dc_date

    def start_dc_subject(self, attrs):
        self.push('category', 1)

    def end_dc_subject(self):
        self.pop('category')

    def start_link(self, attrs):
        self.push('link', self.inchannel or self.initem)

    def end_link(self):
        self.pop('link')

    def start_guid(self, attrs):
        self.guidislink = ('ispermalink', 'false') not in attrs
        self.push('guid', 1)

    def end_guid(self):
        self.pop('guid')
        if self.guidislink:
            self.items[-1]['link'] = self.items[-1]['guid']

    def start_title(self, attrs):
        self.push('title', self.inchannel or self.initem)

    def start_description(self, attrs):
        self.push('description', self.inchannel or self.initem)

    def start_content_encoded(self, attrs):
        self.push('content_encoded', 1)
    start_fullitem = start_content_encoded

    def end_content_encoded(self):
        self.pop('content_encoded')
    end_fullitem = end_content_encoded

    def start_admin_generatoragent(self, attrs):
        self.push('generator', 1)
        value = self._getAttribute(attrs, 'rdf:resource')
        if value:
            self.elementstack[-1][2].append(value)
        self.pop('generator')

    def unknown_starttag(self, tag, attrs):
        self._addNamespaces(attrs)
        colonpos = tag.find(':')
        if colonpos <> -1:
            prefix = tag[:colonpos]
            suffix = tag[colonpos+1:]
            prefix = self.namespacemap.get(prefix, prefix)
            if prefix:
                prefix = prefix + '_'
            methodname = 'start_' + prefix + suffix
            try:
                method = getattr(self, methodname)
                return method(attrs)
            except AttributeError:
                return self.push(prefix + suffix, 0)
        return self.push(tag, 0)

    def unknown_endtag(self, tag):
        colonpos = tag.find(':')
        if colonpos <> -1:
            prefix = tag[:colonpos]
            suffix = tag[colonpos+1:]
            prefix = self.namespacemap.get(prefix, prefix)
            if prefix:
                prefix = prefix + '_'
            methodname = 'end_' + prefix + suffix
            try:
                method = getattr(self, methodname)
                return method()
            except AttributeError:
                return self.pop(prefix + suffix)
        return self.pop(tag)

    def handle_charref(self, ref):
        # called for each character reference, e.g. for "&#160;", ref will be "160"
        # Reconstruct the original character reference.
        if not self.elementstack: return
        self.elementstack[-1][2].append("&#%(ref)s;" % locals())

    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for "&copy;", ref will be "copy"
        # Reconstruct the original entity reference.
        if not self.elementstack: return
        self.elementstack[-1][2].append("&%(ref)s;" % locals())

    def handle_data(self, text):
        # called for each block of plain text, i.e. outside of any tag and
        # not containing any character or entity references
        if not self.elementstack: return
        self.elementstack[-1][2].append(text)

    def handle_comment(self, text):
        # called for each comment, e.g. <!-- insert message here -->
        pass

    def handle_pi(self, text):
        # called for each processing instruction, e.g. <?instruction>
        pass

    def handle_decl(self, text):
        # called for the DOCTYPE, if present, e.g.
        # <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        #     "http://www.w3.org/TR/html4/loose.dtd">
        pass

    _new_declname_match = re.compile(r'[a-zA-Z][-_.a-zA-Z0-9:]*\s*').match
    def _scan_name(self, i, declstartpos):
        rawdata = self.rawdata
        n = len(rawdata)
        if i == n:
            return None, -1
        m = self._new_declname_match(rawdata, i)
        if m:
            s = m.group()
            name = s.strip()
            if (i + len(s)) == n:
                return None, -1  # end of buffer
            return string.lower(name), m.end()
        else:
            self.updatepos(declstartpos, i)
            self.error("expected name token")

    def parse_declaration(self, i):
        # override internal declaration handler to handle CDATA blocks
        if self.rawdata[i:i+9] == '<![CDATA[':
            k = self.rawdata.find(']]>', i)
            if k == -1: k = len(self.rawdata)
            self.handle_data(cgi.escape(self.rawdata[i+9:k]))
            return k+3
        return sgmllib.SGMLParser.parse_declaration(self, i)

def open_resource(source, etag=None, modified=None, agent=None, referrer=None):
    """
    URI, filename, or string --> stream

    This function lets you define parsers that take any input source
    (URL, pathname to local or network file, or actual data as a string)
    and deal with it in a uniform manner.  Returned object is guaranteed
    to have all the basic stdio read methods (read, readline, readlines).
    Just .close() the object when you're done with it.

    If the etag argument is supplied, it will be used as the value of an
    If-None-Match request header.

    If the modified argument is supplied, it must be a tuple of 9 integers
    as returned by gmtime() in the standard Python time module. This MUST
    be in GMT (Greenwich Mean Time). The formatted date/time will be used
    as the value of an If-Modified-Since request header.

    If the agent argument is supplied, it will be used as the value of a
    User-Agent request header.

    If the referrer argument is supplied, it will be used as the value of a
    Referer[sic] request header.

    The optional arguments are only used if the source argument is an HTTP
    URL and the urllib2 module is importable (i.e., you must be using Python
    version 2.0 or higher).
    """

    if hasattr(source, "read"):
        return source

    if source == "-":
        return sys.stdin

    # try to open with urllib2 (to use optional headers)
    try:
        import urllib2
        request = urllib2.Request(source)
        if etag:
            request.add_header("If-None-Match", etag)
        if modified:
            request.add_header("If-Modified-Since", format_http_date(modified))
        if agent:
            request.add_header("User-Agent", agent)
        if referrer:
            # http://www.dictionary.com/search?q=referer
            request.add_header("Referer", referrer)
        request.add_header("Accept-encoding", "gzip")
        try:
            return urllib2.urlopen(request)
        except urllib2.HTTPError:
            # either the resource is not modified or some other HTTP
            # error occurred so return an empty resource
            return StringIO.StringIO("")
        except:
            # source must not be a valid URL but it might be a valid filename
            pass
    except ImportError:
        # urllib2 isn't available so try to open with urllib
        try:
            return urllib.urlopen(source)
        except:
            # source still might be a filename
            pass

    # try to open with native open function (if source is a filename)
    try:
        return open(source)
    except:
        pass

    # treat source as string
    return StringIO.StringIO(str(source))

def get_etag(resource):
    """
    Get the ETag associated with a response returned from a call to
    open_resource().

    If the resource was not returned from an HTTP server or the server did
    not specify an ETag for the resource, this will return None.
    """

    if hasattr(resource, "info"):
        return resource.info().getheader("ETag")
    return None

def get_modified(resource):
    """
    Get the Last-Modified timestamp for a response returned from a call to
    open_resource().

    If the resource was not returned from an HTTP server or the server did
    not specify a Last-Modified timestamp, this function will return None.
    Otherwise, it returns a tuple of 9 integers as returned by gmtime() in
    the standard Python time module().
    """

    if hasattr(resource, "info"):
        last_modified = resource.info().getheader("Last-Modified")
        if last_modified:
            return parse_http_date(last_modified)
    return None

short_weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
long_weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def format_http_date(date):
    """
    Formats a tuple of 9 integers into an RFC 1123-compliant timestamp as
    required in RFC 2616. We don't use time.strftime() since the %a and %b
    directives can be affected by the current locale (HTTP dates have to be
    in English). The date MUST be in GMT (Greenwich Mean Time).
    """

    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (short_weekdays[date[6]], date[2], months[date[1] - 1], date[0], date[3], date[4], date[5])

rfc1123_match = re.compile(r"(?P<weekday>[A-Z][a-z]{2}), (?P<day>\d{2}) (?P<month>[A-Z][a-z]{2}) (?P<year>\d{4}) (?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}) GMT").match
rfc850_match = re.compile(r"(?P<weekday>[A-Z][a-z]+), (?P<day>\d{2})-(?P<month>[A-Z][a-z]{2})-(?P<year>\d{2}) (?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}) GMT").match
asctime_match = re.compile(r"(?P<weekday>[A-Z][a-z]{2}) (?P<month>[A-Z][a-z]{2})  ?(?P<day>\d\d?) (?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}) (?P<year>\d{4})").match

def parse_http_date(date):
    """
    Parses any of the three HTTP date formats into a tuple of 9 integers as
    returned by time.gmtime(). This should not use time.strptime() since
    that function is not available on all platforms and could also be
    affected by the current locale.
    """

    date = str(date)
    year = 0
    weekdays = short_weekdays

    m = rfc1123_match(date)
    if not m:
        m = rfc850_match(date)
        if m:
            year = 1900
            weekdays = long_weekdays
        else:
            m = asctime_match(date)
            if not m:
                return None

    try:
        year = year + int(m.group("year"))
        month = months.index(m.group("month")) + 1
        day = int(m.group("day"))
        hour = int(m.group("hour"))
        minute = int(m.group("minute"))
        second = int(m.group("second"))
        weekday = weekdays.index(m.group("weekday"))
        a = int((14 - month) / 12)
        julian_day = (day - 32045 + int(((153 * (month + (12 * a) - 3)) + 2) / 5) + int((146097 * (year + 4800 - a)) / 400)) - (int((146097 * (year + 4799)) / 400) - 31738) + 1
        daylight_savings_flag = 0
        return (year, month, day, hour, minute, second, weekday, julian_day, daylight_savings_flag)
    except:
        # the month or weekday lookup probably failed indicating an invalid timestamp
        return None

def parse(uri, etag=None, modified=None, agent=None, referrer=None):
    r = RSSParser()
    f = open_resource(uri, etag=etag, modified=modified, agent=agent, referrer=referrer)
    data = f.read()
    if hasattr(f, "headers"):
        if f.headers.get('content-encoding', None) == 'gzip':
            data = gzip.GzipFile(fileobj=StringIO.StringIO(data)).read()
    r.feed(data)
    result = {"channel": r.channel, "items": r.items}
    newEtag = get_etag(f)
    if newEtag: result["etag"] = newEtag
    elif etag: result["etag"] = etag
    newModified = get_modified(f)
    if newModified: result["modified"] = newModified
    elif modified: result["modified"] = modified
    f.close()
    return result

TEST_SUITE = ('http://www.pocketsoap.com/rssTests/rss1.0withModules.xml',
              'http://www.pocketsoap.com/rssTests/rss1.0withModulesNoDefNS.xml',
              'http://www.pocketsoap.com/rssTests/rss1.0withModulesNoDefNSLocalNameClash.xml',
              'http://www.pocketsoap.com/rssTests/rss2.0noNSwithModules.xml',
              'http://www.pocketsoap.com/rssTests/rss2.0noNSwithModulesLocalNameClash.xml',
              'http://www.pocketsoap.com/rssTests/rss2.0NSwithModules.xml',
              'http://www.pocketsoap.com/rssTests/rss2.0NSwithModulesNoDefNS.xml',
              'http://www.pocketsoap.com/rssTests/rss2.0NSwithModulesNoDefNSLocalNameClash.xml')

if __name__ == '__main__':
    import sys
    if sys.argv[1:]:
        urls = sys.argv[1:]
    else:
        urls = TEST_SUITE
    from pprint import pprint
    for url in urls:
        print url
        print
        result = parse(url)
        pprint(result['channel'])
        print
