from django import forms
from .models import WorkSample, Service

INPUT = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm'
TEXTAREA = 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm'


class WorkSampleForm(forms.ModelForm):
    class Meta:
        model = WorkSample
        fields = ['title', 'description', 'image', 'is_featured', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': INPUT}),
            'description': forms.Textarea(attrs={'class': TEXTAREA, 'rows': 4}),
        }


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['title', 'description', 'image', 'features', 'order', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': INPUT}),
            'description': forms.Textarea(attrs={'class': TEXTAREA, 'rows': 3}),
            'features': forms.Textarea(attrs={
                'class': TEXTAREA, 'rows': 5,
                'placeholder': 'One feature per line:\nHigh precision machining\nTolerances ±0.01mm'
            }),
            'order': forms.NumberInput(attrs={'class': INPUT}),
        }
