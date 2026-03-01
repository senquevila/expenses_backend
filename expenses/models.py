from datetime import timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import models
from django.db.models import F
from django.db.models.functions import Abs
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from expenses.mixins import CreationModificationDateMixin


class Period(models.Model):
    month = models.IntegerField(_("Mes"))
    year = models.IntegerField(_("Año"))
    closed = models.BooleanField(_("Solo lectura"), default=False)
    total = models.DecimalField(_("Monto total"), max_digits=13, decimal_places=2, default=0)
    active = models.BooleanField(_("Es visible"), default=True)

    class Meta:
        verbose_name = _("Periodo")
        verbose_name_plural = _("Periodos")
        unique_together = ("month", "year")

    def __str__(self) -> str:
        return f"{self.year}-{self.month:02}"

    @staticmethod
    def get_period_from_date(payment_date):
        try:
            return Period.objects.get(year=payment_date.year, month=payment_date.month)
        except Period.DoesNotExist:
            return None


class Currency(models.Model):
    name = models.CharField(_("Nombre"), max_length=100)
    alpha3 = models.CharField(_("Codigo alpha-3"), max_length=3, blank=True, null=True)

    class Meta:
        verbose_name = _("Moneda")
        verbose_name_plural = _("Monedas")

    def __str__(self) -> str:
        return self.name


class CurrencyConvert(models.Model):
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    exchange = models.DecimalField(_("Tasa de conversión"), max_digits=10, decimal_places=4)
    date = models.DateField(_("Fecha de conversión"), auto_now_add=True)

    class Meta:
        verbose_name = _("Conversion de moneda")
        verbose_name_plural = _("Conversiones de monedas")

    def __str__(self) -> str:
        return f"{self.date} > {self.currency}"


class Account(models.Model):
    DEBE = -1
    HABER = 1
    SIGN_TYPE = (
        (DEBE, "Debe (-)"),
        (HABER, "Haber (+)"),
    )
    FIXED = "FIX"
    VARIABLE = "VAR"
    ACCOUNT_TYPE = (
        (FIXED, "Fijo"),
        (VARIABLE, "Variable"),
    )
    name = models.CharField(_("Nombre"), max_length=100)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE)
    sign = models.IntegerField(_("Signo"), choices=SIGN_TYPE)
    account_type = models.CharField(_("Tipo de cuenta"), max_length=5, choices=ACCOUNT_TYPE, default=VARIABLE)

    class Meta:
        verbose_name = _("Cuenta")
        verbose_name_plural = _("Cuentas")

    def __str__(self) -> str:
        _sign = "-" if self.sign == -1 else "+"
        p_name = f" < {self.parent.name}" if self.parent else ""
        return f"{self.name} {p_name} [{_sign}{self.account_type}]"


