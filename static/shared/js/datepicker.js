
// on page load

$(function() {
    $( ".datePicker" ).datepicker({
        changeMonth: true,
        changeYear: true,
        yearRange: "1900:2100",
        defaultDate: +0,
    });
});
