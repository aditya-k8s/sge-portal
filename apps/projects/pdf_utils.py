"""
PDF generation for Shri Gouri Engineers.
- Professional GST Invoice
- Project Timeline / History export
"""
import io
from decimal import Decimal
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfgen import canvas as rl_canvas

# ── Brand colours ──────────────────────────────────────────────────────────
ORANGE   = colors.HexColor('#E85D04')
DARK     = colors.HexColor('#1A1E2E')
STEEL    = colors.HexColor('#4B5563')
LIGHT_BG = colors.HexColor('#F9FAFB')
BORDER   = colors.HexColor('#E5E7EB')
GREEN    = colors.HexColor('#16A34A')
W        = A4[0]
H        = A4[1]


def _base_style(**kw):
    defaults = dict(fontName='Helvetica', fontSize=9, textColor=STEEL,
                    leading=14, spaceAfter=0)
    defaults.update(kw)
    return ParagraphStyle('s', **defaults)


# ── INVOICE PDF ────────────────────────────────────────────────────────────

def generate_invoice_pdf(bill, company_settings=None):
    """
    Returns bytes of a professional GST invoice PDF.
    bill: ProjectBill instance
    """
    buf = io.BytesIO()
    project = bill.project
    client  = project.client

    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=20*mm)

    story = []
    W_pt = A4[0] - 30*mm   # usable width

    # ── Header ──────────────────────────────────────────────────────────
    header_data = [[
        Paragraph('<b><font size="18" color="#E85D04">SHRI GOURI</font></b><br/>'
                  '<font size="9" color="#6B7280">ENGINEERS</font><br/><br/>'
                  '<font size="8" color="#6B7280">Precision CNC / VMC Manufacturing</font>',
                  _base_style()),
        Paragraph('<b><font size="20" color="#1A1E2E">TAX INVOICE</font></b><br/><br/>'
                  f'<font size="9" color="#6B7280">Invoice No: </font>'
                  f'<b>{bill.invoice_number or f"INV-{bill.pk:04d}"}</b><br/>'
                  f'<font size="9" color="#6B7280">Date: </font>'
                  f'<b>{bill.uploaded_at.strftime("%d %b %Y")}</b>',
                  _base_style(alignment=TA_RIGHT)),
    ]]
    ht = Table(header_data, colWidths=[W_pt*0.55, W_pt*0.45])
    ht.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(ht)
    story.append(HRFlowable(width='100%', thickness=2, color=ORANGE, spaceAfter=12))

    # ── Billed To / From ────────────────────────────────────────────────
    co_addr = (company_settings or {})
    from_text = (
        '<b>From:</b><br/>'
        '<b>Shri Gouri Engineers</b><br/>'
        + (co_addr.get('address', '') + '<br/>' if co_addr.get('address') else '')
        + (f'GST: <b>{co_addr.get("gstin", "")}</b><br/>' if co_addr.get('gstin') else '')
        + (f'Phone: {co_addr.get("phone", "")}<br/>' if co_addr.get('phone') else '')
        + (f'Email: {co_addr.get("email", "")}<br/>' if co_addr.get('email') else '')
    )
    to_text = (
        '<b>Bill To:</b><br/>'
        f'<b>{client.get_full_name() or client.username}</b><br/>'
        + (f'{client.company_name}<br/>' if client.company_name else '')
        + (f'{client.address}<br/>' if client.address else '')
        + (f'Email: {client.email}<br/>' if client.email else '')
        + (f'Phone: {client.phone}<br/>' if client.phone else '')
    )
    addr_data = [[
        Paragraph(from_text, _base_style(leading=16)),
        Paragraph(to_text,   _base_style(leading=16)),
    ]]
    at = Table(addr_data, colWidths=[W_pt*0.5, W_pt*0.5])
    at.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (0,0), LIGHT_BG),
        ('BACKGROUND', (1,0), (1,0), colors.white),
        ('BOX', (0,0), (0,0), 0.5, BORDER),
        ('BOX', (1,0), (1,0), 0.5, BORDER),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(at)
    story.append(Spacer(1, 12))

    # ── Project Info ────────────────────────────────────────────────────
    proj_data = [
        [Paragraph('<b>Project Details</b>', _base_style(fontSize=10, textColor=DARK)), ''],
        ['Project Name', project.project_name],
        ['Project Code', project.project_code],
        ['Client',       client.get_full_name() or client.username],
        ['Status',       project.get_status_display()],
    ]
    if project.start_date:
        proj_data.append(['Start Date', project.start_date.strftime('%d %b %Y')])
    if project.expected_delivery:
        proj_data.append(['Expected Delivery', project.expected_delivery.strftime('%d %b %Y')])

    pt = Table(proj_data, colWidths=[W_pt*0.3, W_pt*0.7])
    pt.setStyle(TableStyle([
        ('SPAN', (0,0), (1,0)),
        ('BACKGROUND', (0,0), (1,0), DARK),
        ('TEXTCOLOR', (0,0), (1,0), colors.white),
        ('BACKGROUND', (0,1), (0,-1), LIGHT_BG),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('FONTNAME', (0,1), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('PADDING', (0,0), (-1,-1), 6),
        ('TEXTCOLOR', (0,1), (-1,-1), STEEL),
    ]))
    story.append(pt)
    story.append(Spacer(1, 12))

    # ── Line Items ──────────────────────────────────────────────────────
    desc = bill.description_of_work or f'Manufacturing services — {project.project_name}'
    amount  = bill.amount or Decimal('0')
    gst_pct = bill.gst_rate
    gst_amt = amount * gst_pct / 100
    total   = amount + gst_amt
    cgst    = gst_amt / 2
    sgst    = gst_amt / 2

    items_header = [
        Paragraph('<b>#</b>',            _base_style(alignment=TA_CENTER, textColor=colors.white)),
        Paragraph('<b>Description</b>',  _base_style(textColor=colors.white)),
        Paragraph('<b>HSN/SAC</b>',       _base_style(alignment=TA_CENTER, textColor=colors.white)),
        Paragraph('<b>Amount (Rs.)</b>', _base_style(alignment=TA_RIGHT, textColor=colors.white)),
    ]
    items_row = [
        Paragraph('1', _base_style(alignment=TA_CENTER)),
        Paragraph(desc, _base_style()),
        Paragraph(bill.hsn_code or '—', _base_style(alignment=TA_CENTER)),
        Paragraph(f'{float(amount):,.2f}', _base_style(alignment=TA_RIGHT)),
    ]

    # Tax breakdown
    tax_rows = []
    if gst_pct > 0:
        tax_rows = [
            ['', '', Paragraph('Subtotal', _base_style(alignment=TA_RIGHT)),
             Paragraph(f'{float(amount):,.2f}', _base_style(alignment=TA_RIGHT))],
            ['', '', Paragraph(f'CGST @ {gst_pct//2}%', _base_style(alignment=TA_RIGHT)),
             Paragraph(f'{float(cgst):,.2f}', _base_style(alignment=TA_RIGHT))],
            ['', '', Paragraph(f'SGST @ {gst_pct//2}%', _base_style(alignment=TA_RIGHT)),
             Paragraph(f'{float(sgst):,.2f}', _base_style(alignment=TA_RIGHT))],
        ]

    total_row = [
        '', '',
        Paragraph('<b>TOTAL</b>', _base_style(alignment=TA_RIGHT, fontSize=11, textColor=DARK)),
        Paragraph(f'<b>Rs. {float(total):,.2f}</b>', _base_style(alignment=TA_RIGHT, fontSize=11, textColor=ORANGE)),
    ]

    table_data = [items_header, items_row] + tax_rows + [total_row]
    cw = [W_pt*0.07, W_pt*0.5, W_pt*0.15, W_pt*0.28]
    it = Table(table_data, colWidths=cw)
    style = [
        ('BACKGROUND', (0,0), (-1,0), DARK),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, LIGHT_BG]),
        ('PADDING', (0,0), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FFF7ED')),
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, ORANGE),
    ]
    it.setStyle(TableStyle(style))
    story.append(it)
    story.append(Spacer(1, 16))

    # ── Amount in Words ─────────────────────────────────────────────────
    story.append(Paragraph(
        f'<b>Amount in Words:</b> <i>Rupees {_amount_to_words(total)} Only</i>',
        _base_style(fontSize=9)
    ))
    story.append(Spacer(1, 12))

    # ── Notes ────────────────────────────────────────────────────────────
    if bill.notes:
        story.append(Paragraph(f'<b>Notes:</b> {bill.notes}', _base_style()))
        story.append(Spacer(1, 8))

    # ── Footer ───────────────────────────────────────────────────────────
    story.append(HRFlowable(width='100%', thickness=1, color=BORDER, spaceBefore=8, spaceAfter=8))
    footer_data = [[
        Paragraph('<font size="8" color="#9CA3AF">This is a computer generated invoice.</font>',
                  _base_style(fontSize=8)),
        Paragraph('<b>For Shri Gouri Engineers</b><br/><br/>'
                  '___________________________<br/>'
                  '<font size="8" color="#9CA3AF">Authorised Signatory</font>',
                  _base_style(alignment=TA_RIGHT, fontSize=9)),
    ]]
    ft = Table(footer_data, colWidths=[W_pt*0.6, W_pt*0.4])
    ft.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'BOTTOM')]))
    story.append(ft)

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ── TIMELINE PDF ──────────────────────────────────────────────────────────

