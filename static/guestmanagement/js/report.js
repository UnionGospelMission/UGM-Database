'use strict';

document.ready=function () {
	// Save reference variables
	window.report_form_div = document.getElementById("report_form");
	window.report_view_toggle_button = document.getElementById("report_view_toggle");
	window.user_inputs_div = document.getElementById('user_inputs');
	window.calculations_div = document.getElementById('calculations');
	window.layout_div = document.getElementById('layout');

	// Initialize zIndex
	report_form_div.style.zIndex=-1;
	
	// Initialize python editors
	window.editors = {};
	window.editorscounter = 0;
	window.editor_default = `'''Available filter Functions:
filterValuesOnDay(date,field,value,return_guest_ids[True/False])
	for returning all guests which had a value on a particular day.
valueOnDay(date,field=None,guest_id=None,date_value_list=None)
	for finding the value for a particular guest on a particular day
	if you use field and guest_id, the database will be queried, else 
	the list of dates and values you provide will be used.
GuestData(criteria1=value,criteria2=value)
	uses the standard django filter system to directly query guestdata
	which consist of guest, field, value
GuestTimeData
	same as GuestData only queries guesttimedatas which consist of 
	guest, field, value, timestamp
Guest
	same as GuestData only queries guest objects, which consist of
	first_name, middle_name, last_name, ssn, program, picture
ProgramHistory
	same as GuestData only queries programhistory objects, which consist
	of guest, timestamp, programlist
GuestFormsCompleted
	same as GuestData only queries guestformscompleted objects, which
	consist of guest, form, complete
filterPrograms(table,**kwargs)
	acts as intermediary to allow filtering guest programs.  Returns
	table.programs.filter(**kwargs)
externalFunctions(name,*args)
	acts as intermediary to allow calling any report builder functions.  
	Returns output from function.
	
Standard Python functions:
len, type, parse (from dateutil), str, int, tuple, float, hashmap (dict
replacement, SecureDict object), sorted, list, iter, dir, relativedelta 
(from dateutil), range, sum, Q (from django)
Callable Attributes:
list.append, QuerySet.filter, QuerySet.first, QuerySet.last, 
QuerySet.exclude, QuerySet.order_by, QuerySet.prefetch_related, 
QuerySet.values_list, ValuesListQuerySet.distinct, str.join, str.split,
datetime.datetime.strftime, datetime.datetime.strptime, 
SecureDict.getItem, SecureDict.setItem, SecureDict.keys, 
SecureDict.values, SecureDict.pop
Replacement functions for uncallable attributes:
getDate(date)
	replacement for date.date().  Returns date.date()
Attribute accessible objects:
list, str, QuerySet, ValuesListQuerySet, ProgramHistory, Guest, 
GuestTimeData, GuestData, GuestFormsCompleted, Field, datetime.datetime,
datetime.date, datetime.timedelta, Program, SecureDict'''`;
	// Load JSON from server into window
	window.allowed_fields=JSON.parse(document.getElementById("loaded_fields").value||'{}');
	window.allowed_forms=Object.keys(allowed_fields);
	
	
	// Load saved report
	var loaded_report = JSON.parse(document.getElementById("loaded_report").value||'[[],[],[]]');
	var user_inputs = loaded_report[0]
	var calculations = loaded_report[1]
	var layout = loaded_report[2]
	
	// Display saved user inputs
	user_inputs = [["test", "test", "list", "test"],["test1", "test1", "date"]];
	var this_input = null;
	for (var idx=0;idx<user_inputs.length;idx++){
		this_input = user_inputs[idx];
		addUserInput(...this_input);
	}
	addUserInput();
	
	// Display saved calculation instructions
	calculations = [
					
					["foreach","variable","list", 
					 [
					  ["query",
					   "my_query",
					   [
					    ["field", "Checkin","Checked In","days active between", "date", "date"],
					    ["guest","","last_name","all"],
					    ["program","","program","on date","date"]
					   ],
					   [
					    ["and", "field", "Checkin", "Checked In", "=", "true", "on date", "date"],
					    ["or", "guest", "guest", "last_name", "contains", "something", "current"],
					    ["and", "program", "program", "program", "contains", "test", "between", "date", "date"]
					   ],
					   [
					    ["3"]
					   ]
					  ],
					  ["set","variable","value"]
					 ]
					]
				   ];
	for (idx=0;idx<calculations.length;idx++) {
		addCalculation(calculations[idx]);
	}
	addCalculation();

	for (idx=0;idx<layout.length;idx++) {
		addLayout("",layout[idx]);
	}
	addLayout(10);
	
}

