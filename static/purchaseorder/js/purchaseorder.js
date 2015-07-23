var vend = JSON.parse(document.getElementById('JSONvendors').value);
var dept = JSON.parse(document.getElementById('JSONdepartments').value);
var cate = JSON.parse(document.getElementById('JSONcategories').value);
var poli = JSON.parse(document.getElementById('JSONpos').value);


var vendor_list = document.getElementById('vendor_list');
for (var i = 0; i<vend.length; i++){
    vendor_list.appendChild(new Option(vend[i][0],vend[i][0]));
}


function createInput(type,name,list,onblur,value,onclick,class_name,ro,mult){
    if (type=="select"){
        var n = document.createElement('select');
    } else if (type=='textarea') {
        var n = document.createElement('textarea');
    } else {
        var n = document.createElement("input");
    }
    n.type=type;
    n.name=name;
    n.setAttribute('list', list);
    if (value){
        if (type=='checkbox'){
            n.checked=true;
        } else {
            n.value=value;
        }
    }
    n.setAttribute('onblur', onblur);
    n.setAttribute('onclick', onclick);
    n.className=class_name;
    if (ro) {
        n.readOnly=true;
    }
    if (mult){
        n.multiple='multiple';
    }
    return n;
}

function isSigner(department){
    for (var i=0;i<dept.length;i++){
        if (department.value==dept[i][0]){
            if (dept[i][1]==document.getElementById('current_username').value || dept[i][2].indexOf(document.getElementById('current_username').value)>-1){
                return true;
            }
            return false;
        }
    }
    return false;
}

function addDetail(i){
    var details = document.getElementById('details'+i);
    var detail = details.appendChild(document.createElement('div'));
    detail.className = 'detail';
    var index = i + '-' + String(Array.prototype.indexOf.call(details.children, detail));


        detail.appendChild(document.createTextNode("Vendor: "));
        detail.appendChild(createInput('text','vendor'+index,'vendor_list',"setAccount(this,this.parentNode.children[2]);",poli['vendor'+index]));
        detail.appendChild(document.createElement("BR"));

        detail.appendChild(document.createTextNode("Account Number: "));
        detail.appendChild(createInput('text','account_number'+index,undefined,poli['account_number'+index]));
        detail.appendChild(document.createElement("BR"));

        detail.appendChild(document.createTextNode("Order Number: "));
        detail.appendChild(createInput('text','order_number'+index,undefined,poli['order_number'+index]));
        detail.appendChild(document.createElement("BR"));

        detail.appendChild(document.createTextNode("Invoice Number: "));
        detail.appendChild(createInput('text','invoice_number'+index,undefined,poli['invoice_number'+index]));
        detail.appendChild(document.createElement("BR"));

        var paymentoptions = detail.appendChild(document.createElement("div"));
            paymentoptions.className="paymentoptions";

            paymentoptions.appendChild(document.createTextNode("Payment Method"));
            paymentoptions.appendChild(document.createElement("BR"));

            var payment_selection = false;

            paymentoptions.appendChild(createInput("radio","payment"+index,undefined,undefined,"check","setPayment(this,'"+index+"');"));
            if (poli['street_address_1'+index]!=undefined){
                payment_selection = paymentoptions.lastChild;
                payment_selection.checked = true;
            }
            paymentoptions.appendChild(document.createTextNode(" Check"));
            paymentoptions.appendChild(document.createElement("BR"));

            paymentoptions.appendChild(createInput("radio","payment"+index,undefined,undefined,"cc","setPayment(this,'"+index+"');"));
            if (poli['cc'+index]!=undefined){
                payment_selection = paymentoptions.lastChild;
                payment_selection.checked = true;
            }
            paymentoptions.appendChild(document.createTextNode(" Credit Card"));
            paymentoptions.appendChild(document.createElement("BR"));

            paymentoptions.appendChild(createInput("radio","payment"+index,undefined,undefined,"reimbursement","setPayment(this,'"+index+"');"));
            if (poli['reimbursement'+index]!=undefined){
                payment_selection = paymentoptions.lastChild;
                payment_selection.checked = true;
            }
            paymentoptions.appendChild(document.createTextNode(" Reimbursement"));
            paymentoptions.appendChild(document.createElement("BR"));

            var payment_info = paymentoptions.appendChild(document.createElement('div'));
                payment_info.className = "payment_info";
                payment_info.id = 'payment_info'+index;

                if (payment_selection!=false){
                    setPayment(payment_selection,index);
                }
        var detailbreakdown = detail.appendChild(document.createElement('div'));
            detailbreakdown.className = 'detailbreakdown';
            detailbreakdown.id = 'detailbreakdown'+index
        detail.appendChild(createInput("button",undefined,undefined,undefined,"Add Breakdown","addDetailBreakdown('"+index+"');",'detailgroup'));
        addDetailBreakdown(index);

}

