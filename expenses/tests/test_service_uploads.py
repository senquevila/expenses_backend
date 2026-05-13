from datetime import date

from django.test import TestCase

from expenses.models import Account, AccountAssociation, Currency, Period, Transaction, Upload
from expenses.services.uploads import (
    _detect_type_from_structure,
    _get_defaults,
    _make_identifier,
    _parse_amount_field,
    _parse_credit_card_row,
    _parse_savings_account_row,
    _update_interval_dates,
    process_upload_result,
)


def cc_row(row_number, date_str, description, local_amount="", local_currency="HNL", usd_amount="", usd_currency="USD"):
    return {
        "row_number": row_number,
        "date": date_str,
        "description": description,
        "local": {"amount": local_amount, "currency": local_currency},
        "usd": {"amount": usd_amount, "currency": usd_currency},
    }


def sa_row(
    row_number, date_str, description, debit_amount="", debit_currency="HNL", credit_amount="", credit_currency="HNL"
):
    return {
        "row_number": row_number,
        "date": date_str,
        "description": description,
        "debit": {"amount": debit_amount, "currency": debit_currency},
        "credit": {"amount": credit_amount, "currency": credit_currency},
    }


class BaseServiceTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hnl = Currency.objects.create(alpha3="HNL", name="Lempira")
        cls.usd = Currency.objects.create(alpha3="USD", name="Dollar")
        cls.expense_account = Account.objects.create(name="__Gasto__", sign=Account.DEBE)
        cls.income_account = Account.objects.create(name="__Ingreso__", sign=Account.HABER)
        cls.open_period = Period.objects.create(month=1, year=2024, closed=False)
        cls.closed_period = Period.objects.create(month=2, year=2024, closed=True)


# ===========================================================================
# _detect_type_from_structure
# ===========================================================================


class TestDetectTypeFromStructure(TestCase):
    def test_detects_credit_card(self):
        row = {"local": {}, "usd": {}, "description": "X"}
        self.assertEqual(_detect_type_from_structure(row), Upload.UploadType.CREDIT_CARD)

    def test_detects_savings_account(self):
        row = {"debit": {}, "credit": {}, "description": "X"}
        self.assertEqual(_detect_type_from_structure(row), Upload.UploadType.SAVINGS_ACCOUNT)

    def test_returns_none_for_unknown_structure(self):
        row = {"amount": "100", "description": "X"}
        self.assertIsNone(_detect_type_from_structure(row))

    def test_returns_none_for_empty_row(self):
        self.assertIsNone(_detect_type_from_structure({}))


# ===========================================================================
# _get_defaults
# ===========================================================================


class TestGetDefaults(TestCase):
    def test_raises_when_currency_missing(self):
        with self.assertRaisesMessage(ValueError, "Default currency not configured"):
            _get_defaults()

    def test_raises_when_expense_account_missing(self):
        Currency.objects.create(alpha3="HNL", name="Lempira")
        Account.objects.create(name="__Ingreso__", sign=Account.HABER)
        with self.assertRaisesMessage(ValueError, "Default expense account not configured"):
            _get_defaults()

    def test_raises_when_income_account_missing(self):
        Currency.objects.create(alpha3="HNL", name="Lempira")
        Account.objects.create(name="__Gasto__", sign=Account.DEBE)
        with self.assertRaisesMessage(ValueError, "Default income account not configured"):
            _get_defaults()

    def test_returns_all_defaults(self):
        Currency.objects.create(alpha3="HNL", name="Lempira")
        Account.objects.create(name="__Gasto__", sign=Account.DEBE)
        Account.objects.create(name="__Ingreso__", sign=Account.HABER)

        result = _get_defaults()

        self.assertEqual(result["currency"].alpha3, "HNL")
        self.assertEqual(result["expense_account"].name, "__Gasto__")
        self.assertEqual(result["income_account"].name, "__Ingreso__")


# ===========================================================================
# _make_identifier
# ===========================================================================


