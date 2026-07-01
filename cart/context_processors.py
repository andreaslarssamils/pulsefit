from .cart import Cart


def cart_item_count(request):
    return {"cart_count": Cart(request).count()}
