from __future__ import print_function
from scheme.symbol import Symbol
from guestmanagement import views
import datetime,dateutil,calendar
import time

__author__ = 'lperkins2'

import scheme
import cStringIO
import django.db.models.manager
from django.db.models import Q
from guestmanagement.models import GuestTimeData, GuestData, Guest, Field
import django.db.models.base
from collections import Iterable
from ast import literal_eval
import sqlparse
from zope.interface import implements
from collections import Mapping
from operator import or_, and_
from django.utils import timezone

MacroSymbol = scheme.macro.MacroSymbol
Macro = scheme.macro.Macro
from scheme.environment import Environment
from scheme.procedure import Procedure
from django.db.models.query import QuerySet


lf = open('scheme.log', 'a')


class AbortReport(Exception): pass
class AccessDenied(Exception): pass

from scheme.debug import LOG


import types



class IdentifierList(object):
    implements(Procedure)

    def __init__(self, *args):
        pass

    def __call__(self, processer, params):
        LOG(31, params)
        return [params[0][0], [i[1] for i in params if i != ',']]


class Identifier(object):
    implements(Macro)

    def __init__(self, *args):
        pass

    def __call__(self, processer, params):
        if len(params) == 1:
            return params[0].toObject(processer.cenv)
        if not processer.in_where:
            return MacroSymbol("Table:Field").setObj([params[0], str.join('', params[2:])])
        if params[0] == "field":
            f = Field.objects.filter(name=params[2])
            if len(f) == 0:
                f = Field.objects.get(name=params[2].replace('_', ' '))
            else:
                f = f[0]
            if not views.testPermission(f.form, processer.user_obj) or not views.testPermission(f.form.program, processer.user_obj):
                raise AccessDenied("Access denied on %r or %r" %(f.form, f.form.program))
            if len(params)==3:
                return MacroSymbol("field__name=%s" % params[2]).setObj({"field": f})
            if params[-1]=='date':
                return MacroSymbol("field__name=%s and date_included" %params[2]).setObj({'field':[f,'date']})
        elif params[0] == 'guestdata' or params[0] == 'guest_time_data':
            return MacroSymbol(params[2]).setObj({params[2]: params[2]})
        else:
            o = "%s__%s" % (params[0], params[2])
            return MacroSymbol(o).setObj({o: None})


op_to_field_string = {
'<': '__lt',
'<=': '__lte',
'>': '__gt',
'>=': '__gte',
'contains': '__icontains'
}


class Comparison(object):
    implements(Macro)

    def __init__(self, *args):
        pass

    def __call__(self, processer, params):
        value = params[2]
        if value == 'True':
            value = "checked='checked'"
        if value == "False":
            value = ""
        if isinstance(value, scheme.symbol.Symbol):
            value = value.toObject(processer.cenv)
        if isinstance(value, list):
            processer.pushStack(value)
            value = processer.process(value, scheme.environment.Environment(processer.env))()
            LOG(89, value)
            processer.popStack(value)
        if params[0] == 'date':
            LOG(72)
            o = MacroSymbol("date__startswith").setObj({"date__startswith": value})
            return o
        processer.pushStack(params[0])
        field_name = processer.process(params[0], scheme.environment.Environment(processer.env))()
        processer.popStack(field_name)

        op = params[1]

        s = op_to_field_string.get(op, '')

        if 'field' in field_name.toObject(None):
            field_name.toObject(None)['value' + s] = value
        else:
            o = str(field_name)
            o = MacroSymbol(o).setObj({o + s: value})
            return o
        return field_name