class TestMakeIdentifier(TestCase):
    def test_returns_sha256_hex_string(self):
        row = cc_row(1, "2024-01-15", "WALMART", local_amount="100.00")
        result = _make_identifier(row)
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 64)

    def test_same_row_gives_same_identifier(self):
        row = cc_row(1, "2024-01-15", "WALMART", local_amount="100.00")
        self.assertEqual(_make_identifier(row), _make_identifier(row))

    def test_different_amounts_give_different_identifiers(self):
        row1 = cc_row(1, "2024-01-15", "WALMART", local_amount="100.00")
        row2 = cc_row(1, "2024-01-15", "WALMART", local_amount="200.00")
        self.assertNotEqual(_make_identifier(row1), _make_identifier(row2))

    def test_savings_account_row_identifier(self):
        row = sa_row(1, "2024-01-15", "RENT", debit_amount="5000.00")
        result = _make_identifier(row)
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 64)

    def test_different_descriptions_give_different_identifiers(self):
        row1 = cc_row(1, "2024-01-15", "WALMART", local_amount="100.00")
        row2 = cc_row(1, "2024-01-15", "AMAZON", local_amount="100.00")
        self.assertNotEqual(_make_identifier(row1), _make_identifier(row2))


# ===========================================================================
# _parse_amount_field
# ===========================================================================


class TestParseAmountField(BaseServiceTestCase):
    def test_empty_amount_returns_none(self):
        amount, currency = _parse_amount_field({"amount": "", "currency": "HNL"}, self.hnl)
        self.assertIsNone(amount)
        self.assertIsNone(currency)

    def test_missing_amount_key_returns_none(self):
        amount, currency = _parse_amount_field({}, self.hnl)
        self.assertIsNone(amount)
        self.assertIsNone(currency)

    def test_valid_amount_returns_float_and_default_currency(self):
        amount, currency = _parse_amount_field({"amount": "100.00", "currency": ""}, self.hnl)
        self.assertEqual(amount, 100.0)
        self.assertEqual(currency, self.hnl)

    def test_valid_amount_with_known_currency_overrides_default(self):
        amount, currency = _parse_amount_field({"amount": "50.00", "currency": "USD"}, self.hnl)
        self.assertEqual(amount, 50.0)
        self.assertEqual(currency, self.usd)

    def test_amount_with_commas_is_parsed(self):
        amount, currency = _parse_amount_field({"amount": "1,500.00", "currency": ""}, self.hnl)
        self.assertEqual(amount, 1500.0)

    def test_zero_amount_returns_none(self):
        amount, currency = _parse_amount_field({"amount": "0.00", "currency": "HNL"}, self.hnl)
        self.assertIsNone(amount)
        self.assertIsNone(currency)

    def test_invalid_amount_string_returns_none(self):
        amount, currency = _parse_amount_field({"amount": "not-a-number", "currency": "HNL"}, self.hnl)
        self.assertIsNone(amount)
        self.assertIsNone(currency)

    def test_negative_amount_is_preserved(self):
        amount, currency = _parse_amount_field({"amount": "-75.50", "currency": ""}, self.hnl)
        self.assertEqual(amount, -75.5)

    def test_amount_with_currency_prefix_is_parsed(self):
        amount, currency = _parse_amount_field({"amount": "L17.23", "currency": "HNL"}, self.hnl)
        self.assertEqual(amount, 17.23)

    def test_amount_with_currency_prefix_and_commas_is_parsed(self):
        amount, currency = _parse_amount_field({"amount": "L10,342.64", "currency": "HNL"}, self.hnl)
        self.assertEqual(amount, 10342.64)

    def test_amount_with_dollar_prefix_is_parsed(self):
        amount, currency = _parse_amount_field({"amount": "$9,853.61", "currency": "USD"}, self.usd)
        self.assertEqual(amount, 9853.61)

    def test_amount_with_currency_suffix_is_parsed(self):
        amount, currency = _parse_amount_field({"amount": "17.23L", "currency": "HNL"}, self.hnl)
        self.assertEqual(amount, 17.23)

    def test_amount_with_suffix_and_commas_is_parsed(self):
        amount, currency = _parse_amount_field({"amount": "10,342.64HNL", "currency": "HNL"}, self.hnl)
        self.assertEqual(amount, 10342.64)


