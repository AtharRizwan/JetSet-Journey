# Generated by Django 4.2.6 on 2023-12-12 15:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hotel_app1', '0012_alter_hotelbooking_zip_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hotelbooking',
            name='hotel',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='hotel_app1.hotel'),
        ),
    ]