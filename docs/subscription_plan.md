# 🔐 Documentação: Assinaturas

Responsável pelo gerenciamento dos Planos de Assinatura para utilização do sistema StamFlow.

## 📊 Resumo das Rotas

| Método | Rota | Ação | Descrição | Parâmetros | Retorno |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | `/subscription_plan/register` | Registrar | Registro do Plano de Assinatura no Banco. | JSON (SubscriptionPlanCreate) | 201 Created |
| **GET** | `/subscription_plan/plans` | Visualizar Planos | Retorna os dados de todos os Planos de Assinatura. | Nenhum | 200 OK |
| **PATCH** | `/subscription_plan/update/{plan_id}` | Atualizar | Atualização dos dados de determinado Plano de Assinatura. | Path ('plan_id') | 200 OK |
| **DELETE** | `/subscription_plan/{plan_id}` | Excluir (Soft Delete) | Exclusão de determinado Plano de Assinatura. | Path ('plan_id') | 204 No Content |

---

## 📝 Detalhamento das Rotas

### 🟢 Registro do Plano de Assinatura
**Endpoint:** `POST /subscription_plan/register`

Registra o Plano de Assinatura no Banco de Dados.

🧠 Regras de Negócio:

- Registro do Plano: O plano só é registrado no Banco de Dados. No Mercado Pago, utilizamos a forma de assinatura dinâmica, uma vez que os valores a serem cobrados dependem da quantidade de licenças desejadas por determinada Empresa (no caso de plano corporativo).

**Payload (JSON):**
* `name`: Nome do Plano
* `price_in_cents`: Preço do Plano em centavos
* `description`: Descrição do Plano
* `type`: Tipo do Plano - Enum de PlanType - ['corporative', 'individual']
* `period`: Periodicidade do Plano - Enum de PlanPeriod - ['monthly', 'quarterly', 'semiannual', 'annual']

**Resposta (201 Created):**
```json
{
    "id": 1,
    "name": "Plano Pro",
    "price_in_cents": 5990,
    "description": "O Plano Pro oferece acesso total ao StamFlow",
    "type": "individual",
    "period": "monthly",
    "is_active": true
}
```

### 🟢 Visualizar Todos os Planos de Assinatura
**Endpoint:** `GET /subscription_plan/plans`

Retorna os dados de todos os Planos de Assinatura **ativos**.

**Parâmetro:**
Nenhum.

**Resposta (200 OK):**
```json
[
    {
        "id": 1,
        "name": "Plano Pro",
        "price_in_cents": 5990,
        "description": "O Plano Pro oferece acesso total ao StamFlow",
        "type": "individual",
        "period": "monthly",
        "is_active": true
    },
    {
        "id": 2,
        "name": "Plano Base",
        "price_in_cents": 3990,
        "description": "O Plano Base oferece acesso a algumas features do StamFlow",
        "type": "individual",
        "period": "annual",
        "is_active": true
    }
]
```

### 🟢 Atualização de Plano de Assinatura
**Endpoint:** `PATCH /subscription_plan/update/{plan_id}`

Atualiza o Plano de Assinatura no Banco de Dados (todos os campos são editáveis).

🧠 Regras de Negócio:

- Validação de Existência (404): O ID passado na rota deve corresponder a um Plano existente.

**Payload (JSON):**
* `name`: Nome do Plano
* `price_in_cents`: Preço do Plano em centavos
* `description`: Descrição do Plano
* `type`: Tipo do Plano - Enum de PlanType - ['corporative', 'individual']
* `period`: Periodicidade do Plano - Enum de PlanPeriod - ['monthly', 'quarterly', 'semiannual', 'annual']
* `is_active`: Boolean que indica se o Plano está ativo ou inativo

**Resposta (200 OK):**
```json
{
    "id": 1,
    "name": "Plano Pro",
    "price_in_cents": 19990,
    "description": "O Plano Pro oferece acesso total ao StamFlow",
    "type": "individual",
    "period": "monthly",
    "is_active": true
}
```

### 🟢 Exclusão de Plano de Assinaura
**Endpoint:** `DELETE /subscription_plan/{plan_id}`

Realiza um Soft Delete do Plano de Assinatura. Seu campo *is_active* é alterado para **False**.

🧠 Regras de Negócio:

- Status de Disponibilidade: Planos "excluídos" são apenas desativados (is_active = False) para manter a integridade das assinaturas que já o utilizam.
- Validação de Existência (404): O ID passado na rota deve corresponder a um Plano existente.

**Parâmetro (Path):**
* `plan_id`: ID do Plano de Assinatura.

**Resposta (200 OK):**
``` json
{
    "message": "Plano desativado com sucesso."
}
```
