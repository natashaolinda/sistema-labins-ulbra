
import re
from datetime import datetime, time, timedelta

from django import forms
from django.contrib.auth.models import User
from django.db.models import Max
from django.utils import timezone

from .models import Agendamento, Laboratorio, Software


class BuscaLaboratorioForm(forms.Form):
    TURNO_CHOICES = [
        ('', 'Todos os Turnos'),
        ('matutino', 'Matutino (08:00 às 13:00)'),
        ('vespertino', 'Vespertino (13:00 às 19:00)'),
        ('noturno', 'Noturno (19:00 às 22:00)'),
    ]

    AREA_CHOICES = [
        ('basico', 'Programas Básicos'),
        ('engenharia', 'Engenharia/Arquitetura'),
        ('desenvolvimento', 'Desenvolvimento/TI'),
        ('medicina', 'Medicina'),
        ('sniffy', 'Sniffy Pro'),
    ]

    data = forms.DateField(
        required=False,
        label='Data',
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'type': 'date',
                'class': 'form-control'
            }
        )
    )

    turno = forms.ChoiceField(
        choices=TURNO_CHOICES,
        required=False,
        label='Turno',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    quantidade_aluno = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Mínimo de vagas',
            'class': 'form-control'
        })
    )

    area = forms.ChoiceField(
        choices=AREA_CHOICES,
        required=False,
        label='Programas Necessários',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['data'].widget.attrs['min'] = (
            timezone.localdate().isoformat()
        )

        if not self.is_bound:
            self.fields['data'].initial = timezone.localdate()

        categorias = {
            'programasbásicos',
            'engenharia/arquitetura',
            'desenvolvimento/ti',
            'medicina',
            'sniffypro'
        }

        outros_softwares = [
            (f'software:{software.pk}', software.nome)
            for software in Software.objects.order_by('nome')
            if software.nome.lower().replace(' ', '') not in categorias
        ]

        self.fields['area'].choices = (
            self.AREA_CHOICES + outros_softwares
        )

    def clean_data(self):
        data = self.cleaned_data.get('data')

        if data and data < timezone.localdate():
            raise forms.ValidationError(
                'Não é permitido consultar disponibilidade '
                'em datas anteriores à data atual.'
            )

        if data and data.weekday() == 6:
            raise forms.ValidationError(
                'Não são permitidas reservas aos domingos.'
            )

        return data


class AgendamentoForm(forms.ModelForm):
    MODO_CHOICES = [
        ('multiplas', 'Datas Específicas (Selecionar no calendário)'),
        ('semestre', 'Semestre Inteiro (Todas as semanas)'),
    ]

    DIA_SEMANA_CHOICES = [
        ('0', 'Segunda-feira'),
        ('1', 'Terça-feira'),
        ('2', 'Quarta-feira'),
        ('3', 'Quinta-feira'),
        ('4', 'Sexta-feira'),
        ('5', 'Sábado'),
    ]

    HORARIOS_TURNOS = {
        'matutino': (time(8, 0), time(13, 0)),
        'vespertino': (time(13, 0), time(19, 0)),
        'noturno': (time(19, 0), time(22, 0)),
    }

    modo_reserva = forms.ChoiceField(
        choices=MODO_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        initial='multiplas',
        label='Modalidade da Reserva'
    )

    datas_selecionadas = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Clique para selecionar as datas',
            'readonly': 'readonly'
        }),
        label='Datas da Aula'
    )

    data_inicio_semestre = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label='Data de Início'
    )

    data_fim_semestre = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label='Data de Término'
    )

    dia_semana = forms.ChoiceField(
        choices=DIA_SEMANA_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Dia da Semana'
    )

    class Meta:
        model = Agendamento

        fields = [
            'professor',
            'curso',
            'disciplina',
            'tipo_reserva',
            'quantidade_alunos',
            'turno',
            'horario_inicio',
            'horario_fim',
            'descricao'
        ]

        widgets = {
            'professor': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome completo'
            }),

            'curso': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Odontologia, Sistemas de Informação'
            }),

            'disciplina': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Algoritmos e Programação'
            }),

            'quantidade_alunos': forms.NumberInput(attrs={
                'class': 'form-control'
            }),

            'turno': forms.Select(attrs={
                'class': 'form-select'
            }),

            'horario_inicio': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control'
            }),

            'horario_fim': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control'
            }),

            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Softwares específicos (opcional)'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.laboratorio = kwargs.pop('laboratorio', None)

        super().__init__(*args, **kwargs)

        self.fields['descricao'].required = False

        hoje = timezone.localdate().isoformat()

        self.fields['data_inicio_semestre'].widget.attrs['min'] = hoje
        self.fields['data_fim_semestre'].widget.attrs['min'] = hoje

    def clean(self):
        cleaned_data = super().clean()

        modo = cleaned_data.get('modo_reserva')
        datas_str = cleaned_data.get('datas_selecionadas')
        data_inicio = cleaned_data.get('data_inicio_semestre')
        data_fim = cleaned_data.get('data_fim_semestre')
        dia_semana = cleaned_data.get('dia_semana')

        turno = cleaned_data.get('turno')
        horario_inicio = cleaned_data.get('horario_inicio')
        horario_fim = cleaned_data.get('horario_fim')
        capacidade_solicitada = cleaned_data.get('quantidade_alunos')

        hoje = timezone.localdate()

        if horario_inicio and horario_fim:
            if horario_inicio >= horario_fim:
                raise forms.ValidationError(
                    'O horário de início deve ser anterior '
                    'ao horário de término.'
                )

            if turno in self.HORARIOS_TURNOS:
                limite_inicio, limite_fim = self.HORARIOS_TURNOS[turno]

                if (
                    horario_inicio < limite_inicio
                    or horario_fim > limite_fim
                ):
                    raise forms.ValidationError(
                        f'O turno {turno.capitalize()} permite reservas '
                        f'somente entre {limite_inicio.strftime("%H:%M")} '
                        f'e {limite_fim.strftime("%H:%M")}.'
                    )

        if (
            self.laboratorio
            and capacidade_solicitada
            and capacidade_solicitada > self.laboratorio.capacidade
        ):
            raise forms.ValidationError(
                f'A turma ({capacidade_solicitada} alunos) excede a '
                f'capacidade do laboratório '
                f'({self.laboratorio.capacidade} postos).'
            )

        lista_datas = []

        if modo == 'multiplas':
            if not datas_str:
                raise forms.ValidationError(
                    'Selecione pelo menos uma data no calendário.'
                )

            for data_texto in datas_str.split(','):
                data_texto = data_texto.strip()

                if not data_texto:
                    continue

                try:
                    data_convertida = datetime.strptime(
                        data_texto,
                        '%Y-%m-%d'
                    ).date()

                except ValueError:
                    raise forms.ValidationError(
                        'Foi informada uma data inválida. '
                        'Selecione novamente pelo calendário.'
                    )

                if data_convertida < hoje:
                    raise forms.ValidationError(
                        'Não é permitido realizar agendamentos '
                        'em datas anteriores à data atual.'
                    )

                lista_datas.append(data_convertida)

        elif modo == 'semestre':
            if not data_inicio or not data_fim or not dia_semana:
                raise forms.ValidationError(
                    'Preencha o início, o fim e o dia da semana '
                    'para realizar uma reserva semestral.'
                )

            if data_inicio < hoje:
                raise forms.ValidationError(
                    'A data inicial do semestre não pode '
                    'ser anterior à data atual.'
                )

            if data_fim < hoje:
                raise forms.ValidationError(
                    'A data final do semestre não pode '
                    'ser anterior à data atual.'
                )

            if data_inicio > data_fim:
                raise forms.ValidationError(
                    'A data de início deve ser anterior '
                    'ou igual à data de término.'
                )

            dia_alvo = int(dia_semana)
            data_atual = data_inicio

            while data_atual <= data_fim:
                if data_atual.weekday() == dia_alvo:
                    lista_datas.append(data_atual)

                data_atual += timedelta(days=1)

            if not lista_datas:
                raise forms.ValidationError(
                    'Não existem dias correspondentes ao dia da semana '
                    'no período selecionado.'
                )

        lista_datas = sorted(set(lista_datas))

        if modo in ('multiplas', 'semestre') and not lista_datas:
            raise forms.ValidationError(
                'Nenhuma data válida foi selecionada.'
            )

        if any(data_aula < hoje for data_aula in lista_datas):
            raise forms.ValidationError(
                'Não é permitido reservar datas anteriores à data atual.'
            )

        if any(data_aula.weekday() == 6 for data_aula in lista_datas):
            raise forms.ValidationError(
                'Não são permitidas reservas aos domingos.'
            )

        if self.laboratorio and lista_datas and turno:
            colisoes = Agendamento.objects.filter(
                laboratorio=self.laboratorio,
                turno=turno,
                data__in=lista_datas,
                status='C'
            )

            if colisoes.exists():
                datas_ocupadas = sorted({
                    reserva.data.strftime('%d/%m/%Y')
                    for reserva in colisoes
                })

                raise forms.ValidationError(
                    'CONFLITO DE AGENDA: O laboratório já possui '
                    'reserva confirmada nas seguintes datas: '
                    + ', '.join(datas_ocupadas) + '.'
                )

        cleaned_data['lista_datas_calculadas'] = lista_datas

        return cleaned_data


