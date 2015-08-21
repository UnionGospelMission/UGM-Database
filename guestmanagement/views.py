from random import randint
import hashlib,datetime,json
import os,re
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.context_processors import csrf
from django.utils.safestring import mark_safe
from django.utils.functional import SimpleLazyObject
from django.contrib import messages,auth
from django.db.models import Q,Max
from django.contrib.auth.models import User
from django.forms.formsets import formset_factory
from guestmanagement.models import Guest,GuestmanagementUserSettings,Program,Form,Field,Prerequisite,GuestData,GuestFormsCompleted,Permission,GuestTimeData,ReportCode,Attachment,DynamicFilePermissions,User_Permission_Setting
from forms import NewGuestForm,NewProgramForm,NewFormForm,NewFieldForm,NewPrerequisiteForm,NewPermissionsForm,NewReportForm,NewAttachmentForm,NewUser_Permission_Setting
from django.core.exceptions import MultipleObjectsReturned

# Common reference dictionaries


target_type_dict = {# Reference dictionary for matching the correct new form to the correct model and record the "primary key"
                    #'target_type':[model_form, model, 'search_field'],
                    'guest':[NewGuestForm,Guest,'id'],
                    'program':[NewProgramForm,Program,'name'],
                    'form':[NewFormForm,Form,'name'],
                    'field':[NewFieldForm,Field,'name'],
                    'prerequisite':[NewPrerequisiteForm,Prerequisite,'name'],
                    'permission':[NewPermissionsForm,Permission,'name'],
                    'report':[NewReportForm,ReportCode,'name'],
                    'attachment':[NewAttachmentForm,Attachment,'name'],
                    'user_permission_setting':[NewUser_Permission_Setting,User_Permission_Setting,'user'],
                }

# Common Methods
def Print(*value):
    '''
    Useful debugging tool.
    Prepends four lines before printing value to the stdout.
    Makes seeing the value easy in the server logs
    '''
    value=list(value)
    print '\n\n\n\n',value.pop(0)
    for i in value:
        print i

def baseContext(request):
    '''
    Creates the context which multiple pages expect
    '''
    # used in redirecting, possibly defunct but not yet removed.
    if request.GET.get('next','') and not isinstance(request.user,SimpleLazyObject):
        a = GuestmanagementUserSettings.objects.get_or_create(user=request.user)[0]
        a.next_page = request.GET['next']
        a.save()
    context = {'nexturl':request.path,'base_site':request.session.get('base_site','')}
    context.update(csrf(request))
    return context

def redirectWithNext(request,url):
    '''
    Checks to see if there was a specified next page previously and redirects there
    possibly defunct, but not yet removed
    '''
    if GuestmanagementUserSettings.objects.get_or_create(user=request.user)[0].next_page:
        a = GuestmanagementUserSettings.objects.get(user=request.user)
        url = a.next_page
        a.next_page=''
        a.save()
    return url

def createForm(field_list,user,request=None,second_object=None,error_flags={}):
    '''
    Builds the html form to be displayed based on a list of fields passed in from requesting view
    '''
    field_type_options={# reference dictionary relating field types (found in the Field model) to specific html
                        # 'field_type' : "html to display" (must have 4 %s locations)
                        'text_box':"<input id='%s' name='%s' type='text' value='%s'></br>\n%s",
                        'comment_box':"<textarea cols='40' id='%s' name='%s' rows='10' size='100'>%s</textarea></br>\n%s",
                        'drop_down':"<select id='%s' name='%s' value='%s'>\n%s</select></br>",
                        'boolean':"<input id='%s' name='%s' %s type='checkbox' />\n%s</br>",
                        'list':"<select multiple='multiple' id='%s' name='%s' value='%s'>\n%s</select></br>",
                        'date':"<input class='datePicker' id='%s' name='%s' readonly='true' type='text' value='%s'></br>\n%s",
                        'url':'<iframe %s%s width="560" height="345" src="%s?rel=0" frameborder="0" allowfullscreen>%s</iframe></br>',
                        'attachment':'<a %s%s href="%s">%s</a></br>',
                        'file':'</br>&nbsp;&nbsp;&nbsp;&nbsp;Change File: <input id="%s" name="%s" type="file" /></br>&nbsp;&nbsp;&nbsp;&nbsp;<a href="%s">%s</a></br>',
                        }
    # return html string for display in template.
    return mark_safe(
                        ''.join([
                                "%s%s%s: %s"%(
                                    error_flags.get(i,''),
                                    i.label,
                                    ' *' if i.required else '',
                                    field_type_options[i.field_type]%(
                                        i.name,
                                        i.name,
                                        i.attachment.attachment.url
                                            if i.field_type=='attachment' else i.external_url
                                            if i.field_type=='url' else GuestData.objects.get_or_create(guest=second_object,field=i)[0].value
                                            if not request else request.POST.get(i.name,'')
                                            if i.field_type != 'boolean' else "checked='checked'"
                                            if request.POST.get(i.name,'')=='on' else '',
                                        i.name if i.field_type=='attachment' else '%s %s: %s'%(second_object.first_name,second_object.last_name,i.label)
                                        if i.field_type=='file' and GuestData.objects.get_or_create(guest=second_object,field=i)[0].value else
                                        ''.join(
                                            [
                                                "<option value='%s' %s>%s</option>\n"%(
                                                    a.strip(),
                                                    {True:"selected='selected'",False:''}[a.strip() in GuestData.objects.get_or_create(guest=second_object,field=i)[0].value]
                                                        if not request else {True:"selected='selected'",False:''}[a.strip() in request.POST.get(i.name,'')],
                                                    a.strip(),
                                                )
                                                for a in i.dropdown_options.split('\n') if a != ''
                                            ]
                                        )
                                    )
                                )
                                 if i.field_type!='title' and testPrerequisites(i,second_object) else '<p class="formlabel"><strong>%s</strong></p></br>'%i.label
                                 if i.field_type=='title' else '<ul><li>Field %s prerequisites not satisfied</li></ul>'%i.name for i in field_list.order_by('order') if testPermission(i,user)
                            ]
                        )
                    )

