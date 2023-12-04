from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .forms import loginForm
from .models import Hotel, RoomAvailability

# Create your views here.
def base(request):
    user = authenticate(username="ali", password="ali@123")
    context = {
        'user': user,
    }
    return render(request, 'base.html', context)

def home(request):
    return render(request, 'home.html')
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
    print(search_params)
    print(hotels)
    context = {
         'city_country': city_country,
         'check_in_date': check_in_date,
         'check_out_date': check_out_date,
         'hotels' : hotels,
         'count' : count
     }


    return render(request, 'searched_hotels.html', context)


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
            form.save()
            messages.success(request, "A new user has been created")
    else:
        form = UserCreationForm()
    
    context = {
        'form': form,
    }

    return render(request, 'register.html', context)

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