class Accountable(CreationModificationDateMixin):
    period = models.ForeignKey(Period, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    amount = models.DecimalField(_("Monto"), max_digits=13, decimal_places=2)

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return f"{self.period} => {self.account}: {self.currency.alpha3} {self.amount}"

    @property
    def amount_str(self):
        return f"{self.currency.alpha3} {self.amount}"

    @property
    def get_signed_value(self) -> float:
        return self.amount * self.account.sign


def expense_upload_path(instance, filename):
    now = timezone.now()
    return f"expenses/{now.strftime('%Y/%m')}/{filename}"


def upload_dimension_default():
    return {
        "rows": 0,
        "cols": 0,
    }


def upload_parameters_default():
    return {
        "rows": {
            "start": 0,
            "end": 0,
        },
        "cols": [],
    }


class Upload(CreationModificationDateMixin):
    file = models.FileField(_("Archivo"), blank=True, null=True, upload_to=expense_upload_path)
    data = models.JSONField(_("Datos"), blank=True, null=True)
    dimension = models.JSONField(_("Dimension del document"), default=upload_dimension_default)
    result = models.JSONField(_("Resultado"), blank=True, null=True)
    parameters = models.JSONField(_("Parámetros"), blank=True, null=True, default=upload_parameters_default)
    start_date = models.DateField(_("Fecha de inicio"), default=timezone.now, blank=True, null=True)
    end_date = models.DateField(_("Fecha de fin"), default=timezone.now, blank=True, null=True)

    class Meta:
        verbose_name = _("Subida de archivo")
        verbose_name_plural = _("Subidas de archivos")

    def __str__(self) -> str:
        return str(self.file.name)


class UploadFile(CreationModificationDateMixin):
    class UploadFileStatus(models.TextChoices):
        PENDING = "PENDING", _("Pendiente")
        PROCESSING = "PROCESSING", _("Procesando")
        ERROR = "ERROR", _("Error")
        FINISHED = "FINISHED", _("Terminado")

    input_file = models.FileField(_("Archivo CSV"), blank=True, null=True, upload_to=expense_upload_path)
    output_file = models.FileField(_("Archivo JSON"), blank=True, null=True, upload_to=expense_upload_path)
    start_date = models.DateField(_("Fecha de inicio"), default=timezone.now, blank=True, null=True)
    end_date = models.DateField(_("Fecha de fin"), default=timezone.now, blank=True, null=True)
    status_upload = models.CharField(
        _("Estado del proceso"), max_length=20, choices=UploadFileStatus.choices, default=UploadFileStatus.PENDING
    )


class Transaction(Accountable):
    description = models.CharField(_("Descripción"), max_length=255, blank=True, null=True)
    payment_date = models.DateField(_("Fecha de pago"), default=timezone.now, blank=True, null=True)
    local_amount = models.DecimalField(_("Monto local"), max_digits=13, decimal_places=2, default=0, editable=False)
    identifier = models.CharField(max_length=64, blank=True, null=True)
    upload = models.ForeignKey(
        Upload,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    upload_file = models.ForeignKey(
        UploadFile,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _("Transacción")
        verbose_name_plural = _("Transacciones")

    def __str__(self) -> str:
        return super().__str__()

    @property
    def get_local_amount(self) -> Decimal:
        data = (
            CurrencyConvert.objects.filter(
                currency=self.currency,
                date__lte=self.payment_date + timedelta(days=settings.CURRENCY_CONVERT_DAYS_RANGE),
                date__gte=self.payment_date - timedelta(days=settings.CURRENCY_CONVERT_DAYS_RANGE),
            )
            .annotate(date_difference=Abs(F("date") - self.payment_date))
            .order_by("date_difference")
            .values("exchange")[:1]
        )
        exchange = data[0]["exchange"] if data else 1
        return Decimal(self.amount) * Decimal(self.account.sign) * Decimal(exchange)

    def save(self, *args, **kwargs):
        self.local_amount = self.get_local_amount
        super().save(*args, **kwargs)


class ProgramTransaction(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    amount = models.DecimalField(_("Monto"), max_digits=13, decimal_places=2)
    name = models.CharField(_("Nombre"), max_length=100)
    start_date = models.DateField(_("Fecha de inicio"), default=timezone.now, blank=True, null=True)
    end_date = models.DateField(_("Fecha de fin"), default=timezone.now, blank=True, null=True)
    active = models.BooleanField(_("Programado"), default=True)

    class Meta:
        verbose_name = _("Transacción programada")
        verbose_name_plural = _("Transacciones programadas")

    def __str__(self) -> str:
        return f"{self.name}"


class AccountAsociation(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    token = models.CharField(_("Token para asociar"), max_length=100)

    class Meta:
        verbose_name = _("Asociacion de cuenta")
        verbose_name_plural = _("Asociaciones de cuentas")

    def __str__(self) -> str:
        return f"{self.account.name} -> {self.token}"


class Loan(models.Model):
    description = models.CharField(_("Descripción"), max_length=255)
    amount = models.DecimalField(_("Monto"), max_digits=13, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    start_date = models.DateField(_("Fecha de inicio"), default=timezone.now, blank=True, null=True)
    monthly_payment = models.DecimalField(_("Pago mensual"), max_digits=13, decimal_places=2)
    months = models.SmallIntegerField(_("Meses"), default=0)
    is_active = models.BooleanField(_("Activo"), default=True)
    bank = models.CharField(_("Banco"), max_length=100)

    class Meta:
        verbose_name = _("Préstamo")
        verbose_name_plural = _("Préstamos")

    def __str__(self) -> str:
        return f"{self.bank} - {self.description} ({self.monthly_payment})"

    @property
    def end_date(self):
        return self.start_date + relativedelta(months=self.months)

    @property
    def percentage(self):
        start_date = self.start_date
        end_date = self.end_date
        if start_date > end_date:
            start_date, end_date = (
                end_date,
                start_date,
            )  # Ensure start_date is before end_date

        total_months = (end_date - start_date).days
        months_elapsed = (timezone.now().date() - start_date).days
        return min(round(months_elapsed * 100.0 / total_months), 100)

    @property
    def get_local_monthly_payment(self):
        currency_convert = (
            CurrencyConvert.objects.filter(
                currency=self.currency,
            )
            .order_by("-date")
            .only("exchange")
            .first()
        )
        exchange = currency_convert.exchange if currency_convert else Decimal(1)
        return self.monthly_payment * exchange

    @staticmethod
    def get_future_payments(date_after):
        if date_after is None:
            return 0

        active_loans = Loan.objects.filter(is_active=True)
        total_payment = Decimal(0)
        for loan in active_loans:
            if loan.end_date < date_after:
                continue

            currency_convert = (
                CurrencyConvert.objects.filter(
                    currency=loan.currency,
                )
                .order_by("-date")
                .only("exchange")
                .first()
            )
            exchange = currency_convert.exchange if currency_convert else Decimal(1)
            total_payment += loan.monthly_payment * exchange
        return total_payment


class Subscription(models.Model):
    MOVIES = "MOVIES"
    MUSIC = "MUSIC"
    BOOKS = "BOOKS"
    OTHER = "OTHER"
    SUBSCRIPTION_TYPE = (
        (MOVIES, "Películas"),
        (MUSIC, "Música"),
        (BOOKS, "Libros"),
        (OTHER, "Otros"),
    )
    name = models.CharField(_("Nombre"), max_length=100)
    subscription_type = models.CharField(_("Tipo"), max_length=10, choices=SUBSCRIPTION_TYPE, default=MOVIES)
    is_active = models.BooleanField(_("Activo"), default=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    monthly_payment = models.DecimalField(_("Pago mensual"), max_digits=13, decimal_places=2)

    class Meta:
        verbose_name = _("Suscripción")
        verbose_name_plural = _("Suscripciones")

    def __str__(self) -> str:
        return f"{self.name} - {self.subscription_type}"

    @property
    def get_local_monthly_payment(self):
        currency_convert = (
            CurrencyConvert.objects.filter(
                currency=self.currency,
            )
            .order_by("-date")
            .only("exchange")
            .first()
        )
        exchange = currency_convert.exchange if currency_convert else Decimal(1)
        return self.monthly_payment * exchange
