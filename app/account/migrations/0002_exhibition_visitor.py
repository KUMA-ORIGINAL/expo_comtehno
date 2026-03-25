# Generated manually for ExhibitionVisitor

import phonenumber_field.modelfields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExhibitionVisitor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_name', models.CharField(max_length=150, verbose_name='Фамилия')),
                ('first_name', models.CharField(max_length=150, verbose_name='Имя')),
                ('middle_name', models.CharField(blank=True, max_length=150, verbose_name='Отчество')),
                ('phone_number', phonenumber_field.modelfields.PhoneNumberField(max_length=128, region='KG', verbose_name='Мобильный телефон')),
                ('city', models.CharField(max_length=200, verbose_name='Город')),
                ('company', models.CharField(max_length=300, verbose_name='Компания')),
                ('exhibition_theme', models.CharField(choices=[('construction', 'Строительная индустрия'), ('energy', 'Энергетика и освещение'), ('security', 'Безопасность'), ('special_tech', 'Спецтехника')], max_length=50, verbose_name='Тематика выставки')),
                ('industry', models.CharField(choices=[('government', 'Государственный орган министерство/агентство/гос сектор'), ('construction', 'Строительная компания'), ('production', 'Производственная компания'), ('electric', 'Электроэнергетическая компания'), ('business_services', 'Услуги для бизнеса'), ('trade', 'Торговая компания (Дистрибьютор, и т.п.)'), ('education', 'Профессиональное учебное заведение'), ('transport', 'Транспортная компания'), ('nonprofit', 'Некоммерческая организация'), ('other', 'Другое')], max_length=50, verbose_name='Сфера деятельности организации')),
                ('position', models.CharField(choices=[('owner', 'Собственник'), ('ceo', 'Генеральный директор'), ('director', 'Директор (коммерческий, технический, исполнительный)'), ('foreman', 'Прораб'), ('chief_engineer', 'Главный инженер'), ('chief_specialist', 'Главный специалист'), ('electrical_engineer', 'Инженер электрических сетей'), ('procurement', 'Специалист отдела закупок'), ('manager', 'Менеджер'), ('designer', 'Проектировщик'), ('architect', 'Архитектор'), ('designer_interior', 'Дизайнер'), ('other', 'Другое')], max_length=50, verbose_name='Должность в организации')),
                ('visit_purposes', models.JSONField(default=list, help_text='Список выбранных целей', verbose_name='Цель посещения выставки')),
                ('source', models.CharField(choices=[('outdoor', 'Наружная реклама по городу'), ('internet', 'Реклама в Интернете'), ('social', 'Фэйсбук/Инстаграм'), ('tv', 'Телевидение'), ('radio', 'Радио'), ('call_center', 'Колл-центр'), ('invitation', 'Письмо с приглашением от организаторов'), ('flyer', 'Листовка'), ('friends', 'От друзей/коллег'), ('other', 'Другое')], max_length=50, verbose_name='Откуда узнали о выставке')),
                ('personal_data_consent', models.BooleanField(default=False, verbose_name='Согласие на обработку персональных данных')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата регистрации')),
            ],
            options={
                'verbose_name': 'Посетитель выставки',
                'verbose_name_plural': 'Посетители выставки',
                'ordering': ['-created_at'],
            },
        ),
    ]
