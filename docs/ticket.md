# 🔐 Documentação: Tickets

Responsável pelo gerenciamento de tickets (mensagens trocadas entre colaboradores e gestores) acerca de algum problema na empresa.

## 📊 Resumo das Rotas

| Método | Rota | Ação | Descrição | Parâmetros | Retorno |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | `/ticket/` | Registrar | Registro de ticket. | JSON (TicketCreate) | 201 Created |
| **GET** | `/ticket/my-tickets` | Visualizar | Retorna os tickets pertencentes àquele usuário. | JSON (Lista de TicketResponse) | 200 OK |
| **PUT** | `/ticket/{ticket_id}/message` | Editar Mensagem | Atualização da mensagem do ticket. | Path ('ticket_id') | 200 OK |
| **DELETE** | `/ticket/{ticket_id}` | Excluir | Exclusão de ticket. | Path ('ticket_id') | 204 No Content |
| **GET** | `/ticket/company-tickets` | Visualizar Tickets da Empresa | Retorna todos os tickets da empresa. | Cookie ('access_token') | 200 OK |
| **PATCH** | `/ticket/{ticket_id}/status` | Atualizar | Retorna os dados do convite. | Path ('ticket_id') | 200 OK |
| **POST** | `/ticket/{ticket_id}/reply` | Resposta | Envia uma resposta ao ticket. | Path ('ticket_id') | 201 Created |

---

## 📝 Detalhamento das Rotas

### 🟢 Registro de Ticket
**Endpoint:** `POST /ticket/`

Responsável pelo registro de tickets e pela criação das mensagens.

🧠 Regras de Negócio:

- Controle de Ação (400): Apenas usuários que possuem um `company_id` podem criar Tickets.

**Payload (JSON):**
* `assunto`: Assunto do Ticket
* `mensagem_inicial`: Mensagem do Ticket

**Resposta (201 Created)**

### 🟢 Visualizar Meus Tickets
**Endpoint:** `GET /ticket/my-tickets`

Lista os tickets pertencentes ao Usuário.

🧠 Regras de Negócio:

- Retorna todos os tickets de um Client específico com suas respectivas mensagens.

**Payload:**
Nenhum

**Resposta (200 OK):**
```json
[
  {
    "id": 1,
    "assunto": "Assunto Geral",
    "status": "aberto",
    "criado_em": "2026-04-14T11:38:56Z",
    "atualizado_em": "2026-04-14T11:38:56Z",
    "messages": [
      {
        "id": 2,
        "author_type": "cliente",
        "content": "Mensagem",
        "criado_em": "2026-04-14T11:39:56Z"
      }
    ]
  },
  {
    "id": 2,
    "assunto": "Assunto Específico",
    "status": "aberto",
    "criado_em": "2026-04-15T11:38:56Z",
    "atualizado_em": "2026-04-16T11:38:56Z",
    "messages": [
      {
        "id": 2,
        "author_type": "cliente",
        "content": "Mensagem",
        "criado_em": "2026-04-15T11:39:56Z"
      }
    ]
  }
]  
```
### 🟢 Editar Mensagem do Ticket
**Endpoint:** `PUT /ticket/{ticket_id}/message`

Responsável por editar mensagens dos Tickets.

🧠 Regras de Negócio:

- Validação de Existência (404): Valida se o Ticket existe antes de tentar sua alteração.
- Verificação de Propriedade (403): Valida se o Ticket pertence ao Usuário que acessou a rota.
- Verificação de Status (400): Só é possível atualizar um Ticket que possua status `aberto`.
- Validação de Existência de Mensagem Prévia (404): Valida se o Ticket possui uma mensagem prévia.

**Payload (JSON):**
* `content`: Nova Mensagem

**Resposta (200 OK):**
```json
{
    "id": 2,
    "assunto": "Assunto Específico",
    "status": "aberto",
    "criado_em": "2026-04-15T11:38:56Z",
    "atualizado_em": "2026-04-16T11:38:56Z",
    "messages": [
      {
        "id": 2,
        "author_type": "cliente",
        "content": "Mensagem",
        "criado_em": "2026-04-15T11:39:56Z"
      }
    ]
  }
```

### 🟢 Exclusão de Ticket
**Endpoint:** `DELETE /ticket/{ticket_id}`

Exclui o ticket no Banco de Dados. 

🧠 Regras de Negócio:

- Validação de Existência (404): Valida se o Ticket existe antes de tentar sua exclusão.
- Verificação de Propriedade (403): Valida se o Ticket pertence ao Usuário que acessou a rota.

**Parâmetro (Path):**
* `ticket_id`: ID do ticket

**Resposta (204 No Content)**

### 🟢 Visualizar Tickets da Empresa
**Endpoint:** `GET /ticket/company-tickets`

Lista os tickets pertencentes à Empresa do Gestor.

🧠 Regras de Negócio:

- Agregação de Dados: Retorna todos os tickets da Empresa da qual o Gestor faz parte.

**Payload:**
Nenhum

**Resposta (200 OK):**
```json
[
  {
    "id": 1,
    "assunto": "Assunto Geral",
    "status": "aberto",
    "criado_em": "2026-04-14T11:38:56Z",
    "atualizado_em": "2026-04-14T11:38:56Z",
    "messages": [
      {
        "id": 2,
        "author_type": "cliente",
        "content": "Mensagem",
        "criado_em": "2026-04-14T11:39:56Z"
      }
    ]
  },
  {
    "id": 2,
    "assunto": "Assunto Específico",
    "status": "aberto",
    "criado_em": "2026-04-15T11:38:56Z",
    "atualizado_em": "2026-04-16T11:38:56Z",
    "messages": [
      {
        "id": 2,
        "author_type": "cliente",
        "content": "Mensagem",
        "criado_em": "2026-04-15T11:39:56Z"
      }
    ]
  }
]
```

### 🟢 Editar Status do Ticket
**Endpoint:** `PATCH /ticket/{ticket_id}/status`

Responsável pela alteração do status do Ticket.

🧠 Regras de Negócio:

- Validação de Existência (404): Valida se o Ticket existe ou se o ticket pertence à mesma Empresa do Gestor.

**Payload (JSON):**
* `status`: Status do Ticket -> ['aberto', 'em_andamento', 'concluido']

**Resposta (200 OK):**
```json
{
    "id": 2,
    "assunto": "Assunto Específico",u
    "status": "concluido",
    "criado_em": "2026-04-15T11:38:56Z",
    "atualizado_em": "2026-04-16T11:38:56Z",
    "messages": [
      {
        "id": 2,
        "author_type": "cliente",
        "content": "Mensagem",
        "criado_em": "2026-04-15T11:39:56Z"
      }
    ]
  }
```

### 🟢 Ticket de Resposta
**Endpoint:** `POST /ticket/{ticket_id}/reply`

Responsável pelo registro de tickets de resposta.

🧠 Regras de Negócio:

- Controle de Acesso (401): Apenas Clients e Managers podem fazer a utilização da rota.
- Validação de Existência (403): Valida se o Ticket existe ou se o ticket pertence à mesma Empresa do Usuário.
- Verificação de Propriedade (403): Verifica se o Ticket pertence àquele usuário.

**Payload (JSON):**
* `content`: Conteúdo do Ticket de Resposta

**Resposta (201 Created)**