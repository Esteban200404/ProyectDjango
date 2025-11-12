from django.urls import path

from . import views

urlpatterns = [
    path('', views.book_list, name='lista_libros'),
    path('libros/nuevo/', views.book_create, name='nuevo_libro'),
    path('libros/<int:libro_id>/', views.book_detail, name='detalle_libro'),
    path('libros/<int:libro_id>/editar/', views.book_edit, name='editar_libro'),
    path('libros/<int:libro_id>/prestar/', views.loan_create, name='prestar_libro'),
    path('prestamos/<int:prestamo_id>/devolver/', views.loan_return, name='devolver_prestamo'),
    path('usuarios/<int:usuario_id>/prestamos/', views.user_loans, name='prestamos_usuario'),
    path('calificaciones/', views.rating_list, name='lista_calificaciones'),
    path('calificaciones/nueva/', views.rating_create, name='nueva_calificacion'),

]
