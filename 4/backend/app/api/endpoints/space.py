from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.repositories import ISSRepository, NASARepository, APODRepository
from app.schemas.space import (
    ISSPositionResponse, 
    NASADatasetResponse, 
    APODResponse,
    PaginatedResponse
)
from app.services.pascal_csv_service import PascalCSVGenerator
from app.services.redis_service import RedisCacheService
from app.core.config import settings

# Создаем router
router = APIRouter(prefix="/space", tags=["space"])

# Инициализация сервисов
pascal_generator = PascalCSVGenerator()
redis_cache = RedisCacheService(settings.REDIS_URL)

@router.get("/iss/positions", response_model=PaginatedResponse[ISSPositionResponse])
async def get_iss_positions(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    page: int = Query(1, ge=1)
):
    """Получить позиции МКС"""
    try:
        repo = ISSRepository(db)
        positions = await repo.get_latest_positions(limit=limit)
        
        total = len(positions)
        start = (page - 1) * limit
        end = start + limit
        
        paginated_items = positions[start:end]
        
        return PaginatedResponse(
            items=paginated_items,
            total=total,
            page=page,
            limit=limit,
            pages=(total + limit - 1) // limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/nasa/datasets", response_model=PaginatedResponse[NASADatasetResponse])
async def get_nasa_datasets(
    db: AsyncSession = Depends(get_db),
    mission: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    page: int = Query(1, ge=1)
):
    """Получить датасеты NASA"""
    try:
        repo = NASARepository(db)
        datasets = await repo.get_datasets(mission=mission, limit=1000)  # Больше для пагинации
        
        if mission:
            datasets = [d for d in datasets if d.mission == mission]
        
        total = len(datasets)
        start = (page - 1) * limit
        end = start + limit
        
        paginated_items = datasets[start:end]
        
        return PaginatedResponse(
            items=paginated_items,
            total=total,
            page=page,
            limit=limit,
            pages=(total + limit - 1) // limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/apod", response_model=PaginatedResponse[APODResponse])
async def get_apods(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(30, ge=1, le=100),
    page: int = Query(1, ge=1)
):
    """Получить Astronomy Picture of the Day"""
    try:
        repo = APODRepository(db)
        apods = await repo.get_apods(limit=1000)  # Больше для пагинации
        
        total = len(apods)
        start = (page - 1) * limit
        end = start + limit
        
        paginated_items = apods[start:end]
        
        return PaginatedResponse(
            items=paginated_items,
            total=total,
            page=page,
            limit=limit,
            pages=(total + limit - 1) // limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pascal/csv")
async def get_pascal_csv_data(
    limit: int = Query(50, ge=1, le=1000, description="Количество строк"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    generate_new: bool = Query(False, description="Сгенерировать новые данные"),
    format: str = Query("json", description="Формат данных (json, csv, html)")
):
    """
    Получить данные Pascal CSV в различных форматах
    """
    try:
        cache_key = f"pascal:csv:data:{limit}:{page}"
        
        # Проверяем кэш, если не генерируем новые данные
        if not generate_new:
            cached_data = await redis_cache.get_cache(cache_key)
            if cached_data:
                print("✅ Данные получены из кэша")
                if format == "csv":
                    return _format_csv_response(cached_data)
                elif format == "html":
                    total_cache_key = f"pascal:csv:total:{limit}"
                    total = await redis_cache.get_cache(total_cache_key) or 1000
                    return HTMLResponse(_format_html_response(cached_data, page, limit, total))
                return cached_data
        
        # Генерируем тестовые данные
        data = []
        from datetime import datetime, timedelta
        import random
        
        base_date = datetime.now()
        total_items = 1000  # Всего элементов
        
        # Рассчитываем диапазон для пагинации
        start = (page - 1) * limit
        end = min(start + limit, total_items)
        
        for i in range(start, end):
            row_date = base_date - timedelta(days=i % 30)
            
            row = {
                "id": i + 1,
                "timestamp": row_date.isoformat(),
                "boolean_field": "ИСТИНА" if i % 2 == 0 else "ЛОЖЬ",
                "numeric_field": round(i * 1.5 + random.uniform(0, 10), 2),
                "text_field": f"Текстовая строка номер {i + 1} с различным содержимым",
                "date_field": row_date.strftime("%Y-%m-%d"),
                "time_field": row_date.strftime("%H:%M:%S"),
                "category": random.choice(["А", "Б", "В", "Г", "Д"]),
                "status": random.choice(["активен", "завершен", "в процессе", "ожидание"])
            }
            data.append(row)
        
        # Сохраняем в кэш на 5 минут
        await redis_cache.set_cache(cache_key, data, ttl=300)
        await redis_cache.set_cache(f"pascal:csv:total:{limit}", total_items, ttl=300)
        
        # Возвращаем в запрошенном формате
        if format == "csv":
            return _format_csv_response(data)
        elif format == "html":
            return HTMLResponse(_format_html_response(data, page, limit, total_items))
        
        return data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pascal/csv/export")
async def export_pascal_data(
    export_request: dict,
    background_tasks: BackgroundTasks
):
    """
    Экспорт данных Pascal CSV по запросу
    """
    try:
        fields = export_request.get("fields", [])
        format_type = export_request.get("format", "csv")
        data_range = export_request.get("range", "all")
        
        # Генерируем данные
        data = []
        from datetime import datetime, timedelta
        import random
        
        base_date = datetime.now()
        count = 100 if data_range == "sample" else 1000
        
        for i in range(count):
            row_date = base_date - timedelta(days=i % 30)
            
            row = {
                "id": i + 1,
                "timestamp": row_date.isoformat(),
                "boolean_field": "ИСТИНА" if i % 2 == 0 else "ЛОЖЬ",
                "numeric_field": round(i * 1.5 + random.uniform(0, 10), 2),
                "text_field": f"Текстовая строка номер {i + 1}",
                "date_field": row_date.strftime("%Y-%m-%d"),
                "time_field": row_date.strftime("%H:%M:%S"),
                "category": random.choice(["А", "Б", "В", "Г", "Д"]),
                "status": random.choice(["активен", "завершен", "в процессе", "ожидание"])
            }
            
            # Фильтруем по выбранным полям
            if fields:
                row = {k: v for k, v in row.items() if k in fields}
            
            data.append(row)
        
        # Экспорт в нужном формате
        if format_type == "excel":
            # Используем сервис для генерации Excel
            filename, excel_filename = pascal_generator.generate_export_excel(data)
            background_tasks.add_task(os.remove, excel_filename)
            
            return FileResponse(
                excel_filename,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename="pascal_export.xlsx"
            )
        else:
            # Генерируем CSV
            csv_content = pascal_generator.generate_csv_string(data)
            
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=pascal_export.csv"}
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pascal/csv/download")
async def download_pascal_csv(
    format: str = Query("csv", description="Формат файла (csv, excel)")
):
    """Скачать Pascal CSV/Excel файл"""
    try:
        if format == "excel":
            filename, excel_filename = pascal_generator.generate_csv_with_types()
            import os
            from fastapi.responses import FileResponse
            
            if os.path.exists(excel_filename):
                return FileResponse(
                    excel_filename,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    filename="pascal_data.xlsx"
                )
            else:
                raise HTTPException(status_code=404, detail="Excel файл не найден")
        else:
            # Генерируем CSV
            filename, _ = pascal_generator.generate_csv_with_types()
            from fastapi.responses import FileResponse
            
            return FileResponse(
                filename,
                media_type="text/csv",
                filename="pascal_data.csv",
                headers={"Content-Disposition": "attachment; filename=pascal_data.csv"}
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pascal/csv/stats")
async def get_pascal_csv_stats():
    """Получить статистику по Pascal CSV данным"""
    try:
        cache_key = "pascal:csv:stats"
        
        # Проверяем кэш
        cached_stats = await redis_cache.get_cache(cache_key)
        if cached_stats:
            return cached_stats
        
        # Генерируем статистику
        from datetime import datetime
        import random
        
        stats = {
            "total_records": 1000,
            "last_generated": datetime.now().isoformat(),
            "formats_available": ["json", "csv", "html", "excel"],
            "fields": {
                "timestamp": {"type": "datetime", "description": "Дата и время"},
                "boolean_field": {"type": "boolean", "values": ["ИСТИНА", "ЛОЖЬ"]},
                "numeric_field": {"type": "float", "min": 0, "max": 1500},
                "text_field": {"type": "string", "max_length": 100},
                "date_field": {"type": "date", "format": "YYYY-MM-DD"},
                "time_field": {"type": "time", "format": "HH:MM:SS"}
            },
            "sample_data": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "boolean_field": "ИСТИНА",
                    "numeric_field": 123.45,
                    "text_field": "Пример текста",
                    "date_field": datetime.now().strftime("%Y-%m-%d"),
                    "time_field": datetime.now().strftime("%H:%M:%S")
                }
            ]
        }
        
        # Сохраняем в кэш на 10 минут
        await redis_cache.set_cache(cache_key, stats, ttl=600)
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _format_csv_response(data: List[Dict[str, Any]]) -> str:
    """Форматировать данные как CSV"""
    import csv
    from io import StringIO
    
    if not data:
        return ""
    
    # Создаем CSV в памяти
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    
    return output.getvalue()

def _format_html_response(data: List[Dict[str, Any]], page: int = 1, limit: int = 50, total: int = 0) -> str:
    """Форматировать данные как HTML таблицу с пагинацией и экспортом"""
    if not data:
        return "<html><body><p>Нет данных</p></body></html>"
    
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    
    # Начало HTML
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Pascal CSV Data</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                border-bottom: 2px solid #4CAF50;
                padding-bottom: 10px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            th {
                background-color: #4CAF50;
                color: white;
                padding: 12px;
                text-align: left;
                position: sticky;
                top: 0;
            }
            td {
                padding: 10px;
                border-bottom: 1px solid #ddd;
            }
            tr:nth-child(even) {
                background-color: #f2f2f2;
            }
            tr:hover {
                background-color: #e8f4e8;
            }
            .boolean-true {
                color: #2E7D32;
                font-weight: bold;
            }
            .boolean-false {
                color: #C62828;
                font-weight: bold;
            }
            .numeric {
                text-align: right;
                font-family: monospace;
            }
            .timestamp {
                font-family: monospace;
                font-size: 0.9em;
            }
            .controls {
                margin-bottom: 20px;
                padding: 15px;
                background: #e8f5e8;
                border-radius: 5px;
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                align-items: center;
            }
            .controls button, .controls a {
                padding: 8px 16px;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                transition: background 0.3s;
            }
            .controls button:hover, .controls a:hover {
                background: #45a049;
            }
            .export-buttons {
                margin-left: auto;
                display: flex;
                gap: 10px;
            }
            .export-buttons button {
                background: #2196F3;
                display: flex;
                align-items: center;
                gap: 5px;
            }
            .export-buttons button:hover {
                background: #1976D2;
            }
            .stats {
                margin-top: 20px;
                padding: 15px;
                background: #e3f2fd;
                border-radius: 5px;
            }
            .pagination {
                margin-top: 20px;
                text-align: center;
                padding: 10px;
            }
            .pagination a {
                display: inline-block;
                padding: 8px 16px;
                margin: 0 5px;
                background: #4CAF50;
                color: white;
                text-decoration: none;
                border-radius: 4px;
            }
            .pagination a:hover {
                background: #45a049;
            }
            .pagination a.disabled {
                background: #ccc;
                cursor: not-allowed;
            }
            .pagination span {
                padding: 8px 16px;
                margin: 0 5px;
                color: #666;
            }
            .modal {
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.5);
            }
            .modal-content {
                background-color: white;
                margin: 15% auto;
                padding: 20px;
                border-radius: 8px;
                width: 400px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.2);
            }
            .close {
                color: #aaa;
                float: right;
                font-size: 28px;
                font-weight: bold;
                cursor: pointer;
            }
            .close:hover {
                color: black;
            }
            .export-options {
                margin-top: 20px;
                padding: 15px;
                background: #f9f9f9;
                border-radius: 5px;
            }
            .export-options label {
                display: block;
                margin: 10px 0;
            }
            .export-options input[type="checkbox"] {
                margin-right: 10px;
            }
            .export-actions {
                margin-top: 20px;
                text-align: right;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Pascal CSV Data Table</h1>
            
            <div class="controls">
                <span>Формат: </span>
                <a href="?format=json&limit={limit}&page={page}">JSON</a>
                <a href="?format=csv&limit={limit}&page={page}">CSV</a>
                <a href="/v1/space/pascal/csv/download?format=csv" target="_blank">📥 CSV файл</a>
                <a href="/v1/space/pascal/csv/download?format=excel" target="_blank">📊 Excel файл</a>
                <a href="?format=html&limit={limit}&page={page}&generate_new=true">🔄 Новые данные</a>
                <a href="/v1/space/pascal/csv/stats" target="_blank">📈 Статистика</a>
                
                <div class="export-buttons">
                    <button onclick="showExportModal()">
                        📤 Экспорт таблицы
                    </button>
                    <button onclick="exportVisibleTable()">
                        📋 Экспорт видимых
                    </button>
                </div>
            </div>
            
            <div class="stats">
                <strong>Всего записей:</strong> {count} |
                <strong>Поля:</strong> {fields} |
                <strong>Типы данных:</strong> timestamp, boolean, numeric, text, date, time |
                <strong>Страница:</strong> {page}/{total_pages}
            </div>
    """.format(
        count=total if total > 0 else len(data),
        fields=", ".join(data[0].keys()) if data else "нет",
        limit=limit,
        page=page,
        total_pages=total_pages
    )
    
    # Таблица
    html += """
            <table id="dataTable">
                <thead>
                    <tr>
    """
    
    # Заголовки таблицы
    for key in data[0].keys():
        html += f'<th data-field="{key}">{key}</th>'
    
    html += """
                    </tr>
                </thead>
                <tbody>
    """
    
    # Строки данных
    for row in data:
        html += '<tr>'
        for key, value in row.items():
            cell_class = ""
            
            # Определяем классы для разных типов данных
            if key == "boolean_field":
                cell_class = "boolean-true" if value == "ИСТИНА" else "boolean-false"
            elif "numeric" in key or "id" == key:
                cell_class = "numeric"
            elif "timestamp" in key:
                cell_class = "timestamp"
            
            html += f'<td class="{cell_class}" data-field="{key}">{value}</td>'
        
        html += '</tr>'
    
    # Закрываем таблицу
    html += """
                </tbody>
            </table>
    """
    
    # Пагинация
    if total_pages > 1:
        html += f"""
            <div class="pagination">
                <a href="?format=html&limit={limit}&page=1" {'class="disabled"' if page == 1 else ''}>⏮️ Первая</a>
                <a href="?format=html&limit={limit}&page={page-1}" {'class="disabled"' if page <= 1 else ''}>◀️ Назад</a>
                <span>Страница {page} из {total_pages}</span>
                <a href="?format=html&limit={limit}&page={page+1}" {'class="disabled"' if page >= total_pages else ''}>Вперед ▶️</a>
                <a href="?format=html&limit={limit}&page={total_pages}" {'class="disabled"' if page == total_pages else ''}>Последняя ⏭️</a>
            </div>
        """
    
    # Модальное окно экспорта
    html += """
            <!-- Модальное окно экспорта -->
            <div id="exportModal" class="modal">
                <div class="modal-content">
                    <span class="close" onclick="closeExportModal()">&times;</span>
                    <h3>📤 Настройки экспорта</h3>
                    
                    <div class="export-options">
                        <h4>Выберите поля для экспорта:</h4>
    """
    
    # Чекбоксы для каждого поля
    if data:
        for key in data[0].keys():
            html += f'''
                <label>
                    <input type="checkbox" name="export_fields" value="{key}" checked> {key}
                </label>
            '''
    
    html += """
                        <h4>Формат экспорта:</h4>
                        <label>
                            <input type="radio" name="export_format" value="csv" checked> CSV
                        </label>
                        <label>
                            <input type="radio" name="export_format" value="excel"> Excel (XLSX)
                        </label>
                        <label>
                            <input type="radio" name="export_format" value="json"> JSON
                        </label>
                        
                        <h4>Дополнительные опции:</h4>
                        <label>
                            <input type="checkbox" name="include_headers" checked> Включать заголовки
                        </label>
                        <label>
                            <input type="checkbox" name="format_dates"> Форматировать даты
                        </label>
                        <label>
                            <input type="checkbox" name="only_visible" checked> Только видимые строки
                        </label>
                    </div>
                    
                    <div class="export-actions">
                        <button onclick="exportSelectedData()">Экспортировать</button>
                        <button onclick="closeExportModal()">Отмена</button>
                    </div>
                </div>
            </div>
            
            <div style="margin-top: 20px; color: #666; font-size: 0.9em;">
                <p>ℹ️ Данные кэшируются на 5 минут. Используйте "Новые данные" для обновления.</p>
                <p>📁 Форматы: JSON (API), CSV (импорт), HTML (просмотр), Excel (с форматами)</p>
                <p>📤 Экспорт: Вы можете экспортировать таблицу или видимые данные</p>
            </div>
        </div>
        
        <script>
            // Глобальная переменная для данных
            const tableData = """
    
    # Вставляем данные в JSON формате для JavaScript
    html += json.dumps(data, ensure_ascii=False)
    
    html += """;
            
            // Модальное окно
            function showExportModal() {
                document.getElementById('exportModal').style.display = 'block';
            }
            
            function closeExportModal() {
                document.getElementById('exportModal').style.display = 'none';
            }
            
            // Закрытие модального окна при клике вне его
            window.onclick = function(event) {
                const modal = document.getElementById('exportModal');
                if (event.target == modal) {
                    closeExportModal();
                }
            }
            
            // Экспорт видимой таблицы
            function exportVisibleTable() {
                const table = document.getElementById('dataTable');
                const rows = table.querySelectorAll('tbody tr:not([style*="display: none"])');
                const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent);
                
                exportData(rows, headers);
            }
            
            // Экспорт выбранных данных
            function exportSelectedData() {
                const format = document.querySelector('input[name="export_format"]:checked').value;
                const includeHeaders = document.querySelector('input[name="include_headers"]').checked;
                const onlyVisible = document.querySelector('input[name="only_visible"]').checked;
                const formatDates = document.querySelector('input[name="format_dates"]').checked;
                
                // Получаем выбранные поля
                const selectedFields = Array.from(document.querySelectorAll('input[name="export_fields"]:checked'))
                    .map(cb => cb.value);
                
                // Получаем данные
                let rows;
                if (onlyVisible) {
                    rows = document.querySelectorAll('#dataTable tbody tr:not([style*="display: none"])');
                } else {
                    rows = document.querySelectorAll('#dataTable tbody tr');
                }
                
                // Фильтруем по выбранным полям
                const headers = selectedFields;
                const data = [];
                
                rows.forEach(row => {
                    const rowData = {};
                    selectedFields.forEach(field => {
                        const cell = row.querySelector(`td[data-field="${field}"]`);
                        rowData[field] = cell ? cell.textContent : '';
                    });
                    data.push(rowData);
                });
                
                // Экспортируем
                switch(format) {
                    case 'csv':
                        exportToCSV(data, headers, includeHeaders, formatDates);
                        break;
                    case 'excel':
                        exportToExcel(data, headers, includeHeaders, formatDates);
                        break;
                    case 'json':
                        exportToJSON(data, formatDates);
                        break;
                }
                
                closeExportModal();
            }
            
            // Функция экспорта в CSV
            function exportToCSV(data, headers, includeHeaders = true, formatDates = false) {
                let csv = '';
                
                // Заголовки
                if (includeHeaders) {
                    csv += headers.join(',') + '\\n';
                }
                
                // Данные
                data.forEach(row => {
                    const rowData = headers.map(header => {
                        let value = row[header] || '';
                        
                        // Форматирование
                        if (formatDates) {
                            if (header.includes('date') || header.includes('timestamp')) {
                                // Преобразование форматов дат
                                try {
                                    const date = new Date(value);
                                    if (!isNaN(date)) {
                                        value = date.toLocaleDateString('ru-RU');
                                    }
                                } catch(e) {
                                    // Оставляем как есть
                                }
                            }
                        }
                        
                        // Экранирование для CSV
                        value = value.toString().replace(/"/g, '""');
                        if (value.includes(',') || value.includes('\\n') || value.includes('"')) {
                            value = `"${value}"`;
                        }
                        
                        return value;
                    });
                    csv += rowData.join(',') + '\\n';
                });
                
                downloadFile(csv, 'pascal_export.csv', 'text/csv;charset=utf-8;');
            }
            
            // Функция экспорта в Excel
            function exportToExcel(data, headers, includeHeaders = true, formatDates = false) {
                // Создаем простой CSV, который можно открыть в Excel
                let excelContent = '';
                
                if (includeHeaders) {
                    excelContent += headers.join('\\t') + '\\n';
                }
                
                data.forEach(row => {
                    const rowData = headers.map(header => {
                        let value = row[header] || '';
                        
                        if (formatDates) {
                            if (header.includes('date') || header.includes('timestamp')) {
                                try {
                                    const date = new Date(value);
                                    if (!isNaN(date)) {
                                        // Формат для Excel
                                        value = date.toISOString().split('T')[0];
                                    }
                                } catch(e) {
                                    // Оставляем как есть
                                }
                            }
                        }
                        
                        // Экранирование для Excel
                        if (typeof value === 'string') {
                            value = value.replace(/"/g, '""');
                            if (value.includes('\\t') || value.includes('\\n') || value.includes('"')) {
                                value = `"${value}"`;
                            }
                        }
                        
                        return value;
                    });
                    excelContent += rowData.join('\\t') + '\\n';
                });
                
                downloadFile(excelContent, 'pascal_export.xlsx', 
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
            }
            
            // Функция экспорта в JSON
            function exportToJSON(data, formatDates = false) {
                const jsonData = formatDates ? 
                    data.map(row => {
                        const formattedRow = {...row};
                        Object.keys(formattedRow).forEach(key => {
                            if (key.includes('date') || key.includes('timestamp')) {
                                try {
                                    const date = new Date(formattedRow[key]);
                                    if (!isNaN(date)) {
                                        formattedRow[key] = date.toISOString();
                                    }
                                } catch(e) {
                                    // Оставляем как есть
                                }
                            }
                        });
                        return formattedRow;
                    }) : data;
                
                const jsonString = JSON.stringify(jsonData, null, 2);
                downloadFile(jsonString, 'pascal_export.json', 'application/json');
            }
            
            // Общая функция скачивания файла
            function downloadFile(content, filename, mimeType) {
                const blob = new Blob([content], { type: mimeType });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }
            
            // Простая сортировка таблицы
            document.addEventListener('DOMContentLoaded', function() {
                const ths = document.querySelectorAll('th');
                ths.forEach(th => {
                    th.style.cursor = 'pointer';
                    th.addEventListener('click', function() {
                        const table = this.closest('table');
                        const tbody = table.querySelector('tbody');
                        const rows = Array.from(tbody.querySelectorAll('tr'));
                        const colIndex = Array.from(this.parentElement.children).indexOf(this);
                        const field = this.getAttribute('data-field');
                        
                        const isAsc = this.classList.contains('asc');
                        rows.sort((a, b) => {
                            const aCell = a.children[colIndex];
                            const bCell = b.children[colIndex];
                            const aText = aCell ? aCell.textContent : '';
                            const bText = bCell ? bCell.textContent : '';
                            
                            // Пытаемся сравнить как числа
                            const aNum = parseFloat(aText.replace(',', '.'));
                            const bNum = parseFloat(bText.replace(',', '.'));
                            
                            if (!isNaN(aNum) && !isNaN(bNum)) {
                                return isAsc ? bNum - aNum : aNum - bNum;
                            }
                            
                            // Сравниваем булевы значения
                            if (field === 'boolean_field') {
                                const aBool = aText === 'ИСТИНА' ? 1 : 0;
                                const bBool = bText === 'ИСТИНА' ? 1 : 0;
                                return isAsc ? bBool - aBool : aBool - bBool;
                            }
                            
                            // Иначе как строки
                            return isAsc ? bText.localeCompare(aText) : aText.localeCompare(bText);
                        });
                        
                        // Убираем предыдущие классы сортировки
                        ths.forEach(th => th.classList.remove('asc', 'desc'));
                        
                        // Добавляем новый класс
                        this.classList.toggle('asc', !isAsc);
                        this.classList.toggle('desc', isAsc);
                        
                        // Обновляем таблицу
                        rows.forEach(row => tbody.appendChild(row));
                    });
                });
                
                // Фильтрация по поиску (дополнительная функция)
                const searchInput = document.createElement('input');
                searchInput.type = 'text';
                searchInput.placeholder = 'Поиск по таблице...';
                searchInput.style.cssText = `
                    padding: 8px;
                    width: 300px;
                    margin-bottom: 10px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                `;
                document.querySelector('.container').insertBefore(searchInput, document.getElementById('dataTable'));
                
                searchInput.addEventListener('input', function() {
                    const searchTerm = this.value.toLowerCase();
                    const rows = document.querySelectorAll('#dataTable tbody tr');
                    
                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        const rowText = Array.from(cells).map(cell => cell.textContent.toLowerCase()).join(' ');
                        
                        if (rowText.includes(searchTerm)) {
                            row.style.display = '';
                        } else {
                            row.style.display = 'none';
                        }
                    });
                });
            });
        </script>
    </body>
    </html>
    """
    
    return html

__all__ = ["router"]