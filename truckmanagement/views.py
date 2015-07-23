from django.shortcuts import render,redirect,get_object_or_404, render_to_response
from django.contrib.auth.decorators import login_required
from django.contrib import auth
from django.contrib import messages
from django.forms.models import model_to_dict
from django.core.context_processors import csrf
from django.utils.safestring import mark_safe
from django.http import HttpResponse
from forms import DivErrorList,DonationForm
from django.template import RequestContext
from truckmanagement.models import Donor,Truck,Donation,Driver,UserSettings
import calendar,datetime
from dateutil.relativedelta import relativedelta
from math import ceil


def getWeekNumber(x):
	offset=x.replace(day=1).weekday()
	if offset==6:
		offset=0
	else:
		offset+=1
	return int(ceil((x.day+offset)/7.0))

months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
week_view_label = {True:'Week',False:'Month'}
weekday_name= lambda x : {0:'Monday',1:'Tuesday',2:'Wednesday',3:'Thursday',4:'Friday',5:'Saturday',6:'Sunday'}[x]
number_suffixes = lambda x : '%s%s'%(x,{1:'st',2:'nd',3:'rd',4:'th',5:'th',6:'th',7:'th',8:'th',9:'th',0:'th'}[x%10])



def Print(value):
	print '\n\n\n',value

def deleteDonationSeries(instance,request):
	target_donation=instance
	if instance.parent_donation:
		target_donation=instance.parent_donation
	allow_delete=True
	for i in Donation.objects.filter(parent_donation=target_donation):
		if i.status != 'picked_up':
			i.delete()
			messages.add_message(request, messages.INFO, 'Pickup Deleted')
		else:
			allow_delete=False
			messages.add_message(request, messages.INFO, 'Pickup Completed, Delete Failed')
	if allow_delete:
		if target_donation.status != 'picked_up':
			target_donation.delete()
			messages.add_message(request, messages.INFO, 'Pickup Deleted')
		else:
			messages.add_message(request, messages.INFO, 'Pickup Completed, Delete Failed')
	else:
		messages.add_message(request, messages.INFO, 'Pickup has completed child pickups, Delete Failed')


def makeRecurringDonation(target_donation,request):
	repeat_times = request.POST.get('repetition_times','')
	if not repeat_times:
		repeat_times = 100
	date_list = []
	a = target_donation.date
	if request.POST['repetition']=='weekdays' and a.weekday()>4:
		messages.add_message(request, messages.INFO, 'You have not selected a weekday')
		target_donation.delete()
		return False
	if request.POST['repetition']=='1':
		repeating_day = target_donation.date.weekday()
		repeating_week = getWeekNumber(target_donation.date)
		add_month = relativedelta(months=1)
		for i in range(0,int(repeat_times)):
			myrepeating_week=repeating_week
			a=a+add_month
			month_range = calendar.monthrange(a.year,a.month)
			if month_range[0]!=6 and month_range[0]>repeating_day:
				myrepeating_week+=1
			for z in range(1,month_range[1]+1):
				if a.replace(day=z).weekday()!=repeating_day:
					continue
				if getWeekNumber(a.replace(day=z))==myrepeating_week:
					date_list.append(a.replace(day=z))
					z+=100
					break
			if z==calendar.monthrange(a.year,a.month)[1]:
				messages.add_message(request, messages.INFO, 'There is no %s %s in %s %s'%(number_suffixes(repeating_week),
																							weekday_name(repeating_day),
																							months[a.month-1],
																							a.year,
																							))
		Print(date_list)
	elif request.POST['repetition']=='2':
		repeating_day = target_donation.date.weekday()
		add_month = relativedelta(months=1)
		for i in range(calendar.monthrange(a.year,a.month)[1],a.day-1,-1):
			if a.replace(day=i) > a and a.replace(day=i).weekday()==a.weekday():
				messages.add_message(request, messages.INFO, 'You have not selected the last %s, try "Same Week, Same Day"'%weekday_name(a.weekday()))
				target_donation.delete()
				return False
		for i in range(0,int(repeat_times)):
			a=a+add_month
			for i in range(calendar.monthrange(a.year,a.month)[1],0,-1):
				if a.replace(day=i).weekday()==repeating_day:
					date_list.append(a.replace(day=i))
					break
	else:
		repeating_pattern = {'daily':[0,0,1],'weekly':[0,1,0],'monthly':[1,0,0],'bi-weekly':[0,2,0],'weekdays':[0,0,1]}[request.POST['repetition']]
		repeating_pattern = relativedelta(months=repeating_pattern[0],weeks=repeating_pattern[1],days=repeating_pattern[2])
		for i in range(0,int(repeat_times)):
			a = a+repeating_pattern
			if request.POST['repetition']=='weekdays' and a.weekday()>4:
				a=a+repeating_pattern
				if request.POST['repetition']=='weekdays' and a.weekday()>4:
					a=a+repeating_pattern
			date_list.append(a)
	object_check = Donation.objects.filter(date__in=date_list,time=target_donation.time,truck=target_donation.truck)
	for i in object_check:
		messages.add_message(request, messages.INFO, 'Conflict with Recurrence on %s'%i.date)
		date_list.pop(date_list.index(i.date))
	parent_id = target_donation.id
	for i in date_list:
		target_donation.id=None
		target_donation.date=i
		target_donation.parent_donation=Donation.objects.get(pk=parent_id)
		target_donation.save()
	messages.add_message(request, messages.INFO, 'Recurrence ends on %s'%date_list[-1])
	return True

