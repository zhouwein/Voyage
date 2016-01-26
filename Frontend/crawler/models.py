from django.db import models
import hashlib

class Page(models.Model):
    url = models.URLField(max_length=2000)
    urlHash = models.BigIntegerField()

    '''def save( self, *args, **kw ):
        m = hashlib.md5()
        m.update(self.url)
        self.urlHash = long(m.hexdigest(), 16)
        super(Page, self).save( *args, **kw )'''

class VisitedPage(Page):
    pass

class ToVisitPage(Page):
    pass