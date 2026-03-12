# Generated manually - create audit tables that were missed

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_alertrule_alertevent'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('running', 'Em Execução'), ('done', 'Concluído'), ('error', 'Erro')], default='running', max_length=10)),
                ('business_summary', models.TextField(blank=True, verbose_name='Resumo do Negócio')),
                ('overall_score', models.IntegerField(blank=True, null=True, verbose_name='Score Geral (0-100)')),
                ('overall_analysis', models.TextField(blank=True, verbose_name='Análise Geral')),
                ('raw_data_snapshot', models.JSONField(blank=True, default=dict, verbose_name='Snapshot dos Dados')),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('duration_seconds', models.FloatField(blank=True, null=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_reports', to='core.project', verbose_name='Projeto')),
            ],
            options={
                'verbose_name': 'Relatório de Auditoria IA',
                'verbose_name_plural': 'Relatórios de Auditoria IA',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AuditRecommendation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('platform', models.CharField(choices=[('google_ads', 'Google Ads'), ('meta_ads', 'Meta Ads'), ('seo', 'SEO / GSC'), ('general', 'Geral')], max_length=20)),
                ('category', models.CharField(choices=[('negative_keywords', 'Palavras-Chave Negativas'), ('sitelinks', 'Sitelinks'), ('callouts', 'Callouts / Extensões'), ('ad_copy', 'Texto do Anúncio'), ('bidding', 'Estratégia de Lances'), ('targeting', 'Segmentação de Público'), ('audience_age', 'Faixa Etária'), ('audience_interests', 'Interesses'), ('audience_geo', 'Geolocalização'), ('ad_schedule', 'Agendamento'), ('keywords', 'Palavras-Chave'), ('quality_score', 'Quality Score'), ('campaign_structure', 'Estrutura de Campanha'), ('creative', 'Criativos'), ('landing_page', 'Landing Page'), ('conversion_tracking', 'Rastreamento de Conversão'), ('indexing', 'Indexação'), ('content_gap', 'Gap de Conteúdo'), ('other', 'Outro')], default='other', max_length=30)),
                ('impact', models.CharField(choices=[('critical', 'Crítico'), ('high', 'Alto'), ('medium', 'Médio'), ('low', 'Baixo')], default='medium', max_length=10)),
                ('title', models.CharField(max_length=300, verbose_name='Título')),
                ('explanation', models.TextField(verbose_name='Explicação Detalhada')),
                ('action_description', models.TextField(blank=True, verbose_name='Ação Proposta')),
                ('action_payload', models.JSONField(blank=True, default=dict, help_text='Dados estruturados para execução automática', verbose_name='Payload da Ação')),
                ('can_auto_apply', models.BooleanField(default=False, verbose_name='Aplicável Automaticamente')),
                ('status', models.CharField(choices=[('pending', 'Pendente'), ('applied', 'Aplicado'), ('dismissed', 'Descartado'), ('failed', 'Falhou')], default='pending', max_length=10)),
                ('apply_result', models.JSONField(blank=True, default=dict, verbose_name='Resultado da Aplicação')),
                ('applied_at', models.DateTimeField(blank=True, null=True)),
                ('campaign_id', models.CharField(blank=True, max_length=100, verbose_name='ID da Campanha')),
                ('campaign_name', models.CharField(blank=True, max_length=300, verbose_name='Nome da Campanha')),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recommendations', to='core.auditreport', verbose_name='Relatório')),
            ],
            options={
                'verbose_name': 'Recomendação de Auditoria',
                'verbose_name_plural': 'Recomendações de Auditoria',
                'ordering': ['report', 'impact', 'platform'],
            },
        ),
    ]
