# Fragment à ajouter à documents/views.py

@login_required
def download_cohort_payment_report(request, cohort_id):
    """
    ZIP avec 2 PDFs:
    1. Bilan des paiements étudiants (montants payés, reste, détails)
    2. Bilan des paiements professeur (détails complets)
    """
    cohort = get_object_or_404(
        Cohort.objects.select_related('teacher', 'subject', 'level', 'academic_year'),
        id=cohort_id
    )
    
    enrollments = cohort.enrollments.select_related('student', 'tariff').prefetch_related('payments').order_by('student__last_name', 'student__first_name')
    teacher_payments = TeacherCohortPayment.objects.filter(cohort=cohort).select_related('teacher').order_by('-payment_date')
    
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        
        # 1. PDF PAIEMENTS ÉTUDIANTS
        def build_student_payments(story, styles):
            h1, h2, normal = styles['Heading1'], styles['Heading2'], styles['BodyText']
            h1.fontSize = 14
            h2.fontSize = 12
            normal.fontSize = 10
            
            story.append(Paragraph(f"BILAN PAIEMENTS ÉTUDIANTS - {cohort.name}", h1))
            story.append(Spacer(1, 0.4 * cm))
            
            # Tableau détaillé
            pay_data = [["N°", "Étudiant", "Montant dû", "Payé", "Reste", "Dernier paiement"]]
            
            for idx, enr in enumerate(enrollments, 1):
                total_tariff = enr.tariff.amount if enr.tariff else 0
                paid = enr.payments.aggregate(total=Coalesce(Sum('amount'), 0))['total']
                remaining = total_tariff - paid
                
                last_payment = enr.payments.order_by('-payment_date').first()
                last_date_str = last_payment.payment_date.strftime('%d/%m/%Y') if last_payment else "Aucun"
                
                pay_data.append([
                    str(idx),
                    f"{enr.student.last_name} {enr.student.first_name}",
                    f"{total_tariff:,.0f} DA".replace(',', ' '),
                    f"{paid:,.0f} DA".replace(',', ' '),
                    f"{remaining:,.0f} DA".replace(',', ' '),
                    last_date_str
                ])
            
            table = Table(pay_data, repeatRows=1, colWidths=[1*cm, 5.5*cm, 2.2*cm, 2.2*cm, 2.2*cm, 2.5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
                ('ALIGN', (0,0), (0,-1), 'CENTER'),
                ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(table)
            
            # Totaux
            total_due = sum(enr.tariff.amount if enr.tariff else 0 for enr in enrollments)
            total_paid = Payment.objects.filter(enrollment__cohort=cohort).aggregate(total=Coalesce(Sum('amount'), 0))['total']
            total_remaining = total_due - total_paid
            
            story.append(Spacer(1, 0.4 * cm))
            story.append(Paragraph(f"<b>Total à percevoir :</b> {total_due:,.0f} DA".replace(',', ' '), normal))
            story.append(Paragraph(f"<b>Total payé :</b> {total_paid:,.0f} DA".replace(',', ' '), normal))
            story.append(Paragraph(f"<b>Total restant :</b> {total_remaining:,.0f} DA".replace(',', ' '), normal))
        
        student_pay_pdf = _generate_pdf_bytes(f"Paiements Étudiants {cohort.name}", build_student_payments, pagesize=A4)
        zf.writestr("01_Paiements_Etudiants.pdf", student_pay_pdf)
        
        # 2. PDF PAIEMENTS PROFESSEUR
        def build_teacher_payments(story, styles):
            h1, h2, normal = styles['Heading1'], styles['Heading2'], styles['BodyText']
            h1.fontSize = 14
            h2.fontSize = 12
            normal.fontSize = 10
            
            story.append(Paragraph(f"BILAN PAIEMENTS PROFESSEUR - {cohort.name}", h1))
            story.append(Spacer(1, 0.3 * cm))
            
            # Infos du prof
            story.append(Paragraph(f"<b>Professeur :</b> {cohort.teacher.get_full_name()}", normal))
            story.append(Paragraph(f"<b>Tarif horaire :</b> {cohort.teacher_hourly_rate:,.0f} DA/h".replace(',', ' '), normal))
            story.append(Spacer(1, 0.3 * cm))
            
            if teacher_payments.exists():
                story.append(Paragraph("Historique des paiements", h2))
                pay_data = [["Date", "Montant", "Méthode", "Notes"]]
                
                for tp in teacher_payments:
                    pay_data.append([
                        tp.payment_date.strftime('%d/%m/%Y'),
                        f"{tp.amount_paid:,} DA".replace(',', ' '),
                        tp.get_payment_method_display(),
                        (tp.notes or "")[:50]
                    ])
                
                table = Table(pay_data, repeatRows=1, colWidths=[2.5*cm, 3*cm, 3*cm, 5.5*cm])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,-1), 8),
                    ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
                    ('ALIGN', (1,0), (1,-1), 'RIGHT'),
                ]))
                story.append(table)
                
                # Total payé
                total_teacher_paid = teacher_payments.aggregate(total=Coalesce(Sum('amount_paid'), 0))['total']
                story.append(Spacer(1, 0.3 * cm))
                story.append(Paragraph(f"<b>Total payé au professeur :</b> {total_teacher_paid:,.0f} DA".replace(',', ' '), normal))
            else:
                story.append(Paragraph("<i>Aucun paiement enregistré</i>", normal))
        
        teacher_pay_pdf = _generate_pdf_bytes(f"Paiements Professeur {cohort.name}", build_teacher_payments, pagesize=A4)
        zf.writestr("02_Paiements_Professeur.pdf", teacher_pay_pdf)
    
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer.read(), content_type='application/zip')
    from urllib.parse import quote
    filename = f"Bilan_Paiements_{cohort.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.zip"
    encoded_filename = quote(filename)
    response['Content-Disposition'] = f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}'
    return response
