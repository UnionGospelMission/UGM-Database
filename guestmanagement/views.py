from random import randint
import hashlib,datetime,calendar,json,os,re, itertools,inspect,shutil
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.context_processors import csrf
from django.utils.safestring import mark_safe
from django.utils.functional import SimpleLazyObject
from django.contrib import messages,auth
from django.db.models import Q,Max,Count
from django.db.models.query import QuerySet,ValuesListQuerySet
from django.contrib.auth.models import User
from django.forms.formsets import formset_factory
from guestmanagement.models import Guest,GuestmanagementUserSettings,Program,Form,Field,Prerequisite,GuestData,GuestFormsCompleted,Permission,GuestTimeData,Report,Attachment,DynamicFilePermissions,User_Permission_Setting,QuickFilter,ProgramHistory
from forms import NewGuestForm,NewProgramForm,NewFormForm,NewFieldForm,NewPrerequisiteForm,NewPermissionsForm,NewReportForm,NewAttachmentForm,NewUser_Permission_Setting
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from cStringIO import StringIO
from copy import deepcopy
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
import traceback
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from collections import namedtuple
from HTMLParser import HTMLParser
from django.core.files.temp import NamedTemporaryFile
from UGM_Database import settings

from Sandbox.Sandbox import Sandbox
from Sandbox.Function import Function
from Sandbox.SecureDict import SecureDict

# Common reference dictionaries


target_type_dict = {# Reference dictionary for matching the correct new form to the correct model and record the "primary key"
                    #'target_type':[model_form, model, 'search_field'],
                    'guest':[NewGuestForm,Guest,'id'],
                    'program':[NewProgramForm,Program,'name'],
                    'form':[NewFormForm,Form,'name'],
                    'field':[NewFieldForm,Field,'name'],
                    'prerequisite':[NewPrerequisiteForm,Prerequisite,'name'],
                    'permission':[NewPermissionsForm,Permission,'name'],
                    'report':[NewReportForm,Report,'name'],
                    'attachment':[NewAttachmentForm,Attachment,'name'],
                    'user_permission_setting':[NewUser_Permission_Setting,User_Permission_Setting,'user'],
                }





#Report method class