def updateStaticPermissions(target_object,delete=False):
    '''
    Method to keep static file permissions up-to-date when changes are made to either forms or fields
    which contain static files previously entered in the database
    '''
    if isinstance(target_object,Form):
        query=Q(form=target_object)
    elif isinstance(target_object,Field):
        query=Q(field=target_object)
    else:
        return
    update_list = DynamicFilePermissions.objects.filter(query)
    for i in update_list:
        if delete:
            os.remove(i[1:])
            i.delete()
        else:
            i.form = i.field.form
            i.permissions_may_have = i.form.permissions_may_have + i.field.permissions_may_have
            i.permissions_must_have = i.form.permissions_must_have + i.field.permissions_must_have
            i.save()


def testPermission(target_object,user,session={},second_object=None,testurl=False):
    '''
    Method of determining based on permissions whether a user has permission to access a form, field, guest, or static file
    a return of True signifies permission, False signifies no permission
    '''
    if testurl:
        # If testing a static file, pull the static file permissions record from the database
        target_object = DynamicFilePermissions.objects.get(path=target_object)
    # If a report is being requested, return false if the user is not listed
    if isinstance(target_object,ReportCode):
        if user not in target_object.users.all():
            return False
    # If a guest is logged in
    if session.get('password',''):
        # Get the guest's record based on the session
        target_guest = Guest.objects.get(pk=session['guest'])
        if isinstance(target_object,Guest) and not target_object==target_guest:
            return False
        if isinstance(target_object,Form):
            if not getattr(target_object,'guest_completable'):
                return False
            # If the form being tested is for a specific guest, and locks when completed, and has been completed
            if second_object and target_object.lock_when_complete and GuestFormsCompleted.objects.filter(guest=target_guest,form=target_object)[0].complete:
                return False
        if isinstance(target_object,DynamicFilePermissions):
            # If the requested url does not belong to the requesting guest and belongs to a guest
            if not target_guest == target_object.guest and target_object.guest:
                return False
        return True
    if hasattr(target_object,'permissions_must_have'):
        for i in target_object.permissions_must_have.all():
            if user not in i.users.all():
                return False
    if hasattr(target_object,'permissions_may_have'):
        test_list = [True for i in target_object.permissions_may_have.all() if user in i.users.all()]
        if test_list==[] and target_object.permissions_may_have.all():
            return False
    if hasattr(target_object,'program'):
        if list(target_object.program.all()) != []:
            test_list=[True for i in getattr(target_object,'program').all() if testPermission(i,user)]
            if test_list==[]:
                return False
    return True

def moveField(target_field,direction):
    '''
    Method for changing what order fields appear on a form
    '''
    # Get the largest number in the order column of the table for the last field of the form
    highest_order = Field.objects.filter(form=target_field.form).aggregate(Max('order'))['order__max']
    # Get the order number the field should end up with when the process is over
    end_order_number = max(min({'up':target_field.order-1,'down':target_field.order+1,'top':0,'bottom':highest_order}[direction],highest_order),0)
    while target_field.order!=end_order_number:
        if target_field.order>end_order_number:
            next_order = target_field.order-1
        else:
            next_order = target_field.order+1
        obstacle_field = Field.objects.filter(form=target_field.form,order=next_order)
        if obstacle_field:
            obstacle_field[0].order = target_field.order
            obstacle_field[0].save()
        target_field.order=next_order
        target_field.save()

def beGone(perm=""):
    '''
    Method for dealing with unauthorized access
    '''
    return HttpResponse('Oops, lack of permission %s</br><a href="/guestmanagement/">Home</a>'%perm)

def testPrerequisites(target_object,guest):
    '''
    Method for determining whether a form's or field's prerequisite(s) is(are) satisfied
    returns True if all prerequisites are satisfied, otherwise False
    '''
    prerequisite_list=getattr(target_object,'{0}_prerequisite'.format({True:'form',False:'field'}[isinstance(target_object,Form)])).all()
    for i in prerequisite_list:
        for a in i.prerequisite_form.all():
            if not GuestFormsCompleted.objects.get_or_create(guest=guest,form=a)[0].complete:
                return False
            if i.score_is_greater_than:
                if int(GuestFormsCompleted.objects.get_or_create(guest=guest,form=a)[0].score)<int(i.score_is_greater_than):
                     return False
        for a in i.prerequisite_field.all():
            if i.is_complete and not GuestData.objects.get_or_create(guest=guest,field=a)[0].value:
                return False
            elif GuestData.objects.get_or_create(guest=guest,field=a)[0].value != i.is_value and i.is_value:
                return False
            elif i.contains not in GuestData.objects.get_or_create(guest=guest,field=a)[0].value and i.contains:
                return False
    return True

def autoGrade(form,guest):
    '''
    Method for comparing answers in a form to a set of predefined answers and returning the percent correct rounded to the nearest whole number
    '''
    field_list = Field.objects.filter(form=form)
    required_questions = float(len(field_list.filter(required=True)))
    correct_questions = float(len([i for i in field_list
                            if GuestData.objects.get(field=i,guest=guest).value == i.correct_answer
                            or (i.field_type=='boolean' and str(GuestData.objects.get(field=i,guest=guest).value == "checked='checked'") == i.correct_answer)
                            or (not i.correct_answer and i.required)]))
    return str(int(round(correct_questions/required_questions*100)))


