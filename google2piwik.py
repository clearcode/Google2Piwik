#!/usr/bin/env python
# -*- coding: utf-8  -*-

#
# Google2Piwik -  exporting Google Analytics to Piwik
#
# @link http://clearcode.cc/
# @license http://www.gnu.org/licenses/gpl-3.0.html GPL v3 or later
#
## google2piwik v1.1, Copyright (C) 2011 by Clearcode (http://clearcode.cc)

# Tested to work on
#   Python 2.6.4 (r264:75706, Dec  7 2009, 18:45:15)
#   [GCC 4.4.1] on linux2

import gdata.analytics.client

from action import ActionManager
import mappers.dimensions as dims
import mappers.values as vals
import config
import sql

from distutils.version import StrictVersion
from itertools import chain, cycle
from hashlib import md5
import datetime
import random
import re
import sys

__VERBOSE__ = 0
SOURCE_APP_NAME = "Google2Piwik Exporter"
CURRENT_VERSION = 1.9

def VERBOSE(message,level=0, new_line=True):
    if __VERBOSE__ >= level: sys.stdout.write(message + '\n' if new_line else '')

def VER_FLUSHED(message, level=0):
    if __VERBOSE__ >= level:
        sys.stdout.write("\b"*len(message))
        sys.stdout.write(message)
        sys.stdout.flush()

def read_date(strdate):
    try:
        date_re = re.compile("(\d{4})-(\d{1,2})-(\d{1,2})")
        year, month, day = map(int, date_re.match(strdate).groups())
        return datetime.date(year,month,day)
    except AttributeError:
        raise Exception("Wrong date %s, check format (YYYY-MM-DD)" % strdate)
    except ValueError:
        raise Exception("Not valid date given %s" % strdate)

def export_period(start, end = None):
    global action_manager, hash_generator
    """ It's best not to export current day """
    if not end:
        end = datetime.date.today() - datetime.timedelta(days=1)

    print "Please wait, this process - depending on popularity of your site may take some time."
    fetcher = GoogleFeedFetcher( config.GOOGLE_TABLE_ID )
    currentdate = start
    enddate = end

    action_manager = create_action_manager( fetcher, str(currentdate), str(enddate) )
    hash_generator = create_visit_hash_generator( fetcher, str(currentdate), str(enddate) )

    while currentdate <= enddate:
        VERBOSE("Exporting %s" % currentdate)
        if sql.nb_visits_day(currentdate, config.ID_SITE) == 0:
            export_day(str(currentdate), fetcher)
        else:
            VERBOSE("Export failed. Visit log for that day is not empty.")
        currentdate += datetime.timedelta(days=1)

    sql.update_visit_actions(start, end + datetime.timedelta(days=1))
    sql.finalize()

def create_action_manager(fetcher, start, end):
    action_manager = ActionManager()
    VERBOSE("Fetching paths and titles of pages.")
    fetcher.FeedFetchSpecial("ga:pagePath,ga:pageTitle", "ga:pageviews", start, end)
    for act in fetcher.FeedToDict():
        action_manager.add_action(act["ga:pagePath"], act["ga:pageTitle"])

    return action_manager

def create_visit_hash_generator(fetcher, start, end):
    hash_generator = VisitHashGenerator()

    VERBOSE("Fetching number of unique users in days and months.")
    fetcher.FeedFetchSpecial("", "ga:visitors", start, end)
    hash_generator.total = int(fetcher.FeedToDict()[0]["metric"]["ga:visitors"])

    fetcher.FeedFetchSpecial("ga:date", "ga:visitors", start, end)
    for entry in fetcher.FeedToDict():
        date = entry["ga:date"]
        year, month, day = date[:4], date[4:6], date[6:8]
        hash_generator.date_unique["-".join([year,month,day])] = int(entry["metric"]["ga:visitors"])

    fetcher.FeedFetchSpecial("ga:month,ga:year", "ga:visitors", start, end)
    for entry in fetcher.FeedToDict():
        month, year = entry["ga:month"], entry["ga:year"]
        hash_generator.month_unique["-".join([year,month])] = int(entry["metric"]["ga:visitors"])
    return hash_generator

