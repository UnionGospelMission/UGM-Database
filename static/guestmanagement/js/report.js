

window.onload=function (){
    window.report_viewer = document.getElementById('report_builder');
    if (document.getElementById('loaded_report').value!=''){
        alert(document.getElementById('loaded_report').value);
        var loaded_report = JSON.parse(document.getElementById('loaded_report').value);
    } else {
        var loaded_report = [];
    }
    for (var i=0;i<loaded_report.length;i++){
        newRow(loaded_report[i][0],loaded_report[i][1],loaded_report[i][2]);
    }
    newRow();
}

function newRow(type,value1,value2){
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
            new_type.onblur = setTarget;
	
        if (value1){
            var new_filter = new_row.appendChild(document.createElement('input'));
            new_filter.value = value1;
            new_filter.name = 'code' + String(new_row.line_number) + '-1';
            new_filter.onblur = setTarget;
        }
        
        if (value2){
            var new_field = new_row.appendChild(document.createElement('input'));
            new_field.value = value2;
            new_field.name = 'code' + String(new_row.line_number) + '-2';
            new_field.onblur = setTarget;
        }



    window.last_row++;
}

function setTarget() {
    window.previous_element = this;
}

function typeChange(){
    if (! this.nextSibling){
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
                break;
        }
    } else if (this.value == 'text' && this.nextSibling.nextSibling){
        this.parentNode.removeChild(this.nextSibling.nextSibling);
    } else if (this.value == '') {
        this.parentNode.removeChild(this.nextSibling);
        this.parentNode.removeChild(this.nextSibling);
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
