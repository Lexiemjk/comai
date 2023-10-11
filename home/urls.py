from django.urls import path

from . import views

app_name = 'home'
urlpatterns = [
    path("", views.index, name="index"),
    path("aboutus", views.aboutus, name="aboutus"),
    path("subscribe", views.subscribe, name="subscribe"),
    path("newsletter", views.newsletter, name="newsletter"),
    path("contact", views.contact, name="contact"),
    path("dpp", views.dpp, name="dpp"),
    path("cgv", views.cgv, name="cgv")
]

handler404 = views.handler_404
