# Generated by Django 4.2.6 on 2023-12-12 17:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hotel_app1', '0015_alter_hotelbooking_room_preference'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='hotelbooking',
            name='room_preference',
        ),
    ]
