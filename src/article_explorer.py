"""
This script retrieves monitoring site, foreign sites,
and keywords from Django database and looks into the monitoring
sites to find matching foreign sites or keywords.
newspaper package is the core to extract and retrieve relevant data.
If any keyword (of text) or foreign sites (of links) matched,
the Article will be stored at Django database as articles.models.Article.
Django's native api is used to easily access and modify the entries.
"""

__author__ = "ACME: CSCC01F14 Team 4"
__authors__ = \
    "Yuya Iwabuchi, Jai Sughand, Xiang Wang, Kyle Bridgemohansingh, Ryan Pan"

import sys
import os

# Add Django directories in the Python paths for django shell to work
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..',
#                                             'Frontend')))
# Append local python lib to the front to assure
# local library(mainly Django 1.7.1) to be used
#sys.path.insert(0, os.path.join(os.environ['HOME'],
#                                '.local/lib/python2.7/site-packages'))
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
from explorer.models import*
from explorer.models import SourceTwitter as ExplorerSourceTwitter
from explorer.models import Keyword as ExplorerKeyword
from explorer.models import SourceSite as ExplorerSourceSite
# To load configurations
import yaml
# To store the article as warc files
import warc_creator
import CrawlerSource
# To get domain from url
import tld
# To concatenate newspaper's articles and CrawlerSource's articles
import itertools
import requests
# For Logging
import logging
import glob
import datetime

def configuration():
    """ (None) -> dict
    Returns a dictionary containing the micro settings from the
    config.yaml file located in the directory containing this file
    """
    config_yaml = open("../config.yaml", 'r')
    conf = yaml.load(config_yaml)
    config_yaml.close()
    return conf

