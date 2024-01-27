from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.cloud import storage

from allauth.socialaccount.models import SocialToken, SocialAccount
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import DetailView
from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect

from urllib.parse import unquote

from .models import *
from . import forms
from users.forms import *

import requests, openai, json, datetime

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
    """
    Renders the dashboard view for the authenticated user.

    If it is the user's first connection, redirects to the configuration page.
    Otherwise, retrieves the user's locations and the last review of the last location.
    If a last review exists, generates lists of stars and empty stars based on the star rating.
    Retrieves the social token for the user's Facebook account.
    Retrieves the Instagram ID and media for the user's Instagram account.
    Retrieves the last Instagram media and last Instagram media comment for the authenticated user.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: The rendered HTML template with the necessary context variables.
    """
    if request.user.first_connection:
        return redirect('app:config')
    else:
        locations = Location.objects.filter(owner=request.user)
        last_review = Review.objects.filter(location=locations.last()).last()
        if last_review:
            stars = range(last_review.star_rating)
            no_stars = range(5 - last_review.star_rating)

        token = SocialToken.objects.get(account__user=request.user, account__provider='facebook')

        insta_id = request_instagram_account(token)
        medias = request_instagram_media(request, token, insta_id)

        last_insta_media = InstagramMedia.objects.filter(author=request.user).last()
        last_insta_comment = InstagramMediaComment.objects.filter(media_related=last_insta_media).last()

    if last_review:
        return render(request, 'app/dashboard.html', {'last_review': last_review, 'stars': stars, 'no_stars': no_stars,
                                                      'last_insta_media': last_insta_media,
                                                      'last_insta_comment': last_insta_comment})
    return render(request, 'app/dashboard.html',
                  {'last_insta_media': last_insta_media, 'last_insta_comment': last_insta_comment})


def generate_insta_caption(keywords):
    """

    Generate a caption for an Instagram post based on user-provided keywords.

    Parameters:
    - keywords (string): The keywords provided by the user to create the caption.

    Returns:
    - caption (string): The generated caption for the Instagram post.

    Example Usage:
    >>> keywords = "delicious food, restaurant, trendy"
    >>> caption = generate_insta_caption(keywords)
    >>> print(caption)
    "Indulge in the delicious food at our trendy restaurant. #foodie #restaurant #trendy"

    """
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
    """
    Handle the configuration of user settings.

    :param request: The request object containing the HTTP request information.
    :type request: HttpRequest
    :return: The HTTP response.
    :rtype: HttpResponse
    """
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


def auth_google(request):
    """

    Method: auth_google

    Description:
    This method is used to authenticate a user using Google. It renders the 'authGoogle.html' template where the user can complete the authentication process.

    Parameters:
    - request: The request object that contains information about the current HTTP request.

    Returns:
    - Returns the rendered template for Google authentication.

    """
    return render(request, 'app/authGoogle.html')


def auth_meta(request):
    """
    Renders the 'authMeta.html' template.

    Parameters:
    - request: The HttpRequest object that represents the current request.

    Returns:
    - The rendered HTML content of 'authMeta.html'.
    """
    return render(request, 'app/authMeta.html')


def get_locations(access_token, token, account_id):
    """
    Retrieves a list of locations associated with the given account ID.

    Parameters:
    - access_token (str): The access token for authentication.
    - token (Token): The token object containing the token secret for refreshing the access token.
    - account_id (str): The ID of the account to retrieve locations from.

    Returns:
    - locations (dict): A dictionary containing the retrieved locations data.

    Example:
    access_token = "your_access_token"
    token = Token("your_token_secret")
    account_id = "your_account_id"
    locations = get_locations(access_token, token, account_id)
    """
    credentials = Credentials(
        token=access_token,
        refresh_token=token.token_secret,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.CLIENT_ID,
        client_secret=settings.CLIENT_SECRET
    )
    print()
    service = build('mybusinessbusinessinformation', 'v1', credentials=credentials)

    parentIUD = f"accounts/{account_id}"
    locations = service.accounts().locations().list(parent=parentIUD,
                                                    readMask="name,title,categories,profile").execute()
    return locations


