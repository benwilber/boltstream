from django.db.models import Q
from django_filters import CharFilter, FilterSet

from .models import Stream


class StreamFilter(FilterSet):

    search = CharFilter(method="filter_streams")

    class Meta:
        model = Stream
        fields = ("search",)

    def filter_streams(self, queryset, name, value):
        q = (
            Q(title__icontains=value)
            | Q(user__username__icontains=value)
            | Q(user__profile__name__icontains=value)
        )
        return queryset.filter(q)
