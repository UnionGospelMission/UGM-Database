from django.db import models
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os

class OverwriteStorage(FileSystemStorage):
    def get_available_name(self, name):
        self.delete(name)
        return name

def guestPictureNamer(instance, filename):
	return 'guestpictures/%s.%s'%(instance.id,filename.split('.')[-1])

# Create your models here.

class User_Permission_Setting(models.Model):
    user = models.ForeignKey(User)
    permissions = models.ManyToManyField("Permission",null=True,blank=True)
    def __unicode__(self):
        return self.user.username

    def permissions_list(self):
        return ' | '.join([i.__unicode__() for i in self.permissions.all()])

    class Meta:
        permissions = (
            ('view_user_permission_settings', 'Can See Permissions by User'),
            ('manage_user_permission_settings', 'Can Set Permissions by User'),
        )

class DynamicFilePermissions(models.Model):
    path = models.CharField(max_length=200)
    permissions_may_have = models.ManyToManyField('Permission', null=True, blank=True, related_name='dynamic_form_may')
    permissions_must_have = models.ManyToManyField('Permission', null=True, blank=True, related_name='dynamic_form_must')
    guest = models.ForeignKey("Guest",null=True,blank=True)
    form = models.ForeignKey("Form", null=True,blank=True)
    field = models.ForeignKey("Field", null=True,blank=True)
    program = models.ManyToManyField("Program",null=True,blank=True)

    def __unicode__(self):
        return self.path


class Attachment(models.Model):
    owner = models.ManyToManyField(User)
    name = models.CharField(max_length=200, unique=True)
    attachment = models.FileField(upload_to='staticforms')
    permissions_may_have = models.ManyToManyField('Permission', null=True, blank=True, related_name='static_form_may')
    permissions_must_have = models.ManyToManyField('Permission', null=True, blank=True, related_name='static_form_must')
    def __unicode__(self):
        return self.name
    class Meta:
        permissions = (
            ('view_attachment', 'Can See Attachments'),
            ('manage_attachment', 'Can Manage Attachments'),
        )


class Program(models.Model):
    owner = models.ManyToManyField(User)
    name = models.CharField(max_length=200)
    permissions_may_have = models.ManyToManyField('Permission', null=True, blank=True, related_name='program_may')
    permissions_must_have = models.ManyToManyField('Permission', null=True, blank=True, related_name='program_must')
    permissions_write = models.ManyToManyField('Permission', null=True, blank=True, related_name='program_write')

    def __unicode__(self):
        return self.name

    class Meta:
        permissions = (
            ('view_program', 'Can See Programs'),
            ('manage_program', 'Can Manage Programs'),
        )


class Form(models.Model):
    owner = models.ManyToManyField(User)
    name = models.CharField(max_length=200)
    program = models.ManyToManyField(Program)
    form_prerequisite = models.ManyToManyField('Prerequisite', null=True, blank=True)
    permissions_must_have = models.ManyToManyField('Permission', null=True, blank=True, related_name='must')
    permissions_may_have = models.ManyToManyField('Permission', null=True, blank=True, related_name='may')
    permissions_write = models.ManyToManyField('Permission', null=True, blank=True, related_name='form_write')
    guest_completable = models.BooleanField(default=False)
    lock_when_complete = models.BooleanField(default=False)
    auto_grade = models.BooleanField(default=False)

    def program_list(self):
        return ' | '.join([i.name for i in self.program.all()])

    def __unicode__(self):
        return self.name

    def prerequisite_list(self):
        return ' | '.join([i.name for i in self.form_prerequisite.all()])

    class Meta:
        permissions = (
            ('view_form', 'Can See Forms'),
            ('manage_form', 'Can Manage Forms'),
        )


class Field(models.Model):
    owner = models.ManyToManyField(User)
    order = models.SmallIntegerField(null=True)
    name = models.CharField(max_length=200)
    label = models.CharField(max_length=200, blank=True, null=True)
    form = models.ForeignKey(Form, null=True)
    field_type = models.CharField(choices=(('text_box', 'Text Box'),
                                           ('comment_box', 'Comment Box'),
                                           ('drop_down', 'Drop Down'),
                                           ('boolean', 'Check Box'),
                                           ('list', 'List'),
                                           ('date', 'Date'),
                                           ('url', 'URL'),
                                           ('attachment', 'Attachment'),
                                           ('file','File'),
                                           ('title','Section Title'),
                                           ), max_length=200)
    attachment = models.ForeignKey(Attachment,blank=True,null=True)
    external_url = models.CharField(max_length=2000, blank=True, default='')
    dropdown_options = models.CharField(max_length=2000, blank=True, default='')
    time_series = models.BooleanField(default=False)
    field_prerequisite = models.ManyToManyField('Prerequisite', null=True, blank=True)
    required = models.BooleanField(default=False)
    add_only = models.BooleanField(default=False)
    permissions_must_have = models.ManyToManyField('Permission', null=True, blank=True, related_name='field_must')
    permissions_may_have = models.ManyToManyField('Permission', null=True, blank=True, related_name='field_may')
    permissions_write = models.ManyToManyField('Permission', null=True, blank=True, related_name='field_write')
    correct_answer = models.CharField(max_length=200, blank=True, null=True)

    def __unicode__(self):
        return self.name

    def prerequisite_list(self):
        return ' | '.join([i.name for i in self.field_prerequisite.all()])

    class Meta:
        permissions = (
            ('view_field', 'Can See Fields'),
            ('manage_field', 'Can Manage Fields'),
            ('change_fixed_field','Can Erase Notes')
        )


