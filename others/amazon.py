"""Python wrapper for Amazon web APIs

This module allows you to access Amazon's web APIs,
to do things like search Amazon and get the results programmatically.
Described here:
  http://www.amazon.com/webservices
  
You need a Amazon-provided license key to use these services.
Follow the link above to get one.  These functions will look in
several places (in this order) for the license key:
- the "license_key" argument of each function
- the module-level LICENSE_KEY variable (call setLicense once to set it)
- an environment variable called AMAZON_LICENSE_KEY
- a file called ".amazonkey" in the current directory
- a file called "amazonkey.txt" in the current directory
- a file called ".amazonkey" in your home directory
- a file called "amazonkey.txt" in your home directory
- a file called ".amazonkey" in the same directory as amazon.py
- a file called "amazonkey.txt" in the same directory as amazon.py

Sample usage:
>>> import amazon
>>> amazon.setLicense('...') # must get your own key!
>>> pythonBooks = amazon.searchByKeyword('Python')
>>> pythonBooks[0].ProductName
u'Learning Python (Help for Programmers)'
>>> pythonBooks[0].URL
...
>>> pythonBooks[0].OurPrice
...

Other available functions:
- browseBestSellers
- searchByASIN
- searchByUPC
- searchByAuthor
- searchByArtist
- searchByActor
- searchByDirector
- searchByManufacturer
- searchByListMania
- searchSimilar

Other usage notes:
- Most functions can take product_line as well, see source for possible values
- All functions can take type="lite" to get less detail in results
- All functions can take page=N to get second, third, fourth page of results
- All functions can take license_key="XYZ", instead of setting it globally
- All functions can take http_proxy="http://x/y/z" which overrides your system setting
"""

__author__ = "Mark Pilgrim (f8dy@diveintomark.org)"
__version__ = "0.4"
__cvsversion__ = "$Revision$"[11:-2]
__date__ = "$Date$"[7:-2]
__copyright__ = "Copyright (c) 2002 Mark Pilgrim"
__license__ = "Python"

from xml.dom import minidom
import os, sys, getopt, cgi, urllib
try:
    import timeoutsocket # http://www.timo-tasi.org/python/timeoutsocket.py
    timeoutsocket.setDefaultSocketTimeout(10)
except ImportError:
    pass

LICENSE_KEY = None
HTTP_PROXY = None

# don't touch the rest of these constants
class AmazonError(Exception): pass
class NoLicenseKey(Exception): pass
_amazonfile1 = ".amazonkey"
_amazonfile2 = "amazonkey.txt"
_licenseLocations = (
    (lambda key: key, 'passed to the function in license_key variable'),
    (lambda key: LICENSE_KEY, 'module-level LICENSE_KEY variable (call setLicense to set it)'),
    (lambda key: os.environ.get('AMAZON_LICENSE_KEY', None), 'an environment variable called AMAZON_LICENSE_KEY'),
    (lambda key: _contentsOf(os.getcwd(), _amazonfile1), '%s in the current directory' % _amazonfile1),
    (lambda key: _contentsOf(os.getcwd(), _amazonfile2), '%s in the current directory' % _amazonfile2),
    (lambda key: _contentsOf(os.environ.get('HOME', ''), _amazonfile1), '%s in your home directory' % _amazonfile1),
    (lambda key: _contentsOf(os.environ.get('HOME', ''), _amazonfile2), '%s in your home directory' % _amazonfile2),
    (lambda key: _contentsOf(_getScriptDir(), _amazonfile1), '%s in the amazon.py directory' % _amazonfile1),
    (lambda key: _contentsOf(_getScriptDir(), _amazonfile2), '%s in the amazon.py directory' % _amazonfile2)
    )

## administrative functions
def version():
    print """PyAmazon %(__version__)s
%(__copyright__)s
released %(__date__)s
""" % globals()
    
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
    raise NoLicenseKey, 'get a license key at http://www.amazon.com/webservices'

def setProxy(http_proxy):
    """set HTTP proxy"""
    global HTTP_PROXY
    HTTP_PROXY = http_proxy

def getProxy(http_proxy = None):
    """get HTTP proxy"""
    return http_proxy or HTTP_PROXY

def getProxies(http_proxy = None):
    http_proxy = getProxy(http_proxy)
    if http_proxy:
        proxies = {"http": http_proxy}
    else:
        proxies = None
    return proxies

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

class Bag: pass
    
def unmarshal(element):
    rc = Bag()
    if isinstance(element, minidom.Element) and (element.tagName == 'Details'):
        rc.URL = element.attributes["url"].value
    childElements = [e for e in element.childNodes if isinstance(e, minidom.Element)]
    if childElements:
        for child in childElements:
            key = child.tagName
            if hasattr(rc, key):
                if type(getattr(rc, key)) <> type([]):
                    setattr(rc, key, [getattr(rc, key)])
                setattr(rc, key, getattr(rc, key) + [unmarshal(child)])
            else:
                setattr(rc, key, unmarshal(child))
    else:
        rc = "".join([e.data for e in element.childNodes if isinstance(e, minidom.Text)])
        if element.tagName == 'SalesRank':
            rc = int(rc.replace(',', ''))
    return rc

def buildURL(search_type, keyword, product_line, type, page, license_key):
    url = "http://xml.amazon.com/onca/xml?v=1.0&f=xml&t=webservices-20"
    url += "&dev-t=%s" % license_key.strip()
    url += "&type=%s" % type
    if page:
        url += "&page=%s" % page
    if product_line:
        url += "&mode=%s" % product_line
    url += "&%s=%s" % (search_type, urllib.quote(keyword))
