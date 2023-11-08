from django.contrib.auth import login
from django.shortcuts import redirect, render
from users.forms import CustomUserCreationForm


def register(request):
    if request.method == "GET":
        return render(
            request, "users/register.html",
            {"form": CustomUserCreationForm}
        )
    elif request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('app:dashboard')
        return render(request, 'users/register.html', {'form': form})