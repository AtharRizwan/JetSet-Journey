from django.shortcuts import render, redirect
from django.contrib.auth import update_session_auth_hash
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib import messages
from .forms import loginForm, CustomUserChangeForm, HotelBookingForm, PaymentForm
from .models import Hotel, RoomAvailability, User_info, HotelBooking, CreditCard
from .models import Airline, Flight, FlightBooking, FlightBookedSeats
from django.contrib.auth.models import User, Group
from django.shortcuts import get_object_or_404
import requests
import json  
from django.contrib.gis.geoip2 import GeoIP2
from datetime import datetime

# Create your views here.
def base(request):
    user = authenticate(username="ali", password="ali@123")
    context = {
        'user': user,
    }
    return render(request, 'base.html', context)

# Function to get country activities
def get_country_activities(country):
    url = "https://travel-info-api.p.rapidapi.com/country-activities"

    querystring = {"country":country}

    headers = {
	    "X-RapidAPI-Key": "6ffd060abfmsh6e4245644fb2d43p10650djsn6a88c2b5417a",
	    "X-RapidAPI-Host": "travel-info-api.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

    return(response.json())

def home(request):
    username = None
    if request.user.is_authenticated:
        first_name = request.user.first_name
        context = {'first_name': first_name,
               
        }
    else: context = {}
    print(get_country_activities("Pakistan"))
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

def search_flights(request):
    if request.method == 'POST':
        departure_city = request.POST.get('departure_city')
        destination_city = request.POST.get('destination_city')
        departure_date = request.POST.get('departure_date', '')
        airline_service = request.POST.get('airline_service')
        # Store the search parameters in the session
        request.session['flight_search_params'] = {
            'departure_city': departure_city,
            'destination_city': destination_city,
            'departure_date': departure_date,
            'airline_service': airline_service,
        }

        # Redirect to the flights_informations view
        return redirect('flights_informations')
    
    return render(request, 'search_flights.html')
    
def flights_informations(request):
    # Retrieve search parameters from the session
    flight_search_params = request.session.get('flight_search_params', {})
    departure_city = flight_search_params.get('departure_city','')
    destination_city = flight_search_params.get('destination_city', '')
    departure_date = flight_search_params.get('departure_date', '')
    airline_service = flight_search_params.get('airline_service', '')

    # Fetch flights based on the search parameters
    get_query = f" SELECT * FROM hotel_app1_flight JOIN hotel_app1_airline USING (airline_id) WHERE departure_city = '{departure_city}' AND destination_city = '{destination_city}' AND departure_date = '{departure_date}' AND airline_name = '{airline_service}'"
    flights = Hotel.objects.raw(get_query)
    count = len(list(flights))

    context = {
         'departure_city': departure_city,
         'destination_city': destination_city,
         'departure_date': departure_date,
         'airline_service': airline_service,
         'flights' : flights,
         'count' : count,
     }

    return render(request, 'flights_informations.html', context)

def flight_details(request, id):
    req_flight = Hotel.objects.filter(hotelid = id)
    print(req_flight)
    context = {
        'req_flight': req_flight
    }
    return render(request, 'flight_details.html', context)

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

def booking(request, id):
    req_hotel = Hotel.objects.filter(hotelid=id).first()
    # Getting data from the session
    search_params = request.session.get('search_params', {})
    check_in_date = search_params.get('check_in_date', '')
    check_out_date = search_params.get('check_out_date', '')
    # Convert the strings to datetime objects
    check_in_date = datetime.strptime(check_in_date, "%Y-%m-%d")
    check_out_date = datetime.strptime(check_out_date, "%Y-%m-%d")
    no_of_days = (check_out_date - check_in_date).days

    if request.method == 'POST':
        form = HotelBookingForm(request.POST)
        if form.is_valid():
            # Store relevant data in session
            
            room_preference = form.cleaned_data['room_preference']
            print(room_preference)
            if(room_preference == "Standard"):
                   payment_price = req_hotel.price_per_night * no_of_days
            elif(room_preference == "Deluxe"):
                    payment_price = (req_hotel.price_per_night * 1.25) * no_of_days
            else:
                    payment_price = (req_hotel.price_per_night * 1.50) * no_of_days
            request.session['booking_data'] = {
                'user': request.user.id,
                'hotel': req_hotel.hotelid,
                'no_of_days': no_of_days,
                'room_preference': room_preference,
                'payment_price': payment_price,
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'address': form.cleaned_data['address'],
                'city': form.cleaned_data['city'],
                'state': form.cleaned_data['state'],
                'zip_code': form.cleaned_data['zip_code'],
                'phone': form.cleaned_data['phone'],
                'email': form.cleaned_data['email'],
                'special_requests': form.cleaned_data['special_requests'],
            }
            
            messages.success(request, "Form Validated Successfully")
            return redirect('payment')
        else:
            print(form.errors)
    else:
        form = HotelBookingForm()

    context = {
        'form': form,
        'req_hotel': req_hotel
    }

    return render(request, 'booking.html', context)


def payment(request):
    # Retrieve data from session
    booking_data = request.session.get('booking_data', {})

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            # Save the PaymentForm instance
            payment_instance = form.save(commit=False)
            
            # Ensure that user_id is set for the CreditCard instance
            payment_instance.user_id = booking_data.get('user', '')
            payment_instance.save()

            # Create and save HotelBooking instance
            hotel_booking_instance = HotelBooking.objects.create(
                user_id=booking_data.get('user', ''),
                hotel_id=booking_data.get('hotel', ''),
                no_of_days=booking_data.get('no_of_days', ''),
                payment_price=booking_data.get('payment_price', ''),
                first_name=booking_data.get('first_name', ''),
                last_name=booking_data.get('last_name', ''),
                address=booking_data.get('address', ''),
                city=booking_data.get('city', ''),
                state=booking_data.get('state', ''),
                zip_code=booking_data.get('zip_code', ''),
                phone=booking_data.get('phone', ''),
                email=booking_data.get('email', ''),
                room_preference=booking_data.get('room_preference', ''),
                special_requests=booking_data.get('special_requests', ''),
            )

            # Clear session data after successful processing
            del request.session['booking_data']

            # Continue with the rest of your payment processing logic
            messages.success(request, "Payment successful!")
            return redirect('payment')
        else:
            messages.error(request, "Payment form is invalid. Please check the entered information.")
    else:
        form = PaymentForm()

    context = {
        'form': form,
    }
    return render(request, 'payment.html', context)




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
            messages.error(request, 'Invalid Username or Password.')
            return redirect('log_in')
    else:
        return render(request, 'log_in.html')
def log_out(request):
    logout(request)
    return redirect('log_in')

def all_users(request):
    # This is equivalent to JOIN operator in SQL
    all_users_info = User_info.objects.select_related('user')
    print(all_users_info)
    context = {
        'all_users_info': all_users_info
    }
    return render(request, 'all_users.html', context)

def all_bookings(request):
    # HotelBooking.objects.all().delete()
    all_bookings_info = HotelBooking.objects.select_related('hotel').all()
    context = {
        'all_bookings_info': all_bookings_info
    }
    return render(request, 'all_bookings.html', context)

def search_buses(request):
    if request.method == 'POST':
        departure_city = request.POST.get('departure_city')
        destination_city = request.POST.get('destination_city')
        departure_date = request.POST.get('departure_date', '')
        bus_service = request.POST.get('airline_service')
        # Store the search parameters in the session
        request.session['flight_search_params'] = {
            'departure_city': departure_city,
            'destination_city': destination_city,
            'departure_date': departure_date,
            'bus_service': bus_service,
        }

        # Redirect to the flights_informations view
        return redirect('flights_informations')
    
    return render(request, 'search_flights.html')
    
def flights_informations(request):
    # Retrieve search parameters from the session
    flight_search_params = request.session.get('flight_search_params', {})
    departure_city = flight_search_params.get('departure_city','')
    destination_city = flight_search_params.get('destination_city', '')
    departure_date = flight_search_params.get('departure_date', '')
    airline_service = flight_search_params.get('airline_service', '')

    # Fetch flights based on the search parameters
    get_query = f" SELECT * FROM hotel_app1_flight JOIN hotel_app1_airline USING (airline_id) WHERE departure_city = '{departure_city}' AND destination_city = '{destination_city}' AND departure_date = '{departure_date}' AND airline_name = '{airline_service}'"
    flights = Hotel.objects.raw(get_query)
    count = len(list(flights))

    context = {
         'departure_city': departure_city,
         'destination_city': destination_city,
         'departure_date': departure_date,
         'airline_service': airline_service,
         'flights' : flights,
         'count' : count,
     }

    return render(request, 'flights_informations.html', context)

def flight_details(request, id):
    req_flight = Hotel.objects.filter(hotelid = id)
    print(req_flight)
    context = {
        'req_flight': req_flight
    }
    return render(request, 'flight_details.html', context)
