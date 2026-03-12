"""Redesign AIProvider: one API key per provider, separate text/image model fields."""

from django.db import migrations, models


def clear_old_providers(apps, schema_editor):
    """Delete all existing AIProvider rows — the old schema is incompatible."""
    AIProvider = apps.get_model("core", "AIProvider")
    AIProvider.objects.all().delete()


class Migration(migrations.Migration):

    atomic = False  # Required for SQLite schema changes after RunPython

    dependencies = [
        ("core", "0014_aiprovider"),
    ]

    operations = [
        # 1. Clear existing data (duplicates would violate new unique_together)
        migrations.RunPython(clear_old_providers, migrations.RunPython.noop),
        # 2. Remove old fields
        migrations.RemoveField(model_name="aiprovider", name="model_name"),
        migrations.RemoveField(model_name="aiprovider", name="capabilities"),
        # 3. Add new fields
        migrations.AddField(
            model_name="aiprovider",
            name="text_model",
            field=models.CharField(
                blank=True, default="", max_length=100, verbose_name="Modelo de Texto",
            ),
        ),
        migrations.AddField(
            model_name="aiprovider",
            name="image_model",
            field=models.CharField(
                blank=True, default="", max_length=100, verbose_name="Modelo de Imagem",
            ),
        ),
        # 4. Add unique constraint
        migrations.AlterUniqueTogether(
            name="aiprovider",
            unique_together={("project", "provider")},
        ),
    ]
