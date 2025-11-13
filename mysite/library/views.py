from django.contrib import messages
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .data_sources import (
    DATA_SOURCE_MONGO,
    DATA_SOURCE_SQL,
    get_active_data_source,
    set_active_data_source,
)
from .forms import (
    BookForm,
    LoanForm,
    LoanReturnForm,
    MongoBookForm,
    MongoLoanForm,
    MongoRatingForm,
    RatingForm,
)
from .models import Book, LibraryUser, Loan, Rating
from .mongo_repository import MongoUnavailableError, mongo_repository


def _parse_sql_id(raw_id):
    if isinstance(raw_id, int):
        return raw_id
    if isinstance(raw_id, str) and raw_id.isdigit():
        return int(raw_id)
    raise Http404('Identificador inválido')


def _fallback_to_sql(request, exc: Exception) -> str:
    messages.error(
        request,
        f'No se pudo usar MongoDB: {exc}. Cambiamos automáticamente a SQLite.',
    )
    set_active_data_source(request, DATA_SOURCE_SQL)
    return DATA_SOURCE_SQL


@require_POST
def change_data_source(request):
    source = request.POST.get('source')
    if source not in (DATA_SOURCE_SQL, DATA_SOURCE_MONGO):
        return HttpResponseBadRequest('Fuente inválida')
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('lista_libros')
    if source == DATA_SOURCE_MONGO and not mongo_repository.is_available():
        messages.error(
            request,
            'MongoDB no está disponible. Instala `pymongo` y asegúrate de tener el servidor ejecutándose.',
        )
        return redirect(next_url)
    set_active_data_source(request, source)
    label = 'MongoDB' if source == DATA_SOURCE_MONGO else 'SQLite'
    messages.info(request, f'Se cambió la fuente de datos a {label}.')
    return redirect(next_url)


def book_list(request):
    data_source = get_active_data_source(request)
    books = None
    if data_source == DATA_SOURCE_MONGO:
        try:
            books = mongo_repository.list_books()
        except MongoUnavailableError as exc:
            data_source = _fallback_to_sql(request, exc)
    if data_source == DATA_SOURCE_SQL:
        books = Book.objects.select_related('author').all()
    return render(
        request,
        'library/book_list.html',
        {
            'books': books,
            'using_mongo': data_source == DATA_SOURCE_MONGO,
        },
    )


def book_detail(request, libro_id):
    data_source = get_active_data_source(request)
    book = None
    active_loan = None
    loan_history = []
    if data_source == DATA_SOURCE_MONGO:
        try:
            book, active_loan, loan_history = mongo_repository.get_book_detail(libro_id)
        except MongoUnavailableError as exc:
            data_source = _fallback_to_sql(request, exc)
    if data_source == DATA_SOURCE_SQL:
        book = get_object_or_404(Book.objects.select_related('author'), pk=_parse_sql_id(libro_id))
        active_loan = book.loans.select_related('user').filter(returned=False).first()
        loan_history = book.loans.select_related('user').all()
    return render(
        request,
        'library/book_detail.html',
        {
            'book': book,
            'active_loan': active_loan,
            'loan_history': loan_history,
        },
    )