// -----
// User Input Functions
// -----

// Function to show/hide extra validation box
function testValidation (t,idx) {
	if (t.value=="list" && !t.nextSibling) {
		var new_element = document.createElement("INPUT");
		t.parentElement.appendChild(new_element);
	} else if (t.nextSibling) {
		t.parentElement.removeChild(t.nextSibling);
	}
}

// Function to control the addition of new user input lines
function addUserInput (name,description,value,criteria) {
	name = name || "";
	description = description || "";
	value = value || "";
	criteria = criteria || "";
	var user_input_div = document.getElementById("user_inputs");
	if (name.type=="change") {
		if (user_input_div.lastChild.children[2].value != "") {
			addUserInput();
		}
		return ;
	}
	var new_element = null;
	var new_div = document.createElement("DIV");
	var new_option = null;

	new_div.appendChild(createButton("^",function(){user_input_div.insertBefore(new_div,new_div.previousSibling);}));
	new_div.appendChild(createButton("v",function(){user_input_div.insertBefore(new_div,new_div.nextSibling.nextSibling);}));

	new_element = document.createElement("INPUT");
	new_element.value = name;
	new_element.addEventListener("change",addUserInput);
	new_div.appendChild(new_element);

	new_element = document.createElement("INPUT");
	new_element.value = description;
	new_div.appendChild(new_element);

	new_element = document.createElement("SELECT");
	
	new_option = new Option("none", "none", value == "none");
	new_element.add(new_option);
	
	new_option = new Option("date", "date", value == "date");
	new_element.add(new_option);
	
	new_option = new Option("list", "list", value == "list");
	new_element.add(new_option);
	
	new_element.addEventListener("change",function(){testValidation(this,idx)});
	new_div.appendChild(new_element);

	if (value == "list") {
		new_element = document.createElement("INPUT");
		new_element.value = criteria;
		new_div.appendChild(new_element);
	}

	
	user_inputs_div.appendChild(new_div);


}

// -----
// Calculation Functions
// -----

// Function to register calculation functions

function availableMethods (name,target_div) {
	
	if (target_div) {
		for (var i=target_div.children.length-1;i>3;i--) {
			target_div.removeChild(target_div.children[i]);
		}
	}
	
	// Define available methods
	var methods = {
		"" : empty,
		"query" : _query,
		"set" : _set,
		"foreach" : _foreach,
		"python" : python,
	}
	
	if (name==undefined) {
		return Object.keys(methods);
	} else {
		return methods[name];
	}
}

// Calculation Function Definitions

function empty (trash) {}

