from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Software(models.Model):
    nome = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nome do Software",
        help_text="Ex: AutoCAD, Visual Studio Code, MATLAB, Pacote Office"
    )
    versao = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Versão",
        help_text="Ex: 2024, 19.0, Community"
    )
    fabricante = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Fabricante / Desenvolvedor",
        help_text="Ex: Autodesk, Microsoft, Adobe"
    )
    descricao = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observações Técnicas",
        help_text="Detalhes sobre licença, dependências ou complementos."
    )

    class Meta:
        verbose_name = "Software"
        verbose_name_plural = "Softwares"
        ordering = ['nome']

    def __str__(self):
        v = f" (v.{self.versao})" if self.versao else ""
        return f"{self.nome}{v}"


class Laboratorio(models.Model):
    nome = models.CharField(
        max_length=100,
        verbose_name="Nome do Laboratório",
        help_text="Identificação do espaço (Ex: Labin 1, Labin 2)"
    )

    ordem = models.PositiveIntegerField(
        default=0,
        verbose_name="Ordem Numérica",
        help_text="Número real do laboratório para forçar a ordenação correta (ex: 9 para Labin IX)"
    )

    capacidade = models.IntegerField(
        verbose_name="Capacidade de Alunos",
        help_text="Quantidade máxima de postos/estações de trabalho para alunos"
    )
    localizacao = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Localização Física",
        help_text="Bloco e sala do laboratório (Ex: Bloco 5, Sala 703)"
    )

    em_manutencao = models.BooleanField(
        default=False,
        verbose_name="Em Manutenção (Bloqueado)",
        help_text="Se marcado, o laboratório é ocultado da lista de agendamentos para os professores."
    )
    justificativa_bloqueio = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Motivo do Bloqueio",
        help_text="Ex: Ar condicionado estragado, formatação de máquinas."
    )

    tem_datashow = models.BooleanField(
        default=True,
        verbose_name="Possui Datashow Fixo?"
    )

    softwares = models.ManyToManyField(
        Software,
        blank=True,
        related_name="laboratorios",
        verbose_name="Softwares Instalados",
        help_text="Selecione os softwares disponíveis neste laboratório."
    )

    descricao_programas = models.TextField(
        blank=True,
        verbose_name="Observações Gerais de Infraestrutura",
        help_text="Notas adicionais sobre os equipamentos ou restrições da sala."
    )

    class Meta:
        verbose_name = "Laboratório"
        verbose_name_plural = "Laboratórios"
        ordering = ['ordem']

    def __str__(self):
        status = " [MANUTENÇÃO]" if self.em_manutencao else ""
        return f"{self.nome}{status}"


class Agendamento(models.Model):
    STATUS_CHOICES = [
        ('C', 'Confirmado'),
        ('X', 'Cancelado pelo Docente'),
        ('T', 'Cancelado pela TI'),
    ]
    TURNO_CHOICES = [
        ('matutino', 'Matutino (08:00 às 13:00)'),
        ('vespertino', 'Vespertino (13:00 às 19:00)'),
        ('noturno', 'Noturno (19:00 às 22:00)'),
    ]
    TIPO_RESERVA_CHOICES = [
        ('TEMP', 'Reserva Temporária / Evento (TEMP)'),
        ('AULA', 'Aula Regular do Semestre (AULA)'),
    ]

    laboratorio = models.ForeignKey(
        Laboratorio,
        on_delete=models.CASCADE,
        related_name="agendamentos",
        verbose_name="Laboratório Solicitado"
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="agendamentos_usuario",
        verbose_name="Conta Institucional (Docente)"
    )
    professor = models.CharField(
        max_length=100,
        verbose_name="Nome do Professor"
    )
    curso = models.CharField(
        max_length=100,
        default='Não informado',
        verbose_name="Curso Solicitante",
        help_text="Ex: Sistemas de Informação, Odontologia"
    )
    disciplina = models.CharField(
        max_length=100,
        verbose_name="Disciplina / Atividade"
    )
    tipo_reserva = models.CharField(
        max_length=4,
        choices=TIPO_RESERVA_CHOICES,
        default='TEMP',
        verbose_name="Tipo de Agendamento"
    )
    quantidade_alunos = models.PositiveIntegerField(
        verbose_name="Quantidade Prevista de Alunos"
    )

    data = models.DateField(
        verbose_name="Data da Aula"
    )
    horario_inicio = models.TimeField(
        verbose_name="Horário de Início"
    )
    horario_fim = models.TimeField(
        verbose_name="Horário de Término"
    )
    turno = models.CharField(
        max_length=15,
        choices=TURNO_CHOICES,
        default='matutino',
        verbose_name="Turno Acadêmico"
    )

    descricao = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observações / Softwares Específicos"
    )

    status = models.CharField(
        max_length=1,
        choices=STATUS_CHOICES,
        default='C',
        verbose_name="Status da Solicitação"
    )
    data_criacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Timestamp de Criação"
    )

    @property
    def pode_cancelar(self):
        from django.utils import timezone
        hoje = timezone.localdate()
        agora = timezone.localtime().time()
        if self.data > hoje:
            return True
        elif self.data == hoje:
            return self.horario_inicio > agora
        return False

    class Meta:
        verbose_name = "Agendamento"
        verbose_name_plural = "Agendamentos"
        ordering = ['-data', 'horario_inicio']

    def __str__(self):
        return f"{self.professor} - {self.laboratorio.nome} ({self.data.strftime('%d/%m/%Y')} - {self.get_turno_display()})"


