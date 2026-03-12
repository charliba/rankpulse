# Generated manually — Add Google OAuth fields to Site model.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_site_google_ads_service_accounts"),
    ]

    operations = [
        migrations.AddField(
            model_name="site",
            name="google_refresh_token",
            field=models.TextField(
                blank=True,
                help_text="OAuth refresh token for GA4 + GSC APIs",
                verbose_name="Google Refresh Token",
            ),
        ),
        migrations.AddField(
            model_name="site",
            name="google_access_token",
            field=models.TextField(
                blank=True,
                help_text="Cached OAuth access token",
                verbose_name="Google Access Token",
            ),
        ),
    ]
