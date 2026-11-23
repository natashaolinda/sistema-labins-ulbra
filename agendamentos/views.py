import json
from datetime import date, datetime
from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .forms import (
    AgendamentoForm,
    BuscaLaboratorioForm,
    CadastroLaboratorioForm,
    EdicaoLaboratorioTIForm,
    EdicaoReservaTIForm,
    PromocaoUsuarioTIForm,
)
from .models import Agendamento, Laboratorio, LogOperacao, Perfil, RelatorioFechamento


def _pode_acessar_ti(usuario):
    perfil = getattr(usuario, 'perfil', None)
    return usuario.is_superuser or bool(perfil and perfil.eh_ti)


def _pode_gerenciar_sistema(usuario):
    perfil = getattr(usuario, 'perfil', None)
    return usuario.is_superuser or bool(perfil and perfil.eh_chefe_ti)


def quadro_horarios(request):
    data_str = request.GET.get('data')
    turno_selecionado = request.GET.get('turno', '')
    lab_selecionado = request.GET.get('laboratorio', '')

    hoje = timezone.localdate()
    agora_hora = timezone.localtime().hour

    if data_str:
        try:
            data_consulta = date.fromisoformat(data_str)
        except ValueError:
            data_consulta = hoje
    else:
        data_consulta = hoje

    agendamentos_qs = Agendamento.objects.filter(
        data=data_consulta,
        status='C'
    ).select_related('laboratorio', 'usuario')

    if data_consulta == hoje and not turno_selecionado:
        if agora_hora >= 19:
            agendamentos_qs = agendamentos_qs.filter(turno='noturno')
        elif agora_hora >= 13:
            agendamentos_qs = agendamentos_qs.filter(
                turno__in=['vespertino', 'noturno']
            )

    if turno_selecionado:
        agendamentos_qs = agendamentos_qs.filter(
            turno=turno_selecionado
        )

    if lab_selecionado:
        agendamentos_qs = agendamentos_qs.filter(
            laboratorio_id=lab_selecionado
        )

    ordem_turnos = Case(
        When(turno='matutino', then=Value(1)),
        When(turno='vespertino', then=Value(2)),
        When(turno='noturno', then=Value(3)),
        default=Value(4),
        output_field=IntegerField(),
    )

    agendamentos_qs = agendamentos_qs.annotate(
        prioridade_turno=ordem_turnos
    ).order_by(
        'prioridade_turno',
        'horario_inicio',
        'laboratorio__nome'
    )

    laboratorios = Laboratorio.objects.all()

    return render(request, 'agendamentos/quadro_horarios.html', {
        'agendamentos': agendamentos_qs,
        'laboratorios': laboratorios,
        'data_consulta': data_consulta,
        'turno_selecionado': turno_selecionado,
        'lab_selecionado': lab_selecionado,
        'eh_hoje': (data_consulta == hoje),
        'agora_hora': agora_hora,
    })


@login_required
def lista_laboratorios(request):
    form = BuscaLaboratorioForm(request.GET or None)

    laboratorios = Laboratorio.objects.filter(
        em_manutencao=False
    )

    if form.is_valid():
        data_busca = form.cleaned_data.get('data')
        turno_busca = form.cleaned_data.get('turno')
        alunos = form.cleaned_data.get('quantidade_aluno')
        area_selecionada = form.cleaned_data.get('area')

        if alunos:
            laboratorios = laboratorios.filter(
                capacidade__gte=alunos
            )

        if area_selecionada and area_selecionada.startswith('software:'):
            software_id = area_selecionada.partition(':')[2]
            if software_id.isdigit():
                laboratorios = laboratorios.filter(
                    softwares__id=int(software_id)
                ).distinct()
        elif area_selecionada and area_selecionada != 'basico':
            mapa_termos = {
                'engenharia': [
                    'AutoCAD', 'CAD', 'Revit', 'Matlab',
                    'Projetos', 'Engenharia'
                ],
                'desenvolvimento': [
                    'Visual Studio', 'Python', 'Java',
                    'IntelliJ', 'Code', 'Django', 'Desenvolvimento'
                ],
                'medicina': [
                    'Anatomia', 'Simulador', 'Saúde', 'Medicina'
                ],
                'sniffy': ['Sniffy']
            }

            termos = mapa_termos.get(area_selecionada, [])

            if termos:
                q_objects = Q()

                for termo in termos:
                    q_objects |= Q(
                        softwares__nome__icontains=termo
                    )

                laboratorios = laboratorios.filter(
                    q_objects
                ).distinct()

        if data_busca and turno_busca:
            ocupados = Agendamento.objects.filter(
                data=data_busca,
                turno=turno_busca,
                status='C'
            ).values_list(
                'laboratorio_id',
                flat=True
            )

            laboratorios = laboratorios.exclude(
                id__in=ocupados
            )

    if request.GET.get('data') and not form.is_valid():
        laboratorios = Laboratorio.objects.none()

    return render(
        request,
        'agendamentos/lista.html',
        {
            'laboratorios': laboratorios,
            'form': form
        }
    )