# Views

def guestlogin(request,target_guest=None):
    '''
    View for logging in guests and storing their information into the session
    '''
    context=baseContext(request)
    # If the user posted a form vs arrived here by redirect
    if request.POST:
        # check for a selected guest, if found check for a correct password
        if not target_guest:
            # if no guest, the search option must have been submitted, retrieve possible guests from the database
            args=[]
            if request.POST['ssn']!='':
                args.append(Q(ssn__endswith=request.POST['ssn']))
            if request.POST['id'].isdigit():
                args.append(Q(id=requestedid))
            if request.POST['last_name']!='':
                args.append(Q(last_name__icontains=request.POST['last_name']))
            test_objects=None
            if args!=[]:
                test_objects = Guest.objects.filter(*args)
            # If no possible guests, direct user to staff,
            # if only one possible guest, return the password page,
            # otherwise, return the list of possible guests
            if not test_objects:
                messages.add_message(request, messages.INFO, 'No guest with that information\nPlease check in with staff or try again')
            elif len(test_objects)==1:
                return redirect('/guestmanagement/guestlogin/%s/'%test_objects[0].id)
            else:
                context.update({'guest_list':[['%s****'%i.last_name[:3],i.id,'%s****'%i.first_name[:3]] for i in test_objects]})
        elif request.POST.get('password',''):
            if not hashlib.sha512(request.POST['password']).hexdigest() == Guest.objects.get(pk=target_guest).password:
                messages.add_message(request, messages.INFO, 'Incorrect Login')
                return redirect('/guestmanagement/')
            request.session['password']=True
            request.session['guest']=target_guest
            request.session.set_expiry(600)
            return redirect('/guestmanagement/view/guest/%s/'%target_guest)
        else:
            messages.add_message(request, messages.INFO, 'Password Required. Please try again')
    elif target_guest:
        context.update({'guest_login':Guest.objects.get(pk=target_guest),'guest_name':'%s****'%Guest.objects.get(pk=target_guest).last_name[:3]})
    return render(request,'guestmanagement/guestlogin.html',context)

def index(request):
    '''
    View which returns the index page
    '''
    context=baseContext(request)
    return render(request,'shared/index.html',context)