class Where(object):
    implements(Macro)

    def __init__(self, *args):
        pass

    def __call__(self, processer, params):
        LOG(105, params)
        processer.in_where = True
        ptr_params = iter(params)
        q = Q()
        op = q.__and__
        for param in ptr_params:
            if param == 'date':
                comparator = ptr_params.next()
                value = ptr_params.next()
                if isinstance(value, Symbol):
                    value = value.toObject(processer.cenv)
                if isinstance(value, list):
                    processer.pushStackN()
                    value = processer.process(value, Environment(processer.cenv), processer.callDepth + 1)
                    processer.popStackN()
                if callable(value):
                    value = value()
                q = op(Q(**{"date%s" % (op_to_field_string.get(comparator, "__startswith")): value}))
            if isinstance(param, list):
                LOG(125, param)
                processer.pushStack(param)
                param = processer.process(param, Environment(processer.env), processer.callDepth)
                LOG(128, param())
                processer.popStack(param)
                if isinstance(param, types.FunctionType):
                    param = param()
                if isinstance(param, MacroSymbol):
                    param = param.toObject({})
                if len(param) == 1 and 'field' in param:
                    comparator = ptr_params.next()
                    s = op_to_field_string.get(comparator, '')
                    value = ptr_params.next()
                    if value == "True":
                        value = "checked='checked'"
                    if value == "False":
                        value = ""
                    if isinstance(value, scheme.symbol.Symbol):
                        value = value.toObject(processer.cenv)
                    if isinstance(value, list):
                        LOG(110, value)
                        processer.pushStackN()
                        value = processer.process(value, Environment(processer.cenv), processer.callDepth + 1)
                        processer.popStackN()
                        LOG(112, value)
                    if callable(value):
                        value = value()
                    print(186, param)
                    if 'field' in param:
                        param['value' + s] = value
                    else:
                        o = param.keys()[0]
                        param = {o + s: value}
                LOG(133, param, Q, type(Q))
                q = op(Q(**param))
                continue
            if param == 'and':
                op = q.__and__
                continue
            if param == 'or':
                op = q.__or__
        processer.in_where = False
        LOG(166)
        return MacroSymbol('Q').setObj(q)


class CompoundFieldQueryPart(object):
    @classmethod
    def resetID(cls):
        cls._nextid=0
    @classmethod
    def nextid(cls):
        cls._nextid+=1
        return cls._nextid
    def __init__(self, table, field_id, op=None, value=None, other=None, date=False, queryField=False, field_name=None):
        if op=='value':
            self.op='='
        elif op=='value__lt':
            self.op='<'
        elif op=='value__lte':
            self.op='<='
        elif op=='value__gt':
            self.op='>'
        elif op=='value__gte':
            self.op='>='
        self.id=self.nextid()
        self.table=table
        self.table_alias=table+str(self.id)
        self.field_id=field_id
        self.value=value
        self.date=date
        setattr(self, 'value%i'%self.id, value)
        self.other=other
        self.queryField=queryField
        self.field_name=field_name
    def __select__(self):
        if self.date:
            return None
        if self.table.endswith('guesttimedata') and self.queryField:
            return '%s.id as id%i, %s.value as %s__value, %s.date as %s__date' %(self.table_alias, self.id, self.table_alias, self.field_name, self.table_alias, self.field_name)
        if self.queryField:
            return '%s.id as id%i, %s.value' %(self.table_alias, self.id, self.table_alias)
        return '%s.id as id%i'%(self.table_alias, self.id)
    def __from__(self):
        if self.date:
            return None
        return '%s as %s'%(self.table, self.table_alias)
    def __where__(self):
        if self.queryField:
            return '%(table_alias)s.field_id=%(field_id)i'%self.__dict__
        if self.date:
            return ('%(table_alias)s.date'+self.op)%(self.__dict__)+'%(value'+str(self.id)+')s'
        return ('%(table_alias)s.field_id=%(field_id)i and '+('%(table_alias)s.guest_id=%(other)s.guest_id and ' if self.other else '')+'%(table_alias)s.value'+self.op)%(self.__dict__)+'%(value'+str(self.id)+')s'
        