def export_day(day, fetcher):
    day_export_start = datetime.datetime.now()
    simulator = VisitSimulator(fetcher.getVisits(day), day)

    if simulator.visit_limit == 0:
        return #nothing to export

    VERBOSE("VISIT: Initialize", 2)
    simulator.initialize(fetcher, "ga:latitude,ga:longitude,ga:hour,ga:flashVersion,ga:javaEnabled,ga:language,ga:screenResolution", "ga:visits")

    for i, d in enumerate(dims.DVALS[CURRENT_VERSION]):
        VERBOSE("VISIT: Fetch " + str(i), 2)
        simulator.update(fetcher, d, "ga:visits")

    """
    Getting landing and exit pages
    """
    VERBOSE("VISIT: Fetch landing, exits", 2)
    simulator.update(fetcher, "ga:exitPagePath,ga:landingPagePath,ga:latitude,ga:longitude,ga:hour","ga:entrances")
    VERBOSE("ACTION: Export paths", 2)
    action_manager.export(config.SITE_BASE_URL, CURRENT_VERSION)
    VERBOSE("ACTION: Completed", 2)
    additional  = {"idsite" : config.ID_SITE, "visit_server_date" : day}

    simulator.finalize(additional)

    """
    Export views to log_view
    """
    VERBOSE("VISIT: Export vitis", 2)
    for v in simulator.visits:
        v.idvisit = sql.insert_log_visit(v.visit_log, CURRENT_VERSION)
    VERBOSE("VISIT: Completed", 2)

    """
    Simulate actions by taking every page (with pageviews and timeOnPage info) and inserting to log_link_visit_action
    """
    fetcher.FeedFetch("ga:pagePath","ga:pageviews,ga:timeOnPage,ga:bounces", day)
    pageViewDict = fetcher.FeedToDict()
    for action in pageViewDict:
        real_action = action_manager[action["ga:pagePath"]]
        real_action.pageviews = int(action["metric"]["ga:pageviews"])
        real_action.timeleft = float(action["metric"]["ga:timeOnPage"])
        real_action.bounces = int(action["metric"]["ga:bounces"])
        real_action.average = real_action.timeleft / real_action.pageviews if real_action.pageviews > 0 else real_action.timeleft

        for v in xrange(len(simulator.visits)):
            visit = simulator.visits[v]
            if real_action.bounces == 0: continue
            if visit.google_data.get("ga:landingPagePath") == real_action.path and not visit.bounce:
                real_action.bounces -= 1
                visit.bounce = True
                try:
                    sql.insert_log_visit_action((visit.idvisit, visit.get_final_value("idcookie"),
                                                 visit.get_final_value("visit_server_date"), config.ID_SITE,
                                                 real_action.id_action_url, real_action.id_action_url,
                                                 real_action.id_action_name, real_action.average))
                except Exception, e:
                    print e


    for action in pageViewDict:
        real_action = action_manager[action["ga:pagePath"]]
        real_action.pageviews = int(action["metric"]["ga:pageviews"])
        real_action.timeleft = float(action["metric"]["ga:timeOnPage"])
        real_action.bounces = int(action["metric"]["ga:bounces"])
        real_action.average = real_action.timeleft / real_action.pageviews if real_action.pageviews > 0 else real_action.timeleft

        candicates = filter(lambda v : not v.bounce, simulator.visits)
        for view in xrange(real_action.pageviews - real_action.bounces):
            visit = random.choice(candicates)
            try:
                sql.insert_log_visit_action((visit.idvisit, visit.get_final_value("idcookie"),
                                             visit.get_final_value("visit_server_date"), config.ID_SITE,
                                             real_action.id_action_url, real_action.id_action_url,
                                             real_action.id_action_name, real_action.average))
            except Exception, e:
                print e


    simulated_unique = len(set([visit.visit_log["config_md5config"] for visit in simulator.visits]))
    VERBOSE("Number of simulated unique visits:\t%s" % simulated_unique)

    VERBOSE("Real number of unique visits:\t%s" % fetcher.getUniqueVisitors(day))
    VERBOSE("DAY EXPORT TIME (in seconds): %s" % (datetime.datetime.now() - day_export_start).seconds,2)
    VERBOSE("")

    del simulator

