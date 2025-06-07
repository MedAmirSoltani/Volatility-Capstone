# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser, Preferences

class CustomUserCreationForm(UserCreationForm):
    birth_date = forms.DateField(required=False)

    class Meta:
        model = CustomUser
        fields = ['username','first_name','last_name', 'email', 'birth_date', 'password1', 'password2']

class CustomAuthenticationForm(AuthenticationForm):
    class Meta:
        model = CustomUser
        


class CustomUserChangeForm(forms.ModelForm):
    birth_date = forms.DateField(required=False)
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'birth_date']



class PreferencesForm(forms.ModelForm):
    class Meta:
        model = Preferences
        fields = ['risk_tolerance', 'investment_horizon', 'investment_objective', 'knowledge_experience', 'sectors', 'available_funds']

from .models import ForumTopic, ForumComment

class ForumTopicForm(forms.ModelForm):
    class Meta:
        model = ForumTopic
        fields = ['topic']

class ForumCommentForm(forms.ModelForm):
    class Meta:
        model = ForumComment
        fields = ['comment']
        

class CsvUploadForm(forms.Form):
    csv_file = forms.FileField(label='Upload CSV File')        