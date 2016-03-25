document.ready=function (){
    if (document.getElementById('field_list').value!=''){
        window.field_list = JSON.parse(document.getElementById('field_list').value);
    } else {
        window.field_list = {};
    }
    if (document.getElementById('form_list').value!=''){
        window.form_list = JSON.parse(document.getElementById('form_list').value);
    } else {
        window.form_list = {};
    }
    window.field_select_div = document.getElementById('field_select_div');
    window.form_select_div = document.getElementById('form_select_div');
    window.filter_div = document.getElementById('filter_div');
    window.viewer_div = document.getElementById('viewer_div');
    window.submit_button = document.getElementById('search');
    
	var header = form_select_div.appendChild(document.createElement('h5'));
	header.appendChild(document.createTextNode('Pick Form:'));
    window.form_select = createFormSelect(form_select_div);
	form_select.name = "form_select";
	form_select.onchange = changeForm;
    window.criterion_number = 0;
    window.field_number = 0;
    if (document.getElementById('submitted_form').value!=''){
		if(document.getElementById('submitted_field').value!=''){
			var submitted_field = JSON.parse(document.getElementById('submitted_field').value);
		} else {
			var submitted_field = [];
		}
		form_select.value = document.getElementById('submitted_form').value;
		changeForm();
		for (var i=0;i<submitted_field.length;i++){
			field_select_div.lastChild.children[0].value = submitted_field[i];
			addFieldSelect(field_select_div.lastChild.children[0]);
		}
		if (document.getElementById('submitted_criteria').value){
			var criteria = JSON.parse(document.getElementById('submitted_criteria').value);
		} else {
			var criteria = [];
		}
		for (var i=0;i<criteria.length;i++){
			filter_div.lastChild.children[0].value = criteria[i][0];
			createFieldSelect(filter_div.lastChild.children[1],criteria[i][0]);
			filter_div.lastChild.children[1].value = criteria[i][1];
			filter_div.lastChild.children[2].value = criteria[i][2];
			filter_div.lastChild.children[3].value = criteria[i][3];
			createCriteria();
		}
	}
    
}

function createFormSelect(t){
	if (! t) {
		t = this.parentNode;
	}
	var select = t.appendChild(document.createElement('select'));
	select.appendChild(new Option("",""));
	for (var i=0; i<form_list.length; i++){
		select.appendChild(new Option(form_list[i],form_list[i]));
	}
	return select;
}

function changeForm(t){
	field_number = 0;
	while (field_select_div.firstChild) {
		field_select_div.removeChild(field_select_div.firstChild);
	}
	var header = field_select_div.appendChild(document.createElement('h5'));
	header.appendChild(document.createTextNode('Pick Field(s):'));
	var field_select = createFieldSelect();
	field_select.onchange = addFieldSelect;
	field_select.name = 'field_select_'+String(field_number);
	field_number += 1;
	var new_div = field_select_div.appendChild(document.createElement('div'));
	new_div.appendChild(field_select);
}

function createFieldSelect(t,v){
	if (! t) {
		var field_select = document.createElement('select');
		var fields = field_list[form_select.value];
	} else {
		var field_select = t;
		var fields = field_list[v];
	}
	if (fields == undefined && ((!t && form_select.value ) || (t && v) )){
		fields = ['ID','First Name','Middle Name','Last Name','SSN','Program'];
	}
	field_select.appendChild(new Option('',''));
	for (var i=0;i<fields.length;i++){
		field_select.appendChild(new Option(fields[i],fields[i]));
	}
		
	return field_select;
}

function addFieldSelect(t){
    if (t instanceof Event) {
        t=this;
    }
    t = t.parentNode;
    if (! t.nextSibling){
		var field_select = createFieldSelect();
			field_select.onchange = addFieldSelect;
			field_select.name = 'field_select_'+String(field_number);
		field_number += 1;
		var new_div = field_select_div.appendChild(document.createElement('div'));
		new_div.appendChild(field_select);
	}
	if (filter_div.children.length==0){
		var header = filter_div.appendChild(document.createElement('h5'));
		header.appendChild(document.createTextNode('Set Criteria:'));
		createCriteria();
	}
}

function createCriteria(t){
    if (t instanceof Event) {
        t=this;
    }
    if (! t || ! t.parentNode.nextSibling){
		var new_div = filter_div.appendChild(document.createElement('div'));
		var form = createFormSelect(new_div);
			form.name = 'form_criteria_'+String(criterion_number);
			form.onchange=changeCriteriaForm;
			form.appendChild(new Option('Guest','Guest'));
		var field = new_div.appendChild(document.createElement('select'));
			field.name = 'field_criteria_'+String(criterion_number);
			field.onchange=createCriteria;
		var operator = new_div.appendChild(document.createElement('select'));
			operator.name = 'operator_' + String(criterion_number);
			operator.appendChild(new Option('',''));
			operator.appendChild(new Option('=','='));
			operator.appendChild(new Option('<>','<>'));
			operator.appendChild(new Option('>','>'));
			operator.appendChild(new Option('>=','>='));
			operator.appendChild(new Option('<','<'));
			operator.appendChild(new Option('<=','<='));
			operator.appendChild(new Option('contains','contains'));
		var value = new_div.appendChild(document.createElement('input'));
			value.name = 'value_' + String(criterion_number);
		criterion_number++;
	}
	if (filter_div.children.length > 2 && submit_button.offsetParent===null){
		submit_button.style.display = 'inline';
		document.getElementById('save').style.display = 'inline';
		document.getElementById('save_label').style.display = 'inline';
	}
}

function changeCriteriaForm(t){
    if (t instanceof Event) {
        t=this;
    }
    var field = t.nextSibling;
    while (field.firstChild){
		field.removeChild(field.firstChild);
	}
	createFieldSelect(field,t.value);
	
}



function toggleName() {
	var save = document.getElementById('save');
	if (save.checked){
		document.getElementById('save_name').style.display = 'inline';
		document.getElementById('save_name_label').style.display = 'inline';
	} else {
		document.getElementById('save_name').style.display = 'none';
		document.getElementById('save_name_label').style.display = 'none';
	}
}


function verifySubmit(t) {
	var form = document.getElementsByName('form_select')[0];
	if (! form.value){
		alert('Pick Form!');
		return;
	}
	var field_test = [];
	for (var i=1;i<field_select_div.children.length;i++){
		field_test.push(field_select_div.children[i].children[0].value=='');
	}
	if (field_test.indexOf(false)<0){
		alert('Pick Field!');
		return;
	}


	var submission = document.getElementsByTagName('form')[0]
	if (t.name == 'search'){
		var submit_type = document.createElement('input');
		submit_type.style.display='none';
		submit_type.name='search';
		submit_type.value='1';
		submission.appendChild(submit_type);
		
	}
	submission.submit();
}

