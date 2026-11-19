
from django.urls import path

from . import views


urlpatterns = [
    path('', views.quadro_horarios, name='quadro_horarios'),

    path('reservar-laboratorio/', views.lista_laboratorios, name='lista_laboratorios'),
    path('reservar/<int:lab_id>/', views.solicitar_reserva, name='solicitar_reserva'),
    path('reserva/sucesso/<int:agendamento_id>/', views.reserva_sucesso, name='reserva_sucesso'),
    path('meus-agendamentos/', views.meus_agendamentos, name='meus_agendamentos'),
    path('reserva/cancelar/<int:agendamento_id>/', views.cancelar_reserva, name='cancelar_reserva'),

    path('ti/painel/', views.painel_ti, name='painel_ti'),
    path('ti/reserva/<int:agendamento_id>/editar/', views.editar_reserva_ti, name='editar_reserva_ti'),
    path('ti/reserva/<int:agendamento_id>/cancelar/', views.cancelar_reserva_ti, name='cancelar_reserva_ti'),
    path('ti/laboratorios/', views.painel_laboratorios_ti, name='painel_laboratorios_ti'),
    path('ti/laboratorios/<int:lab_id>/editar/', views.editar_laboratorio_ti, name='editar_laboratorio_ti'),
    path('ti/laboratorios/novo/', views.cadastrar_laboratorio, name='cadastrar_laboratorio'),
    path('ti/usuarios/', views.gerenciar_usuarios, name='gerenciar_usuarios'),

    path('ti/gestao/', views.painel_gestao, name='painel_gestao'),
    path('ti/gestao/relatorio/gerar/', views.gerar_relatorio_ocupacao, name='gerar_relatorio_ocupacao'),
    path('ti/gestao/relatorio/<int:relatorio_id>/baixar/', views.baixar_relatorio_ocupacao, name='baixar_relatorio_ocupacao'),
    path('ti/gestao/relatorio/<int:relatorio_id>/excluir/', views.excluir_relatorio_ocupacao, name='excluir_relatorio_ocupacao'),

    path('sair-sistema/', views.custom_logout_view, name='logout_customizado'),
]