@login_required
def solicitar_reserva(request, lab_id):
    laboratorio = get_object_or_404(Laboratorio, pk=lab_id)

    data_pre_selecionada = request.GET.get('data', '')

    hoje = timezone.localdate()

    agendamentos_existentes = Agendamento.objects.filter(
        laboratorio=laboratorio,
        status='C',
        data__gte=hoje
    ).values_list('data', 'turno')

    # A disponibilidade é por laboratório, data e turno.
    datas_ocupadas = {turno: [] for turno in (
        'matutino', 'vespertino', 'noturno'
    )}
    for data_reserva, turno_reserva in agendamentos_existentes:
        datas_ocupadas.setdefault(turno_reserva, []).append(
            data_reserva.isoformat()
        )
    datas_ocupadas_json = json.dumps({
        turno: sorted(set(datas))
        for turno, datas in datas_ocupadas.items()
    })

    if request.method == 'POST':
        # O bloqueio da linha do laboratório serializa reservas concorrentes
        # deste espaço no MySQL. A validação ocorre dentro da transação.
        with transaction.atomic():
            laboratorio_bloqueado = get_object_or_404(
                Laboratorio.objects.select_for_update(), pk=lab_id
            )
            form = AgendamentoForm(
                request.POST,
                laboratorio=laboratorio_bloqueado
            )
            if form.is_valid() and laboratorio_bloqueado.em_manutencao:
                form.add_error(
                    None, 'Este laboratório está em manutenção e não aceita reservas.'
                )

            if form.is_valid():
                datas_geradas = form.cleaned_data['lista_datas_calculadas']
                reservas_criadas = []

                for data_aula in datas_geradas:
                    reserva = Agendamento.objects.create(
                        laboratorio=laboratorio_bloqueado,
                        usuario=request.user,
                        status='C',
                        data=data_aula,
                        professor=form.cleaned_data['professor'],
                        curso=form.cleaned_data['curso'],
                        disciplina=form.cleaned_data['disciplina'],
                        tipo_reserva=form.cleaned_data.get('tipo_reserva', 'TEMP'),
                        quantidade_alunos=form.cleaned_data['quantidade_alunos'],
                        turno=form.cleaned_data['turno'],
                        horario_inicio=form.cleaned_data['horario_inicio'],
                        horario_fim=form.cleaned_data['horario_fim'],
                        descricao=form.cleaned_data['descricao'],
                    )
                    reservas_criadas.append(reserva)
                    LogOperacao.objects.create(
                        usuario=request.user,
                        acao='CRIACAO',
                        agendamento_id=reserva.id,
                        campo_alterado=(
                            'Agendamento em Lote' if len(datas_geradas) > 1
                            else 'Agendamento'
                        ),
                        detalhe_atualizacao=(
                            f'Reserva no {laboratorio_bloqueado.nome} '
                            f'(Data: {data_aula:%d/%m/%Y})'
                        ),
                    )

        if form.is_valid():
            email_remetente = settings.DEFAULT_FROM_EMAIL
            email_ti = settings.EMAIL_SUPORTE_TI

            datas_str = ", ".join([
                d.strftime('%d/%m/%Y')
                for d in datas_geradas
            ])

            if len(datas_geradas) > 5:
                datas_str = (
                    f"{len(datas_geradas)} datas selecionadas "
                    "ao longo do semestre."
                )

            assunto = (
                f"[Novo Agendamento] {laboratorio.nome} - "
                f"{len(datas_geradas)} aula(s)"
            )

            corpo_base = (
                f"Detalhes da Solicitação:\n\n"
                f"Laboratório: {laboratorio.nome}\n"
                f"Docente: {form.cleaned_data['professor']}\n"
                f"Curso: {form.cleaned_data['curso']}\n"
                f"Disciplina: {form.cleaned_data['disciplina']}\n"
                f"Datas reservadas: {datas_str}\n"
                f"Horário: "
                f"{form.cleaned_data['horario_inicio'].strftime('%H:%M')} "
                f"às "
                f"{form.cleaned_data['horario_fim'].strftime('%H:%M')}\n"
            )

            try:
                send_mail(
                    assunto,
                    (
                        "Novo agendamento registrado "
                        f"no Sistema Labins.\n\n{corpo_base}"
                    ),
                    email_remetente,
                    [email_ti],
                    fail_silently=True
                )

                if request.user.email:
                    send_mail(
                        (
                            "[Labins] Confirmação de Reserva - "
                            f"{laboratorio.nome}"
                        ),
                        (
                            f"Olá, {form.cleaned_data['professor']}!\n"
                            "Sua reserva foi confirmada "
                            f"com sucesso.\n\n{corpo_base}"
                        ),
                        email_remetente,
                        [request.user.email],
                        fail_silently=True
                    )

            except Exception as e:
                print(f"Erro ao enviar email de criação: {e}")

            if len(reservas_criadas) == 1:
                return redirect(
                    'reserva_sucesso',
                    agendamento_id=reservas_criadas[0].id
                )

            else:
                messages.success(
                    request,
                    (
                        f"{len(reservas_criadas)} aulas agendadas "
                        f"com sucesso no {laboratorio.nome}!"
                    )
                )

                return redirect('meus_agendamentos')

    else:
        initial_data = {
            'professor': (
                request.user.get_full_name()
                or request.user.username
            ),
            'turno': request.GET.get('turno', ''),
            'datas_selecionadas': data_pre_selecionada
        }

        form = AgendamentoForm(
            initial=initial_data,
            laboratorio=laboratorio
        )

    return render(
        request,
        'agendamentos/form_reserva.html',
        {
            'form': form,
            'laboratorio': laboratorio,
            'data_pre_selecionada': data_pre_selecionada,
            'datas_ocupadas': datas_ocupadas_json
        }
    )


