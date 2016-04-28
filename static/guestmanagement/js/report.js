document.ready=function (){
    window.debug = false;
    // Miscellaneous
	window.total_form = document.getElementsByName('TotalForm')[0];
    // Field Select
    if (document.getElementById('loaded_fields').value!=''){
        window.loaded_fields = JSON.parse(document.getElementById('loaded_fields').value);
    } else {
        window.loaded_fields = [];
    }
    window.field_viewer = document.getElementById('fields');
    window.previous_element = undefined;
    window.previous_element_inserted = undefined;
    
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
    // Variable Select
    if (document.getElementById('helper_variables').value!=''){
        window.helper_variables = JSON.parse(document.getElementById('helper_variables').value);
    } else {
        window.helper_variables = [];
    }
    changeReturnVariable();
	// Set global onfocus
	var focusHandler = function(event) {
		if (previous_element_inserted){
			previous_element = undefined;
			previous_element_inserted = undefined;
		}
	};
	document.body.addEventListener('focus', focusHandler, true);
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
    indentRows();
}

function indentRows(){
    var indent_level = 0;
    for (var i=0;i<report_viewer.children.length;i++){
        report_viewer.children[i].style.marginLeft = String(indent_level * 10)+"px";
        switch (report_viewer.children[i].children[0].value){
            case 'query':
            case 'list':
            case 'sum':
            case 'count':
            case 'display':
            case 'if':
                indent_level += 1;
                break;
            case 'end':
                indent_level -= 1;
                report_viewer.children[i].style.marginLeft = String(indent_level * 10)+"px";
                break;
        }
    }
    return indent_level
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
            new_type.appendChild(new Option('query','query'));
            new_type.appendChild(new Option('if','if'));
            new_type.appendChild(new Option('and','and'));
            new_type.appendChild(new Option('or','or'));
            new_type.appendChild(new Option('display','display'));
            new_type.appendChild(new Option('function','function'));
            new_type.appendChild(new Option('extrafield','extrafield'));
            new_type.appendChild(new Option('end','end'));
            new_type.appendChild(new Option('set','set'));
            new_type.appendChild(new Option('user input','user input'));
            new_type.appendChild(new Option('begin table','begin table'));
            new_type.appendChild(new Option('end table','end table'));
            new_type.appendChild(new Option('link','link'));
            new_type.appendChild(new Option('calendar','calendar'));
            new_type.appendChild(new Option('section break','section break'));
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
            try {
                if (new_type.parentNode.children[i+1].type!='checkbox'){
                    new_type.parentNode.children[i+1].value = values[i];
                } else {
                    new_type.parentNode.children[i+1].checked = values[i];
                }
                if (i+1==1 && new_type.value=='function'){
                    setFunctionName(new_type.parentNode.children[i+1]);
                }
            }
            catch (err){

            }
        }
    }

    window.last_row++;
    if (insert){
        return new_row;
    }
    indentRows();
}

function setTarget() {
	if (previous_element_inserted){
		previous_element_inserted = false;
	} else {
		window.previous_element = this;
	}
}

