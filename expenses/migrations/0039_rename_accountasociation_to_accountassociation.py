from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("expenses", "0038_upload_upload_status_upload_upload_type"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="AccountAsociation",
            new_name="AccountAssociation",
        ),
    ]
