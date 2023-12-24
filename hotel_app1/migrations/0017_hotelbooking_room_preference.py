# Generated by Django 4.2.6 on 2023-12-12 20:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotel_app1', '0016_remove_hotelbooking_room_preference'),
    ]

    operations = [
        migrations.AddField(
            model_name='hotelbooking',
            name='room_preference',
            field=models.CharField(blank=True, choices=[('1', 'Standard'), ('2', 'Deluxe'), ('3', 'Suite')], max_length=20, null=True),
        ),
    ]