from .models import Wallet


def wallet_balance(request):
    if not request.user.is_authenticated:
        return {}
    wallet = Wallet.objects.filter(user=request.user).first()
    return {"wallet_balance": wallet.balance if wallet else 0}
