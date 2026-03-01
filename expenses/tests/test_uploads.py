import json
from datetime import date

from django.test import TestCase

from expenses.models import Account, Currency, Period, Transaction, Upload
from expenses.utils.uploads import (
    get_defaults,
    get_field_indexes_account,
    get_field_indexes_credit_card,
    get_payment_date_and_period,
    get_transaction_money_account,
    get_transaction_money_credit_card,
    process_account_csv,
    process_credit_card_csv,
    set_message,
    skip_row_account,
    skip_row_credit_card,
    update_interval_date,
)

CREDIT_CARD_COLS = [
    {"payment_date": 1},
    {"description": 2},
    {"amount": 3},
    {"amount_currency": 4},
]

ACCOUNT_COLS = [
    {"payment_date": 1},
    {"description": 2},
    {"amount_debit": 3},
    {"amount_credit": 4},
]

CREDIT_CARD_INDEXES = {
    "payment_date": 1,
    "description": 2,
    "amount": 3,
    "amount_currency": 4,
}

ACCOUNT_INDEXES = {
    "payment_date": 1,
    "description": 2,
    "amount_debit": 3,
    "amount_credit": 4,
}


def make_credit_card_upload(data, rows_start=0, rows_end=None):
    if rows_end is None:
        rows_end = len(data) - 1
    return Upload.objects.create(
        data=data,
        parameters={
            "rows": {"start": rows_start, "end": rows_end},
            "cols": CREDIT_CARD_COLS,
        },
    )


def make_account_upload(data, rows_start=0, rows_end=None):
    if rows_end is None:
        rows_end = len(data) - 1
    return Upload.objects.create(
        data=data,
        parameters={
            "rows": {"start": rows_start, "end": rows_end},
            "cols": ACCOUNT_COLS,
        },
    )


class BaseUploadTestCase(TestCase):
    """Common DB objects required by get_defaults() and most tests."""

    @classmethod
    def setUpTestData(cls):
        cls.hnl = Currency.objects.create(alpha3="HNL", name="Lempira")
        cls.usd = Currency.objects.create(alpha3="USD", name="Dollar")
        cls.expense_account = Account.objects.create(name="__Gasto__", sign=Account.DEBE)
        cls.income_account = Account.objects.create(name="__Ingreso__", sign=Account.HABER)
        cls.open_period = Period.objects.create(month=1, year=2024, closed=False)
        cls.closed_period = Period.objects.create(month=2, year=2024, closed=True)
        cls.dec_2025 = Period.objects.create(month=12, year=2025, closed=False)


# ===========================================================================
# get_defaults
# ===========================================================================


class TestGetDefaults(TestCase):
    def test_raises_when_currency_missing(self):
        with self.assertRaisesMessage(ValueError, "Default currency not configured"):
            get_defaults()

    def test_raises_when_expense_account_missing(self):
        Currency.objects.create(alpha3="HNL", name="Lempira")
        Account.objects.create(name="__Ingreso__", sign=Account.HABER)
        with self.assertRaisesMessage(ValueError, "Default expense account not configured"):
            get_defaults()

    def test_raises_when_income_account_missing(self):
        Currency.objects.create(alpha3="HNL", name="Lempira")
        Account.objects.create(name="__Gasto__", sign=Account.DEBE)
        with self.assertRaisesMessage(ValueError, "Default income account not configured"):
            get_defaults()

    def test_returns_default_objects(self):
        Currency.objects.create(alpha3="HNL", name="Lempira")
        Account.objects.create(name="__Gasto__", sign=Account.DEBE)
        Account.objects.create(name="__Ingreso__", sign=Account.HABER)

        result = get_defaults()

        self.assertEqual(result["currency"].alpha3, "HNL")
        self.assertEqual(result["expense_account"].name, "__Gasto__")
        self.assertEqual(result["income_account"].name, "__Ingreso__")


# ===========================================================================
# get_field_indexes_credit_card / get_field_indexes_account
# ===========================================================================


