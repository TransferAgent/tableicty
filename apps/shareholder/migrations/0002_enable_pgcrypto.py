from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shareholder', '0001_initial'),
    ]
    
    operations = [
        migrations.RunSQL(
            sql='CREATE EXTENSION IF NOT EXISTS pgcrypto;',
            reverse_sql='DROP EXTENSION IF EXISTS pgcrypto;'
        ),
    ]
