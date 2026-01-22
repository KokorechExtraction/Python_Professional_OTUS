from django.db import models

from django.contrib.auth import get_user_model
from django.conf import settings

# User = get_user_model()


class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name="posts"
    )
    title = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    tags = models.ManyToManyField("Tag", related_name="posts")
    views = models.IntegerField(default=0)


    def __str__(self):
        return self.title

class Comment(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name="comment"
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")


class Tag(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


