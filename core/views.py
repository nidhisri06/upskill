from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Profile, Message, PhoneOTP
import random


def home(request):
    return render(request, "index.html")

def signup_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        phone = request.POST.get("phone")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("signup")

        # Delete old OTP if exists
        PhoneOTP.objects.filter(phone_number=phone).delete()

        otp = str(random.randint(100000, 999999))
        PhoneOTP.objects.create(phone_number=phone, otp=otp)

        request.session['signup_data'] = {
            "username": username,
            "email": email,
            "password": password,
            "phone": phone
        }

        print("OTP is:", otp)  # Demo purpose

        return redirect("verify_otp")

    return render(request, "signup.html")


def verify_otp(request):
    signup_data = request.session.get("signup_data")

    if not signup_data:
        return redirect("signup")

    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        phone = signup_data["phone"]

        try:
            otp_obj = PhoneOTP.objects.get(phone_number=phone)
        except PhoneOTP.DoesNotExist:
            messages.error(request, "OTP expired")
            return redirect("signup")

        if otp_obj.otp == entered_otp:

            # Prevent duplicate user creation
            if User.objects.filter(username=signup_data["username"]).exists():
                user = User.objects.get(username=signup_data["username"])
            else:
                user = User.objects.create_user(
                    username=signup_data["username"],
                    email=signup_data["email"],
                    password=signup_data["password"]
                )

            # Update profile (auto created by signal)
            profile = user.profile
            profile.phone_number = phone
            profile.is_phone_verified = True
            profile.save()

            otp_obj.delete()
            del request.session["signup_data"]

            login(request, user)
            return redirect("dashboard")

        else:
            messages.error(request, "Invalid OTP")

    return render(request, "verify_otp.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password")

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def dashboard(request):
    profile = request.user.profile

    received_requests = Connection.objects.filter(
        receiver=request.user,
        status='pending'
    )

    sent_requests = Connection.objects.filter(
        sender=request.user,
        status='pending'
    )

    connections = Connection.objects.filter(
        Q(sender=request.user, status='accepted') |
        Q(receiver=request.user, status='accepted')
    )

    return render(request, 'dashboard.html', {
        'profile': profile,
        'received_requests': received_requests,
        'sent_requests': sent_requests,
        'connections': connections
    })


@login_required
def edit_profile(request):
    profile = request.user.profile

    if request.method == "POST":
        profile.bio = request.POST.get('bio')
        profile.skills_offered = request.POST.get('skills_offered')
        profile.skills_wanted = request.POST.get('skills_wanted')

        if request.FILES.get('profile_picture'):
            profile.profile_picture = request.FILES.get('profile_picture')

        profile.save()
        return redirect('profile', user_id=request.user.id)

    return render(request, 'edit_profile.html', {'profile': profile})


@login_required
def explore(request):
    search_query = request.GET.get('skill')

    profiles = Profile.objects.exclude(user=request.user)

    if search_query:
        profiles = profiles.filter(
            Q(skills__icontains=search_query) |
            Q(skills_icontains=search_query)
        )

    return render(request, 'explore.html', {
        'profiles': profiles,
        'search_query': search_query
    })


@login_required
def send_request(request, user_id):
    receiver = User.objects.get(id=user_id)

    if not Connection.objects.filter(sender=request.user, receiver=receiver).exists():
        Connection.objects.create(sender=request.user, receiver=receiver)

    return redirect('explore')


@login_required
def accept_request(request, request_id):
    connection = Connection.objects.get(id=request_id)
    connection.status = 'accepted'
    connection.save()
    return redirect('dashboard')


@login_required
def reject_request(request, request_id):
    connection = Connection.objects.get(id=request_id)
    connection.delete()
    return redirect('dashboard')


@login_required
def chat(request, user_id):
    other_user = User.objects.get(id=user_id)

    is_connected = Connection.objects.filter(
        Q(sender=request.user, receiver=other_user, status='accepted') |
        Q(sender=other_user, receiver=request.user, status='accepted')
    )

    if not is_connected.exists():
        return redirect('dashboard')

    if request.method == "POST":
        content = request.POST.get('content')
        if content:
            Message.objects.create(
                sender=request.user,
                receiver=other_user,
                content=content
            )
        return redirect('chat', user_id=user_id)

    messages_list = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).order_by('timestamp')

    return render(request, 'chat.html', {
        'other_user': other_user,
        'messages': messages_list
    })


@login_required
def profile_view(request, user_id):
    user = User.objects.get(id=user_id)
    profile = user.profile

    return render(request, 'profile.html', {
        'profile_user': user,
        'profile': profile
    })

def dashboard(request):
    profile = request.user.profile
    completion = 0

    if profile.bio:
        completion += 20
    if profile.profile_pic:
        completion += 20
    if profile.skills:
        completion += 20
    if profile.phone:
        completion += 20
    if profile.phone_verified:
        completion += 20

    context = {
        'profile': profile,
        'completion': completion
    }
    return render(request, 'dashboard.html', context)