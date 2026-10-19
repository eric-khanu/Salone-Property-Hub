from django.urls import path
from . import views
app_name='advertisements'
urlpatterns=[path('create/',views.create,name='create'),path('<int:pk>/click/',views.click,name='click')]