class ReportProcessor():
    '''
        Main class for handling preparing and running reports
    '''
    def __init__(self):
        ### Helper variables for creating tables
        self.tableVariables = { 'table_new_row':'</tr><tr>',
                                'table_new_row_with_break':'</tr><tr><td></td></tr><tr>',
                                'table_new_cell':'</td><td>',
                                'table_open_cell':'<td>',
                                'table_close_cell':'</td>',
                                'table_open_row':'<tr>',
                                'table_close_row':'</tr>',
        }
        ### External functions (found on the report builder when "function" is selected)
        self.functions = {  'add':self.add,
                            'subtract':self.subtract,
                            'today': self.today,
                            'subtract_dates': self.subtractDates,
                            'length': self.length,
                            'count_bool_times_activated':self.countBooleans,
                            'count_bool_days_active':self.countDays,
                            'last_day_bool_activated':self.lastDayActivated,
                            'last_day_bool_deactivated':self.lastDayDeactivated,
                            'first_day_bool_activated':self.firstDayActivated,
                            'bool_active_during':self.boolActiveDuring,
                            'format_picture':self.formatPicture,
                            'add_subtract_dates':self.addSubtractDates,
                            'anniversary_check':self.checkAnniversaries,
                            'merge_lists':self.mergeLists,
                            'append_to_list':self.appendList,
                            'concatenate':self.concatenateStrings,
                            'to string':self.toString,
                            'divide':self.divideValues,
                            'multiply':self.multiplyValues,
                            'python':self.python,
                            'get_value_on_day':self.valueOnDay,
                            'filter_values_on_day':self.filterValuesOnDay,
        }
        ### Internal functions (found on the report builder in each line's dropdown)
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
                            'link':self.link,
                            'calendar':self.makeCalendar,
                            'section break':self.Pass,
                            'comment':self.Pass,
        }
        ### Dictionary to convert report builder operators to django query filters
        self.filter_dict = {
                            '=':'exact',
                            '>':'gt',
                            '<':'lt',
                            '>=':'gte',
                            '<=':'lte',
                            '<>':'exact',
                            'in':'in',
                            'contains':'icontains',
                            'only contains':'icontains',
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
            if not isinstance(parent,ReportProcessor.Env):
                for k,v in parent.iteritems():
                    self[k]=v
            else:
                self.parent=parent
                self.parent.children.append(self)
            self.children = []
            
        def __getitem__(self,item):
            # If variable is local, return it
            # Otherwise check the parent for the variable
            if item in self:
                return super(ReportProcessor.Env, self).__getitem__(item)
            try:
                return self.parent[item]
            except AttributeError:
                raise Exception('Undefined Variable: %s'%item)
            
        def __setitem__(self,item,value):
            # check for variable in parents if not in current environment
            if hasattr(self,'parent') and item not in self:
                p = self
                while True:
                    if item in p:
                        p[item]=value
                        return
                    if hasattr(p,'parent'):
                        p=p.parent
                    else:
                        break
            super(ReportProcessor.Env, self).__setitem__(item,value)
            
        def __get_global__(self,item,alternative=None):
            p=self
            while True:
                if hasattr(p,'parent') and p.parent:
                    p=p.parent
                else:
                    break
            try:
                return p[item]
            except KeyError as e:
                if alternative is not None:
                    return alternative
                raise e
            
        def __set_global__(self,item,value):
            p=self
            while True:
                if hasattr(p,'parent') and p.parent:
                    p=p.parent
                else:
                    break
            p[item]=value
            
        def __get_variable_state__(self):
            retval = {}
            a = self
            while hasattr(a,'parent'):
                a = a.parent
            retval.update(a)
            while hasattr(a,'children') and len(a.children)>0:
                a = a.children[-1]
                retval.update(a)
            return retval
                

    ### external functions
    def filterValuesOnDay(self,env,date,field,value,return_guest_ids=None):
        if env != None:
            date = self.evalVariables(env,date)
            field = self.evalVariables(env,field)
            value = self.evalVariables(env,value)
        if not isinstance(date,datetime.datetime):
            date = parse(date)
        field = field.split('.',1)
        if field[0]=='field':
            field = field[1]
        elif field[0]=='guest':
            if field[1]!='program':
                z=Guest.objects.filter(**{field[1]:value})
                if return_guest_ids:
                    return z.values_list(field[1],flat=True)
                return z
            else:
                q='''SELECT a.* FROM (
                                    (  
                                      (SELECT id as phid,* FROM guestmanagement_programhistory WHERE date <= %s) AS a
                                      INNER JOIN
                                      (SELECT guest_id AS tid, MAX(date) AS mdate FROM
                                           (SELECT * FROM guestmanagement_programhistory WHERE date<=%s) AS c
                                       GROUP BY tid  
                                      ) AS d  
                                      ON a.guest_id=d.tid AND a.date=d.mdate
                                    ) AS a    
                                    INNER JOIN
                                    (SELECT * FROM guestmanagement_programhistory_program WHERE program_id = %s) AS b
                                    ON a.phid=b.programhistory_id
                                  );'''
                program_id = Program.objects.get(name=value).id
                z = ProgramHistory.objects.raw(q,[date,date,program_id])
                if return_guest_ids:
                    return [i.guest_id for i in z]
                return Guest.objects.filter(id__in=[i.guest_id for i in z])
                
        elif field[0]=='date':
            raise Exception('Filter values on days only implemented for fields and guests')
        else:
            field=field[0]
        field_id = Field.objects.filter(name=field)[0].id
        q='''SELECT a.* FROM (
                                (SELECT * from guestmanagement_guesttimedata WHERE guestmanagement_guesttimedata.field_id=%s AND guestmanagement_guesttimedata.date<=%s) AS a 
                                 INNER JOIN
                                     (SELECT guest_id,MAX(date) AS mdate 
                                         FROM 
                                             (SELECT * from guestmanagement_guesttimedata WHERE guestmanagement_guesttimedata.field_id=%s AND guestmanagement_guesttimedata.date<=%s) AS c 
                                         GROUP BY guest_id
                                     ) AS b
                                 ON a.guest_id=b.guest_id AND b.mdate=a.date
                             ) 
             WHERE a.value=%s;'''
        z=GuestTimeData.objects.raw(q,[field_id,date,field_id,date,value])
        if return_guest_ids:
            return [i.guest_id for i in z]
        return Guest.objects.filter(id__in=[i.guest_id for i in z])
    
    def valueOnDay(self,env,date,field=None,guest_id=None,date_value_list=None):
        if env != None:
            date=self.evalVariables(env,date)
            field = self.evalVariables(env,field)
            date_value_list = self.evalVariables(env,date_value_list)
            guest_id = self.evalVariables(env,guest_id)
        if not isinstance(date,datetime.datetime):
            date=parse(date).date()
        if hasattr(date,'date'):
            date = date.date()
        if date_value_list != None:
            date_value_list = sorted(date_value_list,key=lambda x: x[0])
            if not date_value_list or date<date_value_list[0][0].date():
                return None
            value = date_value_list[0][1]
            for i in date_value_list[1:]:
                if date>=i[0].date():
                    value = i[1]
                else:
                    break
            return value
        
        if guest_id and not isinstance(guest_id,list):
            guest_id = [guest_id]
        if True in [isinstance(i,list) for i in guest_id]:
            raise Exception('guest_ids must be integers or strings, not lists')
        if field.startswith('guest.'):
            if field == 'guest.program':
                q = '''
                    SELECT * FROM (
                            (SELECT * FROM guestmanagement_programhistory WHERE date <= %s and guest_id IN %s) AS a
                            INNER JOIN
                            (SELECT guest_id AS tid, MAX(date) AS mdate FROM
                                (SELECT * FROM guestmanagement_programhistory WHERE date <= %s and guest_id IN %s) AS c
                            GROUP BY guest_id) AS b
                            ON a.guest_id=b.tid AND b.mdate=a.date
                        )
                
                '''
                return [[i.guest_id,'|'.join([a.name for a in i.program.all()])] for i in ProgramHistory.objects.raw(q,[date,tuple(guest_id),date,tuple(guest_id)])]
            guests = Guest.objects.filter(id__in=guest_id)
            return [[i.id,getattr(i,field.replace('guest.','',1),None)] for i in guests]
        else:
            field = Field.objects.get(name=field.replace('field.','',1))
            if not field.time_series:
                return [[i.guest.id,i.value] for i in GuestData.objects.filter(guest__id__in=guest_id,field=field)]
            q='''SELECT a.* FROM (
                                (SELECT * from guestmanagement_guesttimedata WHERE guestmanagement_guesttimedata.field_id=%s AND guestmanagement_guesttimedata.date<=%s) AS a 
                                 INNER JOIN
                                     (SELECT guest_id,MAX(date) AS mdate 
                                         FROM 
                                             (SELECT * from guestmanagement_guesttimedata WHERE guestmanagement_guesttimedata.field_id=%s AND guestmanagement_guesttimedata.date<=%s) AS c 
                                         GROUP BY guest_id
                                     ) AS b
                                 ON a.guest_id=b.guest_id AND b.mdate=a.date
                             ) 
             WHERE a.guest_id IN %s;
            '''
            return [[i.guest_id,i.value] for i in GuestTimeData.objects.raw(q,[field.id,date,field.id,date,tuple(guest_id)])]
    
    def python(self,env,code):
        c=compile(code,'report','exec')
        a=env
        gl = {'True':True,'False':False,'None':None}
        gl.update(a)
        while hasattr(a,'parent'):
            a=a.parent
            gl.update(a)
        def filterPrograms(table,**kwargs):
            return table.program.filter(**kwargs)
        def getDate(date):
            return date.date()
        def valueOnDay(date,field=None,guest_id=None,date_value_list=None):
            return self.valueOnDay(env,date,field,guest_id,date_value_list)
        def filterValuesOnDay(date,field,value,return_guest_ids=None):
            return self.filterValuesOnDay(env,date,field,value,return_guest_ids)
        def noFunction(env,*args):
            return 'Invalid Function'
        def externalFunction(name,*args):
            return self.functions.get(name,noFunction)(env,*args)
        allowed_functions = {
                                'filterValuesOnDay':filterValuesOnDay,
                                'valueOnDay':valueOnDay,
                                'GuestData':GuestData.objects.filter,
                                'GuestTimeData':GuestTimeData.objects.filter,
                                'Guest':Guest.objects.filter,
                                'ProgramHistory':ProgramHistory.objects.filter,
                                'GuestFormsCompleted':GuestFormsCompleted.objects.filter,
                                'len':len,
                                'type':lambda x: type(x),
                                'parse':parse,
                                'filterPrograms':filterPrograms,
                                'str':str,
                                'int':int,
                                'tuple':tuple,
                                'float':float,
                                'hashmap':SecureDict,
                                'sorted':sorted,
                                'list':list,
                                'iter':iter,
                                'dir':dir,
                                'round':round,
                                'relativedelta':relativedelta,
                                'getDate':getDate,
                                'range':lambda x,y,z=1: range(x,y,z),
                                'sum':sum,
                                'Q':Q,
                                'externalFunction': externalFunction,
        }
        class_functions = [ list.append,
                            list.pop,
                            QuerySet.filter.im_func,
                            QuerySet.first.im_func,
                            QuerySet.last.im_func,
                            QuerySet.exclude.im_func,
                            QuerySet.order_by.im_func,
                            QuerySet.prefetch_related.im_func,
                            QuerySet.values_list.im_func,
                            ValuesListQuerySet.distinct.im_func,
                            str.join,
                            str.split,
                            str.isdigit,
                            datetime.datetime.strftime,
                            datetime.datetime.strptime,
                            SecureDict.getItem.im_func,
                            SecureDict.setItem.im_func,
                            SecureDict.keys.im_func,
                            SecureDict.values.im_func,
                            SecureDict.pop.im_func
                            ]
        attribute_access = [list,
                            str,
                            QuerySet,
                            ValuesListQuerySet,
                            ProgramHistory,
                            Guest,
                            GuestTimeData,
                            GuestData,
                            GuestFormsCompleted,
                            Field,
                            datetime.datetime,
                            datetime.date,
                            datetime.timedelta,
                            Program,
                            SecureDict,
                            relativedelta
                           ]
        f=Function('demo',c,allowed_functions.keys())
        s=Sandbox(None,f,allowed_functions.values(),globals=gl,functions=tuple(allowed_functions.values()+class_functions),attributes_accessible=tuple(attribute_access),debug=False)
        timeout = 100
        g=s.execute(1000000,timeout)
        try:
            t = next(g)
        except Exception as e:
            from dis import findlinestarts
            from bisect import bisect
            linestarts = list(findlinestarts(c))
            line_no_table = list(findlinestarts(c))
            bytecode_table = [i[0] for i in line_no_table]
            line_table = [i[1] for i in line_no_table]
            line_idx = bisect(bytecode_table, s.last_index)-1
            line = line_table[line_idx]            
            raise Exception('%s\nIn python code line:%s'%(e,line))
        for i in allowed_functions.keys():
            s.local_variables.pop(i)
        if t:
            raise Exception('Report Timed Out after %s seconds'%timeout)
        return_global = s.local_variables.get('__return_global__',False)
        s.local_variables['__return_global__']=False
        a=env.parent.parent
        a.update(s.local_variables)
        if return_global:
            update_dict = {i:s.local_variables.get(i,None) for i in return_global if i in s.local_variables.keys()}
            while hasattr(a,'parent'):
                a=a.parent
                a.update(update_dict)
    
    def divideValues(self,env,divide,by,round_digits=0):
        value1 = self.evalVariables(env,divide)
        value2 = self.evalVariables(env,by)
        round_digits = int(self.evalVariables(env,round_digits) or 0)
        return round(float(value1)/float(value2),round_digits)
    
    def multiplyValues(self,env,value1,value2,round_digits=0):
        value1 = self.evalVariables(env,value1)
        value2 = self.evalVariables(env,value2)
        round_digits = int(self.evalVariables(env,round_digits) or 0)
        return round(float(value1)*float(value2),round_digits)

    def toString(self,env,variable):
        ''' 
            Function to convert a variable to a string
        '''
        return str(self.evalVariables(env,variable))
    
    def appendList(self,env,current_list,new_element):
        current_list = self.evalVariables(env,current_list)
        new_element = self.evalVariables(env,new_element)
        current_list.append(new_element)
        return current_list
    
    def concatenateStrings(self,env,string1,string2):
        '''
            Function which combines two strings into one
        '''
        string1 = self.evalVariables(env,string1)
        string2 = self.evalVariables(env,string2)
        return string1 + string2
    
    def mergeLists(self,env,list1,list2):
        '''
            Function which combines two lists into one
        '''
        list1 = self.evalVariables(env,list1)
        list2 = self.evalVariables(env,list2)
        return list1 + list2
    
    def checkAnniversaries(self,env,date,from_date,to_date):
        '''
            Function to look for an aniversary date within a specified range.<br />Arguments: date to check, starting date of range, ending 
            date of range.<br />Returns: the number of years if anniversary falls within the specified range or False if not.
        '''
        # Convert dates into datetime objects
        date=parse(self.evalVariables(env,date))
        from_date=parse(self.evalVariables(env,from_date))
        to_date=parse(self.evalVariables(env,to_date))
        # Calculate the earliest anniversary date
        earliest=date+relativedelta(years=from_date.year-date.year)
        # Calculate the latest anniversary date (if test range overlaps year end)
        latest=date+relativedelta(years=to_date.year-date.year)
        # Set return date to earlier
        return_date = earliest
        # Test for overlap on earlier date
        overlap = self.dateRangeOverlap(env,earliest,earliest,from_date,to_date)
        # If early date does not match and range overlaps year end
        if not overlap and latest != earliest:
            # Repeat test with latest date and set return date
            overlap = self.dateRangeOverlap(env,latest,latest,from_date,to_date)
            return_date = latest
        # If anniversary falls within specified range
        if overlap:
            # Return number of years
            return relativedelta(return_date,date).years
        # Return false if anniversary does not fall in specified range
        return False
        
        
    
    def addSubtractDates(self,env,date,adjustment,days_months_years,operator):
        '''
            Function to add or subtract time to a date by days, months, or years<br />
            Arguments: Date to adjust, quantity of adjustment, type of addjustment, addition or subtraction.<br />\
            Returns: Date after modification.
        '''
        # Evaluate the date variable
        date = self.evalVariables(env,date)
        # If the entered date is not already a datetime
        if not isinstance(date,(datetime.datetime,datetime.date)):
            # Convert the submitted variable to a datetime
            date = parse(date)
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
            Function to make guest picture record display capable in a report.<br />
            Arguments: link to picture, desired height (in pixels), desired width (in pixels)<br />
            Returns: formatted picture link suitable for display in reports.<br />
            NOTE: This function does not display the picture.  Use the "display" instruction to actually place
            picture in report.
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
            Function to find the last date on which a boolean field was activated.<br />
            Arguments: List of timeseries data from the desired boolean field.<br />
            Returns: Last day the field activated.
        '''
        return self.booleanMethods(env,boolean_list,last_day_activated=True)

    def boolActiveDuring(self,env,boolean_list,start_date,end_date):
        '''
            Function to determine whether a boolean field was ever active during a specified date range.<br />
            Arguments: List of timeseries data from the desired boolean field, date range start, date range end.<br />
            Returns: Number of days during the given date range when the boolean was active.  Returns 0 if the boolean was
            not active during that time.
        '''
        return self.booleanMethods(env,boolean_list,start_date=start_date,end_date=end_date)
    
    def lastDayDeactivated(self,env,boolean_list):
        '''
            Function to find the last date on which a boolean field was deactivated.<br />
            Arguments: List of timeseries data from the desired boolean field.<br />
            Returns: Last day the field deactivated.
        '''
        return self.booleanMethods(env,boolean_list,last_day_deactivated=True)

    def firstDayActivated(self,env,boolean_list):
        '''
            Function to find the first date on which a boolean field was activated.<br />
            Arguments: List of timeseries data from the desired boolean field.<br />
            Returns: First day the field activated.
        '''
        return self.booleanMethods(env,boolean_list,first_day_activated=True)
    
    def countBooleans(self,env,boolean_list, blank_each_time_field=False):
        '''
            Function to count how many times a boolean field was activated.<br />
            Arguments: List of timeseries data from the desired boolean field.<br />
            Returns: Number of times boolean activated.
        '''
        return self.booleanMethods(env,boolean_list,blank_each_time_field=blank_each_time_field)
    
    def countDays(self,env,boolean_list):
        '''
            Function to count how many days a boolean field spent active.<br />
            Arguments: List of timeseries data from the desired boolean field.<br />
            Returns: Total days boolean has been active.
        '''
        return self.booleanMethods(env,boolean_list,count_days=True)
    
    def add(self,env,value1,value2):
        '''
            Function to add two numbers.<br />
            Arguments: First value, Second value.<br />
            Returns: Sum of the two values.
        '''
        value1 = self.evalVariables(env,value1) or 0
        value2 = self.evalVariables(env,value2) or 0
        return str(float(value1) + float(value2))

    def subtract(self,env,value1,value2):
        '''
            Function to subtract two numbers.<br />
            Arguments: First value, Second value.<br />
            Returns: Difference of the two values.
        '''
        return str(float(self.evalVariables(env,value1)) - float(self.evalVariables(env,value2)))

    def today(self,env):
        '''
            Function to obtain today's date.<br />
            Arguments: None.<br />
            Returns: Today's date.
        '''
        return datetime.datetime.now().date()
        
    def subtractDates(self,env,date1,date2,days_months_years=None):
        '''
            Function to subtract two dates.<br />
            Arguments: First date, Second date, desired unit of difference (days, months, or years).<br />
            Returns: Number of units between the two dates in days, months, or years.
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
        '''
            Function to obtain number of elements in a list or number of characters in a string.<br />
            Arguments: variable.<br />
            Returns: Length of provided variable.
        '''
        # Eval variable
        variable = self.evalVariables(env,variable)
        # Return length
        return len(variable)
            

    ### internal functions
    def Pass(self,env,*code):
        pass
    
    def makeCalendar(self,env,date_list,comment_list):
        date_list = self.evalVariables(env,date_list)
        comment_list = self.evalVariables(env,comment_list)
        if isinstance(date_list,(str,unicode)):
            date_list = date_list.split(',')
        if isinstance(comment_list,(str,unicode)):
            comment_list = comment_list.split(',')
        combined_list = []
        if isinstance(date_list[0],list) or isinstance(comment_list[0],list):
            assert isinstance(date_list[0],list) and isinstance(comment_list[0],list), 'Type of list mismatch error.  Date list and comment list must be either *both* timeseries lists or *both* comma separated list'
            for i in date_list:
                for a in comment_list:
                    if i[0]==a[0]:
                        combined_list.append([parse(i[1]),a[1]])
        else:
            assert len(date_list) == len(comment_list), "date list and comment list must be of equal length"
            for i in range(0,len(date_list)):
                combined_list.append([date_list[i],comment_list[i]])
        combined_list = sorted(combined_list,key=lambda x: x[0])
        assert isinstance(combined_list[0][0],(datetime.datetime,datetime.date)),"No dates in date list"
        start_date = combined_list[0][0].replace(day=1)
        end_date = combined_list[-1][0].replace(day=calendar.monthrange(combined_list[-1][0].year,combined_list[-1][0].month)[1])
        notes_dict = {}
        for i in combined_list:
            notes_dict[parse(i[0].strftime('%m/%d/%Y'))]=notes_dict.get(parse(i[0].strftime('%m/%d/%Y')),[])
            notes_dict[parse(i[0].strftime('%m/%d/%Y'))].append(i[1])
        month_dict = {1:'January',
                      2:'February',
                      3:'March',
                      4:'April',
                      5:'May',
                      6:'June',
                      7:'July',
                      8:'August',
                      9:'September',
                      10:'October',
                      11:'November',
                      12:'December'}
        env['print'](month_dict[start_date.month]+'<br/>')
        env['print']('<table rules="rows" table-layout="fixed" width="1000px"><tr><th>Sunday</th><th>Monday</th><th>Tuesday</th><th>Wednesday</th><th>Thursday</th><th>Friday</th><th>Saturday</th></tr>')
        start_dict = {0:'<tr><td bgcolor="#E6E6E6"></td>',
                      1:'<tr><td bgcolor="#E6E6E6" colspan=2></td>',
                      2:'<tr><td bgcolor="#E6E6E6" colspan=3></td>',
                      3:'<tr><td bgcolor="#E6E6E6" colspan=4></td>',
                      4:'<tr><td bgcolor="#E6E6E6" colspan=5></td>',
                      5:'<tr><td bgcolor="#E6E6E6" colspan=6></td>',
                      6:''}
        env['print'](start_dict[start_date.weekday()])
        tracking_date = start_date
        add_day = datetime.timedelta(days=1)
        while tracking_date <= end_date:
            if tracking_date.weekday()==6:
                env['print']('<tr>')
            env['print']('<td width="1000px" word-wrap="break-word">')
            env['print']('<h5>'+str(tracking_date.day)+'</h5><br/>')
            for i in notes_dict.get(parse(tracking_date.strftime('%m/%d/%Y')),[]):
                env['print'](i)
                env['print']('<br/>')
            env['print']('</td>')
            next_day = tracking_date + add_day
            if next_day.weekday()==6:
                env['print']('</tr>')
            if next_day.month != tracking_date.month:
                if next_day.weekday()!=6:
                    env['print']('<td bgcolor="#E6E6E6" colspan=%s></td></tr>'%(6-next_day.weekday(),))
                env['print']('</table><br/>')
                if next_day<end_date:
                    env['print'](month_dict[next_day.month]+'<br/>')
                    env['print']('<table rules="rows" table-layout="fixed" width="1000px"><tr><th>Sunday</th><th>Monday</th><th>Tuesday</th><th>Wednesday</th><th>Thursday</th><th>Friday</th><th>Saturday</th></tr>')
                    env['print'](start_dict[next_day.weekday()])
            tracking_date = next_day

                

    def beginTable(self,env,comma_separated_headers):
        '''
            Instruction to begin building a table.
            Takes a comma separated list of headers and displays them on the report
        '''
        # Split headers variable into list
        headers = comma_separated_headers.split(',')
        # Start html table
        env['print']('<table border="1"><tr>')
        # If headers specified
        if comma_separated_headers:
            # Print each header into a header row
            for i in headers:
                env['print']('<th>'+i+'</th>')
            # Start new row for table
            env['print']('</tr><tr>')

    def endTable(self,env):
        '''
            Instruction to end a table.
        '''
        env['print']('</tr></table>')

    def booleanMethods(self,env,boolean_list,count_days=False,last_day_activated=False,last_day_deactivated=False,first_day_activated=False,start_date=False,end_date=False,blank_each_time_field=False):
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
        # Initialize active dates
        # active_dates = [[turned on, turned off],...]
        active_dates = []
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
        if first_day_activated:
            return checkin_date
        active_dates.append([checkin_date])
        # Iterate the remaining list after boolean first activates
        for i in boolean_list:
            # If boolean is now inactive and (counting days or wants last deactivation) and previous record was active
            if i[1] == u'' and (count_days or last_day_deactivated or start_date) and current[1] =="checked='checked'":
                # increase days active count
                count += int(self.subtractDates(env,i[0],checkin_date))
                # Set deactivated date
                checkout_date = i[0]
                # append date to active_dates
                active_dates[-1].append(checkout_date)
            # If boolean is now active and previous record was not active or counting blank_each_time fields
            if i[1] == "checked='checked'" and (current[1]==u'' or blank_each_time_field):
                # If not counting days
                if not count_days:
                    # Increase counter
                    count += 1
                # Set activated date
                checkin_date=i[0]
                # append date to active_dates
                active_dates.append([checkin_date])
            # Set previous record to current record for next iteration
            current = i
        # If active_dates ends checked in
        if len(active_dates[-1])<2:
            active_dates[-1].append(datetime.datetime.now())
        # If testing checked in during
        if start_date:
            # Initialize variable of how many days
            overlap = 0
            # Iterate list of active dates
            for i in active_dates:
                overlap += self.dateRangeOverlap(env,i[0],i[1],start_date,end_date)
            return overlap
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
            Function to display text on the report.  Takes bold level and text to display as arguments.
        '''
        # If no bold selected
        value = ''.join([str(self.evalVariables(env,i.split('}}')[0]))+''.join(i.split('}}')[1:]) for i in value.split('{{')])
        if bold == 'none':
            # append text to report
            env['print'](value)
        else:
            # Put text in appropriate h tag
            env['print']('<%s>%s</%s>'%(bold,value,bold))

    def set_(self,env,key,value):
        '''
            Instruction to set variable to value.  Takes a variable name and a value (which can be another variable) 
            and registers the variable name as being equal to the value provided.  For example: if you provide name as "my_first_variable"
            and value as "Hello World", then when you reference "$my_first_variable" the server will translate that to "Hello World".
        '''
        # Recognize new lists
        value = self.evalVariables(env,value)
        if value == '[]':
            value = []
        # If list element not being updated
        if '::' not in key:
            # Set parent environment variable
            env.parent.parent[key] = value
        else:
            # Split update variable into list of steps
            slice_list = key.split('::')
            # Retrieve base variable
            key = slice_list.pop(0)
            # Retrieve last element reference
            end = int(self.evalVariables(env,slice_list.pop()))
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
            a[end] = value
            # Set base variable to new list value in parent environment
            env.parent.parent[key] = cur_value
                
    
    def display(self,env,display_value,separator,timeseries, *code):
        '''
            Instruction to translate variables or pull data from the database and display the result.
            This instruction takes a value to display which can be a variable from the Defined Variables Section
            or a field from the Select Field Section, a separator character for displaying multiple values, whether
            the request is timeseries (applies to fields only) and additional instructions.  The additional instructions
            are given as indented lines until an end instruction closes the display instruction.  See the additional 
            instructions for further details.
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
            filter = self.buildFilter(env,display_value,0,timeseries,code)
            # If filter returns more than one record
            if len(filter)>1:
                # Warn user
                env['print']('filter returned more than one value')
            elif len(filter)==1:
                # Use separator to create a string from the filter's list and append
                assert isinstance(separator,(str,unicode)), "Display separator must be string (did you pick the wrong variable name?)"
                env['print'](separator.join([str(i) if not isinstance(i, (datetime.datetime,datetime.date)) else i.strftime('%m/%d/%Y') for i in filter[0]]))
                

    def newline(self, env):
        '''
            Instruction to insert a line break in the report.
        '''
        env['print']('<br />')

    def query(self, env, list_type,list_variable,sort_by,list_range, timeseries, *code):
        '''
            Instruction to retrive data from database.  This instruction takes type of query, a variable name in which to 
            store the results, which column to sort by, the first field to return, whether the first field is timeseries, and additional 
            instructions.  NOTE: While this instruction accepts both fields and numbers as types of query only fields is relevant.  The 
            additional instructions are given as indented lines until an end instruction closes the display instruction.  See the 
            additional instructions for further details.
        '''
        # Retrieve filter results
        a = self.buildFilter(env,list_range,sort_by,timeseries,code)
        # Save filter results into parent environment
        env.parent.parent[list_variable.replace('!','')] = a

    def if_(self,env,operator,value1,value2,*code):
        '''
            Instruction to run some code conditionally.  Takes an operator (e.g. =,<,>,!=, etc), and two values to compare, with 
            instructions to run.  If the comparison condition evaluates to true, then the conditional instructions are executed
            otherwise, the conditional instructions are ignored.
        '''
        if code:
            code=list(code)
        # Initialize true flag
        true = False
        complete = False
        while len(code)>1 and len(code[1])>0 and (code[1][0]=='and' or code[1][0]=='or'):
            sub_operator = code.pop(1)
            if not complete:
                test = self.if_(env,sub_operator[1],sub_operator[2],sub_operator[3])
                if sub_operator[0]=='or' and test:
                    true = True
                    complete = True
                if sub_operator[0]=='and' and not test:
                    true=False
                    complete = True
        if not complete:
            # Evaluate variables to be compared
            a = self.evalVariables(env,value1)
            b = self.evalVariables(env,value2)
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
                else:
                    try:
                        a = parse(a)
                    except:
                        pass
                    try:
                        b = parse(b)
                    except:
                        pass
                if operator == '>':
                    if b>a:
                        true = True
                elif operator == '<':
                    if b<a:
                        true = True
                elif operator == '>=':
                    if b>=a:
                        true = True
                elif operator == '<=':
                    if b<=a:
                        true = True
                elif operator == '<>':
                    if a!=b:
                        true = True
        if code:
            if true:
                current_index = env.__get_global__('__trace_index__')
                tracking_index = current_index+1
                env.__set_global__('__trace_index__',tracking_index)
                # Prepare code for execution
                code=['do']+list(code)
                # Run code
                self.listProcess(self.Env(env), deepcopy(code))
                env.__set_global__('__trace_index__',current_index)
                for i in range(current_index+1,max(env.__get_global__('__traceback__').keys())+1):
                    env.__get_global__('__traceback__').pop(i)
                env.parent.parent.update(env.children[0].children[0])
        else:
            return true

    def link(self,env,guest=None,form=None,text=None):
        '''
            Function to create a link to a particular guest's record or a particular form for a particular guest
        '''
        # Eval variables
        guest = self.evalVariables(env,guest)
        form = self.evalVariables(env,form)
        text = self.evalVariables(env,text)
        if form and not form.isdigit():
            form = Form.objects.get(name=form).id
        env['print']('<a href="/guestmanagement/view/')
        if guest and not form:
            env['print']('guest/%s/'%guest)
        else:
            env['print']('form/%s/%s/'.replace('//','/')%(form,guest))
        env['print']('">%s</a>'%text)
    
    def list_(self, env, list_type,list_variable,sort_by,row_items,row_num,row_separator,list_range, timeseries, *code):
        '''
            Instruction to iterate over lists or a range of numbers.  Takes whether a list or numbers, a variable name for use as the list
            iterates, which column to sort by, how many items to iterate before inserting a row break, how many row breaks to insert 
            before inserting a page break, what to insert for row breaks, what field to return (if a field list) or what range of numbers 
            to iterate (if a number range list), whether the first field is time series (if a field list), additional instructions and 
            instructions to run every iteration.  The list instruction starts by searching for additional instructions and retrieving the 
            fields/numbers to iterate (see additional instructions for more information).  Once the list to iterate is constructed, the 
            list instruction will set the variable provided to the first value from the list, then execute the instructions provided, then 
            set the variable provided to the second value from the list, then reexecute the instructions provided, then set the variable 
            provided to the third value from the list, and so on until there are no more remaining elements in the list.
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
            a = self.buildFilter(env,list_range,sort_by,timeseries,code)
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
        current_index = env.__get_global__('__trace_index__')
        tracking_index = current_index+1
        env.__set_global__('__trace_index__',tracking_index)
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
            # Ensure number of rows is an integer
            row_items = row_items or '1'
            row_items = row_items if row_items.isdigit() else '1'
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
            env.__get_global__('__traceback__').pop(tracking_index)
        env.__set_global__('__trace_index__',current_index)
        for i in range(current_index+1,max(env.__get_global__('__traceback__').keys())+1):
            env.__get_global__('__traceback__').pop(i)

    def count(self,env,return_field,timeseries,*code):
        '''
            Instruction to retrieve the requested fields from the database and put into the report how many records were pulled.
            Takes the field requested, whether to search timeseries, and additional instructions.  See Additional Instructions for more
            information.
        '''
        # Retrieve filter
        filter = self.buildFilter(env,return_field,0,timeseries,code)
        # Update html with number of items returned
        env['print'](str(len(filter)))

    def sum(self,env,return_field,timeseries,*code):
        '''
            Instruction to retrieve the requested fields from the database and put into the sum of the values returned
            Takes the field requested, whether to search timeseries, and additional instructions.  See Additional Instructions for more
            information.
        '''
        # Retrieve filter
        filter = self.buildFilter(env,return_field,0,timeseries,code)
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
        '''
            Instruction to execute a specified function and store result in the provided variable.
            See the list of functions for more information.
        '''
        self.set_(env,return_variable.replace('$',''),self.functions[function](env,*args))


    # system functions
    
    def dateRangeOverlap(self,env,start_date1,end_date1,start_date2,end_date2):
        '''
            Function to test if two date ranges overlap
            Returns the number of days overlapped or zero if not overlapped.
        '''
        # Convert start and end dates to date objects
        if not isinstance(start_date1,datetime.datetime):
            start_date1 = parse(self.evalVariables(env,start_date1))
        if not isinstance(end_date1,datetime.datetime):
            end_date1 = parse(self.evalVariables(env,end_date1))
        if not isinstance(start_date2,datetime.datetime):
            start_date2 = parse(self.evalVariables(env,start_date2))
        if not isinstance(end_date2,datetime.datetime):
            end_date2 = parse(self.evalVariables(env,end_date2))
        # Create named range of start and end
        Range = namedtuple('Range', ['start', 'end'])
        # Initialize active range
        r1 = Range(start=start_date1, end=end_date1)
        # Initialize comparison range
        r2 = Range(start=start_date2, end=end_date2)
        # Find latest start
        latest_start = max(r1.start, r2.start)
        # Find earliest end
        earliest_end = min(r1.end, r2.end)
        # negative comparisons mean no overlap, so ignore them
        return max(0,(earliest_end - latest_start).days + 1)

    def do(self, env, *args):
        #Function to catch code and process it
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

    def buildFilter(self,env,return_field,sort_by,timeseries,code):
        '''
            Function to retrieve data from database
        '''
        
        #----
        # Initialization section
        # creates required variables and converts incomming instructions
        # into organized lists
        #----
        
        # date_filters = [date1, ...]
        date_filters = []

        # Evaluate any variables in return_field
        if '::' in return_field:
            a = return_field.split('::')
            for i in range(1,len(a)):
                if '$' in a[i]:
                    a[i]=str(self.evalVariables(env,a[i]))
            return_field = '::'.join(a)
        
        
        # return_field_list = [[field,timeseries],...]
        return_field_list = [[return_field,timeseries]]

        # filter = [["and/or",operator,value1,value2,timeseries],...]
        filter = []
        if code:
            # Convert any parameters in code into criteria or return fields
            tracker = iter(code)
            current = tracker.next()
            while current[0]=='and' or current[0]=='or' or current[0]=='extrafield':

                if current[0]=='extrafield':
                    # Add requested field to return_field_list after
                    # evaluating any report variables
                    if '::' in current[1]:
                        a = current[1].split('::')
                        for i in range(1,len(a)):
                            if '$' in a[i]:
                                a[i]=str(self.evalVariables(env,a[i]))
                        current[1] = '::'.join(a)
                    return_field_list.append([current[1],current[2]])
                
                elif 'date.' in current[3]:
                    # Put date in date filters
                    date_filters.append(current)
                    
                else:
                    # Put filter in filter list
                    filter.append(current)
                
                # Prepare next iteration or exit
                try:
                    current = tracker.next()
                except StopIteration:
                    break
        
        
        #----
        # Filtering against variable section
        # When filtering against a variable, this section processes the
        # filter as though the variable were a database where each element
        # is a record and each element of the elements is a column.
        #
        # Each record is identified with its index in the original 
        # variable, and then tested against any criteria.  Those which 
        # meet the criteria are then parsed for what is being requested
        # and compiled into return values
        #----
        
        if '$' in return_field:
            
            # All return fields must come from the same parent variable
            test = [i[0].split('::')[0].replace('$','').replace(' ','') for i in return_field_list]
            assert test[1:]==test[:-1], 'All return fields must come from the same variable'
            
            # All criteria must also come from the same parent variable
            test = [i[3].split('::')[0].replace('$','').replace(' ','') for i in filter]
            assert test[1:]==test[:-1] and (return_field.split('::')[0].replace('$','').replace(' ','') in test or test==[]), 'All criteria must come from the filtered variable'

            # record_list = the original value of the variable
            record_list = self.evalVariables(env,return_field_list[0][0].split('::')[0])
            
            if not isinstance(record_list,list) or False in [isinstance(i,list) for i in record_list]:
                record_list = [record_list]
            
            # valid_ids = [id,...]
            valid_ids = []
            if filter==[]:
                # If no criteria, return all field ids as valid
                valid_ids = range(0,len(record_list))
            else:
                # Process each record against each criteria

                # Set flag to catch first criteria
                first_filter = True
                
                for i in filter:
                    holding_valid_ids = []

                    # Evaluate filter into criteria
                    value = self.evalVariables(env,i[2])
                    comparator_address = [int(self.evalVariables(env,a)) for a in i[3].split('::')[1:]]
                    for record_id in range(0,len(record_list)):
                        comparator = record_list[record_id]
                        if i[4] == 'on':
                            # If filtering on time series, if the address 
                            # has more than one element assume the user
                            # is specifying a specific element in each
                            # timeseries value and check that element
                            # in each timeseries value
                            #
                            # otherwise, assume the user is specifying
                            # the entire list of timeseries values and
                            # check against the entire list as a whole
                            if len(comparator_address)>1:
                                for a in comparator_address[:-1]:
                                    comparator = comparator[a]
                                if True in [self.if_(env,i[1],value,a[comparator_address[-1]]) for a in comparator]:
                                    if record_id not in holding_valid_ids:
                                        holding_valid_ids.append(record_id)
                            else:
                                for a in comparator_address:
                                    comparator = comparator[a]
                                if True in [self.if_(env,i[1],value,a) for a in comparator]:
                                    if record_id not in holding_valid_ids:
                                        holding_valid_ids.append(record_id)
                        else:
                            for a in comparator_address:
                                comparator = comparator[a]
                            if self.if_(env,i[1],value,comparator):
                                if record_id not in holding_valid_ids:
                                    holding_valid_ids.append(record_id)
                
                    # Process and/or criteria against holding_valid_ids
                    if i[0] == 'or':
                        valid_ids = valid_ids + [new_id for new_id in holding_valid_ids if new_id not in valid_ids]
                    else:
                        # First filters will always start blank, so an
                        # and against a blank filter will always remain
                        # blank
                        if valid_ids == [] and first_filter:
                            valid_ids = list(holding_valid_ids)
                        else:
                            valid_ids = list(set(valid_ids) & set(holding_valid_ids))
                    # Set first_filter flag
                    first_filter = False
            
            # Catch filters just returning entire list
            if not filter and '::' not in return_field:
                return self.mySort(env,record_list,sort_by)

            # Prepare return value from list of valid ids created above
            
            # return_dict = {record_id: [return record],...}
            return_dict = {}
            for each_id in valid_ids:
                return_dict[each_id] = return_dict.get(each_id,[])
                for each_field in return_field_list:
                    address = each_field[0].split("::")[1:]
                    value = record_list[each_id]
                    # If a varying length list is too short for what the
                    # user specified, return ''
                    for i in address:
                        try:
                            value = value[int(i)]
                        except IndexError:
                            value = ''
                    
                    if not address or each_field[1]:
                        # If asking for original record or a timeseries field
                        # Find timeseries criteria
                        filter = [i for i in filter if i[4]]
                        if filter and each_field[1]:
                            # if a timeseries field being filtered run a second
                            # filter against just the time series field
                            new_env = {'__query__':value}
                            
                            # Build the filter based on the time series criteria
                            # matching the field being requested which is
                            # the return field + the address variables from above
                            new_filter = []
                            for a in filter:
                                # If the return field + the address is the
                                # first part of the criteria, include that
                                # criteria in the new filter
                                valid = False not in [int(address[i])==int(a[3].split('::')[1:][i]) for i in range(0,len(address))]
                                if valid:
                                    new_filter.append([a[0],a[1],a[2],'__query__'+a[3].replace(a[3].split('::')[0]+'::'+'::'.join(address),''),''])
                            # replace current value with new filter and handle normally
                            value = self.buildFilter(new_env,'$__query__','','',tuple(new_filter))

                        return_dict[each_id].extend(value)
                    else:
                        return_dict[each_id].append(value)
            
            if len(record_list)==1 and timeseries and len(return_dict.values())>0:
                return self.mySort(env,return_dict.values()[0],sort_by)
            # Return filter results
            return self.mySort(env,return_dict.values(),sort_by)


        # If filtering against the database
        # If no criteria
        if filter==[]:
            # Return all guests
            guest_list = [i.id for i in Guest.objects.all() if testPermission(i,env['user'])]
            no_criteria = True
        else:
            no_criteria = True not in [i[4]=='on' for i in filter]
            # Initialize guest list
            # guest_list = [guest1,guest2,...]
            guest_list = []
            # Iterate over filters
            for i in filter:
                # Initialize equals kwargs
                # eqargs=[Q(field:value),...]
                eqargs = []
                # Initialize not equals kwargs
                # neargs=[Q(field:value),...]
                neargs = []
                # If filtering against a field
                if 'field.' in i[3]:
                    # place field name in filter criteria
                    eqargs.append(Q(**{'field__name':i[3].split('field.')[1]}))
                    # Translate filter comparator into django filter format
                    operator = 'value__%s'%self.filter_dict[i[1]]
                    # If filtering for not equal
                    if i[1] == '<>':
                        # Append operator into neargs
                        neargs.append(Q(**{operator:self.evalVariables(env,i[2])}))
                    else:
                        # Append operator into eqargs
                        eqargs.append(Q(**{operator:self.evalVariables(env,i[2])}))
                    # If filtering on timeseries and dates specified
                    if i[4]==u'on' and date_filters!=[]:
                        # Iterate through date filters
                        for a in date_filters:
                            # Add to eqkwargs date filter requirements
                            eqargs.append(Q(**{'date__{0}'.format(self.filter_dict[a[1]]):self.evalVariables(env,a[2])}))
                    # run filter based on timeseries (GuestTimeData vs GuestData) and kwargs; return list of guestids who fit critera
                    current_guest_list = self.filter_dict['field'][i[4]].objects.filter(*eqargs).exclude(*neargs).values_list('guest',flat=True)
                else:
                    # If filtering on guests
                    # initialize operator with first guest attribute
                    operator = '%s__'%i[3].split('guest.',1)[1]
                    # Set table to filter
                    filter_table = Guest.objects
                    # If filtering on guest program
                    if i[3].split('guest.',1)[1]=='program':
                        # Add name to operator (results in operator == "program__name__")
                        operator += 'name__'
                        if i[4]==u'on':
                            filter_table = ProgramHistory.objects
                        if i[1] == '=':
                            # Change filter table for equals
                            filter_table = filter_table.annotate(num_prog=Count('program'))
                            eqargs.append(Q(**{'num_prog':1}))
                    # Add django filter comparator
                    operator = operator + self.filter_dict[i[1]]
                    # If filtering on not equal
                    if i[1] == '<>':
                        # Append filter to not equal kwargs
                        neargs.append(Q(**{operator:self.evalVariables(env,i[2])}))
                    else:
                        # Append filter to equal kwargs
                        eqargs.append(Q(**{operator:self.evalVariables(env,i[2])}))
                    # Run django filter returning list of guest ids where guest matches criteria
                    current_guest_list = list(filter_table.filter(*eqargs).exclude(*neargs).distinct().values_list({'':'id',u'on':'guest_id'}[i[4]],flat=True))
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
        # Test view_guest permission
        if not testPermission('view_guest',env['user']):
            guest_list = []
        else:
            # Convert list of guest ids to list of guest objects
            guest_list = [i for i in Guest.objects.filter(id__in=list(guest_list)).distinct() if testPermission(i,env['user'])]
        # Initialize Retval
        # retval = [[[record1],[record2],...],[[record1],[record2],...],...]
        retval = []
        # Initialize holding
        # holding = {guest:[field1,field2,...],...}
        holding = {}
        # Iterate over return field list
        for i in return_field_list:
            # Split table and field
            table,field = i[0].split('.',1)
            # If table is guest
            if 'guest' == table:
                if i[1]==u'on':
                    prog_hist_query = ProgramHistory.objects.filter(guest__in=guest_list)
                    for a in date_filters:
                        prog_hist_query = prog_hist_query.filter(Q(**{'date__{0}'.format(self.filter_dict[a[1]]):self.evalVariables(env,a[2])}))
                    prog_hist_dict = {}
                    for a in prog_hist_query:
                        prog_hist_dict[a.guest.id] = prog_hist_dict.get(a.guest.id,[])
                        prog_hist_dict[a.guest.id].append([a.date,'|'.join([z.name for z in self.safegetattr(a,field).all()])])
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
                        if i[1] == u'on':
                            holding[a].append(prog_hist_dict.get(a.id,[]))
                        else:
                            holding[a].append('|'.join([z.name for z in self.safegetattr(a,field).all()]))
                            
                    else:
                        holding[a].append(str(self.safegetattr(a,field)))
            else:
                # If table is field
                # Retrieve filter from database where field name matches and guest is in guest list
                filter = self.filter_dict['field'][i[1]].objects.filter(guest__in=guest_list,field__name=field).distinct()
                # limit date filters to applicable records if no other criteria were given
                if i[1] and date_filters and no_criteria:
                    for a in date_filters:
                        filter = filter.filter(Q(**{'date__{0}'.format(self.filter_dict[a[1]]):self.evalVariables(env,a[2])}))
                # Test permission to view field
                if not testPermission(['and',Field.objects.get(name=field),Field.objects.get(name=field).form],env['user']):
                    if not (Field.objects.get(name=field).permissions_may_have.all() or Field.objects.get(name=field).permissions_may_have.all()) or not testPermission(Field.objects.get(name=field),env['user']):
                        filter = self.filter_dict['field'][i[1]].objects.filter(guest__in=[])
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
        # Iterate through sorting possiblities
        return self.mySort(env,retval,sort_by)
    
    def sortByDateStringsKeys(self,el,sb=0):
        a=el[sb].split('/')
        assert len(a)==3 or el[sb]==""
        if len(a)==3:
            return (a[2],a[0],a[1])

    def mySort(self,env,retval,sort_by=0):
        if len(retval)==0:
            return retval
        sort_by = self.evalVariables(env,sort_by)
        if isinstance(sort_by,(str,unicode)):
            sort_by = int(sort_by) if sort_by.isdigit() else 0
        sort_by = sort_by if sort_by < len(retval[0]) else 0
        for i in [lambda x: sorted(x, key=lambda y: self.sortByDateStringsKeys(y,sort_by)),
                    lambda x: sorted(x, key=lambda s: s[sort_by].lower()),
                    ]:
            # Try each sorting possiblity, continue to the next if it fails
            try:
                # Try sorting each pattern
                return i(retval)
            except (AttributeError,AssertionError,IndexError):
                continue
        try:
            return sorted(retval)
        except:
            return retval
    
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
        retval = variable
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
                    retval = var
                else:
                    retval = var
        if retval == 'True':
            retval = "checked='checked'"
        return retval

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
                    if line[2]:
                        user_variables.append([line[1],line[2].split(',')])
                    else:
                        user_variables.append([line[1],[]])
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
            env=self.Env({'__traceback__':{0:[]},'__trace_index__':0})
        if not isinstance(env,self.Env):
            env = self.Env(env)
        # If code not executable
        if not isinstance(code,list) or not code:
            # Return the value
            return code
        # Pull first instruction
        first = code.pop(0)
        env.__get_global__('__traceback__')[env.__get_global__('__trace_index__')]=env.__get_global__('__traceback__').get(env.__get_global__('__trace_index__'),[])
        env.__get_global__('__traceback__')[env.__get_global__('__trace_index__')].append(first)
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
    
def datesToStrings(target):
    for i in range(0,len(target)):
        if isinstance(target[i],datetime.datetime):
            target[i] = str(target[i])
        elif isinstance(target[i],list):
            target[i] = datesToStrings(target[i])
    return target

def readableList(value):
    '''
        Function to print lists to console which are multiline and readable
    '''
    value = datesToStrings(value)
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
    context = {'nexturl':request.path,
                'base_site':request.session.get('base_site',''),
                'org_title':settings.MYSETTINGS['TITLE'],
                'logo':settings.MYSETTINGS['LOGOFILE'],
                "report_title_background": settings.MYSETTINGS["REPORTBUILDERBACKGROUNDS"]["TITLE"],
                "report_builder_background": settings.MYSETTINGS["REPORTBUILDERBACKGROUNDS"]["BUILDER"],
                'report_functionselect_background':settings.MYSETTINGS["REPORTBUILDERBACKGROUNDS"]["FUNCTIONSELECT"],
                'report_formselect_background':settings.MYSETTINGS["REPORTBUILDERBACKGROUNDS"]["FORMSELECT"],
                'report_fields_background':settings.MYSETTINGS["REPORTBUILDERBACKGROUNDS"]["FIELDS"],
                }
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
    
def testListValues(a,i,second_object):
    value=GuestData.objects.get_or_create(guest=second_object,field=i)[0].value
    if a.strip() == value:
        return True
    values=re.findall(r"'\s*([^']*?)\s*'", value)
    return a.strip() in values

def createForm(field_list,user,request=None,second_object=None,error_flags=None,session=None,edit_past=False,extra_fields=None):
    '''
    Builds the html form to be displayed based on a list of fields passed in from requesting view
    '''
    error_flags = error_flags or {}
    session = session or {}
    extra_fields = extra_fields or []
    if len(extra_fields)>0:
        extra_header = type("Foo", (object,), {})()
        extra_header.label = "Extra Fields (For Reference Only)"
        extra_header.field_type = 'title'
        extra_fields = [extra_header] + list(extra_fields)
    # Order field_list by "order"
    if not isinstance(field_list,list):
        field_list = field_list.order_by('order')
    field_type_options={# reference dictionary relating field types (found in the Field model) to specific html
                        # 'field_type' : "html to display" (must have 5 %s locations)
                        'text_box':"<input %s id='%s' name='%s' type='text' value='%s'></br>\n%s",
                        'comment_box':"<textarea %s cols='40' id='%s' name='%s' rows='10' size='100'>%s</textarea></br>\n%s",
                        'drop_down':"<select %s id='%s' name='%s' value='%s'>\n%s</select></br>",
                        'boolean':"<input %s id='%s' name='%s' %s type='checkbox' />\n%s</br>",
                        'list':"<select %s multiple='multiple' id='%s' name='%s' value='%s'>\n%s</select></br>",
                        'date':"<input %s class='datePicker' id='%s' name='%s' readonly='true' type='text' value='%s'><input type='button' onclick='clearDate(this)' value='Clear' /></br>\n%s",
                        'url':'<iframe %s %s%s width="560" height="345" src="%s?rel=0" frameborder="0" allowfullscreen>%s</iframe></br>',
                        'attachment':'<a %s %s%s href="%s">%s</a></br>',
                        'file':'</br>&nbsp;&nbsp;&nbsp;&nbsp;Change File: <input %s id="%s" name="%s" type="file" /></br>&nbsp;&nbsp;&nbsp;&nbsp;<a href="%s">%s</a></br>',
                        }
    # return html string of form for display in template.
    return mark_safe(
                        ''.join([
                                "%s%s%s: %s"%(
                                    error_flags.get(i,''),
                                    i.label,
                                    ' *' if i.required else '',
                                    field_type_options[i.field_type]%(
                                        {True:'',False:'Disabled'}[testPermission(i,user,session,second_object=second_object,write=True) and not i in extra_fields],
                                        i.name,
                                        i.name,
                                        ''
                                            if (i.blank_each_time and not edit_past) else i.attachment.attachment.url
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
                                                    ''
                                                        if (i.blank_each_time and not edit_past) else {True:"selected='selected'",False:''}[testListValues(a,i,second_object)]
                                                        if not request else {True:"selected='selected'",False:''}[a.strip() in request.POST.get(i.name,'')],
                                                    a.strip(),
                                                )
                                                for a in i.dropdown_options.split('\n') if a != ''
                                            ]
                                        )
                                    )
                                )
                                 if i.field_type!='title' and (not isinstance(i,Field) or testPrerequisites(i,second_object)) else '<p class="formlabel"><strong>%s</strong></p></br>'%i.label
                                 if i.field_type=='title' else '<ul><li>Field %s prerequisites not satisfied</li></ul>'%i.name for i in list(field_list) + extra_fields if testPermission(i,user)
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
            i.permissions_may_have = list(i.form.permissions_may_have.all()) + list(i.field.permissions_may_have.all())
            i.permissions_must_have = list(i.form.permissions_must_have.all()) + list(i.field.permissions_must_have.all())
            i.save()


def testPermission(target_object,user,session={},second_object=None,testurl=False,owner=False,write=False,owner_override=False):
    '''
    Method of determining based on permissions whether a user has permission to access a form, field, guest, or static file
    '''
    owner_override = owner or owner_override
    # Return True if a superuser
    if user and user.is_superuser:
        return True
    if testurl:
        # If testing a static file, pull the static file permissions record from the database
        target_object,created = DynamicFilePermissions.objects.get_or_create(path=target_object.replace('%20',' '))
        if created:
            if 'guestpictures' in target_object.path:
                base_guest = Guest.objects.get(picture=target_object.path)
                target_object.permissions_may_have = base_guest.permissions_may_have.all()
                target_object.permissions_must_have = base_guest.permissions_must_have.all()
                target_object.permissions_write = base_guest.permissions_write.all()
            else:
                path = target_object.path
                target_object.delete()
                raise ValueError('Missing DynamicFilePermission for %s'%path)
    if isinstance(target_object,list):
        option = target_object.pop(0)
        if option == 'or':
            test = [True for i in target_object if testPermission(i,user,session,second_object,testurl)]
            if not test:
                return False
        else:
            for i in target_object:
                if not testPermission(i,user,session,second_object,testurl,owner,write,owner_override):
                    return False
    elif session.get('password',''):
        # If a guest is logged in
        # Get the guest's record based on the session
        target_guest = Guest.objects.get(pk=session['guest'])
        # Deny access if a guest is requesting a different guest's records
        if isinstance(target_object,Guest) and not target_object==target_guest:
            return False
        if isinstance(target_object,(Form,Field)):
            if isinstance(target_object,Field):
                target_object = target_object.form
            if not getattr(target_object,'guest_completable'):
                return False
            # If the form being tested is for a specific guest, and locks when completed, and has been completed
            if second_object and target_object.lock_when_complete and GuestFormsCompleted.objects.filter(guest=target_guest,form=target_object)[0].complete:
                return False
        if isinstance(target_object,DynamicFilePermissions):
            # If the requested url does not belong to the requesting guest and belongs to a guest
            if not target_guest == target_object.guest and target_object.guest:
                return False
    elif isinstance(target_object,str):
        # If testing Framework level permission
        if not user.has_perm('guestmanagement.' + str(target_object)):
            return False
    else:
        if hasattr(target_object,'owner') and owner:
            if not user in target_object.owner.all():
                return False

        if hasattr(target_object,'permissions_write') and write:
            if list(target_object.permissions_write.all()) != []:
                test = [True for i in target_object.permissions_write.all() if user in i.users.all()]
                if not test:
                    return False
            elif hasattr(target_object,'form'):
                if not testPermission(target_object.form,user,write=write):
                    return False
        else:
            if hasattr(target_object,'permissions_must_have'):
                for i in target_object.permissions_must_have.all():
                    if user not in i.users.all():
                        if not hasattr(target_object,'owner') or not (owner_override and user in target_object.owner.all()):
                            return False
            if hasattr(target_object,'permissions_may_have'):
                test_list = [True for i in target_object.permissions_may_have.all() if user in i.users.all()]
                if test_list==[] and target_object.permissions_may_have.all():
                    if not hasattr(target_object,'owner') or not (owner_override and user in target_object.owner.all()):
                        return False

        if hasattr(target_object,'program'):
            if list(target_object.program.all()) != []:
                test_list=[True for i in getattr(target_object,'program').all() if testPermission(i,user,write=write)]
                if test_list==[] and [True for i in target_object.program.all() if list(i.permissions_may_have.all()) or list(i.permissions_must_have.all())]:
                    return False

        if second_object:
            if isinstance(second_object,(str,unicode)):
                second_object = Guest.objects.get(pk=second_object)
            s1 = set(second_object.program.all())
            if hasattr(target_object,'form'):
                s2 = set(target_object.form.program.all())
            else:
                s2 = set(target_object.program.all())
            test = [True for i in list(s1.intersection(s2)) if testPermission(i,user,write=write)]
            if test==[]:
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
        success = False
        while not success:
            try:
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
                success = True
            except MultipleObjectsReturned, e:
                deduplicateGuestInfo(e,guest)
                success = False
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

def deduplicateGuestInfo(e,guest,table=GuestData):
    # Retrieve all data
    b=table.objects.filter(guest=guest)
    # Initialize holding dict
    c={}
    # Iterate through data
    for i in b:
        # Obtain key based on table type
        if isinstance(i,GuestData):
            key=i.field.name
            value = 'value'
        elif isinstance(i,GuestFormsCompleted):
            key=i.form.name
            value = 'complete'
        # If data not in holding dict
        if c.get(key,None)==None:
            # Update holding dict
            c[key]=i
        elif getattr(c[key],value)==getattr(i,value):
            # If data already in holding dict and values match
            # Delete second data point
            i.delete()
        else:
            # If data already in holding dict and values do not match
            # Reraise exception
            raise e

# Views

@login_required
def quickfilter(request):
    '''
        View for executing one filter against the database and updating multiple records
    '''
    context=baseContext(request)
    perm_list = Permission.objects.filter(users=request.user)
    program_list = Program.objects.filter(Q(Q(permissions_must_have__in=perm_list)|Q(permissions_must_have__isnull=True)),Q(Q(permissions_may_have__in=perm_list)|Q(permissions_may_have__isnull=True))).distinct()
    form_list = Form.objects.filter(Q(Q(permissions_must_have__in=perm_list)|Q(permissions_must_have__isnull=True)),Q(Q(permissions_may_have__in=perm_list)|Q(permissions_may_have__isnull=True)),program__in=program_list)
    fields = [i for i in Field.objects.filter(form__in=form_list) if testPermission(i,request.user)]
    field_dict = {}
    for i in fields:
        field_dict[i.form.name]=field_dict.get(i.form.name,[])
        field_dict[i.form.name].append(i.name)
    context.update({'form_list':json.dumps([i.name for i in Form.objects.all() if testPermission(i,request.user)]),
                    'field_list':json.dumps(field_dict),
                    'query_list':QuickFilter.objects.filter(user=request.user),
                    })
    if request.POST:
        if request.POST.get('load',False) and request.POST['load_query']:
            quick_filter = QuickFilter.objects.get(name=request.POST['load_query'],user=request.user)
            if not testPermission(['and']+list(quick_filter.field.all()),request.user):
                messages.add_message(request, messages.INFO, 'You may not view field %s.  Did permissions change?'%list(quick_filter.field.all()))
            else:
                context.update({'submission': [quick_filter.form.name, json.dumps([i.name for i in quick_filter.field.all()]), quick_filter.criteria],
                                'write_perm':json.dumps([testPermission(i,request.user,write=True) for i in quick_filter.field.all()]),
                                })
        elif request.POST.get('search',False):
            guest_list = []
            form_list = []
            field_list = []
            criteria = []
            index = '0'
            while isinstance(index,str):
                form = request.POST.get('form_criteria_'+index,False)
                if form:
                    field = request.POST.get('field_criteria_'+index,False)
                    if field:
                        operator = request.POST.get('operator_'+index,False)
                        if operator:
                            value = request.POST.get('value_'+index,False)
                            if value:
                                criteria.append([form,field,operator,value])
                index = str(int(index)+1)
                if not request.POST.get('form_criteria_'+index,False) and request.POST.get('form_criteria_'+index,False)!='':
                    index = False

            index = '0'
            while isinstance(index,str):
                field = request.POST.get('field_select_'+index,False)
                if field:
                    try:
                        field_list.append(Field.objects.get(name=field))
                    except ObjectDoesNotExist:
                        messages.add_message(request, messages.INFO, "Field %s does not exist"%field)
                index = str(int(index)+1)
                if not request.POST.get('field_select_'+index,False) and request.POST.get('field_select_'+index,False)!='':
                    index = False
            
            
            for i in criteria:
                eqkwargs = {}
                nekwargs = {}
                if i[0] != 'Guest':
                    eqkwargs['field__name']=i[1]
                    operator = 'value__%s'%report_processor.filter_dict[i[2]]
                    if operator == '<>':
                        nekwargs[operator]=i[3].replace('True',"checked='checked'")
                    else:
                        eqkwargs[operator]=i[3].replace('True',"checked='checked'")
                    current_guest_list = list(GuestData.objects.filter(**eqkwargs).exclude(**nekwargs).values_list('guest',flat=True))
                else:
                    operator = '%s__'%i[1]
                    filter_table = Guest.objects
                    if i[1]=='Program':
                        operator += 'name__'
                        if i[2] == '=':
                            # Change filter table for equals
                            filter_table = Guest.objects.annotate(num_prog=Count('program'))
                            eqkwargs['num_prog']=1
                    operator = operator.lower().replace(' ','_')
                    operator = operator + report_processor.filter_dict[i[2]]
                    if i[2] == '<>':
                        nekwargs[operator]=i[3].replace('True',"checked='checked'")
                    else:
                        eqkwargs[operator]=i[3].replace('True',"checked='checked'")
                    current_guest_list = list(filter_table.filter(**eqkwargs).exclude(**nekwargs).distinct().values_list('id',flat=True))
                if guest_list==[]:
                    guest_list = set(current_guest_list)
                else:
                    guest_list = guest_list & set(current_guest_list)
            guest_list = list(guest_list)
            guest_list = [i for i in Guest.objects.filter(id__in=guest_list) if testPermission(i,request.user)]
            if not field_list or not request.POST['form_select']:
                messages.add_message(request, messages.INFO, "No form/field selected... sorry, I have no idea what you wanted, let's start over.")
                return redirect(request.get_full_path())
            target_form = Form.objects.get(name=request.POST['form_select'])
            if not testPermission(target_form,request.user) or False in [testPermission(i,request.user) for i in field_list]:
                return beGone('get lost hacker')
            context.update({'submission': [target_form.name, json.dumps([i.name for i in field_list]), json.dumps([[str(i) for i in a] for a in criteria])]})
            field_types = {'boolean':'<input type="checkbox" name="%s" %s %s />',
                            'text_box':'<input name="%s" %s value="%s" />',
                            'date':"<input class='datePicker' name='%s' readonly='true' type='text' %s value='%s' />",
                            'comment_box':'<textarea name="%s" %s >%s</textarea>',
                            'drop_down':'<select name="%s" %s value="%s" >',
                            'list':'<select name="%s" multiple="multiple" %s value="%s" >',
                            }
            html_return = []
            html_dict = {}
            
            if [True for i in field_list if i.time_series and testPermission(i,request.user,write=True)]:
                html_return.append("date: <input class='datePicker' name='form_date' readonly='true' type='text' /><br />")
                html_return.append("time: <input class='timePicker' name='form_time' readonly='true' type='text' /><br />")
                html_return.append('update current record <input type="checkbox" name="current_update" /><br />')
            guest_data_dict = {i:{} for i in guest_list}
            guest_datas = GuestData.objects.filter(guest__in=guest_list,field__in=field_list)
            for eachdata in guest_datas:
                guest_data_dict[eachdata.guest].update({eachdata.field:eachdata.value})
            
            for eachfield in field_list:
                if field_types.get(eachfield.field_type,False):
                    for i in guest_list:
                        html_dict[i] = html_dict.get(i,[])
                        answer = guest_data_dict[i].get(eachfield,'') if not eachfield.blank_each_time else ''
                        input_line = ''
                        if eachfield.field_type=='boolean':
                            input_line = '<input name="submit_field_%s" hidden>'%(eachfield.name+"_"+str(i.id),)
                        input_line += field_types[eachfield.field_type]%(
                            "submit_field_"+eachfield.name+"_"+str(i.id),
                            {True:'',False:'disabled'}[testPermission(eachfield,request.user,second_object=i,write=True)],
                            answer,
                        )
                        html_dict[i].append(input_line)
                        if eachfield.field_type == 'drop_down' or eachfield.field_type == 'list':
                            html_dict[i][-1] +=''.join(['<option value="%s" selected="selected" >%s</option>'%(a,a) if a==answer else '<option value="%s">%s</option>'%(a,a) for a in eachfield.dropdown_options.split('\r\n')])
                else:
                    messages.add_message(request, messages.INFO, 'Invalid Field Type "%s": Pick a Different Field'%eachfield.field_type)
            html_return.append('<table><tr><th>Guest</th>'+''.join(['<th>%s</th>'%i.name for i in field_list])+'</tr>')
            for eachguest in sorted(html_dict.keys(),key=lambda x: x.last_name.lower()):
                html_return.append('<tr><td>'+eachguest.last_name+', '+eachguest.first_name+'</td>'+''.join(['<td>%s</td>'%i for i in html_dict[eachguest]])+'</tr>')
            html_return = mark_safe(''.join(html_return)+'</table>')
            context.update({'form':html_return})
            context.update({'write_perm':json.dumps([testPermission(i,request.user,write=True) for i in field_list])})

            if request.POST.get('save',False) == 'on' and request.POST.get('save_name',False):
                quick_filter = QuickFilter.objects.get_or_create(user=request.user,name=request.POST['save_name'])[0]
                quick_filter.form=target_form
                quick_filter.field=field_list
                quick_filter.criteria = json.dumps(criteria)
                quick_filter.save()
        else:
            time_stamp = datetime.datetime.now()

            field_list = []
            if request.POST.get('form_date',''):
                new_date = parse(request.POST['form_date'])
                time_stamp = time_stamp.replace(year=new_date.year,month=new_date.month,day=new_date.day)
            if request.POST.get('form_time',''):
                new_time = parse(request.POST['form_time'])
                time_stamp = time_stamp.replace(hour=new_time.hour,minute=new_time.minute,second=new_time.second)
            for i in request.POST.keys():
                if i.startswith('submit_field_'):
                    keysplit = i.split('_')
                    field = Field.objects.get(name=keysplit[2])
                    guest = Guest.objects.get(pk=keysplit[3])
                    if testPermission(field,request.user,second_object=guest,write=True):
                        value = request.POST[i]
                        if value == 'on' and field.field_type=='boolean':
                            value = "checked='checked'"
                        current_record = GuestData.objects.get_or_create(guest=guest,field=field)[0]
                        if not field.time_series:
                            current_record.value = value
                            current_record.save()
                        else:
                            new_record = GuestTimeData.objects.get_or_create(guest=guest,field=field,date=time_stamp)[0]
                            new_record.value = value
                            new_record.save()
                            previous_records = GuestTimeData.objects.filter(guest=guest,field=field,date__gte=time_stamp).order_by('date')
                            if request.POST.get('current_update',''):
                                for a in previous_records[1:]:
                                    a.value = value
                                    a.save()
                                current_record.value = value
                                current_record.save()
                            else:
                                previous_record = previous_records.last()
                                if current_record.value != previous_record.value:
                                    current_record.value = previous_record.value
                                    current_record.save()
                    else:
                        messages.add_message(request, messages.INFO, 'Commit denied for field %s on guest %s'%(field.id,guest.id))
            messages.add_message(request, messages.INFO, 'Commit Completed')
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
                args.append(Q(id=request.POST['id']))
            if request.POST['last_name']!='':
                args.append(Q(last_name__icontains=request.POST['last_name']))
            if request.POST['barcode']!='':
                args.append(Q(barcode=request.POST['barcode']))
                possible_guests = Guest.objects.filter(barcode=request.POST['barcode'])
                if len(possible_guests)==1:
                    target_guest=possible_guests[0].id
                    request.session['password']=True
                    request.session['guest']=target_guest
                    request.session.set_expiry(600)
                    return redirect('/guestmanagement/view/guest/%s/'%target_guest)
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
    # Initialize context
    context=baseContext(request)
    if target_type:
        target_type.replace('_',' ')
    context.update({'target_type':target_type,'target_object':target_object})
    # If the main manage screen (no target type picked yet)
    if not target_type:
        return render(request,'guestmanagement/manage.html',context)
    # Check user for permission to manage or view target type
    if not testPermission(['or','manage_{0}'.format(target_type),'view_{0}'.format(target_type)],request.user):
        return beGone(str(['or','manage_{0}'.format(target_type),'view_{0}'.format(target_type)]))
    # If managing a type but not object (e.g. managing forms but not a specific form)
    if not target_object:
        # Get the list of searchable fields from the target type dictionary
        filter_list = target_type_dict[target_type][0].Meta.list_filter
        # List comprehension to iterate over filter_list and create input boxes for each searchable field
        search_html = ''.join(["%s <input id='%s' type='%s' name='%s'> "%(i[0].replace('_',' ').capitalize(),i[0],'password' if i[0]=='barcode' else 'text',i[0]) for i in filter_list])
        # Add search area to context
        context.update({'search_html':mark_safe(search_html)})
        # Handling input from the just generated search boxes and the selection of guests
        # Returns /view/guest/guest id if a guest was selected
        # Returns a dynamically generated table of search results otherwise
        if request.POST:
            '''
            Should be defunct, pending removal - 2/2/2016
            if request.POST.get('set_guest',''):
                a = GuestmanagementUserSettings.objects.get_or_create(user=request.user)[0]
                a.guest=Guest.objects.get(pk=request.POST['set_guest'])
                a.save()
                return redirect('/guestmanagement/view/guest/%s/'%a.guest.id)
            '''
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
                for i in filter_list if not (i[0]=='barcode' and  request.POST[i[0]]=='')]
            # Get user Content permissions
            perm_list = Permission.objects.filter(users=request.user)
            if hasattr(base_table,'program'): #and not request.user.is_superuser:
                program_list = Program.objects.filter(Q(Q(permissions_must_have__in=perm_list)|Q(permissions_must_have__isnull=True)),Q(Q(permissions_may_have__in=perm_list)|Q(permissions_may_have__isnull=True))).distinct()
                args.append(Q(program__in=program_list))
            # pull in anything owned by the user
            owner_override = []
            if hasattr(base_table,'owner'):
                owner_override = [Q(owner=request.user)]
            # Run the query just created (meatballing permissions) and return distinct entries
            raw_object_list = base_table.objects.filter(Q(*args)|Q(*owner_override)).distinct().filter(*args).order_by('id')
            object_list = []
            # for loop to iterate over the objects returned from the filter and list_display
            # and create a list of lists of viewable fields
            for i in raw_object_list:
                # Run exact test on permission to view object
                if testPermission(i,request.user,owner_override=True):
                    # Determine edit and view permissions on the current object
                    b = [[testPermission(i,request.user,owner=True) if target_type != 'guest' else testPermission(i,request.user,write=True),testPermission(i,request.user)]]
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
            if len(object_list)==1 and request.POST.get('barcode',None) and object_list[0][0][1]:
                return redirect('/guestmanagement/view/guest/%s/'%object_list[0][1])
        # Whether or not a search has been run
        return render(request,'guestmanagement/manage.html',context)
    # End managing a type but not object
    # Test Framework Permissions
    if not testPermission('manage_{0}'.format(target_type),request.user):
        return beGone('manage_{0}'.format(target_type))
    # Initialize a variable used in moving fields from one form to another
    currentform=False
    # If managing an object (e.g. a particular form)
    # If a new object
    if target_object=='new':
        # Check Permissions
        if not testPermission('add_{0}'.format(target_type),request.user):
            return beGone('add_{0}'.format(target_type))
        # Set no instance flag
        target_instance = None
        # Set wording to appear on webpage
        create_or_edit = 'Create New'
    else:
        # Check Framework permissions
        if not testPermission('change_{0}'.format(target_type),request.user):
            return beGone('change_{0}'.format(target_type))
        # Pull current database entry for object being managed
        target_instance = target_type_dict[target_type][1].objects.get(pk=target_object)
        # Check Content permissions
        if not testPermission(target_instance,request.user,owner=True):
            return beGone('Access to this specific %s'%target_type)
        # If changing a guest, verify write permission on program
        if isinstance(target_instance,Guest) and not testPermission(target_instance,request.user,write=True):
            return beGone('Write access to this specific %s'%target_type)
        # user_permission_settings get updated at this point
        if target_type == 'user_permission_settings':
            # Update user_permissions_settings model to include all the permissions the user currently has
            target_instance.permissions = Permission.objects.filter(users__id=target_instance.user.id)
            target_instance.save()
        # Store the current form associate with the target field if applicable
        if target_type == 'field':
            currentform=target_instance.form
        # If loading a report, attach current code to context
        if target_type == 'report':
            context.update({'loaded_report':target_instance.code})
        # Set wording to appear on webpage
        create_or_edit = 'Modify'
        # Check view permission
        context.update({'view_perm':testPermission(target_instance,request.user)})
    # If a report add all copyable reports to context
    if target_type == 'report':
        context.update({'other_reports':[[i.id,i.name] for i in Report.objects.all() if testPermission(i,request.user,owner_override = True)]})
    # Add wording to context
    context.update({'create_or_edit':create_or_edit})
    # Initialize form variable
    form = ''
    # If changes are being made either creation, deletion, or modification of a specific instance of the target_type
    if request.POST:
        # If deleting the target object
        if request.POST.get('delete_{0}'.format(target_type),''):
            # Check Framework Permissions
            if not testPermission('delete_{0}'.format(target_type),request.user):
                return beGone('delete_{0}'.format(target_type))
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
        if 'copy_report' in request.POST.keys():
            if not request.POST['copy_report']:
                messages.add_message(request, messages.INFO, 'Choose report to copy')
                return redirect(request.get_full_path())
            copy_report = Report.objects.get(pk=request.POST['copy_report'])
            if not testPermission(copy_report,request.user,owner_override=True):
                messages.add_message(request, messages.INFO, 'You have no permission to copy that report')
                return redirect(request.get_full_path())
            if not target_instance:
                name = copy_report.name+' (copy)'
                target_instance,created = Report.objects.get_or_create(name=name)
                while not created:
                    name = name + ' (copy)'
                    target_instance,created = Report.objects.get_or_create(name=name)
            target_instance.description = copy_report.description
            target_instance.code = copy_report.code
            target_instance.owner = [request.user]
            target_instance.variables = copy_report.variables
            target_instance.permissions_must_have = copy_report.permissions_must_have.all()
            target_instance.permissions_may_have = copy_report.permissions_may_have.all()
            target_instance.save()
            return redirect('/guestmanagement/manage/report/%s/'%target_instance.id)

                
        # Initialize created flag
        created=False
        # If this is a new object being created there will not yet be a target_instance
        if not target_instance:
            # Guests are tracked by the id field, which needs to have a default added to the post
            if target_type == 'guest':
                targetid=Guest.objects.all().order_by("-id")
                if not targetid:
                    targetid=1
                else:
                    targetid=targetid[0].id+1
                request.POST['id']=targetid
            # get the search_field from the reference dictionary for the target_type and link it to the value from the submitted form
            kwargs = {'{0}'.format(target_type_dict[target_type][2]):request.POST[target_type_dict[target_type][2]]
                                                                        if target_type != 'user_permission_setting' else User.objects.get(pk=request.POST['user'])}
            # get the database model object from the reference dictionary and dump the unique identifier into it
            target_instance,created = target_type_dict[target_type][1].objects.get_or_create(**kwargs)
            # if a new object was not created (user trying to reuse the unique identifier)
            if not created:
                messages.add_message(request, messages.INFO, '%s already exists!'%target_type)
                return redirect('/guestmanagement/manage/%s/'%target_type)
            # Special processing for new fields
            if target_type=='field':
                if request.POST['form']:
                    if not testPermission(Form.objects.get(id=request.POST['form']),request.user,owner=True):
                        return beGone(': You do not own the selected form')
                    # set field objects order to the end of their parent form object (will = 0 if there is one field in the form)
                    starting_order = Field.objects.filter(form=Form.objects.get(id=request.POST['form'])).aggregate(Max('order'))['order__max']
                    # if there are no fields in the form
                    if not starting_order and starting_order != 0:
                        # Create a default starting order
                        starting_order = -1
                    # increase the starting order by one to miss the last field already on the form
                    target_instance.order=starting_order+1
        # There is now a target_instance whether it is just created or being modified
        # Initialize hashpassword flag
        hashpassword=True
        # If changing a guest but no password provided
        if target_type=='guest' and not request.POST.get('password',''):
            # Set submitted password to password hash on file
            request.POST['password']=target_instance.password
            # Set flag to not hash password
            hashpassword=False
        # If changing a guest but no barcode provided
        if target_type=='guest' and not request.POST.get('barcode',''):
            request.POST['barcode']=target_instance.barcode
        # get the new/modify form from the reference dictionary and bind the submitted data to it
        form = target_type_dict[target_type][0](request.POST,request.FILES,instance=target_instance)
        # Set sanity check flag
        sanity_check = True
        # Run sanity check on fields
        if target_type == 'field':
            if (request.POST.get('field_type','')=='list' or request.POST['field_type']=='drop_down'):
                if not request.POST.get('dropdown_options',''):
                    messages.add_message(request, messages.INFO, '%s requires drop down options'%request.POST['field_type'])
                    sanity_check = False
                if "'" in request.POST.get('dropdown_options',''):
                    messages.add_message(request, messages.INFO, "%s drop down options cannot contain apostrophes"%request.POST['field_type'])
                    sanity_check = False
            if request.POST.get('field_type','')=='attachment' and not request.POST.get('attachment',''):
                messages.add_message(request, messages.INFO, 'Select an attachment')
                sanity_check = False
            if request.POST.get('field_prerequisite','') and request.POST.get('required',''):
                messages.add_message(request, messages.INFO, 'Fields with prerequisites cannot be required')
                sanity_check = False
            if request.POST.get('blank_each_time','') and not request.POST.get('time_series',''):
                messages.add_message(request, messages.INFO, 'Fields blanking every time must be time series')
                sanity_check = False
        if target_type == 'guest':
            test = [True for i in Program.objects.filter(id__in=request.POST.getlist('program')) if testPermission(i,request.user,write=True) and testPermission(i,request.user)]
            if not test:
                messages.add_message(request, messages.INFO, 'You lack write permission on any of the selected programs')
                sanity_check = False
            # Test for unique barcode
            if request.POST.get('barcode',''):
                test = Guest.objects.filter(barcode=request.POST['barcode'])
                if len(test)!=0 and (len(test)>1 or test[0]!=target_instance):
                    messages.add_message(request, messages.INFO, 'Guest barcodes must be unique')
                    sanity_check = False
                    
        # If the form has all the required data
        if form.is_valid() and sanity_check:
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
                # Record program history
                a = ProgramHistory.objects.get_or_create(date=datetime.datetime.now(),guest=myobject)[0]
                a.program=myobject.program.all()
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
                filepermissionlist.permissions_may_have = myobject.permissions_may_have.all()
                filepermissionlist.permissions_must_have = myobject.permissions_must_have.all()
                filepermissionlist.save()
            # Special processing for changing user permissions
            if target_type=='user_permission_setting':
                # Remove user from all permissions
                permission_list = Permission.objects.filter(users__id=target_instance.user.id)
                for i in permission_list:
                    i.users.remove(target_instance.user)
                # Update all affected permissions
                for i in target_instance.permissions.all():
                    i.users.add(target_instance.user)
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
            context.update({'loaded_report':json.dumps(json.loads(target_instance.code)[1]) if target_instance.code else json.dumps([])})
        # Pull all the forms from the database which the user is allowed to see
        all_forms_list = sorted([i.name for i in Form.objects.all() if testPermission(i,request.user)])
        # Pull all fields from the database which the user is allowed to see
        all_field_dict = {i:sorted([[a.name.replace('(',''),a.field_type] for a in Field.objects.filter(form__name=i).distinct() if testPermission(a,request.user)]) for i in all_forms_list}
        all_field_dict.update({'date':[['date','date']],'guest':[['id','id'],['first_name','text_field'],['middle_name','text_field'],['last_name','text_field'],['ssn','text_field'],['program','list'],['picture','url'],['image_tag','picture']]})
        # Put the list of fields and forms into the context
        context.update({'all_forms_list':all_forms_list,'all_field_dict':json.dumps(all_field_dict),'available_functions':json.dumps([[i,list(report_processor.functions[i].func_code.co_varnames)[:report_processor.functions[i].func_code.co_argcount]] for i in report_processor.functions.keys()])})
        # Put helper variables in context
        context.update({'helper_variables':json.dumps(report_processor.tableVariables.keys())})
    # Add the form and instance to the context
    context.update({'form':form.as_p(),'target_object':target_instance or target_object})
    # Serve up the page :)
    return render(request,'guestmanagement/manage.html',context)

def unsetcomplete(request,form_id,guest_id):
    '''
    View for allowing guests or staff to recomplete a previously completed form
    does not return a template of its own, and is always called as a GET with a next redirect
    '''
    target_form = Form.objects.get(pk=form_id)
    target_guest = Guest.objects.get(pk=guest_id)
    if not testPermission('delete_guestformscompleted',request.user):
        return beGone('delete_guestformscompleted')
    if not testPermission(target_form,request.user,second_object=target_guest,write=True):
        return beGone('Write Permission %s'%target_guest.id)
    a = GuestFormsCompleted.objects.get_or_create(guest=target_guest,form=target_form)[0]
    a.complete = False
    a.save()
    return redirect(request.GET['next'])

def setscore(request,form_id,guest_id):
    '''
    View to allow forced setting of scored forms
    will continue to show setscore template until a valid score is entered
    '''
    context = baseContext(request)
    target_form = Form.objects.get(pk=form_id)
    target_guest = Guest.objects.get(pk=guest_id)
    if not testPermission('change_guestformscompleted',request.user):
        return beGone('change_guestformscompleted')
    if not testPermission(target_form,request.user,second_object=target_guest,write=True):
        return beGone('Write Permission %s'%target_guest.id)
    if request.POST:
        try:
            score = int(request.POST.get('score',''))
            a = GuestFormsCompleted.objects.get_or_create(form=target_form,guest=target_guest)[0]
            a.score=request.POST['score']
            a.save()
            return redirect(request.GET['next'])
        except ValueError:
            messages.add_message(request, messages.INFO, 'Invalid Score Value')
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
    # Test Permission to view or guest permission to view specific object
    if not testPermission(['or' if target_type != 'report' else 'and','view_{0}'.format(target_type),target_object],request.user,request.session,second_object):
        return beGone('lacking%s view_%s%s'%(' either' if second_object else "",
                                                target_type,
                                                ' or view guest %s'%second_object if second_object else "",
                                            ))
    # If viewing specific instance of target object
    if second_object:
        if not testPrerequisites(target_object,second_object):
            return beGone(str(second_object))
        if target_type=='form':
            if not testPermission(['and','view_guest',Guest.objects.get(pk=second_object)],request.user,request.session):
                return beGone('view_guest')
    context=baseContext(request)
    # If the user is not authenticated, it must be a logged in guest to have made it past the above permissions test
    if not request.user.is_authenticated():
        context.update({'guest_logged_in':True})
    link_list = None
    context.update({'target_type':target_type,'target_object':target_object})
    if target_type == 'guest':
        # Check for permission to view guest
        if not testPermission(target_object,request.user,request.session):
            return beGone('view guest %s'%target_object.id)
        context.update({'view_image':target_object.image_tag})
        # create list of forms based on prerequisites and permissions along with status of each and links to view/complete
        try:
            form_list = [(i,{True:'Completed',False:'Incomplete'}[GuestFormsCompleted.objects.get_or_create(guest=target_object,form=i)[0].complete],i.lock_when_complete,GuestFormsCompleted.objects.get_or_create(guest=target_object,form=i)[0].score,i.auto_grade) for i in Form.objects.filter(program__in=target_object.program.all()).distinct() if testPrerequisites(i,target_object) and testPermission(i,request.user,request.session,second_object)]
        except MultipleObjectsReturned, e:
            deduplicateGuestInfo(e,target_object,GuestFormsCompleted)
            form_list = [(i,{True:'Completed',False:'Incomplete'}[GuestFormsCompleted.objects.get_or_create(guest=target_object,form=i)[0].complete],i.lock_when_complete,GuestFormsCompleted.objects.get_or_create(guest=target_object,form=i)[0].score,i.auto_grade) for i in Form.objects.filter(program__in=target_object.program.all()).distinct() if testPrerequisites(i,target_object) and testPermission(i,request.user,request.session,second_object)]
        form_list = sorted(form_list,key=lambda x: x[0].name)
        context.update({'form_list':form_list})
    if target_type == 'form':
        # Test for permission to view particular form
        if not testPermission(target_object,request.user,request.session):
            return beGone('view form %s'%target_object.id)
        form=''
        field_list = Field.objects.filter(form=target_object)
        extra_fields = Field.objects.filter(extra_forms=target_object)
        # if there is no second_object, no guest is being associated with this form, therefore any posted data relates to moving fields
        if not second_object:
            write_perm = testPermission(['and','change_form',target_object,target_object],request.user,owner=True)
            context.update({'write_perm':write_perm})
            if request.POST:
                # Test Framework and Content permissions
                if not write_perm:
                    return beGone('either change_form or not owner of form %s'%target_object.id)
                # Move Field
                moveField(Field.objects.get(pk=request.POST['move_field']),request.POST['move_type'])
        else:
            second_object = Guest.objects.get(pk=second_object)
            context.update({'write_perm':True if [True for i in field_list if testPermission(i,request.user,request.session,second_object=second_object,write=True)] else False})
            context.update({'second_object':second_object})
            if request.POST:
                # If a form is being completed
                # If a form was solely being viewed
                if request.POST.get('submit_form','')=='Continue':
                    return redirect('/guestmanagement/view/guest/%s/'%second_object.id)
                # Test Framework Permissions on staff
                if request.user.is_authenticated():
                    if not testPermission(target_object,request.user,request.session,second_object=second_object,write=True):
                        return beGone('No write permission on %s or %s'%(target_object,second_object.id))
                # Test for completed forms
                if target_object.lock_when_complete:
                    completed_form = GuestFormsCompleted.objects.get_or_create(guest=second_object,form=target_object)
                    if completed_form[1]:
                        completed_form[0].delete()
                    else:
                        # Test for completed forms permissions
                        completed_form = completed_form[0]
                        if completed_form.complete:
                            if not testPermission('change_guestformscompleted',request.user):
                                return beGone('change_guestformscompleted')
                # check for incomplete required fields and add appropriate error messages
                required_test={i:'<ul class="errorlist"><li>This field is required.</li></ul>' for i in field_list.order_by('order') if i.required and not request.POST.get(i.name,'') and i.field_type!='boolean' and testPrerequisites(i,second_object) and testPermission(i,request.user,request.session,second_object)}
                if not required_test:
                    time_stamp=datetime.datetime.now()
                    if getattr(target_object,'single_per_day',None):
                        date_list = [i.name for i in field_list.order_by('order') if i.field_type=='date']
                        if date_list:
                            time_stamp = parse(request.POST.get(date_list[0],'') or time_stamp.strftime('%m/%d/%Y'))
                        else:
                            time_stamp = parse(time_stamp.strftime('%m/%d/%Y'))
                    for i in field_list.order_by('order'):
                        # Test write permission on field
                        if not testPermission(i,request.user,request.session,second_object=second_object,write=True):
                            messages.add_message(request, messages.INFO, 'No write permission on %s for %s...skipped'%(i.name,second_object.id))
                            continue
                        if testPrerequisites(i,second_object):
                            try:
                                a = GuestData.objects.get_or_create(guest=second_object,field=i)[0]
                            except MultipleObjectsReturned, e:
                                deduplicateGuestInfo(e,second_object)
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
                            elif i.field_type == 'drop_down' and not request.POST.get(i.name):
                                a.value = ""
                            elif i.field_type == 'list':
                                a.value=request.POST.getlist(i.name)
                            elif i.field_type == 'comment_box' and i.add_only and not request.user.has_perm('guestmanagement.change_fixed_field'):
                                if a.value:
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
                                if getattr(target_object,'single_per_day',None) and i.blank_each_time:
                                    b.value = a.value or b.value
                                else:
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
                    form=createForm(field_list,request.user,request,second_object,required_test,extra_fields=extra_fields)
                    context.update({'required_failed':True})
            # if no form was created from request.POST or no request.POST submitted
            # Create form
            while not form:
                try:
                    # Try building form
                    form=createForm(field_list,request.user,second_object=second_object,session=request.session,extra_fields=extra_fields)
                except MultipleObjectsReturned, e:
                    # If guest has more than one datapoint for a field
                    # deduplicate
                    deduplicateGuestInfo(e, second_object)
                    # Reloop while loop to build form
                    form = ''


            context.update({'form':form})
        context.update({'field_list':field_list.order_by('order')})
        # Update general information at the bottom of the screen
        link_list=[['Form Prerequisites','prerequisite',target_object.form_prerequisite.all()],
                    ['Programs using form','program',target_object.program.all()],
                    ['May have permissions','permission',target_object.permissions_may_have.all()],
                    ['Must have permissions','permission',target_object.permissions_must_have.all()],
                    ['Write Permissions','permission',target_object.permissions_write.all()],
                ]
    if target_type == 'field':
        # Update general information at the bottom of the screen
        link_list=[['Parent form','form',[target_object.form]],
                    ['Other fields on form','field',Field.objects.filter(form=target_object.form).exclude(pk=target_object.id).distinct()],
                    ['Required prerequisites','prerequisite',target_object.field_prerequisite.all()],
                    ['May have permissions','permission',target_object.permissions_may_have.all()],
                    ['Must have permissions','permission',target_object.permissions_must_have.all()],
                    ['Write Permissions','permission',target_object.permissions_write.all()],
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
                    ['Write Permissions','permission',target_object.permissions_write.all()],
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
    if not testPermission(Report.objects.get(pk=report_id),request.user):
        return beGone('You may not view report')
    context=baseContext(request)
    # Retrieve compiled code from report code object
    report_code = json.loads(Report.objects.get(pk=report_id).code)[0]
    # Retrieve report name
    report_name=Report.objects.get(pk=report_id).name
    # Create a file like buffer
    output = StringIO()
    # Initialize environment
    env = report_processor.Env({'print':output.write,'user':request.user,'__traceback__':{0:[]},'__trace_index__':0})
    # Add user defined variables to environment
    for k,v in request.GET.iteritems():
        if k.startswith('variable__'):
            env[k.replace('variable__','')]=v
    # Add external functions, helper variables, internal functions to report environment
    env.update(report_processor.functions)
    env.update(report_processor.tableVariables)
    env.update(report_processor._functions)
    try:
        # Run Report
        success = report_processor.listProcess(env, ['do']+report_code)
    except Exception as e:
        # Display errors
        ff_dict = {'list':True,'query':True,'if':True,'display':True,'sum':True,'count':True}
        human_code = json.loads(Report.objects.get(pk=report_id).code)[1]
        current_human_code = 0
        trace_back = env['__traceback__']
        max_trace = max(trace_back.keys())
        trace_ind_list = iter(xrange(0,max_trace+1))
        current_trace = trace_ind_list.next()
        while current_trace or current_trace==0:
            this_trace = iter(trace_back[current_trace])
            each_element = this_trace.next()
            
            while each_element:
                skip=True
                if each_element != 'do':
                    skip=False
                    while human_code[current_human_code][0]!=each_element:
                        current_human_code += 1
                
                try:
                    each_element = this_trace.next()
                    if ff_dict.get(human_code[current_human_code][0],False) and not skip:
                        count=1
                        while count>0:
                            current_human_code+=1
                            if ff_dict.get(human_code[current_human_code][0],False):
                                count += 1
                            elif human_code[current_human_code][0]=='end':
                                count -= 1
                
                except StopIteration:
                    break

            try:
                current_trace = trace_ind_list.next()
            
            except StopIteration:
                break
        env['print']('<pre>')
        env['print'](str(e))
        env['print']('\n-----------\n')
        env['print']('Error in line %s:\n'%current_human_code)
        env['print']('%s: %s\n'%(current_human_code,str(human_code[current_human_code])))
        if ff_dict.get(each_element,False):
            include_dict = {'and':True,'or':True,'extrafield':True}
            next_line = current_human_code+1
            while include_dict.get(human_code[next_line][0],False):
                env['print']('%s: %s\n'%(next_line,str(human_code[next_line])))
                next_line += 1
        env['print']('-----------\nVariable Dictionary\n-----------\n')
        var_list = ['%s = %s'%(str(k),str(v).replace('<',"").replace('>','')) for k,v in env.__get_variable_state__().iteritems() if '__' not in k and not callable(v)]
        env['print']('\n'.join(var_list))
        env['print']('</pre>')
    env = None
    # Display results
    download_path = request.get_full_path()
    if "?" not in download_path:
        download_path += '?filename=%s'%report_name
    else:
        download_path += '&filename=%s'%report_name
    context.update({'report':mark_safe(output.getvalue()),'report_name':report_name,'download_path':download_path})
    if request.GET.get('filename',''):
        dl = StringIO()
        dl.write(output.getvalue())
        dl.seek(0,0)
        response = HttpResponse(dl, content_type='application/vnd.ms-excel; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="%s"' % request.GET['filename']
        return response
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
    # Retrieve guest object
    target_guest = Guest.objects.get(pk=target_guest)
    # Retrieve form object
    target_form = Form.objects.get(pk=target_form)
    # Test permission to change past forms
    if not testPermission(['and','change_guesttimedata',target_form],request.user,second_object=target_guest,write=True):
        return beGone('change_guesttimedata')
    # Set base context
    context=baseContext(request)
    # Retrieve field list for form
    target_field_list = Field.objects.filter(Q(form=target_form)&(Q(time_series=True)|Q(field_type='title'))).order_by('order')
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
        # Retrieve affected guest time data
        target_guesttimedata = GuestTimeData.objects.get(pk=target_guesttimedata)
        # Retrieve all guest time data from that date
        guesttimedata_list = GuestTimeData.objects.filter(date=target_guesttimedata.date,guest=target_guesttimedata.guest,field__form=target_guesttimedata.field.form).distinct()
        # If posting changes
        if request.POST:
            # If user trying to delete data
            if request.POST.get('delete'):
                # If not allowed to delete
                if not testPermission('delete_guesttimedata',request.user):
                    return beGone('delete_guesttimedata')
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
            if not target_form.single_per_day:
                new_date = new_date + new_time
            else:
                new_date = new_date + "00:00 AM"
                date_list = [i.name for i in sorted([i.field for i in guesttimedata_list],key=lambda x: x.order) if i.field_type == 'date']
                if date_list:
                    new_date = (request.POST.get(date_list[0], '') or new_date.split(' ')[0])  + " 00:00 AM"
            # Convert date to datetime
            new_date = parse(new_date)
            # Retrieve potential conflicts
            test_list = GuestTimeData.objects.filter(guest=target_guest,date=new_date,field__in=[i.field for i in guesttimedata_list])
            # If potential conflicts
            if len(test_list)>0 and new_date != target_guesttimedata.date:
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
                current_record = GuestData.objects.get_or_create(field=i.field,guest=i.guest)[0]
                previous_records = GuestTimeData.objects.filter(date__gt=new_date,field=i.field,guest=i.guest).order_by('date')
                if len(previous_records)==0:
                    current_record.value = i.value
                    current_record.save()
                else:
                    previous_record=previous_records.last()
                    if previous_record.value!=current_record.value:
                        current_record.value=previous_record.value
                        current_record.save()
            messages.add_message(request, messages.INFO, 'Form Changed')
            return redirect('/guestmanagement/view/guest/%s/'%target_guest.id)
        else:
            # If no update being posted
            # Build dictionary of current values on particular form
            request.POST = {}
            for i in guesttimedata_list:
                if i.value == None:
                    i.value = ''
                    i.save()
                request.POST.update({i.field.name:i.value.replace("checked='checked'",'on')})
            # Create form
            form = createForm(target_field_list,request.user,second_object=target_guest,request=request,edit_past=True)
            context.update({'form':form})
    # Serve it up
    context.update({'target_guest':target_guest, 'target_form':target_form})
    return render(request,'guestmanagement/edit.html',context)

def reportwiki(request):
    context = baseContext(request)
    _doc = [[i,mark_safe(inspect.getdoc(report_processor._functions[i]))] for i in report_processor._functions.keys()]
    doc = [[i,mark_safe(inspect.getdoc(report_processor.functions[i]))] for i in report_processor.functions.keys()]
    context.update({'internal_documentation':_doc,'external_documentation':doc})
    return render(request,'guestmanagement/reportwiki.html',context)
    
