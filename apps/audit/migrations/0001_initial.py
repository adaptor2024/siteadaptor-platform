from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("tenant_schema", models.CharField(blank=True, db_index=True, max_length=100)),
                (
                    "actor_type",
                    models.CharField(
                        choices=[
                            ("user", "User"),
                            ("system", "System"),
                            ("cron", "Cron"),
                            ("integration", "Integration"),
                        ],
                        default="system",
                        max_length=20,
                    ),
                ),
                ("actor_id", models.CharField(blank=True, max_length=100)),
                ("actor_display", models.CharField(blank=True, max_length=200)),
                ("action", models.CharField(db_index=True, max_length=100)),
                ("resource_type", models.CharField(db_index=True, max_length=50)),
                ("resource_id", models.CharField(db_index=True, max_length=100)),
                ("changes", models.JSONField(blank=True, default=dict)),
                ("diff_summary", models.TextField(blank=True)),
                ("context", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(
                fields=["resource_type", "resource_id"], name="audit_resource_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(
                fields=["tenant_schema", "-created_at"], name="audit_tenant_created_idx"
            ),
        ),
    ]
