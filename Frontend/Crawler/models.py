from django.db import models

class Page(models.Model):
    url = models.URLField(max_length=2000, required=True)
    urlHash = models.IntegerField(required=True)
    site = models.ForeignKey('explorer.ReferringSite', on_delete=models.CASCADE, required=True)

class VisitedPage(Page):
    pass

class ToVisitPage(Page):
    pass