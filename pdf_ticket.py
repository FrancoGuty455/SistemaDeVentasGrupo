import os
from datetime import datetime
from typing import Optional
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
try:
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderPDF
    _QR_AVAILABLE = True
except Exception:
    _QR_AVAILABLE = False
from config import get_connection

def _fetch_empresa():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT TOP 1 Nombre, CUIT, CondicionIVA, Direccion, Telefono, Email, LogoPath
            FROM dbo.Empresa ORDER BY EmpresaID
        """)
        row = cur.fetchone()
        if not row:
            return {"Nombre": "Empresa", "CUIT": None, "CondicionIVA": None,
                    "Direccion": None, "Telefono": None, "Email": None, "LogoPath": None}
        cols = [c[0] for c in cur.description]
        return dict(zip(cols, row))
    finally:
        conn.close()

def _fetch_venta(venta_id: int):
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT v.VentaID, v.Fecha, v.Total, c.Nombre AS ClienteNombre
            FROM dbo.Ventas v
            LEFT JOIN dbo.Clientes c ON c.ClienteID = v.ClienteID
            WHERE v.VentaID = ?
        """, (venta_id,))
        cab = cur.fetchone()
        if not cab:
            raise ValueError(f"Venta {venta_id} no existe")

        cur.execute("""
            SELECT d.ProductoID, p.Nombre, d.Cantidad, d.PrecioUnitario
            FROM dbo.VentaDetalle d
            JOIN dbo.Productos p ON p.ProductoID = d.ProductoID
            WHERE d.VentaID = ?
            ORDER BY d.DetalleID
        """, (venta_id,))
        det = cur.fetchall()
        return cab, det
    finally:
        conn.close()

def _fmt_currency(value: float) -> str:
    s = f"{value:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s

