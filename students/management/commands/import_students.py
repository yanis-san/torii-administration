import json
from django.core.management.base import BaseCommand
from students.models import Student


class Command(BaseCommand):
    help = 'Import students from JSON file without enrolling them to any cohort'

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Path to the JSON file containing student data'
        )

    def handle(self, *args, **options):
        json_file = options['json_file']
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                students_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {json_file}'))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f'Invalid JSON file: {json_file}'))
            return

        created_count = 0
        skipped_count = 0
        errors = []

        for idx, student_info in enumerate(students_data, 1):
            try:
                phone = student_info.get('phone', '').strip()
                
                # Verify that phone exists
                if not phone:
                    errors.append(f"Row {idx}: Missing phone number")
                    skipped_count += 1
                    continue

                # Check if student already exists by phone number
                existing_student = Student.objects.filter(phone=phone).first()
                
                if existing_student:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Row {idx}: Student with phone {phone} already exists "
                            f"({existing_student.first_name} {existing_student.last_name})"
                        )
                    )
                    skipped_count += 1
                    continue

                # Extract student data
                first_name = student_info.get('first_name', '').strip()
                last_name = student_info.get('last_name', '').strip()
                phone_2 = student_info.get('phone_2', '').strip()
                motivation = student_info.get('motivation', '').strip()

                # Validate required fields
                if not first_name or not last_name:
                    errors.append(f"Row {idx}: Missing first_name or last_name")
                    skipped_count += 1
                    continue

                # Create the student
                student = Student.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    phone_2=phone_2 or '',
                    motivation=motivation
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Row {idx}: Created student: {student.last_name} {student.first_name} "
                        f"(Phone: {phone})"
                    )
                )
                created_count += 1

            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")
                skipped_count += 1

        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"Created: {created_count} students"))
        self.stdout.write(self.style.WARNING(f"Skipped: {skipped_count} records"))

        if errors:
            self.stdout.write(self.style.ERROR(f"\nErrors found:"))
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
