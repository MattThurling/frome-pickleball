from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("teams", "0004_event_ends_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventsignup",
            name="status",
            field=models.CharField(
                choices=[
                    ("yes", "Yes"),
                    ("maybe", "Maybe"),
                    ("no", "No"),
                    ("waitlist", "Waitlist"),
                ],
                default="yes",
                max_length=10,
            ),
        ),
    ]
