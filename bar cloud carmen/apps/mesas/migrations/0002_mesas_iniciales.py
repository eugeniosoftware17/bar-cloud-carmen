from django.db import migrations


def crear(apps, schema_editor):
    Mesa = apps.get_model('mesas', 'Mesa')
    if not Mesa.objects.exists():
        Mesa.objects.bulk_create([Mesa(nombre=f'Mesa {i}', orden=i) for i in range(1, 9)])


class Migration(migrations.Migration):

    dependencies = [
        ('mesas', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(crear, migrations.RunPython.noop),
    ]
