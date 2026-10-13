"""Small factories shared by the automated tests (not a test module itself)."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import Profile
from payments.models import Payment
from subscriptions.models import Category, Subscription

PASSWORD = "Str0ng-Pass!234"


def make_user(email="user@example.com", name="Tester", account_type="individual", business_name=""):
    user = get_user_model().objects.create_user(username=email, email=email, password=PASSWORD, first_name=name)
    Profile.objects.create(user=user, account_type=account_type, business_name=business_name)
    return user


def make_category(name="تصنيف اختبار"):
    return Category.objects.get_or_create(name=name)[0]


def make_subscription(user, **overrides):
    today = timezone.localdate()
    data = {
        "user": user,
        "category": make_category(),
        "service_name": "Netflix",
        "amount": Decimal("45.00"),
        "currency": "SAR",
        "billing_cycle": "monthly",
        "start_date": today - timedelta(days=30),
        "next_renewal_date": today + timedelta(days=30),
        "status": "active",
        "is_recurring": True,
        "reminder_days_before": 3,
    }
    data.update(overrides)
    return Subscription.objects.create(**data)


def make_payment(user, subscription=None, **overrides):
    today = timezone.localdate()
    data = {
        "user": user,
        "subscription": subscription,
        "amount": Decimal("45.00"),
        "currency": subscription.currency if subscription else "SAR",
        "payment_date": today,
        "status": "paid",
    }
    data.update(overrides)
    return Payment.objects.create(**data)
