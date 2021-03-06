from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from django.contrib.auth import get_user_model
from django.db.models import Count

from .models import (  # @@@ make all these read-only
    Account,
    BankAccount,
    BitcoinReceiver,
    Card,
    Charge,
    Coupon,
    Customer,
    Event,
    EventProcessingException,
    Invoice,
    InvoiceItem,
    Plan,
    Subscription,
    Transfer,
    TransferChargeFee,
    UserAccount,
    TransferChargeFee,
    Product,
    Sku,
    Order
)


def user_search_fields():
    User = get_user_model()
    fields = [
        "user__{0}".format(User.USERNAME_FIELD)
    ]
    if "email" in [f.name for f in User._meta.fields]:  # pragma: no branch
        fields += ["user__email"]
    return fields


def customer_search_fields():
    return [
        "customer__{0}".format(field)
        for field in user_search_fields()
    ]


class CustomerHasCardListFilter(admin.SimpleListFilter):
    title = "card presence"
    parameter_name = "has_card"

    def lookups(self, request, model_admin):
        return [
            ["yes", "Has Card"],
            ["no", "Does Not Have a Card"]
        ]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(card__isnull=True)
        elif self.value() == "no":
            return queryset.filter(card__isnull=False)
        return queryset.all()


class InvoiceCustomerHasCardListFilter(admin.SimpleListFilter):
    title = "card presence"
    parameter_name = "has_card"

    def lookups(self, request, model_admin):
        return [
            ["yes", "Has Card"],
            ["no", "Does Not Have a Card"]
        ]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(customer__card__isnull=True)
        elif self.value() == "no":
            return queryset.filter(customer__card__isnull=False)
        return queryset.all()


class CustomerSubscriptionStatusListFilter(admin.SimpleListFilter):
    title = "subscription status"
    parameter_name = "sub_status"

    def lookups(self, request, model_admin):
        statuses = [
            [x, x.replace("_", " ").title()]
            for x in Subscription.objects.all().values_list(
                "status",
                flat=True
            ).distinct()
        ]
        statuses.append(["none", "No Subscription"])
        return statuses

    def queryset(self, request, queryset):
        if self.value() == "none":
            # Get customers with 0 subscriptions
            return queryset.annotate(subs=Count("subscription")).filter(subs=0)
        elif self.value():
            # Get customer pks without a subscription with this status
            customers = Subscription.objects.filter(
                status=self.value()).values_list(
                "customer", flat=True).distinct()
            # Filter by those customers
            return queryset.filter(pk__in=customers)
        return queryset.all()


class AccountListFilter(admin.SimpleListFilter):
    title = "account"
    parameter_name = "stripe_account"

    def lookups(self, request, model_admin):
        return [("none", "Without Account")] + [(a.pk, str(a)) for a in Account.objects.all()]

    def queryset(self, request, queryset):
        if self.value() == "none":
            return queryset.filter(stripe_account__isnull=True)
        if self.value():
            return queryset.filter(stripe_account__pk=self.value())
        return queryset


class PrefetchingChangeList(ChangeList):
    """A custom changelist to prefetch related fields."""
    def get_queryset(self, request):
        qs = super(PrefetchingChangeList, self).get_queryset(request)

        if subscription_status in self.list_display:
            qs = qs.prefetch_related("subscription_set")
        if "customer" in self.list_display:
            qs = qs.prefetch_related("customer")
        if "user" in self.list_display:
            qs = qs.prefetch_related("user")
        return qs


class ModelAdmin(admin.ModelAdmin):
    def get_changelist(self, request, **kwargs):
        return PrefetchingChangeList


class ChargeAdmin(ModelAdmin):
    list_display = [
        "stripe_id",
        "customer",
        "amount",
        "description",
        "paid",
        "disputed",
        "refunded",
        "receipt_sent",
        "created_at",
    ]
    list_select_related = [
        "customer",
    ]
    search_fields = [
        "stripe_id",
        "customer__stripe_id",
        "invoice__stripe_id",
    ] + customer_search_fields()
    list_filter = [
        "paid",
        "disputed",
        "refunded",
        "created_at",
    ]
    raw_id_fields = [
        "customer",
        "invoice",
    ]

    def get_queryset(self, request):
        qs = super(ChargeAdmin, self).get_queryset(request)
        return qs.prefetch_related("customer__user", "customer__users")


