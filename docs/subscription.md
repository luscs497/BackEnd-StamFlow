# 🔐 Documentação: Assinaturas

Responsável pelo gerenciamento das assinaturas que permitem acessar o sistema StamFlow.

## 📊 Resumo das Rotas

| Método | Rota | Ação | Descrição | Parâmetros | Retorno |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | `/subscription/checkout/subscribe` | Realizar Assinatura | Pagamento/Realização da Assinatura. | JSON (SubscriptionCheckoutRequest) | 201 Created |
| **GET** | `/subscription/my-subscription` | Visualizar | Retorna os dados da assinatura. | Path ('subscription_id') | 200 OK |
| **PATCH** | `/subscription/update` | Atualizar | Atualização dos dados da assinatura. | JSON (SubscriptionUpdate) | 200 OK |
| **DELETE** | `/subscription/{subscription_id}` | Excluir (Soft Delete) | Cancelamento de Assinatura. | Path ('subscription_id') | 200 OK |

---

## 📝 Detalhamento das Rotas

### 🟢 Realização de Assinatura
**Endpoint:** `POST /subscription/checkout/subscribe`

Registra a Assinatura no Banco de Dados como incompleta inicialmente e redireciona o usuário para o checkout (pagamento) na plataforma do Mercado Pago.

🧠 Regras de Negócio:

- Validação de Exisência (404): O plano informado deve existir no Banco de Dados.
- Compatibilidade de Plano (400): Usuários Client só podem assinar planos do tipo individual. Usuários Company devem selecionar planos corporative.
- Fluxo de Pagamento: A assinatura nasce com status INCOMPLETE e só é ativada após a confirmação do webhook do Mercado Pago.
- Quantidade de Licenças (400): Quando é selecionado um plano corporativo, é necessário que o usuário Company selecione uma quantidade maior que 0 para gestores e colaboradores.
- Finalização do Checkout (500): Caso houver algum erro ao registrar a assinatura no Mercado Pago, um rollback é acionado.

**Payload (JSON):**
* `plan_id`: ID do Plano
* `managers_quantity`: Quantidade de Gestores para a empresa
* `employees_quantity`: Quantidade de Colaboradores para a empresa

**Resposta (201 Created):**
```json
{
    "message": "Assinatura ativada com sucesso!",
    "subscription_id": "new_subscription.id",
    "checkout_url": "checkout_url",
    "status": "mp_response.get('status')"
}
```
### 🟢 Atualização da Assinatura
**Endpoint:** `PATCH /subscription/update`

Atualiza a Assinatura no Banco de Dados para os dados de um outro Plano.

🧠 Regras de Negócio:

- Controle de Acesso (400): A rota só pode ser acessada por usuários Client ou Company.
- Compatibilidade de Plano (400): Usuários Client só podem atualizar assinatura do tipo individual. Usuários Company só podem atualizar plano corporativo.
- Validação de Existência (404): A assinatura e o plano vinculado a ela devem existir. O ID do plano passado no Schema deve corresponder a um plano existente.

**Payload (JSON):**
* `plan_id`: ID do Plano
* `managers_quantity`: Quantidade de Gestores para a empresa
* `employees_quantity`: Quantidade de Colaboradores para a empresa

**Resposta (201 Created):**
```json
{
  "plan_id": 2,
  "managers_quantity": 2,
  "employees_quantity": 2,
}
```

### 🟢 Visualizar Assinatura
**Endpoint:** `GET /subscription/my-subscription`

Retorna os dados da Assinatura do usuário.

🧠 Regras de Negócio:

- Verificação de Propriedade (403): Um usuário só pode excluir uma assinatura que pertence a ele mesmo.
- Validação de Existência (404): Para retornar os dados da assinatura, ela deve existir.

**Parâmetro:**
Nenhum.

**Resposta (200 OK):**
```json
{
  "id": 1,
  "plan": "",
  "status": "incomplete",
  "initial_date": "2026-04-08T11:38:56Z",
  "end_date": null,
  "license_quantity": 1,
  "client": "",
  "company": "",
  "mp_subscription_id": "dsfsdfn12312mfd-fdgreerf-gfd",
  "price_at_purchase": 10.99
}
```

### 🟢 Exclusão de Assinaura
**Endpoint:** `DELETE /subscription/{subscription_id}`

Realiza um Soft Delete da Assinatura. Seu status é alterado para "cancelado", é encerrada no Mercado Pago para o usuário, porém permanece registrada no Banco de Dados.

🧠 Regras de Negócio:

- Verificação de Propriedade (400): Um usuário só pode excluir uma assinatura que pertence a ele mesmo.
- Validação de Existência (404): Para retornar os dados da assinatura, ela deve existir.
- Compatibilidade de Plano (403): Usuários Client só podem excluir assinatura de planos do tipo individual. Usuários Company só podem excluir assinatura de planos do tipo corporativo.
- Finalização do Cancelamento (500): Caso houver algum erro ao cancelar a assinatura no Mercado Pago, um rollback é acionado.


**Parâmetro (Path):**
* `subscription_id`: ID da Assinatura.

**Resposta (200 OK):**
``` json
{
    "message": "Assinatura cancelada com sucesso."
}
```
