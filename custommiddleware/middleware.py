
class setBaseSite():
    def process_request(self,request):
        if request.path == '/':
            request.session['base_site']=''
        if not request.session.get('base_site',''):
            if 'guestmanagement' in request.path:
                request.session['base_site']='guestmanagement'
            elif 'purchaseorder' in request.path:
                request.session['base_site']='purchaseorder'
            elif 'truckmanagement' in request.path:
                request.session['base_site']='truckmanagement'