class Guest(models.Model):
    first_name = models.CharField(max_length=200, blank=True, null=True)
    middle_name = models.CharField(max_length=200, blank=True, null=True)
    last_name = models.CharField(max_length=200, blank=True, null=True)
    ssn = models.CharField(max_length=9, blank=True, null=True)
    program = models.ManyToManyField(Program)
    picture = models.ImageField(upload_to=guestPictureNamer,storage=OverwriteStorage())
    password = models.CharField(max_length=2000, blank=True, null=True)

    def clean(self):
        if self.ssn=='':
            self.ssn=None

    def __unicode__(self):
        return '%s %s' % (self.first_name, self.last_name)

    def program_list(self):
        return ' | '.join([i.name for i in self.program.all()])

    def last_4_ssn(self):
        if self.ssn:
            return u'%s' % self.ssn[-4:]
        return u''

    def image_tag(self,height=42,width=42):
        return mark_safe(u'<img src="%s" height="%s" width="%s"/>' % (self.picture.url,height,width))

    def name(self):
        return '%s %s' % (self.first_name.capitalize(), self.last_name.capitalize())

    image_tag.short_description = 'Image'
    image_tag.allow_tags = True

    class Meta:
        permissions = (
            ('view_guest', 'Can See Guests'),
            ('manage_guest', 'Can Manage Guests'),
        )


class Permission(models.Model):
    owner = models.ManyToManyField(User,related_name='permission_owner')
    name = models.CharField(max_length=2000, unique=True)
    users = models.ManyToManyField(User, blank=True, null=True)

    def __unicode__(self):
        return self.name

    def user_list(self):
        return ' | '.join([i.__unicode__() for i in self.users.all()])

    class Meta:
        permissions = (
            ('view_permission', 'Can See Permissions'),
            ('manage_permission', 'Can Manage Permissions'),
        )


class Prerequisite(models.Model):
    owner = models.ManyToManyField(User)
    name = models.CharField(max_length=2000, blank=True, null=True)
    prerequisite_form = models.ManyToManyField(Form, blank=True, null=True)
    prerequisite_field = models.ManyToManyField(Field, blank=True, null=True)
    is_complete = models.BooleanField(default=False)
    score_is_greater_than = models.CharField(max_length=2000, blank=True, null=True)
    is_value = models.CharField(max_length=2000, blank=True, null=True)
    contains = models.CharField(max_length=2000, blank=True, null=True)

    def __unicode__(self):
        return self.name

    def form_list(self):
        return ' | '.join([i.name for i in self.prerequisite_form.all()])

    def field_list(self):
        return ' | '.join([i.name for i in self.prerequisite_field.all()])

    class Meta:
        permissions = (
            ('view_prerequisite', 'Can See Prerequisites'),
            ('manage_prerequisite', 'Can Manage Prerequisites'),
        )


class GuestTimeData(models.Model):
    date = models.DateTimeField(null=True, blank=True)
    guest = models.ForeignKey(Guest)
    field = models.ForeignKey(Field)
    value = models.CharField(max_length=20000, blank=True, null=True, default='')


class GuestData(models.Model):
    date = models.DateTimeField(null=True, blank=True)
    guest = models.ForeignKey(Guest)
    field = models.ForeignKey(Field)
    value = models.CharField(max_length=20000, blank=True, null=True, default='')


class GuestFormsCompleted(models.Model):
    guest = models.ForeignKey(Guest)
    form = models.ForeignKey(Form)
    complete = models.BooleanField(default=False)
    score = models.CharField(max_length=2000, blank=True, null=True)


class GuestmanagementUserSettings(models.Model):
    user = models.ForeignKey(User, primary_key=True)
    guest = models.ForeignKey(Guest, null=True)
    next_page = models.CharField(max_length=2000, blank=True, null=True)


class Report(models.Model):
    name = models.CharField(max_length=2000, blank=True, null=True, unique=True)
    description = models.CharField(max_length=2000)
    code = models.CharField(max_length=200000, blank=True, null=True)
    owner = models.ManyToManyField(User,related_name="guestmanagement_report_users")
    variables = models.CharField(max_length=20000, blank=True, null=True)
    permissions_must_have = models.ManyToManyField('Permission', null=True, blank=True, related_name='report_must')
    permissions_may_have = models.ManyToManyField('Permission', null=True, blank=True, related_name='report_may')

    def owner_list(self):
        return ' | '.join([i.__unicode__() for i in self.owner.all()])

    class Meta:
        permissions = (
            ('view_report', 'Can See Reports'),
            ('manage_report', 'Can Manage Reports'),
        )

class QuickFilter(models.Model):
    name = models.CharField(max_length=2000, blank=True, null=True, unique=True)
    field = models.ForeignKey(Field, blank=True, null=True)
    form = models.ForeignKey(Form, blank=True, null=True)
    criteria = models.CharField(max_length=200000, blank=True, null=True)
    user = models.ForeignKey(User)

    def __unicode__(self):
        return self.name