def manage(request,target_type=None,target_object=None):
    '''
    View which provides the management interface for all possible user editable types of objects
        Possible values of target_type:
            Guests
            Forms
            Fields
            Programs
            Prerequisites
            Permissions
            Reports
            Attachments
        target_object represents a specific instance of the above types
    '''
    # Check user for permission to manage specific type (e.g. manage forms)
    if not request.user.has_perm('guestmanagement.manage_{0}'.format(target_type)) and target_type:
        return beGone('guestmanagement.manage_{0}'.format(target_type))
    # Initialize context
    context=baseContext(request)
    if target_type:
        target_type.replace('_',' ')
    context.update({'target_type':target_type,'target_object':target_object})
    # If the main manage screen (no target type picked yet)
    if not target_type:
        return render(request,'guestmanagement/manage.html',context)
    # If managing a type but not object (e.g. managing forms but not a specific form)
    if not target_object:
        # Get the list of searchable fields from the target type dictionary
        filter_list = target_type_dict[target_type][0].Meta.list_filter
        # List comprehension to iterate over filter_list and create input boxes for each searchable field
        search_html = ''.join(["%s <input id='%s' type='text' name='%s'> "%(i[0].replace('_',' ').capitalize(),i[0],i[0]) for i in filter_list])
        # Add search area to context
        context.update({'search_html':mark_safe(search_html)})
        # Handling input from the just generated search boxes and the selection of guests
        # Returns /view/guest/guest id if a guest was selected
        # Returns a dynamically generated table of search results otherwise
        if request.POST:
            if request.POST.get('set_guest',''):
                a = GuestmanagementUserSettings.objects.get_or_create(user=request.user)[0]
                a.guest=Guest.objects.get(pk=request.POST['set_guest'])
                a.save()
                return redirect('/guestmanagement/view/guest/%s/'%a.guest.id)
            # Get the list of fields to display for that target type
            list_display = list(target_type_dict[target_type][0].Meta.list_display)
            # Add the id field to whatever list was created
            list_display.append('id')
            # List comprehension to iterate over the list_display and create table header for each visible field excluding id which
            # is always appended to the end
            table_header_html = ''.join(['<th>%s</th>'%i.replace('_',' ').capitalize() for i in list_display[:-1]])
            # Get the model associated with the target type
            base_table = target_type_dict[target_type][1]
            # list comprehension to create a list of query objects to filter
            # iterates over filterable fields and creates django Q(fieldname__fieldsearchtype=value) if a normal field
            # Q(fieldname__foreignkeyfieldname__fieldsearchtype=value)|(fieldname__isnull=True) if a field is a foreignkey and no search term was entered
            # Q(fieldname__foreignkeyfieldname__fieldsearchtype=value) if a field is a foreignkey and a searchterm was entered
            args=[Q(**{'{0}__{1}'.format(i[0],i[1]):request.POST[i[0]]})
                      if i[1]!='many' and request.POST[i[0]]!='' else
                  Q(**{'{0}__isnull'.format(i[0]):True})|Q(**{'{0}__{1}'.format(i[0],i[1]):request.POST[i[0]]})
                      if i[1]!='many' else
                  Q(**{'{0}__{1}__{2}'.format(i[0],i[2],i[3]):request.POST[i[0]]})|Q(**{'{0}__isnull'.format(i[0]):True})
                      if request.POST[i[0]]=='' else
                  Q(**{'{0}__{1}__{2}'.format(i[0],i[2],i[3]):request.POST[i[0]]})
                for i in filter_list]
            # Run the query just created and return distinct entries
            raw_object_list = base_table.objects.filter(*args).distinct().order_by('id')
            object_list = []
            # for loop to iterate over the objects returned from the filter and list_display
            # and create a list of lists of viewable fields
            for i in raw_object_list:
                if testPermission(i,request.user):
                    b = []
                    for a in list_display:
                        if not callable(getattr(i,a)):
                            b.append(getattr(i,a))
                        else:
                            b.append(getattr(i,a)())
                    object_list.append(b)
                # Limits search results to 50
                if len(object_list)>=50:
                    messages.add_message(request, messages.INFO, 'Results limited to 50 of %s. Please narrow search'%len(raw_object_list))
                    break
            # Put the search results into the context
            context.update({'object_list':object_list,
                            'table_header_html':mark_safe(table_header_html),
                            })
        # If a search has not been run
        return render(request,'guestmanagement/manage.html',context)
    # End managing a type but not object
    # Initialize a variable used in moving fields from one form to another
    currentform=False
    # If managing an object (e.g. a particular form)
    # If a new object
    if target_object=='new':
        # Check Permissions
        if not request.user.has_perm('guestmanagement.add_{0}'.format(target_type.replace('report','reportcode'))):
            return beGone('guestmanagement.add_{0}'.format(target_type.replace('report','reportcode')))
        # Set no instance flag
        target_instance = None
        # Set wording to appear on webpage
        create_or_edit = 'Create New'
    else:
        # Check Permissions
        if not request.user.has_perm('guestmanagement.change_{0}'.format(target_type.replace('report','reportcode'))):
            return beGone('guestmanagement.change_{0}'.format(target_type.replace('report','reportcode')))
        # Pull current database entry for object being managed
        target_instance = target_type_dict[target_type][1].objects.get(pk=target_object)
        # Make target object match target instance (pending cleanup)
        target_object = target_instance
        # user_permission_settings get updated at this point
        if target_type == 'user_permission_settings':
            # Update user_permissions_settings model to include all the permissions the user currently has
            target_object.permissions = Permission.object.filter(users__id=target_object.user.id)
            target_object.save()
        # Store the current form associate with the target field if applicable
        if target_type == 'field':
            currentform=target_object.form
        # If loading a report, attach current code to context
        if target_type == 'report':
            context.update({'loaded_report':target_object.code})
        # Set wording to appear on webpage
        create_or_edit = 'Modify'
    # Add wording to context
    context.update({'create_or_edit':create_or_edit})
    # Initialize form variable
    form = ''
    # If changes are being made either creation, deletion, or modification of a specific instance of the target_type
    if request.POST:
        # If deleting the target object
        if request.POST.get('delete_{0}'.format(target_type),''):
            # Check Permissions
            if not request.user.has_perm('guestmanagement.delete_{0}'.format(target_type)):
                return beGone('guestmanagement.delete_{0}'.format(target_type))
            # If deleting the instance, remove any static files related to the instance, then delete the instance itself
            updateStaticPermissions(target_instance,True)
            # if deleting a field, move it to the bottom of the form before deleting to preserve field order
            if target_type=='field':
                moveField(target_instance,'bottom')
            # Delete the instance
            target_instance.delete()
            # Notify the user of success
            messages.add_message(request, messages.INFO, '%s deleted'%target_type)
            return redirect('/guestmanagement/manage/%s/'%target_type)
        # Initialize created flag
        created=False
        # If this is a new object being created there will not yet be a target_instance
        if not target_instance:
            # Convert user id to user object if dealing with a user_permission_setting
            if target_type == 'user_permission_setting':
                request.POST['user'] = User.objects.get(pk=request.POST['user'])
            # Guests are tracked by the id field, which needs to have a default added to the post
            if target_type == 'guest':
                targetid=Guest.objects.all().order_by("-id")
                if targetid == []:
                    targetid=1
                else:
                    targetid=targetid[0].id+1
                request.POST['id']=targetid
            # get the search_field from the reference dictionary for the target_type and link it to the value from the submitted form
            kwargs = {'{0}'.format(target_type_dict[target_type][2]):request.POST[target_type_dict[target_type][2]]}
            # get the database model object from the reference dictionary and dump the unique identifier into it
            target_instance,created = target_type_dict[target_type][1].objects.get_or_create(**kwargs)
            # if a new object was not created (user trying to reuse the unique identifier)
            if not created:
                messages.add_message(request, messages.INFO, '%s already exists!'%target_type)
                return redirect('/guestmanagement/manage/%s/'%target_type)
            # Special processing for new fields
            if target_type=='field':
                if request.POST['form']:
                    # set field objects order to the end of their parent form object (will = 0 if there is one field in the form)
                    starting_order = Field.objects.filter(form=Form.objects.get(id=request.POST['form'])).aggregate(Max('order'))['order__max']
                    # if there are no fields in the form
                    if not starting_order and starting_order != 0:
                        # Create a default starting order
                        starting_order = -1
                    # increase the starting order by one to miss the last field already on the form
                    target_instance.order=starting_order+1
        # There is now a target_instance whether it is just created or being modified
        # get the new/modify form from the reference dictionary and bind the submitted data to it
        form = target_type_dict[target_type][0](request.POST,request.FILES,instance=target_instance)
        # If the form has all the required data
        if form.is_valid():
            # Special Handling for fields before saving if a field is being modified and moved from one form to another
            if target_type=='field' and not created and target_instance.form!=currentform:
                # Variable to remember where the field needs to end up
                endform=target_instance.form
                # Return the field to the original form restoring the field order of the original form
                target_instance.form=currentform
                # Move the field to the end of the form to preserve original form's starting order
                moveField(target_instance,'bottom')
                # Move the field to the new form
                target_instance.form=endform
                # set field objects order to the end of their parent form object (will = 0 if there is one field in the form)
                starting_order = Field.objects.filter(form=Form.objects.get(id=request.POST['form'])).aggregate(Max('order'))['order__max']
                # if there are no fields in the form
                if not starting_order and starting_order != 0:
                    # Create a default starting order
                    starting_order = -1
                # increase the starting order by one to miss the last field already on the form
                target_instance.order=starting_order+1
            # Save the form
            myobject = form.save()
            # Special processing for guests
            if target_type=='guest':
                # Hash the guest's password
                myobject.password = hashlib.sha512(myobject.password).hexdigest()
                # Save the guest object
                myobject.save()
                # set static file permissions for the guest picture
                filepermissionlist = DynamicFilePermissions.objects.get_or_create(path=myobject.picture.url)[0]
                filepermissionlist.program = myobject.program.all()
                filepermissionlist.guest = myobject
                filepermissionlist.save()
                # Set the guest as target guest for the user
                a = GuestmanagementUserSettings.objects.get_or_create(user=request.user)[0]
                a.guest = myobject
                a.save()
            # Update static permissions
            if target_type=='form' or target_type=='field':
                # trigger the updating of permissions for static files
                updateStaticPermissions(myobject)
            # Special processing for fields
            if target_type=='field':
                # Set name as default label
                if not myobject.label:
                    myobject.label = myobject.name
                    myobject.save()
                # Set first form as default form
                if not myobject.form:
                    myobject.form=Form.objects.all()[0]
                    myobject.save()
            # Special Processing for attachments
            if target_type=='attachment':
                # set the permissions for the new/modified static file
                filepermissionlist = DynamicFilePermissions.objects.get_or_create(path=myobject.attachment.url)[0]
                filepermissionlist.permissions_may_have = myobject.permissions_may_have
                filepermissionlist.permissions_must_have = myobject.permissions_must_have
                filepermissionlist.save()
            # Special processing for changing user permissions
            if target_type=='user_permission_setting':
                # Remove user from all permissions
                permission_list = Permission.objects.filter(users__id=target_object.user.id)
                for i in permission_list:
                    i.users.remove(target_object.user)
                # Update all affected permissions
                for i in target_object.permissions.all():
                    i.users.add(target_object.user)
            # Special processing for reports
            if target_type=='report':
                request_dict = dict(request.POST)
                report_code = []
                report_row_counter = '0'
                while isinstance(report_row_counter, str):
                    report_code_row = []
                    report_col_counter = '0'
                    while isinstance(report_col_counter,str):
                        report_code_row.append(request_dict['code'+report_row_counter+'-'+report_col_counter][0])

                        found_next = False
                        for k,v in request_dict.iteritems():
                            if k.find('code'+report_row_counter+'-'+str(int(report_col_counter)+1)) > -1:
                                found_next = True
                                break
                        if found_next:
                            report_col_counter = str(int(report_col_counter)+1)
                        else:
                            report_col_counter = False
                    
                    if report_code_row[0] != u'':
                        report_code.append(report_code_row)
                    
                    found_next = False
                    for k,v in request_dict.iteritems():
                        if k.find('code'+str(int(report_row_counter)+1)) > -1:
                            found_next = True
                            break
                    if found_next:
                        report_row_counter = str(int(report_row_counter)+1)
                    else:
                        report_row_counter = False
                    
                myobject.code = json.dumps(report_code)
                myobject.save()
                            
            # if user wants to save a report but continue modifying it
            if request.POST.get('save_report',''):
                # Add the form to the context
                context.update({'form':form})
                return redirect('/guestmanagement/manage/report/%s/'%myobject.id)
            # Return user to the managment page
            return redirect(redirectWithNext(request,'/guestmanagement/manage/%s/'%target_type))
        elif created:
            # if the form was invalid and the target object was a new instance, delete the new instance which will only contain the unique identifier
            target_instance.delete()
    # If no target object is being posted
    if not form:
        # Create a new, blank form for the target type
        form = target_type_dict[target_type][0](request.POST or None,instance=target_instance)
    # Special processing for reports
    if target_type == 'report':
        # Bind current code
        if target_instance:
            context.update({'loaded_report':target_instance.code})
        # Pull all the forms from the database which the user is allowed to see
        all_forms_list = [i for i in Form.objects.all() if testPermission(i,request.user)]
        # Pull all fields from the database which the user is allowed to see
        all_field_dict = {i.name:[[a.name.replace('(',''),a.field_type] for a in Field.objects.filter(form=i).distinct() if testPermission(a,request.user)] for i in all_forms_list}
        all_field_dict.update({'guest':[['first_name','text_field'],['middle_name','text_field'],['last_name','text_field'],['ssn','text_field'],['program','list']]})
        # Put the list of fields and forms into the context
        context.update({'all_forms_list':all_forms_list,'all_field_dict':json.dumps(all_field_dict)})
    # Add the form and instance to the context
    context.update({'form':form.as_p(),'target_object':target_object})
    # Serve up the page :)
    return render(request,'guestmanagement/manage.html',context)

