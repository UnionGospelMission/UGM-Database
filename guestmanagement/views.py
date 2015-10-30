from random import randint
import hashlib,datetime,json
import os,re, itertools
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
from cStringIO import StringIO
from copy import deepcopy
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
import traceback
from django.utils import timezone
from django.contrib.auth.decorators import login_required

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

#Report method class



class ReportProcessor():
    '''
        Main class for handling preparing and running reports
    '''
    def __init__(self):
        # Helper variables for creating tables
        self.tableVariables = { 'table_new_row':'</tr><tr>',
                                'table_new_row_with_break':'</tr><tr><td></td></tr><tr>',
                                'table_new_cell':'</td><td>',
                                'table_open_cell':'<td>',
                                'table_close_cell':'</td>',
                                'table_open_row':'<tr>',
                                'table_close_row':'</tr>',
        }
        # External functions (found on the report builder when "function" is selected)
        self.functions = {  'add':self.add,
                            'subtract':self.subtract,
                            'today': self.today,
                            'subtract_dates': self.subtractDates,
                            'length': self.length,
                            'count_bool_times_activated':self.countBooleans,
                            'count_bool_days_active':self.countDays,
                            'last_day_bool_activated':self.lastDayActivated,
                            'last_day_bool_deactivated':self.lastDayDeactivated,
                            'format_picture':self.formatPicture,
                            'add_subtract_dates':self.addSubtractDates,
        }
        # Internal functions (found on the report builder in each line's dropdown)
        self._functions = { 
                            'do':self.do,
                            'newline': self.newline,
                            'text': self.text,
                            'function':self.function,
                            'display':self.display,
                            'list':self.list_,
                            'count':self.count,
                            'sum':self.sum,
                            'set':self.set_,
                            'query':self.query,
                            'begin table':self.beginTable,
                            'end table':self.endTable,
                            'if':self.if_,
        }
        # Dictionary to convert report builder operators to django query filters
        self.filter_dict = {
                            '=':'exact',
                            '>':'gt',
                            '<':'lt',
                            '>=':'gte',
                            '<=':'lte',
                            '<>':'exact',
                            'contains':'icontains',
                            'guest':Guest,
                            'field':{u'':GuestData,u'on':GuestTimeData},

        }
        
        
    class Env(dict):
        '''
            Environment container for reports
        '''
        def __init__(self,parent):
            super(ReportProcessor.Env, self).__init__()
            # Make current instance a child of its parent
            self.parent=parent
            
        def __getitem__(self,item):
            # If variable is local, return it
            # Otherwise check the parent for the variable
            if item in self:
                return super(ReportProcessor.Env, self).__getitem__(item)
            return self.parent[item]
            
        def __setitem__(self,item,value):
            # check for variable in parents if not in current environment
            if item not in self:
                p = self.parent
                while True:
                    if item in p:
                        p[item]=value
                        return
                    if isinstance(p,ReportProcessor.Env):
                        p=p.parent
                    else:
                        break
            super(ReportProcessor.Env, self).__setitem__(item,value)

    # external functions
    
    def addSubtractDates(self,env,date,adjustment,days_months_years,operator):
        '''
            Function to manipulate dates
        '''
        # Evaluate the date variable
        date = self.evalVariables(env,date)
        # If the entered date is not already a datetime
        if not isinstance(date,(datetime.datetime,datetime.date)):
            # Convert the submitted variable to a datetime
            date = datetime.datetime.strptime(date,'%m/%d/%Y')
        # Evaluate the adjustment variable and convert to integer
        adjustment = int(self.evalVariables(env,adjustment))
        # Create a dictionary of the type of adjustment and quantity of adjustment
        kwargs = {'{0}'.format(days_months_years):adjustment}
        # Translate the dictionary into a relative delta
        b = relativedelta(**kwargs)
        # If adding the delta, return the addition, otherwise return the subtraction
        if operator=='+':
            return date + b
        else:
            return date - b

    def formatPicture(self,env,url,height,width):
        '''
            function to convert guest picture record to html img tag
        '''
        # Evaluate the url variable
        url = self.evalVariables(env,url)
        # Evaluate the height variable
        height = self.evalVariables(env,height)
        # Evaluate the width variable
        width = self.evalVariables(env,width)
        # Return html img tag
        return u'<img src="%s" height="%s" width="%s"/>' % (url,height,width)
    
    def lastDayActivated(self,env,boolean_list):
        '''
            pass through function to booleanMethods
        '''
        return self.booleanMethods(env,boolean_list,False,True)
    
    def lastDayDeactivated(self,env,boolean_list):
        '''
            pass through function to booleanMethods
        '''
        return self.booleanMethods(env,boolean_list,False,False,True)
    
    def countBooleans(self,env,boolean_list):
        '''
            pass through function to booleanMethods
        '''
        return self.booleanMethods(env,boolean_list)
    
    def countDays(self,env,boolean_list):
        '''
            pass through function to booleanMethods
        '''
        return self.booleanMethods(env,boolean_list,True)
    
    def add(self,env,value1,value2):
        # Eval both variables and return their sum
        return str(float(self.evalVariables(env,value1)) + float(self.evalVariables(env,value2)))

    def subtract(self,env,value1,value2):
        # Eval both variables and return their difference
        return str(float(self.evalVariables(env,value1)) - float(self.evalVariables(env,value2)))


    def today(self,env):
        # Return now as a datetime
        return datetime.datetime.now().date()
        
    def subtractDates(self,env,date1,date2,days_months_years=None):
        '''
            Function to subtract date 1 from date two
        '''
        # evaluate variables
        a = self.evalVariables(env,date1)
        b = self.evalVariables(env,date2)
        # Ensure variables a and b are valid for function
        if not isinstance(a,(datetime.datetime,unicode,datetime.date)) or not isinstance(b,(datetime.datetime,unicode,datetime.date)):
            return ''
        # Convert variables to datetime if unicode
        if isinstance(a,unicode):
            a = parse(a).date()
        if isinstance(b,unicode):
            b = parse(b).date()
        # Ensure variables are the same type
        if not isinstance(b,type(a)) or not isinstance(a,type(b)):
            if isinstance(a,datetime.datetime):
                a = a.date()
            if isinstance(b,datetime.datetime):
                b = b.date()
        # Obtain relative delta between the two variables
        c = relativedelta(a,b)
        # Obtain difference between the two variables
        d = a - b
        # If months or years specified, return same
        if days_months_years == 'months':
            return str(c.years * 12 + c.months)
        if days_months_years == 'years':
            return str(c.years)
        # return number of days
        return str(d.days)
    
    def length(self,env,variable):
        # Eval variable
        variable = self.evalVariables(env,variable)
        # Return length
        return len(variable)
            

    # internal functions
    def beginTable(self,env,comma_separated_headers):
        '''
            Helper function to build html table
        '''
        # Split headers variable into list
        headers = comma_separated_headers.split(',')
        # Start html table
        env['print']('<table><tr>')
        # If headers specified
        if comma_separated_headers:
            # Print each header into a header row
            for i in headers:
                env['print']('<th>'+i+'</th>')
            # Start new row for table
            env['print']('</tr><tr>')

    def endTable(self,env):
        # Close last row and table
        env['print']('</tr></table>')

    def booleanMethods(self,env,boolean_list,count_days=False,last_day_activated=False,last_day_deactivated=False):
        '''
            Function for manipulating timedata boolean list.
                The list should be in the form [[date1,true/false],[date2,true/false],...]
        '''
        # Eval list variable if not already a list
        if not isinstance(boolean_list,list):
            boolean_list = self.evalVariables(env,boolean_list)
        # Make a copy of list to preserve original
        boolean_list = deepcopy(boolean_list)
        # Initialize counter of days active
        count = 1
        # Retrieve first date record from list
        current = boolean_list.pop(0)
        # Initialize turned on date
        checkin_date = current[0]
        # Initialize turned off date
        checkout_date = ""
        # Iterate the list until boolean activated
        while current[1] !="checked='checked'":
            try:
                # Take next record from list
                current = boolean_list.pop(0)
                # Set turned on date
                checkin_date = current[0]
            except IndexError:
                # If the boolean never activates
                return 0
        # Iterate the remaining list after boolean first activates
        for i in boolean_list:
            # If boolean is now inactive and (counting days or wants last deactivation) and previous record was active
            if i[1] == u'' and (count_days or last_day_deactivated) and current[1] =="checked='checked'":
                # increase days active count
                count += int(self.subtractDates(env,i[0],checkin_date))
                # Set deactivated date
                checkout_date = i[0]
            # If boolean is now active and previous record was not active
            if i[1] == "checked='checked'" and current[1]==u'':
                # If not counting days
                if not count_days:
                    # Increase counter
                    count += 1
                # Set activated date
                checkin_date=i[0]
            # Set previous record to current record for next iteration
            current = i
        # If counting days and list ended with active boolean
        if count_days and current[1]=="checked='checked'":
            # Increase count with difference from today to boolean last activated
            count += int(self.subtractDates(env,datetime.datetime.now(),checkin_date))
        # If wanting last day activated
        if last_day_activated:
            # Return date activated
            return checkin_date
        # If wanting last day deactivated
        if last_day_deactivated:
            # Return date deactivated
            return checkout_date
        # Return day count
        return count

    def text(self, env, bold, value):
        '''
            Function to put text into html
        '''
        # If no bold selected
        if bold == 'none':
            # append text to report
            env['print'](value)
        else:
            # Put text in appropriate h tag
            env['print']('<%s>%s</%s>'%(bold,value,bold))

    def set_(self,env,key,value):
        '''
            Function to update environment variable with value
        '''
        # If list element not being updated
        if '::' not in key:
            # Set parent environment variable
            env.parent.parent[key] = self.evalVariables(env,value)
        else:
            # Split update variable into list of steps
            slice_list = key.split('::')
            # Retrieve base variable
            key = slice_list.pop(0)
            # Retrieve last element reference
            end = int(slice_list.pop())
            # Convert intermediary steps into index integers
            slice_list = [int(i) for i in slice_list]
            # Obtain base variable value
            cur_value = self.evalVariables(env,'$'+key)
            # Set walker to entire list
            a = cur_value
            # Walk the intermediary steps
            for i in slice_list:
                # Set walker to list element
                a = a[i]
            # If ending element shorter than last element index
            while len(a)<=end:
                # Increase list length
                a.append('')
            # Set last element to evaluated variable (mutable lists auto update original list)
            a[end] = self.evalVariables(env,value)
            # Set base variable to new list value in parent environment
            env.parent.parent[key] = cur_value
                
    
    def display(self,env,display_value,separator,timeseries, *code):
        '''
            Function to look up variables and append html
        '''
        # Evaluate separator variable
        separator = self.evalVariables(env,separator)
        # If not running a query
        if not code:
            # Evaluate display_value variable
            retval = self.evalVariables(env,display_value)
            # If variable is a datetime
            if isinstance(retval, (datetime.datetime,datetime.date)):
                # Format datetime to string
                env['print'](retval.strftime('%m/%d/%Y'))
            else:
                # Append variable to html
                env['print'](str(retval))
        else:
            # Build filter from variables
            filter = self.buildFilter(env,display_value,timeseries,code)
            # If filter returns more than one record
            if len(filter)>1:
                # Warn user
                env['print']('filter returned more than one value')
            elif len(filter)==1:
                # Use separator to create a string from the filter's list and append
                env['print'](separator.join(filter[0]))
                

    def newline(self, env):
        # Append html new line
        env['print']('<br />')

    def query(self, env, list_type,list_variable,list_range, timeseries, *code):
        '''
            Function to retrive data from database
        '''
        # Retrieve filter results
        a = self.buildFilter(env,list_range,timeseries,code)
        # Save filter results into parent environment
        env.parent.parent[list_variable.replace('!','')] = a

    def if_(self,env,operator,value1,value2,*code):
        '''
            Function to run some code conditionally
        '''
        # Evaluate variables to be compared
        a = self.evalVariables(env,value1)
        b = self.evalVariables(env,value2)
        # Initialize true flag
        true = False
        # Determine type of conditional
        if operator == '=':
            # If equals
            if a==b:
                # Set true flag
                true = True
            elif str(a).isdigit() and str(b).isdigit():
                # Double check not integer comparison
                if int(str(a))==int(str(b)):
                    # Set true flag
                    true = True
        elif operator == 'contains':
            if a in b:
                true = True
        else:
            if str(a).isdigit() and str(b).isdigit():
                a = int(str(a))
                b = int(str(b))
            if operator == '>':
                if a>b:
                    true = True
            elif operator == '<':
                if a<b:
                    true = True
            elif operator == '>=':
                if a>=b:
                    true = True
            elif operator == '<=':
                if a<=b:
                    true = True
            elif operator == '<>':
                if a!=b:
                    true = True
        if code:
            if true:
                # Prepare code for execution
                code=['do']+list(code)
                # Run code
                self.listProcess(self.Env(env), deepcopy(code))
        else:
            return true

    def list_(self, env, list_type,list_variable,row_items,row_num,row_separator,list_range, timeseries, *code):
        '''
            Function for iterating over lists or ranges
        '''
        # Evaluate row separator
        row_separator = self.evalVariables(env,row_separator)
        # Copy code to preserve original
        c = list(code)
        # If iterating range
        if list_type == u'numbers':
            # Split start and stop in two
            start,stop = list_range.split(':')
            # Evaluate start and stop if variables
            if '$' in start:
                start = int(self.evalVariables(env,start))-1
            if '$' in stop:
                stop = int(self.evalVariables(env,stop))-1
            # Build generator to iterate
            a = xrange(int(start), int(stop)+1)
        else:
            # build filter to iterate
            a = self.buildFilter(env,list_range,timeseries,code)
            # Remove filter from code
            while c[0][0]=='and' or c[0][0]=='or' or c[0][0]=='extrafield':
                c.pop(0)
                if c == []:
                    break
        # Prepare code for execution
        c.insert(0, 'do')
        # Initialize row item counter
        rowcount = 1
        # Initialize Page counter
        pagecount = 2
        # Iterate over range
        for i in a:
            # If walker should be global
            if '!' in list_variable:
                # Store walker in environment parent
                env.parent.parent[list_variable.replace('!','')] = i
            else:
                # Store walker in environment
                env[list_variable] = i
            # Execute code
            self.listProcess(self.Env(env), deepcopy(c))
            # If number of items iterated is multiple of items per row
            if rowcount % int(row_items) == 0:
                # If number of rows per page specified
                if row_num:
                    # If number of rows multiple of number of rows per page
                    if pagecount % int(row_num) == 0:
                        # Reset page counter
                        pagecount = 0
                        # Force pagebreak after this row
                        env['print'](row_separator[:-1] + ' style="page-break-after: always"' + row_separator[-1:])
                    else:
                        # Start new row
                        env['print'](row_separator)
                else:
                    # Start new row
                    env['print'](row_separator)
                # Reset item per row counter
                rowcount = 0
                # Increase row per page counter
                pagecount += 1
            # Increase Item per row counter
            rowcount += 1

    def count(self,env,return_field,timeseries,*code):
        '''
            Function to count number of items returned by filter
        '''
        # Retrieve filter
        filter = self.buildFilter(env,return_field,timeseries,code)
        # Update html with number of items returned
        env['print'](str(len(filter)))

    def sum(self,env,return_field,timeseries,*code):
        '''
            Function to return sum of all items in filter
        '''
        # Retrieve filter
        filter = self.buildFilter(env,return_field,timeseries,code)
        # Initialize sum
        retval = 0.0
        # Iterate filter
        for i in filter:
            # Iterate values in each element
            for a in i:
                # Add to sum if valid type
                try:
                    retval += float(a)
                except (TypeError, ValueError):
                    pass
        # Enter sum in html
        env['print'](str(retval))

    def function(self, env, function, return_variable, *args):
        # pass through function to specific selected functions
        self.set_(env,return_variable.replace('$',''),self.functions[function](env,*args))

    # system functions

    def do(self, env, *args):
        '''
            Function to catch code and process it
        '''
        ret = ''
        for arg in args:
            ret = self.listProcess(self.Env(env), arg)
        return ret

    def distinct(self,list_):
        '''
            Function to remove duplicate elements from lists
        '''
        retval = []
        for i in list_:
            if i not in retval:
                retval.append(i)
        return retval

    def buildFilter(self,env,return_field,timeseries,code):
        '''
            Function to retrieve data from database
        '''
        # Initialize date_filters list
        # date_filters = [date1, ...]
        date_filters = []
        # If filtering on variable and variable has sub elements
        if '::' in return_field:
            # Split return field into list
            a = return_field.split('::')
            # Iterate list and eval variables
            for i in range(1,len(a)):
                if '$' in a[i]:
                    a[i]=str(self.evalVariables(env,a[i]))
            # Return updated list to string
            return_field = '::'.join(a)
        # Place initial return_field variable into list with timeseries flag
        # return_field_list = [[field,timeseries],...]
        return_field_list = [[return_field,timeseries]]
        # Initialize filter
        # filter = [["and/or",operator,value1,value2,timeseries],...]
        filter = []
        # if filter has criterion
        if code:
            # convert code list to generator
            tracker = iter(code)
            # set walker to first element
            current = tracker.next()
            # Iterate over filter criterion
            while current[0]=='and' or current[0]=='or' or current[0]=='extrafield':
                # If filter should return another field
                if current[0]=='extrafield':
                    # If filtering on variable and variable has sub elements
                    if '::' in current[1]:
                        # Split current return field into list
                        a = current[1].split('::')
                        # Iterate list
                        for i in range(1,len(a)):
                            # If variable
                            if '$' in a[i]:
                                # Evaluate variable and store in list
                                a[i]=str(self.evalVariables(env,a[i]))
                        # Return updated list to string
                        current[1] = '::'.join(a)
                    # Put evaluated extra field into return list with timeseries flag
                    return_field_list.append([current[1],current[2]])
                elif 'date.' in current[3]:
                    # If filtering for date
                    # Put date in date filters
                    date_filters.append(current)
                else:
                    # Put filter in filter list
                    filter.append(current)
                try:
                    # Get next criterion
                    current = tracker.next()
                except StopIteration:
                    # If no more elements to iterate
                    break
        # If filtering against variable
        if '$' in return_field:
            # Initialize dictionary of fields
            # field_dict = {'field':[[value1,value2...],...]...}
            field_dict = {}
            # If no criterion
            if filter==[]:
                # Iterate list of fields to return
                for i in return_field_list:
                    # Split each return field into list
                    a = i[0].split('::')
                    # If return field has sub elements
                    if len(a)>1:
                        # field key is base variable through pentultimate element
                        k = '||'.join(a[:-1]).replace('$','').replace(' ','')
                    else:
                        # Key is field name
                        k = a[0].replace('$','').replace(' ','')
                    # If each field not already in field dict
                    if k not in field_dict.keys():
                        # evaluate variable
                        v = self.evalVariables(env,'$'+k.replace('||','::'))
                        # If value has a length
                        if len(v)>0:
                            # If value first element not a list (value is not a list of lists)
                            if not isinstance(v[0],list):
                                # Make value a list
                                v = [v]
                        # Set value of field in dictionary
                        field_dict[k]=v
            else:
                # Set flag for first filter
                first_filter = True
                # Iterate criteria
                for i in filter:
                    # Retrieve variable being filtered against
                    data = self.evalVariables(env,i[3].split('::')[0])
                    # Evaluate value being sought
                    value = self.evalVariables(env,i[2])
                    # Initialize holding dictionary for items matching criteria
                    # holdingdict = {field_name: [[data,data,data,...],...}
                    holdingdict = {}
                    # Walk through each record in variable being filtered
                    for a in data:
                        # Set found flag
                        found = False
                        # Retreive comparison value from the sub element of the current record
                        comparator = a[int(self.evalVariables(env,i[3].split('::')[1]))]
                        # run comparison
                        # compare values
                        found = self.if_(env,i[1],comparator,value)
                        if found:
                            # Initialize holding dict list for field
                            holdingdict[i[3].replace('$','').replace(' ','').split('::')[0]] = holdingdict.get(i[3].replace('$','').replace(' ','').split('::')[0],[])
                            # If this record is not already in the holding dict list for this field
                            if a not in holdingdict[i[3].replace('$','').replace(' ','').split('::')[0]]:
                                # Append this record to the holding dict list for this field
                                holdingdict[i[3].replace('$','').replace(' ','').split('::')[0]].append(a)
                    # Iterate through the key, value pairs of the holding dict
                    for k,v in holdingdict.iteritems():
                        # Initialize the field_dict list for the field
                        field_dict[k] = field_dict.get(k,[])
                        # If filter is an "or"
                        if i[0]=='or':
                            # Add all records to existing field list
                            field_dict[k] = field_dict[k] + v
                        else:
                            # If an 'and' filter
                            # If no list for the current field and this is the first filter
                            if field_dict[k] == [] and first_filter:
                                # Set field list equal to the current record list
                                field_dict[k] = v
                            else:
                                # Set field list equal to the intersection of previous records and current records
                                field_dict[k] = self.listToSet(set(self.listToSet(v)) & set(self.listToSet(field_dict[k])),True)
                    # Set first_filter flag
                    first_filter = False
            # Initialize return list
            # retval = [[[record1],[record2],...],[[record1],[record2],...]]
            retval = []
            # Iterate through the key, value pairs of field_dict
            for k,v in field_dict.iteritems():
                # Iterate through the records of each field
                for i in v:
                    # Initialize the list for records
                    # return_list = [[record1],[record2],...]
                    return_list = []
                    # Iterate through the list of fields to return
                    for a in return_field_list:
                        # Split the field into a list
                        ak = a[0].split('::')
                        # If field has sub elements
                        if len(ak)>1:
                            # Retrieve Last index
                            ai = ak[-1]
                            # Put base variable through pentultimate element back into field key
                            ak = '||'.join(ak[:-1]).replace('$','').replace(' ','')
                            # If current field is matches the just created key
                            if k == ak:
                                # Append records into return list
                                return_list.append(i[int(ai)])
                        else:
                            # If field has no sub elements
                            # Append records into return list
                            return_list = i
                    # Append return list into retval
                    retval.append(return_list)
            # Return filter results
            return retval


        # If filtering against the database
        # If no criteria
        if filter==[]:
            # Return all guests
            guest_list = [i for i in Guest.objects.all() if testPermission(i,env['user'])]
        else:
            # Initialize guest list
            # guest_list = [guest1,guest2,...]
            guest_list = []
            # Order filter ands then ors
            filter = sorted(filter)
            # Iterate over filters
            for i in filter:
                # Initialize equals kwargs
                # eqkwargs={field:value,...}
                eqkwargs = {}
                # Initialize not equals kwargs
                # nekwargs={field:value,...}
                nekwargs = {}
                # If filtering against a field
                if 'field.' in i[3]:
                    # place field name in filter criteria
                    eqkwargs['field__name']=i[3].split('field.')[1]
                    # Translate filter comparator into django filter format
                    operator = 'value__%s'%self.filter_dict[i[1]]
                    # If filtering for not equal
                    if i[1] == '<>':
                        # Append operator into nekwargs
                        nekwargs[operator]=self.evalVariables(env,i[2]).replace('True',"checked='checked'")
                    else:
                        # Append operator into eqkwargs
                        eqkwargs[operator]=self.evalVariables(env,i[2]).replace('True',"checked='checked'")
                    # If filtering on timeseries and dates specified
                    if i[4]==u'on' and date_filters!=[]:
                        # Iterate through date filters
                        for a in date_filters:
                            # Add to eqkwargs date filter requirements
                            eqkwargs.update({'date__{0}'.format(self.filter_dict[a[1]]):self.evalVariables(env,a[2])})
                    # run filter based on timeseries (GuestTimeData vs GuestData) and kwargs; return list of guestids who fit critera
                    current_guest_list = self.filter_dict['field'][i[4]].objects.filter(**eqkwargs).exclude(**nekwargs).values_list('guest',flat=True)
                else:
                    # If filtering on guests
                    # initialize operator with first guest attribute
                    operator = '%s__'%i[3].split('guest.')[1]
                    # If filtering on guest program
                    if i[3].split('guest.')[1]=='program':
                        # Add name to operator (results in operator == "program__name__")
                        operator += 'name__'
                    # Add django filter comparator
                    operator = operator + self.filter_dict[i[1]]
                    # If filtering on not equal
                    if i[1] == '<>':
                        # Append filter to not equal kwargs
                        nekwargs[operator]=self.evalVariables(env,i[2]).replace('True',"checked='checked'")
                    else:
                        # Append filter to equal kwargs
                        eqkwargs[operator]=self.evalVariables(env,i[2]).replace('True',"checked='checked'")
                    # Run django filter returning list of guest ids where guest matches criteria
                    current_guest_list = list(Guest.objects.filter(**eqkwargs).exclude(**nekwargs).distinct().values_list('id',flat=True))
                # If criteria is "and"
                if i[0]=='and':
                    # If no guests in list
                    if guest_list==[]:
                        # Guest list is currently returned list
                        guest_list = set(current_guest_list)
                    else:
                        # Guest list is the intersection of current list and previous list
                        guest_list = guest_list & set(current_guest_list)
                else:
                    # If criteria is "or"
                    # If guest list is a set
                    if isinstance(guest_list,set):
                        # Convert to list
                        guest_list = list(guest_list)
                    # If current guest list is not a list
                    if not isinstance(current_guest_list,list):
                        # Convert to list
                        current_guest_list = list(current_guest_list)
                    # Merge guest list and current guest list deduplicating
                    guest_list = self.distinct(guest_list + current_guest_list)
        # Convert list of guest ids to list of guest objects
        guest_list = list(Guest.objects.filter(id__in=list(guest_list)).distinct())
        # Initialize Retval
        # retval = [[[record1],[record2],...],[[record1],[record2],...],...]
        retval = []
        # Initialize holding
        # holding = {guest:[field1,field2,...],...}
        holding = {}
        # Iterate over return field list
        for i in return_field_list:
            # Split table and field
            table,field = i[0].split('.')
            # If table is guest
            if 'guest' == table:
                # Iterate over the list of guest objects
                for a in guest_list:
                    # Initialize holding for this guest
                    holding[a] = holding.get(a,[])
                    # Append the attribute being requested from the current guest
                    if field=='image_tag':
                        holding[a].append(self.safegetattr(a,field)())
                    elif field=='picture':
                        holding[a].append(self.safegetattr(a,field).url)
                    elif field=='program':
                        holding[a].append('|'.join([i.name for i in self.safegetattr(a,field).all()]))
                    else:
                        holding[a].append(str(self.safegetattr(a,field)))
            else:
                # If table is field
                # Retrieve filter from database where field name matches and guest is in guest list
                filter = self.filter_dict['field'][i[1]].objects.filter(guest__in=guest_list,field__name=field).distinct()
                # Make a copy of guest list
                guest_list_copy = deepcopy(guest_list)
                # Initialize timeseries agregation
                # timeseries_agregation = {guest:[[date,value],[date,value],...],...}
                timeseries_agregation = {}
                # If filtering against timeseries
                if i[1] == u'on':
                    # Order filter by date
                    filter = filter.order_by('date')
                    # Iterate through records
                    for a in filter:
                        # Initialize timeseries agregation for specific guest
                        timeseries_agregation[a.guest] = timeseries_agregation.get(a.guest,[])
                        # Append current record into timeseries agregation
                        timeseries_agregation[a.guest].append([a.date,a.value])
                else:
                    # If not filtering on timeseries
                    # Iterate through records
                    for a in filter:
                        # Initialize holding for specific guest
                        holding[a.guest] = holding.get(a.guest,[])
                        # Append value to holding
                        holding[a.guest].append(a.value)
                        # Remove guest from list
                        guest_list_copy.pop(guest_list_copy.index(a.guest))
                # Iterate remaining guests in list copy
                for a in guest_list_copy:
                    # Initialize holding for specific guest (will be all guests if not filtering on timeseries)
                    holding[a] = holding.get(a,[])
                    # Append timeseries agregation or blank
                    holding[a].append(timeseries_agregation.get(a,''))
        # Iterate through guests in holding
        for i in holding.keys():
            # Add to return each guest's records
            retval.append(holding[i])
        try:
            # Try sorting on lower case the first element
            return sorted(retval, key=lambda s: s[0].lower())
        except AttributeError:
            # Other wise just sort list
            return sorted(retval)
    
    def listToSet(self,_list,rev=False):
        '''
            Function to convert list and sublists to or from set
        '''
        # Copy list
        _list = deepcopy(_list)
        # If converting to set
        if not rev:
            # Iterate list
            for i in range(0,len(_list)):
                # If element is list
                if isinstance(_list[i],list):
                    # Convert element to set
                    _list[i] = self.listToSet(_list[i])
            # Return tuple of list copy
            return tuple(_list)
        # If reverting to list
        # convert outer tuple to list
        _list = list(_list)
        # Iterate newly converted list
        for i in range(0,len(_list)):
            # If element is tuple
            if isinstance(_list[i],tuple):
                # Convert element to list
                _list[i] = self.listToSet(_list[i],True)
        # return list
        return _list

    def safegetattr(self,obj,attr):
        '''
            Function to limit user access to attributes
        '''
        if not attr.startswith('__'):
            return getattr(obj,attr)
        return ''

    def evalVariables(self,env,variable):
        '''
            Function to convert variable names into values
        '''
        # If variable is string or unicode
        if isinstance(variable,(str,unicode)):
            # If actual variable
            if '$' in variable:
                # Request from env value of variable base name
                var = env[variable.replace('$','').replace(' ','').split('::')[0]]
                # If variable has sub elements
                if '::' in variable:
                    # Get element list from variable
                    subs_list = variable.split('::')[1:]
                    # Iterate over sub element list
                    for i in subs_list:
                        # Evaluate sub element index
                        index = int(self.evalVariables(env,i))
                        # If current list longer than index
                        if len(var)>=index+1:
                            # Set current list to sub element
                            var = var[index]
                        else:
                            # Set current list blank
                            var = ''
                    return var
                else:
                    return var
        # If not variable
        return variable

    @staticmethod
    def preProcessReport(code,first_indent=None):
        '''
            Method to translate report builder list into processable list
        '''
        # List of words indicating agregate code
        indent_list = ['list', 'sum', 'count', 'display', 'query', 'if']
        # Initialize return
        # retval = [[instruction1],[instruction2],...]
        retval = []
        # Initialize user defined variables
        # user_variables = [variable name1, variable name2,...]
        user_variables = []
        # Iterate over the entire list
        while True:
            try:
                # Get first remaining element of code list
                line = code.pop(0)
                # If closing an indent
                if line[0] == 'end':
                    # If no indent to close
                    if not first_indent:
                        # Warn user
                        return 'bad code',[]
                    # Return current code
                    return retval,user_variables
                # If opening an indent
                if line[0] in indent_list:
                    # Process remaining code into block
                    sub_list,sub_user_variables = ReportProcessor.preProcessReport(code,line)
                    # If indented code not valid
                    if sub_list == 'bad code':
                        # Warn user
                        return 'bad code',[]
                    # Add code block to current instruction
                    line.extend(sub_list)
                    # Add current instruction to return value
                    retval.append(line)
                    # Add any user variables to global list
                    user_variables = user_variables + sub_user_variables
                elif line[0] == 'user input':
                    # If user input requested, add to list of user variables
                    user_variables.append(line[1])
                else:
                    # Add current instructions to return value
                    retval.append(line)
            except IndexError:
                # If code list is empty
                # If number of ends does not match number of indents
                if first_indent:
                    # Notify user
                    return 'bad code',[]
                break
        return retval,user_variables
    
    def listProcess(self, env, code):
        '''
            Method to process code
        '''
        # If no environment supplied
        if env is None:
            # Create environment
            env={}
        # If code not executable
        if not isinstance(code,list) or not code:
            # Return the value
            return code
        # Pull first instruction
        first = code.pop(0)
        # If first code is code
        if isinstance(first,list):
            # Set function the outcome of processing code
            function = self.listProcess(self.Env(env), first)
        else:
            # Set function
            function = env[first]
        # Execute function
        return function(self.Env(env), *code)


