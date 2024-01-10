from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms

from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ("email",)


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ("email",)


class AnswerPreferenceForm(forms.Form):
    answerGenerationPreferences = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple
    )

    def __init__(self, *args, openai_answers=None, **kwargs):
        super(AnswerPreferenceForm, self).__init__(*args, **kwargs)

        choices = []
        if openai_answers:
            for key, value in openai_answers.items():
                # Create a tuple of (key, display_value) and append to choices
                display_value = f"{dict(CustomUser.ANSWER_GENERATION_CHOICES)[key]}: {value}"
                choices.append((key, display_value))

        self.fields['answerGenerationPreferences'].choices = choices


class GooglePreferencesForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['is_google_managed', 'answerGenerationPreferences']
        widgets = {
            'answerGenerationPreferences': forms.Select(choices=CustomUser.ANSWER_GENERATION_CHOICES,
                                                        attrs={'class': 'form-select'}),
            'is_google_managed': forms.CheckboxInput(
                attrs={'class': 'form-check-input', 'type': 'checkbox', 'role': 'switch',
                       'id': 'flexSwitchCheckDefault'})
        }


class finishConfigForm(forms.Form):
    pass
