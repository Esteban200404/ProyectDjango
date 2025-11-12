from django.core.exceptions import ValidationError
from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200)
    year = models.PositiveIntegerField()
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')

    class Meta:
        ordering = ['title']

    def __str__(self) -> str:
        return f'{self.title} ({self.year})'

    def is_loaned(self) -> bool:
        """Return True if the book has an active loan that has not been marked as returned."""
        return self.loans.filter(returned=False).exists()


class LibraryUser(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return f'{self.name} <{self.email}>'


class Loan(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='loans')
    user = models.ForeignKey(LibraryUser, on_delete=models.CASCADE, related_name='loans')
    start_date = models.DateField()
    end_date = models.DateField()
    returned = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_date']

    def __str__(self) -> str:
        status = 'Devuelto' if self.returned else 'En préstamo'
        return f'{self.book.title} → {self.user.name} ({status})'

    def clean(self):
        """Simple validations to keep the domain rules in one place."""
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'La fecha de fin no puede ser anterior a la fecha de inicio.'})

        if self.book and not self.returned:
            active_loans = Loan.objects.filter(book=self.book, returned=False)
            if self.pk:
                active_loans = active_loans.exclude(pk=self.pk)
            if active_loans.exists():
                raise ValidationError({'book': 'El libro ya está prestado.'})

class Rating(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre")
    comments = models.TextField(blank=True, verbose_name="Comentarios")
    rating = models.PositiveIntegerField(
        choices=[(i, str(i)) for i in range(1, 11)],
        verbose_name="Calificación (1-10)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Calificación"
        verbose_name_plural = "Calificaciones"

    def __str__(self):
        return f"{self.name} - {self.rating}/10"