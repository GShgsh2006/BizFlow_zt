#生成excal表（员工信息）
from openpyxl import Workbook
from io import BytesIO


def build_excel(rows: list) -> bytes:
    """rows: [{"name": 姓名, "tasks": 任务, "salary": 工资}, ...]"""
    wb = Workbook()
    ws = wb.active
    ws.title = "员工信息"
    ws.append(["员工姓名", "任务", "工资"])
    for r in rows or []:
        ws.append([r.get("name", ""), r.get("tasks", ""), r.get("salary", 0)])
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()
