from types import CodeType


class Function(object):
    def __repr__(self):
        return "<Function %s(%s)>" % (self.name, ','.join(self.arguments))
    def __init__(self, name, code, arguments, closure=None):
        self.code = code
        self.arguments = arguments
        self.name = name
        self.names = code.co_names
        self.constants = code.co_consts
        self.closure = closure
        self.varnames = code.co_varnames
    def __getitem__(self, item):
        return self.code.co_code[item]
