#!/usr/bin/python
"""Ultra-liberal feed parser

Visit http://diveintomark.org/projects/feed_parser/ for the latest version

Handles RSS 0.9x, RSS 1.0, RSS 2.0, Pie/Atom/Echo feeds

RSS 0.9x/common elements:
- title, link, guid, description, webMaster, managingEditor, language
  copyright, lastBuildDate, pubDate

Additional RSS 1.0/2.0 elements:
- dc:rights, dc:language, dc:creator, dc:date, dc:subject,
  content:encoded, admin:generatorAgent, admin:errorReportsTo,
  
Addition Pie/Atom/Echo elements:
- subtitle, created, issued, modified, summary, id, content

Things it handles that choke other parsers:
- bastard combinations of RSS 0.9x and RSS 1.0
- illegal XML characters
- naked and/or invalid HTML in description
- content:encoded in item element
- guid in item element
- fullitem in item element
- non-standard namespaces
- inline XML in content (Pie/Atom/Echo)
- multiple content items per entry (Pie/Atom/Echo)

Requires Python 2.2 or later
"""

__version__ = "2.5.3"
__author__ = "Mark Pilgrim <http://diveintomark.org/>"
__copyright__ = "Copyright 2002-3, Mark Pilgrim"
__contributors__ = ["Jason Diamond <http://injektilo.org/>",
                    "John Beimler <http://john.beimler.org/>"]
