import xlwt
import numpy
from datetime import datetime

example  = numpy.matrix([[1,2],[3,4],[5,6],[7,8]])
example2 = numpy.matrix('1 2; 3 4')

print(example)
print(example2)
style0 = xlwt.easyxf('font: name Times New Roman, color-index black',
    num_format_str='#,##0.00')
style1 = xlwt.easyxf(num_format_str='D-MMM-YY')

wb = xlwt.Workbook()
ws = wb.add_sheet('A Test Sheet')

ws.write(0, 0, 1234.56, style0)

wb.save('example.xls')
