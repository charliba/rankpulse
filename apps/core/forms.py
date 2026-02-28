"""Core forms — Site, Event, KPI and Integrations management."""
from __future__ import annotations

from django import forms

from .models import GA4EventDefinition, KPIGoal, Site

_INPUT = "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all"
_TEXTAREA = f"{_INPUT} resize-none font-mono"
_CHECK = "rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 h-5 w-5"


class SiteForm(forms.ModelForm):
    """Form for creating/editing a Site."""

    class Meta:
        model = Site
        fields = [
            "name",
            "domain",
            "url",
            "description",
            "ga4_measurement_id",
            "ga4_api_secret",
            "ga4_property_id",
            "gsc_verified",
            "gsc_site_url",
            "sitemap_url",
            "robots_txt_url",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
                "placeholder": "Meu Site",
            }),
            "domain": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
                "placeholder": "meusite.com.br",
            }),
            "url": forms.URLInput(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
                "placeholder": "https://meusite.com.br",
            }),
            "description": forms.Textarea(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all resize-none",
                "rows": 3,
                "placeholder": "Descrição do site (opcional)",
            }),
            "ga4_measurement_id": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
                "placeholder": "G-XXXXXXXXXX",
            }),
            "ga4_api_secret": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
                "placeholder": "API Secret (opcional)",
            }),
            "ga4_property_id": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
                "placeholder": "Property ID (opcional)",
            }),
            "gsc_verified": forms.CheckboxInput(attrs={
                "class": "rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 h-5 w-5",
            }),
            "gsc_site_url": forms.URLInput(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
                "placeholder": "https://meusite.com.br",
            }),
            "sitemap_url": forms.URLInput(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
                "placeholder": "https://meusite.com.br/sitemap.xml",
            }),
            "robots_txt_url": forms.URLInput(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
                "placeholder": "https://meusite.com.br/robots.txt",
            }),
        }


class GA4EventForm(forms.ModelForm):
    """Form for creating/editing a GA4 Event Definition."""

    class Meta:
        model = GA4EventDefinition
        fields = [
            "event_name",
            "description",
            "trigger_page",
            "priority",
            "is_conversion",
            "server_side",
            "is_implemented",
            "js_snippet",
        ]
        widgets = {
            "event_name": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
                "placeholder": "Ex: sign_up, purchase, generate_lead",
            }),
            "description": forms.Textarea(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all resize-none",
                "rows": 2,
                "placeholder": "O que esse evento rastreia?",
            }),
            "trigger_page": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
                "placeholder": "/checkout, /obrigado, etc.",
            }),
            "priority": forms.Select(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
            }),
            "is_conversion": forms.CheckboxInput(attrs={
                "class": "rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 h-5 w-5",
            }),
            "server_side": forms.CheckboxInput(attrs={
                "class": "rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 h-5 w-5",
            }),
            "is_implemented": forms.CheckboxInput(attrs={
                "class": "rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 h-5 w-5",
            }),
            "js_snippet": forms.Textarea(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm font-mono focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all resize-none",
                "rows": 4,
                "placeholder": "gtag('event', 'sign_up', { ... })",
            }),
        }


class KPIGoalForm(forms.ModelForm):
    """Form for creating/editing a KPI Goal."""

    class Meta:
        model = KPIGoal
        fields = [
            "metric_name",
            "source",
            "period",
            "target_value",
            "current_value",
            "unit",
        ]
        widgets = {
            "metric_name": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
                "placeholder": "Sessões Orgânicas",
            }),
            "source": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
                "placeholder": "GA4, GSC, Admin",
            }),
            "period": forms.Select(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
            }),
            "target_value": forms.NumberInput(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
                "placeholder": "1000",
            }),
            "current_value": forms.NumberInput(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
                "placeholder": "0",
            }),
            "unit": forms.TextInput(attrs={
                "class": "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all",
                "placeholder": "R$, %, unidades",
            }),
        }


class IntegrationsForm(forms.ModelForm):
    """Form for configuring Google Ads, GA4 and GSC per-site credentials."""

    # Password fields that must preserve existing values when left blank.
    _SECRET_FIELDS = ("google_ads_client_secret", "google_ads_refresh_token")

    class Meta:
        model = Site
        fields = [
            # GA4
            "ga4_measurement_id",
            "ga4_api_secret",
            "ga4_property_id",
            # GSC
            "gsc_site_url",
            "gsc_verified",
            # Google Ads
            "google_ads_customer_id",
            "google_ads_developer_token",
            "google_ads_client_id",
            "google_ads_client_secret",
            "google_ads_refresh_token",
            "google_ads_login_customer_id",
            # Service Account Keys
            "gsc_service_account_key",
            "ga4_service_account_key",
        ]
        widgets = {
            "ga4_measurement_id": forms.TextInput(attrs={
                "class": _INPUT, "placeholder": "G-XXXXXXXXXX",
            }),
            "ga4_api_secret": forms.TextInput(attrs={
                "class": _INPUT, "placeholder": "Ex: pFUeJMUfTWuMwim6NYe0Uw",
            }),
            "ga4_property_id": forms.TextInput(attrs={
                "class": _INPUT, "placeholder": "Ex: 526327250",
            }),
            "gsc_site_url": forms.URLInput(attrs={
                "class": _INPUT, "placeholder": "https://seusite.com.br",
            }),
            "gsc_verified": forms.CheckboxInput(attrs={"class": _CHECK}),
            "google_ads_customer_id": forms.TextInput(attrs={
                "class": _INPUT, "placeholder": "123-456-7890",
            }),
            "google_ads_developer_token": forms.TextInput(attrs={
                "class": _INPUT, "placeholder": "Token da API do Google Ads",
            }),
            "google_ads_client_id": forms.TextInput(attrs={
                "class": _INPUT, "placeholder": "xxxx.apps.googleusercontent.com",
            }),
            "google_ads_client_secret": forms.PasswordInput(attrs={
                "class": _INPUT, "placeholder": "Manter atual (deixe vazio)",
                "autocomplete": "new-password",
            }),
            "google_ads_refresh_token": forms.PasswordInput(attrs={
                "class": _INPUT, "placeholder": "Manter atual (deixe vazio)",
                "autocomplete": "new-password",
            }),
            "google_ads_login_customer_id": forms.TextInput(attrs={
                "class": _INPUT, "placeholder": "Opcional — ID da conta MCC",
            }),
            "gsc_service_account_key": forms.Textarea(attrs={
                "class": _TEXTAREA, "rows": 4,
                "placeholder": '{"type": "service_account", "project_id": "...", ...}',
            }),
            "ga4_service_account_key": forms.Textarea(attrs={
                "class": _TEXTAREA, "rows": 4,
                "placeholder": '{"type": "service_account", "project_id": "...", ...}',
            }),
        }

    def save(self, commit: bool = True) -> Site:
        """Preserve secret fields when the user leaves them blank."""
        instance = super().save(commit=False)
        if self.instance.pk:
            for field in self._SECRET_FIELDS:
                if not self.cleaned_data.get(field):
                    # Restore the value from the database
                    setattr(instance, field, getattr(
                        Site.objects.get(pk=self.instance.pk), field,
                    ))
        if commit:
            instance.save()
        return instance
