_NOT_FOUND = object()

# noinspection PyPep8Naming
# pylint: disable=invalid-name
class cached_property:
    """
    Lightweight and non-thread safe cached property decorator.
    This is an alternative to the functools.cached_property that, while thread safe,
    is also slower, and we don't care about true thread safety in this program.
    This version also has fewer checks than the Django version because it is only
    for python 3.10+
    """

    def __init__(self, func):
        self.func = func
        self.attr_name = None
        self.__doc__ = func.__doc__

    def __set_name__(self, owner, name):
        if self.attr_name is None:
            self.attr_name = name
        elif name != self.attr_name:
            raise TypeError(
                "Cannot assign the same cached_property to two different names " f"({self.attr_name!r} and {name!r})."
            )

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        if self.attr_name is None:
            raise TypeError("Cannot use cached_property instance without calling __set_name__ on it.")
        res = instance.__dict__[self.attr_name] = self.func(instance)
        return res
