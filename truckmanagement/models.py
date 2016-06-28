from django.db import models
from django.contrib.auth.models import User
import datetime
from django.utils.safestring import mark_safe

class Donor(models.Model):
	'''
	Database definition for tracking donations
	'''
	first_name = models.CharField(max_length=200,blank=True,null=True)
	last_name = models.CharField(max_length=200,blank=True,null=True)
	company_name = models.CharField(max_length=200,blank=True,null=True)
	address1 = models.CharField(max_length=200,blank=True,null=True)
	address2 = models.CharField(max_length=200,blank=True,null=True)
	city = models.CharField(max_length=200,blank=True,null=True)
	state = models.CharField(max_length=2,blank=True,null=True)
	zip_code = models.CharField(max_length=9,blank=True,null=True)
	mailing_address1 = models.CharField(max_length=200,blank=True,null=True)
	mailing_address2 = models.CharField(max_length=200,blank=True,null=True)
	mailing_city = models.CharField(max_length=200,blank=True,null=True)
	mailing_state = models.CharField(max_length=2,blank=True,null=True)
	mailing_zip_code = models.CharField(max_length=9,blank=True,null=True)
	first_contact_date = models.DateField(blank=True,null=True)
	nearest_facility = models.CharField(max_length=9,blank=True,null=True)
	exported_to_donor_perfect = models.BooleanField()
	thankyou = models.BooleanField()
	mailing_list = models.BooleanField()
	home_phone = models.CharField(max_length=30,blank=True,null=True)
	business_phone = models.CharField(max_length=30,blank=True,null=True)
	business_fax = models.CharField(max_length=30,blank=True,null=True)
	mobile_phone = models.CharField(max_length=30,blank=True,null=True)
	email = models.EmailField(blank=True,null=True)
	comments = models.CharField(max_length=2000,blank=True,null=True)
	contact_preference = models.CharField(choices=(('home_phone','Home Phone'),
													('business_phone','Business Phone'),
													('business_fax','Business Fax'),
													('mobile_phone','Mobile Phone'),
													('email','Email'),
													),max_length=200)
	referral = models.CharField(max_length=200,blank=True,null=True)

	def __unicode__(self):
		if self.company_name and (self.first_name or self.last_name):
			return '%s %s @ %s'%(self.first_name,self.last_name,self.company_name)
		elif self.company_name:
			return self.company_name
		else:
			return '%s %s'%(self.first_name,self.last_name)
		
	class Meta:
		ordering=["last_name"]

class Driver(models.Model):
	'''
	Database definition for tracking drivers
	'''
	name = models.CharField(max_length=200)
	hire_date = models.DateField()
	drivers_licence_number = models.CharField(max_length=20)
	drivers_licence_state = models.CharField(max_length=2)
	drivers_licence_expiration = models.DateField()
	def __unicode__(self):
		return self.name

class Truck(models.Model):
	'''
	Database defintion for tracking trucks
	'''
	description = models.CharField(max_length=200)
	name = models.CharField(max_length=200,unique=True)
	entered_service_date = models.DateField()
	last_service_date = models.DateField()
	vehicle_vin = models.CharField(max_length=17)
	licence_plate_number = models.CharField(max_length=15)
	driver = models.ForeignKey(Driver)
	fleet_number = models.SmallIntegerField(unique=True)
	background_color = models.CharField(choices=(('background-color:#EBF4F4;','Blue'),
													('background-color:#C3FDB8;','Green'),
													('background-color:#FFFFC2;','yellow'),
													('background-color:#FDD7E4;','Purple'),
													('background-color:#FFE5B4;','Orange'),
													('','No Color'),
													),max_length=200,default='')
	def __unicode__(self):
		return self.name

class Donation(models.Model):
	'''
	Database definition for tracking donations
	'''
	date = models.DateField()
	time = models.TimeField()
	donor = models.ForeignKey(Donor)
	address1 = models.CharField(max_length=200,blank=True,null=True)
	address2 = models.CharField(max_length=200,blank=True,null=True)
	city = models.CharField(max_length=200,blank=True,null=True)
	state = models.CharField(max_length=2,blank=True,null=True)
	zip_code = models.CharField(max_length=9,blank=True,null=True)
	nearest_facility = models.CharField(max_length=9,blank=True,null=True)
	items_description = models.CharField(max_length=200,blank=True,null=True)
	special_instructions = models.CharField(max_length=200,blank=True,null=True)
	feedback = models.CharField(max_length=200,blank=True,null=True)
	truck = models.ForeignKey(Truck)
	status = models.CharField(max_length=20,choices=(('pending','Pending'),('scheduled','Scheduled'),('picked_up','Picked Up')))
	driver = models.ForeignKey(Driver)
	delivered_to = models.CharField(max_length=200,blank=True,null=True)
	time_in = models.TimeField(null=True,blank=True)
	time_out = models.TimeField(null=True,blank=True)
	repetition = models.CharField(blank=True,max_length=20,choices=(
																	('daily','Daily'),
																	('weekly','Weekly'),
																	('monthly','Monthly'),
																	('bi-weekly','Bi-Weekly'),
																	('weekdays','Weekdays'),
																	('1','Same Week, Same Day'),
																	('2','Last Week, Same Day'),
																	))
	repetition_times = models.SmallIntegerField(blank=True,null=True)
	parent_donation = models.ForeignKey('self',blank=True,null=True)
	large_load = models.BooleanField(default=False)
	comments = models.CharField(max_length=200,blank=True,null=True)
	class Meta:
		permissions = (('changefinished_donation','Can Change Finished Donations'),)
	def __unicode__(self):
		return mark_safe("<b>%s</b> %s, %s, %s"%(self.time.strftime("%I:%M %p"),self.donor,self.address1,self.zip_code))

class UserSettings(models.Model):
	user = models.ForeignKey(User,primary_key=True)
	week_view = models.BooleanField(default=False)
	month = models.SmallIntegerField(blank=True,null=True)
	year = models.SmallIntegerField(blank=True,null=True)
	donor = models.ForeignKey(Donor,blank=True,null=True)
	week = models.SmallIntegerField(blank=True,null=True)
	truck = models.ForeignKey(Truck,blank=True,null=True)
