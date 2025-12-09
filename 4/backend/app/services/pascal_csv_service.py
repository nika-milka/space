import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
import csv

class PascalCSVGenerator:
    @staticmethod
    def generate_csv_with_types(filename: str = "pascal_data.csv"):
        """Генерация CSV с правильными типами данных"""
        data = []
        
        # Генерация тестовых данных
        for i in range(100):
            row = {
                "timestamp": datetime.now().isoformat(),
                "boolean_field": "ИСТИНА" if i % 2 == 0 else "ЛОЖЬ",
                "numeric_field": i * 1.5,
                "text_field": f"Строка данных номер {i}",
                "date_field": datetime.now().strftime("%Y-%m-%d"),
                "time_field": datetime.now().strftime("%H:%M:%S")
            }
            data.append(row)
        
        # Сохранение с указанием типов
        df = pd.DataFrame(data)
        
        # Экспорт в Excel с форматами
        with pd.ExcelWriter("pascal_data.xlsx", engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Данные', index=False)
            
            # Получаем workbook и worksheet
            workbook = writer.book
            worksheet = writer.sheets['Данные']
            
            # Форматы
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
            time_format = workbook.add_format({'num_format': 'hh:mm:ss'})
            number_format = workbook.add_format({'num_format': '#,##0.00'})
            
            # Применяем форматы к колонкам
            worksheet.set_column('A:A', 25)  # timestamp
            worksheet.set_column('B:B', 15)  # boolean
            worksheet.set_column('C:C', 15, number_format)  # numeric
            worksheet.set_column('D:D', 30)  # text
            worksheet.set_column('E:E', 15, date_format)  # date
            worksheet.set_column('F:F', 15, time_format)  # time
        
        # Сохранение CSV
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        return filename, "pascal_data.xlsx"