class TestGetFieldIndexes(TestCase):
    def test_credit_card_returns_correct_indexes(self):
        result = get_field_indexes_credit_card(CREDIT_CARD_COLS)
        self.assertEqual(result, {"payment_date": 1, "description": 2, "amount": 3, "amount_currency": 4})

    def test_account_returns_correct_indexes(self):
        result = get_field_indexes_account(ACCOUNT_COLS)
        self.assertEqual(result, {"payment_date": 1, "description": 2, "amount_debit": 3, "amount_credit": 4})


# ===========================================================================
# skip_row_credit_card
# ===========================================================================


class TestSkipRowCreditCard(TestCase):
    def test_empty_row_is_skipped(self):
        self.assertTrue(skip_row_credit_card([], CREDIT_CARD_INDEXES))

    def test_skipped_when_payment_date_empty(self):
        self.assertTrue(skip_row_credit_card(["1", "", "WALMART", "100.00", ""], CREDIT_CARD_INDEXES))

    def test_skipped_when_both_amounts_empty(self):
        self.assertTrue(skip_row_credit_card(["1", "2024-01-15", "WALMART", "", ""], CREDIT_CARD_INDEXES))

    def test_not_skipped_when_amount_present(self):
        self.assertFalse(skip_row_credit_card(["1", "2024-01-15", "WALMART", "100.00", ""], CREDIT_CARD_INDEXES))

    def test_not_skipped_when_amount_currency_present(self):
        self.assertFalse(skip_row_credit_card(["1", "2024-01-15", "WALMART", "", "USD 14.00"], CREDIT_CARD_INDEXES))

    def test_not_skipped_when_amount_is_zero_string_and_currency_present(self):
        self.assertFalse(skip_row_credit_card(["1", "2024-01-15", "WALMART", "0.00", "USD 14.00"], CREDIT_CARD_INDEXES))

    def test_short_row_is_skipped(self):
        self.assertTrue(skip_row_credit_card(["1"], CREDIT_CARD_INDEXES))


# ===========================================================================
# skip_row_account
# ===========================================================================


class TestSkipRowAccount(TestCase):
    def test_empty_row_is_skipped(self):
        self.assertTrue(skip_row_account([], ACCOUNT_INDEXES))

    def test_skipped_when_payment_date_empty(self):
        self.assertTrue(skip_row_account(["1", "", "RENT", "5000.00", ""], ACCOUNT_INDEXES))

    def test_skipped_when_both_amounts_empty(self):
        self.assertTrue(skip_row_account(["1", "2024-01-15", "RENT", "", ""], ACCOUNT_INDEXES))

    def test_not_skipped_when_debit_present(self):
        self.assertFalse(skip_row_account(["1", "2024-01-15", "RENT", "5000.00", ""], ACCOUNT_INDEXES))

    def test_not_skipped_when_credit_present(self):
        self.assertFalse(skip_row_account(["1", "2024-01-15", "SALARY", "", "10000.00"], ACCOUNT_INDEXES))

    def test_short_row_is_skipped(self):
        self.assertTrue(skip_row_account(["1"], ACCOUNT_INDEXES))


# ===========================================================================
# get_payment_date_and_period
# ===========================================================================


class TestGetPaymentDateAndPeriod(BaseUploadTestCase):
    def test_returns_date_and_period(self):
        row = ["1", "2024-01-15", "WALMART", "100.00", ""]
        payment_date, period = get_payment_date_and_period(row, CREDIT_CARD_INDEXES)
        self.assertEqual(payment_date, date(2024, 1, 15))
        self.assertEqual(period, self.open_period)

    def test_returns_none_when_period_not_found(self):
        row = ["1", "2024-03-15", "WALMART", "100.00", ""]
        payment_date, period = get_payment_date_and_period(row, CREDIT_CARD_INDEXES)
        self.assertEqual(payment_date, date(2024, 3, 15))
        self.assertIsNone(period)

    def test_raises_on_invalid_date(self):
        row = ["1", "not-a-date", "WALMART", "100.00", ""]
        with self.assertRaisesMessage(ValueError, "Invalid date format"):
            get_payment_date_and_period(row, CREDIT_CARD_INDEXES)

    def test_parses_slash_date_format(self):
        row = ["1", "15/01/2024", "WALMART", "100.00", ""]
        payment_date, period = get_payment_date_and_period(row, CREDIT_CARD_INDEXES)
        self.assertEqual(payment_date, date(2024, 1, 15))
        self.assertEqual(period, self.open_period)