@login_required
def reserva_sucesso(request, agendamento_id):
    reservas = Agendamento.objects.all()

    if not _pode_acessar_ti(request.user):
        reservas = reservas.filter(
            usuario=request.user
        )

    agendamento = get_object_or_404(
        reservas,
        pk=agendamento_id
    )

    return render(
        request,
        'agendamentos/reserva_sucesso.html',
        {'agendamento': agendamento}
    )



@login_required
def meus_agendamentos(request):
    hoje = timezone.localdate()

    agendamentos = (
        Agendamento.objects.filter(
            usuario=request.user
        )
        .select_related('laboratorio')
        .annotate(
            prioridade_data=Case(
                When(data__gte=hoje, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by(
            'prioridade_data',
            'data',
            'horario_inicio',
            'id'
        )
    )

    return render(
        request,
        'agendamentos/meus_agendamentos.html',
        {
            'agendamentos': agendamentos
        }
    )



@login_required
def cancelar_reserva(request, agendamento_id):
    reserva = get_object_or_404(
        Agendamento,
        pk=agendamento_id,
        usuario=request.user
    )

    if request.method == 'POST':
        if reserva.status in ['X', 'T']:
            messages.warning(
                request,
                'Esta reserva já se encontra cancelada.'
            )
            return redirect('meus_agendamentos')

        if not reserva.pode_cancelar:
            messages.error(
                request,
                'Não é permitido cancelar agendamentos passados ou em andamento.'
            )
            return redirect('meus_agendamentos')

        reserva.status = 'X'
        reserva.save()

        LogOperacao.objects.create(
            usuario=request.user,
            acao='CANCELAMENTO',
            agendamento_id=reserva.id,
            campo_alterado='Status',
            detalhe_atualizacao=(
                "Alterar Confirmado para Cancelado pelo Docente "
                f"(Lab: {reserva.laboratorio.nome})"
            )
        )

        email_remetente = settings.DEFAULT_FROM_EMAIL
        email_ti = settings.EMAIL_SUPORTE_TI

        corpo_cancelamento = (
            f"A reserva do {reserva.laboratorio.nome} "
            f"para o dia {reserva.data.strftime('%d/%m/%Y')} "
            "foi CANCELADA pelo docente. A vaga está livre."
        )

        try:
            send_mail(
                f"[Labins] Cancelamento: {reserva.laboratorio.nome}",
                corpo_cancelamento,
                email_remetente,
                [email_ti],
                fail_silently=True
            )

            if request.user.email:
                send_mail(
                    (
                        "[Labins] Reserva Cancelada - "
                        f"{reserva.laboratorio.nome}"
                    ),
                    (
                        f"Olá, {reserva.professor}!\n"
                        "Confirmamos o cancelamento da sua reserva "
                        f"para o dia {reserva.data.strftime('%d/%m/%Y')}."
                    ),
                    email_remetente,
                    [request.user.email],
                    fail_silently=True
                )

        except Exception as e:
            print(f"Erro ao enviar email: {e}")

        messages.success(
            request,
            'Reserva cancelada com sucesso. Laboratório liberado.'
        )

        return redirect('meus_agendamentos')

    return redirect('meus_agendamentos')


@login_required
def painel_ti(request):
    if not _pode_acessar_ti(request.user):
        raise PermissionDenied("Acesso restrito à equipe de TI.")

    hoje = timezone.localdate()
    agora = timezone.localtime().time()
    data_filtro = request.GET.get('data', '')
    turno_filtro = request.GET.get('turno', '')
    lab_filtro = request.GET.get('laboratorio', '')
    status_filtro = request.GET.get('status', 'todos')

    # Mantém os cancelamentos no histórico e permite filtrar por data.
    agendamentos = Agendamento.objects.select_related('laboratorio', 'usuario')
    data_consulta = None

    if data_filtro:
        try:
            data_consulta = date.fromisoformat(data_filtro)
        except ValueError:
            data_consulta = None
        if data_consulta:
            agendamentos = agendamentos.filter(data=data_consulta)
    else:
        agendamentos = agendamentos.filter(
            Q(data=hoje, horario_fim__gte=agora) | Q(data__gt=hoje)
        )

    if turno_filtro:
        agendamentos = agendamentos.filter(turno=turno_filtro)
    if lab_filtro:
        agendamentos = agendamentos.filter(laboratorio_id=lab_filtro)

    if status_filtro == 'confirmadas':
        agendamentos = agendamentos.filter(status='C')
    elif status_filtro == 'canceladas':
        agendamentos = agendamentos.filter(status__in=['X', 'T'])

    agendamentos = agendamentos.order_by('data', 'horario_inicio', 'id')

    return render(request, 'agendamentos/painel_ti.html', {
        'agendamentos': agendamentos,
        'laboratorios': Laboratorio.objects.all(),
        'data_consulta': data_consulta,
        'turno_selecionado': turno_filtro,
        'lab_selecionado': lab_filtro,
        'status_selecionado': status_filtro,
    })


@login_required
@require_POST
def cancelar_reserva_ti(request, agendamento_id):
    if not _pode_acessar_ti(request.user):
        raise PermissionDenied("Acesso restrito à equipe de TI.")

    justificativa = (request.POST.get('justificativa') or '').strip()
    if not (10 <= len(justificativa) <= 1000):
        messages.error(request, "A justificativa deve ter entre 10 e 1000 caracteres.")
        return redirect('painel_ti')

    with transaction.atomic():
        reserva = get_object_or_404(
            Agendamento.objects.select_for_update().select_related('laboratorio', 'usuario'),
            pk=agendamento_id,
        )
        if reserva.status != 'C':
            messages.warning(request, 'Esta reserva já está cancelada.')
            return redirect('painel_ti')

        reserva.status = 'T'
        reserva.save(update_fields=['status'])
        LogOperacao.objects.create(
            usuario=request.user,
            acao='CANCELAMENTO',
            agendamento_id=reserva.id,
            campo_alterado='Status',
            detalhe_atualizacao=(
                f"Confirmado para Cancelado pela TI. "
                f"Laboratório: {reserva.laboratorio.nome}. "
                f"Docente: {reserva.professor}. "
                f"Justificativa: {justificativa}"
            ),
        )
        email_professor = reserva.usuario.email
        assunto = f'[Labins] Reserva cancelada pela TI - {reserva.laboratorio.nome}'
        corpo = (
            f"Olá, {reserva.professor}!\n\n"
            "Sua reserva foi cancelada pela equipe de TI.\n\n"
            f"Laboratório: {reserva.laboratorio.nome}\n"
            f"Disciplina: {reserva.disciplina}\n"
            f"Data: {reserva.data:%d/%m/%Y}\n"
            f"Turno: {reserva.get_turno_display()}\n"
            f"Horário: {reserva.horario_inicio:%H:%M} às {reserva.horario_fim:%H:%M}\n"
            "Situação: Cancelada pela TI\n\n"
            f"Justificativa do cancelamento:\n{justificativa}\n\n"
            "Atenciosamente,\nEquipe de TI - Sistema Labins"
        )

    if email_professor:
        try:
            send_mail(
                assunto, corpo, settings.DEFAULT_FROM_EMAIL,
                [email_professor], fail_silently=False
            )
        except Exception:
            messages.warning(
                request, 'A reserva foi cancelada, mas o e-mail não pôde ser enviado.'
            )

    messages.success(request, 'Reserva cancelada pela TI. Registro mantido no histórico.')
    return redirect('painel_ti')


@login_required
def editar_reserva_ti(request, agendamento_id):
    if not _pode_acessar_ti(request.user):
        raise PermissionDenied("Acesso restrito à equipe de TI.")

    reserva = get_object_or_404(Agendamento, pk=agendamento_id)
    lab_anterior = reserva.laboratorio.nome
    status_anterior = reserva.status

    if status_anterior != 'C':
        messages.warning(request, 'Uma reserva cancelada não pode ser alterada.')
        return redirect('painel_ti')

    if request.method == 'POST':
        form = EdicaoReservaTIForm(request.POST, instance=reserva)
        if form.is_valid():
            justificativa = (form.cleaned_data.get('justificativa_ti') or '').strip()
            novo_status = form.cleaned_data.get('status') or status_anterior
            if novo_status in ('T', 'X') and novo_status != status_anterior:
                if not (10 <= len(justificativa) <= 1000):
                    form.add_error('justificativa_ti', 'Para cancelar, informe de 10 a 1000 caracteres.')
                elif novo_status == 'X':
                    form.add_error('status', 'Cancelamento pela TI deve usar o status Cancelado pela TI.')

            if not form.errors:
                with transaction.atomic():
                    reserva_editada = form.save()
                    cancelada = reserva_editada.status == 'T'
                    LogOperacao.objects.create(
                        usuario=request.user,
                        acao='CANCELAMENTO' if cancelada else 'EDICAO',
                        agendamento_id=reserva_editada.id,
                        campo_alterado='Status' if cancelada else (
                            'Laboratório' if lab_anterior != reserva_editada.laboratorio.nome else 'Dados'
                        ),
                        detalhe_atualizacao=(
                            f"Cancelado pela TI. Justificativa: {justificativa}"
                            if cancelada else
                            f"Reserva atualizada pela TI. Laboratório anterior: {lab_anterior}. "
                            f"Laboratório atual: {reserva_editada.laboratorio.nome}. "
                            f"Justificativa: {justificativa or 'Não informada.'}"
                        ),
                    )

                situacao = 'cancelada' if cancelada else 'atualizada'
                assunto = (
                    f"[Labins] Reserva cancelada - {reserva_editada.laboratorio.nome}"
                    if cancelada else '[Labins] Sua reserva foi atualizada'
                )
                corpo_email = (
                    f"Olá, {reserva_editada.professor}!\n\n"
                    f"Sua reserva foi {situacao} pela equipe de TI.\n\n"
                    "INFORMAÇÕES DA RESERVA\n\n"
                    f"Laboratório: {reserva_editada.laboratorio.nome}\n"
                    f"Curso: {reserva_editada.curso}\n"
                    f"Disciplina: {reserva_editada.disciplina}\n"
                    f"Data: {reserva_editada.data:%d/%m/%Y}\n"
                    f"Turno: {reserva_editada.get_turno_display()}\n"
                    f"Horário: {reserva_editada.horario_inicio:%H:%M} às "
                    f"{reserva_editada.horario_fim:%H:%M}\n"
                    f"Quantidade de alunos: {reserva_editada.quantidade_alunos}\n"
                    f"Situação: {reserva_editada.get_status_display()}\n\n"
                    f"JUSTIFICATIVA DA TI\n{justificativa or 'Não informada.'}\n\n"
                    "Atenciosamente,\nSistema Labins"
                )

                if reserva_editada.usuario.email:
                    try:
                        send_mail(
                            assunto, corpo_email, settings.DEFAULT_FROM_EMAIL,
                            [reserva_editada.usuario.email], fail_silently=False
                        )
                    except Exception:
                        messages.warning(request, 'Reserva alterada, mas o e-mail não pôde ser enviado.')

                messages.success(request, 'Reserva atualizada com sucesso!')
                return redirect('painel_ti')
    else:
        form = EdicaoReservaTIForm(instance=reserva)

    return render(request, 'agendamentos/editar_reserva_ti.html', {
        'form': form,
        'reserva': reserva,
        'lab_anterior': lab_anterior,
    })


@login_required
def painel_laboratorios_ti(request):
    if not _pode_acessar_ti(request.user):
        raise PermissionDenied("Acesso restrito à equipe de TI.")

    if request.method == 'POST':
        if not _pode_gerenciar_sistema(request.user):
            raise PermissionDenied('Somente a Chefia de TI pode excluir laboratórios.')
        lab_id = (
            request.POST.get('excluir_laboratorio_id')
            or request.POST.get('laboratorio_id')
            or request.POST.get('lab_id')
            or request.POST.get('excluir_lab_id')
        )
        if not lab_id:
            messages.error(request, 'Selecione um laboratório para excluir.')
            return redirect('painel_laboratorios_ti')
        laboratorio = get_object_or_404(Laboratorio, pk=lab_id)
        if Agendamento.objects.filter(laboratorio=laboratorio).exists():
            messages.error(request, 'Laboratório com histórico de reservas não pode ser excluído.')
        else:
            nome = laboratorio.nome
            with transaction.atomic():
                laboratorio.delete()
                LogOperacao.objects.create(
                    usuario=request.user,
                    acao='EDICAO',
                    campo_alterado='Laboratório',
                    detalhe_atualizacao=f'Laboratório {nome} excluído pela Chefia de TI.',
                )
            messages.success(request, 'Laboratório excluído com sucesso.')
        return redirect('painel_laboratorios_ti')

    return render(request, 'agendamentos/painel_laboratorios_ti.html', {
        'laboratorios': Laboratorio.objects.all().order_by('nome'),
    })


@login_required
def editar_laboratorio_ti(request, lab_id):
    if not _pode_acessar_ti(request.user):
        raise PermissionDenied(
            "Acesso restrito à equipe de TI."
        )

    laboratorio = get_object_or_404(
        Laboratorio,
        pk=lab_id
    )

    status_anterior = laboratorio.em_manutencao

    if request.method == 'POST':
        form = EdicaoLaboratorioTIForm(
            request.POST,
            instance=laboratorio
        )

        if form.is_valid():
            lab_salvo = form.save()

            if status_anterior != lab_salvo.em_manutencao:
                st_ant = (
                    "Bloqueado"
                    if status_anterior
                    else "Ativo"
                )

                st_nov = (
                    "Bloqueado"
                    if lab_salvo.em_manutencao
                    else "Ativo"
                )

                LogOperacao.objects.create(
                    usuario=request.user,
                    acao='BLOQUEIO',
                    agendamento_id=None,
                    campo_alterado='Status de Manutenção',
                    detalhe_atualizacao=(
                        f"{st_ant} para {st_nov} "
                        f"({lab_salvo.nome})"
                    )
                )

            messages.success(
                request,
                "Laboratório atualizado!"
            )

            return redirect('painel_laboratorios_ti')

    else:
        form = EdicaoLaboratorioTIForm(
            instance=laboratorio
        )

    return render(
        request,
        'agendamentos/editar_laboratorio_ti.html',
        {
            'form': form,
            'laboratorio': laboratorio
        }
    )


@login_required
def cadastrar_laboratorio(request):
    if not _pode_gerenciar_sistema(request.user):
        raise PermissionDenied(
            "Acesso exclusivo à Chefia de TI."
        )

    if request.method == 'POST':
        form = CadastroLaboratorioForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                laboratorio = form.save()

                LogOperacao.objects.create(
                    usuario=request.user,
                    acao='CRIACAO',
                    campo_alterado='Laboratório',
                    detalhe_atualizacao=(
                        f"Laboratório cadastrado: {laboratorio.nome} "
                        f"(ID: {laboratorio.pk})."
                    ),
                )

            messages.success(
                request,
                "Laboratório cadastrado com sucesso."
            )

            return redirect('painel_laboratorios_ti')

    else:
        form = CadastroLaboratorioForm()

    return render(
        request,
        'agendamentos/cadastrar_laboratorio.html',
        {'form': form},
    )


@login_required
def gerenciar_usuarios(request):
    if not _pode_gerenciar_sistema(request.user):
        raise PermissionDenied('Acesso exclusivo à Chefia de TI.')

    if request.method == 'POST':
        id_usuario = request.POST.get('usuario_id') or request.POST.get('id_usuario')
        novo_tipo = (
            request.POST.get('novo_tipo')
            or request.POST.get('tipo')
            or request.POST.get('novo_perfil')
        )

        if id_usuario and novo_tipo:
            if novo_tipo not in dict(Perfil.TIPO_USUARIO_CHOICES):
                messages.error(request, 'Perfil inválido.')
                return redirect('gerenciar_usuarios')

            usuario = get_object_or_404(User, pk=id_usuario, is_superuser=False)
            if usuario == request.user:
                messages.error(request, 'Não é permitido alterar seu próprio perfil por esta tela.')
                return redirect('gerenciar_usuarios')

            with transaction.atomic():
                perfil = Perfil.objects.select_for_update().get(usuario=usuario)
                anterior = perfil.tipo
                if anterior != novo_tipo:
                    perfil.tipo = novo_tipo
                    perfil.save(update_fields=['tipo'])
                    LogOperacao.objects.create(
                        usuario=request.user,
                        acao='EDICAO',
                        campo_alterado='Perfil do usuário',
                        detalhe_atualizacao=(
                            f"Perfil de {usuario.username} (ID: {usuario.pk}) "
                            f"alterado de {anterior} para {novo_tipo}."
                        ),
                    )
            messages.success(request, 'Perfil atualizado com sucesso.')
            return redirect('gerenciar_usuarios')

        form = PromocaoUsuarioTIForm(request.POST)
        if form.is_valid():
            usuario = form.cleaned_data['usuario']
            with transaction.atomic():
                perfil = Perfil.objects.select_for_update().get(usuario=usuario)
                if perfil.tipo != 'docente':
                    form.add_error('usuario', 'Este usuário não é docente.')
                else:
                    perfil.tipo = 'ti'
                    perfil.save(update_fields=['tipo'])
                    LogOperacao.objects.create(
                        usuario=request.user,
                        acao='EDICAO',
                        campo_alterado='Perfil do usuário',
                        detalhe_atualizacao=(
                            f"Usuário {usuario.username} (ID: {usuario.pk}) "
                            "promovido de Docente para Técnico de TI."
                        ),
                    )
                    messages.success(request, 'Usuário promovido para Técnico de TI.')
                    return redirect('gerenciar_usuarios')
    else:
        form = PromocaoUsuarioTIForm()

    usuarios = (
        User.objects.select_related('perfil')
        .filter(is_superuser=False)
        .order_by('first_name', 'last_name', 'username')
    )
    return render(request, 'agendamentos/gerenciar_usuarios.html', {
        'form': form,
        'usuarios': usuarios,
        'tipos_usuario': Perfil.TIPO_USUARIO_CHOICES,
    })


@login_required
def painel_gestao(request):
    if not _pode_gerenciar_sistema(request.user):
        raise PermissionDenied(
            "Acesso exclusivo à Chefia de TI."
        )

    logs_recentes = LogOperacao.objects.all()[:200]
    relatorios_salvos = RelatorioFechamento.objects.all()

    return render(
        request,
        'agendamentos/painel_gestao.html',
        {
            'logs': logs_recentes,
            'relatorios': relatorios_salvos
        }
    )


def _criar_relatorio_pdf(agendamentos, periodo):
    total_alunos = sum(
        agendamento.quantidade_alunos
        for agendamento in agendamentos
    )

    total_reservas = len(agendamentos)

    buffer = BytesIO()

    documento = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    estilos = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        'TituloRelatorioLabins',
        parent=estilos['Heading1'],
        alignment=TA_CENTER,
        textColor=colors.HexColor('#194C3A'),
        spaceAfter=15
    )

    estilo_celula = ParagraphStyle(
        'CelulaRelatorioLabins',
        parent=estilos['Normal'],
        fontSize=7,
        leading=9
    )

    elementos = []

    elementos.append(
        Paragraph(
            "RELATÓRIO DE OCUPAÇÃO DOS LABORATÓRIOS",
            estilo_titulo
        )
    )

    elementos.append(
        Paragraph(
            f"<b>Período:</b> {periodo}",
            estilos['Normal']
        )
    )

    elementos.append(
        Paragraph(
            f"<b>Total de reservas confirmadas:</b> {total_reservas}",
            estilos['Normal']
        )
    )

    elementos.append(
        Paragraph(
            f"<b>Atendimentos previstos:</b> {total_alunos}",
            estilos['Normal']
        )
    )

    elementos.append(Spacer(1, 15))

    dados_tabela = [[
        'Data',
        'Laboratório',
        'Professor',
        'Disciplina',
        'Curso',
        'Alunos'
    ]]

    for agendamento in agendamentos:
        dados_tabela.append([
            agendamento.data.strftime('%d/%m/%Y'),

            Paragraph(
                escape(
                    str(agendamento.laboratorio.nome)
                ),
                estilo_celula
            ),

            Paragraph(
                escape(
                    str(agendamento.professor)
                ),
                estilo_celula
            ),

            Paragraph(
                escape(
                    str(agendamento.disciplina)
                ),
                estilo_celula
            ),

            Paragraph(
                escape(
                    str(agendamento.curso)
                ),
                estilo_celula
            ),

            str(agendamento.quantidade_alunos)
        ])

    tabela = Table(
        dados_tabela,
        colWidths=[
            2.2 * cm,
            4.0 * cm,
            4.0 * cm,
            5.0 * cm,
            6.0 * cm,
            2.0 * cm
        ],
        repeatRows=1,
        hAlign='CENTER'
    )

    tabela.setStyle(TableStyle([
        (
            'BACKGROUND',
            (0, 0),
            (-1, 0),
            colors.HexColor('#194C3A')
        ),

        (
            'TEXTCOLOR',
            (0, 0),
            (-1, 0),
            colors.white
        ),

        (
            'FONTNAME',
            (0, 0),
            (-1, 0),
            'Helvetica-Bold'
        ),

        (
            'VALIGN',
            (0, 0),
            (-1, -1),
            'TOP'
        ),

        (
            'GRID',
            (0, 0),
            (-1, -1),
            0.3,
            colors.grey
        ),

        (
            'ROWBACKGROUNDS',
            (0, 1),
            (-1, -1),
            [
                colors.white,
                colors.HexColor('#F2F5F3')
            ]
        ),

        (
            'TOPPADDING',
            (0, 0),
            (-1, -1),
            7
        ),

        (
            'BOTTOMPADDING',
            (0, 0),
            (-1, -1),
            7
        ),
    ]))

    elementos.append(tabela)
    documento.build(elementos)
    return buffer.getvalue()


def _estilizar_planilha(aba, larguras):
    verde = PatternFill(fill_type='solid', fgColor='194C3A')
    for celula in aba[1]:
        celula.fill = verde
        celula.font = Font(color='FFFFFF', bold=True)
        celula.alignment = Alignment(horizontal='center', vertical='center')

    aba.freeze_panes = 'A2'
    aba.auto_filter.ref = aba.dimensions
    aba.row_dimensions[1].height = 26
    for numero, largura in enumerate(larguras, 1):
        aba.column_dimensions[get_column_letter(numero)].width = largura
    for linha in aba.iter_rows(min_row=2):
        for celula in linha:
            celula.alignment = Alignment(vertical='top', wrap_text=True)


def _criar_relatorio_excel(agendamentos, periodo):
    planilha = Workbook()
    aba = planilha.active
    aba.title = 'Agendamentos'
    aba.append([
        'Data', 'Laboratório', 'Professor', 'Curso', 'Disciplina',
        'Tipo de reserva', 'Turno', 'Início', 'Fim', 'Alunos', 'Status',
    ])

    resumo = {}
    for agendamento in agendamentos:
        aba.append([
            agendamento.data,
            agendamento.laboratorio.nome,
            agendamento.professor,
            agendamento.curso,
            agendamento.disciplina,
            agendamento.get_tipo_reserva_display(),
            agendamento.get_turno_display(),
            agendamento.horario_inicio.strftime('%H:%M'),
            agendamento.horario_fim.strftime('%H:%M'),
            agendamento.quantidade_alunos,
            agendamento.get_status_display(),
        ])
        # Campos informados pelos usuários são texto, nunca fórmulas Excel.
        for coluna in (2, 3, 4, 5):
            celula = aba.cell(row=aba.max_row, column=coluna)
            celula.data_type = 's'
        aba.cell(row=aba.max_row, column=1).number_format = 'DD/MM/YYYY'
        nome = agendamento.laboratorio.nome
        reserva = resumo.setdefault(nome, {'reservas': 0, 'alunos': 0})
        reserva['reservas'] += 1
        reserva['alunos'] += agendamento.quantidade_alunos

    _estilizar_planilha(aba, [16, 26, 30, 28, 36, 32, 28, 12, 12, 12, 22])

    aba_resumo = planilha.create_sheet('Resumo de Ocupação')
    aba_resumo.append(['Laboratório', 'Reservas confirmadas', 'Atendimentos previstos'])
    for nome, valores in sorted(resumo.items()):
        aba_resumo.append([nome, valores['reservas'], valores['alunos']])
    aba_resumo.append([
        'TOTAL', len(agendamentos),
        sum(item.quantidade_alunos for item in agendamentos),
    ])
    _estilizar_planilha(aba_resumo, [30, 26, 26])
    for celula in aba_resumo[aba_resumo.max_row]:
        celula.font = Font(bold=True)

    buffer = BytesIO()
    planilha.save(buffer)
    resultado = buffer.getvalue()
    buffer.close()
    return resultado


@login_required
@require_POST
def gerar_relatorio_ocupacao(request):
    if not _pode_gerenciar_sistema(request.user):
        raise PermissionDenied('Apenas a Chefia de TI pode gerar relatórios.')

    try:
        data_inicio = date.fromisoformat(request.POST.get('data_inicio', ''))
        data_fim = date.fromisoformat(request.POST.get('data_fim', ''))
    except (ValueError, TypeError):
        messages.error(request, 'Informe um período válido.')
        return redirect('painel_gestao')

    if data_inicio > data_fim:
        messages.error(request, 'A data inicial não pode ser posterior à data final.')
        return redirect('painel_gestao')

    formato = request.POST.get('formato', 'pdf').lower()
    if formato not in ('pdf', 'xlsx'):
        messages.error(request, 'Formato de relatório inválido.')
        return redirect('painel_gestao')

    agendamentos = list(
        Agendamento.objects.filter(
            data__range=(data_inicio, data_fim), status='C'
        ).select_related('laboratorio').order_by('data', 'horario_inicio')
    )
    if not agendamentos:
        messages.warning(request, 'Não existem agendamentos confirmados nesse período.')
        return redirect('painel_gestao')

    periodo = f'{data_inicio:%d/%m/%Y} a {data_fim:%d/%m/%Y}'
    if formato == 'xlsx':
        conteudo = _criar_relatorio_excel(agendamentos, periodo)
    else:
        conteudo = _criar_relatorio_pdf(agendamentos, periodo)

    nome_arquivo = (
        f'relatorio_ocupacao_{data_inicio:%Y%m%d}_'
        f'{data_fim:%Y%m%d}.{formato}'
    )
    relatorio = RelatorioFechamento(periodo=periodo, gerado_por=request.user)
    relatorio.arquivo.save(nome_arquivo, ContentFile(conteudo), save=True)
    messages.success(request, 'Relatório de ocupação gerado com sucesso!')
    return redirect('painel_gestao')


@login_required
def baixar_relatorio_ocupacao(request, relatorio_id):
    if not _pode_gerenciar_sistema(request.user):
        raise PermissionDenied('Apenas a Chefia de TI pode baixar relatórios.')

    relatorio = get_object_or_404(RelatorioFechamento, pk=relatorio_id)
    if (
        not relatorio.arquivo
        or not relatorio.arquivo.storage.exists(relatorio.arquivo.name)
    ):
        raise Http404('Arquivo do relatório não encontrado.')

    extensao = relatorio.arquivo.name.rsplit('.', 1)[-1].lower()
    if extensao == 'xlsx':
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif extensao == 'pdf':
        content_type = 'application/pdf'
    else:
        raise Http404('Formato não reconhecido.')

    from pathlib import PurePath
    return FileResponse(
        relatorio.arquivo.open('rb'),
        as_attachment=True,
        filename=PurePath(relatorio.arquivo.name).name,
        content_type=content_type,
    )


@login_required
@require_POST
def excluir_relatorio_ocupacao(request, relatorio_id):
    if not _pode_gerenciar_sistema(request.user):
        raise PermissionDenied(
            "Apenas a Chefia de TI pode excluir relatórios."
        )

    relatorio = get_object_or_404(
        RelatorioFechamento,
        pk=relatorio_id
    )

    arquivo_nome = (
        relatorio.arquivo.name
        if relatorio.arquivo
        else None
    )

    armazenamento = (
        relatorio.arquivo.storage
        if arquivo_nome
        else None
    )

    relatorio.delete()

    if arquivo_nome:
        try:
            armazenamento.delete(arquivo_nome)

        except Exception:
            messages.warning(
                request,
                (
                    "Registro excluído, mas não foi possível "
                    "apagar o arquivo do armazenamento."
                )
            )

            return redirect('painel_gestao')

    messages.success(
        request,
        "Relatório excluído. Os agendamentos foram preservados."
    )

    return redirect('painel_gestao')


def custom_logout_view(request):
    if request.method == 'POST':
        logout(request)

        return redirect('quadro_horarios')

    return render(
        request,
        'agendamentos/logout.html'
    )