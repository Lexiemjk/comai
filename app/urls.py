from django.urls import path, re_path

from . import views
from .views import InstagramMediaDetailView

app_name = "app"
urlpatterns = [
    path("", views.dashboard, name='dashboard'),
    path("config", views.config, name="config"),
    path("config/auth_google", views.auth_google, name="auth_google"),
    path("config/auth_meta", views.auth_meta, name="auth_meta"),
    path('config/Google/', views.config_google, name='configGoogle'),
    path('config/Meta/', views.config_meta, name="configMeta"),
    path("googleManager", views.google_manager, name='googleManager'),
    path("googleManagerPreferences", views.google_preferences, name="googleManagerPreferences"),
    path("facebookManager", views.fb_manager, name='fbManager'),
    path("instagramManager", views.insta_manager, name='instaManager'),
    path('instagramManager/fetch_recent_comments/<str:media_id>/', views.fetch_recent_comments, name='fetch_recent_comments'),
    path('instagramManager/fetch_recent_posts/', views.fetch_recent_posts, name='fetch_recent_posts'),
    path("InstagramManager/generate_response", views.generate_response, name="generate_response"),
    path('InstagramManager/post_instagram_comment_reply/', views.post_instagram_comment_reply,
         name='post_instagram_comment_reply'),
    path('instagramManager/mediaDetails/<str:pk>/', InstagramMediaDetailView.as_view(), name='insta_media_detail'),
    re_path(r'librairy/(?P<path>.*)', views.gcs_librairy, name='gcs_librairy'),
    path('librairy/upload/', views.upload_file_to_gcs, name='upload_file_to_gcs'),
    re_path(r'librairy/delete/(?P<file_name>.+)/$', views.delete_file_from_gcs, name='delete_file_from_gcs'),

]
