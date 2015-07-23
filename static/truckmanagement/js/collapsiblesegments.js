$('#hideTrigger').live('click', function(e){
  var name = $(this).attr("class").split(' ')[0];
  $("div.collapse" + name).toggle();
});
