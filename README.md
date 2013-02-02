Google2Piwik Exporter, version 1.5, February 2013

Description
===========
Google2Piwik is script written in Python to enable exporting
statistics from Google Analytics to Piwik.

Requirements
============
- Access to Piwik Installation.
- Google Analytics Account with read or admin rights.
- The Google Analytics API currently does not support Google Apps for your Domain Accounts.
  Thats why you can't export data from account@yourdomain.com even if you have access via web interface.
  However you can grant privileges to your Gmail account, and use it to perform the export.
- Goggle APIs API key (here you can get one: https://code.google.com/apis/console/)
- Python 2.6 with components:
  - gdata-python-client (Google Python API) - http://code.google.com/p/gdata-python-client/
  - MySQLdb
  - PyQt4 (http://www.riverbankcomputing.co.uk/software/pyqt/download) --gui version only

Preparation
===========
Before running the script please be sure to:
- Prepare `google2piwik.conf` configuration file - sample in  google2piwik.conf.sample
- If you don't know your site table_id, type: python google2piwik.py -p
  (remember to fill google login and pass configuration before)
- Check if configuration file is acceptable and all rights are present (./google2piwik.py -c)
- Create backup of your Piwik MySQL Database
- Set the timezone in Piwik for the site where you import data to UTC

After export
============
After successful export, please go to your Piwik installation folder
and run:
/usr/bin/php5 /path/to/piwik/misc/cron/archive.php -- url=http://example.org/piwik/

Limitations
===========
Unfortunately because of lack of full access to data, some statistics
may be different from presented in Google Analytics.

Known not trustworthy statistics:
 * Visitors -> Visitor Log statistics are not reliable.
   This one is generated semi-randomly to supply informations about Actions (Pageviews, Bouncy Rate etc.)
 * Sometimes page `Bouncy Rate` and `Average time on page` is slightly different from Google Analytics
 * Visits Providers are unknown (because Google doesn't supply such informations)
 * Actions -> Unique Pageviews
 * Visitors -> Settings -> Plugins
   Google provides only informations about Flash Player and Java enabled.

Because of Google API Policy, there is a limit of requests per 24 hours. Exporter uses google API quota (50k requests/day).
Currently this script is using 6 requests (fetching 10 000 data rows) for one exported day, plus 3 for whole period.
One additional request (6th) has been added to populate visit numbers and days since last visit tables. It slowed a bit whole process of export.
However number of requests depends on number of visits and total number of pageviews.
This means that you should be able to export about 2000 days per 24h in low and medium visited sites.

Running GUI
===========
$ cd Google2Piwik
$ python google2piwikgui.py

Building binaries
=================
- Make sure you have all the requirements, including PyQt4
- Get pyinstaller (http://www.pyinstaller.org/)
- Run:
$ python /path/to/pyinstaller/Configure.py
$ python /path/to/pyinstaller/Makespec.py --onefile Google2Piwik/google2piwikgui.py
$ python /path/to/pyinstaller/Build.py google2piwikgui.spec
- Copy Google2Piwik/lib/* to dist/lib/*

Contact
=======
Developed & maintained by Clearcode (http://clearcode.cc)

Development Team:
Daniel Borzęcki
Maciej Zawadziński
Piotr Rzepecki
Maciej Sobczak
Grzegorz Janik

Contact: office@clearcode.cc

License
=======
http://www.gnu.org/licenses/gpl-3.0.html GPL v3 or later
