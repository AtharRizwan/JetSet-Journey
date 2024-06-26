# Generated by Django 4.2.6 on 2023-12-28 02:52

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Airline',
            fields=[
                ('airline_id', models.AutoField(primary_key=True, serialize=False)),
                ('airline_name', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Flight',
            fields=[
                ('flightid', models.AutoField(primary_key=True, serialize=False)),
                ('departure_date', models.DateField(default='2023-12-30')),
                ('departure_time', models.TimeField(default='12:00:00')),
                ('departure_city', models.CharField(max_length=250)),
                ('destination_city', models.CharField(max_length=250)),
                ('price', models.IntegerField(default=100)),
                ('airline', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='hotel_app1.airline')),
            ],
        ),
        migrations.CreateModel(
            name='Hotel',
            fields=[
                ('hotelid', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=250, unique=True)),
                ('country', models.CharField(max_length=250)),
                ('city', models.CharField(max_length=250)),
                ('price_per_night', models.IntegerField(default=100)),
            ],
        ),
        migrations.CreateModel(
            name='Suites',
            fields=[
                ('suiteid', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=250)),
                ('description', models.CharField(max_length=250)),
                ('bedrooms', models.IntegerField(default=100)),
                ('size', models.IntegerField(default=100)),
                ('price_per_night', models.IntegerField(default=100)),
            ],
        ),
        migrations.CreateModel(
            name='User_info',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_no', models.CharField(max_length=50, unique=True)),
                ('city', models.CharField(max_length=50)),
                ('country', models.CharField(max_length=50)),
                ('address', models.CharField(max_length=50)),
                ('first_name', models.CharField(default='', max_length=100)),
                ('last_name', models.CharField(default='', max_length=100)),
                ('state', models.CharField(default='', max_length=50)),
                ('zip_code', models.IntegerField(default=10000)),
                ('email', models.EmailField(default='', max_length=254)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='RoomAvailability',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('isAvailable', models.BooleanField(default=True)),
                ('name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='hotel_app1.hotel', to_field='name')),
            ],
        ),
        migrations.CreateModel(
            name='HotelServices',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service', models.CharField(max_length=50)),
                ('hotel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='hotel_app1.hotel')),
            ],
        ),
        migrations.CreateModel(
            name='HotelBooking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('no_of_days', models.IntegerField(default=0)),
                ('payment_price', models.IntegerField(default=0)),
                ('hotel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='hotel_app1.hotel')),
                ('suite_id', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='hotel_app1.suites')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='FlightBooking',
            fields=[
                ('booking_id', models.AutoField(primary_key=True, serialize=False)),
                ('num_seats', models.IntegerField(default=0)),
                ('payment_price', models.IntegerField(default=0)),
                ('flight', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='hotel_app1.flight')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='FlightBookedSeats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('seat_no', models.IntegerField()),
                ('booking_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='hotel_app1.flightbooking')),
            ],
        ),
        migrations.CreateModel(
            name='CreditCard',
            fields=[
                ('card_no', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('bank_name', models.CharField(default='', max_length=50)),
                ('cvc', models.IntegerField()),
                ('expiry_date', models.DateField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
