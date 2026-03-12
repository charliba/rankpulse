from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat_support", "0005_add_feedback_image_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="feedbacklog",
            name="email",
            field=models.EmailField(
                blank=True,
                help_text="E-mail do remetente (útil para anônimos)",
                max_length=254,
            ),
        ),
    ]