admin.site.register(
    EventProcessingException,
    list_display=[
        "message",
        "event",
        "created_at"
    ],
    search_fields=[
        "message",
        "traceback",
        "data"
    ],
    raw_id_fields=[
        "event"
    ],
)

admin.site.register(
    Event,
    raw_id_fields=["customer", "stripe_account"],
    list_display=[
        "stripe_id",
        "kind",
        "livemode",
        "valid",
        "processed",
        "created_at",
        "stripe_account",
    ],
    list_filter=[
        "kind",
        "created_at",
        "valid",
        "processed",
        AccountListFilter,
    ],
    search_fields=[
        "stripe_id",
        "customer__stripe_id",
        "validated_message",
        "=stripe_account__stripe_id",
    ] + customer_search_fields(),
)


class SubscriptionInline(admin.TabularInline):
    model = Subscription
    extra = 0
    max_num = 0

class SubscriptionAdmin(admin.ModelAdmin):
    model = Order

    raw_id_fields = [
        "customer"
    ]

    readonly_fields = [
        "current_period_end",
        "current_period_start",
        "trial_end",
        "trial_start"
    ]

    list_display = [
        "customer",
        "plan",
        "quantity",
        "start",
        "ended_at",
        "status"
    ]

    search_fields = [
        "customer__user__email",
        "customer__user__username",
        "stripe_id",
    ]

class CardInline(admin.TabularInline):
    model = Card
    extra = 0
    max_num = 0


class BitcoinReceiverInline(admin.TabularInline):
    model = BitcoinReceiver
    extra = 0
    max_num = 0


def subscription_status(obj):
    return ", ".join([subscription.status for subscription in obj.subscription_set.all()])
subscription_status.short_description = "Subscription Status"  # noqa


class CustomerAdmin(ModelAdmin):
    raw_id_fields = ["user", "stripe_account"]
    list_display = [
        "stripe_id",
        "user",
        "account_balance",
        "currency",
        "delinquent",
        "default_source",
        subscription_status,
        "date_purged",
        "stripe_account",
    ]
    list_filter = [
        "delinquent",
        CustomerHasCardListFilter,
        CustomerSubscriptionStatusListFilter,
        AccountListFilter,
    ]
    search_fields = [
        "stripe_id",
    ] + user_search_fields()
    inlines = [
        SubscriptionInline,
        CardInline,
        BitcoinReceiverInline
    ]


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    max_num = 0


def customer_has_card(obj):
    return obj.customer.card_set.exclude(fingerprint="").exists()
customer_has_card.short_description = "Customer Has Card"  # noqa


def customer_user(obj):
    if not obj.customer.user:
        return ""
    User = get_user_model()
    username = getattr(obj.customer.user, User.USERNAME_FIELD)
    email = getattr(obj, "email", "")
    return "{0} <{1}>".format(
        username,
        email
    )
customer_user.short_description = "Customer"  # noqa


admin.site.register(
    Invoice,
    raw_id_fields=["customer"],
    list_display=[
        "stripe_id",
        "paid",
        "closed",
        customer_user,
        customer_has_card,
        "period_start",
        "period_end",
        "subtotal",
        "total"
    ],
    search_fields=[
        "stripe_id",
        "customer__stripe_id",
    ] + customer_search_fields(),
    list_filter=[
        InvoiceCustomerHasCardListFilter,
        "paid",
        "closed",
        "attempted",
        "attempt_count",
        "created_at",
        "date",
        "period_end",
        "total"
    ],
    inlines=[
        InvoiceItemInline
    ]
)

admin.site.register(
    Plan,
    raw_id_fields=["stripe_account"],
    list_display=[
        "stripe_id",
        "name",
        "amount",
        "currency",
        "interval",
        "interval_count",
        "trial_period_days",
        "stripe_account",
    ],
    search_fields=[
        "stripe_id",
        "name",
        "=stripe_account__stripe_id",
    ] + customer_search_fields(),
    list_filter=[
        "currency",
        AccountListFilter,
    ],
    readonly_fields=[
        "stripe_id",
        "name",
        "amount",
        "currency",
        "interval",
        "interval_count",
        "trial_period_days",
        "statement_descriptor",
        "created_at",
    ],
)


