# Generated by Django 4.2.6 on 2023-12-26 19:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hotel_app1', '0001_squashed_0028_alter_flight_departure_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flight',
            name='departure_date',
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name='hotel',
            name='hotelid',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
    ]
