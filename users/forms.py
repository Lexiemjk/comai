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


class finishConfigForm(forms.Form):
    pass