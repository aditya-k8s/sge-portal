"""
Smoke tests covering every page, the access rules, and the PWA endpoints.

Run with:

    python manage.py test tests

These run against whatever DB_ENGINE is configured. Django builds a separate
test database and drops it again afterwards, so they never touch real data.
A database server has to be reachable; point DB_ENGINE at a local mongod to
run them offline.
"""

import json
from datetime import date, timedelta

from django.contrib.messages import get_messages
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import OTPCode, User
from apps.machines.models import Machine
from apps.notifications.models import Notification
from apps.portfolio.models import Service, WorkSample
from apps.projects.models import Project, ProjectBill, ProjectFile, ProjectProcess
from apps.website.models import ContactEnquiry


class BaseFixtureMixin:
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username='admin_user', password='test-pass-1234',
            email='admin@example.test', role='admin', is_staff=True,
        )
        cls.client_a = User.objects.create_user(
            username='client_a', password='test-pass-1234',
            email='a@example.test', role='client', company_name='Alpha Works',
            first_name='Asha', last_name='Rao',
        )
        cls.client_b = User.objects.create_user(
            username='client_b', password='test-pass-1234',
            email='b@example.test', role='client', company_name='Beta Tools',
        )
        cls.machine = Machine.objects.create(
            machine_name='Test VMC 850', machine_type='VMC', is_active=True,
        )
        cls.project_a = Project.objects.create(
            project_name='Alpha gear shaft', client=cls.client_a,
            machine=cls.machine, status='in_progress', quantity=10,
            start_date=date.today(), expected_delivery=date.today() + timedelta(days=7),
        )
        cls.project_b = Project.objects.create(
            project_name='Beta flange', client=cls.client_b, quantity=1,
        )
        for index, name in enumerate(['Cutting', 'Milling', 'Completed']):
            ProjectProcess.objects.create(
                project=cls.project_a, process_name=name, order=index,
                status='completed' if index == 0 else 'pending',
            )


