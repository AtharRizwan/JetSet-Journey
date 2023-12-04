from django import forms

class loginForm(forms.Form):
    username = forms.CharField(max_length=70)
    password = forms.CharField(max_length=70, widget = forms.PasswordInput)