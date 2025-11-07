from django.contrib import admin, messages
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.html import strip_tags
from .models import (
    Article,
    ConsultationLead,
    NewsletterSubscriber,
    NewsletterWelcomeMessage,
    NewsletterCampaign,
)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'published_at', 'updated_at')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'author', 'content')
    list_filter = ('published_at',)


@admin.register(ConsultationLead)
class ConsultationLeadAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "company", "created_at")
    search_fields = ("name", "email", "company", "phone")
    list_filter = ("created_at",)


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "source", "created_at")
    search_fields = ("email", "source")
    list_filter = ("created_at", "source")


@admin.register(NewsletterWelcomeMessage)
class NewsletterWelcomeMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("subject", "body")
    readonly_fields = ("updated_at",)
    actions = ["send_test_email"]
    
    fieldsets = (
        (None, {"fields": ("subject", "is_active")}),
        ("Content", {"fields": ("body",)}),
        ("Media", {"fields": ("hero_image",)}),
        ("Metadata", {"fields": ("updated_at",)})
    )

    @admin.action(description="Send test email to yourself")
    def send_test_email(self, request, queryset):
        admin_email = request.user.email
        if not admin_email:
            self.message_user(
                request,
                "Your admin account doesn't have an email address.",
                level=messages.ERROR,
            )
            return

        sent_count = 0
        for msg in queryset:
            try:
                html_body = msg.build_html_body(request)
                plain_body = msg.build_plain_body() or strip_tags(html_body or "")

                email = EmailMultiAlternatives(
                    f"{msg.subject}",
                    plain_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [admin_email],
                )
                if html_body:
                    email.attach_alternative(html_body, "text/html")
                email.send()
                sent_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to send '{msg.subject}': {str(e)}",
                    level=messages.ERROR,
                )

        if sent_count > 0:
            self.message_user(
                request,
                f"Sent {sent_count} test email(s) to {admin_email}",
                level=messages.SUCCESS,
            )


@admin.register(NewsletterCampaign)
class NewsletterCampaignAdmin(admin.ModelAdmin):
    list_display = ("subject", "is_sent", "scheduled_for", "sent_at", "updated_at")
    list_filter = ("is_sent", "created_at")
    search_fields = ("subject", "body")
    readonly_fields = ("sent_at", "created_at", "updated_at")
    actions = ["send_campaign", "send_test_email"]
    
    fieldsets = (
        (None, {"fields": ("subject", "is_sent", "scheduled_for")}),
        ("Content", {"fields": ("body",)}),
        ("Media", {"fields": ("hero_image",)}),
        ("Delivery", {"fields": ("sent_at", "created_at", "updated_at")}),
    )

    @admin.action(description="Send test email to yourself")
    def send_test_email(self, request, queryset):
        admin_email = request.user.email
        if not admin_email:
            self.message_user(
                request,
                "Your admin account doesn't have an email address.",
                level=messages.ERROR,
            )
            return

        sent_count = 0
        for campaign in queryset:
            try:
                html_body = campaign.build_html_body(request)
                plain_body = campaign.build_plain_body() or strip_tags(html_body or "")

                email = EmailMultiAlternatives(
                    f"{campaign.subject}",
                    plain_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [admin_email],
                )
                if html_body:
                    email.attach_alternative(html_body, "text/html")
                email.send()
                sent_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to send '{campaign.subject}': {str(e)}",
                    level=messages.ERROR,
                )

        if sent_count > 0:
            self.message_user(
                request,
                f"Sent {sent_count} test email(s) to {admin_email}",
                level=messages.SUCCESS,
            )

    @admin.action(description="Send selected campaigns to all subscribers")
    def send_campaign(self, request, queryset):
        total_emails = 0
        sent_campaigns = 0
        
        for campaign in queryset:
            sent = campaign.send_to_subscribers(request=request)
            if sent:
                total_emails += sent
                sent_campaigns += 1
        
        if total_emails:
            self.message_user(
                request,
                f"Sent {total_emails} email(s) via {sent_campaigns} campaign(s).",
                level=messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                "No emails were sent (already sent or no subscribers).",
                level=messages.WARNING,
            )