def get_openai_answer_default(review):
    """
    Get responses from OpenAI GPT-3.5-Turbo model for a given review.

    Parameters:
        review (str): The review text.

    Returns:
        dict: A dictionary containing the formal, friendly, and emoji answers from the model.

    Example:
        >>> review = "This product is amazing!"
        >>> answers = get_openai_answer_default(review)
        >>> answers
        {'formal': '', 'friendly': '', 'emoji': ''}
    """
    openai.api_key = settings.OPENAI_KEY
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
             "content": "You are the owner of the business responding to those reviews in the corresponding language. I want three answers: one formal labeled 'formal', one more friendly labeled 'friendly', and one with emojis labeled 'emoji'. Provide your answers in JSON format"},
            {"role": "user", "content": review},
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


def get_openai_review_answer(review, preferences):
    """
    Retrieve an answer from OpenAI's GPT-3.5 Turbo model based on a given review and preferences.

    Parameters:
    - review (str): The review for which an answer is requested.
    - preferences (str): The preferences for generating the answer.

    Returns:
    - content (str): The generated answer based on the given review and preferences.
    """
    openai.api_key = settings.OPENAI_KEY

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "system",
             "content": "You are the owner of the business responding to those reviews in the corresponding language. I want an answer generated respecting these preferences : " + preferences},
            {"role": "user", "content": review},
        ]
    )
    content = response['choices'][0]['message']['content']
    return content


def get_openai_comment_answer(comment, caption):
    """

    This method, `get_openai_comment_answer`, is used to retrieve a response from the OpenAI GPT-3.5-turbo chat-based language model, given a comment and a caption.

    Parameters:
    - `comment` (str): The comment from the user.
    - `caption` (str): The caption of the post for context.

    Returns:
    - `content` (str): The response generated by the OpenAI model.

    Example usage:
    comment = "Great post!"
    caption = "Check out our new product!"
    response = get_openai_comment_answer(comment, caption)
    print(response)
    # Output: "Thank you! We're glad you like it. Don't forget to use the Instagram code: XXXX when placing an order!"

    Note:
    - Make sure to set the `settings.OPENAI_KEY` variable with the appropriate OpenAI API key before calling this method.

    """
    openai.api_key = settings.OPENAI_KEY

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "system",
             "content": "You are the community Manager of the business. Answer friendly and use Instagram code. This the caption of your post for context : " + caption},
            {"role": "user", "content": comment},
        ]
    )

    content = response['choices'][0]['message']['content']
    return content


def save_service(service_data):
    """
    Save a service to the database or update an existing service.

    Args:
        service_data (dict): A dictionary containing the service data including 'id' and 'name' fields.

    Returns:
        tuple: A tuple containing the saved or updated Service object and a boolean indicating whether it was created or not.

    """
    service_id = service_data['id']
    name = service_data['name']
    return Service.objects.get_or_create(service_id=service_id, name=name)


def save_location(location, owner):
    """
    Save Location

    Save the given location into the database.

    Parameters:
    - location (dict): A dictionary containing the details of the location.
    - owner (User): The owner of the location.

    Returns:
    - loc (Location): The saved `Location` object.

    Example Usage:
    location = {'name': '/categories/gcid:12345', 'categories': {'primaryCategory': {'name': 'categories/gcid:12345', 'serviceTypes': [{'serviceTypeId': 'job_type_id:12345'}]}}}
    owner = User.objects.get(username='admin')
    saved_location = save_location(location, owner)
    """
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
    """
    Saves reviews data in the database.

    Parameters:
    reviews_data (dict): A dictionary containing the reviews data.
    location_instance (Location): An instance of the Location model.

    Returns:
    None
    """
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


def config_google(request):
    """

    Configure Google

    Configures the Google API for a user's account.

    Parameters:
    - request (HttpRequest): The HTTP request object.

    Returns:
    - HttpResponse: The HTTP response object.

    """
    token = SocialToken.objects.get(account__user=request.user, account__provider='google')
    account_id = SocialAccount.objects.get(user=request.user, provider='google').uid

    locations = get_locations(token.token, token, account_id)

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
    try:
        review = reviews['reviews'][0]['comment']
    except:
        review = None
    if review:
        save_reviews(reviews, loc)

        answers = ""
        if not 'reviewReply' in reviews['reviews'][0]:
            answers = get_openai_answer_default(review)
    else:
        review = "Nous avons passé un super moment dans votre restaurant ! Merci pour tout !"
        answers = get_openai_answer_default(review)

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
            locations_form.save()

            # Present the OpenAI preference form to the user
            answer_preferences_form = AnswerPreferenceForm(request.POST, openai_answers=answers)
            return render(request, 'app/configGoogle.html',
                          {'answer_preferences_form': answer_preferences_form, 'location': locations['locations'][0],
                           'review': review,
                           'answers': answers})


    else:
        location_form = forms.LocationParametersForm(instance=loc)

    return render(request, 'app/configGoogle.html',
                  {'location': locations['locations'][0], 'review': review, 'answers': answers,
                   'locations_form': location_form})


