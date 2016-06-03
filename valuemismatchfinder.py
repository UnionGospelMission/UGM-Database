import os,django,sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "UGM_Database.settings")
django.setup()

from guestmanagement.models import Guest,GuestTimeData,GuestData,Field

def findMismatchedData(field_name):
	q = '''SELECT a.*,e.value FROM ( 
			(
					(SELECT * from guestmanagement_guesttimedata WHERE guestmanagement_guesttimedata.field_id=%s) AS a
					INNER JOIN  
					(SELECT guest_id as tid,MAX(date) AS mdate FROM
							(SELECT * FROM guestmanagement_guesttimedata WHERE guestmanagement_guesttimedata.field_id=%s) AS c
					GROUP BY tid
					) AS b
					ON a.guest_id=b.tid AND b.mdate=a.date
			) AS a
			INNER JOIN
			(SELECT * FROM guestmanagement_guestdata WHERE guestmanagement_guestdata.field_id=%s) AS e
			ON a.guest_id=e.guest_id 
		) where a.value != e.value;'''
	field_id = Field.objects.get(name=field_name).id
	z=GuestTimeData.objects.raw(q,[field_id,field_id,field_id])
	return Guest.objects.filter(id__in=[i.guest_id for i in z])

def updateGuestTimeDataToMatch(field_name,guest_list):
	field_id = Field.objects.get(name=field_name).id
	for i in guest_list:
		y=GuestTimeData.objects.filter(guest=i,field__id=field_id).order_by('-date').first()
		if y:
			y.value = GuestData.objects.get(guest=i,field__id=field_id).value
			y.save()
		sys.stdout.write('%s                \r'%(float(list(guest_list).index(i))/float(len(list(guest_list))),))
		sys.stdout.flush()

def updateGuestDataToMatch(field_name,guest_list):
	field_id = Field.objects.get(name=field_name).id
	for i in guest_list:
		y=GuestTimeData.objects.filter(guest=i,field__id=field_id).order_by('-date').first()
		if y:
			x= GuestData.objects.get(guest=i,field__id=field_id)
			x.value = y.value
			x.save()
		sys.stdout.write('%s                \r'%(float(list(guest_list).index(i))/float(len(list(guest_list))),))
		sys.stdout.flush()
