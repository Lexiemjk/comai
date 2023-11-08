from django.contrib import admin
from .models import *

@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('categorie_id', 'name')
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('service_id', 'name')
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('location_id', 'name', 'owner', 'categorie')
    search_fields = ('name', 'owner__username')
    ordering = ('name',)
    list_filter = ('categorie', 'owner',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('review_id', 'reviewer_name', 'star_rating', 'location')
    search_fields = ('reviewer_name', 'location__name')
    sortable_by = ('star_rating',)
    list_filter = ('star_rating', 'location',)
    ordering = ('-star_rating',)

@admin.register(InstagramMedia)
class InstagramMediaAdmin(admin.ModelAdmin):
    list_display = ('instagram_media_id', 'author', 'caption', 'media_type', 'media_url')
    search_fields = ('author__username', 'caption')
    list_filter = ('media_type',)
    ordering = ('author',)

@admin.register(InstagramMediaComment)
class InstagramMediaCommentAdmin(admin.ModelAdmin):
    list_display = ('instagram_media_comment_id', 'content', 'send_at')
    search_fields = ('content',)
    date_hierarchy = 'send_at'
    ordering = ('-send_at',)

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'upload_at', 'author')
    search_fields = ('author', 'title')
    date_hierarchy = 'upload_at'
    ordering = ('-upload_at',)

@admin.register(PhotoObject)
class PhotoObjectAdmin(admin.ModelAdmin):
    list_display = ('label', 'confidence', 'is_placed')
    search_fields = ('label',)
