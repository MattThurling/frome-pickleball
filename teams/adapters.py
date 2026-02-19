from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        email = (user.email or "").strip().lower()
        if email and not user.username:
            user.username = email
        if commit:
            user.save()
        return user