def request_instagram_account(token):
    """
    Request Instagram Account

    This method makes a request to Facebook's Graph API to retrieve the Instagram Business Account ID of the specified Facebook page.

    Parameters:
        token (str): The access token required for authentication.

    Returns:
        str: The Instagram Business Account ID associated with the specified Facebook page.

    Example:
        >>> token = 'your_access_token'
        >>> request_instagram_account(token)
        '1234567890'
    """
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


def save_media(request, media):
    """
    Save the media in the database.

    Parameters:
    - request: The HTTP request object that contains the user information.
    - media: A dictionary that contains the media information.

    Returns:
    None
    """
    media_instance, created = InstagramMedia.objects.get_or_create(instagram_media_id=media['id'], author=request.user)

    media_instance.media_url = media['media_url']
    media_instance.media_type = media['media_type']
    media_instance.caption = media['caption']
    media_instance.published_at = datetime.datetime.strptime(media['timestamp'], "%Y-%m-%dT%H:%M:%S%z")

    media_instance.save()

    if media['comments']:
        save_comments(media['comments'], media['id'])


def save_comments(comments, id):
    """
    Saves the comments for a given Instagram media.

    Parameters:
    comments (dict): The comments data.
    id (int): The id of the Instagram media.

    Returns:
    None
    """
    for comment in comments['data']:
        comment_instance, created = InstagramMediaComment.objects.get_or_create(
            instagram_media_comment_id=comment['id'])

        comment_instance.content = comment['text']
        comment_instance.send_at = datetime.datetime.strptime(comment['timestamp'], "%Y-%m-%dT%H:%M:%S%z")
        comment_instance.media_related = InstagramMedia.objects.get(instagram_media_id=id)

        comment_instance.save()


def request_instagram_media(request, token, insta_id):
    """

    """
    url = "https://graph.facebook.com/v18.0/{0}/media?access_token={1}".format(insta_id, token)
    response = requests.get(url)

    medias = response.json()

    for media in medias['data']:
        url = "https://graph.facebook.com/v18.0/{0}/?fields={1}&access_token={2}".format(media['id'],
                                                                                         "id, caption, media_type, media_url, comments, timestamp",
                                                                                         token)
        response = requests.get(url)
        save_media(request, response.json())

    return medias


def config_meta(request):
    """
    This method config_meta is used to configure the meta information for a social media account. It takes a request object as a parameter.

    Parameters:
    - request: The request object representing the HTTP request made to the server.

    Returns:
    - None

    Example usage:
    config_meta(request)
    """
    token = SocialToken.objects.get(account__user=request.user, account__provider='facebook')

    insta_id = request_instagram_account(token)
    request_instagram_media(request, token, insta_id)

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


def google_manager(request):
    """

    """
    locations = Location.objects.filter(owner=request.user)

    last_review = Review.objects.filter(location=locations.last()).last()
    if last_review:
        stars = range(last_review.star_rating)
        no_stars = range(5 - last_review.star_rating)

        last_ten_reviews = Review.objects.filter(location=locations.last())[1:10]
        generated_answer = get_openai_review_answer(last_review.comment, request.user.answerGenerationPreferences)

        return render(request, 'app/googleManager.html',
                      {'last_review': last_review, 'stars': stars, 'no_stars': no_stars,
                       'generated_answer': generated_answer,
                       'last_ten_reviews': last_ten_reviews})
    return render(request, 'app/googleManager.html')


def google_preferences(request):
    """
    Google Preferences

    Method to handle the Google Preferences form submission.

    Parameters:
    - request: The HTTP request object.

    Returns:
    - If the request method is 'POST' and the form data is valid, redirects to 'app:googleManager' URL.
    - If the request method is not 'POST', renders the 'app/googleManagerPreferences.html' template with the GooglePreferencesForm.

    Example Usage:
    request = HttpRequest()
    google_preferences(request)
    """
    if request.method == 'POST':
        form = GooglePreferencesForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('app:googleManager')
    else:
        form = GooglePreferencesForm()

    return render(request, 'app/googleManagerPreferences.html', {'form': form})