# ===========================================================================
# get_transaction_money_credit_card
# ===========================================================================


class TestGetTransactionMoneyCreditCard(BaseUploadTestCase):
    def test_amount_in_amount_field(self):
        row = ["1", "2024-01-15", "WALMART", "100.00", ""]
        amount, currency = get_transaction_money_credit_card(row, CREDIT_CARD_INDEXES, self.hnl)
        self.assertEqual(amount, 100.0)
        self.assertEqual(currency, self.hnl)

    def test_zero_amount_falls_back_to_amount_currency_field(self):
        # Real-world case: amount="0.00", amount_currency="USD 14.00"
        row = ["16", "29/12/2025", "PAYPAL *HELPCOURSER 8UCSO402935773 11:03", "0.00", "USD 14.00"]
        amount, currency = get_transaction_money_credit_card(row, CREDIT_CARD_INDEXES, self.hnl)
        self.assertEqual(amount, 14.0)
        self.assertEqual(currency, self.usd)

    def test_amount_with_currency_prefix(self):
        row = ["1", "2024-01-15", "AMAZON", "USD 50.00", ""]
        amount, currency = get_transaction_money_credit_card(row, CREDIT_CARD_INDEXES, self.hnl)
        self.assertEqual(amount, 50.0)
        self.assertEqual(currency, self.usd)

    def test_negative_amount(self):
        row = ["1", "2024-01-15", "REFUND", "-50.00", ""]
        amount, currency = get_transaction_money_credit_card(row, CREDIT_CARD_INDEXES, self.hnl)
        self.assertEqual(amount, -50.0)
        self.assertEqual(currency, self.hnl)

    def test_both_empty_returns_none(self):
        row = ["1", "2024-01-15", "WALMART", "", ""]
        amount, currency = get_transaction_money_credit_card(row, CREDIT_CARD_INDEXES, self.hnl)
        self.assertIsNone(amount)
        self.assertIsNone(currency)


# ===========================================================================
# get_transaction_money_account
# ===========================================================================


class TestGetTransactionMoneyAccount(BaseUploadTestCase):
    def test_debit_amount_with_default_currency(self):
        row = ["1", "2024-01-15", "RENT", "5000.00", ""]
        amount, currency, is_credit = get_transaction_money_account(row, ACCOUNT_INDEXES, self.hnl, self.hnl)
        self.assertEqual(amount, 5000.0)
        self.assertEqual(currency, self.hnl)
        self.assertFalse(is_credit)

    def test_credit_amount_with_default_currency(self):
        row = ["1", "2024-01-15", "SALARY", "", "10000.00"]
        amount, currency, is_credit = get_transaction_money_account(row, ACCOUNT_INDEXES, self.hnl, self.hnl)
        self.assertEqual(amount, 10000.0)
        self.assertEqual(currency, self.hnl)
        self.assertTrue(is_credit)

    def test_returns_max_when_both_present(self):
        row = ["1", "2024-01-15", "ENTRY", "200.00", "500.00"]
        amount, currency, is_credit = get_transaction_money_account(row, ACCOUNT_INDEXES, self.hnl, self.hnl)
        self.assertEqual(amount, 500.0)
        self.assertEqual(currency, self.hnl)
        self.assertTrue(is_credit)

    def test_debit_wins_when_both_present_and_larger(self):
        row = ["1", "2024-01-15", "ENTRY", "800.00", "500.00"]
        amount, currency, is_credit = get_transaction_money_account(row, ACCOUNT_INDEXES, self.hnl, self.hnl)
        self.assertEqual(amount, 800.0)
        self.assertFalse(is_credit)

    def test_non_default_currency_uses_get_amount_currency(self):
        row = ["1", "2024-01-15", "AMAZON", "50.00", ""]
        amount, currency, is_credit = get_transaction_money_account(row, ACCOUNT_INDEXES, self.usd, self.hnl)
        self.assertEqual(amount, 50.0)
        self.assertEqual(currency, self.usd)
        self.assertFalse(is_credit)

    def test_both_empty_returns_none(self):
        row = ["1", "2024-01-15", "EMPTY", "", ""]
        amount, currency, is_credit = get_transaction_money_account(row, ACCOUNT_INDEXES, self.hnl, self.hnl)
        self.assertIsNone(amount)
        self.assertIsNone(currency)
        self.assertIsNone(is_credit)