#    print url
    return url

## main functions
def search(search_type, keyword, product_line, type="heavy", page=None,
           license_key = None, http_proxy = None):
    """search Amazon

    You need a license key to call this function; see
    http://www.amazon.com/webservices
    to get one.  Then you can either pass it to
    this function every time, or set it globally; see the module docs for details.
    
    Parameters:
    keyword - keyword to search
    search_type - in (KeywordSearch, BrowseNodeSearch, AsinSearch, UpcSearch, AuthorSearch, ArtistSearch, ActorSearch, DirectorSearch, ManufacturerSearch, ListManiaSearch, SimilaritySearch)
    product_line - type of product to search for.  restrictions based on search_type
        UpcSearch - in (music, classical)
        AuthorSearch - must be "books"
        ArtistSearch - in (music, classical)
        ActorSearch - in (dvd, vhs, video)
        DirectorSearch - in (dvd, vhs, video)
        ManufacturerSearch - in (electronics, kitchen, videogames, software, photo, pc-hardware)
    http_proxy (optional) - address of HTTP proxy to use for sending and receiving SOAP messages

    Returns: list of Bags, each Bag may contain the following attributes:
      Asin - Amazon ID ("ASIN" number) of this item
      Authors - list of authors
      Availability - "available", etc.
      BrowseList - list of related categories
      Catalog - catalog type ("Book", etc)
      CollectiblePrice - ?, format "$34.95"
      ImageUrlLarge - URL of large image of this item
      ImageUrlMedium - URL of medium image of this item
      ImageUrlSmall - URL of small image of this item
      Isbn - ISBN number
      ListPrice - list price, format "$34.95"
      Lists - list of ListMania lists that include this item
      Manufacturer - manufacturer
      Media - media ("Paperback", "Audio CD", etc)
      NumMedia - number of different media types in which this item is available
      OurPrice - Amazon price, format "$24.47"
      ProductName - name of this item
      ReleaseDate - release date, format "09 April, 1999"
      Reviews - reviews (AvgCustomerRating, plus list of CustomerReview with Rating, Summary, Content)
      SalesRank - sales rank (integer)
      SimilarProducts - list of Product, which is ASIN number
      ThirdPartyNewPrice - ?, format "$34.95"
      URL - URL of this item
    """
    license_key = getLicense(license_key)
    url = buildURL(search_type, keyword, product_line, type, page, license_key)
    proxies = getProxies(http_proxy)
    u = urllib.FancyURLopener(proxies)
    usock = u.open(url)
    xmldoc = minidom.parse(usock)
    usock.close()
    data = unmarshal(xmldoc).ProductInfo
    if hasattr(data, 'ErrorMsg'):
        raise AmazonError, data.ErrorMsg
    else:
        return data.Details

def searchByKeyword(keyword, product_line="books", type="heavy", page=1, license_key=None, http_proxy=None):
    return search("KeywordSearch", keyword, product_line, type, page, license_key, http_proxy)

def browseBestSellers(browse_node, product_line="books", type="heavy", page=1, license_key=None, http_proxy=None):
    return search("BrowseNodeSearch", browse_node, product_line, type, page, license_key, http_proxy)

def searchByASIN(ASIN, type="heavy", license_key=None, http_proxy=None):
    return search("AsinSearch", ASIN, None, type, None, license_key, http_proxy)
  
def searchByUPC(UPC, type="heavy", license_key=None, http_proxy=None):
    return search("UpcSearch", UPC, None, type, None, license_key, http_proxy)
  
def searchByAuthor(author, type="heavy", page=1, license_key=None, http_proxy=None):
    return search("AuthorSearch", author, "books", type, page, license_key, http_proxy)

def searchByArtist(artist, product_line="music", type="heavy", page=1, license_key=None, http_proxy=None):
    if product_line not in ("music", "classical"):
        raise AmazonError, "product_line must be in ('music', 'classical')"
    return search("ArtistSearch", artist, product_line, type, page, license_key, http_proxy)

def searchByActor(actor, product_line="dvd", type="heavy", page=1, license_key=None, http_proxy=None):
    if product_line not in ("dvd", "vhs", "video"):
        raise AmazonError, "product_line must be in ('dvd', 'vhs', 'video')"
    return search("ActorSearch", actor, product_line, type, page, license_key, http_proxy)

def searchByDirector(director, product_line="dvd", type="heavy", page=1, license_key=None, http_proxy=None):
    if product_line not in ("dvd", "vhs", "video"):
        raise AmazonError, "product_line must be in ('dvd', 'vhs', 'video')"
    return search("DirectorSearch", director, product_line, type, page, license_key, http_proxy)

def searchByManufacturer(manufacturer, product_line="pc-hardware", type="heavy", page=1, license_key=None, http_proxy=None):
    if product_line not in ("electronics", "kitchen", "videogames", "software", "photo", "pc-hardware"):
        raise AmazonError, "product_line must be in ('electronics', 'kitchen', 'videogames', 'software', 'photo', 'pc-hardware')"
    return search("ManufacturerSearch", manufacturer, product_line, type, page, license_key, http_proxy)

def searchByListMania(listManiaID, type="heavy", page=1, license_key=None, http_proxy=None):
    return search("ListManiaSearch", listManiaID, None, type, page, license_key, http_proxy)

def searchSimilar(ASIN, type="heavy", page=1, license_key=None, http_proxy=None):
    return search("SimilaritySearch", ASIN, None, type, page, license_key, http_proxy)
