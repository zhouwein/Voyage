from django.db import models

# Create your models here.

class Article(models.Model):
    domain = models.URLField(max_length=2000, verbose_name="Referring Site")
    title = models.CharField(max_length=200, blank=True)
    text = models.TextField(max_length=None, blank=True)
    text_hash = models.CharField(max_length=100, blank=True)
    language = models.CharField(max_length=200, blank=True)
    date_added = models.DateTimeField('Date Added', blank=True, null=True)
    date_last_seen = models.DateTimeField('Date Last Seen', blank=True, null=True)
    date_published = models.DateTimeField('Date Published', blank=True, null=True)
    date_modified = models.DateTimeField('Date Modified', blank=True, null=True)
    found_by = models.CharField(max_length=100, blank=True)

    def __unicode__(self):
        if len(self.title) >= 30:
            return self.title[:27] + '...'
        return self.title

    @property
    def url(self):
        return self.url_set.first().name
    

class Url(models.Model):
    article = models.ForeignKey(Article)
    name = models.URLField(max_length=2000, verbose_name="URL")

    def __unicode__(self):
        return self.name


class Author(models.Model):
    article = models.ForeignKey(Article)
    name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name


class SourceSite(models.Model):
    article = models.ForeignKey(Article)
    url = models.CharField(max_length=2000)
    domain = models.URLField(max_length=2000, verbose_name="Source Site")
    anchor_text = models.CharField(max_length=2000, verbose_name="Anchor Text")
    matched = models.BooleanField(default=False)
    local = models.BooleanField(default=True)

    def __unicode__(self):
        return self.url


class SourceTwitter(models.Model):
    article = models.ForeignKey(Article)
    name = models.CharField(max_length=200)
    matched = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name


class Keyword(models.Model):
    article = models.ForeignKey(Article)
    name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name
