# Documento de Visão

## StamFlow

### Histórico da Revisão 
| Data | Versão | Descrição | 
|:----|:------|:----------|
| 28/04/2026 | **1.2** | Versão Inicial |

## 1. Objetivo do Projeto 
O projeto visa desenvolver uma plataforma que, por meio da utilização do algoritmo do MediaPipe, monitora aspectos como ergonomia e humor do usuário durante seu tempo em frente ao computador, geralmente trabalhando, a fim de prevenir futuros problemas de saúde e acompanhar o bem-estar dele.

## 2. Descrição do problema 
| | | 
|:---|:---|
| **_O problema_** | Diante de tanto tempo em frente ao computador, muitos usuários ficam "relaxados" e se descuidam de uma ergonomia ideal, além de estarem exaustos mentalmente no período do trabalho. |
| **_Consequências_** | Futuros problemas de coluna e desenvolvimento de transtornos mentais. |
| **_Quem é impactado_** | Principalmente os colaboradores de empresas, as empresas e usuários de computador avulsos. |
| **_Proposta de Solução_** | Oferecer uma monitoria da ergonomia e do humor do usuário por meio do uso de Inteligência Artificial e Machine Learning do MediaPipe, desenvolvido pelo Google. |

## 3. Descrição dos usuários
| Nome | Descrição | Ações |
|:-|:-|:-|
| Usuário Avulso | Usuário cadastrado e com assinatura ativa;  O usuário, após realizar seu cadastro no site e a assinatura, poderá usufruir do monitoramento de ergonomia e humor em tempo real. | Após a realização da inclusão de dados cadastrais tais como login, senha e endereço e a realização do pagamento da assinatura, o usuário passa a ser visto como assinante poderá usufruir do sistema StamFlow. O usuário deve ter acesso às seguintes funcionalidades no site: Alterar seus dados cadastrais; Visualizar seu dashboard de métricas; Gerenciar assinatura. |
| Colaborador | Usuário cadastrado por meio de convite por parte da Empresa/Gestor; O usuário, após entrar no sistema via convite da Empresa/Gestor, poderá ver suas métricas de ergonomia e humor. | Após a realização do cadastro via convite, o Colaborador deve ter acesso às seguintes funcionalidades no site: Alterar seus dados cadastrais; Visualizar seu dashboard de métricas; Abrir Tickets para reportar alguma situação da empresa. |
| Gestor | Usuário cadastrado por meio de convite por parte da Empresa; O usuário, após entrar no sistema via convite da Empresa, poderá monitorar sua sub-equipe. | Após a realização do cadastro via convite, o Gestor deve ter acesso às seguintes funcionalidades no site: Alterar seus dados cadastrais; Visualizar o dashboard de métricas da sua sub-equipe; Elaborar Tickets de Resposta; Convidar novos Colaboradores para compor sua sub-equipe. |
| Empresa | Gestor de empresa, com CNPJ registrado. | Usuário responsável por gerenciar a sua assinatura e convidar novos Colaboradores/Gestores para sua equipe. |

## 4. Principais necessidades dos usuários
- **Usuário Avulso**: Gerenciar sua assinatura e acompanhar suas métricas de humor e ergonomia.
- **Colaborador**: Acompanhar suas métricas de humor e ergonomia.
- **Gestor**: Monitorar as métricas de humor e ergonomia da sua sub-equipe e acompanhar o bem-estar dela.
- **Empresa**: Gerenciar sua assinatura do sistema para proporcionar o monitoramento eficaz de sua equipe.

## 5. Visão Geral do Produto
O StamFlow é um sistema digital projetado para monitorar a ergonomia e o humor de usuários de computadores por meio de análise via webcam, em composição com o modelo de Inteligência Artificial MediaPipe da Google. As métricas coletadas alimentam o indicador exclusivo de **Stamina** (Sistema de Energia Produtiva), que pode ser acompanhado em tempo real através de um dashboard ou analisado a longo prazo na seção de Relatórios.

A plataforma entrega valor de duas formas distintas:

- Para o Plano Corporativo (B2B): Permite às empresas monitorar de forma inteligente o bem-estar coletivo de seus colaboradores. As métricas geradas oferecem insumos valiosos para o RH e gestão aplicarem melhorias no ambiente de trabalho e prevenirem o esgotamento (burnout).

- Para o Plano Individual (B2C): Foca no autocuidado preventivo. O sistema emite alertas e gera relatórios sobre a qualidade da ergonomia e o estado de humor do usuário no dia a dia, ajudando a evitar lesões físicas e transtornos de saúde mental a longo prazo.

## 6. Requisitos Funcionais

### 6.1. Gestão de Usuários e Autenticação

