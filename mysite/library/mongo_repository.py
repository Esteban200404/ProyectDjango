from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from django.conf import settings
from django.http import Http404

try:
    from bson import ObjectId
    from bson.errors import InvalidId
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
except ImportError:  # pragma: no cover - handled at runtime
    ObjectId = None  # type: ignore
    InvalidId = Exception  # type: ignore
    MongoClient = None  # type: ignore
    PyMongoError = Exception  # type: ignore


class MongoUnavailableError(RuntimeError):
    """Raised when MongoDB backend cannot be used."""

    pass


@dataclass
class MongoAuthor:
    id: str
    name: str


@dataclass
class MongoUser:
    id: str
    name: str
    email: str = ''


@dataclass
class MongoBook:
    id: str
    title: str
    year: Optional[int]
    author: MongoAuthor
    _is_loaned: bool = False

    def is_loaned(self) -> bool:
        return self._is_loaned


@dataclass
class MongoLoan:
    id: str
    user: MongoUser
    start_date: str
    end_date: str
    returned: bool
    book: Optional[MongoBook] = None


@dataclass
class MongoRating:
    id: str
    name: str
    comments: str
    rating: int
    created_at: datetime


def _safe_title(doc: dict) -> str:
    return doc.get('title') or 'Sin título'


class MongoDataSource:
    def __init__(self) -> None:
        self._client: Optional[MongoClient] = None

    def _require_client(self) -> MongoClient:
        if not self.is_available():  # pragma: no cover - import guard path
            raise MongoUnavailableError(
                'pymongo no está instalado. Ejecuta `pip install pymongo` para habilitar la fuente Mongo.'
            )
        if self._client is None:
            try:
                self._client = MongoClient(
                    settings.MONGO_URI,
                    serverSelectionTimeoutMS=3000,
                )
                # Force a quick ping to fail fast if the server is unreachable.
                self._client.admin.command('ping')
            except PyMongoError as exc:  # pragma: no cover - runtime guard
                self._client = None
                raise MongoUnavailableError(f'No se pudo conectar a MongoDB ({exc}).') from exc
        return self._client

    @property
    def db(self):
        return self._require_client()[settings.MONGO_DB_NAME]

    def is_available(self) -> bool:
        return MongoClient is not None

    def _object_id(self, raw_id: str) -> ObjectId:
        if ObjectId is None:  # pragma: no cover
            raise RuntimeError('pymongo no está disponible')
        try:
            return ObjectId(str(raw_id))
        except (InvalidId, TypeError):
            raise Http404('Identificador no válido')

    @staticmethod
    def _serialize_date(value) -> str:
        if not value:
            return ''
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _placeholder_book(title: str = 'Libro desconocido') -> MongoBook:
        return MongoBook(
            id='',
            title=title,
            year=None,
            author=MongoAuthor(id='', name='Autor desconocido'),
        )

    # ----- helpers -----
    def _authors_by_id(self, author_ids: Iterable[ObjectId]) -> Dict[str, MongoAuthor]:
        ids = [aid for aid in author_ids if aid]
        if not ids:
            return {}
        cursor = self.db.authors.find({'_id': {'$in': ids}})
        return {str(doc['_id']): MongoAuthor(id=str(doc['_id']), name=doc.get('name', 'Autor')) for doc in cursor}

    def _users_by_id(self, user_ids: Iterable[ObjectId]) -> Dict[str, MongoUser]:
        ids = [uid for uid in user_ids if uid]
        if not ids:
            return {}
        cursor = self.db.library_users.find({'_id': {'$in': ids}})
        return {
            str(doc['_id']): MongoUser(
                id=str(doc['_id']),
                name=doc.get('name', 'Usuario'),
                email=doc.get('email', ''),
            )
            for doc in cursor
        }

    def _loans_by_book(self, book_ids: Sequence[ObjectId]) -> Dict[str, List[MongoLoan]]:
        book_id_list = list(book_ids)
        if not book_id_list:
            return {}
        cursor = self.db.loans.find({'book_id': {'$in': book_id_list}})
        user_ids = {loan.get('user_id') for loan in cursor if loan.get('user_id')}
        cursor = self.db.loans.find({'book_id': {'$in': book_id_list}})
        users = self._users_by_id(user_ids)
        grouped: Dict[str, List[MongoLoan]] = defaultdict(list)
        for doc in cursor:
            book_id = str(doc['book_id'])
            grouped[book_id].append(
                MongoLoan(
                    id=str(doc['_id']),
                    user=users.get(str(doc.get('user_id')), MongoUser(id='', name='Usuario desconocido')),
                    start_date=doc.get('start_date', ''),
                    end_date=doc.get('end_date', ''),
                    returned=doc.get('returned', False),
                )
            )
        return grouped

    # ----- books -----
    def list_books(self) -> List[MongoBook]:
        docs = list(self.db.books.find({}))
        if not docs:
            return []
        author_map = self._authors_by_id([doc.get('author_id') for doc in docs if doc.get('author_id')])
        loan_map = self._loans_by_book([doc['_id'] for doc in docs])
        books: List[MongoBook] = []
        for doc in docs:
            book_id = str(doc['_id'])
            author = author_map.get(str(doc.get('author_id')), MongoAuthor(id='', name='Autor desconocido'))
            loans = loan_map.get(book_id, [])
            books.append(
                MongoBook(
                    id=book_id,
                    title=_safe_title(doc),
                    year=doc.get('year'),
                    author=author,
                    _is_loaned=any(not loan.returned for loan in loans),
                )
            )
        return books

    def get_book_detail(self, raw_book_id: str) -> Tuple[MongoBook, Optional[MongoLoan], List[MongoLoan]]:
        book_oid = self._object_id(raw_book_id)
        doc = self.db.books.find_one({'_id': book_oid})
        if not doc:
            raise Http404('Libro no encontrado')
        author_doc = None
        if doc.get('author_id'):
            author_doc = self.db.authors.find_one({'_id': doc['author_id']})
        author = (
            MongoAuthor(id=str(author_doc['_id']), name=author_doc.get('name', 'Autor'))
            if author_doc
            else MongoAuthor(id='', name='Autor desconocido')
        )
        loan_docs = list(self.db.loans.find({'book_id': book_oid}))
        user_ids = {loan.get('user_id') for loan in loan_docs if loan.get('user_id')}
        users = self._users_by_id(user_ids)
        loans: List[MongoLoan] = []
        active_loan: Optional[MongoLoan] = None
        book_summary = MongoBook(
            id=str(doc['_id']),
            title=_safe_title(doc),
            year=doc.get('year'),
            author=author,
        )
        for loan_doc in sorted(loan_docs, key=lambda value: value.get('start_date', ''), reverse=True):
            loan = MongoLoan(
                id=str(loan_doc['_id']),
                user=users.get(str(loan_doc.get('user_id')), MongoUser(id='', name='Usuario desconocido')),
                start_date=loan_doc.get('start_date', ''),
                end_date=loan_doc.get('end_date', ''),
                returned=loan_doc.get('returned', False),
                book=book_summary,
            )
            if not loan.returned and not active_loan:
                active_loan = loan
            loans.append(loan)
        book_summary._is_loaned = active_loan is not None
        return book_summary, active_loan, loans

    def get_book(self, raw_book_id: str) -> MongoBook:
        book, _, _ = self.get_book_detail(raw_book_id)
        return book

    def author_choices(self) -> List[Tuple[str, str]]:
        return [(str(doc['_id']), doc.get('name', 'Autor')) for doc in self.db.authors.find().sort('name')]

    def user_choices(self) -> List[Tuple[str, str]]:
        return [
            (str(doc['_id']), f"{doc.get('name', 'Usuario')} ({doc.get('email', 'sin email')})")
            for doc in self.db.library_users.find().sort('name')
        ]

    def create_book(self, data: dict) -> str:
        author_id = data.get('author')
        if not author_id:
            raise ValueError('El autor es obligatorio.')
        payload = {
            'title': data.get('title'),
            'year': int(data.get('year')) if data.get('year') else None,
            'author_id': self._object_id(author_id),
            'created_at': datetime.utcnow(),
        }
        result = self.db.books.insert_one(payload)
        return str(result.inserted_id)

    def update_book(self, raw_book_id: str, data: dict) -> None:
        book_oid = self._object_id(raw_book_id)
        updates = {
            'title': data.get('title'),
            'year': int(data.get('year')) if data.get('year') else None,
        }
        author_id = data.get('author')
        if author_id:
            updates['author_id'] = self._object_id(author_id)
        self.db.books.update_one({'_id': book_oid}, {'$set': updates})

    # ----- loans -----
    def create_loan(self, raw_book_id: str, data: dict) -> str:
        book_oid = self._object_id(raw_book_id)
        existing = self.db.loans.find_one({'book_id': book_oid, 'returned': False})
        if existing:
            raise ValueError('El libro ya está prestado.')
        user_id = data.get('user')
        if not user_id:
            raise ValueError('El usuario es obligatorio.')
        payload = {
            'book_id': book_oid,
            'user_id': self._object_id(user_id),
            'start_date': self._serialize_date(data.get('start_date')),
            'end_date': self._serialize_date(data.get('end_date')),
            'returned': False,
        }
        result = self.db.loans.insert_one(payload)
        return str(result.inserted_id)

    def get_user(self, raw_user_id: str) -> MongoUser:
        doc = self.db.library_users.find_one({'_id': self._object_id(raw_user_id)})
        if not doc:
            raise Http404('Usuario no encontrado')
        return MongoUser(id=str(doc['_id']), name=doc.get('name', 'Usuario'), email=doc.get('email', ''))

    def list_user_loans(self, raw_user_id: str) -> List[MongoLoan]:
        user = self.get_user(raw_user_id)
        cursor = self.db.loans.find({'user_id': self._object_id(raw_user_id)})
        book_ids = {doc['book_id'] for doc in cursor}
        cursor = self.db.loans.find({'user_id': self._object_id(raw_user_id)})
        books = self._books_by_id(book_ids)
        return [
            MongoLoan(
                id=str(doc['_id']),
                user=user,
                start_date=doc.get('start_date', ''),
                end_date=doc.get('end_date', ''),
                returned=doc.get('returned', False),
                book=books.get(
                    str(doc.get('book_id')),
                    self._placeholder_book(),
                ),
            )
            for doc in cursor
        ]

    def _books_by_id(self, book_ids: Iterable[ObjectId]) -> Dict[str, MongoBook]:
        ids = [bid for bid in book_ids if bid]
        if not ids:
            return {}
        cursor = self.db.books.find({'_id': {'$in': ids}})
        author_map = self._authors_by_id({doc.get('author_id') for doc in cursor if doc.get('author_id')})
        cursor = self.db.books.find({'_id': {'$in': ids}})
        books = {}
        for doc in cursor:
            author = author_map.get(str(doc.get('author_id')), MongoAuthor(id='', name='Autor'))
            books[str(doc['_id'])] = MongoBook(
                id=str(doc['_id']),
                title=_safe_title(doc),
                year=doc.get('year'),
                author=author,
            )
        return books

    def get_loan(self, raw_loan_id: str) -> MongoLoan:
        loan_oid = self._object_id(raw_loan_id)
        doc = self.db.loans.find_one({'_id': loan_oid})
        if not doc:
            raise Http404('Préstamo no encontrado')
        user = self.get_user(str(doc.get('user_id')))
        book = self.get_book(str(doc.get('book_id')))
        return MongoLoan(
            id=str(doc['_id']),
            user=user,
            start_date=doc.get('start_date', ''),
            end_date=doc.get('end_date', ''),
            returned=doc.get('returned', False),
            book=book,
        )

    def mark_loan_returned(self, raw_loan_id: str) -> None:
        loan_oid = self._object_id(raw_loan_id)
        self.db.loans.update_one({'_id': loan_oid}, {'$set': {'returned': True}})

    # ----- ratings -----
    def list_ratings(self) -> List[MongoRating]:
        docs = self.db.ratings.find().sort('created_at', -1)
        return [
            MongoRating(
                id=str(doc['_id']),
                name=doc.get('name', ''),
                comments=doc.get('comments', ''),
                rating=int(doc.get('rating', 0)),
                created_at=doc.get('created_at', datetime.utcnow()),
            )
            for doc in docs
        ]

    def create_rating(self, data: dict) -> str:
        payload = {
            'name': data.get('name'),
            'comments': data.get('comments', ''),
            'rating': int(data.get('rating')),
            'created_at': datetime.utcnow(),
        }
        result = self.db.ratings.insert_one(payload)
        return str(result.inserted_id)


mongo_repository = MongoDataSource()