def _wrap_text(txt: str, max_width_mm: float, font_name: str, font_size: float) -> list[str]:
    if not txt:
        return [""]
    max_width = max_width_mm * mm
    words = txt.split()
    lines = []
    cur = ""
    for w in words:
        test = f"{cur} {w}".strip()
        if stringWidth(test, font_name, font_size) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def _draw_header(
    c: canvas.Canvas, x0: float, y0: float, w: float, h: float,
    venta_id: int, fecha: datetime | str, cliente: Optional[str],
    empresa: dict,
    mostrar_qr: bool = True
) -> float:

    c.setFillColor(colors.HexColor("#111827"))
    c.setStrokeColor(colors.HexColor("#111827"))
    c.rect(x0, y0 - h, w, h, fill=1, stroke=0)

    P = 6 * mm


    logo_h = max(14 * mm, h - 2 * P)
    logo_w = min(24 * mm, logo_h * 1.2)
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.white)

    logo_path = (empresa.get("LogoPath") or "").strip()
    if logo_path and os.path.isfile(logo_path):
        try:
            c.drawImage(logo_path, x0 + P, y0 - P - logo_h,
                        width=logo_w, height=logo_h,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            c.roundRect(x0 + P, y0 - P - logo_h, logo_w, logo_h, 2*mm, fill=0, stroke=1)
            c.setFont("Helvetica-Bold", 10)
            c.drawCentredString(x0 + P + logo_w/2, y0 - P - logo_h/2, "LOGO")
    else:
        c.roundRect(x0 + P, y0 - P - logo_h, logo_w, logo_h, 2*mm, fill=0, stroke=1)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(x0 + P + logo_w/2, y0 - P - logo_h/2, "LOGO")


    qr_size = 0
    if _QR_AVAILABLE and mostrar_qr:
        qr_size = min(22 * mm, h - 2 * P)
        qr_x = x0 + w - P - qr_size
        qr_y = y0 - P - qr_size
        try:
            qr = QrCodeWidget(f"venta:{venta_id}")
            d = Drawing(qr_size, qr_size)
            d.add(qr)
            renderPDF.draw(d, c, qr_x, qr_y)
        except Exception:
            qr_size = 0


    text_left = x0 + P + logo_w + 6 * mm
    text_right = x0 + w - P - (qr_size + 6 * mm if qr_size else 0)


    if isinstance(fecha, str):
        fecha_txt = fecha
    else:
        try:
            fecha_txt = fecha.strftime("%d/%m/%Y %H:%M")
        except Exception:
            fecha_txt = str(fecha)


    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(text_left, y0 - P - 6 * mm, empresa.get("Nombre") or "SISTEMA DE VENTAS")

    c.setFont("Helvetica", 9)

    info1 = []
    if empresa.get("CUIT"): info1.append(f"CUIT: {empresa['CUIT']}")
    if empresa.get("CondicionIVA"): info1.append(f"IVA: {empresa['CondicionIVA']}")
    if info1:
        c.drawString(text_left, y0 - P - 11.5 * mm, " • ".join(info1))


    info2 = []
    if empresa.get("Direccion"): info2.append(empresa["Direccion"])
    if empresa.get("Telefono"):  info2.append(f"Tel: {empresa['Telefono']}")
    if empresa.get("Email"):     info2.append(empresa["Email"])
    if info2:
        c.drawString(text_left, y0 - P - 16.5 * mm, " • ".join(info2))


    c.drawString(text_left, y0 - P - 22 * mm, f"Ticket / Venta: {venta_id}")
    c.drawString(text_left, y0 - P - 26.5 * mm, f"Fecha: {fecha_txt}")
    c.drawString(text_left, y0 - P - 31 * mm, f"Cliente: {cliente or '-'}")


    return y0 - h - 6 * mm



def _draw_table_header(c: canvas.Canvas, x: float, y: float, widths_mm: dict) -> float:
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.black)
    c.setStrokeColor(colors.HexColor("#9CA3AF"))  
    c.setLineWidth(0.3)
    c.line(x, y - 2*mm, x + sum(widths_mm.values())*mm, y - 2*mm)

    c.drawString(x, y, "Producto")
    c.drawRightString(x + (widths_mm["nombre"] + widths_mm["cant"])*mm, y, "Cant.")
    c.drawRightString(x + (widths_mm["nombre"] + widths_mm["cant"] + widths_mm["punit"])*mm, y, "P.Unit")
    c.drawRightString(x + sum(widths_mm.values())*mm, y, "Importe")
    return y - 6*mm


def _check_page_break(c: canvas.Canvas, y: float, bottom: float, top_after_break: float,
                      draw_header_cb) -> float:
    if y < bottom:
        c.showPage()
        y = top_after_break
        y = draw_header_cb(y)
    return y


def _draw_footer(c: canvas.Canvas, page_w: float, margin_x: float, margin_bottom: float):

    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawString(margin_x, margin_bottom - 6*mm, "Gracias por su compra.")

    try:
        page_num = c.getPageNumber()
        c.drawRightString(page_w - margin_x, margin_bottom - 6*mm, f"Página {page_num}")
    except Exception:
        pass

def _draw_qr_bottom_right(
    c: canvas.Canvas,
    venta_id: int,
    page_w: float,
    margin_x: float,
    margin_bottom: float,
    size_mm: float = 16.0,      
):
    if not _QR_AVAILABLE:
        return
    try:
        qr_size = size_mm * mm
        qr_x = page_w - margin_x - qr_size
        qr_y = margin_bottom + 2 * mm  
        qr_data = f"venta:{venta_id}"
        qr = QrCodeWidget(qr_data)
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics import renderPDF
        d = Drawing(qr_size, qr_size)
        d.add(qr)
        renderPDF.draw(d, c, qr_x, qr_y)
    except Exception:
        pass



