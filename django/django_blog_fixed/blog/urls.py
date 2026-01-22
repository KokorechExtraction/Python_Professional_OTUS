from django.urls import path

from .views import IndexTemplateView, PostListView, PostCreateView, PostDetailView, PostUpdateView, PostDeleteView

urlpatterns = [
    path("", IndexTemplateView.as_view(), name="index"),
    path("posts/", PostListView.as_view(), name="post_list"),
    path("posts/add/", PostCreateView.as_view(), name="add_post"),
    path("posts/<int:pk>/", PostDetailView.as_view(), name="post_detail"),
    path("posts/<int:pk>/edit", PostUpdateView.as_view(), name="edit_post"),
    path("posts/delete/<int:pk>/", PostDeleteView.as_view(), name="post_delete"),

]