def generate_timeline_pdf(project):
    """Returns bytes of a project timeline/history PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=20*mm)

    story = []
    W_pt = A4[0] - 30*mm

    # Header
    story.append(Paragraph(
        f'<font color="#E85D04"><b>SHRI GOURI ENGINEERS</b></font>',
        _base_style(fontSize=16)
    ))
    story.append(Paragraph('Project Timeline Report', _base_style(fontSize=11, textColor=DARK)))
    story.append(HRFlowable(width='100%', thickness=2, color=ORANGE, spaceBefore=6, spaceAfter=10))

    # Project summary
    client = project.client
    summary = [
        ['Project Name', project.project_name,   'Project Code', project.project_code],
        ['Client',       client.get_full_name() or client.username,
         'Company',      client.company_name or '—'],
        ['Status',       project.get_status_display(),
         'Progress',     f'{project.progress_percentage}%'],
        ['Start Date',   project.start_date.strftime('%d %b %Y') if project.start_date else '—',
         'Delivery',     project.expected_delivery.strftime('%d %b %Y') if project.expected_delivery else '—'],
    ]
    if project.material:
        summary.append(['Material', project.material, 'Quantity', str(project.quantity or '—')])
    if project.machine:
        summary.append(['Machine', project.machine.machine_name, '', ''])

    st = Table(summary, colWidths=[W_pt*0.2, W_pt*0.3, W_pt*0.2, W_pt*0.3])
    st.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), LIGHT_BG),
        ('BACKGROUND', (2,0), (2,-1), LIGHT_BG),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('PADDING', (0,0), (-1,-1), 6),
        ('TEXTCOLOR', (0,0), (-1,-1), STEEL),
    ]))
    story.append(st)
    story.append(Spacer(1, 14))

    # Process stages
    story.append(Paragraph('<b>Manufacturing Process</b>',
                            _base_style(fontSize=11, textColor=DARK)))
    story.append(Spacer(1, 6))

    STATUS_COLOR = {
        'completed':   GREEN,
        'in_progress': ORANGE,
        'pending':     STEEL,
        'skipped':     colors.HexColor('#9CA3AF'),
    }
    STATUS_LABEL = {
        'completed': 'COMPLETED', 'in_progress': 'IN PROGRESS',
        'pending': 'PENDING', 'skipped': 'SKIPPED',
    }

    proc_header = [
        Paragraph('<b>#</b>', _base_style(textColor=colors.white, alignment=TA_CENTER)),
        Paragraph('<b>Stage</b>', _base_style(textColor=colors.white)),
        Paragraph('<b>Status</b>', _base_style(textColor=colors.white, alignment=TA_CENTER)),
        Paragraph('<b>Completed At</b>', _base_style(textColor=colors.white, alignment=TA_CENTER)),
    ]
    proc_rows = [proc_header]
    for i, p in enumerate(project.processes.order_by('order'), 1):
        sc = STATUS_COLOR.get(p.status, STEEL)
        sl = STATUS_LABEL.get(p.status, p.status)
        completed_str = p.completed_at.strftime('%d %b %Y %H:%M') if p.completed_at else '—'
        proc_rows.append([
            Paragraph(str(i), _base_style(alignment=TA_CENTER)),
            Paragraph(p.process_name, _base_style()),
            Paragraph(f'<b><font color="{sc.hexval()}">{sl}</font></b>',
                      _base_style(alignment=TA_CENTER)),
            Paragraph(completed_str, _base_style(alignment=TA_CENTER)),
        ])

    pt = Table(proc_rows, colWidths=[W_pt*0.07, W_pt*0.38, W_pt*0.25, W_pt*0.30])
    pt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), DARK),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT_BG]),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(pt)
    story.append(Spacer(1, 14))

    # Activity log
    activities = project.activities.order_by('-created_at')[:30]
    if activities:
        story.append(Paragraph('<b>Activity Log</b>', _base_style(fontSize=11, textColor=DARK)))
        story.append(Spacer(1, 6))
        act_header = [
            Paragraph('<b>Date & Time</b>', _base_style(textColor=colors.white)),
            Paragraph('<b>Activity</b>',    _base_style(textColor=colors.white)),
            Paragraph('<b>By</b>',          _base_style(textColor=colors.white)),
        ]
        act_rows = [act_header]
        for a in activities:
            act_rows.append([
                Paragraph(a.created_at.strftime('%d %b %Y %H:%M'), _base_style()),
                Paragraph(a.action, _base_style()),
                Paragraph(a.actor.get_full_name() or a.actor.username if a.actor else '—', _base_style()),
            ])
        at = Table(act_rows, colWidths=[W_pt*0.25, W_pt*0.5, W_pt*0.25])
        at.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), DARK),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT_BG]),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(at)
        story.append(Spacer(1, 10))

    # Bills
    bills = project.bills.all()
    if bills:
        story.append(Paragraph('<b>Bills & Invoices</b>', _base_style(fontSize=11, textColor=DARK)))
        story.append(Spacer(1, 6))
        bill_rows = [[
            Paragraph('<b>Invoice No</b>', _base_style(textColor=colors.white)),
            Paragraph('<b>Date</b>', _base_style(textColor=colors.white)),
            Paragraph('<b>Amount</b>', _base_style(textColor=colors.white, alignment=TA_RIGHT)),
            Paragraph('<b>GST</b>', _base_style(textColor=colors.white, alignment=TA_RIGHT)),
            Paragraph('<b>Total</b>', _base_style(textColor=colors.white, alignment=TA_RIGHT)),
        ]]
        for b in bills:
            bill_rows.append([
                Paragraph(b.invoice_number or f'INV-{b.pk:04d}', _base_style()),
                Paragraph(b.uploaded_at.strftime('%d %b %Y'), _base_style()),
                Paragraph(f'Rs. {float(b.amount or 0):,.2f}', _base_style(alignment=TA_RIGHT)),
                Paragraph(f'{b.gst_rate}%', _base_style(alignment=TA_RIGHT)),
                Paragraph(f'Rs. {float(b.total_amount or 0):,.2f}',
                          _base_style(alignment=TA_RIGHT, textColor=ORANGE)),
            ])
        bt = Table(bill_rows, colWidths=[W_pt*0.2, W_pt*0.2, W_pt*0.2, W_pt*0.15, W_pt*0.25])
        bt.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), DARK),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT_BG]),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(bt)

    # Footer
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width='100%', thickness=1, color=BORDER))
    story.append(Paragraph(
        f'<font size="8" color="#9CA3AF">Generated by Shri Gouri Engineers Project Portal · '
        f'{project.project_code} · Confidential</font>',
        _base_style(fontSize=8, alignment=TA_CENTER)
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ── Helpers ────────────────────────────────────────────────────────────────

def _amount_to_words(amount):
    """Convert decimal amount to words (simplified)."""
    try:
        n = int(amount)
        ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
                'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen',
                'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
        tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty',
                'Sixty', 'Seventy', 'Eighty', 'Ninety']
        def words(n):
            if n == 0: return ''
            if n < 20: return ones[n]
            if n < 100: return tens[n//10] + (' ' + ones[n%10] if n%10 else '')
            if n < 1000: return ones[n//100] + ' Hundred' + (' and ' + words(n%100) if n%100 else '')
            if n < 100000: return words(n//1000) + ' Thousand' + (' ' + words(n%1000) if n%1000 else '')
            if n < 10000000: return words(n//100000) + ' Lakh' + (' ' + words(n%100000) if n%100000 else '')
            return words(n//10000000) + ' Crore' + (' ' + words(n%10000000) if n%10000000 else '')
        return words(n) or 'Zero'
    except Exception:
        return str(amount)
