"""
Utilitaires pour la génération de PDF avec ReportLab
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from datetime import datetime
import os
from django.conf import settings


class PDFReportBase:
    """Classe de base pour tous les rapports PDF"""
    
    def __init__(self, filename="rapport.pdf"):
        self.filename = filename
        self.pagesize = A4
        self.width, self.height = self.pagesize
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Définir les styles personnalisés"""
        # Titre principal
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#312e81'),  # Indigo foncé
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Sous-titre
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#4f46e5'),  # Indigo
            spaceAfter=10,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        ))
        
        # Section
        self.styles.add(ParagraphStyle(
            name='CustomSection',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#1e40af'),  # Bleu
            spaceAfter=6,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        ))
        
        # Info label
        self.styles.add(ParagraphStyle(
            name='InfoLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#6b7280'),  # Gris
            fontName='Helvetica-Bold'
        ))
        
        # Info value
        self.styles.add(ParagraphStyle(
            name='InfoValue',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#111827'),  # Noir
        ))
    
    def add_header(self, elements, title, subtitle=None):
        """Ajouter l'en-tête avec logo"""
        # Logo (si existe)
        logo_path = os.path.join(settings.STATIC_ROOT or settings.BASE_DIR / 'static', 'images', 'logo.png')
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=4*cm, height=2*cm)
                logo.hAlign = 'CENTER'
                elements.append(logo)
                elements.append(Spacer(1, 10*mm))
            except:
                pass
        
        # Titre
        elements.append(Paragraph(title, self.styles['CustomTitle']))
        if subtitle:
            elements.append(Paragraph(subtitle, self.styles['CustomSubtitle']))
        
        # Date de génération
        date_str = f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
        elements.append(Paragraph(date_str, self.styles['InfoLabel']))
        elements.append(Spacer(1, 8*mm))
        
        # Ligne de séparation
        line_table = Table([['']], colWidths=[self.width - 2*cm])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 2, colors.HexColor('#4f46e5')),
        ]))
        elements.append(line_table)
        elements.append(Spacer(1, 5*mm))
    
    def add_info_section(self, elements, info_dict):
        """Ajouter une section d'informations"""
        data = []
        for label, value in info_dict.items():
            data.append([
                Paragraph(f"<b>{label}:</b>", self.styles['InfoLabel']),
                Paragraph(str(value), self.styles['InfoValue'])
            ])
        
        table = Table(data, colWidths=[5*cm, 10*cm])
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 5*mm))
    
    def create_data_table(self, data, col_widths=None, header_color='#4f46e5', wrap_columns=None, compact=False):
        """Créer un tableau de données stylisé
        
        Args:
            data: Liste de listes contenant les données
            col_widths: Liste des largeurs de colonnes
            header_color: Couleur de l'en-tête
            wrap_columns: Liste des index de colonnes où appliquer le retour à la ligne (0-based)
        """
        if not col_widths:
            # Distribution équitable
            available_width = self.width - 2*cm
            col_widths = [available_width / len(data[0])] * len(data[0])
        
        # Appliquer Paragraph aux colonnes spécifiées pour permettre le retour à la ligne
        if wrap_columns:
            processed_data = []
            for row_idx, row in enumerate(data):
                new_row = []
                for col_idx, cell in enumerate(row):
                    if row_idx > 0 and col_idx in wrap_columns:  # Pas l'en-tête
                        # Convertir en Paragraph pour permettre le retour à la ligne
                        style = ParagraphStyle(
                            name='CellText',
                            fontSize=9,
                            leading=11,
                            textColor=colors.black,
                            fontName='Helvetica'
                        )
                        new_row.append(Paragraph(str(cell), style))
                    else:
                        new_row.append(cell)
                processed_data.append(new_row)
            data = processed_data
        
        table = Table(data, colWidths=col_widths, repeatRows=1)
        
        # Styles de base (ajustés si compact)
        header_font_size = 10 if not compact else 9
        body_font_size = 9 if not compact else 8
        padding_top = 5 if not compact else 3
        padding_bottom = 5 if not compact else 3
        padding_lr = 8 if not compact else 4

        table_style = TableStyle([
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(header_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), header_font_size),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Corps
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), body_font_size),
            ('TOPPADDING', (0, 1), (-1, -1), padding_top),
            ('BOTTOMPADDING', (0, 1), (-1, -1), padding_bottom),
            ('LEFTPADDING', (0, 0), (-1, -1), padding_lr),
            ('RIGHTPADDING', (0, 0), (-1, -1), padding_lr),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Alignement vertical en haut
            
            # Lignes alternées
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
            
            # Bordures
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#9ca3af')),
        ])
        
        table.setStyle(table_style)
        return table
    
    def add_footer(self, canvas, doc):
        """Ajouter un pied de page"""
        canvas.saveState()
        # Ligne de séparation
        canvas.setStrokeColor(colors.HexColor('#e5e7eb'))
        canvas.setLineWidth(1)
        canvas.line(2*cm, 2*cm, self.width - 2*cm, 2*cm)
        
        # Texte du pied de page
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#6b7280'))
        canvas.drawString(2*cm, 1.5*cm, "Institut de Formation")
        canvas.drawRightString(self.width - 2*cm, 1.5*cm, f"Page {doc.page}")
        canvas.restoreState()
