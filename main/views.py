import threading
import urllib.parse
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail, EmailMultiAlternatives
from django.http import Http404
from rest_framework import status
from rest_framework import viewsets, generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    ARTICLE_LIST_CACHE_KEY,
    Article,
    ConsultationLead,
    NewsletterSubscriber,
    NewsletterWelcomeMessage,
    article_detail_cache_key,
)
from .serializers import ArticleDetailSerializer, ArticleListSerializer


CACHE_TIMEOUT = getattr(settings, "CACHE_TTL", 300)


def run_async(target, *args, **kwargs):
    threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True).start()

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all().order_by('-published_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return ArticleListSerializer
        return ArticleDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, 'action', None) == 'list':
            return queryset.defer('content')
        return queryset

    def list(self, request, *args, **kwargs):
        cache_key = ARTICLE_LIST_CACHE_KEY if not request.query_params else None
        if cache_key:
            cached = cache.get(cache_key)
            if cached:
                return Response(cached)
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            if cache_key:
                cache.set(cache_key, response.data, CACHE_TIMEOUT)
            return response
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        if cache_key:
            cache.set(cache_key, data, CACHE_TIMEOUT)
        return Response(data)


class ArticleDetailBySlugView(generics.RetrieveAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleDetailSerializer
    lookup_field = 'slug'

    def get(self, request, *args, **kwargs):
        slug = kwargs.get(self.lookup_field)
        cache_key = article_detail_cache_key(slug) if slug else None
        if cache_key:
            cached = cache.get(cache_key)
            if cached:
                return Response(cached)
        try:
            article = self.get_object()
        except Http404:
            return Response({"detail": "Article not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(article)
        data = serializer.data
        if cache_key:
            cache.set(cache_key, data, CACHE_TIMEOUT)
        return Response(data)


class ConsultationSubmitView(APIView):
    def post(self, request):
        data = request.data

        required_fields = ["name", "email", "phone", "company", "question"]
        for field in required_fields:
            if field not in data or not data[field]:
                return Response({"error": f"{field} is required"}, status=400)

        name = data["name"]
        email = data["email"]
        phone = data["phone"]
        company = data["company"]
        question = data["question"]

        ConsultationLead.objects.create(
            name=name,
            email=email,
            phone=phone,
            company=company,
            question=question,
        )

        subject = f"Konsultasi Baru dari {name}"
        message = (
            f"Nama: {name}\n"
            f"Email: {email}\n"
            f"Telepon: {phone}\n"
            f"Perusahaan: {company}\n\n"
            f"Pertanyaan:\n{question}"
        )

        receiver_email = settings.CONSULTATION_RECEIVER_EMAIL

        run_async(
            send_mail,
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [receiver_email],
        )

        wa_number = (settings.CONSULTATION_WHATSAPP or "").strip()
        wa_url = None
        if wa_number:
            wa_message = urllib.parse.quote(
                f"Halo, saya {name} dari {company}. Email: {email}, Telepon: {phone}. Pertanyaan: {question}"
            )
            wa_url = f"https://wa.me/{wa_number}?text={wa_message}"

        response_data = {
            "success": True,
            "message": "Form submitted.",
        }
        if wa_url:
            response_data.update({
                "message": "Form submitted. Redirect to WhatsApp.",
                "whatsapp_url": wa_url,
            })

        return Response(response_data)


class NewsletterSubscribeView(APIView):
    def post(self, request):
        email = request.data.get("email")
        source = request.data.get("source", "footer")
        if not email:
            return Response({"error": "Email is required"}, status=400)

        obj, created = NewsletterSubscriber.objects.get_or_create(
            email=email, 
            defaults={"source": source}
        )

        admin_subject = "New Newsletter Subscriber"
        admin_message = f"Email: {email}\nSource: {source}"
        run_async(
            send_mail,
            admin_subject,
            admin_message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.CONSULTATION_RECEIVER_EMAIL],
        )

        fallback_subject = "Terima kasih sudah subscribe Corvidian"
        fallback_message = (
            "Hi!\n\n"
            "Terima kasih sudah berlangganan newsletter Corvidian.\n"
            "Kami akan kirim insight seputar teknologi, automasi, dan transformasi digital.\n\n"
            "Salam,\nCorvidian Team\nwww.corvidian.io"
        )

        active_message = (
            NewsletterWelcomeMessage.objects.filter(is_active=True)
            .order_by("-updated_at")
            .first()
        )

        if active_message:
            user_subject = active_message.subject
            plain_body = active_message.build_plain_body()
            user_message = plain_body or fallback_message
            html_body = active_message.build_html_body(request)
            
            message = EmailMultiAlternatives(
                user_subject,
                user_message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
            )
            if html_body:
                message.attach_alternative(html_body, "text/html")
            run_async(message.send, fail_silently=False)
        else:
            run_async(
                send_mail,
                fallback_subject,
                fallback_message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
            )

        return Response({"success": True, "created": created}, status=200)
