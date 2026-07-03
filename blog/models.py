from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class BlogPost(models.Model):
    """Editorial blog article, authored in the Django admin (US-25/26/27)."""

    STATUS_CHOICES = [("draft", "Draft"), ("published", "Published")]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    excerpt = models.CharField(max_length=300, blank=True)
    body = models.TextField()
    image = models.URLField(blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blog_posts",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Auto-fill slug for seeded/programmatic rows (admin also prepopulates it).
        if not self.slug:
            self.slug = slugify(self.title)
        # Stamp the publish time the first time the post goes live so the public
        # list can order by a real publication date.
        if self.status == "published" and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("blog:detail", kwargs={"slug": self.slug})
