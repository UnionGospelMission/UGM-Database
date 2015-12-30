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

function changeForm(){
	var field_select_div = document.getElementById('field_select_div');
	while (field_select_div.firstChild) {
		field_select_div.removeChild(field_select_div.firstChild);
	}
	var header = field_select_div.appendChild(document.createElement('h5'));
	header.appendChild(document.createTextNode('Pick Field:'));
	var field_select = field_select_div.appendChild(document.createElement('select'));
	field_select.appendChild(new Option('',''));
	for (var i=0;i<field_list[this.value].length;i++){
		field_select.appendChild(new Option(field_list[this.value][i],field_list[this.value][i]));
	}
	field_select.onchange = setFilter;
	field_select.name = "field_select";
}

function setFilter(){
	criterion_number = 0;
	var filter_div = document.getElementById('filter_div');
	while (filter_div.firstChild) {
		filter_div.removeChild(filter_div.firstChild);
	}
	var header = filter_div.appendChild(document.createElement('h5'));
	header.appendChild(document.createTextNode('Set Criterion:'));
	newCriterion(filter_div);
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
		submit_button.style.display = 'block';
	}
}

function setFields(){
	t=this.nextSibling;
	while (t.firstChild) {
		t.removeChild(t.firstChild);
	}
	t.appendChild(new Option('',''));
	var my_field_list = field_list[this.value];
	if (my_field_list == undefined){
		my_field_list = ['ID','First Name','Middle Name','Last Name','SSN','Program'];
	}
	for (var i=0;i<my_field_list.length;i++){
		t.appendChild(new Option(my_field_list[i],my_field_list[i]));
	}
	
}
