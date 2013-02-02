#!/usr/bin/env python
# -*- coding: utf-8  -*-
#
# Google2Piwik -  exporting Google Analytics to Piwik
#
# @link http://clearcode.cc/
# @license http://www.gnu.org/licenses/gpl-3.0.html GPL v3 or later
#

import MySQLdb
import warnings
import datetime


warnings.filterwarnings("ignore", category=MySQLdb.Warning)

T_LOGVA = "log_link_visit_action"
T_LOGA  = "log_action"
T_LOGV  = "log_visit"
T_SITE  = "site"

INSERT_LOG_VISIT_ACTION = """INSERT INTO {{LVA}} (idvisit, idvisitor, server_time, idsite, idaction_url,
                                                  idaction_url_ref, idaction_name, time_spent_ref_action, idaction_name_ref)
                                          VALUES (%s, binary(unhex(substring(%s,1,16))), %s, %s, %s, %s, %s, %s, 0) """


LOGV_TEMPLATE = u""" INSERT INTO {{LV}} (idsite, visitor_localtime, idvisitor, visitor_returning, config_id,
                                                   visit_first_action_time, visit_last_action_time,
                                                   visit_exit_idaction_url, visit_entry_idaction_url, visit_total_actions,
                                                   visit_total_time, referer_type, referer_name, visit_goal_converted,
                                                   referer_url, referer_keyword, config_os, config_browser_name,
                                                   config_browser_version, config_resolution, config_pdf, config_flash,
                                                   config_java, config_director, config_quicktime, config_realplayer,
                                                   config_windowsmedia, config_gears, config_silverlight, config_cookie,
                                                   location_ip, location_browser_lang, location_country{0},
                                                   visitor_count_visits, visitor_days_since_last, visitor_days_since_first,
                                                   visit_exit_idaction_name, visit_entry_idaction_name{1})

                                        VALUES   ( %(idsite)s, %(visitor_localtime)s, binary(unhex(substring(%(visitor_idcookie)s,1,16))),
                                                   %(visitor_returning)s, binary(unhex(substring(%(config_md5config)s,1,16))),
                                                   %(visit_first_action_time)s, %(visit_last_action_time)s,
                                                   %(visit_exit_idaction_url)s, %(visit_entry_idaction_url)s, %(visit_total_actions)s,
                                                   %(visit_total_time)s, %(referer_type)s, %(referer_name)s, 0,
                                                   %(referer_url)s, %(referer_keyword)s, %(config_os)s, %(config_browser_name)s,
                                                   %(config_browser_version)s, %(config_resolution)s, 0, %(config_flash)s,
                                                   %(config_java)s, 0, 0, 0, 0, 0, 0, 0, 0,
                                                   %(location_browser_lang)s, %(location_country)s{2},
                                                   %(visitor_count_visits)s, %(visitor_days_since_last)s, 0, 0, 0{3}) """

INSERT_LOG_VISIT = {
    1.9: (", location_city", ", location_region", ", %(location_city)s", ", %(location_region)s"),
    1.8: (", location_continent", "", ", %(location_continent)s", "")
}

INSERT_LOG_ACTION = {
    1.8: "INSERT INTO {{LA}} (name, hash, type) VALUES (%s, %s, %s) ",
    1.9: "INSERT INTO {{LA}} (name, hash, type, url_prefix) VALUES (%s, %s, %s, %s)"
}


SELECT_NB_VISITS = "SELECT count(*) FROM {{LV}} WHERE visitor_localtime = %s and idsite = %s"


def initialize(mysql_data):
    global T_LOGVA, T_LOGA, T_LOGV, T_SITE
    global db, cursor
    global INSERT_LOG_VISIT_ACTION, INSERT_LOG_ACTION, INSERT_LOG_VISIT
    global SELECT_NB_VISITS
    global LOGV_TEMPLATE
    prefix = mysql_data["table_prefix"]
    T_LOGVA = "%s_%s" % (prefix, T_LOGVA) if prefix else T_LOGVA
    T_LOGA  = "%s_%s" % (prefix, T_LOGA) if prefix else T_LOGA
    T_LOGV  = "%s_%s" % (prefix, T_LOGV) if prefix else T_LOGV
    T_SITE  = "%s_%s" % (prefix, T_SITE) if prefix else T_SITE

    INSERT_LOG_VISIT_ACTION = INSERT_LOG_VISIT_ACTION.replace("{{LVA}}", T_LOGVA)
    SELECT_NB_VISITS        = SELECT_NB_VISITS.replace("{{LV}}", T_LOGV)

    LOGV_TEMPLATE = LOGV_TEMPLATE.replace("{{LV}}", T_LOGV)
    for k, v in INSERT_LOG_VISIT.iteritems():
        INSERT_LOG_VISIT[k] = LOGV_TEMPLATE.format(*INSERT_LOG_VISIT[k])

    for k, v in INSERT_LOG_ACTION.iteritems():
        INSERT_LOG_ACTION[k] = INSERT_LOG_ACTION[k].replace("{{LA}}", T_LOGA)

    db = init_db(mysql_data)
    db.set_character_set('utf8')
    cursor = db.cursor()


