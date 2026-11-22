from django.db import migrations, models


def crear_configuracion_predeterminada(apps, schema_editor):
    ConfiguracionVencimiento = apps.get_model("inventario", "ConfiguracionVencimiento")
    ConfiguracionVencimiento.objects.using(schema_editor.connection.alias).get_or_create(
        pk=1,
        defaults={
            "perecible_aviso_1": 15,
            "perecible_aviso_2": 7,
            "perecible_aviso_3": 3,
            "despensa_aviso": 30,
        },
    )


def eliminar_configuracion_predeterminada(apps, schema_editor):
    ConfiguracionVencimiento = apps.get_model("inventario", "ConfiguracionVencimiento")
    ConfiguracionVencimiento.objects.using(schema_editor.connection.alias).filter(pk=1).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("inventario", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConfiguracionVencimiento",
            fields=[
                ("id_configuracion", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ("perecible_aviso_1", models.PositiveSmallIntegerField(default=15)),
                ("perecible_aviso_2", models.PositiveSmallIntegerField(default=7)),
                ("perecible_aviso_3", models.PositiveSmallIntegerField(default=3)),
                ("despensa_aviso", models.PositiveSmallIntegerField(default=30)),
            ],
            options={
                "db_table": "configuracion_vencimientos",
                "verbose_name": "configuración de vencimientos",
                "verbose_name_plural": "configuración de vencimientos",
            },
        ),
        migrations.RunPython(
            crear_configuracion_predeterminada,
            eliminar_configuracion_predeterminada,
        ),
    ]
