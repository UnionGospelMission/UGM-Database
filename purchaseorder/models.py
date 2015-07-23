from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class GetOrNoneManager(models.Manager):
    """Adds get_or_none method to objects
    """
    def get_or_none(self, **kwargs):
        try:
            return self.get(**kwargs)
        except self.model.DoesNotExist:
            return None

class Department(models.Model):
    name = models.CharField(max_length=200)
    head = models.ForeignKey(User,related_name='department_head')
    signers = models.ManyToManyField(User,null=True, blank=True)
    sub = models.CharField(max_length=200,null=True, blank=True)

    def __unicode__(self):
        return self.name

class Vendor(models.Model):
    name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name

class PurchaseOrder(models.Model):
    owner = models.ForeignKey(User,null=True,blank=True)
    purchase_date = models.DateTimeField(null=True, blank=True)
    purchase_total = models.CharField(max_length=200,null=True,blank=True)
    locked = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)
    received = models.BooleanField(default=False)
    processed = models.BooleanField(default=False)
    attachments = models.CharField(max_length=200,null=True,blank=True)
    created_date = models.DateTimeField(null=True, blank=True)
    received_date = models.DateTimeField(null=True, blank=True)
    processed_date = models.DateTimeField(null=True, blank=True)
    revision = models.CharField(max_length=200,default=1)
    objects = GetOrNoneManager()

class BudgetCategory(models.Model):
    name = models.CharField(max_length=200)

class SpecialCategory(models.Model):
    name = models.CharField(max_length=200)
    department = models.ForeignKey(Department)
    created_date = models.DateTimeField()
    completed = models.BooleanField(default=False)

class AccountingStaff(models.Model):
	user = models.ForeignKey(User)

class Detail(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder)
    vendor = models.ForeignKey(Vendor)
    account_number = models.CharField(max_length=200)
    order_number = models.CharField(max_length=200)
    invoice_number = models.CharField(max_length=200)
    breakdown = models.ManyToManyField("DetailBreakdown",related_name="detail_breakdown_list")
    payment = models.CharField(max_length=200)
    credit_card = models.CharField(max_length=200)
    street_address = models.CharField(max_length=200)
    reimbursement = models.CharField(max_length=200)

class DetailBreakdown(models.Model):
    detail = models.ForeignKey(Detail)
    department = models.ForeignKey(Department)
    sub = models.CharField(max_length=200)
    category = models.CharField(max_length=200)
    amount = models.CharField(max_length=200)
    description = models.CharField(max_length=200)
    signed = models.BooleanField(default=False)
    signed_date = models.DateTimeField(null=True, blank=True)