class EdicaoReservaTIForm(forms.ModelForm):
    justificativa_ti = forms.CharField(
        required=False,
        label='Justificativa da Alteração (Para notificação do Docente)',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': (
                'Informe o motivo caso esteja trocando '
                'o laboratório ou horário...'
            )
        })
    )

    class Meta:
        model = Agendamento

        fields = [
            'laboratorio',
            'curso',
            'disciplina',
            'tipo_reserva',
            'data',
            'turno',
            'horario_inicio',
            'horario_fim',
            'quantidade_alunos',
            'status'
        ]

        widgets = {
            'laboratorio': forms.Select(attrs={
                'class': 'form-select'
            }),

            'curso': forms.TextInput(attrs={
                'class': 'form-control'
            }),

            'disciplina': forms.TextInput(attrs={
                'class': 'form-control'
            }),

            'data': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),

            'turno': forms.Select(attrs={
                'class': 'form-select'
            }),

            'horario_inicio': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control'
            }),

            'horario_fim': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control'
            }),

            'quantidade_alunos': forms.NumberInput(attrs={
                'class': 'form-control'
            }),

            'status': forms.Select(attrs={
                'class': 'form-select fw-bold'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for campo in [
            'curso',
            'disciplina',
            'tipo_reserva',
            'status'
        ]:
            if campo in self.fields:
                self.fields[campo].required = False

    def clean(self):
        cleaned_data = super().clean()

        if self.instance.pk:
            for campo in [
                'curso',
                'disciplina',
                'tipo_reserva',
                'status'
            ]:
                if not cleaned_data.get(campo):
                    cleaned_data[campo] = getattr(self.instance, campo)

        lab_destino = cleaned_data.get('laboratorio')
        data = cleaned_data.get('data')
        turno = cleaned_data.get('turno')
        horario_inicio = cleaned_data.get('horario_inicio')
        horario_fim = cleaned_data.get('horario_fim')
        capacidade_solicitada = cleaned_data.get('quantidade_alunos')
        status = cleaned_data.get('status')

        if data and data.weekday() == 6:
            raise forms.ValidationError(
                'Não são permitidas reservas aos domingos.'
            )

        if (
            horario_inicio
            and horario_fim
            and horario_inicio >= horario_fim
        ):
            raise forms.ValidationError(
                'O horário de início deve ser anterior ao de término.'
            )

        if (
            lab_destino
            and capacidade_solicitada
            and capacidade_solicitada > lab_destino.capacidade
        ):
            raise forms.ValidationError(
                f'Incompatibilidade de infraestrutura: '
                f'O {lab_destino.nome} suporta apenas '
                f'{lab_destino.capacidade} alunos.'
            )

        if lab_destino and data and turno and status == 'C':
            conflitos = Agendamento.objects.filter(
                laboratorio=lab_destino,
                data=data,
                turno=turno,
                status='C'
            )

            if self.instance.pk:
                conflitos = conflitos.exclude(
                    pk=self.instance.pk
                )

            if conflitos.exists():
                raise forms.ValidationError(
                    f'Conflito: O {lab_destino.nome} já possui '
                    'aula confirmada neste turno e data.'
                )

        return cleaned_data


class EdicaoLaboratorioTIForm(forms.ModelForm):
    class Meta:
        model = Laboratorio

        fields = [
            'capacidade',
            'tem_datashow',
            'em_manutencao',
            'justificativa_bloqueio',
            'softwares'
        ]

        widgets = {
            'capacidade': forms.NumberInput(attrs={
                'class': 'form-control'
            }),

            'tem_datashow': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),

            'em_manutencao': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),

            'justificativa_bloqueio': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Opcional. Ex: Ar condicionado em manutenção'
            }),

            'softwares': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
        }


