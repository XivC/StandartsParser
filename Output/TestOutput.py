import sqlite3

import openpyxl as pyx
from Database.Controller import Controller
from Database.Sqlite import Sqlite
from openpyxl.utils.cell import column_index_from_string

class TestOutput:

    @staticmethod
    def get_cell(ws, row, column):
        column = column_index_from_string(column)
        return ws.cell(row, column)

    @staticmethod
    def dump_db(filename, out_filename):
        wb = pyx.load_workbook(filename)
        ws = wb.active
        db = Controller("sqlite")

        db.execute('''SELECT * from parsed_standards''')
        data = [[x for x in y] for y in db.get()]
        for r in range(len(data)):
            for c in range(len(data[r])):
                if data[r][c] is None:
                    data[r][c] = ""
        n = 0
        for row in range(3, len(data) + 3):
            TestOutput.get_cell(ws, row, 'A').value = data[row-3][1] + '\n' + data[row-3][12] + '\n' + data[row-3][14]
            TestOutput.get_cell(ws, row, 'B').value = data[row - 3][2]
            TestOutput.get_cell(ws, row, 'C').value = data[row - 3][3]
            TestOutput.get_cell(ws, row, 'D').value = data[row - 3][5]
            TestOutput.get_cell(ws, row, 'E').value = data[row - 3][6]
            TestOutput.get_cell(ws, row, 'F').value = data[row - 3][7]
            TestOutput.get_cell(ws, row, 'G').value = data[row - 3][9]
            TestOutput.get_cell(ws, row, 'H').value = data[row - 3][0]
            TestOutput.get_cell(ws, row, 'J').value = data[row - 3][10]
            TestOutput.get_cell(ws, row, 'K').value = data[row - 3][11]
            TestOutput.get_cell(ws, row, 'L').value = data[row - 3][12]
            TestOutput.get_cell(ws, row, 'M').value = data[row - 3][13]
            TestOutput.get_cell(ws, row, 'S').value = data[row - 3][14]
            TestOutput.get_cell(ws, row, 'U').value = data[row - 3][15]
            TestOutput.get_cell(ws, row, 'W').value = data[row - 3][17]
            TestOutput.get_cell(ws, row, 'X').value = data[row - 3][18]
            TestOutput.get_cell(ws, row, 'Y').value = data[row - 3][19]
            TestOutput.get_cell(ws, row, 'Z').value = data[row - 3][20]
            TestOutput.get_cell(ws, row, 'AA').value = data[row - 3][21]
            TestOutput.get_cell(ws, row, 'AB').value = data[row - 3][22]
            TestOutput.get_cell(ws, row, 'AC').value = data[row - 3][23]
            TestOutput.get_cell(ws, row, 'AD').value = data[row - 3][24]

        wb.save(out_filename)






