from django.db import migrations, models
import django.db.models.deletion


def add_placeholder_venues(apps, schema_editor):
    Venue = apps.get_model("teams", "Venue")
    Event = apps.get_model("teams", "Event")

    if Venue.objects.exists():
        default_venue = Venue.objects.first()
    else:
        venues = [
            {
                "name": "YMCA Vallis Road",
                "address_line1": "Vallis Road",
                "address_line2": "",
                "city": "Frome",
                "postcode": "BA11 3EF",
                "url": "https://example.com/ymca-vallis-road",
                "info": "Main court. Enter via reception and head to the sports hall.",
            },
            {
                "name": "Victoria Park Courts",
                "address_line1": "Victoria Park",
                "address_line2": "",
                "city": "Frome",
                "postcode": "BA11 1HJ",
                "url": "https://example.com/victoria-park",
                "info": "Outdoor courts. Bring layers if it gets chilly.",
            },
        ]
        created = [Venue.objects.create(**data) for data in venues]
        default_venue = created[0]

    if default_venue:
        Event.objects.filter(venue__isnull=True).update(venue=default_venue)


class Migration(migrations.Migration):

    dependencies = [
        ("teams", "0005_eventsignup_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="Venue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=140)),
                ("address_line1", models.CharField(max_length=200)),
                ("address_line2", models.CharField(blank=True, max_length=200)),
                ("city", models.CharField(blank=True, max_length=120)),
                ("postcode", models.CharField(max_length=20)),
                ("url", models.URLField(blank=True)),
                ("info", models.TextField(blank=True)),
            ],
        ),
        migrations.AddField(
            model_name="event",
            name="venue",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="events", to="teams.venue"),
        ),
        migrations.RunPython(add_placeholder_venues, migrations.RunPython.noop),
    ]
