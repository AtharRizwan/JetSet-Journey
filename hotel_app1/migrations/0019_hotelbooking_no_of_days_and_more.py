# Generated by Django 4.2.6 on 2023-12-13 06:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotel_app1', '0018_alter_hotelbooking_room_preference'),
    ]

    operations = [
        migrations.AddField(
            model_name='hotelbooking',
            name='no_of_days',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='hotelbooking',
            name='price_to_be_paid',
            field=models.IntegerField(default=0),
        ),
    ]