# ===========================================================================
# _parse_credit_card_row
# ===========================================================================


class TestParseCreditCardRow(BaseServiceTestCase):
    def test_uses_local_amount_when_present(self):
        row = cc_row(1, "2024-01-15", "WALMART", local_amount="100.00")
        amount, currency, is_income = _parse_credit_card_row(row, self.hnl)
        self.assertEqual(amount, 100.0)
        self.assertEqual(currency, self.hnl)
        self.assertFalse(is_income)

    def test_falls_back_to_usd_when_local_empty(self):
        row = cc_row(1, "2024-01-15", "PAYPAL", local_amount="0.00", usd_amount="14.00", usd_currency="USD")
        amount, currency, is_income = _parse_credit_card_row(row, self.hnl)
        self.assertEqual(amount, 14.0)
        self.assertEqual(currency, self.usd)
        self.assertFalse(is_income)

    def test_negative_local_amount_is_income(self):
        row = cc_row(1, "2024-01-15", "REFUND", local_amount="-50.00")
        amount, currency, is_income = _parse_credit_card_row(row, self.hnl)
        self.assertEqual(amount, -50.0)
        self.assertTrue(is_income)

    def test_both_empty_returns_none(self):
        row = cc_row(1, "2024-01-15", "X")
        amount, currency, is_income = _parse_credit_card_row(row, self.hnl)
        self.assertIsNone(amount)
        self.assertIsNone(currency)
        self.assertFalse(is_income)

    def test_usd_currency_resolved_from_local_field(self):
        row = cc_row(1, "2024-01-15", "AMAZON", local_amount="50.00", local_currency="USD")
        amount, currency, is_income = _parse_credit_card_row(row, self.hnl)
        self.assertEqual(currency, self.usd)


# ===========================================================================
# _parse_savings_account_row
# ===========================================================================


class TestParseSavingsAccountRow(BaseServiceTestCase):
    def test_credit_is_income(self):
        row = sa_row(1, "2024-01-15", "SALARY", credit_amount="10000.00")
        amount, currency, is_income = _parse_savings_account_row(row, self.hnl)
        self.assertEqual(amount, 10000.0)
        self.assertEqual(currency, self.hnl)
        self.assertTrue(is_income)

    def test_debit_is_expense(self):
        row = sa_row(1, "2024-01-15", "RENT", debit_amount="5000.00")
        amount, currency, is_income = _parse_savings_account_row(row, self.hnl)
        self.assertEqual(amount, 5000.0)
        self.assertEqual(currency, self.hnl)
        self.assertFalse(is_income)

    def test_credit_takes_precedence_over_debit(self):
        row = sa_row(1, "2024-01-15", "ENTRY", debit_amount="100.00", credit_amount="200.00")
        amount, currency, is_income = _parse_savings_account_row(row, self.hnl)
        self.assertEqual(amount, 200.0)
        self.assertTrue(is_income)

    def test_both_empty_returns_none(self):
        row = sa_row(1, "2024-01-15", "X")
        amount, currency, is_income = _parse_savings_account_row(row, self.hnl)
        self.assertIsNone(amount)
        self.assertIsNone(currency)
        self.assertFalse(is_income)

    def test_usd_credit_uses_usd_currency(self):
        row = sa_row(1, "2024-01-15", "WIRE", credit_amount="2187.00", credit_currency="USD")
        amount, currency, is_income = _parse_savings_account_row(row, self.hnl)
        self.assertEqual(currency, self.usd)
        self.assertTrue(is_income)


# ===========================================================================
# _update_interval_dates
# ===========================================================================


