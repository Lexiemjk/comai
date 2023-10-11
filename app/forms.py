from django import forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column


from users.models import CustomUser
from .models import Location, Categorie, Service
class ConfigForm(forms.ModelForm):
    class Meta :
        model = CustomUser
        fields = ['first_name', 'last_name']

class LocationParametersForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ['name','owner', 'categorie', 'services']

    name = forms.CharField()
    categorie = forms.ModelChoiceField(queryset=Categorie.objects.all(), empty_label=None)
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.all(),
        widget=forms.CheckboxSelectMultiple
    )

    def __init__(self, *args, **kwargs):
        super(LocationParametersForm, self).__init__(*args, **kwargs)

        self.fields['owner'].widget = forms.HiddenInput()

        self.helper = FormHelper(self)

        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6 mb-0'),
                Column('categorie', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'services',
            Submit('submit', 'Submit')
        )

class fileDemoForm(forms.Form):
    title = forms.CharField(max_length=50)
    file = forms.FileField()