function _query (target_div,instruction){
	// instruction = [name, return_variable, [[form 1, field 1, timeframe, date], [form 2, field 2, timeframe, date], ...], [criteria 1, criteria 2, ...]]
	
	var return_variable = document.createElement("INPUT");
	return_variable.addEventListener("change",function () {return_variable.value=return_variable.value.replace(" ","_");});
	if (instruction) {
		return_variable.value = instruction[1] || "";
	}
	target_div.appendChild(return_variable);
	
	var margin = getMargins(target_div);

	var select_title = document.createElement("DIV");
	select_title.innerHTML = "SELECT";
	select_title.style.margin = margin;
	target_div.appendChild(select_title);
	
	var select_div = document.createElement("DIV");
	select_div.style.margin = margin;

	target_div.appendChild(createButton("Add Field",function(){queryAddSelect(select_div)},margin));

	var field_div = null;
	var current_instruction = null;
	if (instruction) {
		for (var i=0;i<instruction[2].length;i++) {
			current_instruction = instruction[2][i];
			queryAddSelect(select_div, ...current_instruction);
		}
	}
	queryAddSelect(select_div);
	
	target_div.appendChild(select_div);
	
	var where_title = document.createElement("DIV");
	where_title.innerHTML = "WHERE";
	where_title.style.margin = margin;
	target_div.appendChild(where_title);
	
	var where_div = document.createElement("DIV");
	where_div.style.margin = margin;
	
	target_div.appendChild(createButton("Add Criteria",function(){queryAddWhere(where_div)},margin));
	
	if (instruction) {
		for (var i=0;i<instruction[3].length;i++) {
			current_instruction = instruction[3][i];
			queryAddWhere(where_div, ...current_instruction);
		}
	}
	queryAddWhere(where_div);
	
	target_div.appendChild(where_div);
	
	var extra_title = document.createElement("DIV");
	extra_title.innerHTML = "EXTRAS";
	extra_title.style.margin = margin;
	target_div.appendChild(extra_title);
	
	var extra_div = document.createElement("DIV");
	extra_div.style.margin = getMargins(where_div);
	
	extra_div.appendChild(document.createTextNode("ORDER BY"));
	var order_by = document.createElement("INPUT");
	order_by.style.width = "30px";
	if (instruction) {
		order_by.value = instruction[4][0];
	}
	extra_div.appendChild(order_by);
	
	target_div.appendChild(extra_div);

	var end_title = document.createElement("DIV");
	end_title.innerHTML = "END QUERY";
	end_title.style.margin = target_div.style.margin;
	target_div.appendChild(end_title);

	
}

function queryAddWhere (target_div, conjunction, type, form, field, operator, value, specialtype, special1, special2) {
	value = value || "";
	var field_div = document.createElement("DIV");
	field_div.handle = "criteria";
	
	field_div.appendChild(createButton("^",function(){target_div.insertBefore(field_div,field_div.previousSibling);}));
	field_div.appendChild(createButton("v",function(){target_div.insertBefore(field_div,field_div.nextSibling.nextSibling);}));
	
	field_div.appendChild(conjunctionSelect(conjunction));

	var type_select = fieldTypeSelect(type);
	field_div.appendChild(type_select);
	var form_select = formSelect(type_select,form);
	field_div.appendChild(form_select);
	var field_select = fieldSelect(form_select, field);
	field_div.appendChild(field_select);
	
	field_div.appendChild(operatorSelect(operator));

	var value_input = document.createElement("INPUT");
	value_input.value = value;
	field_div.appendChild(value_input);
	var return_type = returnTypeSelect(field_select, specialtype);
	field_div.appendChild(return_type);
	testReturnType(return_type, special1, special2);
	
	target_div.appendChild(field_div);
	
	
}

function queryAddSelect (target_div, type, form, field, rtype, rargument1, rargument2) {
	var field_div = document.createElement("DIV");
	field_div.handle = "select";

	field_div.appendChild(createButton("^",function(){target_div.insertBefore(field_div,field_div.previousSibling);}));
	field_div.appendChild(createButton("v",function(){target_div.insertBefore(field_div,field_div.nextSibling.nextSibling);}));


	var type_select = fieldTypeSelect(type);
	field_div.appendChild(type_select);
	var form_select = formSelect(type_select,form);
	field_div.appendChild(form_select);
	var field_select = fieldSelect(form_select, field);
	field_div.appendChild(field_select);
	var return_type = returnTypeSelect(field_select,rtype);
	field_div.appendChild(return_type);
	testReturnType(return_type, rargument1, rargument2);

	target_div.appendChild(field_div);
}

function testReturnType (t, val1, val2) {
	clearSpecialInputs(t.parentNode,"return_type_special");
	if (t.value=="on date") {
		var select_date = document.createElement("INPUT");
		select_date.handle = "return_type_special";
		select_date.value = val1 || "";
		t.parentNode.insertBefore(select_date,t.nextSibling);
	} else if (t.value=="days active between") {
		var select_date = document.createElement("INPUT");
		select_date.handle = "return_type_special";
		select_date.value = val1 || "";
		t.parentNode.insertBefore(select_date,t.nextSibling);
		var select_date1 = document.createElement("INPUT");
		select_date1.handle = "return_type_special";
		select_date1.value = val2 || "";
		t.parentNode.insertBefore(select_date1,select_date.nextSibling);
	}
}

