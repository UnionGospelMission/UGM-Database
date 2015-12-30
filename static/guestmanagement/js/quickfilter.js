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
    var form_select_div = document.getElementById('form_select_div');
	var header = form_select_div.appendChild(document.createElement('h5'));
	header.appendChild(document.createTextNode('Pick Form:'));
    var form_select = createFormSelect(form_select_div);
	form_select.name = "form_select";
	form_select.onchange = changeForm;
    window.criterion_number = 0;
    if (document.getElementById('submitted_form').value!=''){
		form_select.value = document.getElementById('submitted_form').value;
		var field_select = changeForm(form_select);
		field_select.value = document.getElementById('submitted_field').value;
		var new_criterion = setFilter();
		var criterion_list = JSON.parse(document.getElementById('submitted_criteria').value);
		for (var i=0;i<criterion_list.length;i++){
			new_criterion.children[0].value = criterion_list[i][0];
			var holding = setFields(new_criterion.children[0]);
			holding = undefined;
			new_criterion.children[1].value = criterion_list[i][1];
			new_criterion.children[2].value = criterion_list[i][2];
			new_criterion.children[3].value = criterion_list[i][3];
			new_criterion = newCriterion(new_criterion.children[0]);
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
    if (t instanceof Event) {
        t=this;
    }
	var field_select_div = document.getElementById('field_select_div');
	while (field_select_div.firstChild) {
		field_select_div.removeChild(field_select_div.firstChild);
	}
	var header = field_select_div.appendChild(document.createElement('h5'));
	header.appendChild(document.createTextNode('Pick Field:'));
	var field_select = field_select_div.appendChild(document.createElement('select'));
	field_select.appendChild(new Option('',''));
	for (var i=0;i<field_list[t.value].length;i++){
		field_select.appendChild(new Option(field_list[t.value][i],field_list[t.value][i]));
	}
	field_select.onchange = setFilter;
	field_select.name = "field_select";
	return field_select;
}

function setFilter(){
	criterion_number = 0;
	var filter_div = document.getElementById('filter_div');
	if (! filter_div.children[0]){
		var header = filter_div.appendChild(document.createElement('h5'));
		header.appendChild(document.createTextNode('Set Criterion:'));
		return newCriterion(filter_div);
	}
}

function newCriterion(t) {
    if (t instanceof Event) {
        t=this;
    }
    if (t.parentNode.nextSibling == null || t.parentNode.tagName=='FORM'){
		if (t.tagName=='DIV'){
			var parent_div = t;
		} else {
			var parent_div = t.parentNode.parentNode;
		}
		var new_criterion = parent_div.appendChild(document.createElement('div'));
		var new_form_select = createFormSelect(new_criterion);
		new_form_select.appendChild(new Option('Guest','Guest'));
		new_form_select.name = 'form_select_' + String(criterion_number);
		new_form_select.onchange=setFields;
		var new_field_select = new_criterion.appendChild(document.createElement('select'));
		new_field_select.name = 'field_select_' + String(criterion_number);
		new_field_select.onchange = newCriterion;
		var new_operator = new_criterion.appendChild(document.createElement('select'));
		new_operator.name = 'operator_' + String(criterion_number);
		new_operator.appendChild(new Option('',''));
		new_operator.appendChild(new Option('=','='));
		new_operator.appendChild(new Option('<>','<>'));
		new_operator.appendChild(new Option('>','>'));
		new_operator.appendChild(new Option('>=','>='));
		new_operator.appendChild(new Option('<','<'));
		new_operator.appendChild(new Option('<=','<='));
		new_operator.appendChild(new Option('contains','contains'));
		var new_value = new_criterion.appendChild(document.createElement('input'));
		new_value.name = 'value_' + String(criterion_number);
		criterion_number++;
	}
	var submit_button = document.getElementById('search');
	if (submit_button.offsetParent===null && t.parentNode.nextSibling != null && t.parentNode.tagName!='FORM'){
		submit_button.style.display = 'inline';
		document.getElementById('save').style.display = 'inline';
		document.getElementById('save_label').style.display = 'inline';
	}
	if (new_criterion){
		return new_criterion;
	}
}

function setFields(t){
    if (t instanceof Event) {
        t=this;
    }
	var my_field_list = field_list[t.value];
	if (my_field_list == undefined && t.value != ''){
		my_field_list = ['ID','First Name','Middle Name','Last Name','SSN','Program'];
	}
	tn=t.nextSibling;
	while (tn.firstChild) {
		tn.removeChild(tn.firstChild);
	}
	tn.appendChild(new Option('',''));
	for (var i=0;i<my_field_list.length;i++){
		tn.appendChild(new Option(my_field_list[i],my_field_list[i]));
	}
	return tn;
	
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
