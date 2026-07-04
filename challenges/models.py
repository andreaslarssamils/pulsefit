from django.db import models
from django.utils import timezone


class Challenge(models.Model):
    """Time-limited group fitness challenge, managed in the Django admin"""

    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.URLField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.title

    @property
    def status(self):
        """upcoming / active / ended, derived from today's date"""
        today = timezone.localdate()
        if today < self.start_date:
            return "upcoming"
        if today > self.end_date:
            return "ended"
        return "active"
