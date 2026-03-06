"""Channels forms — Channel creation and credential configuration."""
from __future__ import annotations

from django import forms

from .models import Channel, ChannelCredential

_INPUT = "w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all"
_CHECK = "rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 h-5 w-5"


class ChannelForm(forms.ModelForm):
    """Form for creating/editing a Channel."""

    class Meta:
        model = Channel
        fields = ["name", "platform"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": _INPUT,
                "placeholder": "Ex: Google Ads — My Face",
            }),
            "platform": forms.Select(attrs={
                "class": _INPUT,
            }),
        }


class ChannelCredentialForm(forms.ModelForm):
    """Form for editing channel credentials."""

    _SECRET_FIELDS = ("client_secret", "refresh_token")

    class Meta:
        model = ChannelCredential
        fields = [
            "customer_id", "developer_token", "client_id",
            "client_secret", "refresh_token", "login_customer_id",
            "access_token", "account_id",
        ]
        widgets = {
            "customer_id": forms.TextInput(attrs={
                "class": _INPUT, "placeholder": "123-456-7890",
            }),
            "developer_token": forms.TextInput(attrs={
                "class": _INPUT, "placeholder": "Token da API",
            }),
            "client_id": forms.TextInput(attrs={
                "class": _INPUT, "placeholder": "xxxx.apps.googleusercontent.com",
            }),
            "client_secret": forms.PasswordInput(attrs={
                "class": _INPUT, "placeholder": "Manter atual (deixe vazio)",
                "autocomplete": "new-password",
            }),
            "refresh_token": forms.PasswordInput(attrs={
                "class": _INPUT, "placeholder": "Manter atual (deixe vazio)",
                "autocomplete": "new-password",
            }),
            "login_customer_id": forms.TextInput(attrs={
                "class": _INPUT, "placeholder": "Opcional — ID da conta MCC",
            }),
            "access_token": forms.TextInput(attrs={
                "class": _INPUT, "placeholder": "Meta Ads Access Token",
            }),
            "account_id": forms.TextInput(attrs={
                "class": _INPUT, "placeholder": "act_123456789",
            }),
        }

    def save(self, commit: bool = True) -> ChannelCredential:
        """Preserve secret fields when the user leaves them blank."""
        instance = super().save(commit=False)
        if self.instance.pk:
            for field in self._SECRET_FIELDS:
                if not self.cleaned_data.get(field):
                    setattr(instance, field, getattr(
                        ChannelCredential.objects.get(pk=self.instance.pk), field,
                    ))
        if commit:
            instance.save()
        return instance
