# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0018_auto_20160117_1730'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='date_last_seen',
            field=models.DateTimeField(null=True, verbose_name=b'Date Last Seen', blank=True),
            preserve_default=True,
        ),
    ]
