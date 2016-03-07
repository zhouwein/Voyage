from django.contrib import admin
from articles.models import Article, Author, SourceSite, Keyword, SourceTwitter
import re
# Register your models here.

import yaml, os

class AuthorInline(admin.TabularInline):
    model = Author
    readonly_fields = ('name',)
    extra = 0

class SourceSiteInline(admin.TabularInline):
    model = SourceSite
    readonly_fields = ('url', 'domain', 'anchor_text', 'matched', 'local',)
    extra = 0

class KeywordInline(admin.TabularInline):
    model = Keyword
    readonly_fields = ('name',)
    extra = 0

class SourceTwitterInline(admin.TabularInline):
    model = SourceTwitter
    readonly_fields = ('name', 'matched',)
    extra = 0

class ArticleAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Basic',               {'fields': ['domain', 'show_urls']}),
        ('Content',               {'fields': ['title', 'language', 'highlighted_text']}),
        ('Dates', {'fields': ['date_added', 'date_last_seen', 'date_published', 'date_modified']}),
        ('Other Information', {'fields': ['id', 'found_by', 'text_hash']})
        ]

    inlines = [AuthorInline, SourceSiteInline, KeywordInline, SourceTwitterInline]

    list_display = ('get_url', 'title', 'get_authors', 'get_keywords', 'get_source_sites', 'get_source_twitters', 'language', 'date_added', 'date_published', 'date_modified', 'link_options')
    search_fields = ['title', 'text']
    list_filter = ['domain', 'keyword__name', 'sourcesite__domain', 'sourcetwitter__name', 'language']
    readonly_fields = ('id', 'url', 'domain', 'title', 'language', 'found_by', 'date_added', 'date_last_seen', 'date_published', 'date_modified', 'text', 'highlighted_text', 'show_urls', 'text_hash')
    ordering = ['-date_added']
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

    def get_keywords(self, obj):
        keywords = ''
        for key in obj.keyword_set.all():
            keywords += key.name + ',<br>'
        return keywords[:-5]

    get_keywords.short_description = 'Matched Keywords'
    get_keywords.admin_order_field = 'keyword__name'
    get_keywords.allow_tags = True

    def get_source_sites(self, obj):
        sources = ''
        for src in obj.sourcesite_set.all():
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
    get_source_sites.admin_order_field = 'sourcesite__url'
    get_source_sites.allow_tags = True

    def get_source_twitters(self, obj):
        accounts = ''
        for acc in obj.sourcetwitter_set.all():
            if acc.matched:
		accounts += acc + '<br>'
        return accounts[:-4]

    get_source_twitters.short_description = 'Matched Source Twitter Accounts'
    get_source_twitters.admin_order_field = 'sourcetwitter__name'
    get_source_twitters.allow_tags = True

    def get_authors(self, obj):
        authors = ''
        for ath in obj.author_set.all():
            authors += ath.name + ', '
        return authors[:-2]

    get_authors.short_description = 'Authors'
    get_authors.admin_order_field = 'author__name'

    def highlighted_text(self, obj):
        tag_front=" <strong><mark>"
        tag_end = "</mark></strong> "
        text = obj.text
        for key in obj.keyword_set.all():
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
        return format(('<a href="/admin/articles/article/%s">Details</a><br>' +\
                       '<a href="/articles/warc/%s">Donwload Warc</a><br>' +\
                       '<a href="/articles/pdf/%s">View PDF</a><br>' +\
                       '<a href="/articles/img/%s">View Screenshot</a>') % (str(obj.pk), obj.url.replace('/', '_'), obj.url.replace('/', '_'), obj.url.replace('/', '_')))

    link_options.allow_tags = True
    link_options.short_description = "Options"


admin.site.register(Article, ArticleAdmin)