class Visit(object):
    """
    This object represents single visit on website. Contains methods updating
    values from Google Analytics and changing them into Piwik Visit values.

    Data taken from Google Analytics is contained in `google_data` dict.
    Piwik representation of Visit is stored in `visit_log` dict.
    """
    def __init__(self, params={}):
        self.google_data = params
        self.visit_log = {}
        self.nb_updates = 0
        self.bounce = False

    def __repr__(self):
        return str(self.visit_log)

    def first(self, params):
        self.google_data = params
        self.nb_updates += 1

    def update(self, params):
        for key in params:
            if not key in self.google_data:
                self.google_data[key] = params[key]
        self.nb_updates += 1

    def compliance(self, other_params):
        compliance_factor = 0
        for key, value in self.google_data.iteritems():
            compliance_factor += other_params.get(key) == value

        return compliance_factor

    def finalize(self, additional):
        """
        This method changes Google Analytics fields and values into Piwik's and stores them in `visit_log` dictionary.
        """
        self.visit_log.update(additional)

        stable = ["ga:screenResolution", "ga:language", "ga:visitLength", "total_actions", "ga:visitCount", "ga:daysSinceLastVisit", "ga:city"]
        for stable_dim in stable:
            self.visit_log[dims.DMAP[stable_dim]] = self.google_data.get(stable_dim) or 0
        self.set_final("ga:visitorType", vals.visitor_returning)
        self.set_final("ga:flashVersion", vals.flash_present)
        self.set_final("ga:javaEnabled", vals.java_present)
        self.set_final("ga:hour", vals.visitor_localtime)
        self.set_final("ga:browser", vals.browser_name)
        self.set_final("ga:country", vals.country_name)
        self.set_final("ga:keyword", vals.referer_keyword)
        self.cut_final("ga:keyword", 255)
        self.set_final("ga:source", vals.referer_url)
        self.set_final("ga:continent", vals.continent_name)
        self.set_final("ga:region", vals.region_name)
        self.set_final_value("referer_type", vals.referer_type(self.google_data.get("ga:source"),
                                                               self.get_final_value("ga:keyword")))

        self.set_final_value("referer_name", vals.referer_name(self.google_data.get("ga:source"),
                                                               self.get_final_value("referer_type")))
        self.cut_final("referer_name", 70)

        self.set_final_value("ga:browserVersion", vals.browser_version(self.get_final_value("ga:browser"),
                                                  self.google_data.get("ga:browserVersion")))
        self.cut_final("ga:browserVersion", 20)

        try:
            landing_act_id = action_manager[self.google_data["ga:landingPagePath"]].id_action_url
        except:
            landing_act_id = 0

        self.set_final_value("ga:landingPagePath", landing_act_id)

        try:
            exit_action_id = action_manager[self.google_data["ga:exitPagePath"]].id_action_url
        except:
            exit_action_id = 0
        self.set_final_value("ga:exitPagePath", exit_action_id)

        self.visit_log["visit_first_action_time"] = self.visit_log["visit_last_action_time"] = \
                "%s %s" % (self.visit_log["visit_server_date"], self.visit_log["visitor_localtime"])

        os = vals.os_name(self.google_data.get("ga:operatingSystem"), self.google_data.get("ga:operatingSystemVersion"))

        self.set_final_value("ga:operatingSystem", os)
        self.set_final_value("md5config", hash_generator.get_md5(self.get_final_value("visit_server_date")))
        self.set_final_value("idcookie", md5(self.get_final_value("md5config")).hexdigest())

    def set_final(self, google_field, function):
        self.visit_log[dims.DMAP[google_field]] = function(self.google_data.get(google_field))

    def set_final_value(self, google_field, value):
        """
        Shortcut for setting value to corresponding google_field
        """
        self.visit_log[dims.DMAP[google_field]] = value

    def get_final_value(self,google_field):
        """
        Shortcut for getting value of corresponding google_field
        """
        return self.visit_log[dims.DMAP[google_field]]

    def cut_final(self, google_field, max_length):
        value = self.get_final_value(google_field)
        if isinstance(value,str):
           self.set_final_value(google_field, value[:max_length])


