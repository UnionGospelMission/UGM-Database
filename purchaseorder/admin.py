from django.contrib import admin
from purchaseorder.models import PurchaseOrder,Department,Vendor,BudgetCategory,SpecialCategory
# Register your models here.



admin.site.register(PurchaseOrder)
admin.site.register(Department)
admin.site.register(Vendor)
admin.site.register(BudgetCategory)
admin.site.register(SpecialCategory)