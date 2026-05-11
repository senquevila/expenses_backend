from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from expenses.models import Account, Currency, Period, Transaction
from expenses.services.periods import calculate_period_total


class TestCalculatePeriodTotal(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.period = Period.objects.create(month=1, year=2026, closed=False)
        cls.currency = Currency.objects.create(alpha3="HNL", name="Lempira")
        cls.account = Account.objects.create(name="Food", sign=Account.HABER)

    def _make_transaction(self, amount):
        return Transaction.objects.create(
            period=self.period,
            account=self.account,
            currency=self.currency,
            amount=amount,
        )

    def test_total_is_sum_of_local_amounts(self):
        self._make_transaction(Decimal("100.00"))
        self._make_transaction(Decimal("250.50"))
        calculate_period_total(self.period)
        self.assertEqual(self.period.total, Decimal("350.50"))

    def test_total_is_persisted_to_database(self):
        self._make_transaction(Decimal("200.00"))
        calculate_period_total(self.period)
        refreshed = Period.objects.get(pk=self.period.pk)
        self.assertEqual(refreshed.total, Decimal("200.00"))

    def test_empty_period_total_is_zero(self):
        calculate_period_total(self.period)
        self.assertEqual(self.period.total, Decimal("0"))

    def test_updates_period_instance_total(self):
        self._make_transaction(Decimal("75.00"))
        calculate_period_total(self.period)
        self.assertEqual(self.period.total, Decimal("75.00"))


class TestPeriodToggleEndpoint(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.currency = Currency.objects.create(alpha3="HNL", name="Lempira")
        cls.account = Account.objects.create(name="Food", sign=Account.HABER)

    def setUp(self):
        self.period = Period.objects.create(month=2, year=2026, closed=False)

    def _toggle_url(self):
        return reverse("api-periods-toggle", kwargs={"pk": self.period.pk})

    def _make_transaction(self, amount):
        return Transaction.objects.create(
            period=self.period,
            account=self.account,
            currency=self.currency,
            amount=amount,
        )

    def test_closing_period_returns_correct_total(self):
        self._make_transaction(Decimal("100.00"))
        self._make_transaction(Decimal("50.00"))
        response = self.client.post(self._toggle_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 150)

    def test_closing_period_response_structure(self):
        response = self.client.post(self._toggle_url())
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("closed", data)
        self.assertIn("total", data)
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["closed"])

    def test_closing_period_with_no_transactions_total_is_zero(self):
        response = self.client.post(self._toggle_url())
        self.assertEqual(response.json()["total"], 0)

    def test_closing_period_persists_total_to_database(self):
        self._make_transaction(Decimal("300.00"))
        self.client.post(self._toggle_url())
        self.period.refresh_from_db()
        self.assertEqual(self.period.total, Decimal("300.00"))

    def test_reopening_period_resets_total_to_zero_in_response(self):
        self._make_transaction(Decimal("100.00"))
        self.client.post(self._toggle_url())
        response = self.client.post(self._toggle_url())
        self.assertEqual(response.json()["total"], 0)
        self.assertFalse(response.json()["closed"])

    def test_reopening_period_persists_zero_total_to_database(self):
        self._make_transaction(Decimal("100.00"))
        self.client.post(self._toggle_url())
        self.client.post(self._toggle_url())
        self.period.refresh_from_db()
        self.assertEqual(self.period.total, Decimal("0"))
