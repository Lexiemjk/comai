import datetime
import json

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from allauth.socialaccount.models import SocialToken, SocialAccount
from django.core.files.storage import default_storage
from django.shortcuts import render, redirect, reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .models import Location, Categorie, Service, Review, InstagramMedia, InstagramMediaComment, Photo, PhotoObject
from . import forms
from users.forms import AnswerPreferenceForm, finishConfigForm
import requests
import openai

STAR_RATING_MAP = {
    'ONE': 1,
    'TWO': 2,
    'THREE': 3,
    'FOUR': 4,
    'FIVE': 5
}


# Create your views here.

@login_required
def dashboard(request):
    if request.user.first_connection:
        return redirect('app:config')

    if request.method == "POST":
        form = forms.fileDemoForm(request.POST, request.FILES)
        if form.is_valid():
            img = request.FILES['file']
            img_name = form.cleaned_data['title']

            existing_photo = Photo.objects.filter(title=img_name, author=request.user).first()
            if existing_photo:
                messages.error(request, "A photo with the same name have already been uploaded")
                img_url = existing_photo.url
            else:
                filename = default_storage.save('uploads/' + img_name, img)
                img_url = default_storage.url(filename)

                new_photo = Photo(
                    title=img_name,
                    url=img_url,
                    author=request.user
                )
                new_photo.save()
                messages.success(request, "Photo uploaded successfully.")
            response_data = objectDetection(img_url)

            if response_data:
                annotations_clairifai = extract_annotations(response_data.get('clarifai', {}).get('items', []), img_url)
                annotations_google = extract_annotations(response_data.get('google', {}).get('items', []), img_url)
                annotations_amazon = extract_annotations(response_data.get('amazon', {}).get('items', []), img_url)
                annotations = annotations_amazon + annotations_google + annotations_clairifai

                labels = [annotation['label'] for annotation in annotations]
                keywords = ", ".join(labels)
                keywords += img_name
                caption = generateInstaCaption(keywords)
                return render(request, 'app/dashboard.html',
                              {'form': form, 'img_url': img_url, 'annotations': annotations, 'caption': caption})
    else:
        form = forms.fileDemoForm()

    return render(request, 'app/dashboard.html', {'form': form})


def objectDetection(img_url):
    headers = {
        'Authorization': 'Bearer ' + settings.EDENAI_KEY
    }
    url = "https://api.edenai.run/v2/image/object_detection"
    data = {
        "providers": "amazon,clarifai,google",
        "file_url": img_url
    }

    try:
        response = requests.post(url, json=data, headers=headers)  # Send JSON data
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"An error occurred: {str(e)}")
        return None

    return response.json()


def extract_annotations(items, img_url):
    annotations = []
    for item in items:
        label = item.get('label')
        confidence = item.get('confidence')
        photo = Photo.objects.get(url=img_url)
        po, created_at = PhotoObject.objects.get_or_create(label=label, photo_associated=photo, confidence=confidence)
        if item.get("x_min") and item.get("y_min"):
            x_min = item.get('x_min')
            x_max = item.get('x_max')
            y_min = item.get('y_min')
            y_max = item.get('y_max')
            width = float(x_max) - float(x_min)
            height = float(y_max) - float(y_min)
            if all(v is not None for v in [x_min, x_max, y_min, y_max]):
                existing_annotation = next((a for a in annotations if a['label'] == label), None)

                if existing_annotation is None:
                    # Append new annotation if label does not exist
                    annotations.append({
                        'label': label,
                        'confidence': confidence,
                        'x_min': x_min,
                        'x_max': x_max,
                        'y_min': y_min,
                        'y_max': y_max,
                        'width': width,
                        'height': height
                    })

            po.x_min = x_min
            po.x_max = x_max
            po.y_min = y_min
            po.y_max = y_max
            po.width = width
            po.height = height
            po.is_placed = True
            po.save()

        else:
            existing_annotation = next((a for a in annotations if a['label'] == label), None)

            if existing_annotation is None:
                annotations.append({
                    'label': label,
                    'confidence': confidence
                })
            po.is_placed = False
            po.save()
    print(annotations)
    return annotations

def generateInstaCaption(keywords):
    openai.api_key = settings.OPENAI_KEY
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system",
             "content": "You are a community manager. You will create a caption for a Instagram post for the new product thanks to the keywords that the user will give to you. The user preferences for the answer are formal and without emojis. But you can use trending hashtags. And the user's business is a restaurant"},
            {"role": "user",
             "content": keywords}
        ]
    )

    return response['choices'][0]['message']['content']


