from django.urls import path

from . import views
from .views import InstagramMediaDetailView

app_name = "app"
urlpatterns = [
    path("", views.dashboard, name='dashboard'),
    path("config", views.config, name="config"),
    path("config/authGoogle", views.authGoogle, name="authGoogle"),
    path("config/authMeta", views.authMeta, name="authMeta"),
    path('config/Google/', views.configGoogle, name='configGoogle'),
    path('config/Meta/', views.configMeta, name="configMeta"),
    path("googleManager", views.googleManager, name='googleManager'),
    path("googleManagerPreferences", views.googlePreferences, name="googleManagerPreferences"),
    path("facebookManager", views.fbManager, name='fbManager'),
    path("instagramManager", views.instaManager, name='instaManager'),
    path('instagramManager/mediaDetails/<str:pk>/', InstagramMediaDetailView.as_view(), name='insta_media_detail'),
]
