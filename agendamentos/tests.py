"""Testes das regras principais de reservas e gestão de laboratórios."""

from datetime import timedelta, time
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import AgendamentoForm
from .models import Agendamento, Laboratorio
from .views import _criar_relatorio_excel
from io import BytesIO
from openpyxl import load_workbook


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class ReservasTestes(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.professor = User.objects.create_user(
            username='professor_teste', password='senha-teste', email='prof@example.org'
        )
        cls.chefe = User.objects.create_user(username='chefe_teste', password='senha-teste')
        cls.chefe.perfil.tipo = 'chefe_ti'
        cls.chefe.perfil.save()
        cls.laboratorio = Laboratorio.objects.create(nome='Labin Teste', capacidade=40)
        cls.data = timezone.localdate() + timedelta(days=7)
        if cls.data.weekday() == 6:
            cls.data += timedelta(days=1)

    def dados_reserva(self, turno='matutino', dia=None, **outros):
        inicio, fim = {
            'matutino': ('08:00', '10:00'),
            'vespertino': ('14:00', '16:00'),
            'noturno': ('19:00', '21:00'),
        }[turno]
        dados = {
            'professor': 'Docente Exemplo',
            'curso': 'ADS', 'disciplina': 'Programação',
            'tipo_reserva': 'TEMP', 'quantidade_alunos': 25,
            'turno': turno, 'horario_inicio': inicio, 'horario_fim': fim,
            'descricao': '', 'modo_reserva': 'multiplas',
            'datas_selecionadas': (dia or self.data).isoformat(),
        }
        dados.update(outros)
        return dados

    def nova_reserva(self, turno='matutino'):
        inicio, fim = {
            'matutino': (time(8), time(10)),
            'vespertino': (time(14), time(16)),
            'noturno': (time(19), time(21)),
        }[turno]
        return Agendamento.objects.create(
            laboratorio=self.laboratorio, usuario=self.professor,
            professor='Docente Exemplo', curso='ADS', disciplina='Programação',
            quantidade_alunos=25, data=self.data, turno=turno,
            horario_inicio=inicio, horario_fim=fim, status='C'
        )

    def test_calendario_informa_turno_sem_bloquear_outro(self):
        self.nova_reserva('matutino')
        self.client.force_login(self.professor)
        resposta = self.client.get(reverse('solicitar_reserva', args=[self.laboratorio.pk]))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn(self.data.isoformat(), resposta.context['datas_ocupadas'])
        import json
        bloqueios = json.loads(resposta.context['datas_ocupadas'])
        self.assertIn(self.data.isoformat(), bloqueios['matutino'])
        self.assertNotIn(self.data.isoformat(), bloqueios['noturno'])

    @patch('agendamentos.views.send_mail', return_value=1)
    def test_turnos_diferentes_podem_ser_reservados(self, envio):
        self.nova_reserva('matutino')
        self.client.force_login(self.professor)
        resposta = self.client.post(
            reverse('solicitar_reserva', args=[self.laboratorio.pk]),
            self.dados_reserva('noturno')
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(Agendamento.objects.filter(status='C').count(), 2)

    @patch('agendamentos.views.send_mail', return_value=1)
    def test_mesmo_turno_nao_aceita_segunda_reserva(self, envio):
        self.nova_reserva('matutino')
        self.client.force_login(self.professor)
        resposta = self.client.post(
            reverse('solicitar_reserva', args=[self.laboratorio.pk]),
            self.dados_reserva()
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'CONFLITO DE AGENDA')
        self.assertEqual(Agendamento.objects.count(), 1)

    def test_reserva_semestral_longa_e_rejeitada(self):
        formulario = AgendamentoForm(
            {**self.dados_reserva(), 'modo_reserva': 'semestre',
             'data_inicio_semestre': self.data.isoformat(),
             'data_fim_semestre': (self.data + timedelta(days=200)).isoformat(),
             'dia_semana': str(self.data.weekday()),
             'datas_selecionadas': ''},
            laboratorio=self.laboratorio,
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('180 dias', str(formulario.errors))

    def test_exclusao_de_laboratorio_sem_historico(self):
        self.client.force_login(self.chefe)
        resposta = self.client.post(
            reverse('painel_laboratorios_ti'),
            {'excluir_laboratorio_id': str(self.laboratorio.pk)},
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertFalse(Laboratorio.objects.filter(pk=self.laboratorio.pk).exists())

    def test_laboratorio_com_historico_nao_pode_ser_excluido(self):
        self.nova_reserva()
        self.client.force_login(self.chefe)
        resposta = self.client.post(
            reverse('painel_laboratorios_ti'),
            {'excluir_laboratorio_id': str(self.laboratorio.pk)},
        )
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(Laboratorio.objects.filter(pk=self.laboratorio.pk).exists())

    def test_professor_nao_pode_excluir_laboratorio(self):
        self.client.force_login(self.professor)
        resposta = self.client.post(
            reverse('painel_laboratorios_ti'),
            {'excluir_laboratorio_id': str(self.laboratorio.pk)},
        )
        self.assertEqual(resposta.status_code, 403)
        self.assertTrue(Laboratorio.objects.filter(pk=self.laboratorio.pk).exists())

    @patch('agendamentos.views.send_mail', return_value=1)
    def test_laboratorio_em_manutencao_nao_aceita_reserva(self, envio):
        self.laboratorio.em_manutencao = True
        self.laboratorio.save(update_fields=['em_manutencao'])
        self.client.force_login(self.professor)
        resposta = self.client.post(
            reverse('solicitar_reserva', args=[self.laboratorio.pk]),
            self.dados_reserva()
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'manutenção')
        self.assertFalse(Agendamento.objects.exists())

    def test_falha_ao_gerar_lote_desfaz_todas_as_reservas(self):
        self.client.force_login(self.professor)
        data_extra = self.data + timedelta(days=1)
        if data_extra.weekday() == 6:
            data_extra += timedelta(days=1)
        dados = self.dados_reserva(
            datas_selecionadas=f'{self.data.isoformat()}, {data_extra.isoformat()}'
        )
        with patch('agendamentos.views.LogOperacao.objects.create',
                   side_effect=RuntimeError('falha simulada')):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    reverse('solicitar_reserva', args=[self.laboratorio.pk]),
                    dados,
                )
        self.assertEqual(Agendamento.objects.count(), 0)

    def test_excel_nao_executa_disciplina_com_formula(self):
        reserva = self.nova_reserva()
        reserva.disciplina = '=1+1'
        reserva.save(update_fields=['disciplina'])
        conteudo = _criar_relatorio_excel([reserva], 'Período de teste')
        documento = load_workbook(BytesIO(conteudo))
        celula = documento['Agendamentos']['E2']
        self.assertEqual(celula.data_type, 's')
        self.assertEqual(celula.value, '=1+1')
