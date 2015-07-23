from django.forms.utils import ErrorList
from django import forms
from truckmanagement.models import Donor,Truck,Donation,Driver
from django.db import models


class DivErrorList(ErrorList):
	def __unicode__(self):
		return self.as_divs()
	def as_divs(self):
		if not self: return ''
		return '<div class="errorlist">%s</div>' % ''.join(['<div class="errors">%s</div>' % e for e in self])

time_widget = forms.widgets.TimeInput(attrs={'class': 'timepicker', 'readonly':'true'})
time_widget.format = '%I:%M %p'
date_widget = forms.widgets.DateInput(attrs={'class':'datePicker', 'readonly':'true'})
date_widget.format = '%m/%d/%Y'

class DonationForm(forms.ModelForm):
	comments = forms.CharField(widget=forms.Textarea(attrs={'size': 100, }),required=False)
	feedback = forms.CharField(widget=forms.Textarea(attrs={'size': 100, }),required=False)
	items_description = forms.CharField(widget=forms.Textarea(attrs={'size': 100, }),required=False)
	special_instructions = forms.CharField(widget=forms.Textarea(attrs={'size': 100, }),required=False)
	time = forms.TimeField(input_formats=['%I:%M %p'],widget=time_widget)
	date = forms.DateField(widget=date_widget)
	time_in = forms.TimeField(input_formats=['%I:%M %p'],widget=time_widget,required=False)
	time_out = forms.TimeField(input_formats=['%I:%M %p'],widget=time_widget,required=False)
	class Meta:
		model=Donation
		exclude=['parent_donation']
		fieldsets = [
						('Donor',		{'fields':['donor'],}),
						('Time',		{'fields':['date','time'],}),
						('Status',		{'fields':['status','large_load'],}),
						('Address',		{'fields':['address1','address2','city','state','zip_code','nearest_facility'],'class':'collapse'}),
						('Notes',		{'fields':['items_description','special_instructions','feedback','comments'],'class':'collapse'}),
						('Truck',		{'fields':['truck','driver'],'class':'collapse'}),
						('Recurrence',	{'fields':['repetition','repetition_times'],'class':'collapse'}),
						('Progress',	{'fields':['delivered_to','time_in','time_out'],'class':'collapse'}),
					]

