def interactiveConsole(a,b=None):
    '''
        Useful function for debugging
        Placing interactiveConsole(locals(),globals()) into code will
        drop into an interactive console when run
    '''
    import code
    d = {}
    if b:
        d.update(b)
    d.update(a)
    c=code.InteractiveConsole(locals=d)
    c.interact()


class SecureDict(object):   
    __slots__ = ('__items__',)
    def __init__(self, *a, **kw):
        self.__items__ = dict(*a, **kw)
    def getItem(self, item, default = None):
        if default!=None:
            return self.__items__.get(item,default)
        try:
            return self.__items__[item]
        except KeyError:
            raise KeyError('Key Error: %s'%item)
    def setItem(self, item, value): 
        self.__items__[item] = value
    def __len__(self):
        return len(self.__items__)
    def __repr__(self):
        return 'SecureDict(%r)' % self.__items__
    __str__ = __repr__
    
    def keys(self):
        return self.__items__.keys()

    def values(self):
        return self.__items__.values()
        
    def pop(self,key):
        return self.__items__.pop(key)
