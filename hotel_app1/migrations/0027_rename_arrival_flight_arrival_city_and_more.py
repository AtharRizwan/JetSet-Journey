# Generated by Django 4.2.6 on 2023-12-26 19:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotel_app1', '0026_airline_flight_user_info_email_user_info_first_name_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='flight',
            old_name='arrival',
            new_name='arrival_city',
        ),
        migrations.RenameField(
            model_name='flight',
            old_name='departure',
            new_name='departure_city',
        ),
        migrations.AddField(
            model_name='flight',
            name='departure_date',
            field=models.DateField(default='2022-12-30'),
            preserve_default=False,
        ),
    ]