def config(request):
    if not request.user.first_connection:
        return redirect('app:dashboard')

    if request.method == "POST":
        form = forms.ConfigForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            # Redirect to some page after updating names
            return redirect('app:authGoogle')
    else:
        form = forms.ConfigForm(instance=request.user)

    return render(request, 'app/config.html', {'form': form})


def authGoogle(request):
    return render(request, 'app/authGoogle.html')


def authMeta(request):
    return render(request, 'app/authMeta.html')


def getLocations(access_token, token, account_id):
    credentials = Credentials(
        token=access_token,
        refresh_token=token.token_secret,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.CLIENT_ID,
        client_secret=settings.CLIENT_SECRET
    )

    service = build('mybusinessbusinessinformation', 'v1', credentials=credentials)

    parentIUD = f"accounts/{account_id}"
    locations = service.accounts().locations().list(parent=parentIUD,
                                                    readMask="name,title,categories,profile").execute()
    return locations


def get_openai_answer(reviews):
    openai.api_key = settings.OPENAI_KEY
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system",
             "content": "You are the owner of the business responding to those reviews in the corresponding language. I want three answers: one formal labeled 'formal', one more friendly labeled 'friendly', and one with emojis labeled 'emoji'. Provide your answers in JSON format"},
            {"role": "user", "content": reviews['reviews'][0]['comment']},
        ]
    )
    content = response['choices'][0]['message']['content']
    parsed_content = json.loads(content)

    # Ensure that the keys exist and provide default values if they don't
    formal_answer = parsed_content.get('formal', '')
    friendly_answer = parsed_content.get('friendly', '')
    emoji_answer = parsed_content.get('emoji', '')

    return {
        'formal': formal_answer,
        'friendly': friendly_answer,
        'emoji': emoji_answer
    }


def save_service(service_data):
    service_id = service_data['id']
    name = service_data['name']
    return Service.objects.get_or_create(service_id=service_id, name=name)


def save_location(location, owner):
    location_id = location['name'].split('/')[-1]
    cat_id = location['categories']['primaryCategory']['name'].replace("categories/gcid:", '')
    categorie = Categorie.objects.get(categorie_id=cat_id)

    loc, _ = Location.objects.get_or_create(location_id=location_id, name=location['title'], categorie=categorie,
                                            owner=owner)

    for service_data in location['categories']['primaryCategory']['serviceTypes']:
        service_id = service_data['serviceTypeId'].replace('job_type_id:', '')
        service = Service.objects.get(service_id=service_id)
        loc.services.add(service)

    return loc


def save_reviews(reviews_data, location_instance):
    for review in reviews_data['reviews']:
        star_rating_int = STAR_RATING_MAP.get(review['starRating'], 0)

        # Only use unique fields in get_or_create
        review_instance, created = Review.objects.get_or_create(
            review_id=review['reviewId'],
        )

        # Update other fields
        review_instance.reviewer_name = review['reviewer']['displayName']
        review_instance.reviewer_picture_url = review['reviewer']['profilePhotoUrl']
        review_instance.star_rating = star_rating_int
        review_instance.comment = review['comment']
        review_instance.location = location_instance

        # Save the updated fields
        review_instance.save()


