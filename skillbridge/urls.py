# urls.py

from django.contrib import admin
from django.urls import path
from core import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('explore/', views.explore, name='explore'),
    path('connect/<int:user_id>/', views.send_request, name='send_request'),
    path('accept/<int:request_id>/', views.accept_request, name='accept_request'),
    path('reject/<int:request_id>/', views.reject_request, name='reject_request'),
    path('chat/<int:user_id>/', views.chat, name='chat'),
    path('profile/<int:user_id>/', views.profile_view, name='profile'),
    path('signup/', views.signup_view, name='signup'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),

    # Notes URLs
    path('courses/<int:course_id>/', views.course_notes, name='course_notes'),
    path('notes/delete/<int:note_id>/', views.delete_note, name='delete_note'),
    path('courses/<int:course_id>/upload/', views.upload_note, name='upload_note'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)