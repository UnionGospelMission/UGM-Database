class Module(object):
    def __init__(self, attrs):
        self.attrs=attrs
    def __getattribute__(self, attr):
        if attr=='attrs':
            return object.__getattribute__(self, attr)
        if attr in self.attrs:
            return self.attrs[attr]
        raise AttributeError()