class CadastroLaboratorioForm(forms.ModelForm):
    novo_software = forms.CharField(
        required=False,
        max_length=100,
        label='Adicionar novo software',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex.: Blender, AutoCAD, Python'
        })
    )

    class Meta:
        model = Laboratorio

        fields = [
            'nome',
            'localizacao',
            'capacidade',
            'tem_datashow',
            'softwares',
            'descricao_programas',
            'em_manutencao',
            'justificativa_bloqueio'
        ]

        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex.: Labin XV'
            }),

            'localizacao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex.: Bloco 5, Sala 703'
            }),

            'capacidade': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),

            'tem_datashow': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),

            'softwares': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),

            'descricao_programas': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),

            'em_manutencao': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),

            'justificativa_bloqueio': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Motivo, caso esteja em manutenção'
            }),
        }

    def clean_nome(self):
        nome = self.cleaned_data['nome'].strip()

        if Laboratorio.objects.filter(
            nome__iexact=nome
        ).exclude(
            pk=self.instance.pk
        ).exists():
            raise forms.ValidationError(
                'Já existe um laboratório com esse nome.'
            )

        return nome

    def clean_capacidade(self):
        capacidade = self.cleaned_data['capacidade']

        if capacidade < 1:
            raise forms.ValidationError(
                'Informe uma capacidade maior que zero.'
            )

        return capacidade

    def clean_novo_software(self):
        return (
            self.cleaned_data.get('novo_software') or ''
        ).strip()

    @staticmethod
    def calcular_ordem(nome):
        identificador = nome.strip().split()[-1].upper()

        if identificador.isdigit():
            return int(identificador)

        if re.fullmatch(r'[IVXLCDM]+', identificador):
            valores = {
                'I': 1,
                'V': 5,
                'X': 10,
                'L': 50,
                'C': 100,
                'D': 500,
                'M': 1000
            }

            numero = 0
            anterior = 0

            for letra in reversed(identificador):
                atual = valores[letra]
                numero += -atual if atual < anterior else atual
                anterior = max(anterior, atual)

            if numero > 0:
                return numero

        maior_ordem = Laboratorio.objects.aggregate(
            maior=Max('ordem')
        )['maior']

        return (maior_ordem or 0) + 1

    def save(self, commit=True):
        laboratorio = super().save(commit=False)

        if not laboratorio.pk:
            laboratorio.ordem = self.calcular_ordem(
                laboratorio.nome
            )

        if commit:
            laboratorio.save()
            self.save_m2m()

            nome_software = self.cleaned_data.get(
                'novo_software'
            )

            if nome_software:
                software = Software.objects.filter(
                    nome__iexact=nome_software
                ).first()

                if software is None:
                    software = Software.objects.create(
                        nome=nome_software
                    )

                laboratorio.softwares.add(software)

        return laboratorio


class PromocaoUsuarioTIForm(forms.Form):
    usuario = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label='Usuário a promover',
        empty_label='Selecione um usuário',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['usuario'].queryset = User.objects.filter(
            perfil__tipo='docente',
            is_superuser=False
        ).order_by(
            'first_name',
            'last_name',
            'username'
        )

        self.fields['usuario'].label_from_instance = (
            self._rotulo_usuario
        )

    @staticmethod
    def _rotulo_usuario(usuario):
        nome = usuario.get_full_name() or usuario.username

        return (
            f'{nome} ({usuario.email})'
            if usuario.email
            else nome
        )