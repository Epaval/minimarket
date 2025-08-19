# django
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    View,
    UpdateView,
    DeleteView,
    DeleteView,
    ListView
)
from django.views.generic.edit import (
    FormView
)
# local
from applications.producto.models import Product
from applications.utils import render_to_pdf
from applications.users.mixins import VentasPermisoMixin
#
from .models import Sale, SaleDetail, CarShop, Cliente
from .forms import VentaForm, VentaVoucherForm
from .functions import procesar_venta

import qrcode
from io import BytesIO
import base64

# ventas/views.py
class AddCarView(VentasPermisoMixin, FormView):
    template_name = 'venta/index.html'
    form_class = VentaForm
    success_url = '.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["productos"] = CarShop.objects.all()
        context["total_cobrar"] = CarShop.objects.total_cobrar()
        context['form_voucher'] = VentaVoucherForm()
        context['clientes_activos'] = Cliente.objects.all().order_by('nombre')  # <= Añade esta línea
        return context

    def form_valid(self, form):
        barcode = form.cleaned_data['barcode']
        count = form.cleaned_data['count']
        try:
            producto = Product.objects.get(barcode=barcode)
            obj, created = CarShop.objects.get_or_create(
                barcode=barcode,
                defaults={
                    'product': producto,
                    'count': count
                }
            )
            if not created:
                obj.count += count
                obj.save()
        except Product.DoesNotExist:
            messages.error(self.request, 'Producto no encontrado.')
        
        return super().form_valid(form)
    


class CarShopUpdateView(VentasPermisoMixin, View):
    """ quita en 1 la cantidad en un carshop """

    def post(self, request, *args, **kwargs):
        car = CarShop.objects.get(id=self.kwargs['pk'])
        if car.count > 1:
            car.count = car.count - 1
            car.save()
        #
        return HttpResponseRedirect(
            reverse(
                'venta_app:venta-index'
            )
        )


class CarShopDeleteView(VentasPermisoMixin, DeleteView):
    model = CarShop
    success_url = reverse_lazy('venta_app:venta-index')


class CarShopDeleteAll(VentasPermisoMixin, View):
    
    def post(self, request, *args, **kwargs):
        #
        CarShop.objects.all().delete()
        #
        return HttpResponseRedirect(
            reverse(
                'venta_app:venta-index'
            )
        )


class ProcesoVentaSimpleView(VentasPermisoMixin, View):
    """ Procesa una venta simple """

    def post(self, request, *args, **kwargs):
        #
        procesar_venta(
            self=self,
            type_invoce=Sale.SIN_COMPROBANTE,
            type_payment=Sale.CASH,
            user=self.request.user,
        )
        #
        return HttpResponseRedirect(
            reverse(
                'venta_app:venta-index'
            )
        )


class ProcesoVentaVoucherView(VentasPermisoMixin, FormView):
    form_class = VentaVoucherForm
    success_url = '.'

    def form_valid(self, form):
        type_payment = form.cleaned_data['type_payment']
        type_invoce = form.cleaned_data['type_invoce']
        cliente = form.cleaned_data.get('cliente')  # Puede ser None

        # Procesamos la venta con cliente
        venta = procesar_venta(
            self=self,
            type_invoce=type_invoce,
            type_payment=type_payment,
            user=self.request.user,
            cliente=cliente  # <-- Pasamos el cliente
        )

        if venta:
            messages.success(self.request, f'Venta realizada con éxito. N°: {venta.id}')
            return HttpResponseRedirect(
                reverse('venta_app:venta-voucher_pdf', kwargs={'pk': venta.pk})
            )
        else:
            messages.error(self.request, 'No se pudo procesar la venta. El carrito está vacío.')
            return HttpResponseRedirect(reverse('venta_app:venta-index'))
                


class VentaVoucherPdf(View):
    def get(self, request, *args, **kwargs):
        venta = get_object_or_404(Sale, id=self.kwargs['pk'])
        detalle_productos = venta.detail_sale.all()

        # Determinar formato
        formato = request.GET.get('format', 'profesional')  # /venta/voucher-pdf/1/?format=thermal

        if formato == 'thermal':
            template_name = 'venta/voucher_thermal.html'
            filename = f"comprobante_{venta.id}_thermal.pdf"
        else:
            template_name = 'venta/voucher_profesional.html'
            filename = f"comprobante_{venta.id}.pdf"

        data = {
            'venta': venta,
            'detalle_productos': detalle_productos,
            'logo_url': request.build_absolute_uri('/static/img/logo.png'),
            # Solo agregar QR en versión profesional
            'qr_base64': self.generate_qr(venta) if formato != 'thermal' else None,
        }

        pdf = render_to_pdf(template_name, data)
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        return HttpResponse("Error al generar PDF", status=500)

    def generate_qr(self, venta):
        import qrcode
        from io import BytesIO
        import base64

        qr_data = f"https://marketdj.com/venta/{venta.id}"
        qr_img = qrcode.make(qr_data, box_size=6)
        buffer = BytesIO()
        qr_img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()


class SaleListView(VentasPermisoMixin, ListView):
    template_name = 'venta/ventas.html'
    context_object_name = "ventas" 

    def get_queryset(self):
        return Sale.objects.ventas_no_cerradas()



class SaleDeleteView(VentasPermisoMixin, DeleteView):
    template_name = "venta/delete.html"
    model = Sale
    success_url = reverse_lazy('venta_app:venta-index')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.anulate = True
        self.object.save()
        # actualizmos sl stok y ventas
        SaleDetail.objects.restablecer_stok_num_ventas(self.object.id)
        success_url = self.get_success_url()

        return HttpResponseRedirect(success_url)
    
    
def cliente_add(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        apellido = request.POST.get("apellido", "").strip()
        dni = request.POST.get("dni", "").strip()
        telefono = request.POST.get("telefono", "").strip()
        email = request.POST.get("email", "").strip()

        # Validación básica
        if not nombre:
            messages.error(request, "El nombre es obligatorio.")
            return redirect('venta_app:venta-index')

        # Evitar DNI duplicado (si se ingresa)
        if dni and Cliente.objects.filter(dni=dni).exists():
            messages.error(request, f"Ya existe un cliente con CI/RIF {dni}.")
            return redirect('venta_app:venta-index')

        # Crear cliente
        cliente = Cliente.objects.create(
            nombre=nombre,
            apellido=apellido,
            dni=dni,
            telefono=telefono,
            email=email,
        )

        messages.success(request, f"Cliente {cliente} registrado con éxito.")
        return redirect('venta_app:venta-index')
    

    

