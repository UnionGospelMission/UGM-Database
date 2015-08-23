window.onload=function (){
    // Miscellaneous
    window.total_form = document.getElementsByTagName('form')[1];
    // Field Select
    if (document.getElementById('loaded_fields').value!=''){
        window.loaded_fields = JSON.parse(document.getElementById('loaded_fields').value);
    } else {
        window.loaded_fields = [];
    }
    window.field_viewer = document.getElementById('fields');
    window.previous_element = undefined;
    
    if (document.getElementById('report_functions').value!=''){
        window.report_functions = JSON.parse(document.getElementById('report_functions').value);
    } else {
        window.report_functions = [];
    }
    // Report Viewer
    window.report_viewer = document.getElementById('report_builder');
    if (document.getElementById('loaded_report').value!=''){
        var loaded_report = JSON.parse(document.getElementById('loaded_report').value);
    } else {
        var loaded_report = [];
    }
    for (var i=0;i<loaded_report.length;i++){
        newRow(loaded_report[i].shift(),loaded_report[i]);
    }
    newRow();
    changeReturnVariable();

}


// Report Viewer Functions

function insertRow(row_num){
    if (! row_num){
        row_num = prompt("Insert Where?", "");
    }
    if (Number(row_num) || (Number(row_num)==0 && row_num!=null)){
        row_num = Number(row_num);
        var new_row = newRow(undefined,undefined,true);
        report_viewer.insertBefore(new_row,report_viewer.children[row_num+1]);
        while (new_row){
            new_row.childNodes[0].nodeValue = leadingZeros(row_num);
            new_row.line_number = row_num;
            for (var i=0;i<new_row.children.length;i++){
                new_row.children[i].name = 'code'+String(row_num)+'-'+String(i);
            }
            new_row = new_row.nextSibling;
            row_num += 1;
        }
    }
}


function newRow(type,values,insert){
    if (! window.last_row) {
        window.last_row = 0;
    }
    if (! insert){
        var new_row = report_viewer.appendChild(document.createElement('div'));
    } else {
        new_row = document.createElement('div');
    }
    new_row.line_number = window.last_row;
        new_row.appendChild(document.createTextNode(leadingZeros(new_row.line_number)));
        var new_type = new_row.appendChild(document.createElement('select'));
            new_type.appendChild(new Option('',''));
            new_type.appendChild(new Option('count','count'));
            new_type.appendChild(new Option('sum','sum'));
            new_type.appendChild(new Option('text','text'));
            new_type.appendChild(new Option('newline','newline'));
            new_type.appendChild(new Option('list','list'));
            new_type.appendChild(new Option('and','and'));
            new_type.appendChild(new Option('or','or'));
            new_type.appendChild(new Option('display','display'));
            new_type.appendChild(new Option('function','function'));
            new_type.appendChild(new Option('extrafield','extrafield'));
            new_type.appendChild(new Option('end','end'));
            new_type.appendChild(new Option('set','set'));
            new_type.setAttribute('title','Select Row Type');
            if (type){
                new_type.value = type;
                typeChange(new_type,true);
            } else {
                new_type.value = '';
            }
            new_type.name = 'code' + String(new_row.line_number) + '-0';
            new_type.onchange = typeChange;
    if (values){
        for (var i=0;i<values.length;i++){
            if (new_type.parentNode.children[i+1].type!='checkbox'){
                new_type.parentNode.children[i+1].value = values[i];
            } else {
                new_type.parentNode.children[i+1].checked = values[i];
            }
			if (i+1==1 && new_type.value=='function'){
				setFunctionName(new_type.parentNode.children[i+1]);
			}
        }
    }

    window.last_row++;
    if (insert){
        return new_row;
    }
}

function setTarget() {
    window.previous_element = this;
}