def configGoogle(request):
    token = SocialToken.objects.get(account__user=request.user, account__provider='google')
    account_id = SocialAccount.objects.get(user=request.user, provider='google').uid

    locations = getLocations(token.token, token, account_id)

    services = [
        {'id': service['serviceTypeId'].replace('job_type_id:', ''), 'name': service['displayName']}
        for service in locations['locations'][0]['categories']['primaryCategory']['serviceTypes']
    ]
    for service_data in services:
        save_service(service_data)

    categorie_data = {
        'categorie_id': locations['locations'][0]['categories']['primaryCategory']['name'].replace("categories/gcid:",
                                                                                                   ''),
        'name': locations['locations'][0]['categories']['primaryCategory']['displayName']
    }
    Categorie.objects.get_or_create(**categorie_data)

    loc = save_location(locations['locations'][0], request.user)

    headers = {
        'Authorization': f'Bearer {token.token}',
        'Content-Type': 'application/json'
    }
    url = f'https://mybusiness.googleapis.com/v4/accounts/{account_id}/locations/{loc.location_id}/reviews'
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        error_msg = f"Failed to retrieve reviews. Status code: {response.status_code}. Response: {response.text}"
        return render(request, 'app/configGoogle.html', {'location': locations['locations'][0], 'error': error_msg})

    reviews = response.json()

    save_reviews(reviews, loc)

    answers = ""
    if not 'reviewReply' in reviews['reviews'][0]:
        answers = get_openai_answer(reviews)

    if request.method == "POST":
        if 'answerGenerationPreferences' in request.POST:
            answer_preferences_form = AnswerPreferenceForm(request.POST, openai_answers=answers)
            if answer_preferences_form.is_valid():
                selected_preferences = ','.join(answer_preferences_form.cleaned_data['answerGenerationPreferences'])
                request.user.answerGenerationPreferences = selected_preferences
                request.user.save()
                return redirect('app:authMeta')

        locations_form = forms.LocationParametersForm(request.POST)
        if locations_form.is_valid():
            location_instance = locations_form.save()
            save_reviews(reviews, location_instance)

            # Present the OpenAI preference form to the user
            answer_preferences_form = AnswerPreferenceForm(request.POST, openai_answers=answers)
            return render(request, 'app/configGoogle.html',
                          {'answer_preferences_form': answer_preferences_form, 'location': locations['locations'][0],
                           'reviews': reviews,
                           'answers': answers})


    else:
        location_form = forms.LocationParametersForm(instance=loc)

    return render(request, 'app/configGoogle.html',
                  {'location': locations['locations'][0], 'reviews': reviews, 'answers': answers,
                   'locations_form': location_form})


def requestInstagramAccount(token):
    url = f'https://graph.facebook.com/v18.0/me/accounts?access_token={token}'

    response = requests.get(url)
    if response.status_code == 200:
        pages_data = response.json()
        page_id = pages_data['data'][0]['id']
        page_name = pages_data['data'][0]['name']

        url = "https://graph.facebook.com/v18.0/{0}?fields=instagram_business_account&access_token={1}".format(page_id,
                                                                                                               token)
        response = requests.get(url)
        insta_id = response.json()['instagram_business_account']['id']

        return insta_id


def saveMedia(request, media):
    media_instance, created = InstagramMedia.objects.get_or_create(instagramMedia_id=media['id'], author=request.user)

    media_instance.media_url = media['media_url']
    media_instance.media_type = media['media_type']
    media_instance.caption = media['caption']
    media_instance.published_at = datetime.datetime.strptime(media['timestamp'], "%Y-%m-%dT%H:%M:%S%z")

    media_instance.save()

    if media['comments']:
        return media['comments']


def saveComments(comments):
    for comment in comments['data']:
        comment_instance, created = InstagramMediaComment.objects.get_or_create(
            instagram_media_comment_id=comment['id'])

        comment_instance.content = comment['text']
        comment_instance.send_at = datetime.datetime.strptime(comment['timestamp'], "%Y-%m-%dT%H:%M:%S%z")

        comment_instance.save()


def requestInstagramMedia(request, token, insta_id):
    url = "https://graph.facebook.com/v18.0/{0}/media?access_token={1}".format(insta_id, token)
    response = requests.get(url)

    medias = response.json()

    for media in medias['data']:
        url = "https://graph.facebook.com/v18.0/{0}/?fields={1}&access_token={2}".format(media['id'],
                                                                                         "id, caption, media_type, media_url, comments, timestamp",
                                                                                         token)
        response = requests.get(url)
        comments = saveMedia(request, response.json())
        comments['data'] = comments['data'][-3:]
        saveComments(comments)


def configMeta(request):
    token = SocialToken.objects.get(account__user=request.user, account__provider='facebook')

    insta_id = requestInstagramAccount(token)
    requestInstagramMedia(request, token, insta_id)

    medias = (InstagramMedia.objects.filter(author=request.user)
              .prefetch_related('media_comment')  # Adjust this line based on your models and relationships
              .order_by('-published_at')[:3])

    if request.method == 'POST':
        form = finishConfigForm(request.POST)
        if form.is_valid():
            request.user.toggleFirstConnection()
            return redirect('app:dashboard')
    else:
        form = finishConfigForm()

    return render(request, 'app/configMeta.html', {'medias': medias, 'form': form})


def googleManager(request):
    return render(request, 'app/googleManager.html')


def fbManager(request):
    return render(request, 'app/fbManager.html')


def instaManager(request):
    return render(request, 'app/instaManager.html')
