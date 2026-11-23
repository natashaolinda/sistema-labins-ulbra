# Sistema Labins - ULBRA Palmas

**Sistema Integrado de Gestão e Agendamento de Laboratórios de TI e Espaços Acadêmicos**

Projeto desenvolvido para a disciplina **Projeto Tecnológico em Desenvolvimento de Sistemas**, do Curso Superior de Tecnologia em Análise e Desenvolvimento de Sistemas da Universidade Luterana do Brasil(ULBRA).

**Acadêmica:** Gabriela Natasha Bandeira Olinda  
**Aplicação publicada:** https://sistema-labins-production.up.railway.app/sistema/  
**Repositório público:** https://github.com/natashaolinda/sistema-labins-ulbra

## 1. Apresentação

O Sistema Labins foi desenvolvido com o objetivo de organizar e automatizar o processo de reserva dos laboratórios de informática da ULBRA Palmas. A proposta surgiu da necessidade de centralizar informações que anteriormente dependiam de solicitações por e-mail e de controles manuais realizados pela equipe de TI.

A aplicação permite consultar a ocupação dos laboratórios, verificar a disponibilidade dos ambientes e realizar agendamentos de acordo com as necessidades acadêmicas. Também disponibiliza recursos administrativos para o acompanhamento das reservas, manutenção dos laboratórios, gerenciamento de usuários, auditoria e emissão de relatórios.

O sistema contempla inicialmente **14 laboratórios de informática**. Sua estrutura foi organizada para atender aos diferentes perfis de acesso, preservando o histórico das operações realizadas.

## 2. Acesso ao sistema

A aplicação encontra-se publicada no Railway e pode ser acessada pelo endereço:

**https://sistema-labins-production.up.railway.app/sistema/**

O **Quadro de Aulas** é público e pode ser consultado sem autenticação. Para utilizar as funcionalidades de reserva e administração, o acesso é realizado por meio da conta Google vinculada ao **e-mail institucional do domínio `@ulbra.br`**, respeitando as permissões atribuídas a cada perfil de usuário.

Para possibilitar a avaliação acadêmica das funcionalidades, foram autorizadas, excepcionalmente, **contas de teste externas ao domínio institucional**, vinculadas aos perfis de professor, equipe de TI e Chefia de TI/Superadministrador. Essas contas permitem verificar os diferentes níveis de acesso e as operações disponíveis no sistema, sem modificar a regra de autenticação institucional adotada para sua utilização regular.

As orientações de acesso e a identificação das contas destinadas aos testes são apresentadas no **Documento de Implementação e Disponibilização do Sistema**. Por questões de segurança, as senhas e demais credenciais não são disponibilizadas neste repositório.

## 3. Funcionalidades implementadas

### 3.1. Quadro público de horários

- Consulta das aulas e reservas confirmadas, sem necessidade de login.
- Apresentação do laboratório, localização, disciplina, docente, turno e horário.
- Filtros por data, turno e laboratório.
- Exibição inicial das aulas do dia, considerando os turnos pertinentes ao horário da consulta.

### 3.2. Consulta e reserva de laboratórios

- Consulta dos laboratórios disponíveis por data, turno, capacidade e softwares cadastrados.
- Identificação dos laboratórios em manutenção, impedindo sua disponibilização para novas reservas.
- Solicitação de reservas para datas específicas ou recorrentes durante o semestre.
- Validação dos horários de acordo com os limites de cada turno.
- Verificação da capacidade do laboratório em relação à quantidade de alunos informada.
- Bloqueio de agendamentos em datas anteriores à atual e aos domingos.
- Prevenção de reservas simultâneas para o mesmo laboratório, data e turno.
- Confirmação automática dos agendamentos, sem necessidade de aprovação manual pela TI.

### 3.3. Acompanhamento das reservas

- Consulta das reservas realizadas pelo docente.
- Cancelamento das próprias reservas, respeitando as regras de antecedência.
- Manutenção das reservas canceladas no histórico, com identificação de sua situação.
- Liberação do laboratório para novo agendamento após o cancelamento.

### 3.4. Operações da equipe de TI

- Acompanhamento dos agendamentos dos diferentes laboratórios.
- Filtragem das reservas por data, turno, laboratório e situação.
- Edição e remanejamento das reservas, conforme as permissões do perfil.
- Cancelamento administrativo de reservas com **justificativa obrigatória**.
- Registro da operação de cancelamento e envio de notificação ao professor responsável.
- Atualização das informações dos laboratórios, incluindo capacidade, recursos, softwares e situação de manutenção.

### 3.5. Administração e gestão

- Cadastro de novos laboratórios pela Chefia de TI.
- Gerenciamento dos perfis de acesso dos usuários autorizados.
- Registro de operações administrativas para consulta e auditoria.
- Geração de relatórios de ocupação por período nos formatos **PDF** e **Excel (.xlsx)**.
- Consulta do histórico de relatórios, com opções de download e exclusão conforme as permissões.

