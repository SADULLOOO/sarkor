from django.db import migrations

DISTRICTS = [
    ("sino", "Сино", "Сино"),
    ("firdavsi", "Фирдавсӣ", "Фирдавси"),
    ("shohmansur", "Шоҳмансур", "Шохмансур"),
    ("somoni", "Исмоили Сомонӣ", "Исмоили Сомони"),
]

# slug, icon, name_tg, name_ru
CATEGORIES = [
    ("plumbing", "faucet", "Сантехник", "Сантехник"),
    ("electrician", "plug", "Электрик", "Электрик"),
    ("repair", "hammer", "Таъмири хона", "Ремонт квартиры"),
    ("cleaning", "broom", "Тозакунӣ", "Уборка"),
    ("moving", "truck", "Боркашон ва кӯчонидан", "Грузчики и переезд"),
    ("delivery", "package", "Расонидан", "Доставка"),
    ("furniture", "sofa", "Васл кардани мебел", "Сборка мебели"),
    ("appliances", "washing-machine", "Таъмири техника", "Ремонт техники"),
    ("handyman", "wrench", "Усто барои корҳои хурд", "Мастер на час"),
    ("tutoring", "book", "Омӯзгори хусусӣ", "Репетиторы"),
    ("auto", "car", "Ёрии автомобилӣ", "Автопомощь"),
    ("other", "dots", "Дигар", "Другое"),
]


def load_data(apps, schema_editor):
    District = apps.get_model("catalog", "District")
    Category = apps.get_model("catalog", "Category")

    for position, (slug, name_tg, name_ru) in enumerate(DISTRICTS):
        District.objects.update_or_create(
            slug=slug, defaults={"name_tg": name_tg, "name_ru": name_ru, "position": position}
        )

    for position, (slug, icon, name_tg, name_ru) in enumerate(CATEGORIES):
        Category.objects.update_or_create(
            slug=slug,
            defaults={"icon": icon, "name_tg": name_tg, "name_ru": name_ru, "position": position},
        )


def remove_data(apps, schema_editor):
    apps.get_model("catalog", "District").objects.filter(slug__in=[d[0] for d in DISTRICTS]).delete()
    apps.get_model("catalog", "Category").objects.filter(slug__in=[c[0] for c in CATEGORIES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(load_data, remove_data),
    ]
