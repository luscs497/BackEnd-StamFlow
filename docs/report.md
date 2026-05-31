# 🔐 Documentação: Reports (Métricas)

Responsável pelo gerenciamento dos reports (métricas) dos usuários em relação ao seu histórico de postura e humor.

## 📊 Resumo das Rotas

| Método | Rota | Ação | Descrição | Parâmetros | Retorno |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | `/report/sync` | Sincronizar | Sincronização das métricas de postura e humor do Usuário. | JSON (SyncPayload) | 200 OK |
| **POST** | `/report/achievement` | Registrar Conquista | Registro de novas Conquistas do Usuário. | JSON (AchievementIncrementPayload) | 200 OK |
| **GET** | `/report/dashboard` | Visualizar Dashboard | Retorna os dados do dashboard de métricas individuais do Usuário. | Query ('start_date', 'end_date') | 200 OK |
| **GET** | `/report/team-dashboard` | Visualizar Dashboard da Equipe | Retorna os dados consolidados do dashboard da equipe para o Gestor. | Query ('start_date', 'end_date') | 200 OK |
| **GET** | `/report/team-achievements` | Visualizar Conquistas da Equipe | Retorna as conquistas consolidadas da equipe para o Gestor. | Query ('start_date', 'end_date') | 200 OK |
| **GET** | `/report/export` | Exportar Relatórios | Exporta os relatórios de métricas da equipe em formato CSV ou PDF. | Query ('start_date', 'end_date', 'format') | 200 OK (Arquivo CSV/PDF) |

---

## 📝 Detalhamento das Rotas

### 🟢 Sincronização das Métricas
**Endpoint:** `POST /report/sync`

Responsável pela sincronização de métricas relacionadas ao progresso do Usuário no StamFlow.

🧠 Regras de Negócio:

- Atualização dos dados: Aqui são incrementadas as conquistas e criado um Report caso ainda não exista.

**Payload (JSON):**
* `date`: Data do Report
* `shoulder`: Objeto contendo os níveis de métrica (perfeito, bom, ruim, crítico) do ombro
* `head`: Objeto contendo os níveis de métrica (perfeito, bom, ruim, crítico) da cabeça
* `rotation`: Objeto contendo os níveis de métrica (perfeito, bom, ruim, crítico) da rotação
* `back`: Objeto contendo os níveis de métrica (perfeito, bom, ruim, crítico) da coluna
* `neutral`: Objeto contendo os níveis de métrica (perfeito, bom, ruim, crítico) da emoção *neutro*
* `happy`: Objeto contendo os níveis de métrica (perfeito, bom, ruim, crítico) da emoção *feliz*
* `sad`: Objeto contendo os níveis de métrica (perfeito, bom, ruim, crítico) da emoção *triste*
* `angry`: Objeto contendo os níveis de métrica (perfeito, bom, ruim, crítico) da emoção *raiva*
* `tempo_uso_segundos`: Tempo de Uso
* `pausas_mentais_feitas`: Conquista - Pausas Mentais
* `exercicios_feitos`: Conquista - Exercícios

**Resposta (200 OK):**
```json
{
  "status": "synced"
}
```

### 🟢 Registro de Conquista
**Endpoint:** `POST /report/achievement`

Responsável pelo registro de conquistas realizadas pelo Usuário, como *pausas mentais* e *exercícios feitos*.

🧠 Regras de Negócio:

- Atualização de dados: Caso o Usuário não tenha um DailyReport ainda, este é criado e são alterados os dados de pausas mentais e exercícios feitos.

**Payload (JSON):**
* `category`: Categoria da conquista -> ['mental', 'exercicios']
* `date`: Data do registro (YYYY-MM-DD)

**Resposta (200 OK):**
```json
{
  "status": "ok"
}
```

### 🟢 Visualizar Dashboard
**Endpoint:** `GET /report/dashboard`

Retorna o dashboard com as métricas do Usuário, como stamina média, melhor dia, tempo e detalhes da ergonomia.

**Payload:**
Nenhum