def book_create(request):
    data_source = get_active_data_source(request)
    form = None
    if data_source == DATA_SOURCE_MONGO:
        try:
            author_choices = mongo_repository.author_choices()
            form = MongoBookForm(request.POST or None, author_choices=author_choices)
            if request.method == 'POST' and form.is_valid():
                book_id = mongo_repository.create_book(form.cleaned_data)
                messages.success(request, 'Libro creado correctamente en MongoDB.')
                return redirect('detalle_libro', libro_id=book_id)
        except MongoUnavailableError as exc:
            data_source = _fallback_to_sql(request, exc)
    if data_source == DATA_SOURCE_SQL:
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
    data_source = get_active_data_source(request)
    form = None
    if data_source == DATA_SOURCE_MONGO:
        try:
            book = mongo_repository.get_book(libro_id)
            author_choices = mongo_repository.author_choices()
            initial = {'title': book.title, 'year': book.year, 'author': book.author.id}
            form = MongoBookForm(request.POST or None, author_choices=author_choices, initial=initial)
            if request.method == 'POST' and form.is_valid():
                mongo_repository.update_book(book.id, form.cleaned_data)
                messages.success(request, 'Cambios guardados en MongoDB.')
                return redirect('detalle_libro', libro_id=book.id)
        except MongoUnavailableError as exc:
            data_source = _fallback_to_sql(request, exc)
    if data_source == DATA_SOURCE_SQL:
        book = get_object_or_404(Book, pk=_parse_sql_id(libro_id))
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
    data_source = get_active_data_source(request)
    form = None
    book = None
    if data_source == DATA_SOURCE_MONGO:
        try:
            book = mongo_repository.get_book(libro_id)
            if request.method != 'POST' and book.is_loaned():
                messages.warning(
                    request,
                    'Este libro ya está prestado. Debe devolverse antes de registrar un nuevo préstamo.',
                )
            user_choices = mongo_repository.user_choices()
            form = MongoLoanForm(request.POST or None, user_choices=user_choices)
            if request.method == 'POST' and form.is_valid():
                try:
                    mongo_repository.create_loan(book.id, form.cleaned_data)
                except ValueError as exc:
                    form.add_error(None, str(exc))
                else:
                    messages.success(request, 'Préstamo registrado en MongoDB.')
                    return redirect('detalle_libro', libro_id=book.id)
        except MongoUnavailableError as exc:
            data_source = _fallback_to_sql(request, exc)
    if data_source == DATA_SOURCE_SQL:
        book = get_object_or_404(Book, pk=_parse_sql_id(libro_id))
        if request.method != 'POST' and book.is_loaned():
            messages.warning(
                request,
                'Este libro ya está prestado. Debe devolverse antes de registrar un nuevo préstamo.',
            )
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
    data_source = get_active_data_source(request)
    user = None
    loans = []
    if data_source == DATA_SOURCE_MONGO:
        try:
            user = mongo_repository.get_user(usuario_id)
            loans = mongo_repository.list_user_loans(usuario_id)
        except MongoUnavailableError as exc:
            data_source = _fallback_to_sql(request, exc)
    if data_source == DATA_SOURCE_SQL:
        user = get_object_or_404(LibraryUser, pk=_parse_sql_id(usuario_id))
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
    data_source = get_active_data_source(request)
    loan = None
    form = None
    if data_source == DATA_SOURCE_MONGO:
        try:
            loan = mongo_repository.get_loan(prestamo_id)
            if loan.returned:
                return redirect('detalle_libro', libro_id=loan.book.id)
            if request.method == 'POST':
                form = LoanReturnForm(request.POST)
                if form.is_valid() and form.cleaned_data['confirm']:
                    mongo_repository.mark_loan_returned(loan.id)
                    messages.success(request, 'Préstamo marcado como devuelto.')
                    return redirect('detalle_libro', libro_id=loan.book.id)
            else:
                form = LoanReturnForm(initial={'confirm': True})
        except MongoUnavailableError as exc:
            data_source = _fallback_to_sql(request, exc)
    if data_source == DATA_SOURCE_SQL:
        loan = get_object_or_404(Loan.objects.select_related('book'), pk=_parse_sql_id(prestamo_id))
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
    data_source = get_active_data_source(request)
    form = None
    if data_source == DATA_SOURCE_MONGO:
        try:
            form = MongoRatingForm(request.POST or None)
            if request.method == 'POST' and form.is_valid():
                mongo_repository.create_rating(form.cleaned_data)
                messages.success(request, 'Calificación registrada correctamente (MongoDB).')
                return redirect('lista_calificaciones')
        except MongoUnavailableError as exc:
            data_source = _fallback_to_sql(request, exc)
    if data_source == DATA_SOURCE_SQL:
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
    data_source = get_active_data_source(request)
    ratings = []
    if data_source == DATA_SOURCE_MONGO:
        try:
            ratings = mongo_repository.list_ratings()
        except MongoUnavailableError as exc:
            data_source = _fallback_to_sql(request, exc)
    if data_source == DATA_SOURCE_SQL:
        ratings = Rating.objects.all()
    return render(request, 'library/rating_list.html', {'ratings': ratings})
