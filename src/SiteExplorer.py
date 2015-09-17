"""
This script retrieves monitoring site, foreign sites,
and keywords from Django database and looks into the monitoring
sites to find matching foreign sites or keywords.
newspaper package is the core to extract and retrieve relevant data.
If any keyword (of text) or foreign sites (of links) matched,
the Article will be stored at Django database as articles.models.Article.
Django's native api is used to easily access and modify the entries.
"""

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
from articles.models import*
from articles.models import Keyword as ArticleKeyword
from articles.models import SourceSite as ArticleSourceSite
from articles.models import SourceTwitter as ArticleSourceTwitter
from explorer.models import*
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
from ExplorerArticle import ExplorerArticle

class SiteExplorer:
    def __init__(self, id, search_parameters):
        self.id = id
        self.search_parameters = search_parameters


    def run(self):
        """ (list of [str, newspaper.source.Source, str],
             list of str, list of str, str) -> None
        Downloads each db_article in the site, extracts, compares
        with Foreign Sites and Keywords provided.
        Then the db_article which had a match will be stored into the Django database
        """

        site = ReferringSite.objects.get(pk=self.id)
        self.setup_logging(site.name)

        article_count = 0
        newspaper_articles = []
        crawlersource_articles = []
        self.logger.info("Site: %s Mode:%i"%(site.name, site.mode))
        #0 = newspaper, 1 = crawler, 2 = both

        if(site.mode == 0 or site.mode == 2):
            newspaper_source = newspaper.build(site.url,
                                             memoize_articles=False,
                                             keep_article_html=True,
                                             fetch_images=False,
                                             language='en',
                                             number_threads=1)
            newspaper_articles = newspaper_source.articles
            article_count += newspaper_source.size()
            self.logger.info("populated {0} articles using newspaper".format(article_count))
        if(site.mode == 1 or site.mode == 2):
            crawlersource_articles = Crawler.Crawler(site.url)
            article_count += crawlersource_articles.probabilistic_n
            self.logger.debug("expecting {0} from plan b crawler".format(crawlersource_articles.probabilistic_n))
        article_iterator = itertools.chain(iter(newspaper_articles), crawlersource_articles)
        processed = 0
        for article in article_iterator:
            #have to put all the iteration stuff at the top because I used continue extensively in this loop
            processed += 1
            print(
                "%s (Article|%s) %i/%i          \r" %
                (str(timezone.localtime(timezone.now()))[:-13],
                 site.name, processed, article_count))
            self.logger.info("Processing %s"%article.url)
            # Check for any new command on communication stream

            url = article.url
            if 'http://www.' in url:
                url = url[:7] + url[11:]
            elif 'https://www.' in url:
                url = url[:8] + url[12:]

            article = ExplorerArticle(article.url)
            # Try to download and extract the useful data
            if(not article.is_downloaded):
                if(not article.download()):
                    self.logger.warning("article skipped because download failed")
                    continue

            article.preliminary_parse()

            if not article.title:
                self.logger.info("article missing title, skipping")
                continue

            if not article.text:
                self.logger.info("article missing text, skipping")
                continue

            # Regex the keyword from the article's text
            keywords = self.get_keywords(article)
            self.logger.debug(u"matched keywords: {0}".format(repr(keywords)))
            # Regex the links within article's html
            sources = self.get_sources_sites(article)
            self.logger.debug(u"matched sources: {0}".format(repr(sources)))
            twitter_accounts = self.get_sources_twitter(article)
            self.logger.debug(u"matched twitter_accounts: {0}".format(repr(twitter_accounts[0])))

            if((not keywords) or (not sources[0]) or (not twitter_accounts[0])):#[] gets coverted to false
                self.logger.debug("skipping article because it's not a match")
                continue
            self.logger.info("match found")

            article.newspaper_parse()

            authors = article.authors
            pub_date = self.get_pub_date(article)
            # Check if the entry already exists
            db_article_list = Article.objects.filter(url=url)
            if not db_article_list:
                self.logger.info("Adding new Article to the DB")
                # If the db_article is new to the database,
                # add it to the database
                db_article = Article(title=article.title, url=url,
                                  domain=site.url,
                                  date_added=timezone.localtime(
                                      timezone.now()),
                                  date_published=pub_date)
                db_article.save()

                db_article = Article.objects.get(url=url)

                for key in keywords:
                    db_article.keyword_set.create(name=key)

                for author in authors:
                    db_article.author_set.create(name=author)
                for account in twitter_accounts[0]:

                    db_article.sourcetwitter_set.create(name = account, matched = True)

                for account in twitter_accounts[1]:
                    db_article.sourcetwitter_set.create(name = account, matched = False)

                for source in sources[0]:
                    db_article.sourcesite_set.create(url=source[0],
                                              domain=source[1], matched=True, local=(source[1] in site["url"]))

                for source in sources[1]:
                    db_article.sourcesite_set.create(url=source[0],
                                              domain=source[1], matched=False, local=(source[1] in site["url"]))

            else:
                self.logger.info("Modifying existing Article in the DB")
                # If the db_article already exists,
                # update all fields except date_added
                db_article = db_article_list[0]
                db_article.title = article.title
                db_article.url = url
                db_article.domain = site.url
                # Do not update the added date
                # db_article.date_added = today
                db_article.date_published = pub_date
                db_article.save()

                for key in keywords:
                    if not db_article.keyword_set.filter(name=key):
                        db_article.keyword_set.create(name=key)

                for author in authors:
                    if not db_article.author_set.filter(name=author):
                        db_article.author_set.create(name=author)

                for account in twitter_accounts[0]:
                    if not db_article.sourcetwitter_set.filter(name=account):
                        db_article.sourcetwitter_set.create(name = account, matched = True)

                for account in twitter_accounts[1]:
                    if not db_article.sourcetwitter_set.filter(name=account):
                        db_article.sourcetwitter_set.create(name = account, matched = False)

                for source in sources[0]:
                    if not db_article.sourcesite_set.filter(url=source[0]):
                        db_article.sourcesite_set.create(url=source[0],
                                              domain=source[1], matched=True, local=(source[1] in site.url))

                for source in sources[1]:
                    if not db_article.sourcesite_set.filter(url=source[0]):
                        db_article.sourcesite_set.create(url=source[0],
                                              domain=source[1], matched=False, local=(source[1] in site.url))

            warc_creator.create_article_warc(url)
        self.logger.info("Finished Site: %s"%site.name)
        print(
            "%s (Article|%s) %i/%i          " %
            (str(timezone.localtime(timezone.now()))[:-13], site.name,
             processed, article_count))

    def get_sources_sites(self, article):
        """ (str, list of str) -> list of [str, str]
        Searches and returns links redirected to sites within the html
        links will be storing the whole url and the domain name used for searching.
        Returns empty list if none found

        Keyword arguments:
        html                -- string of html
        sites               -- list of site urls to look for
        """
        result_urls_matched = []
        result_urls_unmatched = []
        # Format the site to assure only the domain name for searching
        formatted_sites = set()

        for site in self.search_parameters.source_sites:
            formatted_sites.add(tld.get_tld(site))

        for url in article.get_urls(article_text_links_only=True):
            try:
                domain = tld.get_tld(url)
            #apparently they don't inherit a common class so I have to hard code it
            except (tld.exceptions.TldBadUrl, tld.exceptions.TldDomainNotFound, tld.exceptions.TldIOError):
                continue
            if domain in formatted_sites:
                # If it matches even once, append the site to the list
                result_urls_matched.append([url[6:-1], domain])
            else:
                result_urls_unmatched.append([url[6:-1], domain])

        # Return the list
        return [result_urls_matched,result_urls_unmatched]


    def get_sources_twitter(self, article):
        matched = []
        unmatched = []
        # Twitter handle name specifications
        accounts = re.findall('(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z]+[A-Za-z0-9]+)', article.text)

        for account in set(accounts):
            if account in self.search_parameters.twitter_accounts:
                matched.append(account)
            else:
                unmatched.append(account)
        return [matched,unmatched]




    def get_pub_date(self, article):
        """ (newspaper.article.Article) -> str
        Searches and returns date of which the article was published
        Returns None otherwise

        Keyword arguments:
        article         -- 'Newspaper.Article' object of article
        """
        dates = []

        # For each metadata stored by newspaper's parsing ability,
        # check if any of the key contains 'date'
        for key, value in article.newspaper_article.meta_data.iteritems():
            if re.search("date", key, re.IGNORECASE):
                # If the key contains 'date', try to parse the value as date
                try:
                    dt = parser.parse(str(value))
                    # If parsing succeeded, then append it to the list
                    dates.append(dt)
                except (KeyboardInterrupt, SystemExit):
                    raise
                except:
                    pass
        # If one of more dates were found,
        # return the oldest date as new ones can be updated dates
        # instead of published date
        if dates:
            date = sorted(dates, key=lambda x: str(x)[0])[0]
            if timezone.is_naive(date):
                return \
                    timezone.make_aware(date,
                                        timezone=timezone.get_default_timezone())
            else:
                return timezone.localtime(date)
        return None


    def get_keywords(self, article):
        """ (newspaper.article.Article, list of str) -> list of str
        Searches and returns keywords which the article's title or text contains
        Returns empty list otherwise

        Keyword arguments:
        article         -- 'Newspaper.Article' object of article
        keywords        -- List of keywords
        """
        matched_keywords = []

        # For each keyword, check if article's text contains it
        for key in self.search_parameters.keywords:
            regex = re.compile('[^a-z]' + key + '[^a-z]', re.IGNORECASE)
            if regex.search(article.title) or regex.search(article.text):
                # If the article's text contains the key, append it to the list
                matched_keywords.append(key)
        # Return the list
        return matched_keywords


    def setup_logging(self, site_name):
        # Load the relevant configs
        config = common.get_config()

        # Logging config
        current_time = datetime.datetime.now().strftime('%Y%m%d')
        log_dir = config['projectdir']+"/log"
        prefix = log_dir + "/" + site_name + "article_explorer-"

        try:
            cycle_number = sorted(glob.glob(prefix + current_time + "*.log"))[-1][-7:-4]
            cycle_number = str(int(cycle_number) + 1)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            cycle_number = "0"

        self.logger = logging.getLogger(site_name)
        self.logger.setLevel(logging.INFO)

        fh = logging.FileHandler(prefix + current_time + "-" + cycle_number.zfill(3) + ".log")
        fh.setLevel(logging.INFO)
        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)
        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        self.logger.addHandler(fh)
        self.logger.addHandler(ch)