def fb_manager(request):
    """
    Renders the 'fbManager.html' template.

    :param request: The HTTP request object.
    """
    return render(request, 'app/fbManager.html')


def fetch_recent_posts(request):
    """
    Fetches the most recent posts from Instagram associated with the given user's Facebook account.

    :param request: The HTTP request object.
    :return: JsonResponse containing the data of the most recent Instagram posts, including the post ID, caption, published date, and the three most recent comments for each post.
    """
    token = SocialToken.objects.get(account__user=request.user, account__provider='facebook')

    insta_id = request_instagram_account(token)
    request_instagram_media(request, token, insta_id)

    insta_medias = InstagramMedia.objects.prefetch_related('media_comment') \
                       .all().order_by('-published_at')[:3]
    data = []
    for media in insta_medias:
        # Fetch 3 most recent comments for each post
        comments = list(media.media_comment.all().order_by('-send_at')[:3].values(
            'instagram_media_comment_id', 'content', 'send_at'))
        data.append({
            'media_id': media.instagram_media_id,
            'caption': media.caption,
            'published_at': media.published_at.isoformat(),
            'comments': comments
        })
    return JsonResponse(data, safe=False)


def fetch_recent_comments(request, media_id):
    """

    Fetches recent comments for a specific post or media.

    Parameters:
    - request (HttpRequest): The HTTP request object.
    - media_id (str): The unique identifier of the media.

    Returns:
    - JsonResponse: A JSON response containing the comments for the specified media. If a media_id is provided, it returns the comments for that post. Otherwise, it returns an error message
    * indicating that the media_id was not provided. If there are no comments available, an empty list will be returned. The response is formatted as follows:

        - If a media_id is provided:
            {
                'comments': [
                    {
                        'instagram_media_comment_id': str,
                        'content': str,
                        'send_at': str
                    },
                    ...
                ]
            }

        - If no media_id is provided:
            {
                'error': 'Media ID not provided'
            }

    Note:
    - This method uses the SocialToken model from the Django's SocialApp framework to retrieve the user's Facebook token.
    - It also uses the request_instagram_account and request_instagram_media functions to obtain the Instagram account and media ID associated with the token.
    - The 'offset' parameter can be passed in the request query string to specify the offset for fetching comments. By default, it is set to 0.
    - The returned comments are ordered by the 'send_at' field in descending order.

    """
    token = SocialToken.objects.get(account__user=request.user, account__provider='facebook')

    insta_id = request_instagram_account(token)
    request_instagram_media(request, token, insta_id)

    offset = int(request.GET.get('offset', 0))

    if media_id:
        # Fetch additional comments for a specific post
        media = InstagramMedia.objects.get(instagram_media_id=media_id)
        comments = list(media.media_comment.all().order_by('-send_at')[offset: offset + 3].values(
            'instagram_media_comment_id', 'content', 'send_at'))
        return JsonResponse({'comments': comments}, safe=False)

    else:
        return JsonResponse({'error': 'Media ID not provided'}, status=400)


def insta_manager(request):
    """
    Renders the 'app/instaManager.html' template with an empty context.

    Parameters:
        request (HttpRequest): The request to be processed.

    Returns:
        HttpResponse: The rendered template as an HTTP response.
    """
    return render(request, 'app/instaManager.html', context={})


def generate_response(request):
    """
    Generates a response based on the given request.

    :param request: The HTTP request containing the data.
    :type request: HttpRequest

    :return: The generated response.
    :rtype: JsonResponse

    :raises: None
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        comment = data.get('comment')
        caption = data.get('caption')
        response = get_openai_comment_answer(comment, caption)
        return JsonResponse({'response': response})
    return JsonResponse({'error': 'Invalid request'}, status=400)


def post_instagram_comment_reply(request):
    """
    Posts a reply to an Instagram comment.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: A JSON response indicating if the comment reply was successfully posted or an error occurred.

    Raises:
        SocialToken.DoesNotExist: If the access token for the user's Facebook account does not exist.

    Example usage:
        # Assuming 'request' is a valid HttpRequest object
        response = post_instagram_comment_reply(request)

    Notes:
        - This method requires the request method to be 'POST'.
        - The request body should contain a JSON object with the following keys:
            - 'comment_id': The ID of the comment to which the reply is being posted.
            - 'response_message': The message of the reply.
        - The user's Facebook access token is retrieved from the 'SocialToken' table in the database.
        - The 'access_token' parameter in the API request payload should be replaced with a valid access token.

    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            comment_id = data.get('comment_id')
            response_message = data.get('response_message')
            access_token = SocialToken.objects.get(account__user=request.user,
                                                   account__provider='facebook')  # Use a secure method to store and retrieve this

            url = f"https://graph.facebook.com/{comment_id}/replies"
            payload = {
                'message': response_message,
                'access_token': access_token
            }
            response = requests.post(url, data=payload)

            if response.status_code == 200:
                return JsonResponse({'success': True})
            else:

                return JsonResponse({'error': 'Failed to post comment', 'details': response.text}, status=500)
        except Exception as e:
            # Log the exception for debugging
            print(f"Error: {e}")
            # Return a JSON response with error details
        return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=400)


