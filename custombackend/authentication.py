import ldap
from UGM_Database import settings
from django.contrib.auth.models import User

class ActiveDirectoryGroupMembershipSSLBackend:
    def authenticate(self,username=None,password=None):
        if username:
            username = username.lower()
        try:
            if len(password) == 0:
                print '\n\n\n2'
                return None
            if settings.AD_CERT_FILE:
                ldap.set_option(ldap.OPT_X_TLS_CACERTFILE,settings.AD_CERT_FILE)
            else:
                ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
            l = ldap.initialize(settings.AD_LDAP_URL)
            l.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            binddn = "%s@%s" % (username,settings.AD_NT4_DOMAIN)
            try:
                l.simple_bind_s(binddn,password)
                l.unbind_s()
                settings.BROADCAST_MESSAGE = ''
                return self.get_or_create_user(username,password)
            except ldap.SERVER_DOWN:
                settings.BROADCAST_MESSAGE = 'Remote Server Unavailable, local login only'

        except ImportError:
            pass
        except ldap.INVALID_CREDENTIALS:
            pass

    def get_or_create_user(self, username, password):
        user,new = User.objects.get_or_create(username=username)
        if new:
            try:
                # debug info
                debug=0
                if len(settings.AD_DEBUG_FILE) > 0 and settings.AD_DEBUG:
                    debug=open(settings.AD_DEBUG_FILE,'w')
                    print >>debug, "create user %s" % username
                if settings.AD_CERT_FILE:
                    ldap.set_option(ldap.OPT_X_TLS_CACERTFILE,settings.AD_CERT_FILE)
                else:
                    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
                ldap.set_option(ldap.OPT_REFERRALS,0) # DO NOT TURN THIS OFF OR SEARCH WON'T WORK!
                # initialize
                if debug:
                    print >>debug, 'ldap.initialize...'
                l = ldap.initialize(settings.AD_LDAP_URL)
                l.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
                # bind
                if debug:
                    print >>debug, 'bind...'
                binddn = "%s@%s" % (username,settings.AD_NT4_DOMAIN)
                l.bind_s(binddn,password)

                # search
                if debug:
                    print >>debug, 'search...'
                result = l.search_ext_s(settings.AD_SEARCH_DN,ldap.SCOPE_SUBTREE,"sAMAccountName=%s" % username,settings.AD_SEARCH_FIELDS)[0][1]
                if debug:
                    print >>debug, result
                # Validate that they are a member of review board group
                membership = result.get('memberOf',None)
                if debug:
                    print >>debug, "required:%s" % settings.AD_MEMBERSHIP_REQ
                bValid=len(settings.AD_MEMBERSHIP_REQ)>0
                for req_group in settings.AD_MEMBERSHIP_REQ:
                    if debug:
                        print >>debug, "Check for %s group..." % req_group
                    for group in membership:
                        group_str="CN=%s," % req_group
                        if group.find(group_str) >= 0:
                            if debug:
                                print >>debug, "User authorized: group_str membership found!"
                            bValid=0
                            break
                if bValid:
                    if debug:
                        print >>debug, "User not authorized, correct group membership not found!"
                    return None

                # get email
                user.email = result.get('mail',[None])[0]
                if debug:
                    print >>debug, "mail=%s" % user.email
                # get surname
                user.last_name = result.get('sn',[None])[0]
                if debug:
                    print >>debug, "sn=%s" % user.last_name
                # get display name
                user.first_name = result.get('givenName',[None])[0]
                if debug:
                    print >>debug, "first_name=%s" % user.first_name

                l.unbind_s()

                user.is_staff = True
                user.is_superuser = False
                '''
                # add user to default group
                group=Group.objects.get(pk=1)
                if debug:
                    print >>debug, group
                if debug:
                    print >>debug, "add %s to group %s" % (username,group)
                user.groups.add(group)
                user.save()
                if debug:
                    print >>debug, "successful group add"
                '''
                if debug:
                    debug.close()

            except Exception, e:
                if debug:
                    print >>debug, "exception caught!"
                    print >>debug, e
                return None


        user.set_password(password)
        user.save()
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
