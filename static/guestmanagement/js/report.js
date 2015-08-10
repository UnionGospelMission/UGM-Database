function toggleReportView() {
    var report_form = document.getElementById('report_form');
    var standard_form = document.getElementById('standard_form');
    if (report_form.style.zIndex=='-1' || report_form.style.zIndex==''){
        report_form.style.zIndex='1';
        document.getElementById('report_view_toggle').value = 'Report Information';
    } else {
        report_form.style.zIndex='-1';
        document.getElementById('report_view_toggle').value = 'Report Builder';
    }
}
