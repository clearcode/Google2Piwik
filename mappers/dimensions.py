#
# Google2Piwik -  exporting Google Analytics to Piwik
#
# @link http://clearcode.cc/
# @license http://www.gnu.org/licenses/gpl-3.0.html GPL v3 or later
#

"""
This file contains field mapping from Google Analytics to Piwik.
"""

DMAP =             {"ga:browser" : "config_browser_name",
                    "ga:browserVersion" : "config_browser_version",
                    "ga:continent" : "location_continent",
                    "ga:country" : "location_country",
                    "ga:flashVersion" : "config_flash",
                    "ga:javaEnabled" : "config_java",
                    "ga:screenResolution": "config_resolution",
                    "ga:language" : "location_browser_lang",
                    "ga:visitLength" : "visit_total_time",
                    "ga:visitorType" : "visitor_returning",
                    "ga:operatingSystem" : "config_os",
                    "ga:hour" : "visitor_localtime",
                    "ga:exitPagePath" : "visit_exit_idaction_url",
                    "ga:landingPagePath" : "visit_entry_idaction_url",
                    "ga:source" : "referer_url",
                    "ga:keyword" : "referer_keyword",
                    
                    "referer_type" : "referer_type",
                    "referer_name" : "referer_name",
                    
                    "visit_server_date" : "visit_server_date",
                    "total_actions" : "visit_total_actions",
                    "md5config" : "config_md5config",
                    "idcookie" : "visitor_idcookie"
                    }
