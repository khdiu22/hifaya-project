from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from core.testing import PASSWORD, make_user

from .models import Profile

User = get_user_model()


def valid_data(**overrides):
    data = {
        "name": "سارة",
        "email": "sara@example.com",
        "password1": PASSWORD,
        "password2": PASSWORD,
        "account_type": "individual",
        "business_name": "",
    }
    data.update(overrides)
    return data


class RegisterTests(TestCase):
    url = None

    def setUp(self):
        self.url = reverse("accounts:register")

    def test_register_individual(self):
        response = self.client.post(self.url, valid_data())
        self.assertRedirects(response, reverse("accounts:login"))
        user = User.objects.get(username="sara@example.com")
        self.assertEqual(user.profile.account_type, "individual")
        self.assertEqual(user.first_name, "سارة")

    def test_password_is_hashed_by_django(self):
        self.client.post(self.url, valid_data())
        user = User.objects.get(username="sara@example.com")
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_register_business_with_name(self):
        response = self.client.post(
            self.url, valid_data(account_type="business", business_name="شركة النور")
        )
        self.assertEqual(response.status_code, 302)
        profile = Profile.objects.get(user__username="sara@example.com")
        self.assertEqual(profile.account_type, "business")
        self.assertEqual(profile.business_name, "شركة النور")

    def test_business_without_name_is_rejected(self):
        response = self.client.post(self.url, valid_data(account_type="business", business_name=""))
        self.assertEqual(response.status_code, 200)
        self.assertIn("business_name", response.context["form"].errors)
        self.assertFalse(User.objects.exists())

    def test_business_with_blank_spaces_name_is_rejected(self):
        response = self.client.post(self.url, valid_data(account_type="business", business_name="   "))
        self.assertIn("business_name", response.context["form"].errors)
        self.assertFalse(User.objects.exists())

    def test_individual_business_name_is_ignored(self):
        self.client.post(self.url, valid_data(business_name="شيء ما"))
        self.assertEqual(Profile.objects.get().business_name, "")

    def test_account_type_is_required(self):
        data = valid_data()
        del data["account_type"]
        response = self.client.post(self.url, data)
        self.assertIn("account_type", response.context["form"].errors)

    def test_duplicate_email_rejected(self):
        make_user("sara@example.com")
        response = self.client.post(self.url, valid_data(email="SARA@example.com"))
        self.assertIn("email", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_password_mismatch_rejected(self):
        response = self.client.post(self.url, valid_data(password2="Different-Pass!999"))
        self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(User.objects.exists())

    def test_weak_password_rejected(self):
        response = self.client.post(self.url, valid_data(password1="12345678", password2="12345678"))
        self.assertIn("password1", response.context["form"].errors)

    def test_database_enforces_business_name(self):
        user = User.objects.create_user(username="y@example.com", password=PASSWORD)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Profile.objects.create(user=user, account_type="business", business_name="")

    def test_logged_in_user_is_redirected_away_from_register(self):
        self.client.force_login(make_user())
        self.assertRedirects(self.client.get(self.url), reverse("core:dashboard"))


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = make_user("login@example.com")
        self.url = reverse("accounts:login")

    def test_login_success_goes_to_dashboard(self):
        response = self.client.post(self.url, {"username": "login@example.com", "password": PASSWORD})
        self.assertRedirects(response, reverse("core:dashboard"))

    def test_login_is_case_insensitive_for_email(self):
        response = self.client.post(self.url, {"username": "LOGIN@Example.com", "password": PASSWORD})
        self.assertEqual(response.status_code, 302)

    def test_wrong_password_shows_error(self):
        response = self.client.post(self.url, {"username": "login@example.com", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "غير صحيحة")

    def test_session_ends_with_browser_when_remember_me_off(self):
        self.client.post(self.url, {"username": "login@example.com", "password": PASSWORD})
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_remember_me_keeps_long_session(self):
        self.client.post(self.url, {"username": "login@example.com", "password": PASSWORD, "remember_me": "on"})
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    def test_logout_requires_post_and_logs_out(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        response = self.client.post(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)


class LanguagePreferenceTests(TestCase):
    """The language button works for visitors and for signed-in users (saved in their account)."""

    def switch(self, language, next_url="/accounts/login/", client=None):
        return (client or self.client).post(
            reverse("accounts:save_language_preference"), {"language": language, "next": next_url}
        )

    def test_visitor_can_switch_language_on_the_login_page(self):
        response = self.switch("en")
        self.assertRedirects(response, "/accounts/login/", fetch_redirect_response=False)
        self.assertEqual(response.cookies["django_language"].value, "en")
        page = self.client.get(reverse("accounts:login"))
        self.assertContains(page, 'lang="en"')
        self.assertContains(page, 'dir="ltr"')

    def test_language_button_is_on_login_and_register_pages(self):
        url = reverse("accounts:save_language_preference")
        self.assertContains(self.client.get(reverse("accounts:login")), url)
        self.assertContains(self.client.get(reverse("accounts:register")), url)

    def test_choice_of_a_signed_in_user_is_saved_in_the_profile(self):
        user = make_user()
        self.client.force_login(user)
        self.switch("en", "/")
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.preferred_language, "en")
        self.switch("ar", "/")
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.preferred_language, "ar")

    def test_saved_language_follows_the_user_to_another_browser(self):
        user = make_user()
        user.profile.preferred_language = "en"
        user.profile.save()
        other_browser = self.client_class()
        other_browser.force_login(user)
        page = other_browser.get(reverse("core:dashboard"))
        self.assertContains(page, 'lang="en"')
        self.assertContains(page, "Dashboard")

    def test_login_applies_the_saved_language(self):
        user = make_user()
        user.profile.preferred_language = "en"
        user.profile.save()
        response = self.client.post(
            reverse("accounts:login"), {"username": user.email, "password": PASSWORD}, follow=True
        )
        self.assertContains(response, 'lang="en"')
        self.assertContains(response, "Welcome back to Hifaya!")

    def test_new_account_gets_the_language_used_to_register(self):
        self.switch("en", "/accounts/register/")
        self.client.post(reverse("accounts:register"), valid_data())
        profile = Profile.objects.get(user__username="sara@example.com")
        self.assertEqual(profile.preferred_language, "en")

    def test_default_language_is_arabic(self):
        self.assertEqual(make_user().profile.preferred_language, "ar")

    def test_invalid_language_is_ignored(self):
        user = make_user()
        self.client.force_login(user)
        response = self.switch("fr", "/")
        self.assertNotIn("django_language", response.cookies)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.preferred_language, "ar")

    def test_unsafe_next_url_goes_home(self):
        response = self.switch("en", "https://evil.example.com/")
        self.assertEqual(response["Location"], "/")

    def test_get_request_is_not_allowed(self):
        self.assertEqual(self.client.get(reverse("accounts:save_language_preference")).status_code, 405)
