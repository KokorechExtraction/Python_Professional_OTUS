from django.contrib import admin
from .models import Post, Comment, Tag


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("author", "content", "views",)

    ordering = ("author",)
    list_filter = ("author",)
    search_fields = ("author",)
    search_help_text = "Введите слово для поиска"

    fields = ("author", "content", "views",)

    def tag_list(self, obj):
        return ", ".join(tag.name for tag in obj.tags.all())

    tag_list.short_description = 'Тэги'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('text', 'author', 'post')
    list_filter = ('author',)
    search_fields = ('text',)

    fieldsets = (
        ('Основная информация', {
            'fields': ('text', 'author')
        }),
        ('Дополнительная информация', {
            'fields': ('post',),
            'classes': ('collapse',)
        })
    )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_filter = ('name',)
    search_fields = ('name',)