class PublicPagesTests(BaseFixtureMixin, TestCase):
    def test_public_pages_load(self):
        WorkSample.objects.create(title='Sample part', is_active=True, is_featured=True)
        Service.objects.create(title='CNC Machining', is_active=True)

        for name in ['home', 'about', 'industries', 'contact', 'our_work', 'services']:
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)

    def test_login_page_loads(self):
        self.assertEqual(self.client.get(reverse('login')).status_code, 200)

    def test_contact_form_saves_enquiry_and_redirects(self):
        response = self.client.post(reverse('contact'), {
            'name': 'Ravi Kumar',
            'email': 'ravi@example.test',
            'phone': '9999999999',
            'subject': 'Quote request',
            'message': 'Please quote for 200 shafts.',
        })
        # Post/redirect/get, so refreshing the page cannot resubmit.
        self.assertRedirects(response, reverse('contact'))
        enquiry = ContactEnquiry.objects.get()
        self.assertEqual(enquiry.name, 'Ravi Kumar')
        self.assertEqual(enquiry.status, 'new')

    def test_contact_form_reports_invalid_input(self):
        response = self.client.post(reverse('contact'), {
            'name': '', 'email': 'not-an-email', 'subject': '', 'message': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ContactEnquiry.objects.exists())
        self.assertTrue(response.context['form'].errors)


class AuthenticationTests(BaseFixtureMixin, TestCase):
    def test_login_succeeds_and_redirects_to_dashboard(self):
        response = self.client.post(reverse('login'), {
            'username': 'client_a', 'password': 'test-pass-1234',
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_next_parameter_cannot_redirect_off_site(self):
        """An absolute external ?next= must be ignored, not followed."""
        response = self.client.post(
            reverse('login') + '?next=https://malicious.example/steal',
            {'username': 'client_a', 'password': 'test-pass-1234'},
        )
        self.assertRedirects(response, reverse('dashboard'))

    def test_next_parameter_allows_internal_path(self):
        target = reverse('project_list')
        response = self.client.post(
            reverse('login') + f'?next={target}',
            {'username': 'client_a', 'password': 'test-pass-1234'},
        )
        self.assertRedirects(response, target)

    def test_password_reset_with_duplicate_emails_does_not_crash(self):
        """
        Two accounts may share an address because the column is not unique.
        get() used to raise MultipleObjectsReturned here, returning a 500.
        """
        User.objects.create_user(
            username='client_a_dup', password='test-pass-1234',
            email='a@example.test', role='client',
        )
        response = self.client.post(reverse('forgot_password'), {'email': 'a@example.test'})
        self.assertRedirects(response, reverse('forgot_password_verify'))

        otp = OTPCode.objects.filter(purpose='password_reset').latest('created_at')
        response = self.client.post(reverse('forgot_password_verify'), {
            'otp_code': otp.code,
            'new_password1': 'fresh-pass-9876',
            'new_password2': 'fresh-pass-9876',
        })
        self.assertRedirects(response, reverse('login'))

    def test_forgot_password_does_not_reveal_unknown_address(self):
        response = self.client.post(reverse('forgot_password'), {'email': 'nobody@example.test'})
        self.assertRedirects(response, reverse('forgot_password_verify'))
        self.assertFalse(OTPCode.objects.filter(email='nobody@example.test').exists())

    def test_otp_requests_are_rate_limited(self):
        for _ in range(6):
            self.client.post(reverse('forgot_password'), {'email': 'a@example.test'})
        self.assertLessEqual(
            OTPCode.objects.filter(email='a@example.test', purpose='password_reset').count(),
            5,
        )


class DashboardAccessTests(BaseFixtureMixin, TestCase):
    ADMIN_PAGES = [
        'dashboard', 'project_list', 'project_create', 'analytics',
        'machine_list', 'machine_create', 'client_list', 'client_create',
        'work_sample_list', 'service_list', 'field_list',
        'process_template_list', 'enquiry_list',
    ]

    def test_admin_can_open_every_dashboard_page(self):
        self.client.force_login(self.admin)
        for name in self.ADMIN_PAGES:
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200, name)

    def test_client_is_refused_admin_pages(self):
        self.client.force_login(self.client_a)
        for name in self.ADMIN_PAGES:
            if name in ('dashboard', 'project_list'):
                continue  # Shared pages, filtered by role.
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertRedirects(response, reverse('dashboard'), msg_prefix=name)

    def test_client_refusal_explains_itself(self):
        self.client.force_login(self.client_a)
        response = self.client.get(reverse('analytics'), follow=True)
        messages = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('administrators' in m for m in messages))

    def test_admin_json_request_is_refused_with_403(self):
        self.client.force_login(self.client_a)
        response = self.client.post(
            reverse('update_process', args=[self.project_a.pk]),
            data='{}', content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 403)

    def test_anonymous_visitor_is_sent_to_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])


class ProjectIsolationTests(BaseFixtureMixin, TestCase):
    def test_client_sees_only_their_own_projects(self):
        self.client.force_login(self.client_a)
        response = self.client.get(reverse('project_list'))
        listed = list(response.context['projects'])
        self.assertIn(self.project_a, listed)
        self.assertNotIn(self.project_b, listed)

    def test_client_cannot_open_another_clients_project(self):
        self.client.force_login(self.client_a)
        response = self.client.get(reverse('project_detail', args=[self.project_b.pk]))
        self.assertEqual(response.status_code, 404)

    def test_client_cannot_download_another_clients_timeline(self):
        self.client.force_login(self.client_a)
        response = self.client.get(reverse('download_timeline', args=[self.project_b.pk]))
        self.assertEqual(response.status_code, 404)

    def test_admin_can_open_any_project(self):
        self.client.force_login(self.admin)
        for project in (self.project_a, self.project_b):
            with self.subTest(project=project.pk):
                response = self.client.get(reverse('project_detail', args=[project.pk]))
                self.assertEqual(response.status_code, 200)


