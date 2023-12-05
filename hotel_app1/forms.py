from django import forms
from django.contrib.auth.forms import UserChangeForm
from .models import User_info
class loginForm(forms.Form):
    username = forms.CharField(max_length=70)
    password = forms.CharField(max_length=70, widget = forms.PasswordInput)



class CustomUserChangeForm(UserChangeForm):
    phone_no = forms.CharField(max_length=20, required=False)
    city = forms.CharField(max_length=20, required=False)
    country = forms.CharField(max_length=20, required=False)
    address = forms.CharField(max_length=20, required=False)
    class Meta(UserChangeForm.Meta):
        fields = ['email', 'first_name', 'last_name', 'phone_no', 'city', 'country', 'address']

    def save(self, commit=True):
        user = super().save(commit)

        # Save additional fields to UserProfile
        profile, created = User_info.objects.get_or_create(user=user)
        profile.phone_no = self.cleaned_data['phone_no']
        profile.city = self.cleaned_data['city']
        profile.country = self.cleaned_data['country']
        profile.address = self.cleaned_data['address']
        # Set other fields as needed
        if commit:
            profile.save()

        return user
