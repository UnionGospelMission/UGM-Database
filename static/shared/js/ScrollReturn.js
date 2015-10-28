document.ready=function (){
	var sm = window.localStorage.getItem('scrollMemory');
	if (sm){
		sm = sm.split(",");
		window.scrollTo(sm[0],sm[1]);
		localStorage.removeItem('scrollMemory');
	}
	
}

function scrollReturn(t) {
	var x = (window.pageXOffset || document.documentElement.scrollLeft) - (document.documentElement.clientLeft || 0);
	var y = (window.pageYOffset || document.documentElement.scrollTop)  - (document.documentElement.clientTop || 0);
	window.localStorage.setItem('scrollMemory',[x,y]);
	
	while (t.tagName!="FORM"){
		t = t.parentNode;
	}
	var a = document.createElement('input');
		a.style.display='none';
		a.value = 'Update';
		a.name = 'submit_form';
	t.appendChild(a);
	t.submit();
}
