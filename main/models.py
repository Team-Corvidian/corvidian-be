from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from django.utils.html import escape, strip_tags
from django.utils.text import slugify
from ckeditor_uploader.fields import RichTextUploadingField
from PIL import Image
from bs4 import BeautifulSoup
import io
import base64
import os


class Article(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    author = models.CharField(max_length=100)
    published_at = models.DateField()
    cover_image = models.ImageField(upload_to='wawasan/covers/', blank=True, null=True)
    content = RichTextUploadingField()
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
    body = RichTextUploadingField(blank=True, null=True)
    hero_image = models.ImageField(upload_to="newsletter/messages/", blank=True, null=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.hero_image and hasattr(self.hero_image, 'file'):
            try:
                if self.pk:
                    old_instance = self.__class__.objects.filter(pk=self.pk).first()
                    if not old_instance or old_instance.hero_image != self.hero_image:
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
            
            max_width = 600
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=70, optimize=True)
            output.seek(0)
            
            original_name = image_field.name
            name_parts = original_name.rsplit('.', 1)
            new_name = name_parts[0] + '.jpg'
            
            return ContentFile(output.read(), name=new_name)
        except Exception as e:
            print(f"Error compressing image: {e}")
            return image_field

    def build_html_body(self, request=None):
        print("\nBuilding email HTML")
        
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        is_localhost = 'localhost' in site_url or '127.0.0.1' in site_url
        
        print(f"Site URL: {site_url}")
        print(f"Is localhost: {is_localhost}")
        
        content_html = self.body or ""
        
        if content_html:
            try:
                soup = BeautifulSoup(content_html, 'html.parser')
                images = soup.find_all('img')
                print(f"Found {len(images)} images in body")
                
                for idx, img in enumerate(images, 1):
                    src = img.get('src', '')
                    print(f"\nBody Image {idx}: {src[:80]}")
                    
                    if src.startswith('data:'):
                        print("Already base64")
                        continue
                    
                    if is_localhost:
                        try:
                            file_path = src.replace('/media/', '').replace('media/', '').lstrip('/')
                            full_path = os.path.join(settings.MEDIA_ROOT, file_path)
                            
                            print(f"Full path: {full_path}")
                            print(f"Exists: {os.path.exists(full_path)}")
                            
                            if os.path.exists(full_path):
                                with open(full_path, 'rb') as f:
                                    img_data = f.read()
                                    base64_data = base64.b64encode(img_data).decode()
                                    
                                    if full_path.lower().endswith('.png'):
                                        mime = 'image/png'
                                    elif full_path.lower().endswith('.gif'):
                                        mime = 'image/gif'
                                    else:
                                        mime = 'image/jpeg'
                                    
                                    img['src'] = f"data:{mime};base64,{base64_data}"
                                    print(f"Converted to base64 ({len(base64_data)} chars)")
                            else:
                                print("File not found")
                        except Exception as e:
                            print(f"Error: {e}")
                    else:
                        if not src.startswith('http'):
                            img['src'] = f"{site_url}/{src.lstrip('/')}"
                        print(f"Using URL: {img['src']}")
                    
                    img['style'] = 'display:block;max-width:100%;width:auto;height:auto;border:0;outline:none;text-decoration:none;margin:10px 0;'
                    
                    if img.get('width'):
                        del img['width']
                    if img.get('height'):
                        del img['height']
                
                content_html = str(soup)
            except Exception as e:
                print(f"Error processing body: {e}")

        hero_markup = ""
        if self.hero_image:
            print("\nProcessing hero image")
            
            try:
                hero_path = self.hero_image.path
                print(f"Hero path: {hero_path}")
                print(f"Exists: {os.path.exists(hero_path)}")
                
                if os.path.exists(hero_path):
                    file_size = os.path.getsize(hero_path)
                    print(f"Size: {file_size} bytes ({file_size/1024:.1f} KB)")
                
                if is_localhost and os.path.exists(hero_path):
                    with open(hero_path, 'rb') as f:
                        img_data = f.read()
                        base64_data = base64.b64encode(img_data).decode()
                        image_url = f"data:image/jpeg;base64,{base64_data}"
                        print(f"Hero converted to base64 ({len(base64_data)} chars)")
                else:
                    image_url = f"{site_url}{self.hero_image.url}"
                    print(f"Using URL: {image_url}")
                
                hero_markup = f'<div style="margin:0 0 20px 0;padding:0;"><img src="{image_url}" alt="{escape(self.subject)}" style="display:block;max-width:100%;width:100%;height:auto;border:0;outline:none;text-decoration:none;border-radius:8px;" /></div>'
                
            except Exception as e:
                print(f"Error with hero: {e}")

        body_content = f"{hero_markup}{content_html}" if hero_markup or content_html else ""
        
        email_html = '<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>' + escape(self.subject) + '</title></head><body style="margin:0;padding:0;background-color:#f4f4f4;font-family:Arial,sans-serif;"><table role="presentation" style="width:100%;border-collapse:collapse;background-color:#f4f4f4;"><tr><td align="center" style="padding:20px 0;"><table role="presentation" style="max-width:600px;width:100%;background-color:#ffffff;border-collapse:collapse;box-shadow:0 2px 4px rgba(0,0,0,0.1);"><tr><td style="padding:30px;color:#333333;line-height:1.6;">' + body_content + '</td></tr><tr><td style="padding:20px 30px;background-color:#f9f9f9;text-align:center;color:#666666;font-size:12px;border-top:1px solid #eeeeee;"><p style="margin:0 0 10px 0;">Corvidian Newsletter</p><p style="margin:0;"><a href="https://www.corvidian.io" style="color:#007bff;text-decoration:none;">www.corvidian.io</a></p></td></tr></table></td></tr></table></body></html>'
        
        print(f"\nHTML built: {len(email_html)} chars")
        print(f"Has base64: {'YES' if 'data:image' in email_html else 'NO'}\n")
        
        return email_html

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
                print(f"Failed to send to {email}: {e}")
                continue

        self.is_sent = True
        self.sent_at = timezone.now()
        self.save(update_fields=["is_sent", "sent_at"])

        return sent_count