function typeChange(t,single){
    if (! t.parentNode){
        t = this;
    }
    while (t.nextSibling){
        t.parentNode.removeChild(t.nextSibling);
    }
    switch (t.previous_value){
        case 'list':
        case 'set':
        case 'function':
            changeReturnVariable();
            break;
    }
    if (t.value != ''){
        var row = t.parentNode;
        var name_offset = 0;
        switch (t.value){
            case 'text':
                var bold = row.appendChild(document.createElement('select'));
                    bold.appendChild(new Option('none','none'));
                    bold.appendChild(new Option('h1','h1'));
                    bold.appendChild(new Option('h2','h2'));
                    bold.appendChild(new Option('h3','h3'));
                    bold.appendChild(new Option('h4','h4'));
                    bold.appendChild(new Option('h5','h5'));
                    bold.value = 'none';
                    bold.name = 'code'+row.line_number+'-1';
                    bold.setAttribute('title','Pick text bold level');

                var value = row.appendChild(document.createElement('input'));
                    value.name = 'code'+row.line_number+'-2';
                    value.setAttribute('title','Enter Text to Display');
                break;

            case 'list':
                name_offset = 3;
                var list_type = row.appendChild(document.createElement('select'));
                    list_type.appendChild(new Option('fields','fields'));
                    list_type.appendChild(new Option('numbers','numbers'));
                    list_type.name = 'code'+row.line_number+'-1';
                    list_type.setAttribute('title','Pick List Type');
                    list_type.onchange = changeListType;
                var list_return = row.appendChild(document.createElement('input'));
                    list_return.name = 'code'+row.line_number+'-2';
                    list_return.setAttribute('title','Set List Variable Name');
                    list_return.onchange = changeReturnVariable;
                var num_per_row = row.appendChild(document.createElement('input'));
                    num_per_row.name = 'code'+row.line_number+'-3';
                    num_per_row.setAttribute('title','Number of Items Per Row');
            case 'extrafield':
            case 'display':
            case 'count':
            case 'sum':
                var display_field = row.appendChild(document.createElement('input'));
                    display_field.name = 'code'+row.line_number+'-'+String(name_offset+1);
                    display_field.setAttribute('title','Pick Field to Return');
                    display_field.onblur = setTarget;
                var timeseries = row.appendChild(document.createElement('input'));
                    timeseries.type = 'checkbox';
                    timeseries.name = 'code'+row.line_number+'-'+String(name_offset+2);
                    timeseries.setAttribute('title','Return Time Series');
                    var empty = document.createElement('input');
                        empty.name = 'code'+row.line_number+'-'+String(name_offset+2);
                        empty.style.display = 'none';
                        total_form.insertBefore(empty,total_form.children[0]);
                    
                if (! single && (' list sum count display'.search(t.previous_value)<1 && ' list sum count display'.search(t.value)>-1)){
                    insertRow(row.line_number+1);
                    row.nextSibling.children[0].value = 'and';
                    typeChange(row.nextSibling.children[0]);
                    insertRow(row.line_number+2);
                    row.nextSibling.nextSibling.children[0].value = 'end';
                    typeChange(row.nextSibling.nextSibling.children[0]);
                }
                break;

            case 'and':
            case 'or':
                var operator = row.appendChild(document.createElement('select'));
                    operator.appendChild(new Option('',''));
                    operator.appendChild(new Option('=','='));
                    operator.appendChild(new Option('>','>'));
                    operator.appendChild(new Option('>=','>='));
                    operator.appendChild(new Option('<','<'));
                    operator.appendChild(new Option('<=','<='));
                    operator.value = '';
                    operator.name = 'code'+row.line_number+'-1';
                    operator.setAttribute('title','Pick Operator');
                    operator.onchange = changeOperator;

                var value = row.appendChild(document.createElement('input'));
                    value.name = 'code'+row.line_number+'-2';
                    value.onblur = setTarget;
                    value.setAttribute('title','Pick Operator First');

                var field = row.appendChild(document.createElement('input'));
                    field.name = 'code'+row.line_number+'-3';
                    field.onblur = setTarget;
                    field.setAttribute('title','Pick Field');
                var timeseries = row.appendChild(document.createElement('input'));
                    timeseries.type = 'checkbox';
                    timeseries.name = 'code'+row.line_number+'-4';
                    timeseries.setAttribute('title','Return Time Series');
                    var empty = document.createElement('input');
                        empty.name = 'code'+row.line_number+'-4';
                        empty.style.display = 'none';
                        total_form.insertBefore(empty,total_form.children[0]);
                break;
            
            case 'function':
                var function_name = row.appendChild(document.createElement('select'));
                for (var i=0;i<report_functions.length;i++){
                    function_name.appendChild(new Option(report_functions[i][0],report_functions[i][0]));
                }
                    function_name.name = 'code'+row.line_number+'-1';
                    function_name.setAttribute('title','Pick Function');
                    function_name.onchange = setFunctionName;
                var function_return = row.appendChild(document.createElement('input'));
                    function_return.name = 'code'+row.line_number+'-2';
                    function_return.setAttribute('title','Set List Variable');
                    function_return.onchange = changeReturnVariable;
                setFunctionName(function_name);
                break;

            case 'set':
                var name = row.appendChild(document.createElement('input'));
                    name.name = 'code'+row.line_number+'-1';
                    name.setAttribute('title','Set Name');
                    name.onchange = changeReturnVariable;
                var value = row.appendChild(document.createElement('input'));
                    value.name = 'code'+row.line_number+'-2';
                    value.setAttribute('title','Set Value');
                break;
        }
    }
    t.previous_value = t.value;
    if (! t.parentNode.nextSibling && ! single){
        newRow();
    }

}

