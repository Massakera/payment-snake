================================================
FILE: README.md
================================================
# 🦀 Rinha de Backend 2025 - Rust

Este repositório contém a minha participação na **Rinha de Backend 2025**, implementada em **Rust**.

## Primeiro projeto de backend em Rust

## 🚀 Tecnologias Utilizadas

- [Rust](https://www.rust-lang.org/)
- [Axum 0.8](https://docs.rs/axum) — Web framework moderno, baseado em Tokio
- [Tokio 1.46](https://tokio.rs/) — Runtime assíncrono de alta performance
- [Serde](https://serde.rs/) — Serialização/deserialização eficiente de JSON
- [Reqwest](https://docs.rs/reqwest) — Cliente HTTP assíncrono
- [Redis 0.32](https://docs.rs/redis) — Gerenciamento de cache, fila de transações, etc
- [Chrono](https://docs.rs/chrono) — Manipulação de datas e horários

## 🚀 Como rodar

Certifique-se de ter o **Docker** e o **Docker Compose** instalados.

```bash
git clone https://github.com/andersongomes001/rinha-2025.git
cd rinha-2025
docker compose up --build
```



================================================
FILE: build-and-push.sh
================================================
#!/bin/bash

set -e
APP_NAME="rinha-api-2025"
DOCKER_USER="andersongomes001"
VERSION=$(git rev-parse --short HEAD)
IMAGE_NAME="$DOCKER_USER/$APP_NAME"

echo "🐳 Build da imagem Docker..."
docker build -t $IMAGE_NAME:$VERSION -t $IMAGE_NAME:latest .

echo "✅ Build concluído:"
echo "  - $IMAGE_NAME:$VERSION"
echo "  - $IMAGE_NAME:latest"

read -p "Deseja fazer push da imagem para Docker Hub? (s/n): " resposta
if [[ "$resposta" =~ ^[sS]$ ]]; then
    echo "🔐 Enviando imagens..."
    docker push $IMAGE_NAME:$VERSION
    docker push $IMAGE_NAME:latest
    echo "🎉 Imagens enviadas!"
fi

#docker build -t andersongomes001/rinha-api-2025:latest .
#docker push andersongomes001/rinha-api-2025:latest

#docker build -t andersongomes001/rinha-worker-2025:latest -f Dockerfile.worker .
#docker push andersongomes001/rinha-worker-2025:latest



================================================
FILE: Cargo.toml
================================================
[package]
name = "rinha2025"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "api"
path = "src/main.rs"

[profile.release]
lto = true
codegen-units = 1


[dependencies]
axum = "0.8.4"
tokio = {version = "1.46.1", features = ["full"]}
serde = { version = "1.0.219", features = ["derive"] }
reqwest = { version = "0.12.22", features = ["json"] }
serde_json = "1.0.140"
redis = {version = "0.32.3", features = ["tokio-comp", "connection-manager", "cluster", "cluster-async"] }
chrono = "0.4.41"
once_cell = "1.21.3"



================================================
FILE: docker-compose.yml
================================================
x-api_template: &api_template
  image: andersongomes001/rinha-api-2025:latest
  environment:
    PAYMENT_PROCESSOR_DEFAULT_URL: "http://payment-processor-default:8080"
    PAYMENT_PROCESSOR_FALLBACK_URL: "http://payment-processor-fallback:8080"
    REDIS_URL: "redis://redis:6379/"
    PORT: 80
  networks:
    - backend
    - payment-processor
  deploy:
    resources:
      limits:
        cpus: "0.5"
        memory: "115MB"

services:
  api01:
    <<: *api_template
    hostname: api01
    depends_on:
      - redis
  api02:
    <<: *api_template
    hostname: api02
    depends_on:
      - redis
  redis:
    image: redis:8.0.3-alpine
    hostname: redis
    networks:
      - backend
    ports:
      - "6379:6379"
    command: ["redis-server", "--appendonly", "yes", "--appendfsync", "everysec"]
    deploy:
      resources:
        limits:
          cpus: "0.3"
          memory: "50MB"
  nginx:
    image: nginx
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "9999:80"
    depends_on:
      - api01
      - api02
    networks:
      - backend
    deploy:
      resources:
        limits:
          cpus: "0.2"
          memory: "70MB"
networks:
  backend:
  payment-processor:
    external: true



================================================
FILE: Dockerfile
================================================
FROM rust:1.87-bookworm AS builder

RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    build-essential \
    ca-certificates \
    && rm -rf /var/lib/apt/lists

WORKDIR /app
COPY . .
RUN rm -rf target
RUN cargo build --bin api --release


FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    libgcc-s1 \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/api /usr/local/bin/
RUN chmod +x /usr/local/bin/api
CMD ["api"]



================================================
FILE: Dockerfile.worker
================================================
FROM rust:1.87-bookworm AS builder

RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    build-essential \
    ca-certificates \
    && rm -rf /var/lib/apt/lists

WORKDIR /app
COPY . .
RUN rm -rf target
RUN cargo build --bin worker --release


FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    libgcc-s1 \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/worker /usr/local/bin/
RUN chmod +x /usr/local/bin/worker
CMD ["worker"]



================================================
FILE: nginx.conf
================================================
worker_processes 1;

events {
    worker_connections 2048;
    use epoll;
    multi_accept on;
}

http {
    access_log off;
    error_log /dev/null crit;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;

    keepalive_timeout 30;
    keepalive_requests 100000;

    client_max_body_size 0;

    upstream api {
        server api01:80 max_fails=1 fail_timeout=1s;
        server api02:80 max_fails=1 fail_timeout=1s;
        keepalive 100;
    }

    server {
        listen 80 default_server;

        location / {
            proxy_pass http://api;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
        }
    }
}



================================================
FILE: rinha-2025.iml
================================================
<?xml version="1.0" encoding="UTF-8"?>
<module type="RUST_MODULE" version="4">
  <component name="NewModuleRootManager" inherit-compiler-output="true">
    <exclude-output />
    <content url="file://$MODULE_DIR$">
      <sourceFolder url="file://$MODULE_DIR$/src" isTestSource="false" />
      <excludeFolder url="file://$MODULE_DIR$/target" />
    </content>
    <orderEntry type="inheritedJdk" />
    <orderEntry type="sourceFolder" forTests="false" />
  </component>
</module>


================================================
FILE: src/lib.rs
================================================
pub use crate::domain::entities::{AnyError, HealthResponse, PostPayments};

pub mod api;
pub mod infrastructure;
pub mod domain;
pub mod application;



================================================
FILE: src/main.rs
================================================
use axum::{
    routing::{get, post}
    , Router,
};
use redis::aio::ConnectionManager;
use reqwest::Client;
use rinha2025::api::handlers::{clear_redis, payments, payments_summary};
use std::env;
use std::sync::Arc;
use tokio::sync::{mpsc, Mutex};
use rinha2025::application::process;
use rinha2025::domain::entities::{AppState, PostPayments};
use rinha2025::infrastructure::redis::get_redis_connection;

#[tokio::main]
async fn main() {
    //start_service_health();
    let (tx, rx) = mpsc::channel::<PostPayments>(100_000);
    let tx_for_worker = tx.clone();
    let port = env::var("PORT").unwrap_or("9999".to_string());
    let client = Arc::new(Client::builder()
        //.timeout(Duration::from_millis(300))
        .build()
        .unwrap());

    let connection : Arc<ConnectionManager> = match get_redis_connection().await {
        Ok(conn) => Arc::new(conn),
        Err(e) => {
            eprintln!("Falha ao conectar no redis: {:?}", e);
            return;
        }
    };
    let connection_for_clear = Arc::clone(&connection);
    clear_redis(connection_for_clear).await;


    let rx = Arc::new(Mutex::new(rx));

    for _ in 0..5 {
        let connection_for_worker = Arc::clone(&connection);
        let client_clone = Arc::clone(&client);
        let rx_clone = Arc::clone(&rx);
        let tx_for_worker = tx_for_worker.clone();

        tokio::spawn(async move {
            let client = client_clone;
            let conn_clone = Arc::clone(&connection_for_worker);

            loop {
                // trava o mutex só enquanto faz o recv
                let maybe_payment = {
                    let mut rx_guard = rx_clone.lock().await;
                    rx_guard.recv().await
                };

                if let Some(post_payments) = maybe_payment {
                    let payload = serde_json::to_string(&post_payments).unwrap();
                    if let Err(e) = process(payload, conn_clone.clone(), client.clone()).await {
                        eprintln!("Erro ao processar pagamento: {:?}", e);
                        if let Err(e) = tx_for_worker.send(post_payments).await {
                            eprintln!("Erro ao tentar colocar o pagamento na fila novamente: {:?}", e);
                        } else {
                            eprintln!("Pagamento recolocado na fila.");
                        }
                    }
                } else {
                    break;
                }
            }
        });
    }

    /*
    let connection_for_worker = Arc::clone(&connection);
    tokio::spawn(async move {
        let client = Arc::clone(&client);
        let conn_clone = Arc::clone(&connection_for_worker);
        while let Some(post_payments) = rx.recv().await {
            let payload = serde_json::to_string(&post_payments).unwrap();
            if let Err(e) = process(payload, conn_clone.clone(), client.clone()).await {
                eprintln!("Erro ao processar pagamento: {:?}", e);
                if let Err(e) = tx_for_worker.send(post_payments).await {
                    eprintln!("Erro ao tentar colocar o pagamento na fila novamente: {:?}", e);
                } else {
                    eprintln!("Pagamento recolocado na fila.");
                }
            }
        }
    });
    */

    let app = Router::new()
        .route("/payments", post(payments))
        .route("/payments-summary", get(payments_summary))
        //.route("/clear_redis",get(clear_redis))
        .with_state(AppState {
            redis: Arc::clone(&connection),
            sender: tx,
        });
    let listener = tokio::net::TcpListener::bind(format!("0.0.0.0:{}", port)).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}




================================================
FILE: src/api/handlers.rs
================================================
use crate::infrastructure::{date_to_ts, round2};
use axum::extract::{Query, State};
use axum::{
    http::StatusCode
    ,
    Json,
};
use redis::AsyncCommands;
use std::string::String;
use std::sync::Arc;
use std::time::Instant;
use redis::aio::ConnectionManager;
use crate::domain::entities::{AppState, PaymentsSummary, PaymentsSummaryFilter, SummaryData};
use crate::PostPayments;

pub async fn clear_redis(redis: Arc<ConnectionManager> ){
    let mut conn = (*redis).clone();
    match AsyncCommands::flushall::<String>(&mut conn).await {
        Ok(_) => {
            println!("Redis cache cleared successfully.");
        },
        Err(_) => {
            println!("Failed to clear Redis cache.");
        }
    }
}
/*pub async fn clear_redis(
    State(state): State<AppState>
) -> StatusCode {
    let mut conn = (*state.redis).clone();
    match AsyncCommands::flushall::<String>(&mut conn).await {
        Ok(_) => {
            StatusCode::OK
        },
        Err(_) => {
            StatusCode::INTERNAL_SERVER_ERROR
        }
    }
}*/

pub async fn payments(
    State(state): State<AppState>,
    Json(payload): Json<PostPayments>,
) -> StatusCode {
    match state.sender.send(payload).await {
        Ok(_) => {
            StatusCode::CREATED
        },
        Err(_) => {
            StatusCode::INTERNAL_SERVER_ERROR
        }
    }
}

pub async fn payments_summary(
    Query(params): Query<PaymentsSummaryFilter>,
    State(state): State<AppState>,
) -> (StatusCode, Json<PaymentsSummary>) {
    let mut conn = (*state.redis).clone();
    let from = date_to_ts(params.from.clone().unwrap_or_else(|| "1970-01-01T00:00:00Z".to_string()));
    let to = date_to_ts(params.to.clone().unwrap_or_else(|| "1970-01-01T00:00:00Z".to_string()));
    //println!("from: {}", from);
    //println!("to: {}", to);
    let start = Instant::now();
    let ids_default: Vec<String> = AsyncCommands::zrangebyscore(&mut conn, "summary:default:history", from, to).await.unwrap_or_default();
    let amounts_default: Vec<f64> = AsyncCommands::hget(&mut conn,"summary:default:data", &ids_default).await.unwrap_or_default();

    let ids_fallback: Vec<String> = AsyncCommands::zrangebyscore(&mut conn,"summary:fallback:history", from, to).await.unwrap_or_default();
    let amounts_fallback: Vec<f64> = AsyncCommands::hget(&mut conn,"summary:fallback:data", &ids_fallback).await.unwrap_or_default();
    println!("Summary gerado em {:?}", start.elapsed());

    let sumary = PaymentsSummary {
        default: SummaryData {
            total_requests: amounts_default.len() as i64,
            total_amount: round2(amounts_default.iter().copied().sum()),
        },
        fallback: SummaryData {
            total_requests: amounts_fallback.len() as i64,
            total_amount: round2(amounts_fallback.iter().copied().sum()),
        },
    };
    println!("{:?}", sumary);
    /*let sumary_admin = PaymentsSummary {
        default: compare_summary(PAYMENT_PROCESSOR_DEFAULT_URL.to_string(),&params).await,
        fallback: compare_summary(PAYMENT_PROCESSOR_FALLBACK_URL.to_string(), &params).await,
    };
    println!("{:?}", sumary_admin);*/
    (StatusCode::OK, Json(sumary))
}

pub async fn compare_summary(host: String, filter: &PaymentsSummaryFilter) -> SummaryData {

    let mut querystring = Vec::new();

    if let (Some(from), Some(to)) = (&filter.from, &filter.to) {
        querystring.push(("from", from.clone()));
        querystring.push(("to", to.clone()));
    }

    let mut headers = reqwest::header::HeaderMap::new();
    headers.insert("x-rinha-token", "123".parse().unwrap());

    let client = reqwest::Client::new();
    return client.get(format!("{}/admin/payments-summary",host))
        .query(&querystring)
        .headers(headers)
        .send()
        .await.unwrap()
        .json::<SummaryData>()
        .await
        .unwrap();
}



================================================
FILE: src/api/mod.rs
================================================
pub mod handlers;
pub use handlers::{
    clear_redis, payments, payments_summary,
};



================================================
FILE: src/application/mod.rs
================================================
pub mod services;

pub use services::{
    process
};



================================================
FILE: src/application/services.rs
================================================
use std::sync::Arc;
use std::thread::sleep;
use std::time::Duration;
use crate::infrastructure::config::{PAYMENT_PROCESSOR_DEFAULT_URL, PAYMENT_PROCESSOR_FALLBACK_URL, QUEUE_FAILED_KEY};
use crate::infrastructure::{payments_request, store_summary};
use chrono::{SecondsFormat, Utc};
use redis::aio::ConnectionManager;
use redis::AsyncCommands;
use reqwest::Client;
use crate::{AnyError, PostPayments};

pub async fn process(payment_json: String, conn: Arc<ConnectionManager>, client: Arc<Client>) -> Result<(), AnyError> {
    let mut conn = (*conn).clone();
    let payment: PostPayments = match serde_json::from_str(&payment_json) {
        Ok(p) => p,
        Err(_) => return Err(format!("Erro ao deserializar JSON {}", &payment_json).into()),
    };


    let timestamp = Utc::now();
    let timestamp_str = timestamp.to_rfc3339_opts(SecondsFormat::Millis, true);
    let timestamp_ms = timestamp.timestamp_millis() as f64;
    let payload = serde_json::json!({
        "correlationId": payment.correlation_id,
        "amount": payment.amount,
        "requestedAt" : timestamp_str
    });
    let id = format!("{}", payment.correlation_id);

    for _ in 0..5 {
        let normal_request = payments_request(&client, PAYMENT_PROCESSOR_DEFAULT_URL.as_str().parse().unwrap(), &payload).await?;
        let status = normal_request.status();
        if status.is_success() {
            store_summary(&mut conn, "default", &id, payment.amount, timestamp_ms, &payment_json).await?;
            return Ok(());
        }
        tokio::time::sleep(Duration::from_millis(500)).await;
    }
    let fallback_request = payments_request(&client, PAYMENT_PROCESSOR_FALLBACK_URL.as_str().parse().unwrap(), &payload).await?;
    let status = fallback_request.status();
    if status.is_success() {
        store_summary(&mut conn, "fallback", &id, payment.amount, timestamp_ms, &payment_json).await?;
        return Ok(());
    }
    //if HEALTH_STATUS.load(Ordering::Relaxed) {}
    //let _ = conn.rpush::<_, _, String>(QUEUE_FAILED_KEY, payment_json).await;
    Err("Erro ao enviar todas as requisiçoes".to_string().into())
}




================================================
FILE: src/domain/entities.rs
================================================
use std::sync::Arc;
use redis::aio::ConnectionManager;
use serde::{Deserialize, Serialize};
use tokio::sync::mpsc::Sender;

#[derive(Deserialize, Serialize, Debug)]
pub struct HealthResponse {
    pub failing : bool,
    #[serde(rename = "minResponseTime")]
    pub min_response_time: i64
}

#[derive(Clone)]
pub struct AppState {
    pub redis: Arc<ConnectionManager>,
    pub sender: Sender<PostPayments>,
}

#[derive(Deserialize, Serialize, Debug,Clone)]
pub struct PaymentsSummaryFilter {
    pub from: Option<String>,
    pub to: Option<String>,
}

#[derive(Deserialize, Serialize, Debug)]
pub struct SummaryData {
    #[serde(rename = "totalRequests")]
    pub total_requests: i64,
    #[serde(rename = "totalAmount")]
    pub total_amount: f64,
}

#[derive(Deserialize, Serialize, Debug)]
pub struct PaymentsSummary {
    pub default: SummaryData,
    pub fallback: SummaryData,
}

#[derive(Deserialize, Serialize, Debug)]
pub struct PostPayments {
    #[serde(rename = "correlationId")]
    pub correlation_id: String,
    pub amount: f64,
}

pub type AnyError = Box<dyn std::error::Error + Send + Sync>;



================================================
FILE: src/domain/mod.rs
================================================
pub mod entities;



================================================
FILE: src/infrastructure/config.rs
================================================
use std::env;
use std::sync::atomic::AtomicBool;
use once_cell::sync::Lazy;

pub const QUEUE_KEY: &str = "queue";
pub const QUEUE_FAILED_KEY: &str = "queue:failed";
pub static HEALTH_STATUS: Lazy<AtomicBool> = Lazy::new(||AtomicBool::new(true));


pub static PAYMENT_PROCESSOR_DEFAULT_URL: Lazy<String> = Lazy::new(|| {
    env::var("PAYMENT_PROCESSOR_DEFAULT_URL").unwrap_or_else(|_| "http://localhost:8001".to_string())
});
pub static PAYMENT_PROCESSOR_FALLBACK_URL: Lazy<String> = Lazy::new(|| {
    env::var("PAYMENT_PROCESSOR_FALLBACK_URL").unwrap_or_else(|_| "http://localhost:8002".to_string())
});

pub static REDIS_URL: Lazy<String> = Lazy::new(|| {
    env::var("REDIS_URL").unwrap_or_else(|_| "redis://127.0.0.1:6379/".to_string())
});



================================================
FILE: src/infrastructure/health.rs
================================================
use std::sync::atomic::Ordering;
use reqwest::Client;
use crate::HealthResponse;
use crate::infrastructure::config::{HEALTH_STATUS, PAYMENT_PROCESSOR_DEFAULT_URL};

pub fn start_service_health() {
    tokio::spawn(async move {
        loop {
            let result = Client::builder()
                .timeout(std::time::Duration::from_millis(10))
                .build()
                .unwrap()
                .get(format!("{}/payments/service-health",PAYMENT_PROCESSOR_DEFAULT_URL.to_string()))
                .send()
                .await;
            match result {
                Ok(response) => {
                    if let Ok(json) = response.json::<HealthResponse>().await {
                        HEALTH_STATUS.store(!json.failing, Ordering::Relaxed);
                    } else {
                        HEALTH_STATUS.store(false, Ordering::Relaxed);
                    }

                }
                Err(_) => {
                    HEALTH_STATUS.store(false, Ordering::Relaxed);
                }
            }
            tokio::time::sleep(std::time::Duration::from_secs(5)).await;
        }
    });
}



================================================
FILE: src/infrastructure/http_clients.rs
================================================
use std::sync::Arc;
use reqwest::{Client, Response};
use serde_json::Value;

pub async fn payments_request(client: &Arc<Client>, host: String, payload: &Value) -> Result<Response, reqwest::Error> {
    client
        .post(format!("{}/payments", host))
        .json(&payload)
        .send().await
}



================================================
FILE: src/infrastructure/mod.rs
================================================
pub mod utils;
pub mod config;
pub mod redis;
pub mod health;
pub mod http_clients;

pub use utils::{
    date_to_ts, round2
};

pub use http_clients::{
    payments_request
};

pub use redis::{
    get_redis_connection,store_summary
};



================================================
FILE: src/infrastructure/redis.rs
================================================
use redis::aio::ConnectionManager;
use redis::{pipe, RedisError};
use crate::infrastructure::config::{QUEUE_FAILED_KEY, REDIS_URL};

pub async fn get_redis_connection() -> Result<ConnectionManager, RedisError> {
    let client = redis::Client::open(REDIS_URL.as_str().to_string())?;   //redis::Client::open(env::var("REDIS_URL").unwrap_or("redis://127.0.0.1:6379/".to_string()))?;
    let manager = client.get_connection_manager().await?;
    Ok(manager)
}


pub async fn store_summary(conn: &mut ConnectionManager, key_prefix: &str, id: &str, amount: f64, timestamp_ms: f64, json: &str) -> redis::RedisResult<()> {
    //println!("store_summary => key_prefix: {}, id: {}, amount: {}, timestamp: {}", key_prefix, id, amount, timestamp_ms);
    pipe()
        .atomic()
        .hset(format!("summary:{}:data", key_prefix), id, amount)
        .zadd(format!("summary:{}:history", key_prefix), id, timestamp_ms)
        //.lrem(QUEUE_FAILED_KEY, 1, json)
        .query_async(conn)
        .await
}



================================================
FILE: src/infrastructure/utils.rs
================================================
use chrono::{DateTime, NaiveDateTime};

pub fn date_to_ts(date: String) -> f64 {
    if let Ok(dt) = DateTime::parse_from_rfc3339(&*date) {
        //println!("parse_from_rfc3339 {}\n", date);
        return dt.timestamp_millis() as f64;
    }
    //println!("parse_from_str {}\n", date);
    let naive = NaiveDateTime::parse_from_str(&*date, "%Y-%m-%dT%H:%M:%S").unwrap();
    naive.and_utc().timestamp_millis() as f64
}

pub fn round2(val: f64) -> f64 {
    let rounded = (val * 100.0).round() / 100.0;
    sanitize_zero(rounded)
}

//remove os -0.0 para ficar 0.0
fn sanitize_zero(val: f64) -> f64 {
    if val == 0.0 {
        0.0
    } else {
        val
    }
}

Directory structure:
└── andersongomes001-rinha-2025/
    ├── README.md
    ├── build-and-push.sh
    ├── Cargo.toml
    ├── docker-compose.yml
    ├── Dockerfile
    ├── Dockerfile.worker
    ├── nginx.conf
    ├── rinha-2025.iml
    └── src/
        ├── lib.rs
        ├── main.rs
        ├── api/
        │   ├── handlers.rs
        │   └── mod.rs
        ├── application/
        │   ├── mod.rs
        │   └── services.rs
        ├── domain/
        │   ├── entities.rs
        │   └── mod.rs
        └── infrastructure/
            ├── config.rs
            ├── health.rs
            ├── http_clients.rs
            ├── mod.rs
            ├── redis.rs
            └── utils.rs



