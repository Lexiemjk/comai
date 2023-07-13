from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage

from .forms import NewsletterForm, ContactForm
from .models import SubscribedUsers



def index(request):
    return render(request, 'home/index.html')


def aboutus(request):
    return render(request, 'home/aboutus.html')


def subscribe(request):
    if request.method == 'POST':
        name = request.POST.get('name', None)
        email = request.POST.get('email', None)

        if not name or not email:
            messages.error(request, "You must type legit name and email to subscribe to a Newsletter")
            return redirect("/")

        subscribe_user = SubscribedUsers.objects.filter(email=email).first()
        if subscribe_user:
            messages.error(request, f"{email} email address is already subscriber.")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        try:
            validate_email(email)
        except ValidationError as e:
            messages.error(request, e.messages[0])
            return redirect("/")

        subscribe_model_instance = SubscribedUsers()
        subscribe_model_instance.name = name
        subscribe_model_instance.email = email
        subscribe_model_instance.save()
        messages.success(request, f'{email} email was successfully subscribed to our newsletter!')
        return redirect(request.META.get("HTTP_REFERER", "/"))


def newsletter(request):
    if request.user.is_superuser:
        if request.method == 'POST':
            form = NewsletterForm(request.POST)
            if form.is_valid():
                subject = form.cleaned_data.get('subject')
                receivers = form.cleaned_data.get('receivers').split(',')
                email_message = form.cleaned_data.get('message')

                mail = EmailMessage(subject, email_message, to=receivers)
                mail.content_subtype = 'html'

                if mail.send():
                    messages.success(request, "Email sent succesfully")
                else:
                    messages.error(request, "There was an error sending email")

            else:
                for error in list(form.errors.values()):
                    messages.error(request, error)

        form = NewsletterForm()
        form.fields['receivers'].initial = ','.join([active.email for active in SubscribedUsers.objects.all()])
        return render(request=request, template_name='home/newsletter.html', context={'form': form})

    return redirect('/')


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']

            EmailMessage(
                'Contact Form Submission from {}'.format(name),
                message,
                'saas.comai@gmail.com',  # Send from (your website)
                ['saas.comai@gmail.com'],  # Send to (your admin email)
                [],
                reply_to=[email]  # Email from the form to get back to
            ).send()
            return redirect('/')
    else:
        form = ContactForm()
    return render(request, 'home/contact.html', {'form': form})