class CompoundFieldQuery(Mapping):
    def __init__(self, processer, table, where, order_field, order, field_name):
        CompoundFieldQueryPart.resetID()
        self.children=[]
        self.table_name=table._meta.db_table
        if isinstance(field_name, list):
            for fn in field_name:
                if fn.startswith('field.'):
                    field=field_name[6:]
                    f = Field.objects.filter(name=field)
                    if len(f) == 0:
                        f = Field.objects.get(name=field.replace('_', ' '))
                    else:
                        f = f[0]
                    if not views.testPermission(f.form, processer.user_obj) or not views.testPermission(f.form.program, processer.user_obj):
                        raise AccessDenied("Access denied on %r or %r" %(f.form, f.form.program))
                    self.children.append(CompoundFieldQueryPart(self.table_name, f.id, queryField=True, other=self.children[0].table_alias if self.children else None, field_name=field))
        else:
            if field_name.startswith('field.'):
                field=field_name[6:]
                f = Field.objects.filter(name=field)
                if len(f) == 0:
                    f = Field.objects.get(name=field.replace('_', ' '))
                else:
                    f = f[0]
                if not views.testPermission(f.form, processer.user_obj) or not views.testPermission(f.form.program, processer.user_obj):
                    raise AccessDenied("Access denied on %r or %r" %(f.form, f.form.program))
                self.children.append(CompoundFieldQueryPart(self.table_name, f.id, queryField=True, field_name=field))
        print (239,where.children)
        ichildren=iter(where.children)
        for child in ichildren:
            if child[0]=='field':
                if isinstance(child[1], list):
                    op,value=ichildren.next()
                    field=child[1][0]
                    
                    field_id=field.id
                    for i in self.children:
                        if i.field_id==field_id:
                            c = CompoundFieldQueryPart(self.table_name, field_id, op, value, self.children[0].table_alias if self.children else None, date=True)
                            c.table_alias=i.table_alias
                            self.children.append(c)
                            break
                else:
                    op,value=ichildren.next()
                    field=child[1]
                    field_id=field.id
                    self.children.append(CompoundFieldQueryPart(self.table_name, field_id, op, value, self.children[0].table_alias if self.children else None))
            else:
                raise Exception()
        
        self.order_field=order_field
        self.order=order
    def __getitem__(self, key):
        if key in self.__dict__:
            return self.__dict__[key]
        for i in self.children:
            if key in i.__dict__:
                return i.__dict__[key]
        return None
    def __iter__(self):
        yield 'order_field'
        for i in self.children:
            yield 'value%i'%i.id
    def __len__(self):
        return len(self.children)
    def __str__(self):
        ret = ('select id1 as id, * from (select distinct on (id1) * from (select %s from %s where %s order by %i) as qry1 order by 1 ) as qry2 order by %i %s ') %(
                                              #self.children[0].table_alias,
                                              str.join(', ', (i.__select__() for i in self.children if not i.date)),
                                              str.join(', ', (i.__from__() for i in self.children if not i.date)),
                                              str.join(' and ', (i.__where__() for i in self.children)),
                                              self.order_field or 1,
                                              self.order_field or 1,
                                              'DESC' if self.order.upper()=='DESC' else 'ASC')
        return ret


class Statement(object):
    implements(Procedure)
    def __init__(self, *args):
        pass
    def __call__(self, processer, params):
        method=params.pop(0)
        table,field_name=params.pop(0)
        where=params.pop(0)
        LOG(344,where, vars(where))
        if params and params[0].upper()=='ORDER' and params[1]=='BY':
            params.pop(0)
            params.pop(0)
            order_field=params.pop(0)
            if params:
                order=params.pop(0)
            else:
                order=''
        else:
            order_field=None
            order=''
        table = table.toObject(processer.cenv)
        headers=[]
        if zip(*where.children)[0].count('field')>1:
            print(275, where)
            qrySet = CompoundFieldQuery(processer, table, where, order_field, order, field_name)
            print(283,str(qrySet))
            query = table.objects.raw(str(qrySet), qrySet)
            print(362, query)
        else:
            query = table.objects.filter(where)
        l = locals()
        if raw_query:
            return lambda *x: FlattenQuery(query, l)
        return lambda *x: FlattenQuery(query, l)(processer, [])