class VisitSimulator(object):
    def __init__(self, nb_visits, day):
        self.visit_limit = int(nb_visits)
        self.visits = [Visit() for v in xrange(self.visit_limit)]
        self.indexed = {}
        self.nb_updates = 0
        self.day = day

    def index_visit(self, visit, latitude, longitude, hour):
        if latitude in self.indexed:
            if longitude in self.indexed[latitude]:
                if hour in self.indexed[latitude][longitude]:
                    self.indexed[latitude][longitude][hour].append(visit)
                else:
                    self.indexed[latitude][longitude][hour] = [visit]
            else:
                self.indexed[latitude][longitude] = {hour : [visit]}
        else:
            self.indexed[latitude] = {longitude:{hour : [visit]}}

    def modify(self, visit_google_data):
        """
        This method scans visits for most suitable with visit_google_data.
        Use queries that contains common dimensions (like latitude and longitude), so
        visit that covers most of values gets update.

        During one VisitSimulator.update one visit can be updated only once
        """
        max, visit_index = -1, None
        lat, lon, hour = visit_google_data.get("ga:latitude"), visit_google_data.get("ga:longitude"), visit_google_data.get("ga:hour")
        if not (lat and lon and hour):
            for v in xrange(self.visit_limit):
                if self.visits[v].nb_updates <= self.nb_updates:
                    visit_compliance = self.visits[v].compliance(visit_google_data)
                    if visit_compliance >= max:
                        max, visit_index = visit_compliance, v
        else:
          try:
            for visit in self.indexed[lat][lon][hour]:
                if visit.nb_updates <= self.nb_updates:
                    visit_compliance = visit.compliance(visit_google_data)
                    if visit_compliance >= max:
                        max, visit_index = visit_compliance, self.visits.index(visit)
          except KeyError:
            for v in xrange(self.visit_limit):
                if self.visits[v].nb_updates <= self.nb_updates:
                    visit_compliance = self.visits[v].compliance(visit_google_data)
                    if visit_compliance >= max:
                        max, visit_index = visit_compliance, v

        if visit_index != None:
            self.visits[visit_index].update(visit_google_data)

    def initialize(self, fetcher, dimensions, metrics):
        """
        Method used to populate visits with basic dimensions.

        metrics parameter should contain only one value in this case.
            eg. ga:visits
        """
        fetcher.FeedFetch(dimensions, metrics, self.day)
        index = 0
        for visit in fetcher.FeedToDict():
            nb_copies = int(visit['metric'][metrics])
            del visit['metric']
            for i in xrange(nb_copies):
                self.visits[index].first(visit)
                self.index_visit(self.visits[index], visit["ga:latitude"], visit["ga:longitude"], visit["ga:hour"])
                index += 1
        self.nb_updates += 1

    def update(self, fetcher, dimensions, metrics):
        """
        Method to fetch and update visits with new dimensions.
        """
        max = self.visit_limit
        step = 1
        modified = 0
        current_step = 0
        fetcher.FeedFetch(dimensions, metrics, self.day)
        last_update = datetime.datetime.now()
        for visit in fetcher.FeedToDict():
            nb_copies = int(visit['metric'][metrics])
            del visit['metric']
            for i in xrange(nb_copies):
                self.modify(visit)
            modified += nb_copies
            if (modified * 1.0 / max) * 100 > current_step:
                timeleft = ((100-current_step)/step)*(datetime.datetime.now() - last_update).seconds or (100 - current_step)
                VER_FLUSHED("%3s perc. finished. estimated %6d seconds left." % (current_step, timeleft), 2)
                last_update = datetime.datetime.now()
                current_step += step

        self.nb_updates += 1
        VERBOSE("", 2)

    def finalize(self, additional):
        """
        Finalizes every visit ( with additional dictionary ).
        """
        for visit in self.visits:
            visit.finalize(additional)

class VisitHashGenerator(object):
    """
    This class is used to simulate visitors uniqueness.
    """
    def __init__(self):
        self.total = 0
        self.random_prefix = "Google2Piwik"
        self.date_unique = {}
        self.month_unique = {}
        self.basket = []
        self.current_month_year = "0000-00"
        self.current_date = "0000-00-00"

    def get_md5(self, date):
        """
        date should be in form : YYYY-MM-DD
        """
        if date != self.current_date:
            self.current_date = date
            self.populate_current_date()

        md5string = "%s;%s" % (self.random_prefix, self.date_basket.next())
        return md5(md5string).hexdigest()

    def populate_current_date(self):
        if self.current_date[:7] != self.current_month_year:
            self.current_month_year = self.current_date[:7]
            self.populate_current_month()

        not_yet_taken = filter(lambda h: not h in self.month_taken, self.month_basket)
        if len(not_yet_taken) == 0:
            self.date_basket = cycle(random.sample(self.month_basket, self.date_unique[self.current_date]))
        elif len(not_yet_taken) < self.date_unique[self.current_date]:
            self.month_taken.update(not_yet_taken)
            self.date_basket = chain(not_yet_taken, cycle(random.sample(self.month_basket, self.date_unique[self.current_date] - len(not_yet_taken))) )
        else:
            chosen = random.sample(not_yet_taken, self.date_unique[self.current_date])
            self.month_taken.update(chosen)
            self.date_basket = cycle(chosen)

    def populate_current_month(self):
        self.month_basket  = xrange(self.month_unique[self.current_month_year])
        self.month_taken = set()

