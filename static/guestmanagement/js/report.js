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
