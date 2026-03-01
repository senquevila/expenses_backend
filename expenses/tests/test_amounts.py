from django.test import TestCase

from expenses.models import Currency
from expenses.utils.uploads import get_amount


class TestGetAmount(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hnl = Currency.objects.create(alpha3="HNL", name="Lempira")
        Currency.objects.create(alpha3="USD", name="Dollars")

    def test_plain_number_uses_default_currency(self):
        amount, currency = get_amount(["100"], 0, self.hnl)
        self.assertEqual(amount, 100.0)
        self.assertEqual(currency.alpha3, "HNL")

    def test_hnl_prefix_uses_hnl_currency(self):
        amount, currency = get_amount(["HNL 100"], 0, self.hnl)
        self.assertEqual(amount, 100.0)
        self.assertEqual(currency.alpha3, "HNL")

    def test_hnl_suffix_uses_hnl_currency(self):
        amount, currency = get_amount(["100 HNL"], 0, self.hnl)
        self.assertEqual(amount, 100.0)
        self.assertEqual(currency.alpha3, "HNL")

    def test_usd_prefix(self):
        amount, currency = get_amount(["USD 100"], 0, self.hnl)
        self.assertEqual(amount, 100.0)
        self.assertEqual(currency.alpha3, "USD")

    def test_usd_suffix(self):
        amount, currency = get_amount(["100 USD"], 0, self.hnl)
        self.assertEqual(amount, 100.0)
        self.assertEqual(currency.alpha3, "USD")

    def test_invalid_index_returns_none(self):
        amount, currency = get_amount(["100 ABC"], -1, self.hnl)
        self.assertIsNone(amount)
        self.assertIsNone(currency)

    def test_empty_row_returns_none(self):
        amount, currency = get_amount([], 0, self.hnl)
        self.assertIsNone(amount)
        self.assertIsNone(currency)

    def test_empty_string_returns_none(self):
        amount, currency = get_amount([""], 0, self.hnl)
        self.assertIsNone(amount)
        self.assertIsNone(currency)

    def test_negative_usd_amount(self):
        amount, currency = get_amount(["USD -1.99"], 0, self.hnl)
        self.assertEqual(amount, -1.99)
        self.assertEqual(currency.alpha3, "USD")