function python (target_div,instruction) {
	var return_variable = document.createElement("INPUT");
	return_variable.addEventListener("change",function () {return_variable.value=return_variable.value.replace(" ","_");});
	if (instruction) {
		return_variable.value = instruction[1] || "";
	}
	target_div.appendChild(return_variable);

	var argument = document.createElement('DIV');
	argument.innerHTML='<text>If you see this text, have your administrator run "git submodule update --init --recursive"</text>';
	argument.style.width = '1000px';
	argument.style.height = '250px';
	argument.id = "Python"+editorscounter;
	editorscounter ++;
    editors[String(argument.id)] = false;
	target_div.appendChild(argument);
	var editor = ace.edit(argument.id);
	editor.setTheme("ace/theme/monokai");
	editor.getSession().setMode("ace/mode/python");
	editor.setValue(editor_default);
	editors[String(argument.id)] = editor;
}

function _set (target_div,instruction){
	// instruction = [name, return_variable, value]
	var return_variable = document.createElement("INPUT");
	return_variable.addEventListener("change",function () {return_variable.value=return_variable.value.replace(" ","_");});
	if (instruction) {
		return_variable.value = instruction[1] || "";
	}
	target_div.appendChild(return_variable);
	var value = document.createElement("INPUT");
	if (instruction) {
		value.value = instruction[2] || "";
	}
	target_div.appendChild(value);
	var type = document.createElement("SELECT");
	var option = new Option("list","list","list" == instruction[3]);
	type.appendChild(option);
	option = new Option("str","str","str" == instruction[3]);
	type.appendChild(option);
	option = new Option("int","int","int" == instruction[3]);
	type.appendChild(option);
	option = new Option("float","float","float" == instruction[3]);
	type.appendChild(option);
	option = new Option("date","date","date" == instruction[3]);
	type.appendChild(option);
	option = new Option("range","range","range" == instruction[3]);
	type.appendChild(option);
	target_div.appendChild(type);
	
}

function _foreach (target_div,instruction){
	// instruction = [name, iteration_variable, list, [instruction 1, instruction 2, ...]]
	var return_variable = document.createElement("INPUT");
	return_variable.addEventListener("change",function () {return_variable.value=return_variable.value.replace(" ","_");});
	if (instruction) {
		return_variable.value = instruction[1] || "";
	}
	target_div.appendChild(return_variable);
	var list = document.createElement("INPUT");
	if (instruction) {
		list.value = instruction[2] || "";
	}
	target_div.appendChild(list);
	
	var foreach_div = document.createElement("DIV");
	if (instruction) {
		for (var i=0;i<instruction[3].length;i++) {
			addCalculation(instruction[3][i],foreach_div);
		}
	}
	addCalculation("",foreach_div);
	target_div.appendChild(foreach_div);
}

// Function to control adding new calculation lines
function addCalculation (instruction, parent_div, next_div, del_div) {
	instruction = instruction || [];
	parent_div = parent_div || calculations_div;
	if (instruction.type=="change") {
		parent_div = this.parentNode.parentNode;
		if (parent_div.children[parent_div.children.length-1].children[3].value!="") {
			addCalculation("", parent_div);
		}
		return ;
	}
	
	if (del_div) {
		parent_div.removeChild(del_div);
	}
	var new_div = document.createElement("DIV");
	new_div.appendChild(createButton("+",function(){addCalculation("",parent_div,new_div)}));
	new_div.appendChild(createButton("^",function(){parent_div.insertBefore(new_div,new_div.previousSibling);}));
	new_div.appendChild(createButton("v",function(){parent_div.insertBefore(new_div,new_div.nextSibling.nextSibling);}));
	if (parent_div!=calculations_div) {
		new_div.style.margin = getMargins(parent_div);
	}
	
	var name = instruction[0] || "";
	var all_method_names = availableMethods();
	
	var name_select = document.createElement("SELECT");
	name_select.addEventListener("change",addCalculation);
	name_select.addEventListener("change",function () {availableMethods(name_select.value,new_div)(new_div);});
	
	var new_option = null;
	var this_option = null;
	for (var i=0;i<all_method_names.length;i++) {
		this_option = all_method_names[i];
		new_option = new Option(this_option, this_option, this_option == name);
		name_select.add(new_option);
	}
	
	new_div.appendChild(name_select);
	
	if (next_div) {
		parent_div.insertBefore(new_div,next_div);
	} else {
		parent_div.appendChild(new_div);
	}
	if (name) {
		availableMethods(name)(new_div, instruction);
	}
}
// -----
// Layout Functions
// -----

