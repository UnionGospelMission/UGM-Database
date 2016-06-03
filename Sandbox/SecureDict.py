

class SecureDict(object):   
    __slots__ = ('__items__',)
    def __init__(self, *a, **kw):   
        self.__items__ = dict(*a, **kw)
    def getItem(self, item, default = None):
		if default:
			return self.__items__.get(item,default)
		return self.__items__[item]
    def setItem(self, item, value): 
        self.__items__[item] = value
    def __repr__(self):
        return 'SecureDict(%r)' % self.__items__
	__str__ = __repr__