function typeChange(t,single){
    if (t instanceof Event) {
        t=this;
    }
    while (t.nextSibling){
        t.parentNode.removeChild(t.nextSibling);
    }
    t.onclick=alertName;
    switch (t.previous_value){
        case 'query':
        case 'list':
        case 'set':
        case 'function':
        case 'user input':
            changeReturnVariable();
            break;
    }
    if (t.value != ''){
        var row = t.parentNode;
        var name_offset = 0;
        switch (t.value){
			case 'section break':
				var text = document.createTextNode('---------------------------------------------------------------------------');
					row.appendChild(text);
				break;
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
                    bold.onclick=alertName;

                var value = row.appendChild(document.createElement('textarea'));
					value.rows = '1';
					value.wrap='soft';
					value.style.height = '17px';
                    value.name = 'code'+row.line_number+'-2';
                    value.setAttribute('title','Enter Text to Display');
                    value.onclick=alertName;
                    value.onblur = setTarget;
                break;

            case 'list':
            case 'query':
                name_offset = 3;
                var list_type = row.appendChild(document.createElement('select'));
                    list_type.appendChild(new Option('fields','fields'));
                    list_type.appendChild(new Option('numbers','numbers'));
                    list_type.name = 'code'+row.line_number+'-1';
                    list_type.setAttribute('title','Pick List Type');
                    list_type.onchange = changeListType;
                    list_type.onclick=alertName;
                var list_return = row.appendChild(document.createElement('input'));
                    list_return.name = 'code'+row.line_number+'-2';
                    list_return.setAttribute('title','Set List Variable Name');
                    list_return.onblur = setTarget;
                    list_return.onchange = changeReturnVariable;
                    list_return.onclick=alertName;
                var sort_by = row.appendChild(document.createElement('input'));
                    sort_by.name = 'code'+row.line_number+'-3';
                    sort_by.setAttribute('title','Set Sort By');
                    sort_by.onblur = setTarget;
                    sort_by.onclick=alertName;
                if (t.value=='list'){
                    var num_per_row = row.appendChild(document.createElement('input'));
                        num_per_row.name = 'code'+row.line_number+'-4';
                        num_per_row.setAttribute('title','Number of Items Per Row');
                        num_per_row.onclick=alertName;
                        num_per_row.onblur = setTarget;
                    var rows_per_page = row.appendChild(document.createElement('input'));
                        rows_per_page.name = 'code'+row.line_number+'-5';
                        rows_per_page.setAttribute('title','Number of Rows Per Page');
                        rows_per_page.onclick=alertName;
                        rows_per_page.onblur = setTarget;
                    var row_separator = row.appendChild(document.createElement('input'));
                        row_separator.name = 'code'+row.line_number+'-6';
                        row_separator.setAttribute('title','Row Separator');
                        row_separator.onblur = setTarget;
                        row_separator.onclick=alertName;
                        name_offset = 6;
                    }
            case 'extrafield':
            case 'display':
            case 'count':
            case 'sum':
                var display_field = row.appendChild(document.createElement('input'));
                    display_field.name = 'code'+row.line_number+'-'+String(name_offset+1);
                    display_field.setAttribute('title','Pick Field to Return');
                    display_field.onblur = setTarget;
                    display_field.onclick=alertName;
                if (t.value=='display'){
                    var separator = row.appendChild(document.createElement('input'));
                        separator.name = 'code'+row.line_number+'-'+String(name_offset+2);
                        separator.setAttribute('title','Display Separator');
                        name_offset+=1;
                        separator.onclick=alertName;
                        separator.onblur = setTarget;
                }
                var timeseries = row.appendChild(document.createElement('input'));
                    timeseries.type = 'checkbox';
                    timeseries.name = 'code'+row.line_number+'-'+String(name_offset+2);
                    timeseries.setAttribute('title','Return Time Series');
                    timeseries.onclick=alertName;
                    
                if (! single && (' list sum count display query'.search(t.previous_value)<1 && ' list sum count display query'.search(t.value)>-1)){
                    insertRow(row.line_number+1);
                    row.nextSibling.children[0].value = 'and';
                    typeChange(row.nextSibling.children[0]);
                    insertRow(row.line_number+2);
                    row.nextSibling.nextSibling.children[0].value = 'end';
                    typeChange(row.nextSibling.nextSibling.children[0]);
                }
                indentRows();
                break;

            case 'and':
            case 'or':
            case 'if':
                var operator = row.appendChild(document.createElement('select'));
                    operator.appendChild(new Option('',''));
                    operator.appendChild(new Option('=','='));
                    operator.appendChild(new Option('<>','<>'));
                    operator.appendChild(new Option('>','>'));
                    operator.appendChild(new Option('>=','>='));
                    operator.appendChild(new Option('<','<'));
                    operator.appendChild(new Option('<=','<='));
                    operator.appendChild(new Option('contains','contains'));
                    operator.value = '';
                    operator.name = 'code'+row.line_number+'-1';
                    operator.setAttribute('title','Pick Operator');
                    operator.onchange = changeOperator;
                    operator.onclick=alertName;

                var value = row.appendChild(document.createElement('input'));
                    value.name = 'code'+row.line_number+'-2';
                    value.onblur = setTarget;
                    value.setAttribute('title','Pick Operator First');
                    value.onclick=alertName;

                var field = row.appendChild(document.createElement('input'));
                    field.name = 'code'+row.line_number+'-3';
                    field.onblur = setTarget;
                    field.setAttribute('title','Pick Field');
                    field.onclick=alertName;
                var timeseries = row.appendChild(document.createElement('input'));
                    timeseries.type = 'checkbox';
                    timeseries.name = 'code'+row.line_number+'-4';
                    timeseries.setAttribute('title','Return Time Series');
                    timeseries.onclick=alertName;
                break;
            
            case 'function':
                var function_name = row.appendChild(document.createElement('select'));
                for (var i=0;i<report_functions.length;i++){
                    function_name.appendChild(new Option(report_functions[i][0],report_functions[i][0]));
                }
                    function_name.name = 'code'+row.line_number+'-1';
                    function_name.setAttribute('title','Pick Function');
                    function_name.onchange = setFunctionName;
                    function_name.onclick=alertName;
                var function_return = row.appendChild(document.createElement('input'));
                    function_return.name = 'code'+row.line_number+'-2';
                    function_return.setAttribute('title','Set List Variable');
                    function_return.onchange = changeReturnVariable;
                    function_return.onclick=alertName;
                    function_return.onblur = setTarget;
                setFunctionName(function_name);
                break;

            case 'set':
            case 'calendar':
            case 'user input':
                var name = row.appendChild(document.createElement('input'));
                    name.name = 'code'+row.line_number+'-1';
                    name.setAttribute('title','Set Name');
                    name.onchange = changeReturnVariable;
                    name.onblur = setTarget;
                    name.onclick=alertName;
                var dropdown = row.appendChild(document.createElement('input'));
					dropdown.name = 'code'+row.line_number+'-2';
                    dropdown.setAttribute('title','Comma Separated Options');
                    dropdown.onclick=alertName;
                if (t.value=='set'){
                        dropdown.setAttribute('title','Set Value');
                        dropdown.onblur=setTarget;
                }
                if (t.value=='calendar'){
                        dropdown.setAttribute('title','Comment List');
                        dropdown.onblur=setTarget;
                        name.setAttribute('title','Date List');
                        name.onblur=setTarget;
                }
                break;

            case 'begin table':
                var name = row.appendChild(document.createElement('input'));
                    name.name = 'code'+row.line_number+'-1';
                    name.setAttribute('title','Comma Separated Row Headers');
                    name.onclick=alertName;
                break;
            
            case 'link':
				var guest_id = row.appendChild(document.createElement('input'));
					guest_id.name = 'code'+row.line_number+'-1';
					guest_id.setAttribute('title','Guest ID');
                    guest_id.onclick=alertName;
                    guest_id.onblur=setTarget;
				var form_id = row.appendChild(document.createElement('input'));
					form_id.name = 'code'+row.line_number+'-2';
					form_id.setAttribute('title','Form ID');
                    form_id.onclick=alertName;
                    form_id.onblur=setTarget;
				var text = row.appendChild(document.createElement('input'));
					text.name = 'code'+row.line_number+'-3';
					text.setAttribute('title','Display Text');
                    text.onclick=alertName;
                    text.onblur=setTarget;
				break;
            
        }
    }
    t.previous_value = t.value;
    if (! t.parentNode.nextSibling && ! single){
        newRow();
    }
    indentRows();
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
                    argument.onclick=alertName;
                    argument.onblur=setTarget;
            }
            break;
        }
    }
}