profile_log = None
def parse_articles(referring_sites, db_keywords, source_sites, twitter_accounts_explorer):
    """ (list of [str, newspaper.source.Source, str],
         list of str, list of str, str) -> None
    Downloads each db_article in the site, extracts, compares
    with Foreign Sites and Keywords provided.
    Then the db_article which had a match will be stored into the Django database

    Keyword arguments:
    referring_sites     -- List of [name, 'built_article'] of each site
    db_keywords         -- List of keywords
    source_sites       -- List of foreign sites
    """
    added, updated, failed, no_match = 0, 0, 0, 0

    # for each db_article in each sites, download and parse important data

    global profile_log
    profile_log= open("profile.log", "a")

    for site in referring_sites:
        # print "\n%s" % site[0]
        profile_log.write("site: {0}\n".format(site['name']))
        profile_site = time.clock()

        article_count = -1
        newspaper_articles = []
        crawlersource_articles = []
        logging.info("Site: %s Type:%i"%(site['name'], site['type']))

        logging.info("Creating Plan B Article generator")
        crawlersource_articles = CrawlerSource.CrawlerSource(site["url"])
        logging.info("Finished creating Plan B Article generator")
        article_iterator = crawlersource_articles
        processed = 0
        logging.info("Starting article parsing")
        try:
            while True:
                profile_next = time.clock()
                article = article_iterator.next()
                profile_log.write("{0},".format(time.clock() - profile_next))
                logging.info("Looking at %s"%article.url)
                # Check for any new command on communication stream
                logging.debug("Checking for any new command on communication stream")
                check_command()

                url = article.url
                if 'http://www.' in url:
                    url = url[:7] + url[11:]
                elif 'https://www.' in url:
                    url = url[:8] + url[12:]

                # Try to download and extract the useful data
                try:
                    if(not article.is_downloaded):
                        logging.debug("Downloading article")
                        logging.disable(logging.ERROR)
                        article.download()
                        logging.disable(logging.NOTSET)
                    if(not article.is_parsed):
                        logging.debug("Parsing article")
                        logging.disable(logging.ERROR)
                        article.parse()
                        logging.disable(logging.NOTSET)
                    title = article.title
                except:
                    logging.warning("Could not parse article")
                    title = ""
                # If downloading/parsing the page fails,
                # stop here and move on to next db_article
                if not ((title == "") or (title == "Page not found")):
                    # Regex the keyword from the article's text
                    logging.debug("Checking Keyword matches")
                    profile_parse = time.clock()
                    keywords = get_keywords(article, db_keywords)
                    # Regex the links within article's html
                    logging.debug("Checking Source Site matches")
                    sources = get_sources_sites(article.article_html, source_sites)
                    logging.debug("Checking Twitter Account matches")
                    twitter_accounts= get_sources_twitter(article.article_html, twitter_accounts_explorer)
                    # Store parsed author
                    authors = article.authors
                    # Try to parse the published date
                    pub_date = get_pub_date(article)
                    profile_log.write("{0},".format(time.clock()-profile_parse))
                    # If neither of keyword nor sources matched,
                    # then stop here and move on to next article
                    if not (keywords == [] and sources[0] == [] and twitter_accounts[0] ==[]):
                        try:
                            url = requests.get(url).url
                        except:
                            logging.warning("Could not request")

                        logging.info("Found Match")
                        # Check if the entry already exists
                        profile_db = time.clock()
                        db_stuff(authors, keywords, pub_date, site, sources, title, twitter_accounts, url)
                        profile_log.write("{0},".format(time.clock() - profile_db))

                        logging.info("Creating warc")

                        profile_warc = time.clock()
                        warc_creator.create_article_warc(url)
                        profile_log.write("{0},".format(time.clock() - profile_warc))


                processed += 1

                # Let the output print back to normal for minimal ui
                sys.stdout = sys.__stdout__
                # Print out minimal information
                sys.stdout.write(
                    "%s (Article|%s) %i/%i          \r" %
                    (str(timezone.localtime(timezone.now()))[:-13],
                     site["name"], processed, article_count))
                sys.stdout.flush()
                # Null the db_article data to free the memory
                #newspaper_source.articles[db_article] = None

                # Null the article object's content to free the memory
                article.article_html = None
                article.text = None
                article.title = None
                article.source_url = None
                article.url = None
                article.top_img = None
                article.meta_img = None
                article.imgs = None
                article.movies = None
                article.keywords = None
                article.meta_keywords = None
                article.tags = None
                article.authors = None
                article.publish_date = None
                article.summary = None
                article.html = None
                article.is_parsed = None
                article.is_downloaded = None
                article.meta_description = None
                article.meta_lang = None
                article.meta_favicon = None
                article.meta_data = None
                article.canonical_link = None
                article.top_node = None
                article.clean_top_node = None
                article.doc = None
                article.clean_doc = None
                article.additional_data = None
        except StopIteration:
            pass
        profile_log.write("total: {0}\n".format(time.clock()-profile_site))


