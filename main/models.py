from django.db import models
from django.utils.text import slugify
from ckeditor.fields import RichTextField

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

