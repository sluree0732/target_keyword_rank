import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


def export_to_excel(results: list, filepath: str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '키워드 분석 결과'

    header_fill = PatternFill(start_color='1565C0', end_color='1565C0', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF', size=11)
    center = Alignment(horizontal='center', vertical='center')
    thin = Side(style='thin', color='BDBDBD')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    headers = ['블로그 주소', '오늘 방문자', '게시글 제목', '키워드', '순위']
    for col, text in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=text)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        cell.border = border

    ws.row_dimensions[1].height = 24

    rank_in_font = Font(color='1B5E20', bold=True)
    rank_out_font = Font(color='B71C1C')

    for row_idx, result in enumerate(results, 2):
        rank = result['rank']
        rank_text = f'{rank}위' if rank > 0 else '순위 밖'
        visitor = result.get('visitor_count', 0)
        visitor_text = str(visitor) if visitor > 0 else '-'

        ws.cell(row=row_idx, column=1, value=result['blog_url']).border = border

        visitor_cell = ws.cell(row=row_idx, column=2, value=visitor_text)
        visitor_cell.alignment = center
        visitor_cell.border = border

        ws.cell(row=row_idx, column=3, value=result['post_title']).border = border
        ws.cell(row=row_idx, column=4, value=result['keyword']).border = border

        rank_cell = ws.cell(row=row_idx, column=5, value=rank_text)
        rank_cell.alignment = center
        rank_cell.border = border
        rank_cell.font = rank_in_font if rank > 0 else rank_out_font

        if row_idx % 2 == 0:
            row_fill = PatternFill(start_color='F5F5F5', end_color='F5F5F5', fill_type='solid')
            for col in range(1, 6):
                ws.cell(row=row_idx, column=col).fill = row_fill

    ws.column_dimensions['A'].width = 35
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 50
    ws.column_dimensions['D'].width = 25
    ws.column_dimensions['E'].width = 12

    wb.save(filepath)
