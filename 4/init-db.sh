#!/bin/bash
set -e

echo "🚀 Инициализация базы данных..."

# Ждем готовности PostgreSQL
until pg_isready -U postgres; do
  echo "⏳ Ожидание PostgreSQL..."
  sleep 1
done

# Создаем пользователя и базу данных через psql
psql -v ON_ERROR_STOP=1 -U postgres <<-EOSQL
    -- Создаем пользователя
    CREATE USER monouser WITH PASSWORD 'monopass';
    
    -- Создаем базу данных
    CREATE DATABASE monolith OWNER monouser;
    
    -- Предоставляем права
    GRANT ALL PRIVILEGES ON DATABASE monolith TO monouser;
EOSQL

echo "✅ Пользователь и база данных созданы"

# Подключаемся к новой базе данных
psql -v ON_ERROR_STOP=1 -U postgres -d monolith <<-EOSQL
    -- Предоставляем права на схеме public
    GRANT ALL ON SCHEMA public TO monouser;
    
    -- Создаем таблицы
    CREATE TABLE IF NOT EXISTS iss_positions (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        latitude FLOAT NOT NULL,
        longitude FLOAT NOT NULL,
        altitude FLOAT DEFAULT 0,
        velocity FLOAT DEFAULT 0,
        visibility VARCHAR(50),
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS nasa_datasets (
        id SERIAL PRIMARY KEY,
        dataset_id VARCHAR(255) UNIQUE,
        title TEXT,
        description TEXT,
        mission VARCHAR(100),
        instrument VARCHAR(100),
        start_time TIMESTAMPTZ,
        end_time TIMESTAMPTZ,
        data_type VARCHAR(50),
        file_size_mb FLOAT,
        is_processed BOOLEAN DEFAULT FALSE,
        raw_data TEXT,
        fetched_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS apod (
        id SERIAL PRIMARY KEY,
        date VARCHAR(20) UNIQUE,
        title TEXT,
        explanation TEXT,
        url TEXT,
        hdurl TEXT,
        media_type VARCHAR(50),
        copyright TEXT,
        fetched_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Создаем индексы
    CREATE INDEX IF NOT EXISTS idx_iss_timestamp ON iss_positions(timestamp DESC);
    CREATE INDEX IF NOT EXISTS idx_nasa_fetched_at ON nasa_datasets(fetched_at DESC);
    CREATE INDEX IF NOT EXISTS idx_apod_date ON apod(date DESC);
    
    -- Добавляем тестовую запись
    INSERT INTO iss_positions (latitude, longitude, altitude, velocity, visibility)
    VALUES (51.5074, -0.1278, 408.0, 27600.0, 'visible')
    ON CONFLICT DO NOTHING;
    
    -- Информация о создании
    CREATE TABLE IF NOT EXISTS db_info (
        id SERIAL PRIMARY KEY,
        version VARCHAR(20) DEFAULT '1.0',
        initialized_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    
    INSERT INTO db_info DEFAULT VALUES;
    
    -- Предоставляем права пользователю на все таблицы
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO monouser;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO monouser;
    
    echo "✅ База данных успешно инициализирована"
EOSQL