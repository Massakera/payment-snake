# Rinha Backend 2025 - Performance Optimized

Uma solução ultra-performática para a Rinha de Backend 2025, focada em atingir P99 < 11ms para maximizar o bônus de performance.

## 🚀 Tecnologias Utilizadas

- **FastAPI + Uvicorn + Gunicorn** - Framework web assíncrono de alta performance
- **PostgreSQL + asyncpg** - Banco de dados com connection pooling otimizado
- **Nginx** - Load balancer com configurações de performance
- **Docker + Docker Compose** - Containerização e orquestração
- **Circuit Breaker Pattern** - Resiliência e fallback inteligente
- **Background Health Monitoring** - Monitoramento de saúde dos processadores

## 🏗️ Arquitetura

### Componentes Principais

1. **Load Balancer (Nginx)**
   - Distribuição de carga entre 2 instâncias da aplicação
   - Rate limiting e otimizações de performance
   - Health checks automáticos

2. **Application Layer (FastAPI)**
   - 2 instâncias para alta disponibilidade
   - Processamento assíncrono de pagamentos
   - Validação otimizada de dados

3. **Database Layer (PostgreSQL)**
   - Connection pooling otimizado
   - Prepared statements para performance
   - Índices otimizados para queries

4. **Payment Processors**
   - Integração com 2 processadores de pagamento
   - Circuit breaker pattern para resiliência
   - Health monitoring em background

## ⚡ Otimizações de Performance

### HTTP Client
- Connection pooling com 100 conexões
- Timeouts agressivos (500ms total)
- JSON serialization otimizada
- Compressão desabilitada para reduzir CPU

### Database
- Prepared statements pré-compilados
- Connection pool com 10-50 conexões
- Configurações PostgreSQL otimizadas
- Índices para queries de summary

### Health Monitoring
- Background monitoring a cada 4.5s
- Cache de status de saúde
- Rate limiting respeitado (1 req/5s)
- Fallback inteligente

### Circuit Breaker
- Threshold de 5 falhas
- Timeout de recuperação de 30s
- Estados: CLOSED, OPEN, HALF_OPEN
- Prevenção de cascata de falhas

## 🐳 Execução

### Pré-requisitos
- Docker e Docker Compose
- Rede `payment-processor` criada pelos processadores

### Comandos

```bash
# 1. Subir os Payment Processors primeiro
cd payment-processor
docker-compose up -d

# 2. Subir o backend
cd ..
docker-compose up -d

# 3. Verificar logs
docker-compose logs -f
```

### Endpoints

- `POST /payments` - Processar pagamento
- `GET /payments-summary` - Resumo de pagamentos
- `GET /health` - Health check
- `GET /status` - Status dos processadores

## 📊 Métricas Esperadas

- **P99 Target**: < 5ms (12% bônus)
- **Database queries**: < 1ms
- **HTTP client calls**: < 300ms
- **Memory usage**: < 350MB total
- **CPU usage**: < 1.5 cores total

## 🔧 Configurações de Recursos

- **Nginx**: 0.1 CPU, 50MB RAM
- **App1/App2**: 0.6 CPU, 150MB RAM cada
- **PostgreSQL**: 0.1 CPU, 50MB RAM
- **Total**: 1.4 CPU, 400MB RAM

## 🛡️ Resiliência

- **Circuit Breaker**: Previne cascata de falhas
- **Health Monitoring**: Detecção proativa de problemas
- **Load Balancing**: Distribuição de carga
- **Fallback Strategy**: Uso inteligente do processador de backup
- **Graceful Degradation**: Continua funcionando mesmo com falhas

## 📈 Estratégia de Taxas

- **Default Processor**: Sempre preferido (menor taxa)
- **Fallback Processor**: Usado apenas quando necessário
- **Health-based Routing**: Escolha baseada em status de saúde
- **Circuit Breaker**: Evita tentativas desnecessárias

## 🔍 Monitoramento

- Logs estruturados
- Health checks automáticos
- Status dos processadores
- Métricas de performance

## 🚀 Performance Features

- **Pre-allocated Objects**: Reduz alocação de memória
- **Async Processing**: Não bloqueia requisições
- **Connection Pooling**: Reutiliza conexões
- **Prepared Statements**: Queries otimizadas
- **Background Tasks**: Operações não críticas em background
- **Minimal Validation**: Validação essencial apenas
- **Optimized JSON**: Serialização otimizada
- **No ORM Overhead**: Queries diretas ao banco 