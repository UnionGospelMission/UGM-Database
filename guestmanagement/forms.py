from guestmanagement.models import Guest,Program,Form,Field,Prerequisite,Permission,ReportCode,Attachment,User_Permission_Setting
from django import forms
from django.utils.safestring import mark_safe

class NewUser_Permission_Setting(forms.ModelForm):
	class Meta:
		model=User_Permission_Setting
		exclude=[]
		list_filter = [['user','many','username','icontains']]
		list_display = ['user','permissions_list']

class NewGuestForm(forms.ModelForm):
	class Meta:
		model=Guest
		exclude=[]
		#widgets = {'password': forms.PasswordInput()}
		list_filter = [['first_name','icontains'],['last_name','icontains'],['ssn','endswith'],['program','many','name','icontains']]
		list_display = ['id','first_name','last_name','last_4_ssn','program_list','image_tag']

class NewProgramForm(forms.ModelForm):
	class Meta:
		model=Program
		exclude=[]
		list_filter = [['name','icontains']]
		list_display = ['name']

class NewFormForm(forms.ModelForm):
	class Meta:
		model=Form
		exclude=[]
		list_filter = [['name','icontains'],['program','many','name','icontains'],['form_prerequisite','many','name','icontains']]
		list_display = ['name','program_list','prerequisite_list']

class NewFieldForm(forms.ModelForm):
	dropdown_options = forms.CharField(widget=forms.Textarea(attrs={'size': 100, }),required=False)
	class Meta:
		model=Field
		exclude=['order']
		list_filter = [['name','icontains'],['form','many','name','icontains'],['label','icontains'],['field_type','icontains']]
		list_display = ['name','form','label','field_type','prerequisite_list']

class NewPrerequisiteForm(forms.ModelForm):
	class Meta:
		model=Prerequisite
		exclude=[]
		list_filter = [['name','icontains'],['prerequisite_form','many','name','icontains'],['prerequisite_field','many','name','icontains']]
		list_display = ['name','form_list','field_list','is_complete','is_value']

class NewPermissionsForm(forms.ModelForm):
	class Meta:
		model=Permission
		exclude=[]
		list_filter = [['name','icontains'],]
		list_display = ['name','user_list']

class NewReportForm(forms.ModelForm):
	description = forms.CharField(widget=forms.Textarea(),required=False)
	class Meta:
		model=ReportCode
		exclude=[]
		fields=['name','users','description']
		list_filter = [['name','icontains']]
		list_display = ['name','user_list']

class NewAttachmentForm(forms.ModelForm):
	class Meta:
		model=Attachment
		exclude=[]
		list_filter = [['name','icontains'],]
		list_display = ['name']
