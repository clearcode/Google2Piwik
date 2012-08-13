#
# Google2Piwik -  exporting Google Analytics to Piwik
#
# @link http://clearcode.cc/
# @license http://www.gnu.org/licenses/gpl-3.0.html GPL v3 or later
#

import ConfigParser

ID_SITE = ""
SITE_BASE_URL   = ""
GOOGLE_TABLE_ID = ""
MYSQL_CREDENTIALS = {}
GOOGLE_USER = ""
GOOGLE_PASS = ""
GOOGLE_KEY = ""
CONFIG_START = ""
CONFIG_END = ""

def read_config(config_file):
    global ID_SITE, SITE_BASE_URL, GOOGLE_TABLE_ID
    global MYSQL_CREDENTIALS, GOOGLE_USER, GOOGLE_PASS, GOOGLE_KEY
    global CONFIG_START, CONFIG_END

    conf = ConfigParser.RawConfigParser()
    if len(conf.read(config_file)) == 0:
        raise Exception("Configuration file not found")
    ID_SITE = conf.get("piwik", "site_id")
    SITE_BASE_URL = conf.get("piwik", "site_url")
    
    GOOGLE_TABLE_ID = conf.get("google", "table_id")
    GOOGLE_USER = conf.get("google", "user_login")
    GOOGLE_PASS = conf.get("google", "user_pass")
    GOOGLE_KEY = conf.get("google", "api_key")
    CONFIG_START= conf.get("export", "start")
    CONFIG_END  = conf.get("export", "end")
    
    MYSQL_CREDENTIALS = dict(conf.items("mysql"))

def write_config(config_file):
    global ID_SITE, SITE_BASE_URL, GOOGLE_TABLE_ID
    global MYSQL_CREDENTIALS, GOOGLE_USER, GOOGLE_PASS
    global CONFIG_START, CONFIG_END
    
    conf = ConfigParser.RawConfigParser()
    conf.add_section("google")
    conf.set("google", "user_login", GOOGLE_USER)
    conf.set("google", "user_pass", GOOGLE_PASS)
    conf.set("google", "table_id", GOOGLE_TABLE_ID)
    conf.set("google", "api_key", GOOGLE_KEY)
    
    conf.add_section("mysql")
    conf.set("mysql", "db", MYSQL_CREDENTIALS["db"])
    conf.set("mysql", "host", MYSQL_CREDENTIALS["host"])
    conf.set("mysql", "port", MYSQL_CREDENTIALS["port"])
    conf.set("mysql", "user", MYSQL_CREDENTIALS["user"])
    conf.set("mysql", "passwd", MYSQL_CREDENTIALS["passwd"])
    conf.set("mysql", "table_prefix", MYSQL_CREDENTIALS["table_prefix"])
    
    conf.add_section("export")
    conf.set("export", "start", CONFIG_START)
    conf.set("export", "end", CONFIG_END)
    
    conf.add_section("piwik")
    conf.set("piwik", "site_id", ID_SITE)
    conf.set("piwik", "site_url", SITE_BASE_URL)
    
    with open(config_file, "w") as fconf:
        conf.write(fconf)
