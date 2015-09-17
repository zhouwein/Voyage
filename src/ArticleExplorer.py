import multiprocessing
import time
from collections import namedtuple
from SiteExplorer import SiteExplorer

import sys
import os

# Add Django directories in the Python paths for django shell to work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..',
                                             'Frontend')))
# Append local python lib to the front to assure
# local library(mainly Django 1.7.1) to be used
##sys.path.insert(0, os.path.join(os.environ['HOME'],
##                                '.local/lib/python2.7/site-packages'))
# newspaper, for populating articles of each site
# and parsing most of the data.
import newspaper
# Used for newspaper's keep_article_html as it was causing error without it
import lxml.html.clean
# Regex, for parsing keywords and sources
import re
# Mainly used to make the explorer sleep
import time
import timeit
# For getting today's date with respect to the TZ specified in Django Settings
from django.utils import timezone
# For extracting 'pub_date's string into Datetime object
from dateutil import parser
# To connect and use the Django Database
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'Frontend.settings'
# For Models connecting with the Django Database
from articles.models import *
from articles.models import Keyword as ArticleKeyword
from articles.models import SourceSite as ArticleSourceSite
from articles.models import SourceTwitter as ArticleSourceTwitter
from explorer.models import *
from explorer.models import SourceTwitter as ExplorerSourceTwitter
from explorer.models import Keyword as ExplorerKeyword
from explorer.models import SourceSite as ExplorerSourceSite
# To load configurations
import common
# To store the article as warc files
import warc_creator
import Crawler
# To get domain from url
import tld
# To concatenate newspaper's articles and Crawler's articles
import itertools
import requests
# For Logging
import logging
import glob
import datetime
from collections import namedtuple
from datetime import datetime
import time
import multiprocessing
import threading
import SiteExplorer
SearchParameters = namedtuple("SearchParameters", ["source_sites", "keywords", "twitter_accounts"])

def stub(id):
    # Retrieve and store foreign site information
    source_sites = []
    for site in ExplorerSourceSite.objects.all():
        # self.search_parameters.source_sites is now in form ['URL', ...]
        source_sites.append(site.url)
    logging.info("Collected {0} Source Sites from Database".format(len(source_sites)))

    # Retrieve all stored keywords
    keywords = []
    for key in ExplorerKeyword.objects.all():
        keywords.append(str(key.name))
    logging.info("Collected {0} Keywords from Database".format(len(keywords)))

    # Retrieve all stored twitter_accounts
    twitter_accounts = []
    for key in ExplorerSourceTwitter.objects.all():
        twitter_accounts.append(str(key.name))
    logging.info("Collected {0} Source Twitter Accounts from Database".format(len(twitter_accounts)))

    search_parameters = SearchParameters(source_sites=source_sites, keywords=keywords, twitter_accounts=twitter_accounts)
    s = SiteExplorer.SiteExplorer(id, search_parameters)
    s.run()

class RunningSite:
    def __init__(self, id):
        self.id = id
        self.last_finish = None
        self.process = None

    def start(self):
        ##self.process = multiprocessing.Process(target=stub, args=(self.id,))
        self.process = threading.Thread(target=stub, args=(self.id,))
        self.process.start()
        self.last_finish = None

    def tick(self):
        if(self.process and not self.process.is_alive()):
            self.last_finish = datetime.now()
            self.process = None

        if(not self.process):
            #db_site = ReferringSite.objects.get(pk=self.id)
            #interval = db_site.interval
            interval = 21600
            if not self.last_finish or ((datetime.now() - self.last_finish).seconds > interval):
                self.start()

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        if(type(other) == type(self)):
            return self.id == other.id
        else:
            return self.id == other

class ArticleExplorer:
    def __init__(self):
        self.running_sites = set()
        self.already_added_site = set()
        self.referring_sites = None

    def main_loop(self):
        self.update_sites()
        for s in self.running_sites:
            s.tick()

        time.sleep(30)


    def update_sites(self):
        for site in ReferringSite.objects.all():
            self.running_sites.add(RunningSite(site.id))

if __name__ == "__main__":
    a = ArticleExplorer()
    a.main_loop()

