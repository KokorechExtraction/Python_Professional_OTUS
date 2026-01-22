from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import FormView, DetailView, TemplateView, CreateView, UpdateView, DeleteView, ListView
from django.contrib import messages

from .models import Post, Comment
from .forms import PostModelForm


class IndexTemplateView(TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Моя оборона'
        context['description'] = 'Добро пожаловать в Мою оборону'
        return context


class PostListView(ListView):
    model = Post
    template_name = "blog/post_list.html"
    context_object_name = "posts"

    def get_queryset(self):
        return Post.objects.order_by("created_at")


class PostDetailView(DetailView):
    model = Post
    template_name = "blog/post_detail.html"
    context_object_name = "post"

    def get(self, request, *args, **kwargs):
        post = self.get_object()
        # Increment view counter safely.
        post.views = (post.views or 0) + 1
        post.save(update_fields=["views"])
        return super().get(request, *args, **kwargs)


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    template_name = "blog/add_post.html"
    form_class = PostModelForm
    success_url = reverse_lazy("post_list")

    def form_valid(self, form):
        form.instance.author = self.request.user
        res = super().form_valid(form)
        messages.success(self.request, 'Пост успешно создан')
        return res


class PostUpdateView(UpdateView):
    model = Post
    template_name = "blog/edit_post.html"
    form_class = PostModelForm

    def get_success_url(self):
        return reverse_lazy("post_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        res = super().form_valid(form)
        messages.success(self.request, 'Пост успешно обновлен')
        return res


class PostDeleteView(DeleteView):
    model = Post
    template_name = "blog/post_delete.html"
    success_url = reverse_lazy('post_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Удаление поста"
        context["description"] = "Вы уверены, что хотите удалить этот пост?"
        return context

    def form_valid(self, form):
        res = super().form_valid(form)
        messages.success(self.request, 'Пост успешно удален')
        return res