class TestUpdateIntervalDates(BaseServiceTestCase):
    def test_sets_min_and_max_dates_from_rows(self):
        upload = Upload.objects.create(upload_type=Upload.UploadType.CREDIT_CARD)
        rows = [
            cc_row(1, "2024-01-20", "STORE B", local_amount="200.00"),
            cc_row(2, "2024-01-05", "STORE A", local_amount="100.00"),
        ]

        _update_interval_dates(upload, rows)

        upload.refresh_from_db()
        self.assertEqual(upload.start_date, date(2024, 1, 5))
        self.assertEqual(upload.end_date, date(2024, 1, 20))

    def test_skips_rows_with_invalid_dates(self):
        upload = Upload.objects.create(upload_type=Upload.UploadType.CREDIT_CARD)
        rows = [
            cc_row(1, "2024-01-15", "VALID", local_amount="100.00"),
            cc_row(2, "not-a-date", "INVALID", local_amount="50.00"),
        ]

        _update_interval_dates(upload, rows)

        upload.refresh_from_db()
        self.assertEqual(upload.start_date, date(2024, 1, 15))
        self.assertEqual(upload.end_date, date(2024, 1, 15))

    def test_no_update_when_all_dates_invalid(self):
        sentinel = date(2023, 6, 1)
        upload = Upload.objects.create(upload_type=Upload.UploadType.CREDIT_CARD, start_date=sentinel)
        rows = [cc_row(1, "bad-date", "X", local_amount="100.00")]

        _update_interval_dates(upload, rows)

        upload.refresh_from_db()
        self.assertEqual(upload.start_date, sentinel)


# ===========================================================================
# process_upload_result
# ===========================================================================


