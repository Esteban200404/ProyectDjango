from django.contrib import admin

from .models import Author, Book, LibraryUser, Loan


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'year')
    list_filter = ('author', 'year')
    search_fields = ('title',)


@admin.register(LibraryUser)
class LibraryUserAdmin(admin.ModelAdmin):
    list_display = ('name', 'email')
    search_fields = ('name', 'email')


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'start_date', 'end_date', 'returned')
    list_filter = ('returned', 'start_date')
    autocomplete_fields = ('book', 'user')