class FlattenQuery(object):
    implements(Procedure)
    def __init__(self, query, locals):
        self.query=query
        self.__dict__.update(locals)
    def __call__(self, processer, params):
        query_results = []
        if len(params):
            query = params[0]
        else:
            query=self.query
        query=list(query)
        print(387, len(query))
        for result in query:
            #processer.pushStackN()
            e = Environment(processer.cenv)
            e['result'] = result
            if isinstance(self.field_name, list):
                this_result = []
                for fn in self.field_name:
                    if fn.startswith('field.'):
                        fn=fn[6:].lower()+'__value'
                    ret = safe_getattr(result,fn)
                    if not fn in self.headers:
                        if fn == 'value':
                            header_name = result.field.name
                            #scheme.processer.Processer().process(
                            #    Symbol('result.field.name'), e)
                            if header_name not in self.headers:
                                self.headers.append(header_name)
                        else:
                            self.headers.append(fn)
                    this_result.append(ret)
                query_results.append(this_result)
            else:
                if not self.field_name in self.headers:
                    if self.field_name.startswith('field.'):
                        self.field_name=self.field_name[6:].lower()+'__value'
                    self.headers.append(self.field_name)
                ret = getattr(e['result'], self.field_name)
#                ret = scheme.processer.Processer().process(Symbol('result.%s' % self.field_name), e)
                query_results.append(ret)
            #processer.popStackN()
        LOG(213, self.method, query)


        if self.method == "count":
            retval = len(query_results)
        elif self.method == sum:
            retval = sum(int(i) for i in query_results)
        elif self.method == 'avg':
            retval = sum(int(i) for i in query_results) / len(query_results)
        else:
            retval = [self.headers, query_results]
        return retval


def keyword_wrapper(func):
    def a(*args):
        kw = {}
        i = iter(args)
        for each in i:
            kw[each] = i.next()
        return func(**kw)

    return a


def safe_getattr(obj, attr):
    if attr == 'save' or attr.startswith('_'):
        raise AttributeError("not allowed to access save attribute or any attributes beginning with _")
    if isinstance(obj, (GuestData, GuestTimeData)):
        return getattr(obj, attr)
    if type(obj) in [django.db.models.manager.Manager, django.db.models.base.ModelBase, list, dict, str, unicode,
                     type(iter([])), GuestTimeData, GuestData, Guest, Field]:
        return getattr(obj, attr)
    if obj in [GuestTimeData, GuestData, Guest]:
        return getattr(obj, attr)
    if isinstance(obj, (Iterable)):
        return getattr(obj, attr)
    if isinstance(obj, FlattenQuery):
        return getattr(obj, attr)
    if isinstance(obj, (datetime.datetime,datetime.date)):
        return getattr(obj, attr)
    raise TypeError("getattr not allowed for %r" % type(obj))


def make_output(flo):
    def writer(*obj):
        LOG(*obj)
        print(*obj, file=flo)

    return writer


def parse(t):
    o = []
    for i in t:
        if isinstance(i, sqlparse.sql.TokenList):
            o.append([i.__class__.__name__] + parse(i.tokens))
        else:
            if not i.is_whitespace() and not i.to_unicode() == 'where':
                o.append(i.to_unicode())
    return o


def list_to_ast(lst):
    o = []
    for i in lst:
        if isinstance(i, (list, tuple)):
            o.append(list_to_ast(i))
        else:
            o.append(MacroSymbol(i).setEnv(scheme.processer.processer.cenv))
    return o



raw_query=False
class parse_sql(object):
    implements(Macro)

    def __call__(self, proc, params):
        global raw_query
        print (430,params)
        if params[0] == 'raw':
            raw_query = True
            params.pop(0)
        elif params[1] == 'raw':
            raw_query = True
            params.pop(1)
        else:
            raw_query = False
        return list_to_ast(parse(sqlparse.parse(str.join(' ', params))))

    def __init__(self, *args):
        pass


