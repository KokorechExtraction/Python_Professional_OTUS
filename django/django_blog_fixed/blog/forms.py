from django import forms
from django.core.exceptions import ValidationError

from blog.models import Post


class PostModelForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'tags']
        labels = {
            'content': 'Содержание',
            'tags': 'Теги',
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Введите содержимое поста'}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }


    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content')
        forbidden_words = ['пластмассовый мир победил']

        if content:
            for word in forbidden_words:
                if word in content.lower():
                    raise ValidationError(f'Пластмассовый мир идет туда-сюда вместе с тобой')
