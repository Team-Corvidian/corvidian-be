from django.urls import path, include
from .views import ArticleViewSet, ArticleDetailBySlugView, ConsultationSubmitView, NewsletterSubscribeView


urlpatterns = [
    path('wawasan/', ArticleViewSet.as_view({'get': 'list'}), name='article-list'),
    path('wawasan/slug/<slug:slug>/', ArticleDetailBySlugView.as_view(), name='article-detail-by-slug'),
    path("consultation/submit/", ConsultationSubmitView.as_view(), name="consultation-submit"),
    path("subscribe/", NewsletterSubscribeView.as_view()),
]