def unsetcomplete(request,form_id,guest_id):
    '''
    View for allowing guests or staff to recomplete a previously completed form
    does not return a template of its own, and is always called as a GET with a next redirect
    '''
    if not request.user.has_perm('guestmanagement.delete_guestformscompleted'):
        return beGone('guestmanagement.delete_guestformscompleted')
    target_form = Form.objects.get(pk=form_id)
    target_guest = Guest.objects.get(pk=guest_id)
    a = GuestFormsCompleted.objects.get_or_create(guest=target_guest,form=target_form)[0]
    a.complete = False
    a.save()
    return redirect(request.GET['next'])

def setscore(request,form_id,guest_id):
    '''
    View to allow forced setting of scored forms
    will continue to show setscore template until a valid score is entered
    '''
    if not request.user.has_perm('guestmanagement.change_guestformscompleted'):
        return beGone('guestmanagement.change_guestformscompleted')
    context = baseContext(request)
    target_form = Form.objects.get(pk=form_id)
    target_guest = Guest.objects.get(pk=guest_id)
    if request.POST:
        try:
            score = int(request.POST.get('score',''))
            a = GuestFormsCompleted.objects.get_or_create(form=target_form,guest=target_guest)[0]
            a.score=request.POST['score']
            a.save()
            return redirect(request.GET['next'])
        except ValueError:
            pass
    context.update({'target_form':target_form,'target_guest':target_guest})
    return render(request,'guestmanagement/setscore.html',context)

