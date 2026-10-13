from datetime import timedelta

from django.utils.translation import gettext as _

from .models import Payment

SIMILARITY_DAYS = 3


def review_reason():
    """Text stored with a flagged payment, in the language active at that moment."""
    return _(
        "مدفوعات متشابهة: نفس الاشتراك والمبلغ والعملة وتاريخ متقارب "
        "(خلال %(days)s أيام). قد تكون مقصودة، راجعها بنفسك."
    ) % {"days": SIMILARITY_DAYS}


def find_similar(payment):
    """Other non-archived payments of the same user with the same subscription,
    amount, currency and a close date. Similar does NOT mean duplicate or fraud."""
    if not payment.subscription_id:
        return Payment.objects.none()
    window = timedelta(days=SIMILARITY_DAYS)
    return Payment.objects.filter(
        user_id=payment.user_id,
        subscription_id=payment.subscription_id,
        amount=payment.amount,
        currency=payment.currency,
        is_archived=False,
        payment_date__range=(payment.payment_date - window, payment.payment_date + window),
    ).exclude(pk=payment.pk)


def flag_similar(payment):
    """Mark the payment (and its look-alikes) as 'needs review'. Never deletes anything."""
    ids = list(find_similar(payment).values_list("pk", flat=True))
    if not ids:
        return False
    reason = review_reason()
    Payment.objects.filter(pk__in=ids + [payment.pk]).update(review_required=True, review_reason=reason)
    payment.review_required = True
    payment.review_reason = reason
    return True