function setPayment(t,index){
    var payment_info = document.getElementById('payment_info'+index);

    while (payment_info.firstChild){
        payment_info.removeChild(payment_info.firstChild);
    }
    switch (t.value){
        case 'check':
            payment_info.appendChild(document.createTextNode("Street Address 1: "));
            payment_info.appendChild(createInput("text","street_address_1"+index,undefined,undefined,poli['street_address_1'+index]));
            payment_info.appendChild(document.createElement("BR"));

            payment_info.appendChild(document.createTextNode("Street Address 2: "));
            payment_info.appendChild(createInput("text","street_address_2"+index,undefined,undefined,poli['street_address_2'+index]));
            payment_info.appendChild(document.createElement("BR"));

            payment_info.appendChild(document.createTextNode("City: "));
            payment_info.appendChild(createInput("text","city"+index,undefined,undefined,poli['city'+index]));
            payment_info.appendChild(document.createTextNode(" State: "));
            payment_info.appendChild(createInput("text","state"+index,undefined,undefined,poli['state'+index]));
            payment_info.appendChild(document.createTextNode(" Zip: "));
            payment_info.appendChild(createInput("text","zip"+index,undefined,undefined,poli['zip'+index]));
            payment_info.appendChild(document.createElement("BR"));
            break;
        case 'cc':
            payment_info.appendChild(document.createTextNode("Last 4: "));
            payment_info.appendChild(createInput("text","cc"+index,undefined,undefined,poli['cc'+index]));
            payment_info.appendChild(document.createElement("BR"));
            break;
        case 'reimbursement':
            payment_info.appendChild(document.createTextNode("Reimbursement Name: "));
            payment_info.appendChild(createInput("text","reimbursement"+index,undefined,undefined,poli['reimbursement'+index]));
            payment_info.appendChild(document.createElement("BR"));
            break;
    }
}

function alertObject(o){
    alert(o);
}

function addDetailBreakdown(i){
    var detailbreakdown = document.getElementById('detailbreakdown'+i);
    var detailgroup = detailbreakdown.appendChild(document.createElement('div'));
    detailgroup.className = 'detailgroup';
    var index = i+'-'+String(Array.prototype.indexOf.call(detailbreakdown.children,detailgroup));

        detailgroup.appendChild(document.createTextNode('Department: '));
        var department = detailgroup.appendChild(createInput("select","department"+index,undefined,"setSubs('"+index+"');"));
            department.appendChild(new Option("",""));
            for (var i = 0; i<dept.length; i++){
                department.appendChild(new Option(dept[i][0],dept[i][0]));
            }
            department.value = poli['department'+index];
        detailgroup.appendChild(document.createElement('BR'));

        detailgroup.appendChild(document.createTextNode('Sub Department: '));
        detailgroup.appendChild(createInput("text","sub_department"+index,"sub_list"+index,undefined,poli['sub_department'+index]));
        detailgroup.appendChild(document.createElement('BR'));

        detailgroup.appendChild(document.createTextNode('Budget Category: '));
        detailgroup.appendChild(createInput("select","budget_category"+index));
        detailgroup.appendChild(document.createElement('BR'));

        detailgroup.appendChild(document.createTextNode('Amount: '));
        detailgroup.appendChild(createInput("text","amount"+index,undefined,undefined,poli['amount'+index]));
        detailgroup.appendChild(document.createElement('BR'));

        detailgroup.appendChild(document.createTextNode('Description: '));
        detailgroup.appendChild(createInput("textarea","description"+index,undefined,undefined,poli['description'+index],undefined,'large_input'));
        detailgroup.appendChild(document.createElement('BR'));

        var signblock = detailgroup.appendChild(document.createElement('div'));
        signblock.id = 'signblock'+index;
        signblock.className = 'signblock';
            signblock.appendChild(createInput('hidden','sign'+index,undefined,undefined,poli['sign'+index]));
            showSign(index);
        setSubs(index,poli['budget_category'+index]);
}

