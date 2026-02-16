from django.db import migrations, models
import datetime
from django.utils import timezone


def set_default_ends_at(apps, schema_editor):
    Event = apps.get_model("teams", "Event")
    for event in Event.objects.filter(ends_at__isnull=True):
        if event.starts_at:
            event.ends_at = event.starts_at + datetime.timedelta(hours=1)
        else:
            event.ends_at = timezone.now()
        event.save(update_fields=["ends_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("teams", "0003_alter_wallettransaction_stripe_payment_intent_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="ends_at",
            field=models.DateTimeField(null=True),
        ),
        migrations.RunPython(set_default_ends_at, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="event",
            name="ends_at",
            field=models.DateTimeField(),
        ),
    ]
