# 🔐 Documentação: Usuário Manager

Responsável pelas operações que envolvem ou modificam diretamente o tipo de usuário Manager. 

## 📊 Resumo das Rotas

| Método | Rota | Ação | Descrição | Parâmetros | Retorno |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | `/manager/register` | Registrar | Registro do Gestor no Banco de Dados. | JSON (ManagerCreate) | 201 Created |
| **GET** | `/manager/` | Visualizar | Retorna os dados do perfil do Gestor. | Nenhum | 200 OK |
| **PATCH** | `/manager/update` | Atualizar | Atualização dos dados de perfil do Gestor. | Nenhum | 200 OK |
| **DELETE** | `/manager/{manager_id}` | Excluir | Exclusão de determinado Gestor. | Path ('manager_id') | 204 No Content |
| **GET** | `/manager/team` | Visualizar Colaboradores | Retorna todos os participantes da equipe específica do Gestor. | Nenhum | 200 OK |

---

## 📝 Detalhamento das Rotas

### 🟢 Registro de Gestor (Manager)
**Endpoint:** `POST /manager/register`

Registra o Gestor no Banco de Dados.

🧠 Regras de Negócio:

- Validação de token (404): O *token* passado na URL deve ser existente e correspondente a um Convite.
- Status do Convite (400): Para o registro, o status do convite deve ser *pending*.
- Expiração do Convite (400): A data de expiração deve ser maior do que a data atual.
- Integridade de Dados (400): `email` e `cpf` são dados que devem ser únicos.

**Payload (JSON):**
* `nome`: Nome do Gestor
* `cpf`: CPF do Gestor
* `telefone`: Telefone do Gestor
* `senha`: Senha do Gestor
* `token`: Token presente na URL da página

**Resposta (201 Created):**
```json
{
    "id": 1,
    "nome": "Alexandre Duarte",
    "cpf": "700.435.984-61",
    "telefone": "(84) 91239-9999",
    "email": "alexandre@email.com",
    "company_id": 2
}
```

### 🟢 Visualizar Perfil
**Endpoint:** `GET /manager/`

Retorna os dados do perfil do Gestor.

**Parâmetro:**
Nenhum.

**Resposta (200 OK):**
```json
{
    "id": 1,
    "nome": "Alexandre Duarte",
    "cpf": "700.435.984-61",
    "telefone": "(84) 91239-9999",
    "email": "alexandre@email.com",
    "company_id": 2
}
```

### 🟢 Atualização dos dados do Gestor (Manager)
**Endpoint:** `PATCH /manager/update`

Atualiza os dados do Gestor no Banco de Dados.

🧠 Regras de Negócio:

- Integridade de Dados (400): `email` e `cpf` são dados que devem ser únicos.

**Payload (JSON):**
* `nome`: Nome do Gestor
* `cpf`: CPF do Gestor
* `telefone`: Telefone do Gestor
* `senha`: Senha do Gestor
* `token`: Token presente na URL da página

**Resposta (200 OK):**
```json
{
    "id": 1,
    "nome": "Alexandre Duarte Ferreira",
    "cpf": "700.435.984-61",
    "telefone": "(84) 91239-8799",
    "email": "alexandre@email.com",
    "company_id": 2
}
```

### 🟢 Exclusão de Gestor
**Endpoint:** `DELETE /manager/{manager_id}`

Responsável por deletar um Gestor do Banco de Dados.

🧠 Regras de Negócio:

- Verificação de Propriedade (403): Uma empresa só pode deletar gestores que pertençam ao seu próprio `company_id`.
- Validação de Existência (404): Valida se o gestor existe antes de tentar a exclusão.

**Parâmetro (Path):**
* `manager_id`: ID do Gestor.

**Resposta (204 No Content)**

### 🟢 Visualizar Time do Gestor
**Endpoint:** `GET /manager/team`

🧠 Regras de Negócio:

- Agregação de Dados: A rota retorna todos os usuários do tipo Client associados ao gestor.

**Parâmetro:**
Nenhum.

**Resposta (200 OK):**
```json
[
    {
        "id": 5,
        "nome_completo": "Davi Neves Ferreira",
        "cpf": "790.355.984-61",
        "telefone": "(84) 94569-8799",
        "email": "davi@email.com",
        "company_id": 2,
        "manager_id": 1,
        "criado_em": "2026-04-08T11:38:56Z"
    },
    {
        "id": 9,
        "nome_completo": "João da Silva Ferreira",
        "cpf": "800.378.084-61",
        "telefone": "(84) 96549-8799",
        "email": "joao@email.com",
        "company_id": 2,
        "manager_id": 1,
        "criado_em": "2026-04-09T11:38:56Z"
    },
]
```