// Function to layout grid




// -----
// System Functions
// -----
function toggleReportView () {
	report_form_div.style.zIndex=String(Number(report_form_div.style.zIndex)*-1);
	if (report_form_div.style.zIndex<0) {
		report_view_toggle_button.value = "Show Builder";
	} else {
		report_view_toggle_button.value = "Show Overview";
	}
}

function getMargins (target_div) {
	var margin = target_div.style.margin || "1px 1px 1px 0px";
	margin = margin.split(" ")[3];
	margin = Number(margin.substring(0,margin.length-2))+10;
	margin = "1px 1px 1px "+margin+"px";
	return margin;
}

function createButton (value, func, margin) {
	margin = margin || "0px 0px 0px 0px";
	var add_button = document.createElement("INPUT");
	add_button.type="button";
	add_button.value = value;
	add_button.style.margin = margin;
	add_button.addEventListener("click",func);
	return add_button;
}

function findSubElementByHandle (target_div,handle) {
	var el = null;
	target_div = target_div || {"children":0};
	for (var i=0;i<target_div.children.length;i++) {
		if (target_div.children[i].handle == handle) {
			el = target_div.children[i];
			break;
		}
	}
	return el;
}

function clearSpecialInputs (target_div,handle) {
	for (var i=target_div.children.length-1;i>-1;i--) {
		if (target_div.children[i].handle == handle) {
			target_div.removeChild(target_div.children[i]);
		}
	}
}



function fieldTypeSelect (type) {
	var field_type_select = document.createElement("SELECT");
	field_type_select.handle = "field_type_select";
	var new_option = new Option("field", "field", "field"==type);
	field_type_select.appendChild(new_option);
	new_option = new Option("guest", "guest", "guest"==type);
	field_type_select.appendChild(new_option);
	new_option = new Option("program", "program", "program"==type);
	field_type_select.appendChild(new_option);
	field_type_select.addEventListener("change",function () {
		formSelect(field_type_select);
		fieldSelect(findSubElementByHandle(field_type_select.parentNode,"form_select"));
		returnTypeSelect(findSubElementByHandle(field_type_select.parentNode,"field_select"));
		testReturnType(findSubElementByHandle(field_type_select.parentNode,"return_type_select"));
	});
	return field_type_select;
}

function formSelect (field_type_select, form) {
	var parent_div = field_type_select.parentNode;
	var type_options = {"field":[""].concat(allowed_forms), "guest":["guest"], "program":["program"]};
	var form_select = findSubElementByHandle(parent_div,"form_select") || document.createElement("SELECT");
	form_select.handle = "form_select";
	form_select.options.length = 0;
	var name = null;
	var chosen_forms = type_options[field_type_select.value];
	var new_option = null;
	for (var i=0;i<chosen_forms.length;i++) {
		name = chosen_forms[i];
		new_option = new Option(name, name, name==form);
		form_select.appendChild(new_option);
	}
	form_select.addEventListener("change",function () {fieldSelect(form_select);});

	return form_select;
}

function fieldSelect (form_select,field) {
	var field_select = findSubElementByHandle(form_select.parentNode,"field_select") || document.createElement("SELECT");
	field_select.handle = "field_select";
	
	field_select.options.length=0;
	var new_option = new Option("", "");
	field_select.appendChild(new_option);
	if (form_select.value) {
		var field_options = allowed_fields[form_select.value] || {"guest":[["last_name",""],["first_name",""],["middle_name",""],["ssn",""],["picture",""]]}[form_select.value] || [["program",""]];
	} else {
		var field_options = [];
	}
	if (field_options) {
		for (var i=0;i<field_options.length;i++) {
			name = field_options[i][0];
			new_option = new Option(name, name, name==field);
			field_select.appendChild(new_option);
		}
	}
	field_select.addEventListener("change",function () {returnTypeSelect(field_select);testReturnType(findSubElementByHandle(field_select.parentNode,"return_type_select"));});
	return field_select;
}

