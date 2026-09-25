from datetime import date

from django import forms
from django.contrib.auth.forms import UserChangeForm
from .models import User_info, HotelBooking, Hotel
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

        # Save additional fields to User_info
        profile = User_info.objects.filter(user=user).first() or User_info(user=user)
        # phone_no is unique, so store "no phone" as NULL rather than ''
        profile.phone_no = self.cleaned_data['phone_no'] or None
        profile.city = self.cleaned_data['city']
        profile.country = self.cleaned_data['country']
        profile.address = self.cleaned_data['address']
        if commit:
            profile.save()

        return user

class HotelForm(forms.ModelForm):
    class Meta:
        model = Hotel
        fields = ['name', 'country', 'city', 'price_per_night']

class HotelBookingForm(forms.ModelForm):

    class Meta:
        model = HotelBooking
        fields = '__all__'
        exclude = ['user', 'hotel', 'no_of_days','payment_price']
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

def luhn_valid(number):
    digits = [int(d) for d in number]
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


class PaymentForm(forms.Form):
    """Demo payment form: validates the card details but never stores them."""
    card_holder = forms.CharField(max_length=100)
    card_no = forms.CharField(label="Card number", max_length=23)
    expiry_date = forms.DateField(label="Expiry date", widget=forms.DateInput(attrs={'type': 'date'}))
    cvc = forms.CharField(label="CVC", max_length=4)

    def clean_card_no(self):
        card_no = self.cleaned_data['card_no'].replace(' ', '').replace('-', '')
        if not card_no.isdigit() or len(card_no) != 16:
            raise forms.ValidationError("Card number must be 16 digits.")
        if not luhn_valid(card_no):
            raise forms.ValidationError("Card number is not valid.")
        return card_no

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data['expiry_date']
        if expiry_date < date.today():
            raise forms.ValidationError("This card has expired.")
        return expiry_date

    def clean_cvc(self):
        cvc = self.cleaned_data['cvc']
        if not cvc.isdigit() or len(cvc) not in (3, 4):
            raise forms.ValidationError("CVC must be 3 or 4 digits.")
        return cvc
