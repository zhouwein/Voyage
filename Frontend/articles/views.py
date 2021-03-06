from django.shortcuts import render, HttpResponse
from django.template import RequestContext, loader
from articles.models import Article, Keyword, SourceSite, Author, SourceTwitter
import sys, os, time, json, yaml, urllib
import common
import warc_creator
import subprocess

def index(request):
    if not request.user.is_authenticated():
        return redirect('/admin/login/?next=%s' % request.path)

    latest_article_list = Article.objects.order_by('date_added')

    context = {'latest_article_list': latest_article_list}
    return render(request, 'articles/index.html', context)


def getJson(request):
    articles = {}
    for art in Article.objects.all():      
        articles[art.url] = {'site': art.domain, 'title': art.title, 
                             'date_added': str(art.date_added),
                             'date_published': str(art.date_published),
                             'matched_keywords': [],
                             'matched_source_sites': [], 'matched_source_twitter_accounts': [], 'authors': []}

    for key in Keyword.objects.all():
        articles[key.article.url]['matched_keywords'].append(key.name)
    for src in SourceSite.objects.all():
        articles[src.article.url]['matched_source_sites'].append({'url':src.url, 
                                                             'site': src.domain, 'matched': src.matched})
    for src in SourceTwitter.objects.all():
        articles[src.article.url]['matched_source_twitter_accounts'].append({'name':src.name,
                                                             'matched': src.matched})
    for ath in Author.objects.all():
        articles[ath.article.url]['authors'].append(ath.name)

    res = HttpResponse(json.dumps(articles, indent=4, sort_keys=True))
    res['Content-Disposition'] = format('attachment; filename=articles-%s.json' 
                                        % time.strftime("%Y%m%d-%H%M%S"))
    return res

def getWarc(request, filename):
    try:
        config = common.get_config()['warc']
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../', config['dir'] + "/" + config['article_subdir']))
        filename_ext = path + "/" + filename + ".warc.gz"
        warc = open(filename_ext, "rb")
        res = HttpResponse(warc, content_type="application/force-download")
        warc.close()

        # To inspect details for the below code, see http://greenbytes.de/tech/tc2231/
        if u'WebKit' in request.META['HTTP_USER_AGENT']:
            # Safari 3.0 and Chrome 2.0 accepts UTF-8 encoded string directly.
            filename_header = 'filename=%s' % (filename + ".warc.gz").encode('utf-8')
        elif u'MSIE' in request.META['HTTP_USER_AGENT']:
            # IE does not support internationalized filename at all.
            # It can only recognize internationalized URL, so we do the trick via routing rules.
            filename_header = ''
        else:
            # For others like Firefox, we follow RFC2231 (encoding extension in HTTP headers).
            filename_header = 'filename*=UTF-8\'\'%s' % urllib.quote((filename + ".warc.gz").encode('utf-8'))
        res['Content-Disposition'] = 'attachment; ' + filename_header

        return res
    except IOError:
        # if the warc file doesn't exist, display 404 page to user, and enqueue the url
        # to task queue to retry generating warc
        url = filename.replace("_", "/")
        warc_creator.enqueue_article(url)
        return render(request, '404/404.html')
    

def getPDF(request, filename):
    try:
        config = common.get_config()['pdf']
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../', config['dir'] + "/" + config['article_subdir']))
        filename_ext = path + "/" + filename + ".pdf"
        pdf = open(filename_ext, "rb")
        # open pdf in browser instead of downloading it
        res = HttpResponse(pdf, content_type="application/pdf")
        pdf.close()
        return res

    except IOError:
        # if the pdf file doesn't exist, display 404 page to user, and enqueue the url
        # to task queue retry generating pdf
        url = filename.replace("_", "/")
        warc_creator.enqueue_article(url)
        return render(request, '404/404.html')

def getImg(request, filename):

    try:
        config = common.get_config()['pdf']
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../', config['dir'] + "/" + config['article_subdir']))
        filename_ext = path + "/" + filename + ".png"
        pdf = open(filename_ext, "rb")
        # open img in browser instead of downloading it
        res = HttpResponse(pdf, content_type="image/png")
        pdf.close()
        return res
    except IOError:
        # if the img file doesn't exist, display 404 page to user, and enqueue the url
        # to task queue to retry generating img
        url = filename.replace("_", "/")
        warc_creator.enqueue_article(url)
        return render(request, '404/404.html')

