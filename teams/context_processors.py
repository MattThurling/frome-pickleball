from django.conf import settings

from .models import Wallet


def wallet_balance(request):
    team_name = getattr(settings, "TEAM_NAME", "Team")
    if not request.user.is_authenticated:
        return {"team_name": team_name}
    wallet = Wallet.objects.filter(user=request.user).first()
    return {
        "wallet_balance": wallet.balance if wallet else 0,
        "team_name": team_name,
    }