def sql_to_ast(p):
    return list_to_ast(parse(sqlparse.parse(p)))


def getitem(lst, item):
    if isinstance(lst, (list, tuple, QuerySet, dict)):
        return lst[item]
    raise TypeError("getitem not allowed for %r" % type(lst))

def getToday():
    return datetime.date.today().strftime('%m/%d/%Y')

def subtractDates(startdate,enddate,returntype=None):
    a=startdate
    if isinstance(startdate,(unicode,str)):
        a = datetime.datetime.strptime(startdate, '%m/%d/%Y')
    b=enddate
    if isinstance(b,(unicode,str)):
        b = datetime.datetime.strptime(enddate, '%m/%d/%Y')
    if not b.tzinfo:
        b=timezone.make_aware(b,timezone.get_default_timezone())
    if not a.tzinfo:
        a=timezone.make_aware(a,timezone.get_default_timezone())
    c = dateutil.relativedelta.relativedelta(a,b)
    d = a - b
    if returntype == 'seconds':
        return c.seconds
    if returntype == 'years':
        return c.years
    return d.days

class safeDjango(object):
    implements(Macro)
    def __init__(self, *args):
        pass
    def __call__(self, proc, params):
        subtable = None
        table = params.pop(0)
        if "." in table:
            subtable = table.split('.')
            table = subtable.pop(0)
        operator = params.pop(0)

        args=iter(params)
        newArgs=[]
        kwArgs={}
        for arg in args:
            if arg.endswith('='):
                arg=arg[:-1]
                val=args.next()
                if '__in' in arg and isinstance(val,list):
                    if val[0] == 'safeDjango':
                        val.pop(0)
                        kwArgs[arg] = self(proc,val)[0]()
                    else:
                        kwArgs[arg] = val
                else:
                    kwArgs[arg]=val.toObject(proc.cenv)
            else:
                newArgs.append(arg)
        order_by = kwArgs.get('order_by',None)
        if order_by:
            kwArgs.pop('order_by')
        tablelist = {'GuestTimeData':GuestTimeData,
                     'GuestData':GuestData,
                     'Guest':Guest,
                     'Field':Field,
                     }
        operatorlist = {'and':and_,'or':or_}
        table = tablelist.get(table,None)
        if table:
            if getattr(table,'objects'):
                table=table.objects
            filter = [Q(**{i[0]:i[1]}) for i in kwArgs.iteritems() ]
            filter_list = table.filter(reduce(operatorlist[operator], filter))
            permission_test = []
            for i in filter_list:
                if getattr(i,'field'):
                    if not views.testPermission(i.field, proc.user_obj):
                        permission_test.append(i)
                else:
                    if not views.testPermission(i, proc.user_obj):
                        permission_test.append(i)
            if permission_test == []:
                if order_by:
                    filter_list = filter_list.order_by(order_by)
                if subtable:
                    for i in subtable:
                        new_filter_list = [safe_getattr(a,i) for a in filter_list]
                        filter_list = list(new_filter_list)
                if 'distinct' in newArgs:
                    new_filter_list =[]
                    for i in filter_list:
                        if i not in new_filter_list:
                            new_filter_list.append(i)
                    filter_list = list(new_filter_list)
                return [lambda *x: list(filter_list)]
            return [lambda *x: ['lacking permissions']]
        return [lambda *x: ['No Table']]

def subtractDays(date, days):
    if isinstance(date,(str,unicode)):
        date = datetime.datetime.strptime(date,'%m/%d/%Y')
    days = datetime.timedelta(days=days)
    return date-days

def setitem(some_dict, some_key, some_value):
    if isinstance(some_dict,(list,dict)):
        some_dict[some_key] = some_value
    else:
        raise TypeError("setitem not allowed for %r" % type(some_dict))