# ===========================================================================
# set_message
# ===========================================================================


class TestSetMessage(TestCase):
    def test_adds_entry_to_result(self):
        data = {"result": {}}
        set_message(data=data, line_number="1", source=["row"], description="CREATED")
        self.assertEqual(data["result"]["1"], {"source": "['row']", "description": "CREATED"})

    def test_overwrites_existing_entry(self):
        data = {"result": {"1": {"source": "old", "description": "old"}}}
        set_message(data=data, line_number="1", source=["new"], description="UPDATED")
        self.assertEqual(data["result"]["1"]["description"], "UPDATED")


# ===========================================================================
# update_interval_date
# ===========================================================================


class TestUpdateIntervalDate(BaseUploadTestCase):
    def test_sets_dates_from_transactions(self):
        upload = make_credit_card_upload([])
        Transaction.objects.create(
            period=self.open_period,
            account=self.expense_account,
            currency=self.hnl,
            amount=100,
            payment_date=date(2024, 1, 10),
            upload=upload,
        )
        Transaction.objects.create(
            period=self.open_period,
            account=self.expense_account,
            currency=self.hnl,
            amount=200,
            payment_date=date(2024, 1, 20),
            upload=upload,
        )

        update_interval_date(upload)

        upload.refresh_from_db()
        self.assertEqual(upload.start_date, date(2024, 1, 10))
        self.assertEqual(upload.end_date, date(2024, 1, 20))

    def test_no_update_when_no_transactions(self):
        upload = make_credit_card_upload([])
        upload.refresh_from_db()  # normalize to date (not datetime from default=timezone.now)
        original_start = upload.start_date

        update_interval_date(upload)

        upload.refresh_from_db()
        self.assertEqual(upload.start_date, original_start)


# ===========================================================================
# process_credit_card_csv
# ===========================================================================


