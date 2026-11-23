"""
Arquivo: agendamentos/admin.py
FINALIDADE: Configuração e personalização da interface de administração nativa do Django (Django Admin).
RESPONSABILIDADES:
1. Mapear a gestão dos laboratórios e softwares da instituição.
2. Disponibilizar a edição de infraestrutura e softwares instalados.
3. Organizar os campos através de agrupamentos visuais (fieldsets).
4. Fornecer filtros e visualização estruturada para auditoria dos agendamentos efetuados.
5. Estender a interface padrão de Usuários (User) para gerenciar os papéis via PerfilInline.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Laboratorio, Agendamento, Perfil, Software


# ==============================================================================
# 1. GESTÃO DE USUÁRIOS E PAPÉIS (RBAC - DOCENTE, TI E CHEFE DA TI)
# ==============================================================================
class PerfilInline(admin.StackedInline):
    """
    Acopla o modelo Perfil diretamente dentro da página de edição do Usuário.
    """
    model = Perfil
    can_delete = False
    verbose_name = "Papel e Permissões no Sistema Labins"
    verbose_name_plural = "Perfil Institucional (Papel no Sistema)"
    fields = ('tipo', 'telefone')


class CustomUserAdmin(BaseUserAdmin):
    """
    Sobrescreve a visualização padrão de Usuários do Django para incluir o PerfilInline.
    """
    inlines = (PerfilInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_tipo_usuario', 'is_staff')

    @admin.display(description="Papel Institucional")
    def get_tipo_usuario(self, instance):
        if hasattr(instance, 'perfil'):
            return instance.perfil.get_tipo_display()
        return "Sem Perfil"


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# ==============================================================================
# 2. GESTÃO ADMINISTRATIVA DE SOFTWARES 
# ==============================================================================
@admin.register(Software)
class SoftwareAdmin(admin.ModelAdmin):
    """
    Permite à TI gerenciar o catálogo de softwares instalados nos laboratórios.
    """
    list_display = ('nome', 'versao', 'fabricante')
    search_fields = ('nome', 'fabricante')
    list_filter = ('fabricante',)


# ==============================================================================
# 3. GESTÃO ADMINISTRATIVA DE LABORATÓRIOS
# ==============================================================================
@admin.register(Laboratorio)
class LaboratorioAdmin(admin.ModelAdmin):
    """
    Personaliza a visualização e edição das salas de informática e associação de softwares.
    """
    list_display = (
        'ordem',
        'nome', 
        'capacidade', 
        'localizacao', 
        'tem_datashow',
        'em_manutencao'
    )
    
    list_filter = (
        'tem_datashow', 
        'em_manutencao',
        'softwares'
    )

    search_fields = ('nome', 'localizacao')

    # ORGANIZAÇÃO DOS CAMPOS DENTRO DO FORMULÁRIO DE CADASTRO/EDIÇÃO (FIELDSETS)
    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                'nome', 
                'ordem',
                'capacidade', 
                'localizacao', 
                'tem_datashow'
            )
        }),
        ('Controle Operacional', {
            'fields': (
                'em_manutencao',
                'justificativa_bloqueio'
            )
        }),
        ('Softwares Instalados', {
            'description': "Selecione os softwares disponíveis neste laboratório (gestão relacional):",
            'fields': ('softwares',),
        }),
        ('Detalhes Técnicos Adicionais', {
            'fields': ('descricao_programas',),
        }),
    )

    # Torna a seleção de softwares em uma caixa de escolha múltipla intuitiva no Admin
    filter_horizontal = ('softwares',)


# ==============================================================================
# 4. GESTÃO ADMINISTRATIVA DE AGENDAMENTOS
# ==============================================================================
@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    """
    Interface para consulta, auditoria e fiscalização operacional das reservas docentes.
    """
    list_display = (
        'professor',
        'disciplina',
        'laboratorio', 
        'data', 
        'turno', 
        'horario_inicio', 
        'horario_fim', 
        'status'
    )

    list_filter = ('data', 'turno', 'status', 'laboratorio')
    search_fields = ('professor', 'disciplina', 'laboratorio__nome')
    date_hierarchy = 'data'