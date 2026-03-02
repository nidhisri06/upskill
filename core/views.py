# views.py
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Profile, Message, PhoneOTP, Connection, Course, Note
import random

# ---------------- HOME ----------------
def home(request):
    return render(request, "index.html")


# ---------------- SIGNUP ----------------
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

        # Generate OTP
        otp = str(random.randint(100000, 999999))
        PhoneOTP.objects.create(phone_number=phone, otp=otp)

        # Store signup data in session
        request.session['signup_data'] = {
            "username": username,
            "email": email,
            "password": password,
            "phone": phone,
            "otp": otp
        }

        return redirect("verify_otp")

    return render(request, "signup.html")


# ---------------- VERIFY OTP ----------------
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

            # Create user safely
            if User.objects.filter(username=signup_data["username"]).exists():
                user = User.objects.get(username=signup_data["username"])
            else:
                user = User(username=signup_data["username"], email=signup_data["email"])
                user.set_password(signup_data["password"])  # <-- important!
                user.save()

            # Update profile (auto-created by signal)
            profile = user.profile
            profile.phone = phone
            profile.phone_verified = True
            profile.save()

            otp_obj.delete()
            del request.session["signup_data"]

            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid OTP")

    return render(request, "verify_otp.html", {"signup_data": signup_data})


# ---------------- LOGIN / LOGOUT ----------------
def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password")

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


# ---------------- DASHBOARD ----------------
@login_required
def dashboard(request):
    users = User.objects.exclude(id=request.user.id)
    pending_requests = Connection.objects.filter(receiver=request.user, accepted=False)
    connections = Connection.objects.filter(accepted=True).filter(
        Q(sender=request.user) | Q(receiver=request.user)
    )
    courses = Course.objects.all()  # All courses for notes section

    context = {
        "users": users,
        "pending_requests": pending_requests,
        "connections": connections,
        "courses": courses,
    }

    return render(request, "dashboard.html", context)


# ---------------- EDIT PROFILE ----------------
@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == "POST":
        profile.bio = request.POST.get('bio')
        profile.skills = request.POST.get('skills')
        if request.FILES.get('profile_pic'):
            profile.profile_pic = request.FILES.get('profile_pic')
        profile.save()
        return redirect('profile', user_id=request.user.id)
    return render(request, 'edit_profile.html', {'profile': profile})


# ---------------- EXPLORE ----------------
@login_required
def explore(request):
    search_query = request.GET.get('skill')
    profiles = Profile.objects.exclude(user=request.user)
    if search_query:
        profiles = profiles.filter(Q(skills__icontains=search_query))
    return render(request, 'explore.html', {'profiles': profiles, 'search_query': search_query})


# ---------------- CONNECTIONS ----------------
@login_required
def send_request(request, user_id):
    receiver = get_object_or_404(User, id=user_id)
    if receiver != request.user:
        Connection.objects.get_or_create(sender=request.user, receiver=receiver, defaults={'accepted': False})
    return redirect('dashboard')


@login_required
def accept_request(request, request_id):
    connection = get_object_or_404(Connection, id=request_id)
    connection.accepted = True
    connection.save()
    return redirect('dashboard')


@login_required
def reject_request(request, request_id):
    connection = get_object_or_404(Connection, id=request_id)
    connection.delete()
    return redirect('dashboard')


# ---------------- CHAT ----------------
@login_required
def chat(request, user_id):
    other_user = get_object_or_404(User, id=user_id)

    is_connected = Connection.objects.filter(
        Q(sender=request.user, receiver=other_user, accepted=True) |
        Q(sender=other_user, receiver=request.user, accepted=True)
    )
    if not is_connected.exists():
        return redirect('dashboard')

    if request.method == "POST":
        content = request.POST.get('content')
        if content:
            Message.objects.create(sender=request.user, receiver=other_user, content=content)
        return redirect('chat', user_id=user_id)

    messages_list = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).order_by('timestamp')

    return render(request, 'chat.html', {'other_user': other_user, 'messages': messages_list})


# ---------------- PROFILE ----------------
@login_required
def profile_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    profile = user.profile
    return render(request, 'profile.html', {'profile_user': user, 'profile': profile})


# ---------------- NOTES ----------------
@login_required
def course_notes(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    notes = Note.objects.filter(course=course).order_by("-uploaded_at")

    if request.method == "POST":
        title = request.POST.get("title")
        pdf = request.FILES.get("pdf")
        if pdf and pdf.name.lower().endswith(".pdf"):
            Note.objects.create(course=course, title=title, pdf=pdf, uploaded_by=request.user)
            return redirect("course_notes", course_id=course.id)
        else:
            messages.error(request, "Please upload a PDF file.")

    return render(request, "course_notes.html", {"course": course, "notes": notes})


@login_required
def delete_note(request, note_id):
    note = get_object_or_404(Note, id=note_id)
    if note.uploaded_by == request.user:
        note.delete()
    else:
        messages.error(request, "You cannot delete this note.")
    return redirect("course_notes", course_id=note.course.id)

@login_required
def upload_note(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        title = request.POST.get("title")
        pdf = request.FILES.get("pdf")
        if pdf and pdf.name.lower().endswith(".pdf"):
            Note.objects.create(course=course, title=title, pdf=pdf, uploaded_by=request.user)
            return redirect("course_notes", course_id=course.id)
        else:
            messages.error(request, "Please upload a PDF file.")

    return render(request, "upload_note.html", {"course": course})