admin.site.register(
    Coupon,
    list_display=[
        "stripe_id",
        "amount_off",
        "currency",
        "percent_off",
        "duration",
        "duration_in_months",
        "redeem_by",
        "valid"
    ],
    search_fields=[
        "stripe_id",
    ],
    list_filter=[
        "currency",
        "valid",
    ],
    readonly_fields=[
        "stripe_id",
        "amount_off",
        "currency",
        "duration",
        "duration_in_months",
        "max_redemptions",
        "metadata",
        "percent_off",
        "redeem_by",
        "times_redeemed",
        "valid",
        "created_at"
    ],
)


class TransferChargeFeeInline(admin.TabularInline):
    model = TransferChargeFee
    extra = 0
    max_num = 0


admin.site.register(
    Transfer,
    raw_id_fields=["event", "stripe_account"],
    list_display=[
        "stripe_id",
        "amount",
        "status",
        "date",
        "description",
        "stripe_account",
    ],
    search_fields=[
        "stripe_id",
        "event__stripe_id",
        "=stripe_account__stripe_id",
        "event__stripe_id",
        "description"
    ],
    inlines=[
        TransferChargeFeeInline
    ],
    list_filter=[
        AccountListFilter,
    ],
)


class AccountAdmin(ModelAdmin):
    raw_id_fields = ["user"]
    list_display = [
        "display_name",
        "type",
        "country",
        "payouts_enabled",
        "charges_enabled",
        "stripe_id",
        "created_at",
    ]
    search_fields = [
        "display_name",
        "stripe_id",
    ],


admin.site.register(
    BankAccount,
    raw_id_fields=["account"],
    list_display=[
        "stripe_id",
        "account",
        "account_holder_type",
        "account_holder_name",
        "currency",
        "default_for_currency",
        "bank_name",
        "country",
        "last4"
    ],
    search_fields=[
        "stripe_id",
    ]
)

admin.site.register(
    UserAccount,
    raw_id_fields=["user", "customer"],
    list_display=["user", "customer"],
    search_fields=[
        "=customer__stripe_id",
        "=user__email",
    ]
)

class SkuInline(admin.TabularInline):
    model = Sku
    extra = 0
    max_num = 0
    readonly_fields = ["stripe_id"]

admin.site.register(
    Product,
    readonly_fields=[
        "stripe_id",
        "created_at",
        "livemode"
    ],
    list_display=[
        "stripe_id",
        "name",
        "caption",
        "description",
        "active",
        "created_at"
    ],
    search_fields=[
        "stripe_id",
        "name",
        "description",
    ],
    inlines=[
        SkuInline
    ]
)

class SkuAdmin(admin.ModelAdmin):
    model = Sku
    raw_id_fields = [
        "product"
    ]

    readonly_fields = [
        "stripe_id",
        "created_at",
        "livemode"
    ]

    list_display = [
        "stripe_id",
        "product_name",
        "image",
        "inventory",
        "active",
        "created_at"
    ]

    search_fields = [
        "stripe_id",
        "product__name",
        "product__description"
    ]

    def product_name(self, obj):
        return obj.product.name

class OrderAdmin(admin.ModelAdmin):
    model = Order
    raw_id_fields = [
        "customer"
    ]

    readonly_fields = [
        "stripe_id",
        "created_at",
        "charge",
        "livemode"
    ]

    list_display = [
        "stripe_id",
        "customer_name",
        "amount",
        "currency",
        "status",
        "created_at"
    ]

    search_fields = [
        "stripe_id",
        "amount",
        "customer__user__first_name",
        "customer__user__last_name"
    ]

    def customer_name(self, obj):
        return "%s %s" % (obj.customer.user.first_name, obj.customer.user.last_name)

admin.site.register(Sku,SkuAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Account, AccountAdmin)
admin.site.register(Charge, ChargeAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Order,OrderAdmin)