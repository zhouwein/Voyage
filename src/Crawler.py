import newspaper
from urlparse import urlparse, urljoin, urlunparse
import random
import common
import requests
import re
import logging
import collections
from ExplorerArticle import ExplorerArticle
import urlnorm
from Crawler.models import VisitedPage
from Crawler.models import ToVisitPage
'''
An iterator class for iterating over articles in a given site
'''

class Crawler(object):
    def __init__(self, site):
        '''
        (Crawler, str) -> Crawler
        creates a Crawler with a given origin_url
        '''
        self.site = site
        self.filters = site.referringsitefilter_set.all()
        #self.visit_queue = collections.deque([site.url])
        #self.visited_urls = set()
        self.domain = urlparse(site.url).netloc
        self.pages_visited = 0

        self.probabilistic_n = common.get_config()["crawler"]["n"]
        self.probabilistic_k = common.get_config()["crawler"]["k"]

    def __iter__(self):
        return self

    def next(self):
        '''
        (Crawler) -> newspaper.Article
        returns the next article in the sequence
        '''
        if(ToVisitPage.objects.count() == 0):
            ToVisitPage(url=self.site.url, site=self.site).save()
            VisitedPage.objects.all().delete()

        #standard non-recursive tree iteration
        while(True):
            if(ToVisitPage.objects.count() <= 0):
                raise StopIteration
            current_url = ToVisitPage.objects.first().url

            if(self._should_skip()):
                logging.info(u"skipping {0} randomly".format(current_url))
                continue

            logging.info(u"visiting {0}".format(current_url))
            #use newspaper to download and parse the article
            article = ExplorerArticle(current_url)
            article.download()

            #get get urls from the article
            for link in article.get_links():
                url = urljoin(current_url, link.href, False)
                if self.url_in_filter(url, self.filters):
                    logging.info("Matches with filter, skipping the {0}".format(url))
                    continue
                try:
                    parsed_url = urlparse(url)
                    parsed_as_list = list(parsed_url)
                    if(parsed_url.scheme != u"http" and parsed_url.scheme != u"https"):
                        logging.info(u"skipping url with invalid scheme: {0}".format(url))
                        continue
                    parsed_as_list[5] = ''
                    url = urlunparse(urlnorm.norm_tuple(*parsed_as_list))
                except Exception as e:
                    logging.info(u"skipping malformed url {0}. Error: {1}".format(url, str(e)))
                    continue
                if(not parsed_url.netloc.endswith(self.domain)):
                    continue
                if(VisitedPage.objects.filter(url=url).count()):
                    continue
                ToVisitPage(url=url, site=self.site).save()
                VisitedPage(url=url, site=self.site).save()
                logging.info(u"added {0} to the visit queue".format(url))

            self.pages_visited += 1
            return article

    def _should_skip(self):
        n = self.probabilistic_n
        k = self.probabilistic_k
        return False
        return random.random() <= Crawler._s_curve(self.pages_visited/n, k)

    @staticmethod
    def _s_curve(x, k):
        if(x <= 0.5):
            return ((k*(2*x)-(2*x))/(2*k*(2*x)-k-1))*0.5
        else:
            return 0.5*((-k*(2*(x-0.5))-(2*(x-0.5)))/(2*-k*(2*(x-0.5))-(-k)-1))+0.5

    def url_in_filter(self, url, filters):
        """
        Checks if any of the filters matches the url.
        Filters can be in regex search or normal string comparison.
        """
        for filt in filters:
            if ((filt.regex and re.search(filt.pattern, url, re.IGNORECASE)) or
                (not filt.regex and filt.pattern in url)):
                return True
        return False
