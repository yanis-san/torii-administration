from django import forms
from .models import CourseSession


class CourseSessionForm(forms.ModelForm):
    """Formulaire pour créer/modifier une séance de cours"""
    
    class Meta:
        model = CourseSession
        fields = ['date', 'start_time', 'end_time', 'teacher', 'classroom', 'status', 'duration_override_minutes', 'teacher_hourly_rate_override', 'note']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
            }),
            'start_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
            }),
            'end_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
            }),
            'teacher': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
            }),
            'classroom': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
            }),
            'duration_override_minutes': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent',
                'placeholder': 'Ex: 90 (optionnel)'
            }),
            'teacher_hourly_rate_override': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent',
                'placeholder': 'Ex: 2500 (optionnel)'
            }),
            'note': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent',
                'rows': 2,
                'placeholder': 'Notes facultatives...'
            }),
        }
        labels = {
            'date': 'Date (optionnel)',
            'start_time': 'Heure de début (optionnel)',
            'end_time': 'Heure de fin (optionnel)',
            'teacher': 'Professeur',
            'classroom': 'Salle',
            'status': 'Statut',
            'duration_override_minutes': 'Durée personnalisée (minutes)',
            'teacher_hourly_rate_override': 'Tarif spécifique (DA/h)',
            'note': 'Notes',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre date, start_time et end_time non-obligatoires
        self.fields['date'].required = False
        self.fields['start_time'].required = False
        self.fields['end_time'].required = False
