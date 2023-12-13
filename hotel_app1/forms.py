from django import forms
from django.contrib.auth.forms import UserChangeForm
from .models import User_info, HotelBooking
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

class add_hotel(forms.Form):
    name = forms.CharField(max_length=70)
    country = forms.CharField(max_length=70)
    city = forms.CharField(max_length=70)

class HotelBookingForm(forms.ModelForm):

    class Meta:
        model = HotelBooking
        fields = '__all__'
        exclude = ['user', 'hotel', 'no_of_days','price_to_be_paid']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'zip_code': forms.NumberInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'room_preference': forms.Select(attrs={'class': 'form-control'})
        }
