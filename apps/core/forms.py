"""Core forms — Site and Event management."""
from __future__ import annotations

from django import forms

from .models import GA4EventDefinition, KPIGoal, Site


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
