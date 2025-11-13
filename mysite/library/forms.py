from django import forms

from .models import Book, Loan, Rating


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'year', 'author']


class LoanForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.book = kwargs.pop('book', None)
        super().__init__(*args, **kwargs)
        if self.book:
            # Ensure the model instance knows about the related book during form validation.
            self.instance.book = self.book

    class Meta:
        model = Loan
        fields = ['user', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'La fecha de fin no puede ser anterior a la fecha de inicio.')

        book = self.book or self.instance.book
        if book and book.is_loaned():
            loan_instance = getattr(self, 'instance', None)
            loan_is_active = not loan_instance or not loan_instance.returned
            if loan_is_active:
                raise forms.ValidationError('El libro ya está prestado.')
        return cleaned_data

    def save(self, commit=True):
        loan = super().save(commit=False)
        if self.book:
            loan.book = self.book
        loan.returned = False
        if commit:
            loan.full_clean()
            loan.save()
        return loan


class LoanReturnForm(forms.Form):
    confirm = forms.BooleanField(widget=forms.HiddenInput(), initial=True)


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['name', 'comments', 'rating']
        widgets = {
            'comments': forms.Textarea(attrs={'rows': 4}),
        }


class MongoBookForm(forms.Form):
    title = forms.CharField(label='Título', max_length=200)
    year = forms.IntegerField(label='Año', min_value=0)
    author = forms.ChoiceField(label='Autor')

    def __init__(self, *args, author_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['author'].choices = author_choices or []


class MongoLoanForm(forms.Form):
    user = forms.ChoiceField(label='Usuario')
    start_date = forms.DateField(label='Inicio', widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(label='Fin', widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, user_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].choices = user_choices or []

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        if start and end and end < start:
            self.add_error('end_date', 'La fecha de fin no puede ser anterior a la fecha de inicio.')
        return cleaned_data


class MongoRatingForm(forms.Form):
    name = forms.CharField(label='Nombre', max_length=100)
    comments = forms.CharField(
        label='Comentarios',
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
    )
    rating = forms.ChoiceField(
        label='Calificación',
        choices=[(str(i), f'{i}') for i in range(1, 11)],
    )

    def clean_rating(self):
        value = self.cleaned_data['rating']
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise forms.ValidationError('Calificación inválida') from exc
