class CentreScopedMixin:
    centre_field = 'centre'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role in ['agent', 'chef_centre']:
            return qs.filter(**{self.centre_field: user.centre})
        return qs