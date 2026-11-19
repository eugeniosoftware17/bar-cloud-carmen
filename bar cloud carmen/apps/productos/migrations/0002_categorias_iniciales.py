from django.db import migrations

CATEGORIAS = ['Bebidas', 'Comida', 'Snacks', 'Otros']


def crear(apps, schema_editor):
    Categoria = apps.get_model('productos', 'Categoria')
    for orden, nombre in enumerate(CATEGORIAS, start=1):
        Categoria.objects.get_or_create(nombre=nombre, defaults={'orden': orden})


def borrar(apps, schema_editor):
    Categoria = apps.get_model('productos', 'Categoria')
    Categoria.objects.filter(nombre__in=CATEGORIAS, productos__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(crear, borrar),
    ]