# Instantiate ReportProcessor
report_processor = ReportProcessor()


# Common Methods

def interactiveConsole(a,b=None):
    '''
        Useful function for debugging
        Placing interactiveConsole(locals(),globals()) into code will
        drop into an interactive console when run
    '''
    import code
    d = {}
    if b:
        d.update(b)
    d.update(a)
    c=code.InteractiveConsole(locals=d)
    c.interact()

def readableList(value):
    '''
        Function to print lists to console which are multiline and readable
    '''
    value = iter(json.dumps(value)+' ')
    retval = ''
    indent = 0
    i = value.next()
    increase = True
    while True:
        ahead = ''
        try:
            if i=='[':
                increase = True
                indent+=1
                retval = retval + '\n' + ' ' * indent + i
            elif i==']':
                indent -=1
                ahead = value.next()
                if ahead==',' and increase:
                    retval = retval + i
                else:
                    if increase:
                        indent +=1
                        increase = False
                        retval = retval + i
                    else:
                        retval = retval + '\n' + ' ' * indent + i
                        if ahead==',':
                            indent -=1
            else:
                retval = retval + i
            if ahead:
                i=ahead
            else:
                i = value.next()
        except StopIteration:
            break
    print retval

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
    # Order field_list by "order"
    if not isinstance(field_list,list):
        field_list = field_list.order_by('order')
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
    # return html string of form for display in template.
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
                                 if i.field_type=='title' else '<ul><li>Field %s prerequisites not satisfied</li></ul>'%i.name for i in field_list if testPermission(i,user)
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