__license__ = "Python"
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
2.3 - 6/11/2003 - MAP - added USER_AGENT for default (if caller doesn't specify);
  also, make sure we send the User-Agent even if urllib2 isn't available.
  Match any variation of backend.userland.com/rss namespace.
2.3.1 - 6/12/2003 - MAP - if item has both link and guid, return both as-is.
2.4 - 7/9/2003 - MAP - added preliminary Pie/Atom/Echo support based on Sam Ruby's
  snapshot of July 1 <http://www.intertwingly.net/blog/1506.html>; changed
  project name
2.5 - 7/25/2003 - MAP - changed to Python license (all contributors agree);
  removed unnecessary urllib code -- urllib2 should always be available anyway;
  return actual url, status, and full HTTP headers (as result['url'],
  result['status'], and result['headers']) if parsing a remote feed over HTTP --
  this should pass all the HTTP tests at <http://diveintomark.org/tests/client/http/>;
  added the latest namespace-of-the-week for RSS 2.0
2.5.1 - 7/26/2003 - RMK - clear opener.addheaders so we only send our custom
  User-Agent (otherwise urllib2 sends two, which confuses some servers)
2.5.2 - 7/28/2003 - MAP - entity-decode inline xml properly; added support for
  inline <xhtml:body> and <xhtml:div> as used in some RSS 2.0 feeds
2.5.3 - 8/6/2003 - TvdV - patch to track whether we're inside an image or
  textInput, and also to return the character encoding (if specified)
"""

try:
    import timeoutsocket # http://www.timo-tasi.org/python/timeoutsocket.py
    timeoutsocket.setDefaultSocketTimeout(10)
except ImportError:
    pass
import cgi, re, sgmllib, string, StringIO, gzip, urllib2
sgmllib.tagfind = re.compile('[a-zA-Z][-_.:a-zA-Z0-9]*')

USER_AGENT = "UltraLiberalFeedParser/%s +http://diveintomark.org/projects/feed_parser/" % __version__

def decodeEntities(data):
    data = data or ''
    data = data.replace('&lt;', '<')
    data = data.replace('&gt;', '>')
    data = data.replace('&quot;', '"')
    data = data.replace('&apos;', "'")
    data = data.replace('&amp;', '&')
    return data

class FeedParser(sgmllib.SGMLParser):
    namespaces = {"http://backend.userland.com/rss": "",
                  "http://blogs.law.harvard.edu/tech/rss": "",
                  "http://purl.org/rss/1.0/": "",
                  "http://example.com/newformat#": "",
                  "http://example.com/necho": "",
                  "http://purl.org/echo/": "",
                  "uri/of/echo/namespace#": "",
                  "http://purl.org/pie/": "",
                  "http://purl.org/rss/1.0/modules/textinput/": "ti",
                  "http://purl.org/rss/1.0/modules/company/": "co",
                  "http://purl.org/rss/1.0/modules/syndication/": "sy",
                  "http://purl.org/dc/elements/1.1/": "dc",
                  "http://webns.net/mvcb/": "admin",
                  "http://www.w3.org/1999/xhtml": "xhtml"}

    def reset(self):
        self.channel = {}
        self.items = []
        self.elementstack = []
        self.inchannel = 0
        self.initem = 0
        self.incontent = 0
        self.intextinput = 0
        self.inimage = 0
        self.contentmode = None
        self.contenttype = None
        self.contentlang = None
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
        if self.incontent and self.initem:
            if not self.items[-1].has_key(element):
                self.items[-1][element] = []
            self.items[-1][element].append({"language":self.contentlang, "type":self.contenttype, "value":output})
        elif self.initem:
            self.items[-1][element] = output
        elif self.inchannel and (not self.intextinput) and (not self.inimage):
            self.channel[element] = output

    def _addNamespaces(self, attrs):
        for prefix, value in attrs:
            if not prefix.startswith("xmlns:"): continue
            prefix = prefix[6:]
            if prefix.find('backend.userland.com/rss') <> -1:
                # match any backend.userland.com namespace
                prefix = 'http://backend.userland.com/rss'
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
    
    def start_image(self, attrs):
        self.inimage = 1
            
    def end_image(self):
        self.inimage = 0
                
    def start_textinput(self, attrs):
        self.intextinput = 1
        
    def end_textinput(self):
        self.intextinput = 0

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
            if not self.items[-1].has_key('link'):
                # guid acts as link, but only if "ispermalink" is not present or is "true",
                # and only if the item doesn't already have a link element
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

    def start_feed(self, attrs):
        self.inchannel = 1

    def end_feed(self):
        self.inchannel = 0

    def start_entry(self, attrs):
        self.items.append({})
        self.push('item', 0)
        self.initem = 1

    def end_entry(self):
        self.pop('item')
        self.initem = 0
        
    def start_subtitle(self, attrs):
        self.push('subtitle', 1)

    def end_subtitle(self):
        self.pop('subtitle')

    def start_summary(self, attrs):
        self.push('summary', 1)

    def end_summary(self):
        self.pop('summary')
        
    def start_modified(self, attrs):
        self.push('modified', 1)

    def end_modified(self):
        self.pop('modified')

    def start_created(self, attrs):
        self.push('created', 1)

    def end_created(self):
        self.pop('created')

    def start_issued(self, attrs):
        self.push('issued', 1)

    def end_issued(self):
        self.pop('issued')

    def start_id(self, attrs):
        self.push('id', 1)

    def end_id(self):
        self.pop('id')

    def start_content(self, attrs):
        self.incontent = 1
        if ('mode', 'escaped') in attrs:
            self.contentmode = 'escaped'
        elif ('mode', 'base64') in attrs:
            self.contentmode = 'base64'
        else:
            self.contentmode = 'xml'
        mimetype = [v for k, v in attrs if k=='type']
        if mimetype:
            self.contenttype = mimetype[0]
        xmllang = [v for k, v in attrs if k=='xml:lang']
        if xmllang:
            self.contentlang = xmllang[0]
        self.push('content', 1)

    def end_content(self):
        self.pop('content')
        self.incontent = 0
        self.contentmode = None
        self.contenttype = None
        self.contentlang = None

    def start_body(self, attrs):
        self.incontent = 1
        self.contentmode = 'xml'
        self.contenttype = 'application/xhtml+xml'
        xmllang = [v for k, v in attrs if k=='xml:lang']
        if xmllang:
            self.contentlang = xmllang[0]
        self.push('content', 1)

    start_div = start_body
    start_xhtml_body = start_body
    start_xhtml_div = start_body
    end_body = end_content
    end_div = end_content
    end_xhtml_body = end_content
    end_xhtml_div = end_content
        
    def unknown_starttag(self, tag, attrs):
        if self.incontent and self.contentmode == 'xml':
            self.handle_data("<%s%s>" % (tag, "".join([' %s="%s"' % t for t in attrs])))
            return
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
        if self.incontent and self.contentmode == 'xml':
            self.handle_data("</%s>" % tag)
            return
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
        text = "&#%s;" % ref
        if self.incontent and self.contentmode == 'xml':
            text = cgi.escape(text)
        self.elementstack[-1][2].append(text)

    def handle_entityref(self, ref):
        # called for each entity reference, e.g. for "&copy;", ref will be "copy"
        # Reconstruct the original entity reference.
        if not self.elementstack: return
        text = "&%s;" % ref
        if self.incontent and self.contentmode == 'xml':
            text = cgi.escape(text)
        self.elementstack[-1][2].append(text)

    def handle_data(self, text):
        # called for each block of plain text, i.e. outside of any tag and
        # not containing any character or entity references
        if not self.elementstack: return
        if self.incontent and self.contentmode == 'xml':
            text = cgi.escape(text)
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

class FeedURLHandler(urllib2.HTTPRedirectHandler, urllib2.HTTPDefaultErrorHandler):
    def http_error_default(self, req, fp, code, msg, headers):
        if ((code / 100) == 3) and (code != 304):
            return self.http_error_302(req, fp, code, msg, headers)
        from urllib import addinfourl
        infourl = addinfourl(fp, headers, req.get_full_url())
        infourl.status = code
        return infourl
#        raise urllib2.HTTPError(req.get_full_url(), code, msg, headers, fp)

    def http_error_302(self, req, fp, code, msg, headers):
        infourl = urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
        infourl.status = code
        return infourl

    def http_error_301(self, req, fp, code, msg, headers):
        infourl = urllib2.HTTPRedirectHandler.http_error_301(self, req, fp, code, msg, headers)
        infourl.status = code
        return infourl

    http_error_300 = http_error_302
    http_error_307 = http_error_302
        
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
    """

    if hasattr(source, "read"):
        return source

    if source == "-":
        return sys.stdin

    if not agent:
        agent = USER_AGENT
        
    # try to open with urllib2 (to use optional headers)
    request = urllib2.Request(source)
    if etag:
        request.add_header("If-None-Match", etag)
    if modified:
        request.add_header("If-Modified-Since", format_http_date(modified))
    request.add_header("User-Agent", agent)
    if referrer:
        request.add_header("Referer", referrer)
        request.add_header("Accept-encoding", "gzip")
    opener = urllib2.build_opener(FeedURLHandler())
    opener.addheaders = [] # RMK - must clear so we only send our custom User-Agent
    try:
        return opener.open(request)
    except:
        # source is not a valid URL, but it might be a valid filename
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
    r = FeedParser()
    f = open_resource(uri, etag=etag, modified=modified, agent=agent, referrer=referrer)
    data = f.read()
    if hasattr(f, "headers"):
        if f.headers.get('content-encoding', '') == 'gzip':
            try:
                data = gzip.GzipFile(fileobj=StringIO.StringIO(data)).read()
            except:
                # some feeds claim to be gzipped but they're not, so we get garbage
                data = ''
    r.feed(data)
    result = {"channel": r.channel, "items": r.items}
    newEtag = get_etag(f)
    if newEtag: result["etag"] = newEtag
    elif etag: result["etag"] = etag
    newModified = get_modified(f)
    if newModified: result["modified"] = newModified
    elif modified: result["modified"] = modified
    if hasattr(f, "url"):
        result["url"] = f.url
    if hasattr(f, "headers"):
        result["headers"] = f.headers.dict
    if hasattr(f, "status"):
        result["status"] = f.status
    elif hasattr(f, "url"):
        result["status"] = 200
    # get the xml encoding
    if result.get('encoding', '') == '':
        xmlheaderRe = re.compile('<\?.*encoding="(.*)".*\?>')
        match = xmlheaderRe.match(data)
        if match:
            result['encoding'] = match.groups()[0].lower()
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
        pprint(result)
        print

"""
TODO
- textinput/textInput
- image
- author
- contributor
- comments
"""
