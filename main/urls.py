from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ArticleViewSet, ArticleDetailBySlugView

router = DefaultRouter()
router.register(r'wawasan', ArticleViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('wawasan/slug/<slug:slug>/', ArticleDetailBySlugView.as_view(), name='article-detail-by-slug'),
]