### 3.6. Autenticação e notificações

- Autenticação com conta Google, por meio do **django-allauth**.
- Restrição de acesso conforme o domínio institucional e as exceções autorizadas para testes.
- Controle de permissões para docentes, equipe de TI, Chefia de TI e superadministrador.
- Notificações por e-mail para confirmação, cancelamento e alterações de reservas, utilizando uma integração com Google Apps Script.

## 4. Tecnologias utilizadas

| Tecnologia | Finalidade | Versão de referência |
| --- | --- | --- |
| Python | Desenvolvimento do back-end | 3.15.1 no ambiente local de desenvolvimento |
| Django | Framework web, formulários, ORM e regras de negócio | 6.0.4 |
| SQLite | Banco de dados utilizado no desenvolvimento local | Integrado ao ambiente Python |
| MySQL | Banco de dados da aplicação publicada | Instância hospedada no Railway |
| HTML, CSS e JavaScript | Estrutura, apresentação e interações das páginas | Tecnologias web |
| Bootstrap | Estilização e responsividade da interface | 5.3 |
| Flatpickr | Seleção de datas para reservas | Biblioteca JavaScript |
| django-allauth | Integração com autenticação Google | 65.16.1 |
| mysqlclient | Conexão do Django com o MySQL | 2.3.1 |
| ReportLab | Geração dos relatórios PDF | 5.1.0 |
| openpyxl | Geração dos relatórios Excel | 3.1.5 |
| Gunicorn | Execução da aplicação no servidor | 27.0.1 |
| WhiteNoise | Gerenciamento de arquivos estáticos | 6.12.0 |
| Railway | Hospedagem da aplicação e do banco MySQL | Plataforma de nuvem |
| Google Apps Script | Envio das notificações por e-mail | Serviço externo |
| Git e GitHub | Versionamento e disponibilização do código-fonte | Ferramentas de desenvolvimento |

A relação completa das bibliotecas Python e suas versões está disponível no arquivo `requirements.txt`.

## 5. Organização do projeto

A aplicação foi estruturada conforme a organização de projetos Django, separando as configurações, os modelos de dados, os formulários, as regras de negócio e os templates.

```text
sistema-labins-ulbra/
├── agendamentos/
│   ├── migrations/                  # Histórico de alterações do banco
│   ├── templates/agendamentos/      # Páginas HTML do sistema
│   ├── adapters.py                  # Regras de acesso pelo Google
│   ├── email_backend.py             # Integração com o serviço de e-mails
│   ├── forms.py                     # Formulários e validações
│   ├── models.py                    # Modelos e relacionamentos
│   ├── urls.py                      # Rotas das funcionalidades
│   └── views.py                     # Processamento e regras de negócio
├── configuracao/
│   ├── settings.py                  # Configurações da aplicação
│   └── urls.py                      # Rotas principais
├── static/                          # Arquivos estáticos do projeto
├── banco_labins.sql                 # Estrutura do MySQL, sem dados reais
├── manage.py                        # Gerenciamento do Django
├── requirements.txt                 # Dependências do Python
└── README.md                        # Orientações do projeto
```

## 6. Instalação e execução local

As instruções abaixo consideram o **Windows com PowerShell**. Para reproduzir a aplicação em outro sistema operacional, é necessário adaptar os comandos de criação e ativação do ambiente virtual.

### 6.1. Obter o código-fonte

```powershell
git clone https://github.com/natashaolinda/sistema-labins-ulbra.git
cd sistema-labins-ulbra
```

### 6.2. Criar e ativar o ambiente virtual

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

### 6.3. Instalar as dependências

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 6.4. Configurar as variáveis de ambiente

Crie um arquivo `.env` na pasta principal do projeto. Para executar o ambiente local utilizando SQLite, utilize a seguinte estrutura de exemplo:

```dotenv
SECRET_KEY=substitua-por-uma-chave-propria-do-ambiente-local
DEBUG=True
DB_ENGINE=sqlite
```

O arquivo `.env` é de uso local e **não deve ser enviado ao GitHub**.

Para utilizar o MySQL em outro ambiente, as configurações correspondentes são `DB_ENGINE=mysql`, `MYSQLDATABASE`, `MYSQLUSER`, `MYSQLPASSWORD`, `MYSQLHOST` e `MYSQLPORT`.

A autenticação com Google depende de credenciais OAuth e da configuração do provedor no Django. O envio de notificações depende das variáveis `LABINS_EMAIL_API_URL` e `LABINS_API_KEY`, que devem ser preenchidas com valores próprios do ambiente. **Nenhuma credencial real é disponibilizada no código-fonte.**

### 6.5. Criar a estrutura do banco local

Para utilizar SQLite no ambiente de desenvolvimento, execute:

```powershell
python manage.py migrate
```

As migrações criam as tabelas da aplicação. O banco gerado não contém os registros utilizados na versão publicada; por isso, pode ser necessário cadastrar laboratórios, softwares e usuários de teste antes de avaliar as funcionalidades autenticadas.

