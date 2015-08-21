window.onload=function (){
    // Report Viewer
    window.report_viewer = document.getElementById('report_builder');
    if (document.getElementById('loaded_report').value!=''){
        var loaded_report = JSON.parse(document.getElementById('loaded_report').value);
    } else {
        var loaded_report = [];
    }
    for (var i=0;i<loaded_report.length;i++){
        newRow(loaded_report[i][0],loaded_report[i][1],loaded_report[i][2],loaded_report[i][3]);
    }
    newRow();
    
    // Field Select
    if (document.getElementById('loaded_fields').value!=''){
        window.loaded_fields = JSON.parse(document.getElementById('loaded_fields').value);
    } else {
        window.loaded_fields = [];
    }
    window.field_viewer = document.getElementById('fields');
    window.previous_element = undefined;
    
}


// Report Viewer Functions


function newRow(type,value1,value2,value3){
    if (! window.last_row) {
        window.last_row = 0;
    }
    var new_row = report_viewer.appendChild(document.createElement('div'));
    new_row.line_number = window.last_row;
        var new_type = new_row.appendChild(document.createElement('select'));
            new_type.appendChild(new Option('',''));
            new_type.appendChild(new Option('count','count'));
            new_type.appendChild(new Option('sum','sum'));
            new_type.appendChild(new Option('text','text'));
            new_type.appendChild(new Option('field','field'));
            new_type.appendChild(new Option('list','list'));
            if (type){
                new_type.value = type;
            } else {
                new_type.value = '';
            }
            new_type.name = 'code' + String(new_row.line_number) + '-0';
            new_type.onchange = typeChange;

        switch (type) {
            case 'text':
                var new_filter = new_row.appendChild(document.createElement('input'));
                new_filter.value = value1;
                new_filter.name = 'code' + String(new_row.line_number) + '-1';
                new_filter.onblur = setTarget;
                break;

            case 'count':
            case 'sum':
            case 'field':
            case 'list':
                var new_filter = new_row.appendChild(document.createElement('input'));
                new_filter.value = value1;
                new_filter.name = 'code' + String(new_row.line_number) + '-1';
                new_filter.onblur = setTarget;
        
                var new_field = new_row.appendChild(document.createElement('input'));
                new_field.value = value2;
                new_field.name = 'code' + String(new_row.line_number) + '-2';
                new_field.onblur = setTarget;
        
                var new_field = new_row.appendChild(document.createElement('input'));
                new_field.type = 'checkbox';
                if (value3 == 'undefined' || value3=='on'){
                    new_field.checked = 'checked';
                }
                new_field.name = 'code' + String(new_row.line_number) + '-3';
            
                break;
        }
    window.last_row++;
}

function setTarget() {
    window.previous_element = this;
}

function typeChange(){
    while (this.nextSibling){
        this.parentNode.removeChild(this.nextSibling);
    }
    if (this.value != ''){
        var new_filter = this.parentNode.appendChild(document.createElement('input'));
        new_filter.name = 'code' + String(this.parentNode.line_number) + '-1';
        new_filter.onblur = setTarget;
        switch (this.value){
            case 'count':
            case 'sum':
            case 'field':
            case 'list':
                var new_field = this.parentNode.appendChild(document.createElement('input'));
                new_field.name = 'code' + String(this.parentNode.line_number) + '-2';
                new_field.onblur = setTarget;
                var new_field = this.parentNode.appendChild(document.createElement('input'));
                new_field.type = 'checkbox';
                new_field.name = 'code' + String(this.parentNode.line_number) + '-3';
                new_field.onblur = setTarget;
                break;
        }
    }
    
    if (! this.parentNode.nextSibling){
        newRow();
    }

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
        document.getElementById('report_title').innerHTML = 'Working on report<br />' + document.getElementById('id_name').value;
    } else {
        report_form.style.zIndex='-1';
        document.getElementById('report_view_toggle').value = 'Report Builder';
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
    if (previous_element.value!=''){
        previous_element.value += ' :: ' + prepend + this.innerHTML;
    } else {
        previous_element.value = prepend + this.innerHTML;
    }
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
    var form = document.getElementsByTagName('form')[1];
    var new_input = form.appendChild(document.createElement('input'));
    new_input.name = 'save_report';
    new_input.value = 'True';
    form.submit();
}
