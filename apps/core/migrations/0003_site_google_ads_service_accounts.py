"""Add Google Ads credentials and Service Account key fields to Site."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_site_owner"),
    ]

    operations = [
        migrations.AddField(
            model_name="site",
            name="google_ads_customer_id",
            field=models.CharField(
                blank=True,
                help_text="Formato: 123-456-7890 (encontre em ads.google.com no canto superior direito)",
                max_length=30,
                verbose_name="Google Ads Customer ID",
            ),
        ),
        migrations.AddField(
            model_name="site",
            name="google_ads_developer_token",
            field=models.CharField(
                blank=True,
                help_text="Token obtido no MCC \u2192 Ferramentas \u2192 Centro de API",
                max_length=100,
                verbose_name="Developer Token",
            ),
        ),
        migrations.AddField(
            model_name="site",
            name="google_ads_client_id",
            field=models.CharField(
                blank=True,
                help_text="ID do cliente OAuth2 do Google Cloud Console",
                max_length=200,
                verbose_name="OAuth Client ID",
            ),
        ),
        migrations.AddField(
            model_name="site",
            name="google_ads_client_secret",
            field=models.CharField(
                blank=True,
                help_text="Secret do cliente OAuth2 do Google Cloud Console",
                max_length=200,
                verbose_name="OAuth Client Secret",
            ),
        ),
        migrations.AddField(
            model_name="site",
            name="google_ads_refresh_token",
            field=models.CharField(
                blank=True,
                help_text="Token de atualiza\u00e7\u00e3o gerado via fluxo de consentimento OAuth2",
                max_length=500,
                verbose_name="OAuth Refresh Token",
            ),
        ),
        migrations.AddField(
            model_name="site",
            name="google_ads_login_customer_id",
            field=models.CharField(
                blank=True,
                help_text="Opcional \u2014 ID da conta MCC gerenciadora, se aplic\u00e1vel",
                max_length=30,
                verbose_name="Login Customer ID (MCC)",
            ),
        ),
        migrations.AddField(
            model_name="site",
            name="gsc_service_account_key",
            field=models.TextField(
                blank=True,
                help_text="Conte\u00fado completo do JSON da Service Account do Google Search Console",
                verbose_name="GSC Service Account JSON",
            ),
        ),
        migrations.AddField(
            model_name="site",
            name="ga4_service_account_key",
            field=models.TextField(
                blank=True,
                help_text="Conte\u00fado completo do JSON da Service Account do GA4 Data API",
                verbose_name="GA4 Service Account JSON",
            ),
        ),
    ]
