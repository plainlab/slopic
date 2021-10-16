# Generated by Django 3.2.8 on 2021-10-16 04:25

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
            name='Athlete',
            fields=[
                ('id', models.PositiveIntegerField(primary_key=True, serialize=False)),
                ('birthday', models.DateField()),
                ('hr_zone_threshold_1', models.FloatField(default=0.6)),
                ('hr_zone_threshold_2', models.FloatField(default=0.7)),
                ('hr_zone_threshold_3', models.FloatField(default=0.8)),
                ('hr_zone_threshold_4', models.FloatField(default=0.9)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]