function setFunctionName(t){
	if (t instanceof Event) {
		t=this;
	}
	var variable_name = t.nextSibling;
	while (variable_name.nextSibling){
		variable_name.parentNode.removeChild(variable_name.nextSibling);
	}
	for (var i=0;i<report_functions.length;i++){
		if (report_functions[i][0]==t.value){
			for (var a=2;a<report_functions[i][1].length;a++){
				var argument = t.parentNode.appendChild(document.createElement('input'));
					argument.name = 'code'+t.parentNode.line_number+'-'+String(a+1);
                    argument.setAttribute('title',report_functions[i][1][a]);
			}
			break;
		}
	}
}

function changeReturnVariable(){
    var var_list = [];
    for (var i=0;i<report_viewer.children.length;i++){
        var return_name = '';
        switch (report_viewer.children[i].children[0].value){
            case 'list':
                report_viewer.children[i].children[2].value = report_viewer.children[i].children[2].value.split(' ').join('_');
                return_name = report_viewer.children[i].children[2].value;
                break;
            case 'function':
                return_name = report_viewer.children[i].children[2].value;
                report_viewer.children[i].children[2].value = report_viewer.children[i].children[2].value.split(' ').join('_');
                break;
            case 'set':
                return_name = report_viewer.children[i].children[1].value;
                report_viewer.children[i].children[1].value = report_viewer.children[i].children[1].value.split(' ').join('_');
                break;
        }
        if (return_name !='' && var_list.indexOf(return_name)==-1){
            var_list.push(return_name);
        }
    }
    var function_select = document.getElementById('function_select');
    function_select.removeChild(function_select.children[1]);
    var var_names = function_select.appendChild(document.createElement('ul'));
        var_names.className += ' variable_list';
    for (var i=0;i<var_list.length;i++){
        var child = document.createTextNode(var_list[i]);
        var list_element = var_names.appendChild(document.createElement('li'));
        list_element.onclick = insertVariable;
        list_element.appendChild(child);
    }
}

function insertVariable(){
    if (! previous_element){
        alert('Click where you want a variable inserted, then click your variable again');
        return;
    }
    var prepend = ' $';
    previous_element.value += prepend + this.innerHTML;
}

function changeListType(){
    if (this.value=='numbers'){
        var from = '';
        var to = '';
        do {
            from = prompt('Number Range from','0');
        } while (! Number(from) && Number(from)!=0 && from!=null);
        if (from==null){
            this.value = 'fields';
            return;
        }
        do {
            to = prompt('Number Range to',String(Number(from)+1));
        } while (! Number(to) && Number(to)!=0 && to!=null);
        if (to==null){
            this.value = 'fields';
            return;
        }
        this.parentNode.children[5].value = String(from)+':'+String(to);
    } else {
        this.parentNode.children[5].value = '';
    }
}

