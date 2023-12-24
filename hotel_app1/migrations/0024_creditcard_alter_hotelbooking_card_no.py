# Generated by Django 4.2.6 on 2023-12-14 19:56

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('hotel_app1', '0023_alter_hotelbooking_card_no_delete_creditcard'),
    ]

    operations = [
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
        migrations.AlterField(
            model_name='hotelbooking',
            name='card_no',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, to='hotel_app1.creditcard'),
        ),
    ]