def view(request,target_type,target_object,second_object=None):
    '''
    View for showing/completing forms attached to guests as well as general information for any other user created objects
        Possible values of target_type:
            Guests
            Forms
            Fields
            Programs
            Prerequisites
            Permissions
            Reports
            Attachments
        target_object represents a specific instance of the above types
        second_object represents a specific instance of the above types linked to target_object (e.g. user for whom a form is being completed)
    '''
    # retrieve the target_object through the database model obtained from the reference dictionary
    target_object = target_type_dict[target_type][1].objects.get(pk=target_object)
    if not request.user.has_perm('guestmanagement.view_{0}'.format(target_type)) and not testPermission(target_object,request.user,request.session,second_object):
        return beGone('guestmanagement.view_{0}'.format(target_type))
    if second_object:
        if not testPrerequisites(target_object,second_object):
            return beGone('prerequisites unsatisfied')
    context=baseContext(request)
    # If the user is not authenticated, it must be a logged in guest to have made it past the above permissions test
    if not request.user.is_authenticated():
        context.update({'guest_logged_in':True})
    link_list = None
    context.update({'target_type':target_type,'target_object':target_object})
    if target_type == 'guest':
        # Check for permission to view guest's programs
        permission_test = [True for i in target_object.program.all() if testPermission(i,request.user,request.session,second_object)]
        if permission_test != []:
            context.update({'view_image':target_object.image_tag})
            # create list of forms based on prerequisites and permissions along with status of each and links to view/complete
            form_list = [(i,{True:'Completed',False:'Incomplete'}[GuestFormsCompleted.objects.get_or_create(guest=target_object,form=i)[0].complete],i.lock_when_complete,GuestFormsCompleted.objects.get_or_create(guest=target_object,form=i)[0].score,i.auto_grade) for i in Form.objects.filter(program__in=target_object.program.all()).distinct() if testPrerequisites(i,target_object) and testPermission(i,request.user,request.session,second_object)]
            context.update({'form_list':form_list})
        else:
            return beGone('Missing permission to view guest program')
    if target_type == 'form':
        form=''
        field_list = Field.objects.filter(form=target_object)
        # if there is no second_object, no guest is being associated with this form, therefore the posted data relates to moving fields
        if not second_object:
            if not request.user.has_perm('guestmanagement.change_form'):
                return beGone('guestmanagement.change_form')
            if request.POST:
                moveField(Field.objects.get(pk=request.POST['move_field']),request.POST['move_type'])
        else:
            second_object = Guest.objects.get(pk=second_object)
            context.update({'second_object':second_object})
            if request.POST:
                # If a form is being completed
                # check for incomplete required fields and add appropriate error messages
                required_test={i:'<ul class="errorlist"><li>This field is required.</li></ul>' for i in field_list.order_by('order') if i.required and not request.POST.get(i.name,'') and i.field_type!='boolean' and testPrerequisites(i,second_object) and testPermission(i,request.user,request.session,second_object)}
                if not required_test:
                    time_stamp=datetime.datetime.now()
                    for i in field_list.order_by('order'):
                        if testPrerequisites(i,second_object):
                            a = GuestData.objects.get_or_create(guest=second_object,field=i)[0]
                            # convert boolean and file fields to appropriate value otherwise take given value and store in database
                            if i.field_type == 'boolean':
                                if request.POST.get(i.name,'') == 'on':
                                    a.value="checked='checked'"
                                else:
                                    a.value=''
                            elif i.field_type == 'file':
                                targetfile = request.FILES.get(i.name,'')
                                if targetfile:
                                    if not os.path.isdir('static/media/dynamicforms'):
                                        os.mkdir('static/media/dynamicforms')
                                    filepath = 'static/media/dynamicforms/'
                                    if i.time_series:
                                        filepath = '%s%s '%(filepath,str(datetime.datetime.now()))
                                    # Intercept file upload and save file onto file system
                                    filepath = '%s%s%s.%s'%(filepath,second_object.id,i.name,targetfile.name.split('.')[-1])
                                    with open(filepath, 'wb+') as destination:
                                        for chunk in targetfile.chunks():
                                            destination.write(chunk)
                                    # record path to file into database
                                    a.value = '/' + filepath
                                    # set static file permissions
                                    filepermissionlist = DynamicFilePermissions.objects.get_or_create(path=a.value)[0]
                                    filepermissionlist.permissions_may_have = list(i.permissions_may_have.all()) + list(target_object.permissions_may_have.all())
                                    filepermissionlist.permissions_must_have = list(i.permissions_must_have.all()) + list(target_object.permissions_must_have.all())
                                    filepermissionlist.guest = Guest.objects.get(pk=second_object.id)
                                    filepermissionlist.field = i
                                    filepermissionlist.form = target_object
                                    filepermissionlist.program = filepermissionlist.guest.program.all()
                                    filepermissionlist.save()
                                else:
                                    a.value = ""
                            elif i.field_type == 'drop_down' and not request.POST.get(i.name):
                                a.value = ""
                            elif i.field_type == 'list':
                                a.value=request.POST.getlist(i.name)
                            elif i.field_type == 'comment_box' and i.add_only and not request.user.has_perm('guestmanagement.change_fixed_field'):
                                if a.value in request.POST.get(i.name):
                                    a.value=request.POST.get(i.name)
                                else:
                                    messages.add_message(request, messages.INFO, '%s: no changing comments, comment not saved'%i.label)
                                    return redirect('/guestmanagement/view/form/%s/%s/'%(target_object.id,second_object.id))
                            else:
                                a.value = request.POST.get(i.name)
                            a.save()
                            if i.time_series:
                                b = GuestTimeData.objects.get_or_create(guest=second_object,field=i,date=time_stamp)[0]
                                b.value = a.value
                                b.save()
                            request.session['active']=True
                    # If save, return to viewing form, if save and continue, return to guest view
                    if request.POST.get('submit_form','')=='Update':
                        return redirect('/guestmanagement/view/form/%s/%s/'%(target_object.id,second_object.id))
                    else:
                        a=GuestFormsCompleted.objects.get_or_create(guest=second_object,form=target_object)[0]
                        a.complete=True
                        if target_object.auto_grade:
                            a.score = autoGrade(target_object,second_object)
                        a.save()
                        return redirect('/guestmanagement/view/guest/%s/'%second_object.id)
                else:
                    # If required field check failed, recreate form with error messages
                    form=createForm(field_list,request.user,request,second_object,required_test)
            # if no form was created from request.POST or no request.POST submitted
            while not form:
                try:
                    form=createForm(field_list,request.user,second_object=second_object)
                except MultipleObjectsReturned, e:
                    b=GuestData.objects.filter(guest=second_object)
                    c={}
                    for i in b:
                        if not c.get(i.field.name,False):
                            c[i.field.name]=i
                        elif c[i.field.name].value==i.value:
                            i.delete()
                        else:
                            raise e
                    form = ''


            context.update({'form':form})
        context.update({'field_list':field_list.order_by('order')})
        # Update general information at the bottom of the screen
        link_list=[['Form Prerequisites','prerequisite',target_object.form_prerequisite.all()],
                    ['Programs using form','program',target_object.program.all()],
                    ['May have permissions','permission',target_object.permissions_may_have.all()],
                    ['Must have permissions','permission',target_object.permissions_must_have.all()],
                ]
    if target_type == 'field':
        # Update general information at the bottom of the screen
        link_list=[['Parent form','form',[target_object.form]],
                    ['Other fields on form','field',Field.objects.filter(form=target_object.form).exclude(pk=target_object.id).distinct()],
                    ['Required prerequisites','prerequisite',target_object.field_prerequisite.all()],
                    ['May have permissions','permission',target_object.permissions_may_have.all()],
                    ['Must have permissions','permission',target_object.permissions_must_have.all()],
                ]
    if target_type == 'prerequisite':
        # Update general information at the bottom of the screen
        link_list=[['Prerequisite fields','field',target_object.prerequisite_field.all()],
                    ['Prerequisite forms','form',target_object.prerequisite_form.all()],
                    ['Dependent fields','field',Field.objects.filter(field_prerequisite__pk=target_object.id)],
                    ['Dependent forms','form',Form.objects.filter(form_prerequisite__pk=target_object.id)],
                ]
    if target_type == 'permission':
        # Update general information at the bottom of the screen
        link_list=[['Dependent may have fields','field',Field.objects.filter(permissions_may_have__pk=target_object.id).distinct()],
                    ['Dependent must have fields','field',Field.objects.filter(permissions_must_have__pk=target_object.id).distinct()],
                    ['Dependent may have forms','form',Form.objects.filter(permissions_may_have__pk=target_object.id).distinct()],
                    ['Dependent must have forms','form',Form.objects.filter(permissions_must_have__pk=target_object.id).distinct()],
                    ['Dependent may have programs','program',Program.objects.filter(permissions_may_have__pk=target_object.id).distinct()],
                    ['Dependent must have programs','program',Program.objects.filter(permissions_must_have__pk=target_object.id).distinct()],
                    ['Users with this permission','nolink',target_object.users.all()],
                ]
    if target_type == 'program':
        # Update general information at the bottom of the screen
        link_list=[['Forms in program','form',Form.objects.filter(program=target_object).distinct()],
                    ['May have permissions','permission',target_object.permissions_may_have.all()],
                    ['Must have permissions','permission',target_object.permissions_must_have.all()],
                ]
    # if not a guest logged in
    if not request.session.get('password',''):
        context.update({'link_list':link_list})
    return render(request,'guestmanagement/view.html',context)

