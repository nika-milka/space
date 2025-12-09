-- Инициализация базы данных для Кассиопея Space Monitor
-- Выполняется автоматически при первом запуске контейнера

-- Создаем пользователя monouser
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'monouser') THEN
        CREATE USER monouser WITH PASSWORD 'monopass';
    END IF;
END
$$;
-- Подключаемся к новой базе данных
\c monolith

-- Устанавливаем расширения
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Создаем таблицу позиций МКС
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

-- Создаем таблицу датасетов NASA
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

-- Создаем таблицу APOD
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

-- Создаем таблицу для логов
CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(20),
    message TEXT,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Создаем индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_iss_timestamp ON iss_positions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_iss_coordinates ON iss_positions(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_nasa_dataset_id ON nasa_datasets(dataset_id);
CREATE INDEX IF NOT EXISTS idx_nasa_mission ON nasa_datasets(mission);
CREATE INDEX IF NOT EXISTS idx_nasa_fetched_at ON nasa_datasets(fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_apod_date ON apod(date DESC);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp DESC);

-- Добавляем тестовые данные
INSERT INTO iss_positions (latitude, longitude, altitude, velocity, visibility)
VALUES 
    (51.5074, -0.1278, 408.0, 27600.0, 'visible'),
    (48.8566, 2.3522, 410.0, 27500.0, 'visible'),
    (40.7128, -74.0060, 412.0, 27400.0, 'visible'),
    (35.6762, 139.6503, 409.0, 27650.0, 'visible')
ON CONFLICT DO NOTHING;

INSERT INTO nasa_datasets (dataset_id, title, mission, instrument, data_type, file_size_mb)
VALUES 
    ('OSDR-2024-001', 'ISS Microgravity Effects on Human Cells', 'ISS', 'Bioanalyzer', 'CSV', 2.5),
    ('OSDR-2024-002', 'Space Radiation Exposure Study', 'Artemis', 'Radiation Monitor', 'JSON', 3.2),
    ('OSDR-2024-003', 'Plant Growth in Microgravity', 'ISS', 'Plant Habitat', 'CSV', 1.8)
ON CONFLICT (dataset_id) DO NOTHING;

INSERT INTO apod (date, title, explanation, url, media_type)
VALUES 
    ('2024-01-15', 'Winter Stars Over Japan', 'A beautiful view of winter constellations over Japanese mountains', 'https://apod.nasa.gov/apod/image/2401/test1.jpg', 'image'),
    ('2024-01-14', 'Aurora Over Norway', 'Northern lights dancing over Norwegian fjords', 'https://apod.nasa.gov/apod/image/2401/test2.jpg', 'image')
ON CONFLICT (date) DO NOTHING;

-- Добавляем лог инициализации
INSERT INTO system_logs (level, message) VALUES ('INFO', 'Database initialized successfully');

-- Предоставляем права пользователю monouser
GRANT ALL PRIVILEGES ON DATABASE monolith TO monouser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO monouser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO monouser;
GRANT USAGE ON SCHEMA public TO monouser;

-- Меняем владельца таблиц на monouser
ALTER TABLE iss_positions OWNER TO monouser;
ALTER TABLE nasa_datasets OWNER TO monouser;
ALTER TABLE apod OWNER TO monouser;
ALTER TABLE system_logs OWNER TO monouser;

-- Выводим информацию об успешной инициализации
\echo '✅ База данных Кассиопея Space Monitor успешно инициализирована'
\echo '👤 Пользователь: monouser'
\echo '🗄️  База данных: monolith'
\echo '📊 Таблицы: iss_positions, nasa_datasets, apod, system_logs'
\echo '📈 Тестовые данные добавлены'