function showSign(index){
    var sign = document.getElementsByName('sign'+index)[0];
    if (!sign.nextSibling){
        var department = document.getElementsByName('department'+index)[0];
        var signblock = sign.parentNode;
        if (sign.value=='false'){
            if (isSigner(department)){
                signblock.appendChild(createInput('button',undefined,undefined,undefined,'Sign Expense','signExpense("Approval","'+index+'");'));
                signblock.appendChild(createInput('button',undefined,undefined,undefined,'Reject Expense','signExpense("Rejection","'+index+'");'));
            } else {
                signblock.appendChild(document.createTextNode('Not Approved'));
            }
        } else if (sign.value=='rejected') {
            signblock.appendChild(document.createTextNode('Rejected'));
        } else if (sign.value=='true') {
            signblock.appendChild(document.createTextNode('Approved'));
        }
    }
}

function signExpense(ar,index){
    if (confirm("Confirm "+ar)){
        var s = document.getElementsByName('sign'+index)[0];
        if (ar=='Approval'){
            s.parentNode.removeChild(s.nextSibling);
            s.parentNode.removeChild(s.nextSibling);
            s.parentNode.appendChild(document.createTextNode('Approved'));
            s.value='true';
        } else {
            s.parentNode.removeChild(s.nextSibling);
            s.parentNode.removeChild(s.nextSibling);
            s.parentNode.appendChild(document.createTextNode('Rejected'));
            s.value='false';
        }
    }
}
//function createInput(type,name,list,onblur,value,onclick,class_name,ro,mult){

function setSubs(index,value){
    var department_input = document.getElementsByName('department'+index)[0];
    var sub_input = document.getElementsByName('sub_department'+index)[0];
    for (var i=0;i<dept.length; i++){
        if (department_input.value==dept[i][0]){
            var t = sub_input.appendChild(document.createElement('datalist'));
            t.id = "sub_list"+index;
            for (a=0;a<dept[i][3].length;a++){
                t.appendChild(new Option(dept[i][3][a]));
            }
        }
    }

    var budget_categories = document.getElementsByName('budget_category'+index)[0];
    budget_categories.options.length=0;
    budget_categories.appendChild(new Option('',"",true,false))
    for (var i=0;i<cate.length;i++){
        budget_categories.appendChild(new Option(cate[i],cate[i],false,false));
    }
    for (var i=0;i<dept.length; i++){
        if (department_input.value==dept[i][0]){
            for (a=0;a<dept[i][4].length;a++){
                budget_categories.appendChild(new Option(dept[i][4][a],dept[i][4][a],false,false));
            }
        }
    }
    if (value){
        budget_categories.value = value;
    }

    var sign = document.getElementsByName('sign'+index)[0];
    if (sign.value=='' && department_input.value!=''){
        if (isSigner(department_input)){
            sign.value = 'true';
        } else {
            sign.value = 'false';
        }
    }
    showSign(index);
}

function setAccount(vendor_input,account_input){
    for (var i = 0; i<vend.length; i++){
        if (vendor_input.value == vend[i][0]) {
            account_input.value = vend[i][1];
        }
    }

}

function addPO(){
    var pos = document.getElementById('pos');
    var new_po =  pos.appendChild(document.createElement("div"));
    var index = String(Array.prototype.indexOf.call(pos.children, new_po));
    new_po.id = 'po'+index;
    new_po.className = 'po';
    if (poli['locked'+index]){
        new_po.classList.add('locked');
        var h1 = new_po.appendChild(document.createElement('h1'));
        h1.appendChild(document.createTextNode("Purchase Order Locked"));
        new_po.appendChild(document.createElement('BR'));
    }
        new_po.appendChild(document.createTextNode("Purchase Order Number: "+poli['po_number'+index]));
        new_po.appendChild(createInput('hidden','po_number'+index,undefined,undefined,poli['po_number'+index],undefined,undefined,true));
        new_po.appendChild(document.createElement('BR'));

        new_po.appendChild(document.createTextNode("Created By: "+poli['created_by'+index]));
        new_po.appendChild(createInput('hidden','created_by'+index,undefined,undefined,poli['created_by'+index],undefined,undefined,true));
        new_po.appendChild(document.createElement('BR'));

        new_po.appendChild(document.createTextNode("Created Date: "+poli['created_date'+index]));
        new_po.appendChild(createInput('hidden','created_date'+index,undefined,undefined,poli['created_date'+index],undefined,undefined,true));
        new_po.appendChild(document.createElement('BR'));

        new_po.appendChild(document.createTextNode("Purchase Date: "));
        new_po.appendChild(createInput("text",'purchase_date'+index,undefined,undefined,poli['purchase_date'+index],undefined,'datePicker',true));
        new_po.appendChild(document.createElement('BR'));

        new_po.appendChild(document.createTextNode("Purchase Total: "));
        new_po.appendChild(createInput("text",'purchase_total'+index,undefined,undefined,poli['purchase_total'+index]));
        new_po.appendChild(document.createElement('BR'));

        new_po.appendChild(document.createTextNode("All Goods Received: "));
        new_po.appendChild(createInput("checkbox",'goods_received'+index,undefined,undefined,poli['goods_received'+index]));
        new_po.appendChild(document.createElement('BR'));

        new_po.appendChild(document.createTextNode("Drop Files in Box "));
        new_po.appendChild(document.createElement('BR'));

        new_po.appendChild(createInput("file",'attachments'+index,undefined,undefined,undefined,undefined,'file_upload',undefined,true));
        if (poli['attachments'+index]!=undefined){
            for (var i=0;i<poli['attachments'+index].length;i++){
                new_po.appendChild(document.createElement('BR'));
                var link = new_po.appendChild(document.createElement('a'));
                link.appendChild(document.createTextNode('Document '+i));
                link.title = 'Document '+i;
                link.href = poli['attachments'+index][i];
            }
        }

        new_details = new_po.appendChild(document.createElement('div'));
            new_details.className = 'details';
            new_details.id = 'details' + index;
        new_po.appendChild(createInput('button',undefined,undefined,undefined,'Add Detail',"addDetail('"+index+"');",'detail'));
        new_po.appendChild(document.createElement('BR'));
        new_po.appendChild(createInput('button',undefined,undefined,undefined,'Remove PO from Submission',"hidePO('"+index+"');",'detail'));

        new_po.appendChild(createInput('hidden','revision'+index,undefined,undefined,poli['revision'+index]));

        addDetail(index);
}