function returnTypeSelect (field_select, type) {
	var options_dict = {"criteria":["current","on date","any","all","none"]};
	var options_list = options_dict[field_select.parentNode.handle] || ["current","all","on date"];
	var return_type_select = findSubElementByHandle(field_select.parentNode,"return_type_select") || document.createElement("SELECT");
	return_type_select.handle="return_type_select";

	return_type_select.options.length = 0;
	var new_option = null;
	var option = null;
	for (var i=0;i<options_list.length;i++) {
		option = options_list[i];
		new_option = new Option(option, option, option==type);
		return_type_select.appendChild(new_option);
	}
	
	var field_type_select = findSubElementByHandle(field_select.parentNode,"field_type_select") || "";
	field_type_select = field_type_select.value;
	
	var form = findSubElementByHandle(field_select.parentNode,"form_select") || "";
	form = allowed_fields[form.value];
	var field_type = null;
	if (field_type_select == "field" && form) {
		var field_tuple = null;
		for (var i=0;i<form.length;i++) {
			field_tuple = form[i];
			if (field_tuple[0] == field_select.value) {
				field_type = field_tuple[1];
				break;
			}
		}
		if (field_type == "boolean") {
			new_option = new Option("first activated", "first activated", "first activated"==type);
			return_type_select.appendChild(new_option);
			new_option = new Option("last activated", "last activated", "last activated"==type);
			return_type_select.appendChild(new_option);
			new_option = new Option("first deactivated", "first deactivated", "first deactivated"==type);
			return_type_select.appendChild(new_option);
			new_option = new Option("last deactivated", "last deactivated", "last deactivated"==type);
			return_type_select.appendChild(new_option);
			new_option = new Option("days active", "days active", "days active"==type);
			return_type_select.appendChild(new_option);
			new_option = new Option("times activated", "times activated", "times activated"==type);
			return_type_select.appendChild(new_option);
			new_option = new Option("days active between", "days active between", "days active between"==type);
			return_type_select.appendChild(new_option);
		}
	} else if (field_type_select == "guest") {
		clearSpecialInputs(field_select.parentNode,"return_type_special");
		return_type_select.options.length = 0;
		var new_option = new Option("current", "current", "current"==type);
		return_type_select.appendChild(new_option);
	}
	return_type_select.addEventListener("change",function () {testReturnType(return_type_select);});
	return return_type_select;
}

function conjunctionSelect (conjunction) {
	var new_select = document.createElement("SELECT");
	var new_option = new Option("","");
	new_select.appendChild(new_option);
	new_option = new Option("and","and", "and" == conjunction);
	new_select.appendChild(new_option);
	new_option = new Option("or","or", "or" == conjunction);
	new_select.appendChild(new_option);
	return new_select;
}

function operatorSelect (operator) {
	var new_select = document.createElement("SELECT");
	var new_option = new Option("","");
	new_select.appendChild(new_option);
	new_option = new Option("=","=", "=" == operator);
	new_select.appendChild(new_option);
	new_option = new Option("<>","<>", "<>" == operator);
	new_select.appendChild(new_option);
	new_option = new Option(">=",">=", ">=" == operator);
	new_select.appendChild(new_option);
	new_option = new Option("<=","<=", "<=" == operator);
	new_select.appendChild(new_option);
	new_option = new Option(">",">", ">" == operator);
	new_select.appendChild(new_option);
	new_option = new Option("<","<", "<" == operator);
	new_select.appendChild(new_option);
	new_option = new Option("in","in", "in" == operator);
	new_select.appendChild(new_option);
	new_option = new Option("contains","contains", "contains" == operator);
	new_select.appendChild(new_option);
	return new_select;
}