class GoogleFeedFetcher(object):
    """
    Class used to retrieve data from Google.
    Contains methods to authenticate user.
    """

    def __init__(self, table):
        self.client = gdata.analytics.client.AnalyticsClient(source=SOURCE_APP_NAME)
        try:
            self.client.ClientLogin(config.GOOGLE_USER,config.GOOGLE_PASS,SOURCE_APP_NAME)
        except gdata.client.BadAuthentication:
            raise Exception('Invalid Google credentials given.')
        except gdata.client.Error:
            raise Exception('Login Error')

        self.table_id = table

    def FeedFetchSpecial(self, dimensions, metrics, day_start, day_end):
        data_query = gdata.analytics.client.DataFeedQuery({
                            'ids': self.table_id,
                            'start-date': day_start,
                            'end-date': day_end,
                            'dimensions': dimensions,
                            'metrics': metrics,
                            'max-results': '10000',
                            'key': config.GOOGLE_KEY})
        self.feed = self.client.GetDataFeed(data_query)

    def FeedFetch(self, dimensions, metrics, day):
        data_query = gdata.analytics.client.DataFeedQuery({
                            'ids': self.table_id,
                            'start-date': day,
                            'end-date': day,
                            'dimensions': dimensions,
                            'metrics': metrics,
                            'max-results': '10000',
                            'key': config.GOOGLE_KEY})
        self.feed = self.client.GetDataFeed(data_query)

    def getUniqueVisitors(self, day):
        self.FeedFetch("", "ga:visitors", day)
        try:
            return self.feed.entry[0].metric[0].value
        except:
            return 0

    def getVisits(self, day):
        self.FeedFetch("", "ga:visits", day)
        try:
            return self.feed.entry[0].metric[0].value
        except:
            return 0

    def checkAccess(self):
        self.FeedFetch("", "ga:visits", datetime.date.today())
        self.feed.entry[0].metric[0].value
        return True


    def FeedToDict(self, take_dimension = True, take_metric = True):
        result = []
        for entry in self.feed.entry:
            result.append(self.EntryToDict(entry, take_dimension, take_metric))

        return result

    def PrintTableIDs(self):
        account_query = gdata.analytics.client.ProfileQuery('~all', '~all',
                                                    {'key': config.GOOGLE_KEY})
        table_feed = self.client.GetManagementFeed(account_query)
        print "Google Analytics Table IDs for your Account\n"
        for entry in table_feed.entry:
            print "Site: %30s \t table_id: %s" % (entry.GetProperty('ga:profileName').value,
                                                    entry.GetProperty('dxp:tableId').value)

    def GetTableIDs(self):
        account_query = gdata.analytics.client.ProfileQuery('~all', '~all',
                                                    {'key': config.GOOGLE_KEY})
        table_feed = self.client.GetManagementFeed(account_query)
        return [(entry.GetProperty('ga:profileName').value, entry.GetProperty('dxp:tableId').value) for entry in table_feed.entry]

    def EntryToDict(self, entry, take_dimension = True, take_metric = False):
        result = {}
        if take_dimension:
            for dim in entry.dimension:
                result[dim.name] = dim.value
        if take_metric:
            result["metric"] = {}
            for met in entry.metric:
                result["metric"][met.name] = met.value

        return result