def runreport(request,report_id):
    '''
    View for executing and displaying reports
    '''
    context=baseContext(request)
    report_code = json.loads(ReportCode.objects.get(pk=report_id).code)
    report = ''
    for i in report_code:
        Print(i)
        if i[0] == 'text':
            report = report + i[1]
        else:
            operator_list = i[1].split('::')
            field_list = i[2].split('::')
            for a in range(0,len(operator_list)):
                operator_list[a] = operator_list.split(' ',1)
                operator_list[a][0] = operator_list[a][0].replace('=','exact').replace('>','gt').replace('<','lt').replace('>=','gte').replace('<=','lte')
                operator_list[a][1] = operator_list[a][0].replace('True',"checked='checked'")
            
            kwargs = {'field__name':i[2].split('.')[1],'value__'+operator:value}
            if len(i)<4:
                filter_list = GuestData.objects.filter(**kwargs).distinct()
            else:
                filter_list = GuestTimeData.objects.filter(**kwargs).distinct()
            if i[0] == 'count':
                report = report + str(len(filter_list))
            if i[0] == 'sum':
                s=0
                for i in filter_list:
                    try:
                        s+=float(i.value)
                    except:
                        pass
                report = report + str(s)
                
    context.update({'report':mark_safe(report)})
    return render(request,'guestmanagement/report.html',context)