| Código | Nome                         | Descrição                                                                                         |
|--------|------------------------------|---------------------------------------------------------------------------------------------------|
| RF001  | Cadastro de Usuário Avulso      | Permite que visitantes criem uma conta. |
| RF002  | Login/Logout                 | Disponibiliza autenticação segura para todos os perfis, com expiração de sessão e bloqueio após múltiplas tentativas falhas. |
| RF003  | Recuperação de Senha         | Possibilita redefinir a senha via e-mail, utilizando token temporário com validade limitada. |
| RF004  | Cadastro de Empresa          | Executa o registro de empresas mediante seus dados válidos. |
| RF005  | Envio de Convites          | Realiza o envio de convites via e-mail para gestores e colaboradores associarem-se à equipe da empresa. |
| RF006  | Cadastro de Gestor          | Executa o registro de gestores mediante um convite enviado pela empresa. |
| RF007  | Cadastro de Colaborador          | Executa o registro de colaboradores mediante um convite enviado pela empresa ou pelo gestor. |
| RF008  | Edição de Perfil             | Permite a atualização de dados pessoais. |
| RF009  | Envio de Convites em Lote            | Permite que empresas e gestores enviem múltiplos convites simultaneamente através do upload de um arquivo CSV ou da listagem de e-mails. |
| RF010  | Visualização da Equipe            | Permite que a Empresa veja todos os gestores e colaboradores, e que o Gestor veja seus colaboradores subordinados. |
| RF011  | Exclusão de Contas/Membros             | Permite a exclusão de contas e a exclusão (individual ou em massa) de colaboradores/gestores. |

### 6.2. Assinaturas e Pagamentos

| Código | Nome                         | Descrição                                                                                         |
|--------|------------------------------|---------------------------------------------------------------------------------------------------|
| RF012  | Planos de Assinatura         | Apresenta diferentes as opções de plano individual e corporativo. |
| RF013  | Gerenciamento de Pagamentos via Webhooks  | Permite atualizar o status de uma Assinatura ao receber uma notificação de pagamento do gateway do Mercado Pago. |
| RF014  | Cancelamento de Assinatura   | Oferece cancelamento autônomo da assinatura. |
| RF015  | Alteração de Assinatura   | Permite realizar o upgrade ou downgrade de planos, bem como alterar a quantidade de licenças de funcionários/gestores. |
| RF016  | Validação do Limite de Vagas   | Impede o envio de novos convites caso a empresa atinja o número máximo de licenças relacionadas à sua assinatura. |
| RF017  | Gestão de Planos   | Permite que o Administrador do sistema seja responsável por gerenciar os planos existentes. |

### 6.3. Monitoramento, Dashboard e Relatórios

| Código | Nome                         | Descrição                                                                                         |
|--------|------------------------------|---------------------------------------------------------------------------------------------------|
| RF018  | Sincronização de Métricas        | Recebe e armazena os dados de ergonomia e humor coletados pelo software. |
| RF019  | Dashboard Individual    | Exibe as métricas de Stamina, tempo de uso, classificação do dia e distribuição de humor/ergonomia do próprio usuário. |
| RF020  | Visão de Desempenho da Equipe         | Permite que gestores e empresas visualizem um consolidado do nível de Stamina e classificação (Excelente a Crítico) da sua equipe. |
| RF021 | Exportação de Relatório PDF | Permite a geração e o download de um documento em formato PDF contendo os dados e gráficos do histórico do usuário ou da equipe. |

### 6.4. Suporte
| Código | Nome | Descrição |
|--------|------------------------------|---------------------------------------------------------------------------------------------------|
| RF022 | Abertura de Tickets (Chamados) | Permite que usuários de planos corporativos (colaboradores/gestores/empresas) criem tickets de suporte. |
| RF023 | Interação em Chamados | Permite a troca de mensagens dentro de um ticket aberto entre o cliente e o gestor. |
| RF024 | Edição de Mensagens | Permite que o autor edite a sua última mensagem enviada, desde que o ticket ainda conste com o status "Aberto". |
| RF025 | Exclusão de Chamados | Permite que o proprietário do ticket realize a exclusão definitiva do chamado no sistema. |


## 7. Requisitos não-funcionais
| Código | Nome | Descrição | Categoria | Classificação |
|:---|:---|:---|:---|:---|
| NF01 | Responsividade | A plataforma deverá adaptar-se automaticamente a diferentes tamanhos de tela e dispositivos. | Usabilidade | Obrigatório |
| NF02 | Segurança de dados | Implementar protocolos de segurança para proteger informações pessoais e comerciais via autenticação JWT. | Segurança | Obrigatório |
| NF03 | Compatibilidade | A plataforma deverá ser compatível com os navegadores modernos mais utilizados. | Usabilidade | Obrigatório |
| NF04 | Confiabilidade | O sistema deve ser capaz de lidar com notificações duplicadas sem corromper os dados (Idempotência) | Integridade | Obrigatório |
| NF05 | Desempenho | O processamento do MediaPipe para análise da webcam não deve comprometer a fluidez (FPS) do navegador do usuário. | Desempenho | Obrigatório |
| NF06 | Disponibilidade | O sistema de recepção de métricas (Sync) deve possuir alta disponibilidade, processando requisições rapidamente para não perder os dados em tempo real. | Disponibilidade | Obrigatório |