if __name__ == '__main__':
    import optparse
    import sys
    parser = optparse.OptionParser(version="google2piwik 1.0")
    parser.add_option("-v", "--verbose", dest="verbose", default=0,
                    action="store",type="int", help="show additional information during export, 1 - normal verbose, 2 - developer verbose")
    parser.add_option("-f", "--config-file", dest="config_file", default="google2piwik.conf", metavar="FILE",
                    help="set configuration file, default \"google2piwik.conf\"")
    parser.add_option("-S", "--start-date", dest="start_date", metavar="DATE",
                    help="set start date of export, DATE should be in form YYYY-MM-DD")
    parser.add_option("-E", "--end-date", dest="end_date", default=None, metavar="DATE",
                    help="""set end date of export, this parameter is optional.
                         If not specified - yesterday's date will be used. DATE should be in form YYYY-MM-DD""")
    parser.add_option("-c", "--check", dest="check", default=False, action="store_true",
                    help="checks if configuration is valid, i.e. connects to MySQL database and Google account")
    parser.add_option("-u", "--update-visit", dest="update_visit_actions", default=False, action="store_true",
                    help="updates visit total actions field (for some cases needed after export)")
    parser.add_option("-p", "--print-table-ids", dest="print_table_id", default=False, action="store_true",
                    help="prints table_id for every site on your Google Analytics Account")
    parser.add_option("-C", "--clear-archives", dest="clear_archives", default=False, action="store_true",
                    help="Drops all archive tables in piwik database")
    (options, args) = parser.parse_args(sys.argv)

    __VERBOSE__ = options.verbose

    if options.print_table_id:
        config.read_config(options.config_file)
        fetcher = GoogleFeedFetcher("")
        fetcher.PrintTableIDs()
        exit()

    if options.clear_archives:
        try:
            config.read_config(options.config_file)
            sql.initialize(config.MYSQL_CREDENTIALS)
        except:
            "Please check your config file and run your script again"
            exit()
        print "Clearing archive tables"
        sql.clear_archives()
        print "Please go to your Piwik installation folder and run misc/cron/archive.sh script."
        exit()

    if options.check:
        print "Checking configuration file:",
        try:
            config.read_config(options.config_file)
            print "[OK]"
        except:
            print "[FAILED]"
            exit()
        print
        print "Checking Google Analytics"

        #if not config.GOOGLE_USER.split("@")[1] == "gmail.com":
            #print "Your e-mail address should be ending with @gmail.com"
            #exit()

        print "Attempting login:",
        try:
            fetcher = GoogleFeedFetcher( config.GOOGLE_TABLE_ID )
            print "[OK]"
        except:
            print "[FAILED]"


        print "Simple query on table:",
        try:
            fetcher.checkAccess()
            print "[OK]"
        except IndexError, e:
            print "[OK]"
        except:
            print "[FAILED]"

        print
        print "Checking MySQL Access"
        print "Initialize database connection:",
        try:
            sql.initialize(config.MYSQL_CREDENTIALS)
            print "[OK]"
        except:
            print "[FAILED]"
            exit()

        print "Checking tables:",
        failed_tables = sql.check_tables(config.MYSQL_CREDENTIALS["table_prefix"])
        if len(failed_tables) == 0:
            print "[OK]"
        else:
            print "[FAILED]"
            print "Tables - %s doesn't exist." % ", ".join(failed_tables)

        print "Checking site:",
        try:
            sql.check_site(config.ID_SITE)
            print "[OK]"
        except:
            print "[FAILED], site with idsite = %s wasn't found" % config.ID_SITE
    else:
        config.read_config(options.config_file)
        if not (options.start_date or config.CONFIG_START):
            print "Start date parameter is required. For more info type ./google2piwik.py -h"
            exit()
        start_date = read_date(options.start_date or config.CONFIG_START)
        end_date = None if not (options.end_date or config.CONFIG_END) else read_date(options.end_date or config.CONFIG_END)
        sql.initialize(config.MYSQL_CREDENTIALS)

        CURRENT_VERSION = sql.get_version(config.MYSQL_CREDENTIALS["table_prefix"])
        if StrictVersion(CURRENT_VERSION) < StrictVersion('1.9'):
            CURRENT_VERSION = 1.8
        else:
            CURRENT_VERSION = 1.9

        if options.update_visit_actions:
            sql.update_total_visit_actions()
            exit()

        sql.update_site_ts_created(config.ID_SITE, start_date)

        export_period(start_date, end_date)

        sql.clear_archives()
        print "Please go to your Piwik installation folder and run misc/cron/archive.sh script."
