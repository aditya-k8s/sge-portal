"""
Management command to seed the database with initial demo data.

Usage:
    python manage.py seed_data
    python manage.py seed_data --clear   (clears existing data first)
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = 'Seed the database with demo data for Shri Gouri Engineers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.machines.models import Machine
        from apps.projects.models import Project, ProjectProcess, ProjectActivity
        from apps.notifications.models import Notification

        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Notification.objects.all().delete()
            ProjectProcess.objects.all().delete()
            ProjectActivity.objects.all().delete()
            Project.objects.all().delete()
            Machine.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.WARNING('Data cleared.'))

        # ── Create superuser/admin ────────────────────────────────────────
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@shrigouriengineers.com',
                password='admin123',
                first_name='Admin',
                last_name='SGE',
                role='admin',
                company_name='Shri Gouri Engineers',
            )
            self.stdout.write(self.style.SUCCESS('[ok] Admin user created (username: admin / password: admin123)'))
        else:
            admin = User.objects.get(username='admin')
            self.stdout.write('  Admin user already exists - skipping.')

        # ── Create client accounts ────────────────────────────────────────
        clients_data = [
            {
                'username': 'abc_industries',
                'email': 'contact@abcindustries.com',
                'first_name': 'Rajesh',
                'last_name': 'Sharma',
                'company_name': 'ABC Industries Pvt. Ltd.',
                'phone': '+91-9876543210',
                'address': '12, MIDC Industrial Area, Pune, Maharashtra',
            },
            {
                'username': 'xyz_engineering',
                'email': 'procurement@xyzengineering.com',
                'first_name': 'Priya',
                'last_name': 'Mehta',
                'company_name': 'XYZ Engineering Works',
                'phone': '+91-9765432109',
                'address': 'Plot 45, Bhosari Industrial Estate, Pune',
            },
            {
                'username': 'delta_auto',
                'email': 'orders@deltaauto.com',
                'first_name': 'Vikram',
                'last_name': 'Patil',
                'company_name': 'Delta Automotive Components',
                'phone': '+91-9654321098',
                'address': 'G-12, Chakan Industrial Zone, Pune',
            },
        ]

        clients = []
        for data in clients_data:
            if not User.objects.filter(username=data['username']).exists():
                client = User.objects.create_user(
                    password='client123',
                    role='client',
                    **data
                )
                clients.append(client)
                self.stdout.write(self.style.SUCCESS(f'[ok] Client created: {data["username"]} / password: client123'))
            else:
                clients.append(User.objects.get(username=data['username']))
                self.stdout.write(f'  Client {data["username"]} already exists - skipping.')

        # ── Create machines ───────────────────────────────────────────────
        machines_data = [
            {
                'machine_name': 'Fanuc CNC Turning Centre',
                'machine_type': 'CNC',
                'model_number': 'Fanuc OT-D',
                'manufacturer': 'Fanuc',
                'description': 'High-precision CNC turning centre for complex shaft and bushing components. Capable of multi-axis turning, threading, and profile machining.',
                'specifications': 'Max turning diameter: Ø 300 mm\nMax turning length: 500 mm\nSpindle speed: 50–4500 RPM\nTolerance: ±0.01 mm',
            },
            {
                'machine_name': 'BFW VMC 850',
                'machine_type': 'VMC',
                'model_number': 'BFW BMV-850',
                'manufacturer': 'BFW (Bharat Fritz Werner)',
                'description': 'Vertical machining centre for milling, drilling, boring and tapping operations. Suitable for prismatic and complex surface components.',
                'specifications': 'Table size: 900 × 500 mm\nX/Y/Z travel: 800 × 500 × 500 mm\nSpindle speed: 60–8000 RPM\nSpindle taper: BT40',
            },
            {
                'machine_name': 'Microcut BMC 1000',
                'machine_type': 'BMC',
                'model_number': 'Microcut HBM-1000',
                'manufacturer': 'Microcut',
                'description': 'Bed milling centre for heavy-duty milling of large and complex workpieces with high material removal rates.',
                'specifications': 'Table size: 1200 × 550 mm\nMax component weight: 800 kg\nHead swivel: ±90°\nSpindle power: 11 kW',
            },
            {
                'machine_name': 'HMT Lathe NH-26',
                'machine_type': 'LATHE',
                'model_number': 'HMT NH-26',
                'manufacturer': 'HMT Machine Tools',
                'description': 'Heavy-duty centre lathe for turning, facing, boring, and threading. Used for both prototype and production turning work.',
                'specifications': 'Swing over bed: Ø 530 mm\nDistance between centres: 1500 mm\nSpindle bore: 65 mm\nSpindle speeds: 14 steps, 25–1400 RPM',
            },
            {
                'machine_name': 'ACE CNC Turning Centre',
                'machine_type': 'CNC',
                'model_number': 'ACE Jobber XL',
                'manufacturer': 'ACE Micromatic',
                'description': 'Compact CNC turning centre for high-volume precision turned components with quick changeover.',
                'specifications': 'Max turning diameter: Ø 200 mm\nMax turning length: 350 mm\nC-axis resolution: 0.001°\nLive tooling: Yes',
            },
        ]

        machines = []
        for data in machines_data:
            machine, created = Machine.objects.get_or_create(
                machine_name=data['machine_name'],
                defaults=data
            )
            machines.append(machine)
            if created:
                self.stdout.write(self.style.SUCCESS(f'[ok] Machine created: {machine.machine_name}'))
            else:
                self.stdout.write(f'  Machine {machine.machine_name} already exists - skipping.')

        # ── Create projects ───────────────────────────────────────────────
        DEFAULT_PROCESSES = [
            'Material Received',
            'Cutting',
            'Milling',
            'Drilling',
            'Heat Treatment',
            'Finishing',
            'Quality Check',
            'Completed',
        ]

        projects_data = [
            {
                'project_name': 'Gear Shaft — 50 Nos',
                'client': clients[0],
                'machine': machines[0],
                'status': 'in_progress',
                'current_process': 'Milling',
                'description': 'EN24 gear shaft components for automotive gearbox assembly. 50 nos per batch.',
                'quantity': 50,
                'material': 'EN24 Steel',
                'start_date': date.today() - timedelta(days=5),
                'expected_delivery': date.today() + timedelta(days=10),
                'completed_processes': 3,  # how many stages done
            },
            {
                'project_name': 'Hydraulic Cylinder Rod',
                'client': clients[0],
                'machine': machines[0],
                'status': 'completed',
                'current_process': 'Completed',
                'description': 'Precision turned hydraulic rod, chrome plated, for industrial cylinder assembly.',
                'quantity': 20,
                'material': 'EN8 Steel',
                'start_date': date.today() - timedelta(days=20),
                'expected_delivery': date.today() - timedelta(days=5),
                'completed_date': date.today() - timedelta(days=3),
                'completed_processes': 8,
            },
            {
                'project_name': 'Spindle Housing — VMC',
                'client': clients[1],
                'machine': machines[1],
                'status': 'in_progress',
                'current_process': 'Drilling',
                'description': 'Cast iron spindle housing, multi-face milling and boring, for machine tool assembly.',
                'quantity': 5,
                'material': 'Cast Iron FG260',
                'start_date': date.today() - timedelta(days=3),
                'expected_delivery': date.today() + timedelta(days=12),
                'completed_processes': 4,
            },
            {
                'project_name': 'Flange Coupling Set',
                'client': clients[1],
                'machine': machines[2],
                'status': 'pending',
                'current_process': '',
                'description': 'Mild steel flange couplings with pilot bore, key-way and bolt holes.',
                'quantity': 30,
                'material': 'Mild Steel IS2062',
                'start_date': date.today() + timedelta(days=2),
                'expected_delivery': date.today() + timedelta(days=18),
                'completed_processes': 0,
            },
            {
                'project_name': 'Brake Drum Components',
                'client': clients[2],
                'machine': machines[3],
                'status': 'in_progress',
                'current_process': 'Finishing',
                'description': 'Automotive brake drum components, high tolerance turning and boring.',
                'quantity': 100,
                'material': 'Grey Cast Iron',
                'start_date': date.today() - timedelta(days=8),
                'expected_delivery': date.today() + timedelta(days=6),
                'completed_processes': 6,
            },
            {
                'project_name': 'Pump Impeller Shaft',
                'client': clients[2],
                'machine': machines[4],
                'status': 'completed',
                'current_process': 'Completed',
                'description': 'SS304 pump shaft with impeller keyway and sealed bearing seats.',
                'quantity': 10,
                'material': 'SS304 Stainless Steel',
                'start_date': date.today() - timedelta(days=30),
                'expected_delivery': date.today() - timedelta(days=15),
                'completed_date': date.today() - timedelta(days=14),
                'completed_processes': 8,
            },
        ]

        for pdata in projects_data:
            completed_processes = pdata.pop('completed_processes')
            completed_date_val = pdata.pop('completed_date', None)

            if Project.objects.filter(project_name=pdata['project_name']).exists():
                self.stdout.write(f'  Project "{pdata["project_name"]}" already exists - skipping.')
                continue

            project = Project(**pdata)
            if completed_date_val:
                project.completed_date = completed_date_val
            project.save()

            # Create process stages
            for i, process_name in enumerate(DEFAULT_PROCESSES):
                if i < completed_processes:
                    status = 'completed'
                    completed_at = timezone.now() - timedelta(days=(completed_processes - i))
                elif i == completed_processes and pdata['status'] == 'in_progress':
                    status = 'in_progress'
                    completed_at = None
                else:
                    status = 'pending'
                    completed_at = None

                ProjectProcess.objects.create(
                    project=project,
                    process_name=process_name,
                    status=status,
                    order=i,
                    completed_at=completed_at if status == 'completed' else None,
                )

            # Activity log
            ProjectActivity.objects.create(
                project=project,
                actor=admin,
                action=f'Project created by Admin'
            )
            if completed_processes > 0:
                ProjectActivity.objects.create(
                    project=project,
                    actor=admin,
                    action=f'Process updated to {pdata.get("current_process", "In Progress")}'
                )

            # Notification for client
            if pdata['status'] != 'pending':
                Notification.objects.create(
                    user=pdata['client'],
                    project=project,
                    message=f'Your project "{project.project_name}" status: {project.get_status_display()}.'
                )

            self.stdout.write(self.style.SUCCESS(f'[ok] Project created: {project.project_name}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 55))
        self.stdout.write(self.style.SUCCESS('  Seed data created successfully!'))
        self.stdout.write(self.style.SUCCESS('=' * 55))
        self.stdout.write('')
        self.stdout.write('  Login credentials:')
        self.stdout.write('  -----------------------------------------------')
        self.stdout.write('  |  Admin     : admin / admin123              |')
        self.stdout.write('  |  Client 1  : abc_industries / client123    |')
        self.stdout.write('  |  Client 2  : xyz_engineering / client123   |')
        self.stdout.write('  |  Client 3  : delta_auto / client123        |')
        self.stdout.write('  -----------------------------------------------')
        self.stdout.write('')
        self.stdout.write('  Start server:  python manage.py runserver')
        self.stdout.write('  Admin panel:   http://127.0.0.1:8000/admin/')
        self.stdout.write('  Public site:   http://127.0.0.1:8000/')
        self.stdout.write('  Dashboard:     http://127.0.0.1:8000/dashboard/')
        self.stdout.write('')
