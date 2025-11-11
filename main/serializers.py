from django.conf import settings
from rest_framework import serializers
from .models import Article

def get_cover_image_url(obj, request=None):
    if not obj.cover_image:
        return None
    base_url = getattr(settings, 'SITE_URL', '').rstrip('/')
    if base_url:
        return f"{base_url}{obj.cover_image.url}"
    if request:
        return request.build_absolute_uri(obj.cover_image.url)
    return obj.cover_image.url


class ArticleListSerializer(serializers.ModelSerializer):
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ['id', 'slug', 'title', 'author', 'published_at', 'cover_image', 'excerpt', 'created_at', 'updated_at']

    def get_cover_image(self, obj):
        return get_cover_image_url(obj, self.context.get('request'))


class ArticleDetailSerializer(serializers.ModelSerializer):
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ['id', 'slug', 'title', 'author', 'published_at', 'cover_image', 'content', 'created_at', 'updated_at']

    def get_cover_image(self, obj):
        return get_cover_image_url(obj, self.context.get('request'))
