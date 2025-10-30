from rest_framework import viewsets, generics
from rest_framework.response import Response
from rest_framework import status
from .models import Article, ConsultationLead, NewsletterSubscriber
from .serializers import ArticleSerializer
from rest_framework.views import APIView
from django.core.mail import send_mail
from django.conf import settings
import urllib.parse

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all().order_by('-published_at')
    serializer_class = ArticleSerializer

class ArticleDetailBySlugView(generics.RetrieveAPIView):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    lookup_field = 'slug'

    def get(self, request, *args, **kwargs):
        try:
            article = self.get_object()
            serializer = self.get_serializer(article)
            return Response(serializer.data)
        except Article.DoesNotExist:
            return Response({"detail": "Article not found"}, status=status.HTTP_404_NOT_FOUND)

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
        wa_number = settings.CONSULTATION_WHATSAPP

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [receiver_email],
            fail_silently=False,
        )

        wa_message = urllib.parse.quote(
            f"Halo, saya {name} dari {company}. Email: {email}, Telepon: {phone}. Pertanyaan: {question}"
        )

        wa_url = f"https://wa.me/{wa_number}?text={wa_message}"

        return Response({
            "success": True,
            "message": "Form submitted. Redirect to WhatsApp.",
            "whatsapp_url": wa_url,
        })

class NewsletterSubscribeView(APIView):
    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response({"error": "Email required"}, status=400)

        send_mail(
            "New Newsletter Subscriber",
            f"New subscriber: {email}",
            settings.DEFAULT_FROM_EMAIL,
            [settings.CONSULTATION_RECEIVER_EMAIL],  
        )

        return Response({"success": True})
    

class NewsletterSubscribeView(APIView):
    def post(self, request):
        email = request.data.get("email")
        source = request.data.get("source", "footer")
        if not email:
            return Response({"error": "Email is required"}, status=400)

        obj, created = NewsletterSubscriber.objects.get_or_create(email=email, defaults={"source": source})

        admin_subject = "New Newsletter Subscriber"
        admin_message = f"Email: {email}\nSource: {source}"
        send_mail(admin_subject, admin_message, settings.DEFAULT_FROM_EMAIL, [settings.CONSULTATION_RECEIVER_EMAIL], fail_silently=False)

        user_subject = "Terima kasih sudah subscribe Corvidian"
        user_message = (
            "Hi!\n\n"
            "Terima kasih sudah berlangganan newsletter Corvidian.\n"
            "Kami akan kirim insight seputar teknologi, automasi, dan transformasi digital.\n\n"
            "Salam,\nCorvidian Team\nwww.corvidian.io"
        )
        send_mail(user_subject, user_message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)

        return Response({"success": True, "created": created}, status=200)
