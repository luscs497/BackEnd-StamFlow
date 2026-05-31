# 🔐 Documentação: Usuário Company

Responsável pelas operações que envolvem ou modificam diretamente o tipo de usuário Company. 

## 📊 Resumo das Rotas

| Método | Rota | Ação | Descrição | Parâmetros | Retorno |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | `/company/register` | Registrar | Registro da Empresa no Banco de Dados. | JSON (CompanyCreate) | 201 Created |
| **GET** | `/company/` | Visualizar | Retorna os dados do perfil da Empresa. | Nenhum | 200 OK |
| **GET** | `/company/all` | Visualizar Empresas | Retorna os dados de todas as Empresas. | Nenhum | 200 OK |
| **PATCH** | `/company/update` | Atualizar | Atualização dos dados de perfil de Empresa. | Nenhum | 200 OK |
| **DELETE** | `/company/{company_id}` | Excluir | Exclusão de determinada Empresa. | Path ('company_id') | 204 No Content |
| **GET** | `/company/team` | Visualizar Colaboradores e Gestores | Retorna todos os participantes da equipe da Empresa. | Nenhum | 200 OK |

---

## 📝 Detalhamento das Rotas

### 🟢 Registro de Empresa (Company)
**Endpoint:** `POST /company/register`

Registra a Empresa no Banco de Dados.

🧠 Regras de Negócio:

- Unicidade de Identidade (400): O sistema impede o cadastro se o CNPJ ou E-mail já estiverem vinculados a outra conta.
- Persistência Segura: A senha é convertida em senha_hash antes da gravação para garantir a segurança.
- Fluxo de cadastro: Primeiro, a empresa se registra no StamFlow e após isso pode definir a quantidade de licenças desejadas, por meio da rota `/subscription/checkout/subscribe`.

**Payload (JSON):**
* `nome_fantasia`: Nome Fantasia da Empresa
* `razao_social`: Razão Social da Empresa
* `email`: Email da Empresa
* `cnpj`: CNPJ da Empresa
* `telefone`: Telefone da Empresa
* `senha`: Senha da Empresa

**Resposta (201 Created):**
```json
{
    "id": 1,
    "nome_fantasia": "Empresa de Natal",
    "razao_social": "Empresa LTDA",
    "email": "empresa@email.com",
    "cnpj": "00.000.000/0001-00",
    "telefone": "(84) 99999-9999",
    "max_gestores": 0,
    "max_funcionarios": 0
}
```

### 🟢 Visualizar
**Endpoint:** `GET /company/`

Retorna os dados do perfil da Empresa.

**Parâmetro:**
Nenhum.

**Resposta (200 OK):**
```json
{
    "id": 1,
    "nome_fantasia": "Empresa de Natal",
    "razao_social": "Empresa LTDA",
    "email": "empresa@email.com",
    "cnpj": "00.000.000/0001-00",
    "telefone": "(84) 99999-9999",
    "max_gestores": 5,
    "max_funcionarios": 25
}
```

### 🟢 Visualizar Todas as Empresas
**Endpoint:** `GET /company/all`

Retorna os dados de todas as Empresas cadastradas no sistema.

**Parâmetro:**
Nenhum.

**Resposta (200 OK):**
```json
[
    {
        "id": 1,
        "nome_fantasia": "Empresa de Natal",
        "razao_social": "Empresa LTDA",
        "email": "empresa@email.com",
        "cnpj": "00.000.000/0001-00",
        "telefone": "(84) 99999-9999",
        "max_gestores": 5,
        "max_funcionarios": 25
    },
    {
        "id": 2,
        "nome_fantasia": "Empresa de Recife",
        "razao_social": "Empresa Recife LTDA",
        "email": "empresarecife@email.com",
        "cnpj": "00.000.000/0001-00",
        "telefone": "(81) 99999-9999",
        "max_gestores": 6,
        "max_funcionarios": 30
    },
]
```

### 🟢 Atualização dos dados da Empresa (Company)
**Endpoint:** `PATCH /company/update`

Atualiza os dados da Empresa no Banco de Dados.
- Se houver um IntegrityError, ou seja, se a empresa digitar um CNPJ ou e-mail já cadastrado no sistema, é retornado um HTTPException do tipo 400 (Bad Request).

**Payload (JSON):**
* `nome_fantasia`: Nome Fantasia da Empresa
* `razao_social`: Razão Social da Empresa
* `email`: Email da Empresa
* `cnpj`: CNPJ da Empresa
* `telefone`: Telefone da Empresa
* `senha`: Senha da Empresa

**Resposta (200 OK):**
```json
{
    "id": 1,
    "nome_fantasia": "Empresa de Natal",
    "razao_social": "Empresa LTDA",
    "email": "empresa@email.com",
    "cnpj": "33.010.000/0001-00",
    "telefone": "(84) 99999-9879",
    "max_gestores": 5,
    "max_funcionarios": 25
}
```

### 🟢 Exclusão de Empresa
**Endpoint:** `DELETE /company/{company_id}`

Responsável por deletar uma Empresa do Banco de Dados.

🧠 Regras de Negócio:

- Validação de Existência (404): A operação só prossegue se o ID da empresa for localizado no banco de dados.
- Integridade Referencial: Ao deletar uma empresa, o sistema realiza o cascade delete para gestores e colaboradores vinculados.

**Parâmetro (Path):**
* `company_id`: ID da Empresa.

**Resposta (204 No Content)**

### 🟢 Visualizar Time da Empresa
**Endpoint:** `GET /company/team`

🧠 Regras de Negócio:

- Agregação de Dados: A rota consolida em uma única resposta todos os usuários do tipo Manager e Client associados à empresa.

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
        "id": 1,
        "nome": "Alexandre Duarte Ferreira",
        "cpf": "700.435.984-61",
        "telefone": "(84) 91239-8799",
        "email": "alexandre@email.com",
        "company_id": 2
    }
]
```