def gcs_librairy(request, path=''):
    """
    This method, gcs_librairy, retrieves the list of files and folders from a Google Cloud Storage bucket and renders them in a web page.

    Parameters:
    - request: An HTTP request object.
    - path: (Optional) A string representing the path within the bucket to list files and folders from. If not provided, the method lists the files and folders from the root directory of
    * the bucket.

    Returns:
    - An HTTP response object, rendering the 'app/librairy.html' template with the list of files and folders.

    Example usage:
    request = ...  # create an HTTP request object
    response = gcs_librairy(request, 'path/to/folder/')  # retrieve list of files and folders from 'path/to/folder/'

    Note: This method requires the 'storage' library to be installed and imported, and the 'settings.GS_BUCKET_NAME' to be set to the desired Google Cloud Storage bucket name.
    """
    client = storage.Client()
    bucket_name = settings.GS_BUCKET_NAME
    bucket = client.get_bucket(bucket_name)

    # Ensure the path ends with a '/' if it's not empty
    if path and not path.endswith('/'):
        path += '/'

    if path:
        blobs = bucket.list_blobs(prefix=path, delimiter='/')
    else:
        blobs = bucket.list_blobs()

    files = []
    folders = []
    for blob in blobs:
        # Remove the current path from the blob's name to get the relative path
        relative_path = blob.name[len(path):]
        if relative_path.endswith('/'):
            folders.append(relative_path)
        elif path:  # only add files to the list if not in the root directory
            files.append(blob)

    path_parts = [part for part in path.split('/') if part]

    context = {
        'files': files,
        'folders': folders,
        'current_path': path,
        'path_parts': path_parts,
    }

    return render(request, 'app/librairy.html', context)


def upload_file_to_gcs(request):
    """
    Uploads a file to Google Cloud Storage.

    Parameters:
    - request (HttpRequest): The HTTP request object containing the file to upload.

    Returns:
    - HttpResponseRedirect: A redirect response to the '/app/librairy/' URL after successful upload.

    """
    if request.method == 'POST':
        uploaded_file = request.FILES['file']
        client = storage.Client()
        bucket = client.get_bucket(settings.GS_BUCKET_NAME)
        blob = bucket.blob(uploaded_file.name)
        blob.upload_from_string(
            uploaded_file.read(),
            content_type=uploaded_file.content_type
        )
        return HttpResponseRedirect('/app/librairy/')


def delete_file_from_gcs(request, file_name):
    """
    Deletes a file from Google Cloud Storage (GCS).

    Parameters:
    - request: The HTTP request object.
    - file_name: The name or path of the file to be deleted from the GCS.

    Returns:
    - An HttpResponseRedirect object that redirects to '/app/library/' after the file is deleted from GCS.
    """
    client = storage.Client()
    bucket = client.get_bucket(settings.GS_BUCKET_NAME)
    file_path = unquote(file_name)
    blob = bucket.blob(file_path)
    blob.delete()
    return HttpResponseRedirect('/app/librairy/')


class InstagramMediaDetailView(DetailView):
    """

    Class: InstagramMediaDetailView(DetailView)

    This class is a subclass of the DetailView class provided by Django. It is used to display the details of an Instagram media object.

    Attributes:
    - model: The model associated with this view. In this case, it is the InstagramMedia model.
    - template_name: The name of the template used to render the view. In this case, it is 'app/insta_media_detail.html'.
    - context_object_name: The name of the variable used to pass the context data to the template. In this case, it is 'insta_media'.

    """
    model = InstagramMedia
    template_name = 'app/insta_media_detail.html'
    context_object_name = 'insta_media'
