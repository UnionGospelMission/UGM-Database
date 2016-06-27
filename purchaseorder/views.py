from django.shortcuts import render
from django.core.context_processors import csrf
from django.contrib import messages,auth
from django.http import HttpResponse
from purchaseorder.models import PurchaseOrder,Vendor,Department,SpecialCategory,BudgetCategory,Detail,DetailBreakdown
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import datetime,json

# Create your views here.

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
    context = {'base_site':request.session.get('base_site','')}
    messages.add_message(request, messages.INFO, 'PO system development suspended... contact lperkin1 if you want it developed')
    context.update(csrf(request))
    return context

@login_required
def index(request):
    '''
    View which returns the index page
    '''
    context=baseContext(request)
    
    return render(request,'shared/index.html',context)


def logout(request):
    '''
    View for logging out users
    '''
    auth.logout(request)
    return render(request,"shared/logout.html")

def view(request,target=None):
    context = baseContext(request)
    return HttpResponse('new')

def retrievePO(po,counter):
    counter = str(counter)
    retval = {'po_number'+counter:po.id,
              'created_by'+counter:'%s %s'%(po.owner.first_name,po.owner.last_name),
              'purchase_date'+counter:str(po.purchase_date),
              'purchase_total'+counter:po.purchase_total,
              'locked'+counter:po.locked,
              'goods_received'+counter:po.received,
              'approved'+counter:po.approved,
              'processed'+counter:po.processed,
              'attachments'+counter:json.dumps(po.attachments),
              'created_date'+counter:po.created_date,
              'received_date'+counter:po.received_date,
              'processed_date'+counter:po.processed_date,
              'revision'+counter:po.revision,
              }
    detail_list = Detail.objects.filter(purchase_order=po)
    detail_counter = 0
    for i in detail_list:
        retval.update({'vendor'+counter+'-'+str(detail_counter):i.vendor,
                       'account_number'+counter+'-'+str(detail_counter):i.account_number,
                       'order_number'+counter+'-'+str(detail_counter):i.order_number,
                       'invoice_number'+counter+'-'+str(detail_counter):i.invoice_number,
                       'payment'+counter+'-'+str(detail_counter):i.payment,
                        })
        if i.payment == 'check':
            address = json.loads(i.street_address)
            retval.update({'street_address_1'+counter+'-'+str(detail_counter):address[0],
                           'street_address_2'+counter+'-'+str(detail_counter):address[1],
                           'city'+counter+'-'+str(detail_counter):address[2],
                           'state'+counter+'-'+str(detail_counter):address[3],
                           'zip'+counter+'-'+str(detail_counter):address[4],
                            })
        elif i.payment == 'cc':
            retval.update({'cc'+counter+'-'+str(detail_counter):i.credit_card})
        elif i.payment == 'reimbursement':
            retval.update({'reimbursement'+counter+'-'+str(detail_counter):i.reimbursement})

        breakdown_counter = 0
        breakdown_list = DetailBreakdown.objects.filter(detail=i)
        for a in breakdown_list:
            retval.update({'department'+counter+'-'+str(detail_counter)+'-'+str(breakdown_counter):a.department.name,
                           'sub_department'+counter+'-'+str(detail_counter)+'-'+str(breakdown_counter):a.sub,
                           'budget_category'+counter+'-'+str(detail_counter)+'-'+str(breakdown_counter):a.category,
                           'amount'+counter+'-'+str(detail_counter)+'-'+str(breakdown_counter):a.amount,
                           'description'+counter+'-'+str(detail_counter)+'-'+str(breakdown_counter):a.description,
                           'signed'+counter+'-'+str(detail_counter)+'-'+str(breakdown_counter):a.signed,
                           'signed_date'+counter+'-'+str(detail_counter)+'-'+str(breakdown_counter):a.signed_date,
                            })
            breakdown_counter += 1


        detail_counter += 1
    return retval