def db_stuff(authors, keywords, pub_date, site, sources, title, twitter_accounts, url):
    db_article_list = Article.objects.filter(url=url)
    if not db_article_list:
        logging.info("Adding new Article to the DB")
        # If the db_article is new to the database,
        # add it to the database
        db_article = Article(title=title, url=url,
                             domain=site["url"],
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
            db_article.sourcetwitter_set.create(name=account, matched=True)

        for account in twitter_accounts[1]:
            db_article.sourcetwitter_set.create(name=account, matched=False)

        for source in sources[0]:
            db_article.sourcesite_set.create(url=source[0],
                                             domain=source[1], matched=True, local=(source[1] in site["url"]))

        for source in sources[1]:
            db_article.sourcesite_set.create(url=source[0],
                                             domain=source[1], matched=False, local=(source[1] in site["url"]))

    else:
        logging.info("Modifying existing Article in the DB")
        # If the db_article already exists,
        # update all fields except date_added
        db_article = db_article_list[0]
        db_article.title = title
        db_article.url = url
        db_article.domain = site["url"]
        # Do not update the added date
        # db_article.date_added = today
        db_article.date_published = pub_date
        db_article.save()

        for key in keywords:
            if not ArticleKeyword.objects.filter(name=key):
                db_article.keyword_set.create(name=key)

        for author in authors:
            if not Author.objects.filter(name=author):
                db_article.author_set.create(name=author)

        for account in twitter_accounts[0]:
            if not SourceTwitter.objects.filter(name=account):
                db_article.sourcetwitter_set.create(name=account, matched=True)

        for account in twitter_accounts[1]:
            if not SourceTwitter.objects.filter(name=account):
                db_article.sourcetwitter_set.create(name=account, matched=False)

        for source in sources[0]:
            if not SourceSite.objects.filter(url=source[0]):
                db_article.sourcesite_set.create(url=source[0],
                                                 domain=source[1], matched=True, local=(source[1] in site["url"]))

        for source in sources[1]:
            if not SourceSite.objects.filter(url=source[0]):
                db_article.sourcesite_set.create(url=source[0],
                                                 domain=source[1], matched=False, local=(source[1] in site["url"]))


def get_sources_sites(html, sites):
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
    formatted_sites = []

    for site in sites:
        formatted_sites.append(tld.get_tld(site))

    for url in re.findall(
            "href=[\"\'][^\"\']*?.*?[^\"\']*?[\"\']", html, re.IGNORECASE):
        try:
            domain = tld.get_tld(url[6:-1])
        except:
            continue
        if domain in formatted_sites:
            # If it matches even once, append the site to the list
            result_urls_matched.append([url[6:-1], domain])
        else:
            result_urls_unmatched.append([url[6:-1], domain])

    # Return the list
    return [result_urls_matched,result_urls_unmatched]


def get_sources_twitter(html, source_twitter):
    matched = []
    unmatched = []
    # Twitter handle name specifications
    accounts = re.findall('(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z]+[A-Za-z0-9]+)', html)

    for account in set(accounts):
        if account in source_twitter:
            matched.append(account)
        else:
            unmatched.append(account)
    return [matched,unmatched]




def get_pub_date(article):
    """ (newspaper.article.Article) -> str
    Searches and returns date of which the article was published
    Returns None otherwise

    Keyword arguments:
    article         -- 'Newspaper.Article' object of article
    """
    dates = []

    # For each metadata stored by newspaper's parsing ability,
    # check if any of the key contains 'date'
    for key, value in article.meta_data.iteritems():
        if re.search("date", key, re.IGNORECASE):
            # If the key contains 'date', try to parse the value as date
            try:
                dt = parser.parse(str(value))
                # If parsing succeeded, then append it to the list
                dates.append(dt)
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


def get_keywords(article, keywords):
    """ (newspaper.article.Article, list of str) -> list of str
    Searches and returns keywords which the article's title or text contains
    Returns empty list otherwise

    Keyword arguments:
    article         -- 'Newspaper.Article' object of article
    keywords        -- List of keywords
    """
    matched_keywords = []

    # For each keyword, check if article's text contains it
    for key in keywords:
        if re.search('[^a-z]' + key + '[^a-z]', article.title + article.text, re.IGNORECASE):
            # If the article's text contains the key, append it to the list
            matched_keywords.append(key)
    # Return the list
    return matched_keywords


def explore():
    """ () -> None
    Connects to keyword and site tables in database,
    crawls within monitoring sites, then pushes articles which matches the
    keywords or foreign sites to the article database
    """

    # Retrieve and store monitoring site information
    logging.info("Collecting all Referring Sites from Database")
    referring_sites = []
    for site in ReferringSite.objects.all():
        referring_sites.append({"name":site.name, "url":site.url, "type":site.mode})
    logging.info("Collected all Referring Sites from Database")

    # Retrieve and store foreign site information
    logging.info("Collecting all Source Sites from Database")
    source_sites = []
    for site in SourceSite.objects.all():
        # source_sites is now in form ['URL', ...]
        source_sites.append(site.url)
    logging.info("Collected all Source Sites from Database")

    # Retrieve all stored keywords
    logging.info("Collecting all Keywords from Database")
    keyword_list = []
    for key in ExplorerKeyword.objects.all():
        keyword_list.append(str(key.name))
    logging.info("Collected all Keywords from Database")

    # Retrieve all stored twitter_accounts
    logging.info("Collecting all Source Twitter Accounts from Database")
    source_twitter_list = []
    twitter_accounts = ExplorerSourceTwitter.objects.all()
    for key in twitter_accounts:
        source_twitter_list.append(str(key.name))
    logging.info("Collected all Source Twitter Accounts from Database")

    # Parse the articles in all sites
    logging.info("Parsing Articles Started")
    parse_articles(referring_sites, keyword_list, source_sites, source_twitter_list)


def comm_write(text):
    """ (Str) -> None
    Writes a command to the comm_file of article.
    The file is used to communicate with the running explorer process,
    to change the status safely.

    Keyword arguments:
    text         -- String of command
    """
    # Load the relevant configs
    conf = configuration()['communication']

    # Wait for retry_count * retry_delta seconds
    for k in range(conf['retry_count']):
        try:
            comm = open('article' + conf['comm_file'], 'w')
            comm.write(text)
            comm.close()
            return None
        except:
            time.sleep(conf['retry_delta'])


def comm_read():
    """ (None) -> Str
    Reads the current status or command listed on the comm_file with the
    article, then returns the output.
    """
    # Load the relevant configs
    conf = configuration()['communication']

    # Wait for retry_count * retry_delta seconds
    for k in range(conf['retry_count']):
        try:
            comm = open('article' + conf['comm_file'], 'r')
            msg = comm.read()
            comm.close()
            return msg
        except:
            time.sleep(conf['retry_delta'])


def comm_init():
    """ (None) -> None
    Initialize The communication file
    """
    # Set the current status as Running
    comm_write('RR %s' % os.getpid())


def check_command():
    """ (None) -> None
    Check the communication file for any commands given.
    Execute according to the commands.
    """
    # Load the relevant configs
    conf = configuration()['communication']
    msg = comm_read()

    # Let the output print back to normal for printing status
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

    if msg[0] == 'W':
        command = msg[1]
        if command == 'S':
            print('Stopping Explorer...')
            comm_write('SS %s' % os.getpid())
            sys.exit(0)
        elif command == 'P':
            print('Pausing ...')
            comm_write('PP %s' % os.getpid())
            while comm_read()[1] == 'P':
                print('Waiting %i seconds ...' % conf['sleep_time'])
                time.sleep(conf['sleep_time'])
                check_command()
        elif command == 'R':
            print('Resuming ...')
            comm_write('RR %s' % os.getpid())


if __name__ == '__main__':

    # Load the relevant configs
    config = configuration()

    # Logging config
    time = datetime.datetime.now().strftime('%Y%m%d')
    log_dir = config['projectdir']+"/log"
    
    try:
        cycle_number = sorted(glob.glob(log_dir + "/article_explorer-" + time + "*.log"))[-1][-7:-4]
        cycle_number = str(int(cycle_number) + 1)
    except:
        cycle_number = "0"
    logging.basicConfig(filename=log_dir+"/article_explorer-" + time + "-" + cycle_number.zfill(3) + ".log",
                        level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    config = config['article']
    logging.info("Connecting to django/database")
    # Connects to Site Database
    django.setup()
    logging.info("Connected to django/database")

    logging.info("Initializing Communication Stream")
    # Initialize Communication Stream
    comm_init()
    logging.info("Initialized Communication Stream")

    logging.info("Checking for any new command on communication stream")
    # Check for any new command on communication stream
    check_command()
    logging.info("Checked for any new command on communication stream")

    start = timeit.default_timer()

    # The main function, to explore the articles
    explore()

    print #for breakpoint
