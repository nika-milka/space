import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
import csv
import random
from io import StringIO

class PascalCSVGenerator:
    @staticmethod
    def generate_export_excel(data: List[Dict[str, Any]], filename: str = "export.xlsx"):
        """Генерация Excel файла для экспорта"""
        import pandas as pd
        from datetime import datetime
        
        df = pd.DataFrame(data)
        
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Экспорт', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['Экспорт']
            
            # Форматы
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
            time_format = workbook.add_format({'num_format': 'hh:mm:ss'})
            datetime_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
            number_format = workbook.add_format({'num_format': '#,##0.00'})
            
            # Применяем форматы к колонкам
            for idx, col in enumerate(df.columns):
                if 'timestamp' in col.lower():
                    worksheet.set_column(idx, idx, 25, datetime_format)
                elif 'date' in col.lower():
                    worksheet.set_column(idx, idx, 15, date_format)
                elif 'time' in col.lower():
                    worksheet.set_column(idx, idx, 15, time_format)
                elif any(x in col.lower() for x in ['numeric', 'id', 'number']):
                    worksheet.set_column(idx, idx, 15, number_format)
                elif 'boolean' in col.lower():
                    worksheet.set_column(idx, idx, 12)
                else:
                    worksheet.set_column(idx, idx, 20)
            
            # Автофильтр
            worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)
            
            # Замораживаем заголовки
            worksheet.freeze_panes(1, 0)
            
            # Добавляем информацию
            info_text = f"Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nКоличество строк: {len(df)}"
            worksheet.write(len(df) + 2, 0, info_text)
        
        return filename, filename
    @staticmethod
    def generate_csv_with_types(filename: str = "pascal_data.csv"):
        """Генерация CSV с правильными типами данных"""
        data = []
        
        # Генерация тестовых данных
        base_date = datetime.now()
        
        for i in range(100):
            row_date = base_date - timedelta(days=i)
            
            row = {
                "timestamp": row_date.isoformat(),
                "boolean_field": "ИСТИНА" if i % 2 == 0 else "ЛОЖЬ",
                "numeric_field": round(i * 1.5 + random.uniform(0, 10), 2),
                "text_field": f"Строка данных номер {i}",
                "date_field": row_date.strftime("%Y-%m-%d"),
                "time_field": row_date.strftime("%H:%M:%S"),
                "category": random.choice(["А", "Б", "В", "Г", "Д"]),
                "status": random.choice(["активен", "завершен", "в процессе"])
            }
            data.append(row)
        
        # Сохранение с указанием типов
        df = pd.DataFrame(data)
        
        # Экспорт в Excel с форматами
        excel_filename = "pascal_data.xlsx"
        with pd.ExcelWriter(excel_filename, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Данные', index=False)
            
            # Получаем workbook и worksheet
            workbook = writer.book
            worksheet = writer.sheets['Данные']
            
            # Форматы
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
            time_format = workbook.add_format({'num_format': 'hh:mm:ss'})
            number_format = workbook.add_format({'num_format': '#,##0.00'})
            boolean_format = workbook.add_format({'align': 'center'})
            
            # Применяем форматы к колонкам
            worksheet.set_column('A:A', 25)  # timestamp
            worksheet.set_column('B:B', 15, boolean_format)  # boolean
            worksheet.set_column('C:C', 15, number_format)  # numeric
            worksheet.set_column('D:D', 30)  # text
            worksheet.set_column('E:E', 15, date_format)  # date
            worksheet.set_column('F:F', 15, time_format)  # time
            worksheet.set_column('G:G', 10)  # category
            worksheet.set_column('H:H', 15)  # status
            
            # Добавляем автофильтр
            worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)
        
        # Сохранение CSV
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        return filename, excel_filename
    
    @staticmethod
    def generate_test_data(count: int = 50) -> List[Dict[str, Any]]:
        """Генерация тестовых данных для API"""
        data = []
        base_date = datetime.now()
        
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
            data.append(row)
        
        return data
    
    @staticmethod
    def generate_csv_string(data: List[Dict[str, Any]]) -> str:
        """Конвертация данных в CSV строку"""
        if not data:
            return ""
        
        output = StringIO()
        
        # Определяем кодировку для кириллицы
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        return output.getvalue()