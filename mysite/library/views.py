from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BookForm, LoanForm, LoanReturnForm, RatingForm
from .models import Book, LibraryUser, Loan, Rating


def book_list(request):
    books = Book.objects.select_related('author').all()
    return render(request, 'library/book_list.html', {'books': books})


def book_detail(request, libro_id):
    book = get_object_or_404(Book.objects.select_related('author'), pk=libro_id)
    active_loan = book.loans.select_related('user').filter(returned=False).first()
    return render(
        request,
        'library/book_detail.html',
        {
            'book': book,
            'active_loan': active_loan,
            'loan_history': book.loans.select_related('user').all(),
        },
    )


def book_create(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save()
            messages.success(request, 'Libro creado correctamente.')
            return redirect('detalle_libro', libro_id=book.pk)
    else:
        form = BookForm()
    return render(request, 'library/book_form.html', {'form': form, 'action': 'Crear libro'})


def book_edit(request, libro_id):
    book = get_object_or_404(Book, pk=libro_id)
    if request.method == 'POST':
        form = BookForm(request.POST, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cambios guardados.')
            return redirect('detalle_libro', libro_id=book.pk)
    else:
        form = BookForm(instance=book)
    return render(request, 'library/book_form.html', {'form': form, 'action': 'Editar libro'})


def loan_create(request, libro_id):
    book = get_object_or_404(Book, pk=libro_id)
    if request.method != 'POST' and book.is_loaned():
        messages.warning(request, 'Este libro ya está prestado. Debe devolverse antes de registrar un nuevo préstamo.')
    if request.method == 'POST':
        form = LoanForm(request.POST, book=book)
        if form.is_valid():
            form.save()
            messages.success(request, 'Préstamo registrado.')
            return redirect('detalle_libro', libro_id=book.pk)
    else:
        form = LoanForm(book=book)
    return render(
        request,
        'library/loan_form.html',
        {
            'form': form,
            'book': book,
        },
    )


def user_loans(request, usuario_id):
    user = get_object_or_404(LibraryUser, pk=usuario_id)
    loans = user.loans.select_related('book', 'book__author').all()
    return render(
        request,
        'library/user_loans.html',
        {
            'user': user,
            'loans': loans,
        },
    )


def loan_return(request, prestamo_id):
    loan = get_object_or_404(Loan.objects.select_related('book'), pk=prestamo_id)
    if loan.returned:
        return redirect('detalle_libro', libro_id=loan.book_id)

    if request.method == 'POST':
        form = LoanReturnForm(request.POST)
        if form.is_valid() and form.cleaned_data['confirm']:
            loan.returned = True
            loan.full_clean()
            loan.save()
            messages.success(request, 'Préstamo marcado como devuelto.')
            return redirect('detalle_libro', libro_id=loan.book_id)
    else:
        form = LoanReturnForm(initial={'confirm': True})

    return render(
        request,
        'library/loan_return.html',
        {
            'form': form,
            'loan': loan,
        },
    )
def rating_create(request):
    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Calificación registrada correctamente.')
            return redirect('lista_calificaciones')
    else:
        form = RatingForm()
    return render(request, 'library/rating_form.html', {'form': form, 'action': 'Registrar calificación'})

def rating_list(request):
    ratings = Rating.objects.all()
    return render(request, 'library/rating_list.html', {'ratings': ratings})