from django.db import migrations

def backfill(apps, schema_editor):
    Recipient = apps.get_model('recipients', 'Recipient')
    ConfigPeriodicite = apps.get_model('recipients', 'ConfigPeriodicite')
    for r in Recipient.objects.all():
        config = ConfigPeriodicite.objects.filter(capacite_kg=r.capacite_kg).first()
        if config:
            r.config_periodicite = config
            r.save(update_fields=['config_periodicite'])

class Migration(migrations.Migration):
    dependencies = [
        ('recipients', '0008_recipient_config_periodicite')
    ]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]