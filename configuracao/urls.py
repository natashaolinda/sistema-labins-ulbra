
"""
Arquivo: configuracao/urls.py

FINALIDADE:
Roteador principal do projeto Django.

RESPONSABILIDADES:
1. Redirecionar a página inicial para o quadro de horários.
2. Disponibilizar o painel administrativo.
3. Encaminhar as rotas do sistema de agendamentos.
4. Disponibilizar as rotas de autenticação.
5. Impedir a exposição pública dos relatórios PDF.
"""

# ============================================================
# 1. IMPORTAÇÕES
# ============================================================

# Painel administrativo nativo do Django.
from django.contrib import admin

# Funções utilizadas para configurar as URLs.
from django.urls import path, include

# Permite redirecionar automaticamente o usuário.
from django.views.generic import RedirectView


# ============================================================
# 2. ROTAS PRINCIPAIS DO SISTEMA
# ============================================================

urlpatterns = [

    # --------------------------------------------------------
    # 1. PÁGINA INICIAL
    # --------------------------------------------------------

    # Redireciona o endereço principal para o quadro
    # de horários do sistema.
    path(
        '',
        RedirectView.as_view(
            url='/sistema/',
            permanent=False
        )
    ),

    # --------------------------------------------------------
    # 2. PAINEL ADMINISTRATIVO
    # --------------------------------------------------------

    # Interface administrativa do Django.
    path(
        'admin/',
        admin.site.urls
    ),

    # --------------------------------------------------------
    # 3. SISTEMA DE AGENDAMENTOS
    # --------------------------------------------------------

    # Encaminha as URLs iniciadas por /sistema/
    # para o arquivo agendamentos/urls.py.
    #
    # Inclui:
    # - Calendário e agendamentos.
    # - Gestão e auditoria.
    # - Geração de relatórios.
    # - Download protegido dos PDFs.
    # - Exclusão de relatórios.
    path(
        'sistema/',
        include('agendamentos.urls')
    ),

    # --------------------------------------------------------
    # 4. AUTENTICAÇÃO
    # --------------------------------------------------------

    # Rotas de autenticação e integração com Google
    # por meio do django-allauth.
    path(
        'accounts/',
        include('allauth.urls')
    ),

]


# ============================================================
# 3. PROTEÇÃO DOS ARQUIVOS DE MÍDIA
# ============================================================

# Não publicamos automaticamente a pasta MEDIA_ROOT.
# Os relátorios são baixados pela view com verificação de permissão.