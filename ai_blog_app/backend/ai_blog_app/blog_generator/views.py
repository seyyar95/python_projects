from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import json
from pytube import YouTube
import os
import assemblyai as ai
import openai
from .models import BlogPost

# Create your views here.
@login_required
def index(request):
    return render(request, "index.html")


@csrf_exempt
def generate_blog(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            yt_link = data["link"]
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({"error": "Invalid data sent"}, status=400)

        # get yt title
        title = yt_title(yt_link)

        # get transcript
        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({"error": "Transcription failed"}, status=500)

        # use OPENAI to generate blog
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({"error": "Blog generation failed"}, status=500)
        
        # save blog to database
        new_blog_article = BlogPost.objects.create(
            user=request.user,
            youtube_title=title,
            youtube_link=yt_link,
            generated_content=blog_content
        )
        new_blog_article.save()
        # return blog as response
        return JsonResponse({'content': blog_content})
    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)


def yt_title(link):
    yt = YouTube(link)
    return yt.title


def download_audio(link):
    yt = YouTube(link)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download(output_path=settings.MEDIA_ROOT)
    base, ext = os.path.splitext(out_file)
    new_file = base + ".mp3"
    os.rename(out_file, new_file)
    return new_file


def get_transcription(link):
    audio_file = download_audio(link)
    ai.settings.api_key = "#"

    transcriber = ai.Transcriber()
    transcript = transcriber.transcribe(audio_file)

    return transcript.text


def generate_blog_from_transcription(transcription):
    openai.api_key = "#"

    prompt = f"Based on the flollowing transcript from a Youtube video, write a comprehensive blog article, write it based on the transcript, but do not make it look like a youtube video, make it look like a proper blog article:\n\n{transcription}\n\nArticle:"

    response = openai.completions.create(
        model="gpt-3.5-turbo",
        prompt=prompt,
        max_tokens=1000
    )

    generated_blog = response.choices[0].text.strip()
    return generated_blog


def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user)
    return render(request, 'all-blogs.html', {'blog_articles': blog_articles})

def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})
    else:
        return redirect('/')


def user_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("/")
        else:
            return render(
                request, "login.html", {"error_message": "Invalid username or password"}
            )
    return render(request, "login.html")


def user_signup(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        repeatPassword = request.POST["repeatPassword"]

        if password == repeatPassword:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect("/")
            except:
                error_message = "Error creating account"
                return render(request, "signup.html", {"error_message": error_message})
        else:
            return render(
                request, "signup.html", {"error_message": "Passwords do not match"}
            )
    return render(request, "signup.html")


def user_logout(request):
    logout(request)
    return redirect("/")