def logout(request):
    '''
    View for logging out users
    '''
    auth.logout(request)
    return render(request,"shared/logout.html")

def editpastform(request,target_guest,target_form,target_guesttimedata=None):
    '''
    View for editing past forms
    '''
    if not request.user.has_perm('guestmanagement.change_guesttimedata'):
        return beGone('guestmanagement.change_guesttimedata')
    
    target_guest = Guest.objects.get(pk=target_guest)
    if not testPermission(target_guest,request.user):
        return beGone('May not access guest')
    target_form = Form.objects.get(pk=target_form)
    if not testPermission(target_form,request.user):
        return beGone('May not access form')
    context=baseContext(request)
    target_field_list = Field.objects.filter(form=target_form,time_series=True).order_by('order')
    if not target_guesttimedata:
        target_field_list = [i for i in target_field_list if testPermission(i,request.user)]
        link_list = []
        readable_dates = []
        guesttimedata_list = GuestTimeData.objects.filter(guest=target_guest,field__in=target_field_list).distinct().order_by('-date')
        for i in guesttimedata_list:
            if i.date.strftime('%Y/%m/%d %H:%M:%S') not in readable_dates:
                link_list.append([i.date.strftime('%Y/%m/%d %H:%M:%S'),i.id])
                readable_dates.append(i.date.strftime('%Y/%m/%d %H:%M:%S'))
        context.update({'link_list':link_list})
    else:
        if request.POST:
            target_guesttimedata = GuestTimeData.objects.get(pk=target_guesttimedata)
            guesttimedata_list = GuestTimeData.objects.filter(date=target_guesttimedata.date,guest=target_guesttimedata.guest,field__form=target_guesttimedata.field.form).distinct()
            if request.POST.get('delete_%s'%target_form.name):
                if not request.user.has_perm('guestmanagement.delete_guesttimedata'):
                    return beGone('guestmanagement.change_guesttimedata')
                for i in guesttimedata_list:
                    i.delete()
                messages.add_message(request, messages.INFO, 'Form Deleted')
                return redirect('/guestmanagement/view/guest/%s/'%target_guest.id)
            new_date = target_guesttimedata.date.strftime('%m/%d/%Y ')
            if request.POST.get('changeDate'):
                new_date = request.POST.get('changeDate') + ' '
            new_time = target_guesttimedata.date.strftime('%H:%M %p')
            if request.POST.get('changeTime'):
                new_time = request.POST.get('changeTime')
            new_date = new_date + new_time
            new_date = datetime.datetime.strptime(new_date,'%m/%d/%Y %H:%M %p')
            test_list = GuestTimeData.objects.filter(guest=target_guest,date=new_date)
            if len(test_list)>0:
                messages.add_message(request, messages.INFO, 'Form already exists in selected date/time slot')
                return redirect('/guestmanagement/view/guest/%s/'%target_guest.id)
            for i in guesttimedata_list:
                i.date = new_date
                if i.field.field_type == 'boolean':
                    if request.POST.get(i.field.name,'') == 'on':
                        i.value="checked='checked'"
                    else:
                        i.value=''
                elif i.field.field_type == 'file':
                    targetfile = request.FILES.get(i.field.name,'')
                    if targetfile:
                        if not os.path.isdir('static/media/dynamicforms'):
                            os.mkdir('static/media/dynamicforms')
                        filepath = 'static/media/dynamicforms/%s'%(filepath,str(datetime.datetime.now()))
                        # Intercept file upload and save file onto file system
                        filepath = '%s%s%s.%s'%(filepath,target_guest.id,i.field.name,targetfile.name.split('.')[-1])
                        with open(filepath, 'wb+') as destination:
                            for chunk in targetfile.chunks():
                                destination.write(chunk)
                        # record path to file into database
                        i.value = '/' + filepath
                        # set static file permissions
                        filepermissionlist = DynamicFilePermissions.objects.get_or_create(path=i.value)[0]
                        filepermissionlist.permissions_may_have = i.field.permissions_may_have + target_form.permissions_may_have
                        filepermissionlist.permissions_must_have = i.field.permissions_must_have + target_form.permissions_must_have
                        filepermissionlist.guest = target_guest
                        filepermissionlist.field = i.field
                        filepermissionlist.form = target_form
                        filepermissionlist.save()
                    else:
                        i.value = ""
                elif i.field.field_type == 'drop_down' and not request.POST.get(i.field.name):
                    i.value = ""
                elif i.field.field_type == 'list':
                    i.value=request.POST.getlist(i.field.name)
                elif i.field.field_type == 'comment_box' and i.field.add_only and not request.user.has_perm('guestmanagement.change_fixed_field'):
                    if i.value in request.POST.get(i.field.name):
                        i.value=request.POST.get(i.field.name)
                    else:
                        messages.add_message(request, messages.INFO, '%s: no changing comments, comment not saved'%i.field.label)
                        return redirect('/guestmanagement/view/guest/%s/'%target_guest.id)
                else:
                    i.value = request.POST.get(i.field.name)
                i.save()
            messages.add_message(request, messages.INFO, 'Form Changed')
            return redirect('/guestmanagement/view/guest/%s/'%target_guest.id)
        else:
            form = createForm(target_field_list,request.user,second_object=target_guest)
            context.update({'form':form})
    context.update({'target_guest':target_guest, 'target_form':target_form.name})
    return render(request,'guestmanagement/edit.html',context)






