@login_required
def quickfilter(request):
    '''
        View for executing one filter against the database
        NOT YET IMPLEMENTED
    '''
    context=baseContext(request)
    if request.POST:
        pass
    context.update({'output':'1'})
    return render(request,'guestmanagement/quickfilter.html',context)
    

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
        if target_type != 'guest' and target_type != 'report':
            if request.user not in target_object.owner.all():
                return beGone("You may not edit other people's content")
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
        hashpassword=True
        if target_type=='guest' and not request.POST.get('password',''):
            request.POST['password']=target_instance.password
            hashpassword=False
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
                if hashpassword:
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
                # Turn POST into standard dictionary
                request_dict = dict(request.POST)
                # Initialize report code
                report_code = []
                # Initialize row counter
                report_row_counter = '0'
                # Process post dictionary to align instructions by "row" and "column"
                # Post values for the code will have the name "code[rownum]-[colnum]"
                # Continue processing rows until no counter exists
                while isinstance(report_row_counter, str):
                    # Initialize each instruction
                    report_code_row = []
                    # Initialize column counter
                    report_col_counter = '0'
                    # Continue processing columns until no counter exists
                    while isinstance(report_col_counter,str):
                        # Multiple values for a name means a checkbox is active
                        if len(request_dict['code'+report_row_counter+'-'+report_col_counter])>1:
                            # Set checkbox value to on
                            request_dict['code'+report_row_counter+'-'+report_col_counter] = [u'on']
                        # Add column value to row list
                        report_code_row.append(request_dict['code'+report_row_counter+'-'+report_col_counter][0])
                        # Initialize found next flag
                        found_next = False
                        # Iterate key, value pairs in the post dictionary
                        for k,v in request_dict.iteritems():
                            # if this row name plus the next column is in the post dictionary
                            if k.find('code'+report_row_counter+'-'+str(int(report_col_counter)+1)) > -1:
                                # Set found next flag
                                found_next = True
                                # Skip remaining searching
                                break
                        # If another column is found
                        if found_next:
                            # Set column counter to next column number
                            report_col_counter = str(int(report_col_counter)+1)
                        else:
                            # Otherwise remove column counter (ends while loop)
                            report_col_counter = False
                    
                    # If row was not blank in report builder
                    if report_code_row[0] != u'':
                        # Add row to code list
                        report_code.append(report_code_row)
                    # Search for next row
                    # Initialize found next flag
                    found_next = False
                    # Iterate key, value pairs in post dictionary
                    for k,v in request_dict.iteritems():
                        # If code + next row number found in key
                        if k.find('code'+str(int(report_row_counter)+1)) > -1:
                            # Set found next flag
                            found_next = True
                            # Skip remaining search
                            break
                    # if found next row
                    if found_next:
                        # Set row counter to next row number
                        report_row_counter = str(int(report_row_counter)+1)
                    else:
                        # Remove row counter (ends while loop)
                        report_row_counter = False
                # Send formed code list to report processor for compiling
                processed_code,user_variables = report_processor.preProcessReport([[a for a in i] for i in report_code])
                # If an error in code
                if processed_code == 'bad code':
                    # Warn User
                    messages.add_message(request, messages.INFO, '%s Contains Invalid Structure'%myobject.name)
                # Store compiled code and uncompiled code into report code object
                myobject.code = json.dumps([processed_code,report_code])
                # Store user variables into report code object
                myobject.variables = json.dumps(user_variables)
                # Save report code object
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
            context.update({'loaded_report':json.dumps(json.loads(target_instance.code)[1])})
        # Pull all the forms from the database which the user is allowed to see
        all_forms_list = [i for i in Form.objects.all() if testPermission(i,request.user)]
        # Pull all fields from the database which the user is allowed to see
        all_field_dict = {i.name:[[a.name.replace('(',''),a.field_type] for a in Field.objects.filter(form=i).distinct() if testPermission(a,request.user)] for i in all_forms_list}
        all_field_dict.update({'date':[['date','date']],'guest':[['id','id'],['first_name','text_field'],['middle_name','text_field'],['last_name','text_field'],['ssn','text_field'],['program','list'],['picture','url'],['image_tag','picture']]})
        # Put the list of fields and forms into the context
        context.update({'all_forms_list':all_forms_list,'all_field_dict':json.dumps(all_field_dict),'available_functions':json.dumps([[i,list(report_processor.functions[i].func_code.co_varnames)[:report_processor.functions[i].func_code.co_argcount]] for i in report_processor.functions.keys()])})
        # Put helper variables in context
        context.update({'helper_variables':json.dumps(report_processor.tableVariables.keys())})
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
                                a.value = a.value.strip()
                                if not a.value:
                                    a.value=request.POST.get(i.name)
                                elif a.value in request.POST.get(i.name,''):
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
            # Create form
            while not form:
                try:
                    # Try building form
                    form=createForm(field_list,request.user,second_object=second_object)
                except MultipleObjectsReturned, e:
                    # If guest has more than one datapoint for a field
                    # Retrieve all data
                    b=GuestData.objects.filter(guest=second_object)
                    # Initialize holding dict
                    c={}
                    # Iterate through data
                    for i in b:
                        # If data not in holding dict
                        if not c.get(i.field.name,False):
                            # Update holding dict
                            c[i.field.name]=i
                        elif c[i.field.name].value==i.value:
                            # If data already in holding dict and values match
                            # Delete second data point
                            i.delete()
                        else:
                            # If data already in holding dict and values do not match
                            # Reraise exception
                            raise e
                    # Reloop while loop to build form
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
    if target_type == 'report':
        # Add user variables for display on report view
        context.update({'variables':json.loads(target_object.variables)})
    return render(request,'guestmanagement/view.html',context)

