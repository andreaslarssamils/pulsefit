from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def send_order_confirmation_email(order):
    body = render_to_string(
        "orders/email/order_confirmation.txt", {"order": order})
    send_mail(
        subject=f"Your PulseFit order {order.order_number}",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.user.email],
        fail_silently=True,
    )
