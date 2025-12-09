### Запуск приложения

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/nika-milka/space.git
cd space/4

# 2. Запустите приложение
docker-compose up -d


# 3. Доступ к приложению
# Базовые
http://localhost:8000/
http://localhost:8000/health
http://localhost:8000/docs
http://localhost:8000/redoc

# API v1
http://localhost:8000/v1/space/iss/positions?limit=50&page=1
http://localhost:8000/v1/space/nasa/datasets?mission=apollo&limit=20
http://localhost:8000/v1/space/apod?limit=10

# Pascal CSV
http://localhost:8000/v1/space/pascal/csv?format=json&limit=100
http://localhost:8000/v1/space/pascal/csv?format=csv&limit=50
http://localhost:8000/v1/space/pascal/csv?format=html&page=1&limit=30
http://localhost:8000/v1/space/pascal/csv/download?format=csv
http://localhost:8000/v1/space/pascal/csv/download?format=excel
http://localhost:8000/v1/space/pascal/csv/stats
