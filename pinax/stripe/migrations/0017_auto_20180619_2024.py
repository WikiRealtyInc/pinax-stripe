# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-06-19 20:24
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pinax_stripe', '0016_auto_20180312_2307'),
    ]

    operations = [
        migrations.CreateModel(
            name='Discount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', models.DateTimeField(blank=True, null=True)),
                ('end', models.DateTimeField(blank=True, null=True)),
                ('coupon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pinax_stripe.Coupon')),
                ('customer', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='pinax_stripe.Customer')),
                ('subscription', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pinax_stripe.Subscription')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='discount',
            unique_together=set([('customer', 'coupon')]),
        ),
    ]