def new(request,year,month,day):
	'''
		Page for creating pickups
	'''
	context={}
	if request.method=='POST':
		Print(request.POST)
		form = DonationForm(request.POST)
		object_check = Donation.objects.filter(truck=request.POST['truck'],time=datetime.datetime.strptime(request.POST['time'],'%I:%M %p'),date=datetime.datetime.strptime(request.POST['date'],'%m/%d/%Y'))
		if object_check:
			messages.add_message(request, messages.INFO, 'Pickup not scheduled: time unavailable')
		else:
			if form.is_valid():
				a = form.save()
				if request.POST.get('repetition'):
					if makeRecurringDonation(a,request):
						return redirect('/schedule')
				else:
					return redirect('/schedule')
		target_donor = Donor.objects.get(pk=request.POST['donor'])
	else:
		user_settings = UserSettings.objects.get(pk=request.user)
		target_truck = user_settings.truck
		target_donor = user_settings.donor
		form = DonationForm({'truck':target_truck.id,
							'donor':target_donor.id,
							'address1':target_donor.address1,
							'address2':target_donor.address2,
							'city':target_donor.city,
							'state':target_donor.state,
							'zip_code':target_donor.zip_code,
							'driver':target_truck.driver.id,
							'nearest_facility':target_donor.nearest_facility,
							'date':datetime.date(int(year),months.index(month)+1,int(day)),
							})
	context.update(csrf(request))
	context.update({'form':fieldsetForm(form,request),'button_value':'Create','page_title':'New Pickup','target_donor':target_donor})
	return render_to_response("truckmanagement/donation.html",context,context_instance=RequestContext(request))

def index(request):
	return render(request,'shared/index.html')

def updateDonor(target_donation):
	parent_target_donation = target_donation
	if target_donation.parent_donation:
		parent_target_donation = target_donation.parent_donation
	if parent_target_donation.status != 'picked_up':
		parent_target_donation.address1=target_donation.donor.address1
		parent_target_donation.address2=target_donation.donor.address2
		parent_target_donation.city=target_donation.donor.city
		parent_target_donation.state=target_donation.donor.state
		parent_target_donation.zip_code=target_donation.donor.zip_code
		parent_target_donation.nearest_facility=target_donation.donor.nearest_facility
		parent_target_donation.save()
	object_check = Donation.objects.filter(parent_donation=parent_target_donation)
	if object_check:
		for i in object_check:
			if i.status != 'picked_up':
				i.address1=target_donation.donor.address1
				i.address2=target_donation.donor.address2
				i.city=target_donation.donor.city
				i.state=target_donation.donor.state
				i.zip_code=target_donation.donor.zip_code
				i.nearest_facility=target_donation.donor.nearest_facility
				i.save()

