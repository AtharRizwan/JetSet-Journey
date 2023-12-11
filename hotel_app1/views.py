from django.shortcuts import render, redirect
from django.contrib.auth import update_session_auth_hash
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib import messages
from .forms import loginForm, CustomUserChangeForm 
from .models import Hotel, RoomAvailability, User_info
from django.contrib.auth.models import User, Group
from django.shortcuts import get_object_or_404
import requests
import json  
from django.contrib.gis.geoip2 import GeoIP2

# Create your views here.
def base(request):
    user = authenticate(username="ali", password="ali@123")
    context = {
        'user': user,
    }
    return render(request, 'base.html', context)

def home(request):
    username = None
    if request.user.is_authenticated:
        first_name = request.user.first_name
        context = {'first_name': first_name,
               
        }
    else: context = {}
    return render(request, 'home.html', context)

    
def search(request):
    if request.method == 'POST':
        city_country = request.POST.get('city_country')
        check_in_date = request.POST.get('check_in_date', '')
        check_out_date = request.POST.get('check_out_date', '')
        print(f"city_country: {city_country}, check_in_date: {check_in_date}, check_out_date: {check_out_date}")
        # Store the search parameters in the session
        request.session['search_params'] = {
            'city_country': city_country,
            'check_in_date': check_in_date,
            'check_out_date': check_out_date,
        }

        # Redirect to the searched_hotels view
        return redirect('searched_hotels')

    return render(request, 'search.html')

# Function to get current IP Address
def ip_addr(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:

       ip = x_forwarded_for.split(',')[0]

    else:

       ip = request.META.get('REMOTE_ADDR')
       return ip

# Function to get Location by IP address
def get_ip_geolocation_data():
    ip_address = ip_addr
    api_key = '86c68403d31c4be0b0e11dc4e6fb4dd7'
    api_url = 'https://ipgeolocation.abstractapi.com/v1/?api_key=' + api_key

    print(ip_address)

    response = requests.get(api_url)

    return response.content

def get_weather_data(city_country):
     # API key
    api_key = '85a91f9d5f17440fab5120026231112'

    weather_url = f'http://api.weatherapi.com/v1/current.json?key={api_key}&q={city_country}&aqi=no'
    weather_response = requests.get(weather_url)

     # Check if the weather request was successful (status code 200)
    if weather_response.status_code == 200:
        # Parse JSON response
        weather_data = weather_response.json()
        return weather_data
    else:
        # If the request was not successful, print the error code
        return (f"Error fetching weather data: {weather_response.status_code}")


def searched_hotels(request):
    # Retrieve search parameters from the session
    search_params = request.session.get('search_params', {})
    city_country = search_params.get('city_country','')
    check_in_date = search_params.get('check_in_date', '')
    check_out_date = search_params.get('check_out_date', '')

    # Fetch hotels based on the search parameters
    get_query = f" SELECT h1.* FROM hotel_app1_hotel AS h1 JOIN hotel_app1_roomavailability AS h2 ON h1.name = h2.name_id WHERE h1.city = '{city_country}' AND h2.date >= '{check_in_date}' AND h2.date <= '{check_out_date}' GROUP BY h1.name"
    hotels = Hotel.objects.raw(get_query)
    count = len(list(hotels))

    # Extracting countr and region
    geolocation_json = get_ip_geolocation_data()
    geolocation_data = json.loads(geolocation_json)
    country = geolocation_data['country']
    region = geolocation_data['region']

    print(country)
    print(region)
    context = {
         'city_country': city_country,
         'check_in_date': check_in_date,
         'check_out_date': check_out_date,
         'hotels' : hotels,
         'count' : count,
         'weather_data': get_weather_data(city_country),
         'user_country' : country,
         'user_region' : region,
     }


    return render(request, 'searched_hotels.html', context)

def add_hotel(request):
    return render(request, 'add_hotel.html')



def hotel_details(request, id):
    req_hotel = Hotel.objects.filter(hotelid = id)
    print(req_hotel)
    context = {
        'req_hotel': req_hotel
    }
    return render(request, 'hotel_details.html', context)


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            group = Group.objects.get(name='customers')

            # Add the user to the group
            group.user_set.add(user)

            messages.success(request, "A new user has been created")
    else:
        form = UserCreationForm()
    
    context = {
        'form': form,
    }

    return render(request, 'register.html', context)

def change_profile(request):
    try:
        user_info_instance = User_info.objects.get(user=request.user)
    except User_info.DoesNotExist:
        user_info_instance = None

    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()

            # Update or create User_info instance
            if user_info_instance:
                # If User_info instance exists, update it
                user_info_instance.city = form.cleaned_data['city']
                user_info_instance.country = form.cleaned_data['country']
                user_info_instance.phone_no = form.cleaned_data['phone_no']
                user_info_instance.address = form.cleaned_data['address']
                user_info_instance.save()
            else:
                # If User_info instance does not exist, create a new one
                User_info.objects.create(
                    user=request.user,
                    city=form.cleaned_data['city'],
                    country=form.cleaned_data['country'],
                    phone_no=form.cleaned_data['phone_no'],
                    address=form.cleaned_data['address'],
                    # Add other fields as needed
                )

            messages.success(request, "Your profile has been updated")
    else:
        form = CustomUserChangeForm(instance=request.user, initial={
            'city': user_info_instance.city if user_info_instance else '',
            'country': user_info_instance.country if user_info_instance else '',
            'phone_no': user_info_instance.phone_no if user_info_instance else '',
            'address': user_info_instance.address if user_info_instance else '',
            # Add other fields as needed
        })

    context = {
        'form': form,
        'username': request.user.first_name,
    }

    return render(request, 'change_profile.html', context)

def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return redirect('change_password')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {
        'form': form
    })

def log_in(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Redirect to a success page.
            return redirect('home')
        
        else:
            return redirect('log_in')
    else:
        return render(request, 'log_in.html')
def log_out(request):
    logout(request)
    return redirect('log_in')