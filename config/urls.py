"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from config.sitemaps import sitemaps
from pages.views import robots_txt

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("accounts/", include("allauth.urls")),
    path("plans/", include("plans.urls")),
    path("shop/", include("products.urls")),
    path("cart/", include("cart.urls")),
    path("orders/", include("orders.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("community/", include("community.urls")),
    path("blog/", include("blog.urls")),
    path("reviews/", include("reviews.urls")),
    path("challenges/", include("challenges.urls")),
    path("newsletter/", include("newsletter.urls")),
    path("", include("subscriptions.urls")),
    path("", include("pages.urls", namespace="pages")),
]