@login_required(login_url='/admin/login')
def donation(request,donation_id):
	Print(request.POST)
	context={}
	context.update(csrf(request))
	target_donation = Donation.objects.get(pk=donation_id)
	Print(target_donation.time)
	if request.POST:
		request.POST=request.POST.copy()
		if request.POST.get('time','')=='00:00 AM':
			request.POST['time']='12:00 AM'
		call_redirect=False
		if 'refresh' in request.POST:
			messages.add_message(request, messages.INFO, 'Donation Donor Info Updated on all related, non-completed donations')
			updateDonor(target_donation)
			return redirect('/schedule')
		elif 'delete' in request.POST:
			if request.POST.get('delete_series'):
				deleteDonationSeries(target_donation,request)
			else:
				object_check = Donation.objects.filter(parent_donation=target_donation)
				if object_check:
					deleteDonationSeries(target_donation,request)
				else:
					if target_donation.status != 'picked_up':
						target_donation.delete()
						messages.add_message(request, messages.INFO, 'Pickup Deleted')
					else:
						messages.add_message(request, messages.INFO, 'Pickup Completed, Delete Failed')
			return redirect('/schedule')

		else:
			update_donor = False
			if target_donation.donor != Donor.objects.get(pk=request.POST['donor']):
				update_donor = True
			requested_date = datetime.datetime.strptime(request.POST['date'],'%m/%d/%Y').date()
			requested_time = datetime.datetime.strptime(request.POST['time'],'%H:%M %p').time()
			object_check = Donation.objects.filter(truck=request.POST['truck'],time=requested_time,date=requested_date).exclude(id=target_donation.id)
			if object_check:
				messages.add_message(request, messages.INFO, 'Pickup not scheduled: time unavailable')
			elif target_donation.repetition and request.POST.get('update_series',''):
				if target_donation.date != requested_date or target_donation.time != requested_time:
					deleteDonationSeries(target_donation,request)
					form = DonationForm(request.POST)
					target_donation = form.save()
					makeRecurringDonation(target_donation,request)
				else:
					target_parent_donation = target_donation
					if target_donation.parent_donation:
						target_parent_donation = target_donation.parent_donation
					for i in Donation.objects.filter(parent_donation=target_parent_donation):
						if i.status != 'picked_up':
							i.donor = Donor.objects.get(pk=request.POST['donor'])
							i.address1 = request.POST['address1']
							i.address2 = request.POST['address2']
							i.city = request.POST['city']
							i.state = request.POST['state']
							i.zip_code = request.POST['zip_code']
							i.nearest_facility = request.POST['nearest_facility']
							i.truck = Truck.objects.get(pk=request.POST['truck'])
							i.driver = Driver.objects.get(pk=request.POST['driver'])
							i.repetition = request.POST['repetition']
							i.save()
					if target_parent_donation.status != 'picked_up':
						target_parent_donation.donor = Donor.objects.get(pk=request.POST['donor'])
						target_parent_donation.address1 = request.POST['address1']
						target_parent_donation.address2 = request.POST['address2']
						target_parent_donation.city = request.POST['city']
						target_parent_donation.state = request.POST['state']
						target_parent_donation.zip_code = request.POST['zip_code']
						target_parent_donation.nearest_facility = request.POST['nearest_facility']
						target_parent_donation.truck = Truck.objects.get(pk=request.POST['truck'])
						target_parent_donation.driver = Driver.objects.get(pk=request.POST['driver'])
						target_parent_donation.repetition = request.POST['repetition']
						target_parent_donation.save()
						target_donation=target_parent_donation
				if update_donor:
					updateDonor(target_donation)
				return redirect('/schedule')
			elif target_donation.status!='picked_up' or request.user.has_perm('truckmanagement.changefinished_donation'):
				form = DonationForm(request.POST or None,instance=target_donation)
				form.save()
				messages.add_message(request, messages.INFO, 'Pickup changed')
				if update_donor:
					updateDonor(target_donation)
				return redirect('/schedule')
			else:
				messages.add_message(request, messages.INFO, 'Pickup complete, modification not possible')
				return redirect('/schedule')
	form = fieldsetForm(DonationForm(instance=target_donation),request)
	context.update({'form':form,
				'button_value':'Update',
				'page_title':'Modify Pickup',
				'forward_donor':target_donation.donor.id,
			})
	return render_to_response("truckmanagement/donation.html",context,context_instance=RequestContext(request))