class TestProcessCreditCardCsv(BaseUploadTestCase):
    # Row layout: [line_number, payment_date, description, amount, amount_currency]

    def test_creates_transaction(self):
        data = [["1", "2024-01-15", "WALMART", "100.00", ""]]
        upload = make_credit_card_upload(data)

        process_credit_card_csv(upload)

        self.assertEqual(Transaction.objects.count(), 1)
        t = Transaction.objects.first()
        self.assertEqual(t.description, "WALMART")
        self.assertEqual(float(t.amount), 100.00)
        self.assertEqual(t.payment_date, date(2024, 1, 15))

    def test_amount_currency_column_used_when_amount_is_zero(self):
        # Real-world case: amount=0.00, amount_currency="USD 14.00"
        data = [["16", "29/12/2025", "PAYPAL *HELPCOURSER 8UCSO402935773 11:03", "0.00", "USD 14.00"]]
        upload = make_credit_card_upload(data)

        process_credit_card_csv(upload)

        self.assertEqual(Transaction.objects.count(), 1)
        t = Transaction.objects.first()
        self.assertEqual(float(t.amount), 14.00)
        self.assertEqual(t.currency, self.usd)

    def test_summary_created_count(self):
        data = [
            ["1", "2024-01-15", "WALMART", "100.00", ""],
            ["2", "2024-01-16", "NETFLIX", "15.00", ""],
        ]
        upload = make_credit_card_upload(data)

        process_credit_card_csv(upload)

        result = json.loads(upload.result)
        self.assertEqual(result["summary"]["created"], 2)

    def test_positive_amount_uses_expense_account(self):
        data = [["1", "2024-01-15", "WALMART", "100.00", ""]]
        upload = make_credit_card_upload(data)

        process_credit_card_csv(upload)

        self.assertEqual(Transaction.objects.first().account, self.expense_account)

    def test_negative_amount_uses_income_account(self):
        data = [["1", "2024-01-15", "REFUND", "-50.00", ""]]
        upload = make_credit_card_upload(data)

        process_credit_card_csv(upload)

        t = Transaction.objects.first()
        self.assertEqual(t.account, self.income_account)
        self.assertEqual(float(t.amount), 50.00)

    def test_skips_row_with_no_payment_date(self):
        data = [["1", "", "WALMART", "100.00", ""]]
        upload = make_credit_card_upload(data)

        process_credit_card_csv(upload)

        self.assertEqual(Transaction.objects.count(), 0)

    def test_skips_row_with_no_amounts(self):
        data = [["1", "2024-01-15", "WALMART", "", ""]]
        upload = make_credit_card_upload(data)

        process_credit_card_csv(upload)

        self.assertEqual(Transaction.objects.count(), 0)

    def test_skips_when_period_not_found(self):
        data = [["1", "2024-03-15", "WALMART", "100.00", ""]]
        upload = make_credit_card_upload(data)

        process_credit_card_csv(upload)

        self.assertEqual(Transaction.objects.count(), 0)
        result = json.loads(upload.result)
        self.assertEqual(result["result"]["1"]["description"], "Period not found or closed")

    def test_skips_when_period_closed(self):
        data = [["1", "2024-02-15", "WALMART", "100.00", ""]]
        upload = make_credit_card_upload(data)

        process_credit_card_csv(upload)

        self.assertEqual(Transaction.objects.count(), 0)
        result = json.loads(upload.result)
        self.assertEqual(result["result"]["1"]["description"], "Period not found or closed")

    def test_skips_duplicate_by_hash(self):
        data = [["1", "2024-01-15", "WALMART", "100.00", ""]]
        upload1 = make_credit_card_upload(data)
        process_credit_card_csv(upload1)

        upload2 = make_credit_card_upload(data)
        process_credit_card_csv(upload2)

        self.assertEqual(Transaction.objects.count(), 1)
        result = json.loads(upload2.result)
        self.assertEqual(result["summary"]["created"], 0)

    def test_upload_dates_set_after_processing(self):
        data = [
            ["1", "2024-01-10", "STORE A", "100.00", ""],
            ["2", "2024-01-20", "STORE B", "200.00", ""],
        ]
        upload = make_credit_card_upload(data)

        process_credit_card_csv(upload)

        upload.refresh_from_db()
        self.assertEqual(upload.start_date, date(2024, 1, 10))
        self.assertEqual(upload.end_date, date(2024, 1, 20))

    def test_amount_with_currency_prefix_creates_usd_transaction(self):
        data = [["1", "2024-01-15", "AMAZON", "USD 50.00", ""]]
        upload = make_credit_card_upload(data)

        process_credit_card_csv(upload)

        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(Transaction.objects.first().currency, self.usd)


# ===========================================================================
# process_account_csv
# ===========================================================================


