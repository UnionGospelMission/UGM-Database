document.ready=function (){
    if (document.getElementById('field_list').value!=''){
        window.field_list = JSON.parse(document.getElementById('field_list').value);
    } else {
        window.field_list = {};
    }
}

function changeForm(t){
	var field_select_div = document.getElementById('field_select_div')
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
}

function setFilter(){
	alert(this);
}