def insert_log_action(values, version):
    values_no = INSERT_LOG_ACTION[version].count('%s')
    # from IPython import embed; embed();
    cursor.execute(INSERT_LOG_ACTION[version], values[:values_no])
    return cursor.lastrowid


def insert_log_visit(values, version):
    try:
        cursor.execute(INSERT_LOG_VISIT[version], values)
    except:
        pass
    return cursor.lastrowid


def insert_log_visit_action(values):
    cursor.execute(INSERT_LOG_VISIT_ACTION, values)
    return cursor.lastrowid


def init_db(mysql_data):
    try:
        db = MySQLdb.connect(mysql_data["host"], mysql_data["user"], mysql_data["passwd"],
                             mysql_data["db"], int(mysql_data["port"]))
        return db
    except MySQLdb.OperationalError, e:
        print "There was problem connecting to your MySQL Service:"
        print "Exception: ", e
        exit()


def test_db(mysql_data):
    global db, cursor
    db = MySQLdb.connect(mysql_data["host"], mysql_data["user"], mysql_data["passwd"],
                         mysql_data["db"], int(mysql_data["port"]))
    db.set_character_set('utf8')
    cursor = db.cursor()


def get_sites(prefix):
    select_site_sql = "SELECT idsite, name, main_url from {SITE_TABLE}".format(SITE_TABLE=prefix + "_" + T_SITE)
    cursor.execute(select_site_sql)
    return [{"id": id, "name": name, "url": url} for (id, name, url) in cursor.fetchall()]


def get_version(prefix):
    t_option = "%s_option" % (prefix) if prefix else "option"
    select_version_sql = "SELECT option_value FROM {table} WHERE option_name = 'version_core'".format(table=t_option)
    cursor.execute(select_version_sql)
    version = cursor.fetchone()[0]
    return version


def check_tables(table_prefix):
    global cursor
    failed = []
    for table in ["log_action", "log_visit", "log_link_visit_action"]:
        table_name = table if not table_prefix else "%s_%s" % (table_prefix, table)
        try:
            cursor.execute("SELECT * FROM {name}".format(name=table_name))
        except MySQLdb.ProgrammingError:
            failed.append(table_name)
    return failed


def check_site(site_id):
    select_site_sql = "SELECT count(*) from {SITE_TABLE} WHERE idsite = %s".format(SITE_TABLE=T_SITE)
    cursor.execute(select_site_sql, site_id)
    return cursor.fetchone()[0] == 1


def update_site_ts_created(site_id, date):
    current_start = datetime.datetime(date.year, date.month, date.day)

    select_site_sql = "SELECT ts_created from {SITE_TABLE} WHERE idsite = %s".format(SITE_TABLE=T_SITE)
    cursor.execute(select_site_sql, site_id)
    ts_created = cursor.fetchone()[0]

    if ts_created > current_start:
        update_site_sql = "UPDATE {SITE_TABLE} SET ts_created = %s WHERE idsite = %s".format(SITE_TABLE=T_SITE)
        cursor.execute(update_site_sql, (current_start, site_id))


def nb_visits_day(date, site_id):
    cursor.execute(SELECT_NB_VISITS, (date, site_id))
    return cursor.fetchone()[0]


def update_visit_actions(start_date, end_date):
    raw_sql = """UPDATE {LV} AS lv
                        LEFT JOIN (
                            SELECT  idvisit, COUNT(*) AS visit_actions
                            FROM
                                {LVA}
                            GROUP BY
                                idvisit
                        ) AS m ON
                            m.idvisit = lv.idvisit
                    SET lv.visit_total_actions = m.visit_actions
                    WHERE visit_last_action_time >= %s
                      AND visit_last_action_time <= %s
                """.format(LV=T_LOGV, LVA=T_LOGVA)
    cursor.execute(raw_sql, (start_date, end_date))


def update_total_visit_actions():
    raw_sql = """UPDATE {LV} AS lv
                        LEFT JOIN (
                            SELECT  idvisit, COUNT(*) AS visit_actions
                            FROM
                                {LVA}
                            GROUP BY
                                idvisit
                        ) AS m ON
                            m.idvisit = lv.idvisit
                    SET lv.visit_total_actions = m.visit_actions
                """.format(LV=T_LOGV, LVA=T_LOGVA)
    cursor.execute(raw_sql)


def finalize():
    raw_sql = """UPDATE {LV}
                    SET visit_exit_idaction_name = visit_exit_idaction_url+1,
                        visit_entry_idaction_name = visit_entry_idaction_url+1;""".format(LV=T_LOGV)
    cursor.execute(raw_sql)

    raw_sql = """UPDATE {LVA}
                    SET idaction_name_ref = idaction_url_ref + 1;""".format(LVA=T_LOGVA)
    cursor.execute(raw_sql)


def clear_archives():
    query = cursor.execute('SHOW TABLES')
    tables = cursor.fetchall()
    to_drop = []
    for col in tables:
        if 'archive' in col[0]:
            to_drop.append(col[0])
    if to_drop:
        raw_sql = 'DROP TABLE ' + (', ').join(to_drop)
        cursor.execute(raw_sql)
