from rest_framework.serializers import HyperlinkedIdentityField, HyperlinkedRelatedField


class UUIDHyperlinkedIdentityField(HyperlinkedIdentityField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("source", "*")
        kwargs.setdefault("lookup_field", "uuid")
        kwargs.setdefault("lookup_url_kwarg", "uuid")
        super().__init__(*args, **kwargs)


class UUIDHyperlinkedRelatedField(HyperlinkedRelatedField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("lookup_field", "uuid")
        kwargs.setdefault("lookup_url_kwarg", "uuid")
        super().__init__(*args, **kwargs)
