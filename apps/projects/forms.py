from django import forms

from apps.core.validators import validate_document_upload

from .models import Project, ProjectBill, ProjectFile, ProjectProcess

INPUT_CLASS = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm'
SELECT_CLASS = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm bg-white'
FILE_CLASS = 'block w-full text-sm text-steel-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-orange-50 file:text-orange-700 hover:file:bg-orange-100 cursor-pointer'


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'project_name', 'client', 'machine', 'status', 'description',
            'quantity', 'material', 'start_date', 'expected_delivery', 'notes'
        ]
        widgets = {
            'project_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'client': forms.Select(attrs={'class': SELECT_CLASS}),
            'machine': forms.Select(attrs={'class': SELECT_CLASS}),
            'status': forms.Select(attrs={'class': SELECT_CLASS}),
            'description': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 3}),
            'quantity': forms.NumberInput(attrs={'class': INPUT_CLASS, 'min': 1}),
            'material': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'start_date': forms.DateInput(attrs={'class': INPUT_CLASS, 'type': 'date'}),
            'expected_delivery': forms.DateInput(attrs={'class': INPUT_CLASS, 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models import User

        self.fields['client'].queryset = User.objects.filter(
            role='client'
        ).order_by('company_name', 'first_name')
        self.fields['client'].label_from_instance = (
            lambda obj: f"{obj.get_full_name() or obj.username} ({obj.company_name})"
        )
        # Only offer machines that are actually in service.
        self.fields['machine'].queryset = self.fields['machine'].queryset.filter(
            is_active=True
        )

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity < 1:
            raise forms.ValidationError('Quantity must be at least 1.')
        return quantity

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        delivery = cleaned.get('expected_delivery')
        # Reported against the field so the user sees it inline, and matches
        # the project_delivery_after_start database constraint.
        if start and delivery and delivery < start:
            self.add_error(
                'expected_delivery',
                'Expected delivery cannot be earlier than the start date.',
            )
        return cleaned


class ProjectProcessForm(forms.ModelForm):
    class Meta:
        model = ProjectProcess
        fields = ['process_name', 'status', 'order', 'notes']
        widgets = {
            'process_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'status': forms.Select(attrs={'class': SELECT_CLASS}),
            'order': forms.NumberInput(attrs={'class': INPUT_CLASS}),
            'notes': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 2}),
        }


class ProjectFileForm(forms.ModelForm):
    class Meta:
        model = ProjectFile
        fields = ['file', 'file_name', 'file_type']
        widgets = {
            'file': forms.FileInput(attrs={'class': FILE_CLASS}),
            'file_name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'file_type': forms.Select(attrs={'class': SELECT_CLASS}),
        }

    def clean_file(self):
        return validate_document_upload(self.cleaned_data.get('file'))


class BillForm(forms.ModelForm):
    """
    Invoice upload form.

    The bill view previously read every one of these values straight out of
    request.POST, so a non-numeric amount raised a database error and
    int(gst_rate) raised ValueError on any unexpected input.
    """

    class Meta:
        model = ProjectBill
        fields = [
            'file', 'invoice_number', 'amount', 'gst_rate', 'hsn_code',
            'description_of_work', 'notes',
        ]
        widgets = {
            'file': forms.FileInput(attrs={'class': FILE_CLASS}),
            'invoice_number': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'amount': forms.NumberInput(attrs={'class': INPUT_CLASS, 'step': '0.01', 'min': '0'}),
            'gst_rate': forms.Select(attrs={'class': SELECT_CLASS}),
            'hsn_code': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'description_of_work': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 3}),
            'notes': forms.TextInput(attrs={'class': INPUT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].required = True

    def clean_file(self):
        return validate_document_upload(self.cleaned_data.get('file'))

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount < 0:
            raise forms.ValidationError('Amount cannot be negative.')
        return amount


class ProcessUpdateForm(forms.Form):
    process_id = forms.IntegerField(widget=forms.HiddenInput())
    status = forms.ChoiceField(
        choices=ProjectProcess.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': SELECT_CLASS})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 2})
    )
