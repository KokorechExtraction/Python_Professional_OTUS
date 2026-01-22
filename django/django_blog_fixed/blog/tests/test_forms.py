from django.test import TestCase

from blog.forms import PostModelForm
from blog.models import Tag


class PostModelFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tag = Tag.objects.create(name="t1")

    def test_form_valid_normal_text(self):
        form = PostModelForm(
            data={"title": "T", "content": "нормальный текст", "tags": [self.tag.pk]}
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejects_forbidden_phrase(self):
        form = PostModelForm(
            data={"title": "T", "content": "Пластмассовый мир победил", "tags": [self.tag.pk]}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Пластмассовый мир идет туда-сюда вместе с тобой", str(form.errors))
