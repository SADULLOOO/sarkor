from catalog.models import Category, District
from tasks.models import Task
from users.models import User

_phone_counter = iter(range(100000000, 999999999))


def make_user(**kwargs):
    kwargs.setdefault("name", "Test user")
    return User.objects.create_user(f"+992{next(_phone_counter)}", **kwargs)


def make_task(customer=None, **kwargs):
    kwargs.setdefault("category", Category.objects.get(slug="plumbing"))
    kwargs.setdefault("district", District.objects.get(slug="sino"))
    kwargs.setdefault("description", "Fix the kitchen tap")
    kwargs.setdefault("address", "Rudaki 10, apt 5")
    return Task.objects.create(customer=customer or make_user(is_customer=True), **kwargs)