def fieldsetForm(form,request):
	form_as_divs = {}
	exclude_list = []
	for i in form.Meta.fieldsets:
		form_as_divs[i[0]]=[]
	for i in form:
		for a in form.Meta.fieldsets:
			if i.name in a[1]['fields']:
				exclude_list.append(i.name)
				form_as_divs[a[0]].append(i)
	form_as_string=''
	for i in form.Meta.fieldsets:
		if 'collapse' in i[1].get('class',''):
			form_as_string='%s%s\n'%(form_as_string,"<div id='hideTrigger' class='%s showhide'><a href='#'>Show/Hide %s</a></div>"%(i[0],i[0]))
			form_as_string='%s%s\n'%(form_as_string,"<div class='collapse%s'>"%i[0])
		else:
			form_as_string='%s%s\n'%(form_as_string,"<div class=' showhide'><a href='#'>%s</a></div>"%(i[0],))
			form_as_string='%s%s\n'%(form_as_string,"<div>")
		for a in form_as_divs[i[0]]:
			if a.errors and 'collapse' in i[1].get('class',''):
				messages.add_message(request, messages.INFO, 'Form has errors at %s in %s'%(a.name,i[0]))
			form_as_string='%s%s%s%s<br/>\n'%(form_as_string,a.errors,a.label_tag(),a)
		form_as_string='%s%s\n'%(form_as_string,"</div>")
	for i in form:
		if not i.name in exclude_list:
			form_as_string='%s%s%s<br/>\n'%(form_as_string,i.label_tag(),i)
	return mark_safe(form_as_string)

