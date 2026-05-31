# 🔐 Documentação: Autenticação e Perfil

Responsável pelo controle de acesso, gestão de sessões via Cookies Globais (`.stamflow.com.br`) e manutenção de dados do usuário logado.

## 📊 Resumo das Rotas

| Método | Rota | Ação | Descrição | Parâmetros | Retorno |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | `/auth/register` | Registrar | Cadastro de novo Colaborador (via convite ou direto). | JSON (ClientCreate) | 201 Created |
| **POST** | `/auth/login` | Realizar Login | Autentica e define cookies de sessão. | Form Data (Username/Password) | 200 OK (User + Cookies) |
| **POST** | `/auth/refresh` | Renovar Access Token | Renova o Access Token silenciosamente. | Cookie ('refresh_token') | 200 OK (Novo Cookie)
| **POST** | `/auth/logout` | Realizar Logout | Encerra a sessão e limpa cookies. | Nenhum | 200 OK |
| **GET** | `/auth/me` | Visualizar Perfil|  Retorna dados do perfil atual. | Cookie ('access_token') | 200 OK |
| **PUT** | `/auth/me` | Atualizar | Atualiza dados do perfil atual. | JSON (UserUpdate) | 200 OK |
| **POST** | `/auth/forgot-password` | Recuperar Senha| Solicita recuperação de senha. | JSON (Email) | 200 OK |
| **DELETE** | `/auth/bulk` | Excluir Em Massa | Exclusão de colaboradores em massa. | JSON (Lista de IDs) | 204 No Content |
| **DELETE** | `/auth/{client_id}` | Excluir | Exclusão de colaborador individual. | Path ('client_id') | 204 No Content |

---

## 📝 Detalhamento das Rotas

### 🟢 Registro de Cliente
**Endpoint:** `POST /auth/register`

Realiza o registro de um novo usuário Client no Banco de Dados.

🧠 Regras de Negócio:

**Registro via convite, vinculado a Empresa**
- Validação de token (404): O *token* passado na URL deve ser existente e correspondente a um Convite.
- Status do Convite (400): Para o registro, o status do convite deve ser *pending*.
- Expiração do Convite (400): A data de expiração deve ser maior do que a data atual.

**Registro de um usuário avulso**
- Validação do JSON (400): Nesse caso, deve ser passado um email no Schema.

**Geral**
- Unicidade de Dados (400): O Usuário não pode se registrar com um email já existente no Banco de Dados.
- Integridade de Dados (400): `email` e `cpf` são dados que devem ser únicos.

**Payload (JSON):**
* `nome_completo`: Nome do usuário
* `cpf`: CPF do usuário
* `telefone`: Telefone do usuário
* `email`: Email do usuário
* `senha`: Senha do usuário
* `token`: Token presente no Convite

**Resposta (201 Created):**
```json
{
  "id": 10,
  "nome_completo": "Davi Barbosa Ferreira",
  "cpf": "790.355.984-61",
  "telefone": "(84) 94569-8799",
  "email": "davi@email.com",
  "company_id": null,
  "manager_id": null,
  "criado_em": "2026-04-08T11:38:56Z"
}
```

### 🟢 Login de Usuário
**Endpoint:** `POST /auth/login`

Valida as credenciais. Se bem-sucedido, define os cookies `access_token` e `refresh_token` no domínio `.stamflow.com.br`.

🧠 Regras de Negócio:

- Validação de Credenciais (401): As credenciais informadas do Usuário devem ter uma correspondência certa no Banco de Dados. 

**Payload (Body - Form Data):**
* `username`: Email do usuário
* `password`: Senha

