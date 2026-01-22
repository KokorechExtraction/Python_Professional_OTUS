from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from blog.models import Post, Tag


class BlogCrudTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(username="u1", password="pass12345")

        cls.tag1 = Tag.objects.create(name="t1")
        cls.tag2 = Tag.objects.create(name="t2")

        cls.post = Post.objects.create(
            author=cls.user,
            title="Old title",
            content="Old content",
            views=0,
        )
        cls.post.tags.add(cls.tag1)

    def test_create_post_sets_author_and_redirects(self):
        self.client.force_login(self.user)

        resp = self.client.post(
            reverse("add_post"),
            data={
                "title": "New title",
                "content": "New content",
                "tags": [self.tag1.pk, self.tag2.pk],
            },
        )
        # CreateView по успеху редиректит на success_url
        self.assertIn(resp.status_code, (302, 303))

        created = Post.objects.get(title="New title")
        self.assertEqual(created.author_id, self.user.id)
        self.assertEqual(created.content, "New content")
        self.assertEqual(set(created.tags.values_list("name", flat=True)), {"t1", "t2"})

    def test_update_post_changes_title_content_and_tags(self):
        resp = self.client.post(
            reverse("edit_post", kwargs={"pk": self.post.pk}),
            data={
                "title": "Updated title",
                "content": "Updated content",
                "tags": [self.tag2.pk],
            },
        )
        self.assertIn(resp.status_code, (302, 303))

        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "Updated title")
        self.assertEqual(self.post.content, "Updated content")
        self.assertEqual(list(self.post.tags.values_list("name", flat=True)), ["t2"])

    def test_delete_post_deletes_and_redirects(self):
        pk = self.post.pk

        resp = self.client.post(reverse("post_delete", kwargs={"pk": pk}))
        self.assertIn(resp.status_code, (302, 303))

        self.assertFalse(Post.objects.filter(pk=pk).exists())
