# 🔐 Documentação: Convites de Colaboradores

Responsável pelo gerenciamento de convites enviados por usuários dos tipos Manager/Company aos colaboradores para integrar o time no StamFlow.

## 📊 Resumo das Rotas

| Método | Rota | Ação | Descrição | Parâmetros | Retorno |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | `/invite/register` | Registrar | Cadastro de convite individual. | JSON (InviteCreate) | 201 Created |
| **POST** | `/invite/register/bulk` | Registrar Em Massa | Convida múltiplos colaboradores. | JSON (Lista de InviteCreate) | 201 Created |
| **DELETE** | `/invite/bulk` | Excluir Em Massa | Exclusão de colaboradores em massa. | JSON (InviteBulkDelete) | 204 No Content |
| **GET** | `/invite/invites` | Listar | Retorna todos os convites realizados pelo usuário autenticado. | Cookie ('access_token') | 200 OK |
| **GET** | `/invite/{invite_id}` | Visualizar | Retorna os dados do convite. | Path ('invite_id') | 200 OK |
| **DELETE** | `/invite/{invite_id}` | Excluir | Exclusão de convite individual. | Path ('invite_id') | 204 No Content |
| **POST** | `/invite/upload` | Realizar Upload CSV | Importa lista de convites via arquivo CSV. | Arquivo (UploadFile) | 200 OK |

---

## 📝 Detalhamento das Rotas

### 🟢 Registro de Convite
**Endpoint:** `POST /invite/register`

Registra o convite no Banco de Dados e envia o e-mail para o destinatário. 

🧠 Regras de Negócio:

- Controle de Acesso (403): Apenas usuários Company ou Manager podem emitir convites.
- Prevenção de Duplicidade (400): Não é permitido enviar um novo convite para um e-mail que já possua um convite pendente e dentro do prazo de validade.
- Verificação de Quota (403): O sistema valida se a empresa ainda possui "vagas" disponíveis (gestores ou funcionários) de acordo com o plano contratado antes de gerar o convite.

**Payload (JSON):**
* `email`: Email do usuário
* `role`: Cargo do usuário -> ['manager', 'employee']

**Resposta (201 Created):**
```json
{
  "message": "Convite para Gestor enviado com sucesso para o e-mail user@example.com."
}
```

### 🟢 Registro de Convites em Massa
**Endpoint:** `POST /invite/register/bulk`

Registra os convites no Banco de Dados em massa e envia o e-mail para os destinatários. 

🧠 Regras de Negócio:

- Controle de Acesso (403): Apenas usuários Company ou Manager podem emitir convites.
- Permissão para Convite (403): Apenas usuários Company podem convidar usuários Manager. Usuários Manager só podem convidar usuários Client.
- Convidar e-mail convidado e ainda válido (400): O sistema proíbe realizar um outro convite para e-mail convidado ainda válido.
- Verificação de Quota (403): O sistema valida se a empresa ainda possui "vagas" disponíveis (gestores ou funcionários) de acordo com o plano contratado antes de gerar o convite.

**Payload (JSON):**
Lista[
* `email`: Email do usuário
* `role`: Cargo do usuário -> ['manager', 'employee']
]

**Resposta (201 Created):**
```json
{
  "message": "10 convites gerados com sucesso e estão sendo enviados."
}
```

### 🟢 Exclusão de Convites em Massa
**Endpoint:** `DELETE /invite/bulk`

Exclui os convites no Banco de Dados em massa. 

🧠 Regras de Negócio:

- Controle de Acesso (403): Apenas usuários Company ou Manager podem excluir convites.
- Validação de Existência (404): A operação só prossegue se o ID do convite for localizado no banco de dados.
- Integridade de Dados (500): Qualquer falha de comunicação durante a exclusão no Banco de Dados aciona um rollback automático, desfazendo a operação para evitar dados inconsistentes.

**Payload (JSON):**
Lista `invite_ids`

**Resposta (204 No Content)**

### 🟢 Listar Convites
**Endpoint:** `GET /invite/invites`

Lista os convites pertencentes ao usuário autenticado.

**Payload:**
Nenhum

**Resposta (200 OK):**
```json
[
  {
    "id": 1,
    "email": "user@example.com",
    "role": "employee",
    "status": "pending",
    "created_at": "2026-04-08T11:38:56Z",
    "expires_at": "2026-04-15T11:38:56Z",
    "token": "hash_do_token_gerado",
    "company_id": 2,
    "manager_id": 4
  },
  {
    "id": 2,
    "email": "user2@example.com",
    "role": "manager",
    "status": "pending",
    "created_at": "2026-03-08T11:38:56Z",
    "expires_at": "2026-03-15T11:38:56Z",
    "token": "hash_do_token_gerado",
    "company_id": 2,
    "manager_id": null
  },
]
```

### 🟢 Visualizar Convite
**Endpoint:** `GET /invite/{invite_id}`

Lista o convite referente ao id passado.

🧠 Regras de Negócio:

- Validação de Existência (404): A operação só prossegue se o ID do convite for localizado no banco de dados.

**Parâmetro (Path):**
* `invite_id`: ID do convite

**Resposta (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "role": "employee",
  "status": "pending",
  "created_at": "2026-04-08T11:38:56Z",
  "expires_at": "2026-04-15T11:38:56Z",
  "token": "hash_do_token_gerado",
  "company_id": 2,
  "manager_id": 4
}
```

### 🟢 Exclusão de Convite
**Endpoint:** `DELETE /invite/{invite_id}`

Exclui o convite no Banco de Dados. 

🧠 Regras de Negócio:

- Validação de Existência (404): A operação só prossegue se o ID do convite for localizado no banco de dados.
- Permissão para Convite (403): Company e Manager só podem excluir convites que os pertencem.

**Parâmetro (Path):**
* `invite_id`: ID do convite

**Resposta (204 No Content)**

### 🟢 Registro de Convites via Upload CSV
**Endpoint:** `POST /invite/upload`

Registra os convites no Banco de Dados em massa e envia o e-mail para os destinatários de acordo com os dados do arquivo CSV. 

🧠 Regras de Negócio:

- Validação de Formato e Conteúdo (400): O arquivo deve ser obrigatoriamente .csv com codificação utf-8-sig ou latin-1, além de não poder ser enviado vazio.
- Convidar e-mail convidado e ainda válido (400): O sistema proíbe realizar um outro convite para e-mail convidado ainda válido.
- Consistência de Colunas (400): Para empresas, exige-se 3 colunas (Nome, E-mail, Cargo). Para gestores, apenas 2 (Nome, E-mail), pois o cargo é fixado como employee.
- Controle de Acesso (403): Apenas usuários Company ou Manager podem emitir convites. 
- Verificação de Quota (403): O sistema valida se a empresa ainda possui "vagas" disponíveis (gestores ou funcionários) de acordo com o plano contratado antes de gerar o convite.
- Processamento em Massa: Convites válidos são disparados via Background Tasks para não travar a resposta da API.

**Payload (Body - Form Data):**
* `file`: Arquivo CSV

**Resposta (201 Created):**
```json
{
  "message": "Arquivo CSV enviado."
}
```