**Resposta (200 OK):**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "user_type": "client",
    "company_id": 10,
    "manager_id": null
  },
  "message": "Login realizado com sucesso"
}
```

### 🟢 Renovar Access Token
**Endpoint:** `POST /auth/refresh`

Responsável por renovar o Access Token do usuário.

🧠 Regras de Negócio:

- Se não houver o *refresh_token_cookie*, é retornado um HTTPException do tipo 401 (Unauthorized).

**Payload:**
Nenhum.

**Resposta (200 OK):**
```json
{
  "message": "Token renovado",
  "token_type": "bearer"
}
```

### 🟢 Logout de Usuário
**Endpoint:** `POST /auth/logout`

Responsável por realizar o logout do usuário. Se bem-sucedido, deleta os cookies `access_token` e `refresh_token` no domínio `.stamflow.com.br`.

**Payload:**
Nenhum.

**Resposta (200 OK):**
```json
{
  "message": "Logout realizado com sucesso"
}
```

### 🟢 Visualizar Perfil
**Endpoint:** `GET /auth/me`

Retorna os dados do perfil do usuário (Client/Manager/Company).

🧠 Regras de Negócio:

- Controle de Acesso (400): O Usuário utilizador da rota deve ser instância de *Client*, *Manager* ou *Company*.

**Payload:**
Nenhum.

**Resposta (200 OK):**
> Client
```json
{
  "id": 1,
  "nome_completo": "Usuário 1",
  "email": "user1@example.com",
  "tipo": "client"
}
```
> Manager
```json
{
  "id": 11,
  "nome_completo": "Usuário 11",
  "email": "user11@example.com",
  "tipo": "manager"
}
```
> Company
```json
{
  "id": 5,
  "nome_completo": "Usuário 5",
  "email": "user5@example.com",
  "tipo": "company"
}
```

### 🟢 Atualização de Perfil
**Endpoint:** `PUT /auth/me`

Responsável por alterar o nome do Usuário e/ou seu email.
- Controle de Acesso (400): O Usuário utilizador da rota deve ser instância de *Client*, *Manager* ou *Company*.

**Payload (JSON):**
* `nome_completo`: Novo nome do Usuário
* `email`: Novo email do Usuário

**Resposta (200 OK):**
```json
{
  "nome_completo": "Usuário Atualizado",
  "email": "useratualizado@example.com"
}
```
### 🟢 Esqueci Minha Senha
**Endpoint:** `POST /auth/forgot-password`

Responsável por enviar um email de recuperação de senha ao usuário.
- Se o email não tiver sido passado no *payload*, é retornado um HTTPException do tipo 400 (Bad Request).

**Payload (Body - Form Data):**
* `email`: Email do usuário

**Resposta (200 OK):**
```json
{
  "message": "Link de recuperação enviado."
}
```

### 🟢 Exclusão em Massa de Usuários Client
**Endpoint:** `DELETE /auth/bulk`

Realiza a exclusão em Massa dos Usuários Client.

🧠 Regras de Negócio:

- Controle de Acesso (403): Apenas gestores (Manager) e empresas (Company) têm permissão para usar esta rota. Usuários do tipo Client são bloqueados.
- Validação de Entrada (404): A lista de IDs enviada no payload não pode estar vazia ou conter IDs inexistentes.
- Integridade de Dados (500): Qualquer falha de comunicação durante a exclusão no Banco de Dados aciona um rollback automático, desfazendo a operação para evitar dados inconsistentes.

**Payload (JSON):**
* `client_ids`: Lista de IDs

**Resposta (204 No Content)**

### 🟢 Exclusão de Usuário Individual
**Endpoint:** `DELETE /auth/{client_id}`

Realiza a exclusão de um Usuário Client.

🧠 Regras de Negócio:

- Validação do Usuário (404): O Client referenciado pelo id deve ser existente.
- Verificação de Propriedade (403): Company pode excluir qualquer Client que a pertencer, enquanto Manager pode excluir apenas Clients associados a eles.
- Controle de Acesso (403): Apenas gestores (Manager) e empresas (Company) têm permissão para usar esta rota. Usuários do tipo Client são bloqueados.

**Parâmetro (Path):**
* `client_id`: ID do Client.

**Resposta (204 No Content)**