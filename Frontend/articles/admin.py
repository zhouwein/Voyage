from django.contrib import admin
from nested_inline.admin import NestedStackedInline, NestedTabularInline, NestedModelAdmin
from articles.models import Article, Version, Author, SourceSite, Keyword, SourceTwitter
import re
# Register your models here.

import yaml, os
import difflib

class AuthorInline(NestedTabularInline):
    model = Author
    readonly_fields = ('name',)
    fk_name = 'version'
    extra = 0

class SourceSiteInline(NestedTabularInline):
    model = SourceSite
    readonly_fields = ('url', 'domain', 'anchor_text', 'matched', 'local',)
    fk_name = 'version'
    extra = 0

class KeywordInline(NestedTabularInline):
    model = Keyword
    readonly_fields = ('name',)
    fk_name = 'version'
    extra = 0

class SourceTwitterInline(NestedTabularInline):
    model = SourceTwitter
    readonly_fields = ('name', 'matched',)
    fk_name = 'version'
    extra = 0

class VersionInline(NestedStackedInline):
    model = Version
    fields = ('title', 'highlighted_text', 'text_hash', 'language', 'date_added', 'date_last_seen', 'date_published', 'found_by',)
    readonly_fields = ('title', 'highlighted_text', 'text_hash', 'language', 'date_added', 'date_last_seen', 'date_published', 'found_by',)
    inlines = [AuthorInline, SourceSiteInline, KeywordInline, SourceTwitterInline]
    extra = 0

    def highlighted_text(self, obj):
        tag_front=" <strong><mark>"
        tag_end = "</mark></strong> "
        text = obj.text

        versions = list(obj.article.version_set.all())
        index = versions.index(obj)
        if (index > 0 and len(versions) - 1 >= index):
            prev_text = versions[index - 1].text
            diff = ''
            for line in difflib.unified_diff(re.split('(\s|\n)', prev_text), re.split('(\s|\n)', text), n=10000):
                for prefix in ('---', '+++', '@@'):
                    if line.startswith(prefix):
                        break
                else:
                    if '\n' in line:
                        if line[0] == '+' or line[0] == '-':
                            diff += line[1:]
                        else:
                            diff += line
                    elif line[0] == '+':
                        diff += ' <span style="background-color: CornflowerBlue"><strong>' + line[1:] + '</strong>&nbsp;</span>'
                    elif line[0] == '-':
                        diff += ' <span style="text-decoration: line-through">' + line[1:] + '&nbsp;</span> '
                    else:
                        diff += line
            text = diff
        for key in obj.keyword_set.all():
            pattern = re.compile('([^a-z]' + key.name + '[^a-z])', re.IGNORECASE)
            result = pattern.subn(tag_front+key.name+tag_end, text)
            text = result[0]
        return '<div style="font-size: 1.2em">' + text + '</div>'

