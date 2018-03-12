import datetime

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from ..models import Account, Customer, Invoice, Plan, Subscription, Sku, Order, Product

try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse


User = get_user_model()


class AdminTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        super(AdminTestCase, cls).setUpClass()

        # create customers and current subscription records
        period_start = datetime.datetime(2013, 4, 1, tzinfo=timezone.utc)
        period_end = datetime.datetime(2013, 4, 30, tzinfo=timezone.utc)
        start = datetime.datetime(2013, 1, 1, tzinfo=timezone.utc)
        cls.plan = Plan.objects.create(
            stripe_id="p1",
            amount=10,
            currency="usd",
            interval="monthly",
            interval_count=1,
            name="Pro"
        )
        cls.plan2 = Plan.objects.create(
            stripe_id="p2",
            amount=5,
            currency="usd",
            interval="monthly",
            interval_count=1,
            name="Light"
        )
        for i in range(10):
            customer = Customer.objects.create(
                user=User.objects.create_user(username="patrick{0}".format(i)),
                stripe_id="cus_xxxxxxxxxxxxxx{0}".format(i)
            )
            Subscription.objects.create(
                stripe_id="sub_{}".format(i),
                customer=customer,
                plan=cls.plan,
                current_period_start=period_start,
                current_period_end=period_end,
                status="active",
                start=start,
                quantity=1
            )
        customer = Customer.objects.create(
            user=User.objects.create_user(username="patrick{0}".format(11)),
            stripe_id="cus_xxxxxxxxxxxxxx{0}".format(11)
        )
        Subscription.objects.create(
            stripe_id="sub_{}".format(11),
            customer=customer,
            plan=cls.plan,
            current_period_start=period_start,
            current_period_end=period_end,
            status="canceled",
            canceled_at=period_end,
            start=start,
            quantity=1
        )
        customer = Customer.objects.create(
            user=User.objects.create_user(username="patrick{0}".format(12)),
            stripe_id="cus_xxxxxxxxxxxxxx{0}".format(12)
        )
        Subscription.objects.create(
            stripe_id="sub_{}".format(12),
            customer=customer,
            plan=cls.plan2,
            current_period_start=period_start,
            current_period_end=period_end,
            status="active",
            start=start,
            quantity=1
        )
        Invoice.objects.create(
            customer=customer,
            date=timezone.now(),
            amount_due=100,
            subtotal=100,
            total=100,
            period_end=period_end,
            period_start=period_start
        )

        product = Product.objects.create(
            stripe_id="pr_123_xxx"
        )

        Sku.objects.create(
            stripe_id="sku_xxx_111",
            product=product,
            price=100,
        )

        Order.objects.create(
            stripe_id="or_123_xxx",
            customer=customer,
            amount=100,

        )

        cls.user = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="admin")
        cls.account = Account.objects.create(stripe_id="acc_abcd")
        cls.client = Client()

    def setUp(self):
        try:
            self.client.force_login(self.user)
        except AttributeError:
            # Django 1.8
            self.client.login(username="admin", password="admin")

    def test_customer_admin(self):
        """Make sure we get good responses for all filter options"""
        url = reverse("admin:pinax_stripe_customer_changelist")

        response = self.client.get(url + "?sub_status=active")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url + "?sub_status=cancelled")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url + "?sub_status=none")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url + "?has_card=yes")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url + "?has_card=no")
        self.assertEqual(response.status_code, 200)

    def test_customer_admin_prefetch(self):
        url = reverse("admin:pinax_stripe_customer_changelist")

        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

        Customer.objects.create(
            user=User.objects.create_user(username="patrick{0}".format(13)),
            stripe_id="cus_xxxxxxxxxxxxxx{0}".format(13)
        )
        with self.assertNumQueries(len(captured)):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_invoice_admin(self):
        url = reverse("admin:pinax_stripe_invoice_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url + "?has_card=no")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url + "?has_card=yes")
        self.assertEqual(response.status_code, 200)

    def test_plan_admin(self):
        url = reverse("admin:pinax_stripe_plan_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_charge_admin(self):
        url = reverse("admin:pinax_stripe_charge_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_account_filter(self):
        url = reverse("admin:pinax_stripe_customer_changelist")
        response = self.client.get(url + "?stripe_account={}".format(self.account.pk))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(url + "?stripe_account=none")
        self.assertEqual(response.status_code, 200)

    def test_sku_admin(self):
        url = reverse("admin:pinax_stripe_sku_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        sku = Sku.objects.first()

        url =  reverse('admin:pinax_stripe_sku_change', args=(sku.pk,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_order_admin(self):
        url = reverse("admin:pinax_stripe_order_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        order = Order.objects.first()

        url = reverse('admin:pinax_stripe_order_change', args=(order.pk,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

class AdminSimpleTestCase(SimpleTestCase):

    def test_customer_user_without_user(self):
        from ..admin import customer_user

        class CustomerWithoutUser(object):
            user = None

        class Obj(object):
            customer = CustomerWithoutUser()

        self.assertEqual(customer_user(Obj()), "")