def savePO(po,v):
    updated = ''
    po.purchase_date = v['purchase_date']
    po.purchase_total = v['purchase_total']
    po.goods_received = v['goods_received']
    if v[attachments]:
        pass
    breakdown_dict = {}
    

def new(request):
    context = baseContext(request)
    context.update({'JSONvendors':json.dumps([[i.name,i.account_number] for i in Vendor.objects.all()]),
                    'JSONdepartments':json.dumps([[i.name,i.head.username,[a.username for a in i.signers.all()],[a for a in json.loads(i.sub)],[a.name for a in SpecialCategory.objects.filter(completed=False)]] for i in Department.objects.all()]),
                    'JSONcategories':json.dumps([i.name for i in BudgetCategory.objects.all()]),
                    })
    if request.POST:
        # Convert post information into dictionaries of purchase orders
        request_dict = dict(request.POST)
        request_dict.pop('csrfmiddlewaretoken')
        po_dict = {}
        counter = '0'
        while isinstance(counter,str):
            po_dict[counter] = {}
            po_dict[counter]['po_number'] = request_dict.pop('po_number'+counter)[0]
            po_dict[counter]['created_by'] = User.objects.get(first_name=request_dict['created_by'+str(counter)][0].split(' ')[0],last_name=request_dict.pop('created_by'+str(counter))[0].split(' ')[1])
            po_dict[counter]['created_date'] = datetime.datetime.strptime(request_dict.pop('created_date'+str(counter))[0],'%Y-%m-%d')
            po_dict[counter]['purchase_date'] = datetime.datetime.strptime(request_dict.pop('purchase_date'+str(counter))[0],'%m/%d/%Y')
            po_dict[counter]['purchase_total'] = request_dict.pop('purchase_total'+str(counter))[0]
            if request_dict.get('goods_received'+str(counter),''):
                goods_received = request_dict.pop('goods_received'+str(counter))[0] == u'on'
            else:
                goods_received = False
            po_dict[counter]['goods_received'] = goods_received
            po_dict[counter]['attachments'] = request.FILES.get('attachments'+str(counter),'')
            po_dict[counter]['breakdown'] = {}
            po_dict[counter]['revision'] = request_dict.pop('revision'+str(counter))[0]

            breakdown_counter = '0'
            while isinstance(breakdown_counter,str):
                po_dict[counter]['breakdown'][breakdown_counter] = {}
                po_dict[counter]['breakdown'][breakdown_counter]['vendor'] = request_dict.pop('vendor'+counter+'-'+breakdown_counter)[0]
                po_dict[counter]['breakdown'][breakdown_counter]['account_number'] = request_dict.pop('account_number'+counter+'-'+breakdown_counter)[0]
                po_dict[counter]['breakdown'][breakdown_counter]['order_number'] = request_dict.pop('order_number'+counter+'-'+breakdown_counter)[0]
                po_dict[counter]['breakdown'][breakdown_counter]['invoice_number'] = request_dict.pop('invoice_number'+counter+'-'+breakdown_counter)[0]
                po_dict[counter]['breakdown'][breakdown_counter]['payment'] = request_dict.pop('payment'+counter+'-'+breakdown_counter)[0]
                if po_dict[counter]['breakdown'][breakdown_counter]['payment'] == 'check':
                    po_dict[counter]['breakdown'][breakdown_counter]['street_address_1'] = request_dict.pop('street_address_1'+counter+'-'+breakdown_counter)[0]
                    po_dict[counter]['breakdown'][breakdown_counter]['street_address_2'] = request_dict.pop('street_address_2'+counter+'-'+breakdown_counter)[0]
                    po_dict[counter]['breakdown'][breakdown_counter]['city'] = request_dict.pop('city'+counter+'-'+breakdown_counter)[0]
                    po_dict[counter]['breakdown'][breakdown_counter]['state'] = request_dict.pop('state'+counter+'-'+breakdown_counter)[0]
                    po_dict[counter]['breakdown'][breakdown_counter]['zip'] = request_dict.pop('zip'+counter+'-'+breakdown_counter)[0]
                elif po_dict[counter]['breakdown'][breakdown_counter]['payment'] == 'cc':
                    po_dict[counter]['breakdown'][breakdown_counter]['cc'] = request_dict.pop('cc'+counter+'-'+breakdown_counter)[0]
                else:
                    po_dict[counter]['breakdown'][breakdown_counter]['reimbursement'] = request_dict.pop('reimbursement'+counter+'-'+breakdown_counter)[0]

                po_dict[counter]['breakdown'][breakdown_counter]['details'] = {}

                detail_counter = '0'
                while isinstance(detail_counter,str):
                    po_dict[counter]['breakdown'][breakdown_counter]['details'][detail_counter]={}
                    po_dict[counter]['breakdown'][breakdown_counter]['details'][detail_counter]['department'] = request_dict.pop('department'+counter+'-'+breakdown_counter+'-'+detail_counter)[0]
                    po_dict[counter]['breakdown'][breakdown_counter]['details'][detail_counter]['sub_department'] = request_dict.pop('sub_department'+counter+'-'+breakdown_counter+'-'+detail_counter)[0]
                    po_dict[counter]['breakdown'][breakdown_counter]['details'][detail_counter]['budget_category'] = request_dict.pop('budget_category'+counter+'-'+breakdown_counter+'-'+detail_counter)[0]
                    po_dict[counter]['breakdown'][breakdown_counter]['details'][detail_counter]['amount'] = request_dict.pop('amount'+counter+'-'+breakdown_counter+'-'+detail_counter)[0]
                    po_dict[counter]['breakdown'][breakdown_counter]['details'][detail_counter]['description'] = request_dict.pop('description'+counter+'-'+breakdown_counter+'-'+detail_counter)[0]
                    po_dict[counter]['breakdown'][breakdown_counter]['details'][detail_counter]['sign'] = request_dict.pop('sign'+counter+'-'+breakdown_counter+'-'+detail_counter)[0]==u'true'

                    detail_counter = False
                    for k,v in request_dict.iteritems():
                        if k.find('department'+counter+'-'+breakdown_counter+'-')>-1:
                            detail_counter = int(k.split('department'+counter+'-'+breakdown_counter+'-')[1])
                            break



                breakdown_counter = False
                for k,v in request_dict.iteritems():
                    if k.find('vendor'+counter+'-')>-1:
                        breakdown_counter = int(k.split('vendor'+counter+'-')[1])
                        break



            counter = False
            for k,v in request_dict.iteritems():
                if k.find('po_number')>-1:
                    counter = k.split('po_number')[1]
                    break

        po_problems = {}
        counter = 0
        for k,v in po_dict.iteritems():
            po = PurchaseOrder.objects.get(id=v['po_number'])
            if po.revision != v['revision']:
                po_problems.update(retrievePO(po,counter))
                messages.add_message(request, messages.INFO, 'PO modified by another user.  Please verify information and try again')
                counter += 1
                continue
            if po.locked:
                po_problems.update(retrievePO(po,counter))
                messages.add_message(request, messages.INFO, 'PO locked.  Contact Accounting')
                counter += 1
                continue
            savePO(po,v)
        context.update({'JSONpos':json.dumps(po_problems)})
        return render(request,'purchaseorder/new.html',context)
    created = False
    while not created:
        if PurchaseOrder.objects.all():
            latest = PurchaseOrder.objects.all().latest('id').id + 1
        else:
            latest = 1
        po,created = PurchaseOrder.objects.get_or_create(id=latest)
    po.owner = request.user
    po.created_date = datetime.date.today()
    po.save()
    context.update({'JSONpos':json.dumps({'po_number0':'%05d'%po.id,
                                            'created_by0': '%s %s'%(po.owner.first_name,po.owner.last_name),
                                            'created_date0':str(po.created_date),
                                            'revision0':po.revision,
                                            'locked0':po.locked,
                                            }),
                    })
    return render(request,'purchaseorder/new.html',context)
