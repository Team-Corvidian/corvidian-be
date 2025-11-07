from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from django.utils.html import escape, strip_tags
from django.utils.text import slugify
from ckeditor.fields import RichTextField
from PIL import Image
from bs4 import BeautifulSoup
import io


class Article(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    author = models.CharField(max_length=100)
    published_at = models.DateField()
    cover_image = models.ImageField(upload_to='wawasan/covers/', blank=True, null=True)
    content = RichTextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ConsultationLead(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    company = models.CharField(max_length=200)
    question = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.company}"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    source = models.CharField(max_length=100, default="footer")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class NewsletterContent(models.Model):
    subject = models.CharField(max_length=255)
    body = RichTextField(blank=True, null=True)
    hero_image = models.ImageField(upload_to="newsletter/messages/", blank=True, null=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.hero_image:
            try:
                if self.pk:
                    old_instance = self.__class__.objects.filter(pk=self.pk).first()
                    if old_instance and old_instance.hero_image != self.hero_image:
                        self.hero_image = self._compress_image(self.hero_image)
                else:
                    self.hero_image = self._compress_image(self.hero_image)
            except Exception as e:
                print(f"Image compression failed: {e}")
        
        super().save(*args, **kwargs)

    def _compress_image(self, image_field):
        try:
            img = Image.open(image_field)
            
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            
            max_width = 800
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            output.seek(0)
            
            original_name = image_field.name
            name_parts = original_name.rsplit('.', 1)
            new_name = name_parts[0] + '.jpg'
            
            return ContentFile(output.read(), name=new_name)
        except Exception as e:
            print(f"Error in _compress_image: {e}")
            return image_field

    def _process_inline_images(self, html_content, request=None):
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            for img in soup.find_all('img'):
                if request and img.get('src') and not img['src'].startswith('http'):
                    img['src'] = request.build_absolute_uri(img['src'])
                
                img['style'] = (
                    'display:block;max-width:100%;width:auto;height:auto;'
                    'border:0;outline:none;text-decoration:none;margin:10px 0;'
                )
                
                if img.get('width'):
                    del img['width']
                if img.get('height'):
                    del img['height']
            
            return str(soup)
        except Exception as e:
            print(f"Error processing inline images: {e}")
            return html_content

    def build_html_body(self, request=None):
        content_html = self.body or ""
        
        if content_html:
            content_html = self._process_inline_images(content_html, request)

        hero_markup = ""
        if self.hero_image:
            image_url = self.hero_image.url
            if request:
                image_url = request.build_absolute_uri(image_url)
            
            hero_markup = (
                f'<div style="margin:0 0 20px 0;padding:0;">'
                f'<img src="{image_url}" alt="{escape(self.subject)}" '
                f'style="display:block;max-width:100%;width:100%;height:auto;'
                f'border:0;outline:none;text-decoration:none;border-radius:8px;" />'
                f'</div>'
            )

        body_content = f"{hero_markup}{content_html}" if hero_markup or content_html else ""
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(self.subject)}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f4;font-family:Arial,sans-serif;">
    <table role="presentation" style="width:100%;border-collapse:collapse;background-color:#f4f4f4;">
        <tr>
            <td align="center" style="padding:20px 0;">
                <table role="presentation" style="max-width:600px;width:100%;background-color:#ffffff;border-collapse:collapse;box-shadow:0 2px 4px rgba(0,0,0,0.1);">
                    <tr>
                        <td style="padding:30px;color:#333333;line-height:1.6;">
                            {body_content}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:20px 30px;background-color:#f9f9f9;text-align:center;color:#666666;font-size:12px;border-top:1px solid #eeeeee;">
                            <p style="margin:0 0 10px 0;">Corvidian Newsletter</p>
                            <p style="margin:0;"><a href="https://www.corvidian.io" style="color:#007bff;text-decoration:none;">www.corvidian.io</a></p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    def build_plain_body(self):
        return strip_tags(self.body or "").strip()


class NewsletterWelcomeMessage(NewsletterContent):
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Newsletter welcome message"
        verbose_name_plural = "Newsletter welcome messages"

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.subject} ({status})"


class NewsletterCampaign(NewsletterContent):
    is_sent = models.BooleanField(default=False)
    scheduled_for = models.DateTimeField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        status = "Sent" if self.is_sent else "Draft"
        return f"{self.subject} ({status})"

    def send_to_subscribers(self, request=None):
        if self.is_sent:
            return 0

        recipients = list(NewsletterSubscriber.objects.values_list("email", flat=True))
        if not recipients:
            return 0

        html_body = self.build_html_body(request)
        plain_body = self.build_plain_body() or strip_tags(html_body or "") or ""

        sent_count = 0
        for email in recipients:
            try:
                message = EmailMultiAlternatives(
                    self.subject,
                    plain_body or "",
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                )
                if html_body:
                    message.attach_alternative(html_body, "text/html")
                message.send()
                sent_count += 1
            except Exception as e:
                print(f"Failed to send email to {email}: {e}")
                continue

        self.is_sent = True
        self.sent_at = timezone.now()
        self.save(update_fields=["is_sent", "sent_at"])

        return sent_count