from .Function import Function
from .Sandbox import Sandbox
import dis,sys

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


comparator_dict = {
                    '==':lambda left,right: left==right,
                    'not in':lambda left,right: left not in right,
                    '!=':lambda left,right: left != right,
                    '<':lambda left,right: left < right,
                    '<=':lambda left,right: left <= right,
                    '>':lambda left,right: left > right,
                    '>=':lambda left,right: left >= right,
                    'in':lambda left,right: left in right,
                    'is':lambda left,right: left is right,
                    'is not':lambda left,right: left is not right,
                  }
class OpMap(object):
    __modules__={}
    NORETURN = object()
    @staticmethod
    def getOp(opname):
        return getattr(OpMap, opname)
    @staticmethod
    def POP_TOP(sandbox, args):
        sandbox.stack.get()
        return OpMap.NORETURN
    @staticmethod
    def ROT_TWO(sandbox, args):
        sandbox.stack[-1], sandbox.stack[-2] = sandbox.stack[-2], sandbox.stack.queue[-1]
        return OpMap.NORETURN
    @staticmethod
    def ROT_THREE(sandbox, args):
        a = sandbox.stack[-3:]
        a.insert(-3, a.get(-1))
        sandbox.stack[-3:] = a
        return OpMap.NORETURN
    @staticmethod
    def DUP_TOP(sandbox, args):
        sandbox.stack.put(sandbox.stack[-1])
        return OpMap.NORETURN

    @staticmethod
    def UNARY_NEGATIVE(sandbox, args):
        sandbox.stack[-1] = - sandbox.stack[-1]
        return OpMap.NORETURN

    @staticmethod
    def UNARY_NOT(sandbox, args):
        sandbox.stack[-1] = not sandbox.stack[-1]
        return OpMap.NORETURN

    @staticmethod
    def UNARY_INVERT(sandbox, args):
        sandbox.stack[-1] = ~ sandbox.stack[-1]
        return OpMap.NORETURN

    @staticmethod
    def BINARY_POWER(sandbox, args):
        a = sandbox.stack.get()
        b = sandbox.stack.get()
        sandbox.stack.put(b**a)
        return OpMap.NORETURN

    @staticmethod
    def BINARY_MULTIPLY(sandbox, args):
        a = sandbox.stack.get()
        b = sandbox.stack.get()
        sandbox.stack.put(b*a)
        return OpMap.NORETURN


    @staticmethod
    def BINARY_FLOOR_DIVIDE(sandbox, args):
        a = sandbox.stack.get()
        b = sandbox.stack.get()
        sandbox.stack.put(b // a)
        return OpMap.NORETURN

    @staticmethod
    def BINARY_TRUE_DIVIDE(sandbox, args):
        a = sandbox.stack.get()
        b = sandbox.stack.get()
        sandbox.stack.put(b / a)
        return OpMap.NORETURN

    @staticmethod
    def BINARY_MODULO(sandbox, args):
        a = sandbox.stack.get()
        b = sandbox.stack.get()
        sandbox.stack.put(b % a)
        return OpMap.NORETURN

    @staticmethod
    def BINARY_ADD(sandbox, args):
        a = sandbox.stack.get()
        b = sandbox.stack.get()
        sandbox.stack.put(b + a)
        return OpMap.NORETURN

    @staticmethod
    def BINARY_SUBTRACT(sandbox, args):
        a = sandbox.stack.get()
        b = sandbox.stack.get()
        sandbox.stack.put(b - a)
        return OpMap.NORETURN

    @staticmethod
    def BINARY_SUBSCR(sandbox, args):
        a = sandbox.stack.get()
        b = sandbox.stack.get()
        sandbox.stack.put(b[a])
        return OpMap.NORETURN

    @staticmethod
    def LOAD_NAME(sandbox, args):
        name_idx = args[0] + args[1] * 256
        name = sandbox.function.names[name_idx]
        sandbox.stack.put(sandbox.loadName(name))
        return OpMap.NORETURN

    def LOAD_FAST(sandbox, args):
        name_idx = args[0] + args[1] * 256
        name = sandbox.function.varnames[name_idx]
        sandbox.stack.put(sandbox.loadName(name))
        return OpMap.NORETURN

    @staticmethod
    def STORE_NAME(sandbox, args):
        name_idx = args[0] + args[1] * 256
        name = sandbox.function.names[name_idx]
        sandbox.storeName(name, sandbox.stack.get())
        return OpMap.NORETURN

    @staticmethod
    def CALL_FUNCTION(sandbox, args):
        argc = args[0]
        argk = args[1]
        kargs = {}
        for idx in range(argk):
            val = sandbox.stack.get()
            key = sandbox.stack.get()
            kargs[key]=val
        args = []
        for idx in range(argc):
            args.insert(0, sandbox.stack.get())
        function = sandbox.stack.get()
        sandbox.stack.put(sandbox.callFunction(function, args, kargs))
        return OpMap.NORETURN

    @staticmethod
    def LOAD_CONST(sandbox, args):
        const_idx = args[0] + args[1] * 256
        sandbox.stack.put(sandbox.function.constants[const_idx])
        return OpMap.NORETURN

    @staticmethod
    def MAKE_FUNCTION(sandbox, args):
        argc = args[0]+args[1]*256
        if argc!=0:
            raise TypeError("Annotations and default arguments are not supported")
        name = sandbox.stack.get()
        code = sandbox.stack.get()
        args = code.co_varnames[:code.co_argcount]
        function = Function(name, code, args, sandbox)
        sandbox.stack.put(function)
        return OpMap.NORETURN

    @staticmethod
    def RETURN_VALUE(sandbox, args):
        return sandbox.stack.get()

    @staticmethod
    def LOAD_ATTR(sandbox, args):
        namei = args[0] + args[1] * 256
        name = sandbox.function.names[namei]
        tos = sandbox.stack.get()
        sandbox.stack.put(sandbox.getAttr(tos, name))
        return OpMap.NORETURN

    @staticmethod
    def BUILD_LIST(sandbox, args):
        count = args[0] + args[1]*256
        if count==0:
            sandbox.stack.put([])
            return OpMap.NORETURN
        o = sandbox.stack[-count:]
        sandbox.stack[-count:] = [o]
        return OpMap.NORETURN

    @staticmethod
    def BUILD_MAP(sandbox, args):
        count = args[0] + args[1] * 256
        o = {}
        for idx in range(count):
            val = sandbox.stack.get()
            o[sandbox.stack.get()] = val
        sandbox.stack.put(o)
        return OpMap.NORETURN

    @staticmethod
    def SETUP_LOOP(sandbox, args):
        delta = args[0] + args[1] * 256
        sandbox.blocks.put(sandbox.function[sandbox.index:sandbox.index + delta])
        return OpMap.NORETURN
    
    @staticmethod
    def GET_ITER(sandbox, args):
        sandbox.stack[-1]=iter(sandbox.stack[-1])
        return OpMap.NORETURN
    
    @staticmethod
    def FOR_ITER(sandbox, args):
        delta = args[0] + args[1] * 256
        sigil = object()
        n = next(sandbox.stack[-1], sigil)
        if n is sigil:
            sandbox.stack.get()
            sandbox.index+=delta
        else:
            sandbox.stack.put(n)
        return OpMap.NORETURN
    
    @staticmethod
    def JUMP_ABSOLUTE(sandbox, args):
        idx = args[0] + args[1] * 256
        sandbox.index = idx
        return OpMap.NORETURN
    
    @staticmethod
    def POP_BLOCK(sandbox, args):
        sandbox.blocks.get()
        return OpMap.NORETURN

    @staticmethod
    def IMPORT_NAME(sandbox, args):
        idx = args[0] + args[1] * 256
        name = sandbox.function.names[idx]
        if name in OpMap.__modules__:
            sandbox.stack.put(OpMap.__modules__[name])
            return OpMap.NORETURN
        raise ImportError()

    @staticmethod
    def LIST_APPEND(sandbox, args):
        idx = args[0] + args[1] * 256
        TOS = sandbox.stack.get()
        lst = sandbox.stack.queue[-idx]
        if type(lst)!=list:
            raise TypeError("List comprehensions can only operate on lists")
        lst.append(TOS)
        return OpMap.NORETURN
    
    @staticmethod
    def COMPARE_OP(sandbox, args):
        idx = args[0] + args[1] * 256
        comparator = dis.cmp_op[idx]
        right=sandbox.stack.get()
        left=sandbox.stack.get()
        if not comparator_dict.get(comparator,None):
            raise TypeError("%s comparator not supported"%comparator)
        sandbox.stack.put(comparator_dict[comparator](left,right))
        return OpMap.NORETURN

    @staticmethod
    def POP_JUMP_IF_FALSE(sandbox, args):
        idx = args[0] + args[1] * 256
        TOS = sandbox.stack.get()
        if not TOS:
            sandbox.index = idx
        return OpMap.NORETURN

    @staticmethod
    def POP_JUMP_IF_TRUE(sandbox, args):
        idx = args[0] + args[1] * 256
        TOS = sandbox.stack.get()
        if TOS:
            sandbox.index = idx
        return OpMap.NORETURN

    @staticmethod
    def JUMP_FORWARD(sandbox, args):
        idx = args[0] + args[1] * 256
        sandbox.index += idx
        return OpMap.NORETURN
    
    @staticmethod
    def JUMP_IF_TRUE_OR_POP(sandbox, args):
        idx = args[0] + args[1] * 256
        if sandbox.stack[-1]:
            sandbox.index += idx
        else:
            TOS = sandbox.stack.get()
        return OpMap.NORETURN

    @staticmethod
    def PRINT_ITEM(sandbox, args):
        TOS = sandbox.stack.get()
        print TOS,
        return OpMap.NORETURN

    @staticmethod
    def PRINT_NEWLINE(sandbox, args):
        sys.stdout.write('\n')
        sys.stdout.flush()
        return OpMap.NORETURN
