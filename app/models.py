from django.db import models
from users.models import CustomUser


class Categorie(models.Model):
    categorie_id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


# Create your models here.
class Service(models.Model):
    service_id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Location(models.Model):
    location_id = models.CharField(max_length=30, primary_key=True)
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='owned_locations')
    categorie = models.ForeignKey(Categorie, on_delete=models.SET_NULL, related_name='similar_locations', null=True)
    services = models.ManyToManyField(Service, related_name='locations')

    def __str__(self):
        return self.name

class Review(models.Model):
    review_id = models.CharField(max_length=100, primary_key=True)
    reviewer_name= models.CharField(max_length=255)
    reviewer_picture_url = models.CharField(max_length=255)
    star_rating = models.IntegerField()
    comment = models.CharField(max_length=255)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='location_reviews')
    pub_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.reviewer_name + " : " + str(self.star_rating) + "/5 : " + self.comment


class InstagramMedia(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('CA', 'CAROUSEL_ALBUM'),
        ('IM', 'IMAGE'),
        ('VI', 'VIDEO')
    ]

    instagram_media_id = models.CharField(max_length=30, primary_key=True)
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='instagram_post')
    caption = models.CharField(max_length=1000)
    media_type = models.CharField(max_length=255, choices=MEDIA_TYPE_CHOICES)
    media_url = models.CharField(max_length=1000)
    published_at = models.DateTimeField(auto_now_add=True)

    def __str__ (self):
        return self.instagram_media_id

class InstagramMediaComment(models.Model):
    instagram_media_comment_id = models.CharField(max_length=30, primary_key=True)
    content = models.CharField(max_length=255)
    send_at = models.DateTimeField(auto_now_add=True)
    media_related = models.ForeignKey(InstagramMedia, on_delete=models.CASCADE, related_name="media_comment", null=True)

    def __str__(self):
        return self.content

class Photo(models.Model):
    title = models.CharField(max_length=255)
    upload_at = models.DateTimeField(auto_now_add=True)
    url = models.CharField(max_length=200)
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="photo_author")


    def __str__(self):
        return self.title

class PhotoObject(models.Model):
    label = models.CharField(max_length=40)
    confidence = models.DecimalField(max_digits=14, decimal_places=2)
    x_min = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    x_max = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    y_min = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    y_max = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    width = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    height = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    is_placed = models.BooleanField(default=False)
    photo_associated = models.ForeignKey(Photo, on_delete=models.CASCADE, related_name="associated_photo", null=True)


    def __str__(self):
        return self.label