//function createInput(type,name,list,onblur,value,onclick,class_name,ro,mult){


function hidePO(i){
    var po = document.getElementById('po'+i);
    if (confirm("Confirm Removal")){
        po.parentNode.removeChild(po);
    }
}

function verify(e){
    e.classList.remove('highlight');
    if (e.value==''){
        e.classList.add('highlight');
        return false;
    } else {
        return true;
    }
}

function preCheck(){
    var form = document.getElementById('form');
    var po_list = form.children[1];
    var is_valid = true;
    for (var i=0;po_list.children[i]!=undefined;i++){
        var cpo = po_list.children[i];
        if (!verify(cpo.children[6])){is_valid=false;}
        if (!verify(cpo.children[8])){is_valid=false;}
        var tpurchase_total = Number(cpo.children[8].value);
        var apurchase_total = 0.0;
        var cdetails = cpo.children[14];
        for (var a=0;cdetails.children[a]!=undefined;a++){
            var cdetail = cdetails.children[a];
            if (a==0){
                if (!verify(cdetail.children[0])){is_valid=false;}
            }
            var cvendor = cdetail.children[0];
            if (cvendor.value!=''){
                var paymentoptions = cdetail.children[8];
                !paymentoptions.classList.remove('highlight')
                if (!paymentoptions.children[1].checked && !paymentoptions.children[3].checked && !paymentoptions.children[5].checked){
                    paymentoptions.classList.add('highlight');
                    is_valid=false;
                } else {
                    if (paymentoptions.children[3].checked || paymentoptions.children[5].checked){
                        if (!verify(paymentoptions.children[7].children[0])){is_valid=false;}
                    }
                }
                var cdetailbreakdowns = cdetail.children[9];
                for (var b=0;cdetailbreakdowns.children[b]!=undefined;b++){
                    var cdetailbreakdown = cdetailbreakdowns.children[b];
                    var cdepartment = cdetailbreakdown.children[0];
                    if (b==0){
                        if (!verify(cdepartment)){is_valid=false;}
                    }
                    if (cdepartment.value!=''){
                        if (!verify(cdetailbreakdown.children[4])){is_valid=false;}
                        if (!verify(cdetailbreakdown.children[6])){is_valid=false;}
                        apurchase_total += Number(cdetailbreakdown.children[6].value);
                        if (!isSigner(cdepartment)){
                            if (!verify(cdetailbreakdown.children[8])){is_valid=false;}
                        }
                    }
                }
            }
        }
        if (apurchase_total!=tpurchase_total){
            alert('purchase total does not match detail');
            is_valid = false;
        }
    }

    if (is_valid){
        form.submit();
    } else {
        alert('please fix errors and resubmit');
    }

}

for (var i=0;poli['po_number'+i]!=undefined;i++){
    addPO();
    for (var a=1;poli['vendor'+i+'-'+a]!=undefined;a++){
        addDetail(i);
        for (var b=1;poli['department'+i+'-'+a+'-'+b]!=undefined;b++){
            addDetailBreakdown(i+'-'+a);
        }
    }
}


