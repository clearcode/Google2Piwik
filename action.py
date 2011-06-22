#
# Google2Piwik -  exporting Google Analytics to Piwik
#
# @link http://clearcode.cc/
# @license http://www.gnu.org/licenses/gpl-3.0.html GPL v3 or later
#

import sql

TYPE_ACTION_URL  = 1
TYPE_ACTION_NAME = 4

class Action(object):  
    def __init__(self, path, title, internal_id):
        self.path = path
        self.titles = [title]
        self.internal_id = internal_id
        self.exported = False
        self.pageviews = 0
        self.timeleft = 0
    
    def __repr__(self):
        return str(self.titles)

    def get_title(self):
        for title in self.titles:
            if title != None: return title
        return ""
    
    def export(self, base_path):
        path = base_path + self.path
        title = self.get_title()
        
        type_url = ( path, self.get_hash(path), TYPE_ACTION_URL )

        type_name = ( title, self.get_hash(title + path), TYPE_ACTION_NAME )
        
        self.id_action_url = sql.insert_log_action(type_url)
        self.id_action_name = sql.insert_log_action(type_name)

        self.exported = True
    
    def get_hash(self, value):
        return abs(hash(value))
    
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
        if path == None:
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
        return filter(lambda x: self.actions[x].exported == False, self.actions)

    def export(self, base_path):
        for action in self.toExport:
            self.actions[action].export(base_path)
        