class ProjectWorkflowTests(BaseFixtureMixin, TestCase):
    def setUp(self):
        self.client.force_login(self.admin)

    def test_creating_a_project_also_creates_its_stages(self):
        response = self.client.post(reverse('project_create'), {
            'project_name': 'New bracket', 'client': self.client_a.pk,
            'machine': self.machine.pk, 'status': 'pending', 'quantity': 5,
            'description': '', 'material': 'EN24', 'notes': '',
            'start_date': '', 'expected_delivery': '',
        })
        project = Project.objects.get(project_name='New bracket')
        self.assertRedirects(response, reverse('project_detail', args=[project.pk]))
        self.assertEqual(
            project.processes.count(), len(Project.DEFAULT_PROCESSES)
        )
        self.assertTrue(project.project_code.startswith('SGE-'))
        # The client is told about it.
        self.assertTrue(
            Notification.objects.filter(user=self.client_a, project=project).exists()
        )

    def test_delivery_date_before_start_date_is_rejected(self):
        response = self.client.post(reverse('project_create'), {
            'project_name': 'Impossible schedule', 'client': self.client_a.pk,
            'status': 'pending', 'quantity': 1,
            'start_date': '2026-05-10', 'expected_delivery': '2026-05-01',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('expected_delivery', response.context['form'].errors)
        self.assertFalse(Project.objects.filter(project_name='Impossible schedule').exists())

    def test_quantity_below_one_is_rejected(self):
        response = self.client.post(reverse('project_create'), {
            'project_name': 'Zero quantity', 'client': self.client_a.pk,
            'status': 'pending', 'quantity': 0,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Project.objects.filter(project_name='Zero quantity').exists())

    def test_project_codes_are_unique_across_many_projects(self):
        codes = set()
        for index in range(25):
            project = Project.objects.create(
                project_name=f'Bulk {index}', client=self.client_a, quantity=1,
            )
            codes.add(project.project_code)
        self.assertEqual(len(codes), 25)

    def test_updating_a_stage_reports_progress(self):
        stage = self.project_a.processes.get(process_name='Milling')
        response = self.client.post(
            reverse('update_process', args=[self.project_a.pk]),
            data=json.dumps({'process_id': stage.pk, 'status': 'in_progress'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['project_status'], 'in_progress')
        self.project_a.refresh_from_db()
        self.assertEqual(self.project_a.current_process, 'Milling')

    def test_completing_every_stage_completes_the_project(self):
        for stage in self.project_a.processes.all():
            self.client.post(
                reverse('update_process', args=[self.project_a.pk]),
                data=json.dumps({'process_id': stage.pk, 'status': 'completed'}),
                content_type='application/json',
            )
        self.project_a.refresh_from_db()
        self.assertEqual(self.project_a.status, 'completed')
        self.assertIsNotNone(self.project_a.completed_date)
        self.assertEqual(self.project_a.progress_percentage, 100)

    def test_malformed_stage_update_returns_400_not_500(self):
        response = self.client.post(
            reverse('update_process', args=[self.project_a.pk]),
            data='not json at all', content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_unknown_stage_status_is_rejected(self):
        stage = self.project_a.processes.first()
        response = self.client.post(
            reverse('update_process', args=[self.project_a.pk]),
            data=json.dumps({'process_id': stage.pk, 'status': 'banana'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        stage.refresh_from_db()
        self.assertNotEqual(stage.status, 'banana')

    def test_stage_from_another_project_is_rejected(self):
        other_stage = ProjectProcess.objects.create(
            project=self.project_b, process_name='Cutting', order=0,
        )
        response = self.client.post(
            reverse('update_process', args=[self.project_a.pk]),
            data=json.dumps({'process_id': other_stage.pk, 'status': 'completed'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)


class DestructiveActionTests(BaseFixtureMixin, TestCase):
    """Deleting must never happen on a GET, which a preloader or an
    <img src> in an email could trigger while an admin is signed in."""

    def setUp(self):
        self.client.force_login(self.admin)
        self.file = ProjectFile.objects.create(
            project=self.project_a, file='project_files/test.pdf',
            file_name='test.pdf', uploaded_by=self.admin,
        )
        self.bill = ProjectBill.objects.create(
            project=self.project_a, file='bills/test.pdf', file_name='test.pdf',
            amount=1000, gst_rate=18, uploaded_by=self.admin,
        )

    def test_file_delete_rejects_get(self):
        response = self.client.get(
            reverse('delete_file', args=[self.project_a.pk, self.file.pk])
        )
        self.assertEqual(response.status_code, 405)
        self.assertTrue(ProjectFile.objects.filter(pk=self.file.pk).exists())

    def test_file_delete_accepts_post(self):
        response = self.client.post(
            reverse('delete_file', args=[self.project_a.pk, self.file.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ProjectFile.objects.filter(pk=self.file.pk).exists())

    def test_bill_delete_rejects_get(self):
        response = self.client.get(
            reverse('delete_bill', args=[self.project_a.pk, self.bill.pk])
        )
        self.assertEqual(response.status_code, 405)
        self.assertTrue(ProjectBill.objects.filter(pk=self.bill.pk).exists())

    def test_field_toggle_rejects_get(self):
        from apps.formbuilder.models import ProjectField

        field = ProjectField.objects.create(label='Drawing number', is_active=True)
        response = self.client.get(reverse('field_toggle', args=[field.pk]))
        self.assertEqual(response.status_code, 405)
        field.refresh_from_db()
        self.assertTrue(field.is_active)


class BillAndInvoiceTests(BaseFixtureMixin, TestCase):
    def setUp(self):
        self.client.force_login(self.admin)

    def test_invalid_bill_amount_is_reported_not_crashed(self):
        response = self.client.post(
            reverse('upload_bill', args=[self.project_a.pk]),
            {'amount': 'not-a-number', 'gst_rate': '18'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ProjectBill.objects.exists())

    def test_invoice_pdf_downloads(self):
        bill = ProjectBill.objects.create(
            project=self.project_a, file='bills/test.pdf', file_name='test.pdf',
            amount=1000, gst_rate=18, uploaded_by=self.admin,
        )
        response = self.client.get(
            reverse('download_invoice', args=[self.project_a.pk, bill.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_timeline_pdf_downloads(self):
        response = self.client.get(
            reverse('download_timeline', args=[self.project_a.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b'%PDF'))


class RatingTests(BaseFixtureMixin, TestCase):
    def test_client_can_rate_only_completed_projects(self):
        self.client.force_login(self.client_a)
        response = self.client.post(
            reverse('submit_rating', args=[self.project_a.pk]),
            {'stars': '5', 'review': 'Excellent work'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(hasattr(self.project_a, 'rating') and self.project_a.rating.pk)

    def test_rating_outside_range_is_rejected(self):
        Project.objects.filter(pk=self.project_a.pk).update(status='completed')
        self.client.force_login(self.client_a)
        self.client.post(
            reverse('submit_rating', args=[self.project_a.pk]), {'stars': '9'}
        )
        self.project_a.refresh_from_db()
        self.assertFalse(hasattr(self.project_a, 'rating'))

    def test_valid_rating_is_saved(self):
        Project.objects.filter(pk=self.project_a.pk).update(status='completed')
        self.client.force_login(self.client_a)
        self.client.post(
            reverse('submit_rating', args=[self.project_a.pk]),
            {'stars': '4', 'review': 'Good'},
        )
        self.project_a.refresh_from_db()
        self.assertEqual(self.project_a.rating.stars, 4)


class NotificationTests(BaseFixtureMixin, TestCase):
    def test_list_shows_unread_state_before_marking_read(self):
        Notification.objects.create(
            user=self.client_a, project=self.project_a, message='Stage updated',
        )
        self.client.force_login(self.client_a)
        response = self.client.get(reverse('notification_list'))
        self.assertEqual(response.status_code, 200)
        # The rows handed to the template are the pre-update ones.
        self.assertFalse(response.context['notifications'][0].is_read)
        # And they are marked read for next time.
        self.assertTrue(Notification.objects.get(user=self.client_a).is_read)

    def test_unread_count_is_not_cacheable(self):
        self.client.force_login(self.client_a)
        response = self.client.get(reverse('unread_count'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_mark_all_read_requires_post(self):
        self.client.force_login(self.client_a)
        self.assertEqual(
            self.client.get(reverse('mark_all_read')).status_code, 405
        )


class PaginationTests(BaseFixtureMixin, TestCase):
    @override_settings(PAGE_SIZE=5)
    def test_project_list_paginates(self):
        for index in range(12):
            Project.objects.create(
                project_name=f'Extra {index}', client=self.client_a, quantity=1,
            )
        self.client.force_login(self.admin)
        response = self.client.get(reverse('project_list'))
        self.assertEqual(len(response.context['projects']), 5)
        self.assertTrue(response.context['page_obj'].has_next())

    def test_out_of_range_page_does_not_error(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('project_list') + '?page=9999')
        self.assertEqual(response.status_code, 200)

    def test_junk_page_value_does_not_error(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('project_list') + '?page=abc')
        self.assertEqual(response.status_code, 200)

    def test_unknown_status_filter_is_ignored(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('project_list') + '?status=banana')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['status_filter'], '')
        self.assertEqual(response.context['total_count'], Project.objects.count())


class SearchTests(BaseFixtureMixin, TestCase):
    def test_project_search_matches_client_company(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('project_list') + '?search=Alpha Works')
        self.assertIn(self.project_a, list(response.context['projects']))

    def test_project_search_matches_client_surname(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('project_list') + '?search=Rao')
        self.assertIn(self.project_a, list(response.context['projects']))


class ApiTests(BaseFixtureMixin, TestCase):
    def test_api_requires_authentication(self):
        response = self.client.get('/api/projects/')
        self.assertEqual(response.status_code, 403)

    def test_client_api_returns_only_their_projects(self):
        self.client.force_login(self.client_a)
        response = self.client.get('/api/projects/')
        self.assertEqual(response.status_code, 200)
        codes = [row['project_code'] for row in response.json()['results']]
        self.assertIn(self.project_a.project_code, codes)
        self.assertNotIn(self.project_b.project_code, codes)

    def test_api_unknown_status_filter_is_ignored(self):
        self.client.force_login(self.admin)
        response = self.client.get('/api/projects/?status=banana')
        self.assertEqual(response.json()['count'], Project.objects.count())

    def test_api_detail_and_processes(self):
        self.client.force_login(self.admin)
        detail = self.client.get(f'/api/projects/{self.project_a.pk}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()['progress_percentage'], 33)

        processes = self.client.get(f'/api/projects/{self.project_a.pk}/processes/')
        self.assertEqual(processes.status_code, 200)
        self.assertEqual(len(processes.json()), 3)


class ProgressiveWebAppTests(TestCase):
    def test_manifest_is_valid_and_installable(self):
        response = self.client.get('/manifest.json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/manifest+json', response['Content-Type'])

        manifest = json.loads(response.content)
        self.assertTrue(manifest['name'])
        self.assertTrue(manifest['short_name'])
        self.assertEqual(manifest['display'], 'standalone')
        self.assertTrue(manifest['start_url'].endswith('/dashboard/'))

        # Chrome will not offer installation without both of these sizes.
        sizes = {icon['sizes'] for icon in manifest['icons']}
        self.assertIn('192x192', sizes)
        self.assertIn('512x512', sizes)

        purposes = {icon.get('purpose') for icon in manifest['icons']}
        self.assertIn('maskable', purposes)

    def test_service_worker_is_served_as_javascript(self):
        response = self.client.get('/serviceworker.js')
        self.assertEqual(response.status_code, 200)
        self.assertIn('javascript', response['Content-Type'])
        body = response.content.decode()
        # A fetch handler is part of Chrome's installability criteria.
        self.assertIn("addEventListener('fetch'", body)

    def test_service_worker_does_not_cache_application_data(self):
        body = self.client.get('/serviceworker.js').content.decode()
        # Navigations go to the network first and are never written to a
        # cache, so one client cannot be shown another's dashboard.
        self.assertIn('networkFirstNavigation', body)
        self.assertNotIn('cache.put(request, response.clone())\n      return response;\n    }\n\n    if (request.mode', body)

    def test_offline_page_renders(self):
        response = self.client.get('/offline/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'You are offline', response.content)

    @override_settings(SCRIPT_PREFIX='/web')
    def test_manifest_scope_setting_is_used(self):
        """
        The manifest must report whatever scope the settings declare. The
        packaged django-pwa templates hardcoded '/manifest.json' and
        '/serviceworker.js', which 404 under a sub-path mount.
        """
        manifest = json.loads(self.client.get('/manifest.json').content)
        self.assertTrue(manifest['scope'].endswith('/'))
        self.assertTrue(manifest['start_url'].startswith(manifest['scope']))


class ErrorPageTests(TestCase):
    def test_missing_page_returns_404(self):
        self.assertEqual(self.client.get('/no-such-page/').status_code, 404)

    @override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'])
    def test_error_templates_render_without_database_access(self):
        """The 500 page must not depend on anything that might be broken."""
        from django.template.loader import render_to_string

        for status in ('400', '403', '404', '500'):
            with self.subTest(status=status):
                html = render_to_string(f'errors/{status}.html')
                self.assertIn(status, html)


class EmailTests(BaseFixtureMixin, TestCase):
    def test_stage_change_emails_the_client(self):
        self.client.force_login(self.admin)
        stage = self.project_a.processes.get(process_name='Milling')
        self.client.post(
            reverse('update_process', args=[self.project_a.pk]),
            data=json.dumps({'process_id': stage.pk, 'status': 'in_progress'}),
            content_type='application/json',
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.client_a.email, mail.outbox[0].to)

    def test_contact_email_link_uses_configured_site_url(self):
        # COMPANY_EMAIL must be set for the admin notification to be sent at
        # all; with no recipient configured the mail backend drops it and the
        # view logs an error instead.
        with override_settings(
            SITE_URL='https://sge.example.test',
            COMPANY_EMAIL='office@example.test',
        ):
            self.client.post(reverse('contact'), {
                'name': 'Ravi', 'email': 'ravi@example.test',
                'subject': 'Hello', 'message': 'Quote please',
            })
        self.assertEqual(len(mail.outbox), 2)  # admin notification + auto-reply
        body = '\n'.join(message.body for message in mail.outbox)
        self.assertIn('https://sge.example.test', body)
        self.assertNotIn('127.0.0.1', body)

    def test_enquiry_without_configured_recipient_still_saves(self):
        """A missing COMPANY_EMAIL must not lose the enquiry."""
        with override_settings(COMPANY_EMAIL='', EMAIL_HOST_USER=''):
            response = self.client.post(reverse('contact'), {
                'name': 'Priya', 'email': 'priya@example.test',
                'subject': 'Bearing housings', 'message': 'Quote for 40 units.',
            })
        self.assertRedirects(response, reverse('contact'))
        self.assertTrue(ContactEnquiry.objects.filter(name='Priya').exists())


class ValidationTests(BaseFixtureMixin, TestCase):
    def test_duplicate_email_is_rejected_when_creating_a_client(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('client_create'), {
            'username': 'new_client', 'first_name': 'New', 'last_name': 'Client',
            'email': 'a@example.test', 'company_name': 'New Co',
            'password1': 'test-pass-1234', 'password2': 'test-pass-1234',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)

    def test_oversized_upload_is_rejected_with_a_readable_message(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.projects.forms import ProjectFileForm

        oversized = SimpleUploadedFile(
            'huge.pdf', b'0' * (11 * 1024 * 1024), content_type='application/pdf'
        )
        form = ProjectFileForm(data={'file_type': 'drawing'}, files={'file': oversized})
        self.assertFalse(form.is_valid())
        self.assertIn('maximum', ' '.join(form.errors['file']).lower())

    def test_unexpected_file_type_is_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.projects.forms import ProjectFileForm

        script = SimpleUploadedFile('payload.html', b'<script>', content_type='text/html')
        form = ProjectFileForm(data={'file_type': 'other'}, files={'file': script})
        self.assertFalse(form.is_valid())
        self.assertIn('not accepted', ' '.join(form.errors['file']))


class DatabaseConstraintTests(BaseFixtureMixin, TestCase):
    def test_negative_bill_amount_is_refused_by_the_database(self):
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError), transaction.atomic():
            ProjectBill.objects.create(
                project=self.project_a, amount=-5, gst_rate=18,
            )

    def test_unsupported_gst_rate_is_refused_by_the_database(self):
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError), transaction.atomic():
            ProjectBill.objects.create(
                project=self.project_a, amount=100, gst_rate=7,
            )

    def test_one_custom_field_value_per_project(self):
        from django.db import IntegrityError, transaction

        from apps.formbuilder.models import ProjectField, ProjectFieldValue

        field = ProjectField.objects.create(label='Drawing number')
        ProjectFieldValue.objects.create(project=self.project_a, field=field, value='A1')
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProjectFieldValue.objects.create(project=self.project_a, field=field, value='A2')

    def test_expected_indexes_exist(self):
        """The indexes the dashboard and notification badge rely on."""
        from django.db import connection

        with connection.cursor() as cursor:
            existing = connection.introspection.get_constraints(
                cursor, Project._meta.db_table
            )
        index_names = set(existing)
        for expected in ('project_status_idx', 'project_client_status_idx'):
            self.assertIn(expected, index_names)
