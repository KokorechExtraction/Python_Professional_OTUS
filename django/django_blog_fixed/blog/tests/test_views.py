from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from blog.models import Post, Tag


class BlogViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username="u1", password="pass12345")

        cls.tag1 = Tag.objects.create(name="t1")

        cls.post = Post.objects.create(
            author=cls.user,
            title="Hello",
            content="Body",
            views=0,
        )
        cls.post.tags.add(cls.tag1)

    def test_index_200(self):
        resp = self.client.get(reverse("index"))
        self.assertEqual(resp.status_code, 200)

    def test_post_list_200(self):
        resp = self.client.get(reverse("post_list"))
        self.assertEqual(resp.status_code, 200)

    def test_post_list_ordering_by_created_at_asc(self):
        # создаём второй пост и вручную делаем его "раньше", чтобы проверить порядок
        p2 = Post.objects.create(
            author=self.user,
            title="Second",
            content="Second body",
            views=0,
        )
        p2.tags.add(self.tag1)

        # делаем p2 более ранним по времени, чем self.post
        earlier = timezone.now() - timezone.timedelta(days=1)
        Post.objects.filter(pk=p2.pk).update(created_at=earlier)

        resp = self.client.get(reverse("post_list"))
        self.assertEqual(resp.status_code, 200)

        posts = list(resp.context["posts"])
        self.assertGreaterEqual(len(posts), 2)
        # PostListView.order_by("created_at") => ранний должен быть первым
        self.assertEqual(posts[0].pk, p2.pk)
        self.assertEqual(posts[1].pk, self.post.pk)

    def test_post_detail_200(self):
        resp = self.client.get(reverse("post_detail", kwargs={"pk": self.post.pk}))
        self.assertEqual(resp.status_code, 200)

    def test_post_detail_increments_views(self):
        self.post.refresh_from_db()
        self.assertEqual(self.post.views, 0)

        self.client.get(reverse("post_detail", kwargs={"pk": self.post.pk}))
        self.post.refresh_from_db()
        self.assertEqual(self.post.views, 1)

        self.client.get(reverse("post_detail", kwargs={"pk": self.post.pk}))
        self.post.refresh_from_db()
        self.assertEqual(self.post.views, 2)

    def test_post_create_page_requires_login(self):
        # PostCreateView = LoginRequiredMixin, значит редирект на LOGIN_URL
        resp = self.client.get(reverse("add_post"))
        self.assertEqual(resp.status_code, 302)
        # дефолтный login URL у Django: /accounts/login/
        self.assertIn("/accounts/login/", resp["Location"])
