from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from .views import RegistroView

urlpatterns = [
    path('api/signup/', RegistroView.as_view(), name='signup'),
    path('api/login/', obtain_auth_token, name='login'),
]