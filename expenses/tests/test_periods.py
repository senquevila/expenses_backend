from decimal import Decimal

from django.conf import settings
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
        self.assertEqual(response.json()["total"], 150.00)

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


class TestPeriodSummaryEndpoint(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.currency = Currency.objects.create(alpha3="HNL", name="Lempira")
        cls.food = Account.objects.create(name="Food", sign=Account.HABER)
        cls.transport = Account.objects.create(name="Transport", sign=Account.HABER)

    def setUp(self):
        self.period = Period.objects.create(month=3, year=2026, closed=False)

    def _summary_url(self):
        return reverse("api-periods-summary", kwargs={"pk": self.period.pk})

    def _make_transaction(self, account, amount):
        return Transaction.objects.create(
            period=self.period,
            account=account,
            currency=self.currency,
            amount=amount,
        )

    def test_returns_200(self):
        response = self.client.get(self._summary_url())
        self.assertEqual(response.status_code, 200)

    def test_empty_period_returns_empty_list(self):
        response = self.client.get(self._summary_url())
        self.assertEqual(response.json(), [])

    def test_sums_transactions_by_account(self):
        self._make_transaction(self.food, Decimal("100.00"))
        self._make_transaction(self.food, Decimal("50.00"))
        self._make_transaction(self.transport, Decimal("30.00"))
        response = self.client.get(self._summary_url())
        data = {row["account_id"]: row for row in response.json()}
        self.assertEqual(Decimal(data[self.food.pk]["total"]["value"]), Decimal("150.00"))
        self.assertEqual(Decimal(data[self.transport.pk]["total"]["value"]), Decimal("30.00"))

    def test_response_includes_expected_fields(self):
        self._make_transaction(self.food, Decimal("100.00"))
        response = self.client.get(self._summary_url())
        row = response.json()[0]
        self.assertIn("account_id", row)
        self.assertIn("account_name", row)
        self.assertIn("total", row)
        self.assertIn("value", row["total"])
        self.assertIn("currency", row["total"])

    def test_total_currency_is_default(self):
        self._make_transaction(self.food, Decimal("100.00"))
        response = self.client.get(self._summary_url())
        self.assertEqual(response.json()[0]["total"]["currency"], settings.DEFAULT_CURRENCY)

    def test_results_ordered_by_account_name(self):
        self._make_transaction(self.transport, Decimal("10.00"))
        self._make_transaction(self.food, Decimal("20.00"))
        response = self.client.get(self._summary_url())
        names = [row["account_name"] for row in response.json()]
        self.assertEqual(names, sorted(names))

    def test_only_includes_accounts_with_transactions(self):
        self._make_transaction(self.food, Decimal("100.00"))
        response = self.client.get(self._summary_url())
        account_ids = [row["account_id"] for row in response.json()]
        self.assertIn(self.food.pk, account_ids)
        self.assertNotIn(self.transport.pk, account_ids)