function changeReturnVariable(){
    var var_list = window.helper_variables;
    for (var i=0;i<report_viewer.children.length;i++){
        var return_name = '';
        if (report_viewer.children[i].children.length > 1){
            switch (report_viewer.children[i].children[0].value){
                case 'query':
                case 'list':
                    report_viewer.children[i].children[2].value = report_viewer.children[i].children[2].value.split(' ').join('_');
                    return_name = report_viewer.children[i].children[2].value;
                    break;
                case 'function':
                    report_viewer.children[i].children[2].value = report_viewer.children[i].children[2].value.split(' ').join('_');
                    return_name = report_viewer.children[i].children[2].value;
                    break;
                case 'user input':
                case 'set':
                    report_viewer.children[i].children[1].value = report_viewer.children[i].children[1].value.split(' ').join('_');
                    return_name = report_viewer.children[i].children[1].value;
                    break;
            }
        }
        return_name = return_name.split('!').join('');
        if (return_name !='' && var_list.indexOf(return_name)==-1 && return_name.indexOf('::')==-1){
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
    if (previous_element.parentNode.children[0].value=='text'){
		previous_element.value += '{{ $' + this.innerHTML + ' }}';
	} else {
		previous_element.value += ' $' + this.innerHTML;
	}
    previous_element.focus();
    previous_element = undefined;
    previous_element_inserted = true;
}

function changeListType(){
    if (this.value=='numbers'){
        var from = '';
        var to = '';
        from = prompt('Number Range from','');
        if (from==null){
            this.value = 'fields';
            return;
        }
        to = prompt('Number Range to','');
        if (to==null){
            this.value = 'fields';
            return;
        }
        switch (this.parentNode.children[0].value){
            case 'list':
                this.parentNode.children[7].value = String(from)+':'+String(to);
                break;
            case 'query':
                this.parentNode.children[4].value = String(from)+':'+String(to);
        }
    } else {
        switch (this.parentNode.children[0].value){
            case 'list':
                this.parentNode.children[7].value = '';
                break;
            case 'query':
                this.parentNode.children[4].value = '';
        }
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
        case '<>':
            this.nextSibling.setAttribute('title','Not Equals What?');
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
        case 'contains':
            this.nextSibling.setAttribute('title','Contains What?');
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
    if (form_name=='date'){
        prepend = 'date.';
    }
    previous_element.value = prepend + this.innerHTML;
    previous_element.focus();
    previous_element = undefined;
    previous_element_inserted = true;
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

function processReport(t) {
    if (indentRows()!=0){
        alert('Report Not Valid');
        return;
    }
    for (var i=0;i<report_viewer.children.length;i++){
        var row = report_viewer.children[i];
        for (var a=0;a<row.children.length;a++){
            if (row.children[a].type=='checkbox'){
                var empty = document.createElement('input');
                empty.name = row.children[a].name;
                empty.style.display = 'none';
                total_form.insertBefore(empty,total_form.children[0]);
            }
        }
    }
    if (t.value=='Submit and Continue Editing'){
        var new_input = total_form.appendChild(document.createElement('input'));
        new_input.style.display = 'none';
        new_input.name = 'save_report';
        new_input.value = 'True';
    }
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
        document.getElementById('menu').style.zIndex='-150';
    } else {
        report_form.style.zIndex='-1';
        document.getElementById('report_view_toggle').value = 'Report Builder';
        document.getElementById('insert_row').style.display = 'none';
        document.getElementById('menu').style.zIndex='150';
    }
}

function leadingZeros(number){
    var retval = "0000" + String(number);
    return retval.substr(retval.length-4);
}

function alertName(){
    if (debug){
        console.log(this.name);
    }
}

function runReport(t){
    var input = document.getElementsByTagName('input');
    if (input.length>0){
        t.href = t.href.split("?")[0] + "?"+input[0].name+'='+input[0].value;
        for (var i=1;i<input.length;i++){
            t.href+='&'+input[i].name+'='+input[i].value;
        }
    }
    var select = document.getElementsByTagName('select');
    if (select.length>0){
		var i=0;
		if (input.length==0){
			t.href = t.href.split("?")[0] + "?"+select[0].name+'='+select[0].value;
			i=1;
		}
        for (i;i<select.length;i++){
            t.href+='&'+select[i].name+'='+select[i].value;
        }
    }
    t.style.display = 'none';
    //alert(document.getElementsByName('variable__test')[0].value);
}
