from django.urls import path

from . import views

app_name = "app"
urlpatterns = [
    path("", views.dashboard, name='dashboard'),
    path("config", views.config, name="config"),
    path("config/authGoogle", views.authGoogle, name="authGoogle"),
    path("config/authMeta", views.authMeta, name="authMeta"),
    path('config/Google/', views.configGoogle, name='configGoogle'),
    path('config/Meta/', views.configMeta, name="configMeta"),
    path("googleManager", views.googleManager, name='googleManager'),
    path("facebookManager", views.fbManager, name='fbManager'),
    path("instagramManager", views.instaManager, name='instaManager'),
]