def schedule(request):
	'''
		main schedule viewer
	'''
	if request.user.is_authenticated():
		user_settings = UserSettings.objects.get_or_create(user=request.user)[0]
		context = {}
		context.update({'truck_list':[i.name for i in Truck.objects.all()]})
		context.update(csrf(request))
		year,month,day = str(datetime.datetime.date(datetime.datetime.now())).split('-')
		if not user_settings.year:
			user_settings.year=int(year)
		month = int(month)
		if not user_settings.month:
			user_settings.month=month
		donation_list = {}
		start_date=''
		end_date=''
		all_donations=''
		month_range=''
		if request.method=='POST':
			if request.POST.get('jump_year',''):
				user_settings.month = months.index(request.POST['jump_month'])+1
				user_settings.year = int(request.POST['jump_year'])
			if request.POST.get('toggle_week_view',''):
				user_settings.week_view = user_settings.week_view == False
				user_settings.week = 1
			if request.POST.get('prev_month',''):
				if not user_settings.week_view:
					user_settings.month -= 1
					if user_settings.month==0:
						user_settings.year-=1
						user_settings.month = 12
				else:
					current_target_week = user_settings.week
					user_settings.week -= 7
					if user_settings.week < 1:
						current_target_weekday = datetime.datetime(user_settings.year,user_settings.month,current_target_week).weekday()
						if current_target_weekday==6:
							current_target_weekday=0
						new_target_weekday=datetime.datetime(user_settings.year,user_settings.month,1).weekday()
						if new_target_weekday==6:
							new_target_weekday=0
						if current_target_weekday<new_target_weekday:
							user_settings.week = 1
						else:
							user_settings.month -= 1
							if user_settings.month==0:
								user_settings.year-=1
								user_settings.month=12
							user_settings.week = calendar.monthrange(user_settings.year,user_settings.month)[1]
			if request.POST.get('next_month',''):
				if not user_settings.week_view:
					user_settings.month +=1
					if user_settings.month==13:
						user_settings.month=1
						user_settings.year+=1
				else:
					current_target_week = user_settings.week
					user_settings.week += 7
					if user_settings.week > calendar.monthrange(user_settings.year,user_settings.month)[1]:
						current_target_weekday = datetime.datetime(user_settings.year,user_settings.month,current_target_week).weekday()
						if current_target_weekday==6:
							current_target_weekday=0
						new_target_weekday=datetime.datetime(user_settings.year,user_settings.month,calendar.monthrange(user_settings.year,user_settings.month)[1]).weekday()
						if new_target_weekday==6:
							new_target_weekday=0
						if current_target_weekday>new_target_weekday:
							user_settings.week = calendar.monthrange(user_settings.year,user_settings.month)[1]
						else:
							user_settings.week = 1
							user_settings.month +=1
							if user_settings.month == 13:
								user_settings.month=1
								user_settings.year += 1
			if request.POST.get('target_truck',''):
				month_range=calendar.monthrange(user_settings.year,user_settings.month)
				start_date = datetime.date(user_settings.year,user_settings.month,1)
				end_date = datetime.date(user_settings.year,user_settings.month,month_range[1])
				target_truck=Truck.objects.get(name=request.POST['target_truck'])
				user_settings.truck=target_truck
				context.update({'target_truck':request.POST['target_truck']})
				all_donations=Donation.objects.filter(date__gte=start_date,date__lte=end_date,truck=user_settings.truck).order_by('time')
			if request.POST.get('all_trucks',''):
				user_settings.truck=None
			if request.POST.get('last_name','') or request.POST.get('first_name','') or request.POST.get('company_name',''):
				all_donors = Donor.objects.filter(first_name__icontains=request.POST.get('first_name',''),
													last_name__icontains=request.POST.get('last_name',''),
													company_name__icontains=request.POST.get('company_name',''),
												)
				donor_list = [[i.id,[i.first_name,i.last_name,i.company_name,i.address1,i.city,i.state,i.zip_code]] for i in all_donors]
				context.update({'donor_list':donor_list,'last_name':request.POST['last_name'],'first_name':request.POST['first_name'],'company_name':request.POST['company_name']})
			if request.POST.get('clear_donor',''):
				user_settings.donor=None
			if request.POST.get('target_donor',''):
				user_settings.donor=Donor.objects.get(pk=request.POST['target_donor'])
		if not month_range:
			month_range=calendar.monthrange(user_settings.year,user_settings.month)
		if not start_date:
			start_date = datetime.date(user_settings.year,user_settings.month,1)
		if not end_date:
			end_date = datetime.date(user_settings.year,user_settings.month,month_range[1])
		if all_donations=='':
			if user_settings.truck:
				all_donations=Donation.objects.filter(date__gte=start_date,date__lte=end_date,truck=user_settings.truck).order_by('time')
			else:
				all_donations=Donation.objects.filter(date__gte=start_date,date__lte=end_date).order_by('time')
		for i in all_donations:
			if not donation_list.get(i.date.day,''):
				donation_list[i.date.day]=[]
			donation_list[i.date.day].append([i.id,i.__unicode__(),{True:'largeload',False:''}[i.large_load]])
		day=1
		a=0
		month_list=[]
		while day<=month_range[1]:
			month_list.append([])
			if a==0 and month_range[0] != 6:
				for b in range(0,month_range[0]+1):
					month_list[a].append(['',[]])
				for b in range(month_range[0],6):
					month_list[a].append([format(day, '02d'),donation_list.get(day,[])])
					day+=1
			else:
				for b in range(0,7):
					if day <= month_range[1]:
						month_list[a].append([format(day, '02d'),donation_list.get(day,[])])
						day+=1
					else:
						month_list[a].append(['',[]])
			a+=1
		if user_settings.week_view:
			my_month_list = []
			for i in month_list:
				for a in i:
					if format(user_settings.week,'02d') in a:
						my_month_list.append(i)
			month_list=my_month_list
		context.update({'month_list':month_list,
						'month':months[user_settings.month-1],
						'year':user_settings.year,
						'toggle_week_view':week_view_label[user_settings.week_view],
						'target_week':user_settings.week,
						'target_donor':user_settings.donor,
						})
		if user_settings.truck:
			context.update({'target_truck':user_settings.truck.name,'truck_color':user_settings.truck.background_color})
		user_settings.save()
		return render_to_response("truckmanagement/schedule.html",context,context_instance=RequestContext(request))
	return HttpResponse("User not authenticated<br/>Comming Soon...ish?<br/><a href='/'>Home</a>")

def logout(request):
	user_settings = UserSettings.objects.get_or_create(user=request.user)[0]
	user_settings.week_view = False
	user_settings.month = None
	user_settings.year = None
	user_settings.donor = None
	user_settings.week = None
	user_settings.truck = None
	user_settings.save()
	auth.logout(request)
	return render(request,"shared/logout.html")

