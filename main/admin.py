from django.contrib import admin
from .models import Article

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'published_at', 'updated_at')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'author', 'content')
    list_filter = ('published_at',)
