# applications/utils.py
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

def render_to_pdf(template_src, context_dict={}):
    """
    Renderiza un template Django a PDF usando xhtml2pdf
    """
    try:
        template = get_template(template_src)
        html = template.render(context_dict)
        result = BytesIO()

        pdf = pisa.pisaDocument(
            BytesIO(html.encode("utf-8")),
            dest=result,
            encoding='utf-8'
        )

        if not pdf.err:
            return HttpResponse(result.getvalue(), content_type='application/pdf')
        else:
            # Para depuración
            print("Errores de PDF:", pdf.err)
            return HttpResponse('Error al generar PDF', status=500)

    except Exception as e:
        print("Excepción en render_to_pdf:", str(e))
        return HttpResponse('Error interno', status=500)