class ArticleAdmin(NestedModelAdmin):
    fieldsets = [
        ('Basic',               {'fields': ['id', 'domain', 'show_urls']})
        ]

    inlines = [VersionInline]

    list_display = ('get_url', 'title', 'get_authors', 'get_keywords', 'get_source_sites', 'get_language', 'get_date_added', 'get_date_published', 'get_date_last_seen', 'link_options')
    search_fields = ['title', 'text']
    list_filter = ['domain']
    readonly_fields = ('id', 'url', 'domain', 'title', 'language', 'found_by', 'date_added', 'date_last_seen', 'date_published', 'text', 'highlighted_text', 'show_urls', 'text_hash')
    actions_on_top = True
    list_per_page = 20

    def get_url(self, obj):
        link_short = obj.url
        if len(link_short) > 50:
            link_short = link_short[:50]+"..."
        return format('<a href="%s" target="_blank">%s</a>' % (obj.url, link_short))

    get_url.short_description = 'URL'
    get_url.admin_order_field = 'domain'
    get_url.allow_tags = True

    def get_authors(self, obj):
        authors = ''
        for ath in obj.version_set.last().author_set.all():
            authors += ath.name + ', '
        return authors[:-2]

    get_authors.short_description = 'Authors'

    def get_keywords(self, obj):
        keywords = ''
        for key in obj.version_set.last().keyword_set.all():
            keywords += key.name + ',<br>'
        return keywords[:-5]

    get_keywords.short_description = 'Matched Keywords'
    get_keywords.admin_order_field = 'version__keyword__name'
    get_keywords.allow_tags = True

    def get_source_sites(self, obj):
        sources = ''
        for src in obj.version_set.last().sourcesite_set.all():
            if src.matched and not src.local:
                if 'http://www.' in src.url:
                    link = 'http://' + src.url[11:]
                else:
                    link = src.url
                link_short = link[7:]
                if len(link_short) > 30:
                    link_short = link_short[:30]+"..."

                sources += format('<a href="%s" target="_blank">%s</a>' % (link, link_short))
                sources += '<br>'
        return sources[:-4]

    get_source_sites.short_description = 'Matched Source Sites'
    get_source_sites.admin_order_field = 'version__sourcesite__url'
    get_source_sites.allow_tags = True

  #   def get_source_twitters(self, obj):
  #       accounts = ''
  #       for acc in obj.version_set.last().sourcetwitter_set.all():
  #           if acc.matched:
        # accounts += acc + '<br>'
  #       return accounts[:-4]

  #   get_source_twitters.short_description = 'Matched Source Twitter Accounts'
  #   get_source_twitters.allow_tags = True

    def get_language(self, obj):
        return obj.language

    get_language.short_description = 'Language'
    get_language.admin_order_field = 'version__language'
    get_language.allow_tags = True

    def get_date_added(self, obj):
        return obj.date_added

    get_date_added.short_description = 'Date Added'
    get_date_added.admin_order_field = 'version__date_added'
    get_date_added.allow_tags = True

    def get_date_published(self, obj):
        return obj.date_published

    get_date_published.short_description = 'Date published'
    get_date_published.admin_order_field = 'version__date_published'
    get_date_published.allow_tags = True

    def get_date_last_seen(self, obj):
        return obj.date_last_seen

    get_date_last_seen.short_description = 'Date last seen'
    get_date_last_seen.admin_order_field = 'version__date_last_seen'
    get_date_last_seen.allow_tags = True

    def highlighted_text(self, obj):
        tag_front=" <strong><mark>"
        tag_end = "</mark></strong> "
        text = obj.text
        for key in obj.version_set.last().keyword_set.all():
            pattern = re.compile('([^a-z]' + key.name + '[^a-z])', re.IGNORECASE)
            result = pattern.subn(tag_front+key.name+tag_end, text)
            text = result[0]
        return text

    highlighted_text.short_description = 'Highlighted Text'
    highlighted_text.allow_tags = True

    def show_urls(self, obj):
        urls = ''
        for url in obj.url_set.all():
            urls += format('<a href="%s" target="_blank">%s</a><br />' % (url.name, url.name))
        return urls

    show_urls.short_description = 'URLs'
    show_urls.allow_tags = True

    def link_url(self, obj):
        return format('<a href="%s" target="_blank">%s</a>' % (obj.url, obj.url))

    link_url.allow_tags = True
    link_url.admin_order_field = 'url'
    link_url.short_description = "URL"

    def link_options(self, obj):
        return format((
            '<a href="/admin/articles/article/%s">Details</a><br />' +\
            '<a href="/articles/warc/%s">Donwload Warc</a><br />' +\
            '<a href="/articles/pdf/%s">View PDF</a><br />' +\
            '<a href="/articles/img/%s">View Screenshot</a><br />' +\
            '<div>Urls: %i<br />Versions: %i</div>') %
            (
                str(obj.pk), obj.url.replace('/', '_'),
                obj.url.replace('/', '_'),
                obj.url.replace('/', '_'),
                obj.url_set.count(),
                obj.version_set.count()))

    link_options.allow_tags = True
    link_options.short_description = "Options"


admin.site.register(Article, ArticleAdmin)
