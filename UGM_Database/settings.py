"""
Django settings for UGM_Database project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os,json
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# import settings from text file
settingsfile = 'settings.conf'
if os.path.isfile('productionsettings.conf'):
	settingsfile = 'productionsettings.conf'
i=open(settingsfile,'r')
MYSETTINGS=json.loads(i.read())
i.close()


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

# import secret key
# SECURITY WARNING: keep the secret key used in production secret!
try:
	from SECRETKEY import SECRET_KEY
except ImportError:
	from django.utils.crypto import get_random_string
	chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
	o=open('SECRETKEY.py','w')
	o.write("SECRET_KEY='%s'"%get_random_string(50, chars))
	o.close()
	from SECRETKEY import SECRET_KEY

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = MYSETTINGS['DEBUG']

TEMPLATE_DEBUG = MYSETTINGS['DEBUG']

ALLOWED_HOSTS = MYSETTINGS['ALLOWED_HOSTS']

#ldap configuration
if MYSETTINGS.get("LDAP",{}).get("SERVER",'').replace("your_server",""):
	import ldap
	AD_DNS_NAME=MYSETTINGS['LDAP']['SERVER']
	AD_LDAP_PORT=MYSETTINGS['LDAP']['PORT']
	AD_LDAP_URL='ldap%s://%s:%s' %({True:'s',False:''}[MYSETTINGS['LDAP']['SSL']],AD_DNS_NAME,AD_LDAP_PORT)
	AD_SEARCH_DN=','.join(['dc='+i for i in MYSETTINGS['LDAP']['DOMAIN_SEARCH_BASE'].split('.')])
	AD_NT4_DOMAIN=MYSETTINGS['LDAP']['DOMAIN']
	AD_SEARCH_FIELDS= ['mail','givenName','sn','sAMAccountName','memberOf']
	AD_MEMBERSHIP_REQ=MYSETTINGS['LDAP']['REQUIRED_GROUPS']
	AD_CERT_FILE=MYSETTINGS['LDAP']['CERT_FILE']
	AUTHENTICATION_BACKENDS = (
		'custombackend.authentication.ActiveDirectoryGroupMembershipSSLBackend',
		'django.contrib.auth.backends.ModelBackend'
	)
	AD_DEBUG=True
	AD_DEBUG_FILE='/tmp/ldap.debug'
    
    
    
# Application definition

INSTALLED_APPS = tuple([
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles'] + MYSETTINGS['APPS'])

MIDDLEWARE_CLASSES = (
	'django.contrib.sessions.middleware.SessionMiddleware',
	'custommiddleware.middleware.setBaseSite',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
	'django.contrib.auth.context_processors.auth',
    'customcontextprocessor.context_processors.addBaseSite',
    'customcontextprocessor.context_processors.addBroadcastMessages',
    'django.contrib.messages.context_processors.messages',
)

ROOT_URLCONF = 'UGM_Database.urls'

WSGI_APPLICATION = 'UGM_Database.wsgi.application'


# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = MYSETTINGS['DATABASE']
PRIVATE_KEY_FILE = MYSETTINGS['PRIVATE_KEY_FILE']
PUBLIC_KEY_FILE = MYSETTINGS['PUBLIC_KEY_FILE']
CHAINED_CERTIFICATES_FILE = MYSETTINGS['CHAINED_CERTIFICATES_FILE']
PORT = MYSETTINGS['PORT']
if isinstance(PORT,str):
	if PORT.isdigit():
		PORT=int(PORT)
# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'US/Pacific'

USE_I18N = True

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, "static/")
STATIC_URL = '/static/'
MEDIA_ROOT = os.path.join(BASE_DIR, "static/media/")
MEDIA_URL='/static/media/'
# Template location
TEMPLATE_DIRS = [os.path.join(BASE_DIR, 'templates')]

# Login URL
LOGIN_URL = '/admin/login/'

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if MYSETTINGS.get('EMAIL',{}).get('EMAIL_HOST'):
	myadmins=MYSETTINGS['EMAIL'].get('ADMINS',[])
	ADMINS=[]
	for i in myadmins:
		ADMINS.append(tuple(i))
	ADMINS=tuple(ADMINS)
	
	EMAIL_HOST = MYSETTINGS['EMAIL'].get('EMAIL_HOST','')
	EMAIL_SUBJECT_PREFIX = MYSETTINGS['EMAIL'].get('EMAIL_SUBJECT_PREFIX','')
	SERVER_EMAIL = MYSETTINGS['EMAIL'].get('SERVER_EMAIL','')
	EMAIL_TIMEOUT = MYSETTINGS['EMAIL'].get('EMAIL_TIMEOUT','')
	EMAIL_PORT = MYSETTINGS['EMAIL'].get('EMAIL_PORT','')
	EMAIL_HOST_USER = MYSETTINGS['EMAIL'].get('EMAIL_HOST_USER','')
	EMAIL_HOST_PASSWORD = MYSETTINGS['EMAIL'].get('EMAIL_HOST_PASSWORD','')
	EMAIL_USE_TLS = MYSETTINGS['EMAIL'].get('EMAIL_USE_TLS','')

