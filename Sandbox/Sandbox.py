from opcode import opname
from Queue import LifoQueue as LQ
import time
from dis import HAVE_ARGUMENT
from .Function import Function
from types import MethodType, BuiltinMethodType

class TimeoutError(Exception):
	def __init__(self, *args, **kwargs):
		Exception.__init__(self,*args,**kwargs)

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


class LifoQueue(LQ):
    def __init__(self,sandbox):
        LQ.__init__(self)
        self.sandbox = sandbox
    def __getitem__(self, item):
        return self.queue[item]
    def __setitem__(self, item, val):
        self.queue[item] = val
    def get(self):
        if self.sandbox.debug:
            print 'get last_index='+str(self.sandbox.last_index)
        return LQ.get(self, False)
    def put(self, val):
        if self.sandbox.debug:
            print 'put last_index='+str(self.sandbox.last_index)
        return LQ.put(self, val)
    def __len__(self):
        return len(self.queue)


class Sandbox(object):
    SUSPEND = object()

    def __init__(self, parent, function, arguments, globals=None, functions=(), attributes_accessible = (), debug=False):
        self.debug = debug
        self.parent = parent
        if globals is None:
            globals = {}
        if parent:
            self.stack = parent.stack
            self.blocks = parent.blocks
            self.frames = parent.frames
            self.globals = parent.globals
            self.functions = parent.functions
            self.attributes_accessible = parent.attributes_accessible
        else:
            self.stack = LifoQueue(self)
            self.blocks = LifoQueue(self)
            self.frames = LifoQueue(self)
            self.globals = globals
            self.functions = functions
            self.attributes_accessible = attributes_accessible
        self.local_variables = {}
        self.function = function
        self.arguments = arguments
        self.index = 0
        self.last_index = 0
    def storeGlobal(self, name, value):
        p = self
        while p.parent:
            p=p.parent
        p.storeName(name, value)
    def loadGlobal(self, name):
        try:
            return self.loadName(name)
        except NameError as e:
            if self.parent:
                return self.parent.loadGlobal(name)
            raise e
    def loadName(self, name):
        if name in self.local_variables:
            return self.local_variables[name]
        closure = self.function.closure
        while closure:
            if name in closure.local_variables:
                return closure.local_variables[name]
            closure = closure.function.closure
        if name in self.globals:
            return self.globals[name]
        raise NameError("%s is not defined" % name)

    def getAttr(self, obj, attr):
        if obj in self.attributes_accessible:
            return getattr(obj, attr)
        if isinstance(obj, tuple(i for i in self.attributes_accessible if type(i) is type)):
            return getattr(obj, attr)
        if type(obj) in self.attributes_accessible:
            return getattr(obj, attr)
        if obj.__class__ in self.attributes_accessible:
            return getattr(obj, attr)
        raise AttributeError("%r attribute access denied" % type(obj))

    def storeName(self, name, value):
        self.local_variables[name] = value

    def callFunction(self, function, arguments, kw=None):
        ofunc = None
        if isinstance(function, BuiltinMethodType):
            oself = function.__self__
            if oself is not None:
                ofunc = getattr(type(oself), function.__name__)
            
        if (ofunc and ofunc in self.functions) or function in self.functions or (isinstance(function, MethodType) and function.__func__ in self.functions):
            if kw is None:
                kw = {}
            return function(*arguments, **kw)
        if type(function) == Function:
            if kw:
                raise TypeError('Keyword arguments unsupported')
            exc = Sandbox(self, function, arguments)
            gen = exc.execute(self.iterlimit - self.counter, self.timelimit + self.startTime - time.time())
            ret = next(gen)
            if ret == self.SUSPEND:
                raise TimeoutError("Timeout in %r" % function)
            self.counter += exc.counter
            return ret
        raise TypeError("Function %r not allowed" %function)

    def execute(self, iterlimit, timelimit):
        self.startTime = time.time()
        self.counter = 0
        self.iterlimit = iterlimit
        self.timelimit = timelimit
        if len(self.arguments) != len(self.function.arguments):
            raise TypeError("%r expects %i arguments, got %i" % (
                self.function,
                len(self.arguments),
                len(self.function.arguments)))
        for idx, i in enumerate(self.function.arguments):
            self.local_variables[i] = self.arguments[idx]
        while True:
            self.counter += 1
            now = time.time()
            if now - self.startTime > self.timelimit:
                self.timelimit += yield self.SUSPEND
            if self.counter > self.iterlimit:
                self.iterlimit += yield self.SUSPEND
            opcode = ord(self.function[self.index])
            self.last_index = self.index
            if opcode >= HAVE_ARGUMENT:
                args = [ord(i) for i in self.function[self.index + 1:self.index + 3]]
                self.index += 3
            else:
                args = []
                self.index += 1
            operation = opname[opcode]
            function = OpMap.getOp(operation)
            ret = function(self, args)
            if ret != OpMap.NORETURN:
                yield ret


from .OpMap import OpMap
