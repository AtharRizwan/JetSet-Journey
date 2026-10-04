"""Renames and data moves for the model cleanup; plain field alterations are in 0006."""
import datetime

from django.db import migrations, models
import django.db.models.deletion


def dedupe_profiles(apps, schema_editor):
    """Keep only the newest User_info per user so the field can become one-to-one."""
    User_info = apps.get_model('bookings', 'User_info')
    seen = set()
    for profile in User_info.objects.order_by('user_id', '-id'):
        if profile.user_id in seen:
            profile.delete()
        else:
            seen.add(profile.user_id)


def copy_availability_hotel(apps, schema_editor):
    """Point availability rows at the hotel's primary key instead of its name, dropping duplicate dates."""
    Hotel = apps.get_model('bookings', 'Hotel')
    RoomAvailability = apps.get_model('bookings', 'RoomAvailability')
    hotel_ids = dict(Hotel.objects.values_list('name', 'hotelid'))
    seen = set()
    for row in RoomAvailability.objects.order_by('id'):
        key = (row.name_id, row.date)
        if key in seen:
            row.delete()
            continue
        seen.add(key)
        row.hotel_id = hotel_ids[row.name_id]
        row.save(update_fields=['hotel'])


def fill_stay_dates(apps, schema_editor):
    """Bookings made before stay dates were stored get a placeholder stay of the right length."""
    HotelBooking = apps.get_model('bookings', 'HotelBooking')
    placeholder = datetime.date(2000, 1, 1)
    for booking in HotelBooking.objects.filter(
        models.Q(check_in__isnull=True) | models.Q(check_out__isnull=True)
    ):
        booking.check_in = booking.check_in or placeholder
        booking.check_out = booking.check_in + datetime.timedelta(days=max(booking.no_of_days, 1))
        booking.save(update_fields=['check_in', 'check_out'])


def copy_seat_trips(apps, schema_editor):
    for model_name, trip_field in (('FlightBookedSeats', 'flight'), ('BusBookedSeats', 'bus')):
        Seat = apps.get_model('bookings', model_name)
        for seat in Seat.objects.select_related('booking'):
            setattr(seat, f'{trip_field}_id', getattr(seat.booking, f'{trip_field}_id'))
            seat.save(update_fields=[trip_field])


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0004_hotel_booking_dates_drop_creditcard'),
    ]

    operations = [
        # Profiles: one per user, unused columns dropped.
        migrations.RunPython(dedupe_profiles, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user_info',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to='auth.user'),
        ),
        migrations.RemoveField(model_name='user_info', name='first_name'),
        migrations.RemoveField(model_name='user_info', name='last_name'),
        migrations.RemoveField(model_name='user_info', name='state'),
        migrations.RemoveField(model_name='user_info', name='zip_code'),
        migrations.RemoveField(model_name='user_info', name='email'),

        # Availability: FK to the hotel's primary key instead of its name.
        migrations.AddField(
            model_name='roomavailability',
            name='hotel',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='bookings.hotel'),
        ),
        migrations.RunPython(copy_availability_hotel, migrations.RunPython.noop),
        migrations.RemoveField(model_name='roomavailability', name='name'),
        migrations.AlterField(
            model_name='roomavailability',
            name='hotel',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bookings.hotel'),
        ),
        migrations.RenameField(model_name='roomavailability', old_name='isAvailable', new_name='is_available'),
        migrations.AddConstraint(
            model_name='roomavailability',
            constraint=models.UniqueConstraint(fields=('hotel', 'date'), name='unique_hotel_availability_date'),
        ),

        # Hotel bookings: suite_id -> suite, required stay dates.
        migrations.RenameField(model_name='hotelbooking', old_name='suite_id', new_name='suite'),
        migrations.RunPython(fill_stay_dates, migrations.RunPython.noop),
        migrations.AlterField(model_name='hotelbooking', name='check_in', field=models.DateField()),
        migrations.AlterField(model_name='hotelbooking', name='check_out', field=models.DateField()),
        migrations.AddConstraint(
            model_name='hotelbooking',
            constraint=models.CheckConstraint(check=models.Q(('check_out__gt', models.F('check_in'))), name='hotel_booking_check_out_after_check_in'),
        ),

        # Booked seats: booking_id -> booking, plus the trip so a seat can only be sold once.
        migrations.RenameField(model_name='flightbookedseats', old_name='booking_id', new_name='booking'),
        migrations.RenameField(model_name='busbookedseats', old_name='booking_id', new_name='booking'),
        migrations.AddField(
            model_name='flightbookedseats',
            name='flight',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='bookings.flight'),
        ),
        migrations.AddField(
            model_name='busbookedseats',
            name='bus',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='bookings.bus'),
        ),
        migrations.RunPython(copy_seat_trips, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='flightbookedseats',
            name='flight',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='bookings.flight'),
        ),
        migrations.AlterField(
            model_name='busbookedseats',
            name='bus',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='bookings.bus'),
        ),
        migrations.AddConstraint(
            model_name='flightbookedseats',
            constraint=models.UniqueConstraint(fields=('flight', 'seat_no'), name='unique_flight_seat'),
        ),
        migrations.AddConstraint(
            model_name='busbookedseats',
            constraint=models.UniqueConstraint(fields=('bus', 'seat_no'), name='unique_bus_seat'),
        ),
    ]
