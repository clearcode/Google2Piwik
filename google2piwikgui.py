#!/usr/bin/env python
#
# Google2PiwikGUI - graphical user interface for Google2Piwik
# 
# @link http://clearcode.cc/
# @license http://www.gnu.org/licenses/gpl-3.0.html GPL v3 or later
#

import sys
import sql
import config
import google2piwik
from PyQt4 import QtGui
from PyQt4 import QtCore
from threading import Thread
from StringIO import StringIO

CONF_FILE = 'google2piwik.conf'

class Google2PiwikWizard(QtGui.QWizard):
    def __init__(self, parent=None):
        QtGui.QWizard.__init__(self, parent)
        
        self.setWindowTitle('Google2Piwik Wizard')
        screen = QtGui.QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)
        self.ga_sites = []
        self.piwik_sites = []
        self.finished = False
        self.setupPages()
    
    def setupPages(self):
        page_ga = GAWizardPage(self)
        page_gap = GAPWizardPage(self)
        page_db = DBWizardPage(self)
        page_piwik = PiwikWizardPage(self)
        page_date = DateWizardPage(self)
        page_export = ExportWizardPage(self)
        self.addPage(page_ga)
        self.addPage(page_gap)
        self.addPage(page_db)
        self.addPage(page_piwik)
        self.addPage(page_date)
        self.addPage(page_export)
        
class GAWizardPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        QtGui.QWizardPage.__init__(self, parent)
        self.setTitle("Google Analytics")
        self.setSubTitle("Please enter your Google Analytics account data.\nGoogle Analytics API currently does not support Google Apps accounts.")
        form = QtGui.QFormLayout()
        form.setHorizontalSpacing(40)
        self.ga_user_field = QtGui.QLineEdit(config.GOOGLE_USER)
        form.addRow(QtGui.QLabel("User"), self.ga_user_field)
        self.ga_password_field = QtGui.QLineEdit(config.GOOGLE_PASS)
        self.ga_password_field.setEchoMode(QtGui.QLineEdit.Password)
        form.addRow(QtGui.QLabel("Password"), self.ga_password_field)
        self.registerField("ga_user", self.ga_user_field)
        self.registerField("ga_password", self.ga_password_field)
        self.setLayout(form)
        
    def validatePage(self):
        try:
            google2piwik.config.GOOGLE_USER = self.ga_user_field.text()
            google2piwik.config.GOOGLE_PASS = self.ga_password_field.text()
            fetcher = google2piwik.GoogleFeedFetcher("")
            self.wizard().ga_sites = fetcher.GetTableIDs()
            return True
        except:
            alert = QtGui.QMessageBox()
            alert.setWindowTitle("Error")
            alert.setText("Invalid Google account data.")
            alert.exec_()
            return False
            
class GAPWizardPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        QtGui.QWizardPage.__init__(self, parent)
        
        self.setTitle("Google Analytics")
        self.setSubTitle("Choose the website you want to export.")
        form = QtGui.QFormLayout()
        form.setHorizontalSpacing(40)
        self.ga_table_combo = QtGui.QComboBox()
        form.addRow(QtGui.QLabel("Website"), self.ga_table_combo)
        self.registerField("ga_table*", self.ga_table_combo)
        self.setLayout(form)
    
    def initializePage(self):
        self.ga_table_combo.clear()
        for (label, id) in self.wizard().ga_sites:
            self.ga_table_combo.addItem(label,id)
        
class DBWizardPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        QtGui.QWizardPage.__init__(self, parent)
        
        self.setTitle("MySQL")
        self.setSubTitle("Please enter your MySQL configuration.")
        form = QtGui.QFormLayout()
        form.setHorizontalSpacing(40)
        self.db_host_field = QtGui.QLineEdit(config.MYSQL_CREDENTIALS["host"])
        form.addRow(QtGui.QLabel("Host"), self.db_host_field)
        self.db_port_field = QtGui.QLineEdit(config.MYSQL_CREDENTIALS["port"])
        form.addRow(QtGui.QLabel("Port"), self.db_port_field)
        self.db_name_field = QtGui.QLineEdit(config.MYSQL_CREDENTIALS["db"])
        form.addRow(QtGui.QLabel("Name"), self.db_name_field)
        self.db_user_field = QtGui.QLineEdit(config.MYSQL_CREDENTIALS["user"])
        form.addRow(QtGui.QLabel("User"), self.db_user_field)
        self.db_password_field = QtGui.QLineEdit(config.MYSQL_CREDENTIALS["passwd"])
        self.db_password_field.setEchoMode(QtGui.QLineEdit.Password)
        form.addRow(QtGui.QLabel("Password"), self.db_password_field)
        self.db_prefix_field = QtGui.QLineEdit(config.MYSQL_CREDENTIALS["table_prefix"])
        form.addRow(QtGui.QLabel("Table prefix"), self.db_prefix_field)
        self.registerField("db_host", self.db_host_field)
        self.registerField("db_port", self.db_port_field)
        self.registerField("db_name", self.db_name_field)
        self.registerField("db_user", self.db_user_field)
        self.registerField("db_password", self.db_password_field)
        self.registerField("db_prefix", self.db_prefix_field)
        self.setLayout(form)        
   
    def validatePage(self):
        try:
            config.MYSQL_CREDENTIALS = {"db" : str(self.field("db_name").toString()), 
                                    "host" : str(self.field("db_host").toString()),
                                    "port" : str(self.field("db_port").toString()),
                                    "user" : str(self.field("db_user").toString()),
                                    "passwd" : str(self.field("db_password").toString()),
                                    "table_prefix" : str(self.field("db_prefix").toString()) }
            sql.test_db(config.MYSQL_CREDENTIALS)
        except Exception as e:
            alert = QtGui.QMessageBox()
            alert.setWindowTitle("Error")
            alert.setText("Unable to connect to the database.\n"+str(e))
            alert.exec_()
            return False
        missing_tables = sql.check_tables(config.MYSQL_CREDENTIALS["table_prefix"])
        if len(missing_tables) == 0:
            return True
        else:
            alert = QtGui.QMessageBox()
            alert.setWindowTitle("Error")
            alert.setText("Tables not found:\n"+", ".join(missing_tables))
            alert.exec_()
            return False
        
class PiwikWizardPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        QtGui.QWizardPage.__init__(self, parent)
        
        self.setTitle("Piwik")
        self.setSubTitle("Please select your Piwik website.")
        form = QtGui.QFormLayout()
        form.setHorizontalSpacing(40)
        self.piwik_sites_combo = QtGui.QComboBox()
        form.addRow(QtGui.QLabel("Website"), self.piwik_sites_combo)
        self.registerField("piwik_sites", self.piwik_sites_combo)
        self.setLayout(form)
    
    def initializePage(self):
        self.piwik_sites_combo.clear()
        self.wizard().piwik_sites = sql.get_sites(self.field("db_prefix").toString())
        for items in self.wizard().piwik_sites:
            self.piwik_sites_combo.addItem(items["name"])
        
class DateWizardPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        QtGui.QWizardPage.__init__(self, parent)
        
        self.setTitle("Date")
        self.setSubTitle("Please enter date range.")
        form = QtGui.QFormLayout()
        form.setHorizontalSpacing(40)
        self.date_from = QtGui.QDateEdit()
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(QtCore.QDate.fromString(config.CONFIG_START, "yyyy-MM-dd"))
        form.addRow(QtGui.QLabel("From"), self.date_from)
        self.date_to = QtGui.QDateEdit()
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setDate(QtCore.QDateTime.currentDateTime().addDays(-1).date())
        form.addRow(QtGui.QLabel("To"), self.date_to)
        self.registerField("date_from", self.date_from)
        self.registerField("date_to", self.date_to)
        self.setLayout(form)

    def initializePage(self):
        self.wizard().finished = False

class ExportWizardPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        QtGui.QWizardPage.__init__(self, parent)
        
        self.setTitle("Google2Piwik")
        self.setSubTitle("Ready to begin.")
        layout = QtGui.QVBoxLayout()
        warning = QtGui.QLabel("Please make sure you have a backup of your database.\n")
        font = QtGui.QFont()
        font.setBold(True)
        warning.setFont(font)
        layout.addWidget(warning)
        layout.addWidget(QtGui.QLabel("Press Finish to begin exporting data.\n"))
        self.saveCheck = QtGui.QCheckBox("Save configuration")
        self.verboseDevCheck = QtGui.QCheckBox("Show developer information during export")
        self.saveCheck.setChecked(True)
        layout.addWidget(self.saveCheck)
        layout.addWidget(self.verboseDevCheck)
        self.registerField("save_conf", self.saveCheck)
        self.registerField("verbose_dev", self.verboseDevCheck)
        self.setLayout(layout)
    
    def initializePage(self):
        self.setupConfig()
    
    def validatePage(self):
        self.wizard().finished = True
        if self.field("save_conf").toBool():
            config.write_config(CONF_FILE)
        if self.field("verbose_dev").toBool():
            google2piwik.__VERBOSE__ = 2
        return True
    
    def setupConfig(self):
        """ Exports gathered settings to the config module. """
        selected = self.field("piwik_sites").toInt()[0]
        config.ID_SITE = self.wizard().piwik_sites[selected]["id"]
        config.SITE_BASE_URL = self.wizard().piwik_sites[selected]["url"]
        config.GOOGLE_TABLE_ID = self.wizard().ga_sites[self.field("ga_table").toInt()[0]][1]
        config.GOOGLE_USER = self.field("ga_user").toString()
        config.GOOGLE_PASS = self.field("ga_password").toString()
        config.CONFIG_START = google2piwik.read_date(self.field("date_from").toString())
        config.CONFIG_END = google2piwik.read_date(self.field("date_to").toString())
        
class LogsGui(QtGui.QWidget):
    """ Displays export logs from the Google2Piwik plugin """
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setGeometry(0, 0, 600, 350)

        self.setWindowTitle('Google2Piwik')
        screen = QtGui.QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)
        
        self.layout = QtGui.QVBoxLayout()
        self.log = QtGui.QTextEdit()
        self.log.setReadOnly(True)
        self.button = QtGui.QPushButton("Close")
        self.button.setEnabled(False)
        self.layout.addWidget(self.log)
        self.layout.addWidget(self.button)
        self.setLayout(self.layout)
        
        self.buffer = StringIO()
        sys.stdout = self.buffer
        self.startWorker()
    
    def startWorker(self):
        """ Starts Google2Piwik worker and a timer. """
        self.timer = QtCore.QTimer()
        self.connect(self.timer, QtCore.SIGNAL("timeout()"), self.updateLog)
        self.timer.start(1000)
        self.worker = Google2PiwikWrapper()
        self.worker.start()
        self.connect(self.button, QtCore.SIGNAL("clicked()"), self.cleanUp)
        
    def updateLog(self):
        """ Updates logs on timer signal. """
        self.log.clear()
        if self.worker.isAlive():
            self.log.append(self.buffer.getvalue())
        else:
            self.timer.stop()
            self.button.setEnabled(True)
            self.log.append(self.buffer.getvalue())
            self.log.append("Finished.")
        self.log.ensureCursorVisible()
        
    def closeEvent(self, arg):
        if self.worker.isAlive():
            arg.ignore()
        else:
            arg.accept()
        
    def cleanUp(self):
        self.worker.join()
        self.close()
        
class Google2PiwikWrapper(Thread):
    """ Runs Google2Piwik in a separate thread. """
    def run(self):
        try:
            sql.initialize(config.MYSQL_CREDENTIALS)
            sql.update_site_ts_created(config.ID_SITE, config.CONFIG_START)
            google2piwik.export_period(config.CONFIG_START, config.CONFIG_END)
        except Exception as e:
            print "Error: ", e
            print "Please check the configuration you provided."


if __name__ == '__main__':
    # Load settings if .conf file exists
    try:
        config.read_config(CONF_FILE)
    except:
        config.MYSQL_CREDENTIALS = {"host":"","port":"3306","user":"","passwd":"",
                                    "db":"","table_prefix":"piwik"}

    # Run wizard configuration
    wiz_app = QtGui.QApplication(sys.argv)
    wiz = Google2PiwikWizard()
    wiz.show()
    wiz_app.exec_()
    
    # Run Google2Piwik
    if wiz.finished:
        logs = LogsGui()
        logs.show()
        wiz_app.exec_()
