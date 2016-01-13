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
import codecs
'''
An iterator class for iterating over articles in a given site
'''

class Crawler(object):
        def __init__(self, origin_url, name):
            '''
            (Crawler, str) -> Crawler
            creates a Crawler with a given origin_url
            '''
            self.origin_url = origin_url
            self.visit_queue = collections.deque([origin_url])
            self.visited_urls = set()
            self.domain = urlparse(origin_url).netloc
            self.pages_visited = 0

            self.probabilistic_n = common.get_config()["crawler"]["n"]
            self.probabilistic_k = common.get_config()["crawler"]["k"]

            self.f = codecs.open(name, 'wb', encoding="utf-8")

        def __iter__(self):
            return self

        def next(self):
            '''
            (Crawler) -> newspaper.Article
            returns the next article in the sequence
            '''
            #standard non-recursive tree iteration
            while(True):
                if(len(self.visit_queue) <= 0):
                    raise StopIteration
                try:
                    self.f.write(u"0 \n")
                    current_url = self.visit_queue.pop()

                    logging.info(u"visiting {0}".format(current_url))
                    #use newspaper to download and parse the article
                    article = ExplorerArticle(current_url)
                    article.download()

                    #get get urls from the article
                    for link in article.get_links():
                        url = urljoin(current_url, link.href, False)
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
                        self.f.write(u"1 " + url + u"\n")
                        if(url in self.visited_urls):
                            continue
                        self.f.write(u"2 " + url + u"\n")
                        self.visit_queue.appendleft(url)
                        self.visited_urls.add(url)
                        logging.info(u"added {0} to the visit queue".format(url))

                    self.pages_visited += 1
                    return article
                except Exception as e:
                    print e

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
            '''
            Checks if any of the filters matches the url.
            Filters can be in regex search or normal string comparison.
            '''
            for filt in filters:
                if ((filt[1] and re.search(filt[0], url, re.IGNORECASE)) or
                    (not filt[1] and filt[0] in url)):
                    return True
            return False
