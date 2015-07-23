from django.contrib import admin

# Register your models here.
from truckmanagement.models import Truck,Driver,Donor,Donation

class DonorAdmin(admin.ModelAdmin):
	fieldsets=[
				('Name',				{'fields':['first_name','last_name','company_name'],}),
				('Street Address',		{'fields':['address1','address2','city','state','zip_code'], 'classes': ['collapse']}),
				('Mailing Address',		{'fields':['mailing_address1','mailing_address2','mailing_city','mailing_state','mailing_zip_code'], 'classes': ['collapse']}),
				('Contact Information',	{'fields':['home_phone','business_phone','business_fax','mobile_phone','email','contact_preference'], 'classes': ['collapse']}),
				('Administration',		{'fields':['nearest_facility','exported_to_donor_perfect','thankyou','mailing_list'], 'classes': ['collapse']}),
				('Notes',				{'fields':['first_contact_date','referral','comments'], 'classes': ['collapse']}),

			]
	list_display = ('id','last_name','first_name','company_name','address1','address2','city','state','zip_code','comments')
	list_filter = ['city','state','zip_code']
	search_fields = ['first_name','last_name','company_name','address1','address2','city','state','zip_code']



admin.site.register(Truck)
admin.site.register(Driver)
admin.site.register(Donor,DonorAdmin)
#admin.site.register(Donation)
