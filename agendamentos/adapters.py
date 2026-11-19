"""
FICHEIRO: agendamentos/adapters.py
FINALIDADE: Interceptar o login do Google e validar regras de negócio (RBAC).
"""

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import redirect
from allauth.exceptions import ImmediateHttpResponse

class FiltroDominioAdapter(DefaultSocialAccountAdapter):
    """
    Bloqueia logins de contas Google que não pertençam aos domínios institucionais
    ou à lista de exceções (homologação/banca).
    """
    def pre_social_login(self, request, sociallogin):
        # 1. Captura o e-mail que o Google nos devolveu e converte para minúsculas
        email_google = sociallogin.account.extra_data.get('email', '').lower()

        # ======================================================================
        # BLOCO DE VALIDAÇÃO DE DOMÍNIO E HOMOLOGAÇÃO
        # ======================================================================
        
        # 2. Lista de exceções para a banca avaliar o trabalho (Whitelist)
        emails_homologacao = [
            'sistemalabins@gmail.com',  # Superadministrador / Sistema
            'tiulbrapalmas@gmail.com',  # Equipe de TI
            'ulbraprofessor@gmail.com'  # Professor
        ]

        # 3. Lista de domínios institucionais permitidos (Docentes e TI)
        # Nota: '@rede.ulbra.br' (alunos) não está aqui, logo serão bloqueados.
        dominios_permitidos = ['@ulbra.br'] 
        
        # 4. Verifica se o e-mail atende a pelo menos uma das condições
        eh_dominio_permitido = any(email_google.endswith(dominio) for dominio in dominios_permitidos)
        eh_email_teste = email_google in emails_homologacao

        # 5. Se não for domínio permitido E não for e-mail de teste, bloqueia o acesso!
        if not (eh_dominio_permitido or eh_email_teste):
            
            # Dispara um alerta vermelho (flash message) que será exibido no base.html
            messages.error(
                request, 
                f"Acesso Negado ({email_google}). O Sistema Labins é restrito a docentes da instituição e credenciais de avaliação."
            )
            
            # Interrompe o processo do allauth e atira o utilizador de volta para a página pública
            raise ImmediateHttpResponse(redirect('quadro_horarios'))