class TestProcessAccountCsv(BaseUploadTestCase):
    # Row layout: [line_number, payment_date, description, amount_debit, amount_credit]

    def test_creates_transaction_from_debit(self):
        data = [["1", "2024-01-15", "RENT", "5000.00", ""]]
        upload = make_account_upload(data)

        process_account_csv(upload, self.hnl)

        self.assertEqual(Transaction.objects.count(), 1)
        t = Transaction.objects.first()
        self.assertEqual(t.description, "RENT")
        self.assertEqual(float(t.amount), 5000.00)

    def test_creates_transaction_from_credit(self):
        data = [["1", "2024-01-15", "SALARY", "", "10000.00"]]
        upload = make_account_upload(data)

        process_account_csv(upload, self.hnl)

        self.assertEqual(Transaction.objects.count(), 1)
        t = Transaction.objects.first()
        self.assertEqual(t.description, "SALARY")
        self.assertEqual(float(t.amount), 10000.00)

    def test_summary_created_count(self):
        data = [
            ["1", "2024-01-15", "RENT", "5000.00", ""],
            ["2", "2024-01-20", "UTILITIES", "800.00", ""],
        ]
        upload = make_account_upload(data)

        process_account_csv(upload, self.hnl)

        result = json.loads(upload.result)
        self.assertEqual(result["summary"]["created"], 2)

    def test_skips_row_with_no_payment_date(self):
        data = [["1", "", "RENT", "5000.00", ""]]
        upload = make_account_upload(data)

        process_account_csv(upload, self.hnl)

        self.assertEqual(Transaction.objects.count(), 0)

    def test_skips_row_with_no_amounts(self):
        data = [["1", "2024-01-15", "RENT", "", ""]]
        upload = make_account_upload(data)

        process_account_csv(upload, self.hnl)

        self.assertEqual(Transaction.objects.count(), 0)

    def test_skips_when_period_not_found(self):
        data = [["1", "2024-03-15", "RENT", "5000.00", ""]]
        upload = make_account_upload(data)

        process_account_csv(upload, self.hnl)

        self.assertEqual(Transaction.objects.count(), 0)
        result = json.loads(upload.result)
        self.assertEqual(result["result"]["1"]["description"], "Period not found or closed")

    def test_skips_when_period_closed(self):
        data = [["1", "2024-02-15", "RENT", "5000.00", ""]]
        upload = make_account_upload(data)

        process_account_csv(upload, self.hnl)

        self.assertEqual(Transaction.objects.count(), 0)
        result = json.loads(upload.result)
        self.assertEqual(result["result"]["1"]["description"], "Period not found or closed")

    def test_skips_duplicate_by_hash(self):
        data = [["1", "2024-01-15", "RENT", "5000.00", ""]]
        upload1 = make_account_upload(data)
        process_account_csv(upload1, self.hnl)

        upload2 = make_account_upload(data)
        process_account_csv(upload2, self.hnl)

        self.assertEqual(Transaction.objects.count(), 1)
        result = json.loads(upload2.result)
        self.assertEqual(result["summary"]["created"], 0)

    def test_usd_currency_creates_usd_transaction(self):
        data = [["1", "2024-01-15", "AMAZON", "50.00", ""]]
        upload = make_account_upload(data)

        process_account_csv(upload, self.usd)

        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(Transaction.objects.first().currency, self.usd)

    def test_debit_amount_uses_expense_account(self):
        data = [["1", "2024-01-15", "RENT", "5000.00", ""]]
        upload = make_account_upload(data)

        process_account_csv(upload, self.hnl)

        self.assertEqual(Transaction.objects.first().account, self.expense_account)

    def test_credit_amount_uses_income_account(self):
        # Real-world case: debit=0.00, credit=2187.00 — should be income
        data = [["13", "2024-01-15", "SALARY", "0.00", "2187.00"]]
        upload = make_account_upload(data)

        process_account_csv(upload, self.hnl)

        t = Transaction.objects.first()
        self.assertEqual(t.account, self.income_account)
        self.assertEqual(float(t.amount), 2187.0)

    def test_usd_credit_amount_uses_income_account(self):
        # Mirrors the reported row: debit='USD 0.00', credit='USD 2187.00'
        ACCOUNT_COLS_USD = [
            {"payment_date": 1},
            {"description": 4},
            {"amount_debit": 5},
            {"amount_credit": 6},
        ]
        data = [["13", "2024-01-15", "566379", "WC", "BAX BIBLIOTECA ACAD", "USD 0.00", "USD 2187.00", "3079.66"]]
        upload = Upload.objects.create(
            data=data,
            parameters={"rows": {"start": 0, "end": 0}, "cols": ACCOUNT_COLS_USD},
        )

        process_account_csv(upload, self.usd)

        t = Transaction.objects.first()
        self.assertEqual(t.account, self.income_account)
        self.assertEqual(float(t.amount), 2187.0)
        self.assertEqual(t.currency, self.usd)
