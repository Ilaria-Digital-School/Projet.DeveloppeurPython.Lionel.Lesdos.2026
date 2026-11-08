"""
Factories factory-boy pour la génération de données de test.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

import factory

from core.extensions import db
from core.models.account import Account
from core.models.budget import Budget
from core.models.category import Category
from core.models.transactions import Transaction
from core.models.user import User


class BaseFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        abstract = True
        sqlalchemy_session = None  # sera injecté dynamiquement

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        session = db.session
        obj = model_class(*args, **kwargs)
        session.add(obj)
        session.flush()
        return obj


class UserFactory(BaseFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    password_hash = factory.LazyFunction(lambda: "pbkdf2:sha256:600000$test$fakehash")
    is_active = True
    email_verified = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", None)
        obj = super()._create(model_class, *args, **kwargs)
        if password:
            obj.password = password
        return obj


class AccountFactory(BaseFactory):
    class Meta:
        model = Account

    user_id = factory.LazyAttribute(lambda o: UserFactory().id)
    name = factory.Sequence(lambda n: f"Compte Test {n}")
    account_type = "courant"
    balance = Decimal("1000.00")
    currency = "EUR"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override pour gérer le __init__ custom d'Account."""
        session = db.session
        obj = model_class(**kwargs)
        session.add(obj)
        session.flush()
        return obj


class CategoryFactory(BaseFactory):
    class Meta:
        model = Category

    user_id = factory.LazyAttribute(lambda o: UserFactory().id)
    name = factory.Sequence(lambda n: f"Catégorie {n}")
    description = "Catégorie de test"
    color = "#6c757d"
    icon = "fa-tag"
    is_expense = True
    category_type = "expense"


class TransactionFactory(BaseFactory):
    class Meta:
        model = Transaction

    user_id = factory.LazyAttribute(lambda o: UserFactory().id)
    account_id = factory.LazyAttribute(lambda o: AccountFactory(user_id=o.user_id).id)
    montant = Decimal("50.00")
    type_transaction = "achat"
    libelle = factory.Sequence(lambda n: f"Transaction test {n}")
    date_heure_transaction = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    statut = "comptabilise"
    devise = "EUR"


class BudgetFactory(BaseFactory):
    class Meta:
        model = Budget

    user_id = factory.LazyAttribute(lambda o: UserFactory().id)
    category_id = factory.LazyAttribute(lambda o: CategoryFactory(user_id=o.user_id).id)
    amount = Decimal("500.00")
    period = "monthly"
    start_date = factory.LazyFunction(lambda: date.today().replace(day=1))
    end_date = factory.LazyFunction(lambda: date.today().replace(day=28))
