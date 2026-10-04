import calendar
from datetime import date

from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from .models import User_info, Hotel


class CustomUserChangeForm(forms.ModelForm):
    """Edits the built-in User's name and email plus the User_info profile fields."""
    phone_no = forms.CharField(max_length=50, required=False)
    city = forms.CharField(max_length=50, required=False)
    country = forms.CharField(max_length=50, required=False)
    address = forms.CharField(max_length=50, required=False)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.profile = User_info.objects.filter(user=self.instance).first() or User_info(user=self.instance)
        if not self.is_bound:
            for field in ('phone_no', 'city', 'country', 'address'):
                self.initial[field] = getattr(self.profile, field) or ''

    def clean_phone_no(self):
        # phone_no is unique, so store "no phone" as NULL rather than ''
        phone_no = self.cleaned_data['phone_no'].strip() or None
        if phone_no and User_info.objects.filter(phone_no=phone_no).exclude(user=self.instance).exists():
            raise forms.ValidationError("This phone number is already used by another account.")
        return phone_no

    def save(self, commit=True):
        user = super().save(commit)
        for field in ('phone_no', 'city', 'country', 'address'):
            setattr(self.profile, field, self.cleaned_data[field])
        if commit:
            self.profile.save()
        return user


class HotelForm(forms.ModelForm):
    class Meta:
        model = Hotel
        fields = ['name', 'country', 'city', 'price_per_night']


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
    card_holder = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'autocomplete': 'cc-name'}))
    card_no = forms.CharField(label="Card number", max_length=23, widget=forms.TextInput(attrs={
        'autocomplete': 'cc-number', 'inputmode': 'numeric', 'placeholder': '1234 5678 9012 3456',
    }))
    expiry = forms.CharField(label="Expiry (MM/YY)", max_length=5, widget=forms.TextInput(attrs={
        'autocomplete': 'cc-exp', 'inputmode': 'numeric', 'placeholder': 'MM/YY',
    }))
    cvc = forms.CharField(label="CVC", max_length=4, widget=forms.TextInput(attrs={
        'autocomplete': 'cc-csc', 'inputmode': 'numeric', 'placeholder': '123',
    }))

    def clean_card_no(self):
        card_no = self.cleaned_data['card_no'].replace(' ', '').replace('-', '')
        if not card_no.isdigit() or len(card_no) != 16:
            raise forms.ValidationError("Card number must be 16 digits.")
        if not luhn_valid(card_no):
            raise forms.ValidationError("Card number is not valid.")
        return card_no

    def clean_expiry(self):
        """Parse MM/YY into the card's last valid day; a card is valid through the end of its expiry month."""
        month, _, year = self.cleaned_data['expiry'].strip().partition('/')
        if not (month.isdigit() and year.isdigit() and 1 <= int(month) <= 12 and len(year) == 2):
            raise forms.ValidationError("Enter the expiry date as MM/YY.")
        year, month = 2000 + int(year), int(month)
        expiry = date(year, month, calendar.monthrange(year, month)[1])
        if expiry < timezone.localdate():
            raise forms.ValidationError("This card has expired.")
        return expiry

    def clean_cvc(self):
        cvc = self.cleaned_data['cvc']
        if not cvc.isdigit() or len(cvc) not in (3, 4):
            raise forms.ValidationError("CVC must be 3 or 4 digits.")
        return cvc