function changeOperator(){
    switch (this.value){
        case '':
            this.nextSibling.setAttribute('title','Pick Operator First');
            break;
        case '=':
            this.nextSibling.setAttribute('title','Equals What?');
            break;
        case '>':
            this.nextSibling.setAttribute('title','Greater Than What?');
            break;
        case '<':
            this.nextSibling.setAttribute('title','Less Than What?');
            break;
        case '>=':
            this.nextSibling.setAttribute('title','Greater Than or Equal to What?');
            break;
        case '<=':
            this.nextSibling.setAttribute('title','Less Than or Equal to What?');
            break;
    }

}


// Field Select Functions

function selectForm(t) {
    field_viewer.removeChild(field_viewer.children[1]);
    window.form_name = t.innerHTML;
    var selected_form = loaded_fields[t.innerHTML];
    var new_field_list = field_viewer.appendChild(document.createElement('table'));
    var new_header = new_field_list.createTHead();
    var header_row = new_header.insertRow();
    var header_cell = header_row.insertCell();
    header_cell.appendChild(document.createTextNode('Field Name'));
    header_cell.className += ' field_list_header';
    var header_cell = header_row.insertCell();
    header_cell.appendChild(document.createTextNode('Field Type'));
    header_cell.className += ' field_list_header';
    for (var i=0;i<selected_form.length;i++){
        var new_row = new_field_list.insertRow();
        var new_cell = new_row.insertCell();
        new_cell.appendChild(document.createTextNode(selected_form[i][0]));
        new_cell.onclick = insertField;
        var new_cell = new_row.insertCell();
        new_cell.appendChild(document.createTextNode(selected_form[i][1]));
    }
}

function insertField(){
    if (! previous_element){
        alert('Click where you want a field inserted, then click your field again');
        return;
    }
    var prepend = 'field.';
    if (form_name=='guest'){
        prepend = 'guest.';
    }
    previous_element.value = prepend + this.innerHTML;
}

// Function Select

function addOperator(t) {
    if (! previous_element){
        alert('Click where you want an operator inserted, then click your operator again');
        return;
    }
    var value = '';
    var insert = '';
    switch (t.innerHTML){
        case 'Equals':
            value = prompt("Equals What?", "");
            insert = '= ';
            break;
        case 'Greater Than':
            value = prompt("Greater Than What?", "");
            insert = '> ';
            break;
        case 'Less Than':
            value = prompt("Less Than What?", "");
            insert = '< ';
            break;
        case 'Greater Than or Equals':
            value = prompt("Greater Than or Equal to What?", "");
            insert = '>= ';
            break;
        case 'Less Than or Equals':
            value = prompt("Less Than or Equal to What?", "");
            insert = '<= ';
            break;
        case 'And':
            insert = ' & ';
            break;
        case 'Or':
            insert = ' | ';
            break;
        case 'Field Change':
            insert = ' :: ';
            break;
    }
    previous_element.value += insert + value;
}

// Miscellaneous

function submitAndContinue() {
    var new_input = total_form.appendChild(document.createElement('input'));
    new_input.name = 'save_report';
    new_input.value = 'True';
    total_form.submit();
}

function toggleReportView() {
    var report_title = document.getElementById('id_name').value;
    if (report_title==''){
        alert('Report needs a name!');
        return
    }
    var report_form = document.getElementById('report_form');
    var standard_form = document.getElementById('standard_form');
    if (report_form.style.zIndex=='-1' || report_form.style.zIndex==''){
        report_form.style.zIndex='1';
        document.getElementById('report_view_toggle').value = 'Report Information';
        document.getElementById('insert_row').style.display = 'inline';
        document.getElementById('report_title').innerHTML = '<h1>Working on report</h1><br /><h1>' + document.getElementById('id_name').value + '</h1>';
    } else {
        report_form.style.zIndex='-1';
        document.getElementById('report_view_toggle').value = 'Report Builder';
        document.getElementById('insert_row').style.display = 'none';
    }
}

function leadingZeros(number){
    var retval = "0" + String(number);
    return retval.substr(retval.length-2);
}

function alertName(){
    alert(this.name);
}
