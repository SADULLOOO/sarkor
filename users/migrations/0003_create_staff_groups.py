from django.contrib.auth.management import create_permissions
from django.db import migrations

GROUP_PERMISSIONS = {
    "Moderator": ["view_user", "change_user"],
    "Admin": ["view_user", "add_user", "change_user", "delete_user"],
}


def create_groups(apps, schema_editor):
    # On a fresh database permissions are created only after all migrations,
    # so make sure they exist before we look them up.
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    for name, codenames in GROUP_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=name)
        permissions = Permission.objects.filter(content_type__app_label="users", codename__in=codenames)
        group.permissions.add(*permissions)


def delete_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=GROUP_PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("users", "0002_alter_user_phone_alter_user_trust_level"),
    ]

    operations = [
        migrations.RunPython(create_groups, delete_groups),
    ]
