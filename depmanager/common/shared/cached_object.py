class CachedObject:
    @property
    def _attributes(self):
        return []

    def _clear_attributes(self, attributes):
        for attrib in attributes:
            try:
                delattr(self, attrib)
            except AttributeError:
                continue

    def clear(self, attributes=None):
        if attributes is None:
            self._clear_attributes(self._attributes)
        else:
            self._clear_attributes(attributes)
