function formSubmitConfirm (formname,message) {
    if (confirm(message)){
        document.getElementsByName(formname)[0].submit();
    } else {
        return;
    }
}