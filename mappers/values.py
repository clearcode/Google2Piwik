#
# Google2Piwik -  exporting Google Analytics to Piwik
#
# @link http://clearcode.cc/
# @license http://www.gnu.org/licenses/gpl-3.0.html GPL v3 or later
#

import cPickle

country_codes = cPickle.load( open("lib/countrycodes.pickle") )
region_codes = cPickle.load( open("lib/regioncodes.pickle") )
unknown = "UNK"

REFERER_TYPE_DIRECT_ENTRY = 1
REFERER_TYPE_SEARCH_ENGINE = 2
REFERER_TYPE_WEBSITE = 3

def browser_name(name):
    browsers = {"Firefox" : "FF",
                "Internet Explorer" : "IE",
                "Opera" : "OP",
                "Opera Mini" : "OP",
                "Safari" : "SF",
                "Chrome" : "CH",
                "Camino" : "CA",
                "Konqueror" : "KO",
                "Mozilla" : "MO",
                "Netscape" : "NS",
                "SeaMonkey" : "SM",
                "Firebird" : "FB",
                }
    return browsers.get(name,unknown)

def browser_version(browser, version):
    """ Function converts long version description i.e. 3.6.13 (Firefox) to 3.6 """

    b_versions = {"FF" : lambda x : '.'.join(x.split('.')[:2]),
                  "CH" : lambda x : '.'.join(x.split('.')[:2])}

    safari_webkit_versions = {"533.19.4" : "5.0.3", "533.18.5" : "5.0.2", "533.17.8" : "5.0.1",
                              "533.16" : "5.0", "531.22.7" : "4.0.5", "531.21.10" : "4.0.4",
                              "531.9.1" : "4.0.3", "530.19.1" : "4.0.2", "530.17" : "4.0.1",
                              "528.17" : "4.0", "528.16" : "4.0", "528.1.1" : "4.0"}

    if browser == "SF":
        return safari_webkit_versions.get(version, "")

    return b_versions.get(browser,(lambda x: x))(version)

def os_name(name, type=None):
    oss = {"BlackBerry" : "BLB",
           "iPod" : "IPD",
           "iPhone" : "IPH",
           "iPad" : "IPA",
           "FreeBSD" : "BSD",
           "Linux" : "LIN",
           "Macintosh" : "MAC",
           "Android" : "AND",
           "SymbianOS" : "SYM",
           }

    oss_typed = {"Windows" : {"Vista" : "WVI",
                              "Server 2003" : "WS3",
                              "XP" : "WXP",
                              "98" : "W98",
                              "2000" : "W2K",
                              "7"  : "WI7",
                              "NT" : "WNT",
                              "CE" : "WCE",
                              "ME" : "WME",
                              }}

    if not oss.get(name):
        return oss_typed.get(name,{}).get(type,unknown)
    else:
        return oss[name]

def referer_keyword(keyword):
    return "" if keyword == "(not set)" else keyword

def referer_url(name):
    if name == "(direct)":
        return ""
    elif name == "google":
        return name
    else:
        return "http://%s/" % name

def referer_type(source, keyword):
    if source == "(direct)":
        return REFERER_TYPE_DIRECT_ENTRY
    elif source == "google" or keyword != "":
        return REFERER_TYPE_SEARCH_ENGINE
    else:
        return REFERER_TYPE_WEBSITE

def referer_name(source, type):
    if type == REFERER_TYPE_SEARCH_ENGINE:
        try:
            return source.capitalize()
        except:
            return "Google"
    return "" if source == "(direct)" else source

def continent_name(name):
    continents = {"Europe" : "eur",
                  "Africa" : "afr",
                  "Asia" : "asi",
                  "Americas" : "amn",
                  "Oceania" : "oce",
                  }
    return continents.get(name,unknown.lower())

def country_name(name):
    try:
        return country_codes[name].lower()
    except:
        return "xx"

def visitor_localtime(google_value):
    return "%s:00:00" % google_value

def visitor_returning(google_value):
    return google_value == "Returning Visitor"

def flash_present(value):
    return value != "(not set)"

def java_present(value):
    return int(value == "Yes")

def region_name(value):
    try:
        return region_codes[value]
    except KeyError:
        return 'xx'
