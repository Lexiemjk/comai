# Generated by Django 4.0.4 on 2023-08-10 12:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='first_connection',
            field=models.BooleanField(default=True),
        ),
    ]
