from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("teams", "0006_venue_and_event_venue"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="event",
            name="location",
        ),
    ]