class TestProcessUploadResult(BaseServiceTestCase):
    def _make_cc_upload(self, rows, upload_type=Upload.UploadType.CREDIT_CARD):
        return Upload.objects.create(result=rows, upload_type=upload_type)

    def _make_sa_upload(self, rows, upload_type=Upload.UploadType.SAVINGS_ACCOUNT):
        return Upload.objects.create(result=rows, upload_type=upload_type)

    # --- Early failure paths ---

    def test_fails_when_result_is_none(self):
        upload = Upload.objects.create(result=None, upload_type=Upload.UploadType.CREDIT_CARD)
        process_upload_result(upload)
        upload.refresh_from_db()
        self.assertEqual(upload.upload_status, Upload.UploadStatus.FAILED)
        self.assertEqual(upload.fails[0]["error"], "No result data to process")

    def test_fails_when_result_is_empty_list(self):
        upload = Upload.objects.create(result=[], upload_type=Upload.UploadType.CREDIT_CARD)
        process_upload_result(upload)
        upload.refresh_from_db()
        self.assertEqual(upload.upload_status, Upload.UploadStatus.FAILED)

    def test_fails_when_upload_type_not_set(self):
        upload = Upload.objects.create(result=[cc_row(1, "2024-01-15", "X", local_amount="100.00")], upload_type=None)
        process_upload_result(upload)
        upload.refresh_from_db()
        self.assertEqual(upload.upload_status, Upload.UploadStatus.FAILED)
        self.assertEqual(upload.fails[0]["error"], "upload_type is not set")

    def test_fails_when_type_does_not_match_structure(self):
        rows = [cc_row(1, "2024-01-15", "X", local_amount="100.00")]
        upload = Upload.objects.create(result=rows, upload_type=Upload.UploadType.SAVINGS_ACCOUNT)
        process_upload_result(upload)
        upload.refresh_from_db()
        self.assertEqual(upload.upload_status, Upload.UploadStatus.FAILED)
        self.assertIn("does not match", upload.fails[0]["error"])

    # --- Successful credit card processing ---

    def test_creates_credit_card_transaction(self):
        rows = [cc_row(1, "2024-01-15", "WALMART", local_amount="100.00")]
        upload = self._make_cc_upload(rows)

        process_upload_result(upload)

        self.assertEqual(Transaction.objects.count(), 1)
        t = Transaction.objects.first()
        self.assertEqual(t.description, "WALMART")
        self.assertEqual(float(t.amount), 100.0)
        self.assertEqual(t.payment_date, date(2024, 1, 15))
        self.assertEqual(t.currency, self.hnl)
        self.assertEqual(t.account, self.expense_account)

    def test_credit_card_negative_amount_uses_income_account(self):
        rows = [cc_row(1, "2024-01-15", "REFUND", local_amount="-50.00")]
        upload = self._make_cc_upload(rows)

        process_upload_result(upload)

        t = Transaction.objects.first()
        self.assertEqual(t.account, self.income_account)
        self.assertEqual(float(t.amount), 50.0)

    def test_credit_card_usd_fallback_creates_usd_transaction(self):
        rows = [cc_row(1, "2024-01-15", "PAYPAL", local_amount="0.00", usd_amount="14.00", usd_currency="USD")]
        upload = self._make_cc_upload(rows)

        process_upload_result(upload)

        t = Transaction.objects.first()
        self.assertEqual(float(t.amount), 14.0)
        self.assertEqual(t.currency, self.usd)

    # --- Successful savings account processing ---

    def test_creates_savings_account_transaction_from_debit(self):
        rows = [sa_row(1, "2024-01-15", "RENT", debit_amount="5000.00")]
        upload = self._make_sa_upload(rows)

        process_upload_result(upload)

        self.assertEqual(Transaction.objects.count(), 1)
        t = Transaction.objects.first()
        self.assertEqual(t.description, "RENT")
        self.assertEqual(float(t.amount), 5000.0)
        self.assertEqual(t.account, self.expense_account)

    def test_savings_account_credit_uses_income_account(self):
        rows = [sa_row(1, "2024-01-15", "SALARY", credit_amount="10000.00")]
        upload = self._make_sa_upload(rows)

        process_upload_result(upload)

        t = Transaction.objects.first()
        self.assertEqual(t.account, self.income_account)
        self.assertEqual(float(t.amount), 10000.0)

    # --- Fail rows logged ---

    def test_logs_fail_for_invalid_date(self):
        rows = [cc_row(1, "not-a-date", "X", local_amount="100.00")]
        upload = self._make_cc_upload(rows)

        process_upload_result(upload)

        upload.refresh_from_db()
        self.assertEqual(Transaction.objects.count(), 0)
        self.assertEqual(upload.upload_status, Upload.UploadStatus.DONE)
        self.assertEqual(upload.fails[0]["row_number"], 1)

    def test_logs_fail_for_period_not_found(self):
        rows = [cc_row(1, "2024-03-15", "X", local_amount="100.00")]
        upload = self._make_cc_upload(rows)

        process_upload_result(upload)

        upload.refresh_from_db()
        self.assertEqual(Transaction.objects.count(), 0)
        self.assertIn("Period not found", upload.fails[0]["reason"])

    def test_logs_fail_for_closed_period(self):
        rows = [cc_row(1, "2024-02-15", "X", local_amount="100.00")]
        upload = self._make_cc_upload(rows)

        process_upload_result(upload)

        upload.refresh_from_db()
        self.assertEqual(Transaction.objects.count(), 0)
        self.assertIn("Period not found or closed", upload.fails[0]["reason"])

    def test_logs_fail_for_zero_amount(self):
        rows = [cc_row(1, "2024-01-15", "X", local_amount="0.00")]
        upload = self._make_cc_upload(rows)

        process_upload_result(upload)

        upload.refresh_from_db()
        self.assertEqual(Transaction.objects.count(), 0)
        self.assertIn("zero or invalid", upload.fails[0]["reason"])

    def test_logs_fail_for_duplicate_transaction(self):
        rows = [cc_row(1, "2024-01-15", "WALMART", local_amount="100.00")]
        upload1 = self._make_cc_upload(rows)
        process_upload_result(upload1)

        upload2 = self._make_cc_upload(rows)
        process_upload_result(upload2)

        self.assertEqual(Transaction.objects.count(), 1)
        upload2.refresh_from_db()
        self.assertEqual(upload2.fails[0]["reason"], "Duplicate transaction")

    # --- Status transitions ---

    def test_upload_status_is_done_after_success(self):
        rows = [cc_row(1, "2024-01-15", "WALMART", local_amount="100.00")]
        upload = self._make_cc_upload(rows)

        process_upload_result(upload)

        upload.refresh_from_db()
        self.assertEqual(upload.upload_status, Upload.UploadStatus.DONE)

    def test_upload_status_is_done_even_with_some_fails(self):
        rows = [
            cc_row(1, "2024-01-15", "OK", local_amount="100.00"),
            cc_row(2, "2024-03-15", "BAD PERIOD", local_amount="50.00"),
        ]
        upload = self._make_cc_upload(rows)

        process_upload_result(upload)

        upload.refresh_from_db()
        self.assertEqual(upload.upload_status, Upload.UploadStatus.DONE)
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(len(upload.fails), 1)

    def test_upload_dates_set_after_processing(self):
        rows = [
            cc_row(1, "2024-01-05", "STORE A", local_amount="100.00"),
            cc_row(2, "2024-01-20", "STORE B", local_amount="200.00"),
        ]
        upload = self._make_cc_upload(rows)

        process_upload_result(upload)

        upload.refresh_from_db()
        self.assertEqual(upload.start_date, date(2024, 1, 5))
        self.assertEqual(upload.end_date, date(2024, 1, 20))

    # --- Account association ---

    def test_account_association_overrides_default_account(self):
        special_account = Account.objects.create(name="Supermercado", sign=Account.DEBE)
        AccountAssociation.objects.create(account=special_account, token="WALMART")
        rows = [cc_row(1, "2024-01-15", "WALMART STORE", local_amount="100.00")]
        upload = self._make_cc_upload(rows)

        process_upload_result(upload)

        t = Transaction.objects.first()
        self.assertEqual(t.account, special_account)

    def test_account_association_is_case_insensitive(self):
        special_account = Account.objects.create(name="Netflix", sign=Account.DEBE)
        AccountAssociation.objects.create(account=special_account, token="netflix")
        rows = [cc_row(1, "2024-01-15", "NETFLIX MONTHLY", local_amount="15.99")]
        upload = self._make_cc_upload(rows)

        process_upload_result(upload)

        t = Transaction.objects.first()
        self.assertEqual(t.account, special_account)

    def test_no_matching_association_uses_expense_account(self):
        special_account = Account.objects.create(name="Other", sign=Account.DEBE)
        AccountAssociation.objects.create(account=special_account, token="AMAZON")
        rows = [cc_row(1, "2024-01-15", "WALMART", local_amount="100.00")]
        upload = self._make_cc_upload(rows)

        process_upload_result(upload)

        t = Transaction.objects.first()
        self.assertEqual(t.account, self.expense_account)

    # --- Currency symbol in amount ---

    def test_savings_account_debit_with_currency_prefix_creates_transaction(self):
        rows = [sa_row(1, "2024-01-15", "Préstamo", debit_amount="L10,342.64")]
        upload = self._make_sa_upload(rows)

        process_upload_result(upload)

        self.assertEqual(Transaction.objects.count(), 1)
        t = Transaction.objects.first()
        self.assertEqual(float(t.amount), 10342.64)
        self.assertEqual(t.account, self.expense_account)

    def test_savings_account_credit_with_currency_prefix_creates_transaction(self):
        rows = [sa_row(1, "2024-01-15", "Intereses", credit_amount="L17.23")]
        upload = self._make_sa_upload(rows)

        process_upload_result(upload)

        self.assertEqual(Transaction.objects.count(), 1)
        t = Transaction.objects.first()
        self.assertEqual(float(t.amount), 17.23)
        self.assertEqual(t.account, self.income_account)

    # --- Upload linked to transaction ---

    def test_transaction_linked_to_upload(self):
        rows = [cc_row(1, "2024-01-15", "WALMART", local_amount="100.00")]
        upload = self._make_cc_upload(rows)

        process_upload_result(upload)

        t = Transaction.objects.first()
        self.assertEqual(t.upload, upload)