def sortlist(lst, key):
    if isinstance(lst,list):
        lst.sort(key=lambda x: x[key])
    else:
        raise TypeError("sortlist not allowed for %r" % type(lst))

def lastday(year,month):
    return calendar.monthrange(year,month)[1]

def lastdayofpreviousmonth(date):
    return date.replace(day=1) - datetime.timedelta(days=1)

def setdayto(date,day):
    return date.replace(day=day)

def load_processer_globals(processer):
    output = cStringIO.StringIO()
    processer.env['output'] = make_output(output)
    processer.env['kw-wrapper'] = keyword_wrapper
    processer.env['getattr'] = safe_getattr
    processer.env['guest_time_data'] = GuestTimeData
    processer.env['guest'] = Guest
    processer.env['guestdata'] = GuestData
    processer.env['field'] = Field
    processer.env['iter'] = iter
    processer.env['literal_eval'] = literal_eval
    processer.env['sql'] = parse_sql()
    processer.env['expand-sql'] = sql_to_ast
    processer.env['Comparison'] = Comparison()
    processer.env['Identifier'] = Identifier()
    processer.env['Where'] = Where()
    processer.env['Statement'] = Statement()
    processer.env['IdentifierList'] = IdentifierList()
    processer.env['getitem'] = getitem
    processer.env['sum'] = sum
    processer.env['callable'] = callable
    processer.env['set'] = set
    processer.env['LOG'] = LOG
    processer.env['tuple'] = tuple
    processer.env['dir'] = dir
    processer.env['range'] = range
    processer.env['list_type'] = list
    processer.env['str'] = str
    processer.env['safeDjango'] = safeDjango()
    processer.env['map'] = map
    processer.env['type'] = type
    processer.env['in'] = lambda x, y: x in y
    processer.env['float'] = float
    processer.env['dict'] = dict
    processer.env['setitem'] = setitem
    processer.env['sleep'] = time.sleep

    processer.env['today'] = getToday
    processer.env['daycount'] = subtractDates
    processer.env['strtodate'] = datetime.datetime.strptime
    processer.env['sortlist'] = sortlist
    processer.env['lastday'] = lastday
    processer.env['lastdayofpreviousmonth'] = lastdayofpreviousmonth
    processer.env['setdayto'] = setdayto
    processer.env['SUBTRACT_DAYS'] = subtractDays
    return output



g = scheme.Globals.Globals

def get_processer():
    newG = Environment(None)
    newG.update(g)
    scheme.Globals.Globals=newG
#    scheme.Globals.Globals = g.copy()
    processer = scheme.processer.Processer()
    scheme.processer.processer = processer
    # processer.env = scheme.environment.Environment(None, scheme.Globals.Globals.copy())
    output = load_processer_globals(processer)
    return output, processer

import gc
import objgraph

from threading import Lock
running_reports={}


l=Lock()
def process(code, request):
    """
        :param code: unicode
        :return: unicode
    """
    user=request.user
    l.acquire()
    
    print(442, request.session)
    try:
        output, processer = get_processer()
        def cancelReport(*_):
            processer.shouldAbort=AbortReport()
        request.environ['IRequest'].notifyFinish().addErrback(cancelReport)
        processer.in_where=False
        processer.user_obj = user
        inp = cStringIO.StringIO(code)
        parser = scheme.parser.Parser(inp)
        ast = parser.ast
        processer.doProcess(ast)
    except AbortReport as e:
        print("Aborting report")
    except AccessDenied as e:
        return e.message
    except Exception as e:        
        import traceback
        print(455, request.session)
        if scheme.debug.getDebug("traceback"):
          raise Exception(traceback.format_exc()+"\n"+`scheme.processer.current_processer.ast`+"\n"+`scheme.processer.current_processer.callStack.queue`)
        raise Exception(traceback.format_exc()+"\n"+`scheme.processer.current_processer.ast`+"\n")
    finally:
        l.release()
    print(459, request.session)
    output.seek(0)
    gc.collect()
    return output.read().replace("~n", "\n")

