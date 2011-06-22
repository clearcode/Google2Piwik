#
# Google2Piwik -  exporting Google Analytics to Piwik
#
# @link http://clearcode.cc/
# @license http://www.gnu.org/licenses/gpl-3.0.html GPL v3 or later
#

import ConfigParser

ID_SITE = 1
SITE_BASE_URL   = ""
GOOGLE_TABLE_ID = ""
MYSQL_CREDENTIALS = {}
GOOGLE_USER = ""
GOOGLE_PASS = ""

def read_config(config_file):
    global ID_SITE, SITE_BASE_URL, GOOGLE_TABLE_ID
    global MYSQL_CREDENTIALS, GOOGLE_USER, GOOGLE_PASS
    global CONFIG_START, CONFIG_END

    conf = ConfigParser.RawConfigParser()
    if len(conf.read(config_file)) == 0:
        raise Exception("Configuration file not found")
    
    ID_SITE = conf.get("piwik", "site_id")
    SITE_BASE_URL = conf.get("piwik", "site_url")
    
    GOOGLE_TABLE_ID = conf.get("google", "table_id")
    GOOGLE_USER = conf.get("google", "user_login")
    GOOGLE_PASS = conf.get("google", "user_pass")
    CONFIG_START= conf.get("export", "start")
    CONFIG_END  = conf.get("export", "end")
    
    MYSQL_CREDENTIALS = dict(conf.items("mysql"))
