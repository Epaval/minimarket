# venta/functions.py
from django.utils import timezone
from .models import Sale, SaleDetail, CarShop
from applications.producto.models import Product

def procesar_venta(self, type_invoce, type_payment, user, cliente=None):  # <-- Nuevo parámetro
    """
    Función que procesa una venta a partir del carrito
    """
    carrito = CarShop.objects.all()

    if carrito.exists():
        # Calculamos valores
        total_amount = sum(item.count * item.product.sale_price for item in carrito)
        total_count = sum(item.count for item in carrito)

        # Creamos la venta
        venta = Sale.objects.create(
            date_sale=timezone.now(),
            count=total_count,
            amount=total_amount,
            type_invoce=type_invoce,
            type_payment=type_payment,
            user=user,
            cliente=cliente,  # <-- Asignamos el cliente
            close=True,
        )

        # Creamos los detalles y actualizamos stock (la señal ya lo hace)
        for item in carrito:
            SaleDetail.objects.create(
                sale=venta,
                product=item.product,
                count=item.count,
                price_purchase=item.product.purchase_price,
                price_sale=item.product.sale_price,
                tax=0,  # Puedes ajustar si usas impuestos
            )

        # Limpiamos el carrito
        carrito.delete()

        return venta  # Retornamos la venta para usar en redirección

    return None