class Perfil(models.Model):
    TIPO_USUARIO_CHOICES = [
        ('docente', 'Docente / Professor'),
        ('ti', 'Técnico de TI'),
        ('chefe_ti', 'Chefe da TI / Administrador'),
    ]
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='perfil',
        verbose_name="Conta do Usuário"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_USUARIO_CHOICES,
        default='docente',
        verbose_name="Papel no Sistema"
    )
    telefone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Telefone / Ramal"
    )

    class Meta:
        verbose_name = "Perfil de Usuário"
        verbose_name_plural = "Perfis de Usuários"

    def __str__(self):
        nome_exibicao = self.usuario.get_full_name() or self.usuario.username
        return f"{nome_exibicao} ({self.get_tipo_display()})"

    @property
    def eh_docente(self):
        return self.tipo == 'docente'
    @property
    def eh_ti(self):
        return self.tipo in ['ti', 'chefe_ti']
    @property
    def eh_chefe_ti(self):
        return self.tipo == 'chefe_ti' or self.usuario.is_superuser


@receiver(post_save, sender=User)
def criar_perfil_usuario(sender, instance, created, **kwargs):
    if kwargs.get('raw', False):
        return

    if created:
        Perfil.objects.create(usuario=instance, tipo='docente')


@receiver(post_save, sender=User)
def salvar_perfil_usuario(sender, instance, **kwargs):
    if kwargs.get('raw', False):
        return

    if hasattr(instance, 'perfil'):
        instance.perfil.save()


class LogOperacao(models.Model):
    ACOES_CHOICES = [
        ('CRIACAO', 'Criação'),
        ('EDICAO', 'Edição'),
        ('CANCELAMENTO', 'Cancelamento'),
        ('BLOQUEIO', 'Bloqueio'),
    ]
    data_hora = models.DateTimeField(auto_now_add=True, verbose_name="Data")
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Usuário")
    agendamento_id = models.IntegerField(null=True, blank=True, verbose_name="ID da Reserva")
    acao = models.CharField(max_length=20, choices=ACOES_CHOICES, verbose_name="Ação Geral")
    campo_alterado = models.CharField(max_length=100, blank=True, null=True, verbose_name="Campo")
    detalhe_atualizacao = models.TextField(verbose_name="Atualizar")

    class Meta:
        verbose_name = "Log de Operação"
        verbose_name_plural = "Logs de Operações"
        ordering = ['-data_hora']

    def __str__(self):
        usuario_str = self.usuario.username if self.usuario else "Sistema"
        return f"{self.data_hora.strftime('%d/%m/%Y %H:%M')} - {usuario_str} - {self.campo_alterado}"


class RelatorioFechamento(models.Model):

    periodo = models.CharField(
        max_length=50,
        verbose_name="Período de Referência",
        help_text="Ex: 01/01/2026 a 31/12/2026"
    )

    data_geracao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data de Geração"
    )

    gerado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Responsável pela Geração"
    )

    arquivo = models.FileField(
        upload_to='relatorios_semestrais/',
        verbose_name="Arquivo do Relatório (PDF)"
    )

    class Meta:
        verbose_name = "Relatório de Ocupação"
        verbose_name_plural = "Relatórios de Ocupação"

        ordering = ['-data_geracao']

    def __str__(self):
        return f"Relatório de Ocupação - {self.periodo}"
