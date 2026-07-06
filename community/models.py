from django.conf import settings
from django.db import models
from django.utils.timezone import localtime


class CommunityPost(models.Model):
    """A member post in the public community feed"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="community_posts",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}: {self.body[:40]}"

    @property
    def iso_timestamp(self):
        """Valid HTML ``datetime`` value (seconds precision, keeps offset).

        ``date:'c'`` emits 6-digit microseconds, which the HTML ``datetime``
        attribute rejects (a fraction of a second must be 1-3 digits)."""
        return localtime(self.created_at).replace(microsecond=0).isoformat()