**Resposta (200 OK):**
```json
{
  "stamina_media": "82%",
  "tempo_total_uso": "42h 15m",
  "melhor_dia": "2026-04-10",
  "pior_dia": "2026-04-12",
  "distribuicao_tempo": {
    "labels": ["Foco", "Pausa", "Exercício"],
    "values": [75.5, 15.0, 9.5]
  },
  "distribuicao_humor": {
    "feliz": 60,
    "neutro": 30,
    "triste": 10
  },
  "detalhes_ergonomia": {
    "postura_correta_percentual": 85,
    "alertas_gerados": 12,
    "tempo_sentado_estimado": "38h"
  },
  "tempos_absolutos": {
    "foco": "31h 40m",
    "pausa_ativa": "4h 20m",
    "descanso": "6h 15m"
  },
  "conquistas_periodo": {
    "total": 12,
    "bronze": 6,
    "prata": 4,
    "ouro": 2
  },
  "conquistas_por_dia": [
    { "data": "2026-04-10", "quantidade": 3 },
    { "data": "2026-04-11", "quantidade": 5 },
    { "data": "2026-04-12", "quantidade": 4 }
  ]
}
```

### 🟢 Visualizar Dashboard da Equipe
**Endpoint:** `GET /report/team-dashboard`

Retorna o Dashboard com as métricas/dados da equipe pertencente àquele Gestor.

🧠 Regras de Negócio:

- Agregação de Dados: Consolida os dados de métricas/conquistas de todos os colaboradores pertencentes à empresa do Gestor.

**Payload:**
Nenhum

**Resposta (200 OK):**
```json
{
  "stamina_media": "78%",
  "tempo_total_uso": "240h 00m",
  "melhor_dia": "2026-04-09",
  "pior_dia": "2026-04-13",
  "distribuicao_tempo": {
    "labels": ["Trabalho", "Pausas", "Engajamento"],
    "values": [80, 10, 10]
  },
  "distribuicao_humor": {
    "feliz": 50,
    "neutro": 40,
    "triste": 10
  },
  "detalhes_ergonomia": null,
  "tempos_absolutos": {
    "media_por_colaborador": "40h"
  },
  "conquistas_periodo": {
    "total": 150
  },
  "conquistas_por_dia": [],
  "engajamento": {
    "exercicios_feitos": 45,
    "pausas_mentais_feitas": 32,
    "tickets_total": 8
  }
}
```

### 🟢 Visualizar Conquistas da Equipe
**Endpoint:** `GET /report/team-achievements`

Retorna as conquistas da equipe daquele Gestor.

🧠 Regras de Negócio:

- Agregação de Dados: Consolida os dados de métricas/conquistas de todos os colaboradores pertencentes à empresa do Gestor.

**Payload:**
Nenhum

**Resposta (200 OK):**
```json
{
  "total": {
    "total": 150,
    "ouro": 20,
    "prata": 50,
    "bronze": 80
  },
  "por_cliente": [
    {
      "client_id": 10,
      "nome": "João Silva",
      "conquistas": {
        "total": 15,
        "ultimo_alcance": "2026-04-14T10:00:00Z"
      }
    },
    {
      "client_id": 11,
      "nome": "Maria Oliveira",
      "conquistas": {
        "total": 22,
        "ultimo_alcance": "2026-04-13T15:30:00Z"
      }
    }
  ]
}
```

### 🟢 Exportar Relatórios
**Endpoint:** `GET /report/export`

Responsável por exportar os relatórios dos Reports para arquivos CSV/PDF.

🧠 Regras de Negócio:

- Controle de Acesso (403): Apenas Gestores podem acessar a rota.
- Dados do Período (404): É necessário haver dados dentro daquele período de tempo selecionado.

**Payload:**
Nenhum

**Resposta (200 OK):**
*(Download do Arquivo)*
O endpoint não retorna um JSON, mas sim um stream de dados (arquivo físico) no formato selecionado (`.csv` ou `.pdf`), definido no header `Content-Disposition`.