### 6.6. Executar a aplicação

```powershell
python manage.py check
python manage.py runserver
```

Acesse no navegador:

**http://127.0.0.1:8000/sistema/**

O quadro de horários pode ser consultado sem login. Para testar reservas e funções administrativas no ambiente local, é necessário configurar a autenticação Google e utilizar contas autorizadas com os respectivos perfis.

## 7. Estrutura do banco de dados

O sistema utiliza um banco de dados relacional. Durante o desenvolvimento local foi utilizado SQLite, enquanto a versão hospedada no Railway utiliza MySQL.

O arquivo **`banco_labins.sql`** contém a definição das **24 tabelas** do banco MySQL, incluindo campos, tipos de dados, chaves primárias, índices e relacionamentos. O script foi exportado **sem os registros armazenados na aplicação**, preservando informações pessoais e dados operacionais.

O arquivo SQL destina-se à consulta da estrutura e à sua recriação em um **banco MySQL vazio, criado para essa finalidade**. Ele não deve ser executado sobre o banco de produção. Para a execução local com SQLite, recomenda-se utilizar as migrações do Django apresentadas na seção anterior.

Entre os modelos específicos do sistema estão:

- `Laboratorio`: informações dos ambientes, capacidade, localização, recursos e manutenção.
- `Software`: programas cadastrados e vinculados aos laboratórios.
- `Agendamento`: dados das reservas, datas, horários, docentes e situações.
- `Perfil`: definição das permissões de acesso dos usuários.
- `LogOperacao`: registro das operações realizadas no sistema.
- `RelatorioFechamento`: identificação e armazenamento dos relatórios gerados.

Além desses modelos, são utilizadas tabelas de autenticação, permissões, sessões e integração com o Google, mantidas pelo Django e pelo django-allauth.

## 8. Orientações para análise do código

Para compreender a organização e o funcionamento do sistema, sugere-se a seguinte sequência:

1. **`agendamentos/models.py`**: identificar as entidades, seus atributos e os relacionamentos entre as tabelas.
2. **`agendamentos/forms.py`**: verificar as validações de datas, horários, capacidade e conflitos de reserva.
3. **`agendamentos/views.py`**: acompanhar as regras de negócio, a criação de reservas, os cancelamentos, as permissões e a geração de relatórios.
4. **`agendamentos/urls.py`**: relacionar as rotas com as funcionalidades disponíveis.
5. **`agendamentos/templates/agendamentos/`**: analisar as páginas, os formulários e as informações apresentadas aos usuários.
6. **`configuracao/settings.py`**: consultar as configurações de banco, autenticação, arquivos estáticos e notificações.

Para verificar o comportamento da aplicação, recomenda-se testar o quadro público, os filtros de disponibilidade, a prevenção de conflitos, os cancelamentos, os diferentes perfis de acesso e a emissão de relatórios PDF e Excel. Os testes de envio de e-mails exigem que a integração esteja configurada.

## 9. Limites do escopo e possibilidades de evolução

O projeto priorizou o gerenciamento dos laboratórios de informática e as operações essenciais de reserva. Algumas funcionalidades previstas inicialmente permaneceram fora do escopo implementado:

- **Provas EAD:** não foi desenvolvido um fluxo específico para a distribuição automática de alunos entre os laboratórios durante as avaliações.
- **Organização modular por prédios e blocos:** os laboratórios possuem informação de localização, mas não foi implementado um módulo de gerenciamento de diferentes prédios e tipos de espaços acadêmicos.
- **Backup automático do MySQL:** não foi desenvolvida uma rotina própria de backup automático como funcionalidade do sistema.

Esses pontos são apresentados e justificados no documento acadêmico de implementação, juntamente com as adequações realizadas durante o desenvolvimento.

## 10. Publicação e segurança

A aplicação encontra-se hospedada no Railway, utilizando MySQL para persistência dos dados e um volume para o armazenamento dos relatórios gerados. O acesso às áreas administrativas depende de autenticação e das permissões associadas ao perfil do usuário.

Para manter a segurança da aplicação, as credenciais de banco de dados, chaves de autenticação e configurações de integração são definidas por variáveis de ambiente. Os arquivos `.env`, bancos locais e demais arquivos contendo informações sensíveis não devem ser versionados.

O repositório público tem finalidade acadêmica e contém o código-fonte necessário à análise do projeto, sem cópia dos registros reais do banco de produção.

## 11. Identificação acadêmica

**Instituição:** Universidade Luterana do Brasil - ULBRA  
**Curso:** Análise e Desenvolvimento de Sistemas  
**Disciplina:** Projeto Tecnológico em Desenvolvimento de Sistemas  
**Projeto:** Sistema Integrado de Gestão e Agendamento de Laboratórios de TI e Espaços Acadêmicos  
**Acadêmica:** Gabriela Natasha Bandeira Olinda  
**Período:** 2026/2
