#
# Google2Piwik -  exporting Google Analytics to Piwik
#
# @link http://clearcode.cc/
# @license http://www.gnu.org/licenses/gpl-3.0.html GPL v3 or later
#
import urlparse
import zlib
import re

import sql


TYPE_ACTION_URL = 1
TYPE_ACTION_NAME = 4


class Action(object):
    def __init__(self, path, title, internal_id):
        self.path = path
        self.titles = [title]
        self.internal_id = internal_id
        self.exported = False
        self.pageviews = 0
        self.timeleft = 0
        self.id_action_name = 0
        self.id_action_url = 0

    def __repr__(self):
        return str(self.titles)

    def get_title(self):
        for title in self.titles:
            if title is not None:
                return title
        return ""

    def export(self, base_path, version):
        path = urlparse.urljoin(base_path, self.path)
        title = self.get_title()

        url = re.sub(r'^http(s)?://(www.)?', '', path)
        url_prefix = self.get_url_prefix(path)
        type_url = (url, self.get_hash(url), TYPE_ACTION_URL, url_prefix)
        type_name = (title, self.get_hash(title), TYPE_ACTION_NAME, None)

        self.id_action_url = sql.insert_log_action(type_url, version)
        self.id_action_name = sql.insert_log_action(type_name, version)

        self.exported = True

    def get_hash(self, value):
        return zlib.crc32(value.encode('utf-8')) & 0xffffffff

    def get_url_prefix(self, path):
        '''
        Return a valid Piwik url_prefix for 'log_action' table
        It returns one of four values:
            0 if path starts with 'http://'
            1 if path starts with 'http://www.'
            2 if path starts with 'https://'
            3 if path starts with 'https://www.'
        '''
        path = urlparse.urlsplit(path)
        ssl = True if path.scheme == 'https' else False

        if path.netloc.startswith('www'):
            return 3 if ssl else 1
        else:
            return 2 if ssl else 0


class ActionManager(object):
    def __init__(self):
        """ self.actions will be path -> Action mapper """
        self.actions = {}
        self.__counter = 0

    def add_action(self, path, title):
        if path in self.actions:
            if not title in self.actions[path].titles:
                self.actions[path].titles.append(title)
        else:
            self.actions[path] = Action(path, title, self.counter_next())

    def __getitem__(self, path):
        if path is None:
            return None
        if not path in self.actions:
            self.actions[path] = Action(path, None, self.counter_next())
        return self.actions[path]

    def counter_next(self):
        self.__counter += 1
        return self.__counter

    @property
    def toExport(self):
        """ Returns list of not yet exported actions"""
        return filter(lambda x: self.actions[x].exported is False,
                      self.actions)

    def export(self, base_path, version):
        for action in self.toExport:
            self.actions[action].export(base_path, version)
