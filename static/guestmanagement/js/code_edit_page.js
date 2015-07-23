

var editor = ace.edit("editor");
editor.setTheme("ace/theme/twilight");
editor.getSession().setMode("ace/mode/scheme");

function onSubmit(){
	//editor = ace.edit('editor');
	var code = editor.getSession().getValue();
	document.getElementById('code').value=code;
}

$(document).click(function(event) {
    var targetform = $(event.target);
    if (targetform.attr('class')=='target_form_choice'){
		var field_list = JSON.parse(document.getElementById('database_viewer').getAttribute('field_dict'))[targetform.attr('targetform')];
		var name_replacement_html = "<h3>Fields on Form</h3><br/><ul>";
		var type_replacement_html = "<h3>Type of Field</h3><br/><ul>";
		var arrayLength = field_list.length;
		for (i = 0; i < arrayLength; i++) {
			name_replacement_html = name_replacement_html.concat('<li class="target_field_choice" field_name="');
			name_replacement_html = name_replacement_html.concat(field_list[i][0]);
			name_replacement_html = name_replacement_html.concat('">');
			name_replacement_html = name_replacement_html.concat(field_list[i][0]);
			name_replacement_html = name_replacement_html.concat('</li>');
			type_replacement_html = type_replacement_html.concat('<li>');
			type_replacement_html = type_replacement_html.concat(field_list[i][1]);
			type_replacement_html = type_replacement_html.concat('</li>');
		}
		name_replacement_html = name_replacement_html.concat('</ul>');
		type_replacement_html = type_replacement_html.concat('</ul>');
		document.getElementById('form_viewer_name').innerHTML = name_replacement_html;
		document.getElementById('form_viewer_type').innerHTML = type_replacement_html;
	}
	else if (targetform.attr('class')=='target_field_choice'){
		editor.insert('field.'.concat(targetform.attr('field_name').replace(' ','_').concat(' ')));
		editor.focus();
	}
	else if (targetform.attr('class')=='target_code_command'){
		var code_command = targetform.attr('code_command');
		switch (code_command){
			case 'clear':
				editor.setValue("");
				resetHelper();
				break;
			case 'reset_help':
				resetHelper();
				break;
			case 'undo':
				editor.undo();
				break;
			case 'redo':
				editor.redo();
				break;
			case 'Database_Query':
				editor.insert('(sql ');
				document.getElementById('code_command_viewer').innerHTML=buildHTML(['End','select','count','where','and','or']);
				break;
			case 'End':
				editor.insert(')');
				resetHelper();
				break;
			case 'count':
				editor.insert('count ');
				document.getElementById('code_command_viewer').innerHTML=buildHTML(['End','select','count','where','and','or']);
				break;
			case 'select':
				editor.insert('select ');
				document.getElementById('code_command_viewer').innerHTML=buildHTML(['End','select','count','where','and','or']);
				break;
			case 'where':
				editor.insert('where ');
				document.getElementById('code_command_viewer').innerHTML=buildHTML(['End','select','count','where','and','or']);
				break;
			case 'and':
				editor.insert(' and ');
				document.getElementById('code_command_viewer').innerHTML=buildHTML(['End','select','count','where','and','or']);
				break;
		}
		editor.focus();
	}
});

function resetHelper (){
	document.getElementById('code_command_viewer').innerHTML=buildHTML(['Database Query']);
}

function buildHTML (command_list){
	var return_html = '';
	for (i = 0; i < command_list.length; i++) {
		return_html = return_html.concat("<div class='target_code_command' code_command='").concat(command_list[i].replace(' ','_')).concat("'>").concat(command_list[i]).concat("</div></br>");
	}
	return return_html;
}