def generar_ticket_pdf(venta_id: int, ruta: str | None = None, abrir: bool = True) -> str:
    cab, det = _fetch_venta(venta_id)

    if ruta is None:
        ruta = os.path.abspath(f"ticket_{venta_id}.pdf")


    c = canvas.Canvas(ruta, pagesize=A4)
    W, H = A4


    MARGIN_X = 18 * mm
    MARGIN_TOP = H - 18 * mm
    MARGIN_BOTTOM = 20 * mm

    header_h = 32 * mm 
    empresa = _fetch_empresa()


    y = _draw_header(
        c,
        x0=MARGIN_X,
        y0=MARGIN_TOP,
        w=W - 2*MARGIN_X,
        h=header_h,
        venta_id=cab[0],
        fecha=cab[1],
        cliente=cab[3],
        empresa=empresa,
        mostrar_qr=False, 
    )

    widths_mm = {
        "nombre": 95.0,
        "cant":   22.0,
        "punit":  28.0,
        "imp":    32.0,
    }


    def redraw_table_header(on_y: float) -> float:
        return _draw_table_header(c, MARGIN_X, on_y, widths_mm)


    y = _draw_table_header(c, MARGIN_X, y, widths_mm)


    body_font = "Helvetica"
    body_size = 9
    line_h = 6 * mm

    total_calc = 0.0
    alt_fill = colors.HexColor("#F3F4F6") 
    row_idx = 0

    for _, nombre, cantidad, punit in det:
        cantidad = float(cantidad)
        punit = float(punit)
        importe = cantidad * punit
        total_calc += importe


        name_lines = _wrap_text(nombre or "", widths_mm["nombre"], body_font, body_size)
        row_height = line_h * max(1, len(name_lines))


        y = _check_page_break(
            c, y - row_height + line_h, MARGIN_BOTTOM + 30, MARGIN_TOP - header_h - 4*mm, redraw_table_header
        )


        if row_idx % 2 == 1:
            c.setFillColor(alt_fill)
            c.setStrokeColor(alt_fill)
            c.rect(MARGIN_X, y - row_height + 1.5*mm, sum(widths_mm.values())*mm, row_height, fill=1, stroke=0)
        row_idx += 1

        c.setFillColor(colors.black)
        c.setFont(body_font, body_size)

        y_text = y
        for ln in name_lines:
            c.drawString(MARGIN_X, y_text, ln)
            y_text -= line_h


        c.setFont("Helvetica", body_size)
        c.drawRightString(MARGIN_X + (widths_mm["nombre"] + widths_mm["cant"])*mm, y, f"{cantidad:,.3f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c.drawRightString(MARGIN_X + (widths_mm["nombre"] + widths_mm["cant"] + widths_mm["punit"])*mm, y, _fmt_currency(punit))
        c.drawRightString(MARGIN_X + sum(widths_mm.values())*mm, y, _fmt_currency(importe))


        y -= row_height


    c.setStrokeColor(colors.HexColor("#9CA3AF"))
    c.setLineWidth(0.3)
    c.line(MARGIN_X, y - 2*mm, MARGIN_X + sum(widths_mm.values())*mm, y - 2*mm)
    y -= 8 * mm

    c.setFont("Helvetica", 9)
    label_x = MARGIN_X + (widths_mm["nombre"] + widths_mm["cant"] + widths_mm["punit"])*mm
    value_x = MARGIN_X + sum(widths_mm.values())*mm

    c.drawRightString(label_x, y, "Total:")
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#111827"))
    c.drawRightString(value_x, y, f"$ {_fmt_currency(float(cab[2] or 0.0))}")
    y -= 8 * mm


    if abs(total_calc - float(cab[2] or 0.0)) > 0.01:
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#B45309"))
        c.drawRightString(value_x, y, f"(Recalculado: $ {_fmt_currency(total_calc)})")
        y -= 6 * mm


    y -= 2 * mm
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawString(MARGIN_X, y, "Cambio y devoluciones dentro de 48h con ticket. Muchas gracias.")
    y -= 10 * mm

    _draw_qr_bottom_right(
        c, venta_id=cab[0], page_w=W,
        margin_x=MARGIN_X, margin_bottom=MARGIN_BOTTOM,
        size_mm=16.0
    )


    _draw_footer(c, W, MARGIN_X, MARGIN_BOTTOM)

    c.save()

    if abrir:
        try:
            os.startfile(ruta)
        except Exception:
            pass

    return ruta
