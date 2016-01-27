#!/usr/bin/env python
import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..','Frontend')))
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'Frontend.settings'
from crawler.models import VisitedPage
from crawler.models import ToVisitPage
from explorer.models import SourceSite

if __name__ == "__main__":
    django.setup()
    VisitedPage.objects.all().delete()
    ToVisitPage.objects.all().delete()
    SourceSite.objects.all().delete()

    source_site = SourceSite(url="example.com", name="example")
    source_site.save()
    ToVisitPage(url="example.com", urlHash=0, sourceSite=source_site).save()

    start = time.time()
    for line in sys.stdin:
        type = line[0]

        if(type == "0"):
            page = ToVisitPage.objects.filter(sourceSite=source_site).first()
            page.delete()
            continue
        arg = line[2:].strip()
        if(type == "1"):
            VisitedPage.objects.filter(url=arg, sourceSite=source_site).count()
        elif(type == "2"):
            VisitedPage(url=arg, urlHash=0, sourceSite=source_site).save()
            ToVisitPage(url=arg, urlHash=0, sourceSite=source_site).save()

    print "elapsed time: " + str((time.time() - start))