# ventas/forms.py
from django import forms
from .models import Sale, Cliente


class VentaForm(forms.Form):
    barcode = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Código de barras',
                'class': 'input-group-field',
                'autofocus': 'autofocus',
            }
        )
    )
    count = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                'value': '1',
                'class': 'input-group-field',
            }
        )
    )

    def clean_count(self):
        count = self.cleaned_data['count']
        if count < 1:
            raise forms.ValidationError('Ingrese una cantidad mayor a cero')
        return count


# ventas/forms.py
class VentaVoucherForm(forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all().order_by('nombre'),
        required=True,  # <-- Obligatorio
        empty_label="Selecciona un cliente *",  # <-- No None, pero con mensaje claro
        widget=forms.Select(attrs={
            'class': 'input-group-field',
            'style': 'width: 100%;',
            'id': 'id_cliente',
        })
    )

    type_payment = forms.ChoiceField(
        required=True,
        choices=Sale.TIPO_PAYMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'input-group-field'})
    )
    type_invoce = forms.ChoiceField(
        required=True,
        choices=Sale.TIPO_INVOCE_CHOICES,
        widget=forms.Select(attrs={'class': 'input-group-field'})
    )