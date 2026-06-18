"""Forms for the plugin settings page."""

from django import forms

from netbox_eol.models import MATCH_TIER_CHOICES, EolSettings

TIER_CHOICES = [(value, label) for value, label in MATCH_TIER_CHOICES if value != "none"]


class EolSettingsForm(forms.ModelForm):
    api_key = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False, attrs={"class": "form-control"}),
        help_text="eol.network integration key. Leave blank to keep the current key.",
    )
    auto_accept_tiers = forms.MultipleChoiceField(
        choices=TIER_CHOICES,
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select"}),
        help_text="Match tiers auto-accepted without review.",
    )
    review_tiers = forms.MultipleChoiceField(
        choices=TIER_CHOICES,
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select"}),
        help_text="Match tiers surfaced for human review.",
    )

    class Meta:
        model = EolSettings
        fields = [
            "base_url",
            "sync_enabled",
            "sync_interval_hours",
            "sync_targets",
            "auto_accept_tiers",
            "review_tiers",
        ]
        widgets = {
            "base_url": forms.URLInput(attrs={"class": "form-control"}),
            "sync_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "sync_interval_hours": forms.NumberInput(attrs={"class": "form-control"}),
            "sync_targets": forms.Select(attrs={"class": "form-select"}),
        }

    def save(self, commit=True):
        obj = super().save(commit=False)
        key = self.cleaned_data.get("api_key")
        if key:
            obj.set_api_key(key)
        if commit:
            obj.save()
        return obj