def runreport(request,report_id):
    '''
    View for executing and displaying reports
    '''
    context=baseContext(request)
    # Retrieve compiled code from report code object
    report_code = json.loads(ReportCode.objects.get(pk=report_id).code)[0]
    # Create a file like buffer
    output = StringIO()
    # Initialize environment
    env = {'print':output.write,'user':request.user}
    # Add user defined variables to environment
    for k,v in request.GET.iteritems():
        env[k.replace('variable__','')]=v
    # Add external functions, helper variables, internal functions to report environment
    env.update(report_processor.functions)
    env.update(report_processor.tableVariables)
    env.update(report_processor._functions)
    try:
        # Run Report
        success = report_processor.listProcess(env, ['do']+report_code)
    except:
        # Display errors
        env['print']('<pre>')
        env['print'](traceback.format_exc()+'\n-----------------------\n')
        env['print'](str(report_code))
        env['print']('</pre>')
    # Display results
    context.update({'report':mark_safe(output.getvalue())})
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
    # Test permission to change past forms
    if not request.user.has_perm('guestmanagement.change_guesttimedata'):
        return beGone('guestmanagement.change_guesttimedata')
    # Retrieve guest object
    target_guest = Guest.objects.get(pk=target_guest)
    # Verify permission to change guest
    if not testPermission(target_guest,request.user):
        return beGone('May not access guest')
    # Retrieve form object
    target_form = Form.objects.get(pk=target_form)
    # Test permission to view form
    if not testPermission(target_form,request.user):
        return beGone('May not access form')
    # Set base context
    context=baseContext(request)
    # Retrieve field list for form
    target_field_list = Field.objects.filter(form=target_form,time_series=True).order_by('order')
    # Test permissions on fields
    target_field_list = [i for i in target_field_list if testPermission(i,request.user)]
    # Initialize link list as flag
    context.update({'link_list':'no links'})
    # If no date to change selected
    if not target_guesttimedata:
        # Initialize link list
        # link_list = [[readable date,id],...]
        link_list = []
        # Initialize readable dates
        # readable_dates = [date,...]
        readable_dates = []
        # Retrieve list of guesttimedata for fields
        guesttimedata_list = GuestTimeData.objects.filter(guest=target_guest,field__in=target_field_list).distinct().order_by('-date')
        # Iterate through guest time datas
        for i in guesttimedata_list:
            # If date not already in readable dates
            if i.date.strftime('%Y/%m/%d %H:%M:%S') not in readable_dates:
                # Append date and id to link list
                link_list.append([i.date.strftime('%Y/%m/%d %H:%M:%S'),i.id])
                # Append date to readable dates
                readable_dates.append(i.date.strftime('%Y/%m/%d %H:%M:%S'))
        # Put link list into context
        context.update({'link_list':link_list})
    else:
        # If date to change selected
        # If posting changes
        if request.POST:
            # Retrieve affected guest time data
            target_guesttimedata = GuestTimeData.objects.get(pk=target_guesttimedata)
            # Retrieve all guest time data from that date
            guesttimedata_list = GuestTimeData.objects.filter(date=target_guesttimedata.date,guest=target_guesttimedata.guest,field__form=target_guesttimedata.field.form).distinct()
            # If user trying to delete data
            if request.POST.get('delete_%s'%target_form.name):
                # If not allowed to delete
                if not request.user.has_perm('guestmanagement.delete_guesttimedata'):
                    return beGone('guestmanagement.change_guesttimedata')
                # Delete data
                for i in guesttimedata_list:
                    i.delete()
                # Notify user
                messages.add_message(request, messages.INFO, 'Form Deleted')
                return redirect('/guestmanagement/view/guest/%s/'%target_guest.id)
            # Get date from current record
            new_date = target_guesttimedata.date.strftime('%m/%d/%Y ')
            # If change date submitted
            if request.POST.get('changeDate'):
                # Update date
                new_date = request.POST.get('changeDate') + ' '
            # Get time from current record
            new_time = target_guesttimedata.date.strftime('%H:%M %p')
            # If chage time submitted
            if request.POST.get('changeTime'):
                # Update time
                new_time = request.POST.get('changeTime')
            # Append time to date
            new_date = new_date + new_time
            # Convert date to datetime
            new_date = datetime.datetime.strptime(new_date,'%m/%d/%Y %H:%M %p')
            # Retrieve potential conflicts
            test_list = GuestTimeData.objects.filter(guest=target_guest,date=new_date)
            # If potential conflicts
            if len(test_list)>0:
                # Warn user
                messages.add_message(request, messages.INFO, 'Form already exists in selected date/time slot')
                # Return to guest view
                return redirect('/guestmanagement/view/guest/%s/'%target_guest.id)
            # Iterate affected guest time datas
            for i in guesttimedata_list:
                # Set date
                i.date = new_date
                # Set value
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
            # If no update being posted
            # Create form
            form = createForm(target_field_list,request.user,second_object=target_guest)
            context.update({'form':form})
    # Serve it up
    context.update({'target_guest':target_guest, 'target_form':target_form})
    return render(request,'guestmanagement/edit.html',context)






















