# 🔐 Documentação: Webhooks (Mercado Pago)

Responsável por receber as notificações do Mercado Pago sobre atualizações de pagamentos e status das assinaturas, mantendo o Banco de Dados do StamFlow sincronizado.

> Esta rota não é consumida pelo Front-end da aplicação. Ela é uma URL de escuta (Callback) configurada no painel de desenvolvedor do Mercado Pago.

## 📊 Resumo das Rotas

| Método | Rota | Ação | Descrição | Parâmetros | Retorno |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | `/webhook/mercadopago` | Receber Notificação | Recebe e processa eventos de assinaturas do MP. | Payload MP | 200 OK |

---

## 📝 Detalhamento das Rotas

### 🟢 Recebimento de Webhook (Mercado Pago)
**Endpoint:** `POST /webhook/mercadopago`

Recebe a notificação de atualização, consulta o status real da assinatura via SDK do Mercado Pago e atualiza o sistema.

🧠 Regras de Negócio:

- **Registro de Log:** Toda requisição cria um registro na tabela `webhook_logs` com o status inicial `processing`.
- **Assinatura Autorizada:** Se o status no MP for `authorized`, o Banco de Dados é atualizado e as licenças da empresa (`max_gestores` e `max_funcionarios`) são liberadas.
- **Assinatura Cancelada/Pausada:** Se o status no MP for `cancelled` ou `paused`, o status da assinatura local é alterado para `canceled`.
- **Eventos não mapeados:** Se o webhook for de um tópico não tratado pelo sistema, o log é atualizado para `ignored`.
- No fim do processo, o log de webhook é atualizado para `success`.

**Payload (JSON do Mercado Pago):**
O payload segue o formato padrão de notificações do Mercado Pago (Webhooks / IPN), contendo tipicamente:
* `type` ou `topic`: Tipo do evento (ex: `preapproval` ou `payment`)
* `data.id`: ID do recurso a ser consultado.

**Resposta (200 OK):**
O Mercado Pago exige que a resposta seja sempre um status 2XX para confirmar o recebimento, independente do que aconteceu internamente.
```json
{
  "status": "success"
}
```