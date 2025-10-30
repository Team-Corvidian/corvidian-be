from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ArticleViewSet, ArticleDetailBySlugView, ConsultationSubmitView, NewsletterSubscribeView

router = DefaultRouter()
router.register(r'articles', ArticleViewSet, basename='articles')

urlpatterns = [
    path('', include(router.urls)),
    path('wawasan/slug/<slug:slug>/', ArticleDetailBySlugView.as_view(), name='article-detail-by-slug'),
    path("consultation/submit/", ConsultationSubmitView.as_view(), name="consultation-submit"),
    path("subscribe/", NewsletterSubscribeView.as_view()),
]
