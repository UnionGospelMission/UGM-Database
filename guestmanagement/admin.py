from django.contrib import admin
from guestmanagement.models import Guest,Program,Form,Field,Prerequisite,GuestData,Permission,GuestTimeData,Report,Attachment,DynamicFilePermissions,GuestmanagementUserSettings,GuestFormsCompleted,User_Permission_Setting,QuickFilter

# Register your models here.

class GuestAdmin(admin.ModelAdmin):
	list_display = ('id','last_4_ssn','last_name','first_name','program_list','image_tag')
	list_filter = ['program']
	search_fields = ['first_name','last_name','ssn']
	readonly_fields = ('image_tag',)

class FormAdmin(admin.ModelAdmin):
	list_display = ('name','program_list','prerequisite_list')
	list_filter = ['program']
	search_fields = ['name']

class FieldAdmin(admin.ModelAdmin):
	list_display = ('name','form','prerequisite_list')
	list_filter = ['form']
	search_fields = ['name']
	
class GuestDataAdmin(admin.ModelAdmin):
	search_fields = ['guest__last_name','field__name']
	list_display = ('guest','field','value')

class GuestTimeDataAdmin(admin.ModelAdmin):
	search_fields = ['guest__last_name']
	list_display = ('guest','date','field','value')

class DynamicFilePermissionsAdmin(admin.ModelAdmin):
	search_fields = ['path']

class GuestFormsCompletedAdmin(admin.ModelAdmin):
	search_fields = ['guest__last_name']
	list_display = ('guest','form','complete')

class ReportAdmin(admin.ModelAdmin):
	list_display = ('name','owner_list','description')

class AttachmentAdmin(admin.ModelAdmin):
	list_display = ('name','attachment')

class GuestmanagementUserSettingsAdmin(admin.ModelAdmin):
	list_display = ('user',)

class User_Permission_SettingAdmin(admin.ModelAdmin):
	list_display = ('user',)

admin.site.register(Guest,GuestAdmin)
admin.site.register(Program)
admin.site.register(QuickFilter)
admin.site.register(Form,FormAdmin)
admin.site.register(Field,FieldAdmin)
admin.site.register(Prerequisite)
admin.site.register(GuestData,GuestDataAdmin)
admin.site.register(Permission)
admin.site.register(GuestTimeData,GuestTimeDataAdmin)
admin.site.register(Report,ReportAdmin)
admin.site.register(Attachment,AttachmentAdmin)
admin.site.register(DynamicFilePermissions,DynamicFilePermissionsAdmin)
admin.site.register(GuestmanagementUserSettings)
admin.site.register(GuestFormsCompleted,GuestFormsCompletedAdmin)
admin.site.register(User_Permission_Setting,User_Permission_SettingAdmin)
