
from reportlab.pdfgen.canvas import Canvas
from reportlab.graphics.shapes import Rect
from reportlab.lib.colors import PCMYKColor, PCMYKColorSep, Color
from PollyReports import *
from invoicedata import data

black = Color(0,0,0,alpha=1)
c1 = Color(44/255,175/255,107/255.3,alpha=0.3)
white = Color(100,100,100,alpha=1)

rpt = Report(data)
rpt.titleband = Band([
    Image((36,50), width=60, height=65, text="typewriter.png"),
    TextElement((300,0), ("Helvetica", 18), text= "INVOICE  ", key = "invoicenumber"),
    TextElement((110,35), ("Helvetica-Bold", 12), text = "CompuGlobalHyperMegaNet Ltd."),
    TextElement((110,50), ("Helvetica", 11), text = "127.0.0.1 internet street"),
    TextElement((110,65), ("Helvetica", 11), text = "computer, isp, webz"),
    TextElement((110,87), ("Helvetica", 11), text = "derpa@ccghm.net"),
    TextElement((110,102), ("Helvetica", 11), text = "(123)123-1234"),
    TextElement((110,117), ("Helvetica", 11), text = "GST No. 123456789"),
    TextElement((490,40), ("Helvetica-Bold", 13), text = "Invoice Date", align="right"),
    TextElement((490,55), ("Helvetica", 11), key = "invoicedate", align="right"),
    TextElement((490,77), ("Helvetica-Bold", 13), text = "Total Due", align="right"),
    TextElement((490,92), ("Helvetica", 11), key = "invoicedue", align="right"),
    ShapeElement((0,135),shape="line",colors=[black],width=7.5*72, height=0),
])

rpt.detailband = Band([
    TextElement((42, 20), ("Helvetica", 9), key = "lineitem"),
    TextElement((89, 20), ("Helvetica-Bold", 9), key = "resourcetypestr"),
    TextElement((89, 32), ("Helvetica", 8), key = "description", width=420),
    TextElement((330, 20), ("Helvetica", 9), key = "quantity", align="right"),
    TextElement((400, 20), ("Helvetica", 9), key = "rate", align="right"),
    TextElement((440, 20), ("Helvetica", 9), key = "tax", align="right"),
    TextElement((7*72, 20), ("Helvetica", 9), key = "amount", align="right")
])
rpt.detailband.backgrounds = [ShapeElement((30,0),shape="rectangle",colors=[c1,white],width=7*72-24,height=None,fill=True,stroke=False), 
                         ]
rpt.pageheader = Band([
    TextElement((24, 2), ("Helvetica", 10), text = "LINE ITEM"),
    TextElement((85, 2), ("Helvetica", 10), text = "ACTIVITY"),
    TextElement((330, 2), ("Helvetica", 10), text = "QTY", align="right"),
    TextElement((400, 2), ("Helvetica", 10), text = "RATE", align="right"),
    TextElement((440, 2), ("Helvetica", 10), text = "TAX", align="right"),
    TextElement((7*72, 2), ("Helvetica", 10), text = "AMOUNT", align="right"),
    ShapeElement((0, 15), shape="line",colors=[black], width=7.5*72, height=0),
])
rpt.pagefooter = Band([
    TextElement(pos=(36, 16), font=("Helvetica-Bold", 12), sysvar = "pagenumber", format = lambda x: "Page %d" % x),
])
rpt.reportfooter = Band([
    ShapeElement((300, 4), shape="line", width=220, height=0),
    TextElement((300, 7), ("Helvetica-Bold", 11),
        text = "Subtotal"),
    TextElement((300, 20), ("Helvetica-Bold", 11),
        text = "Taxes"),
    TextElement((300, 40), ("Helvetica-Bold", 14),
        text = "Total"),
    TextElement((7*72, 7), ("Helvetica", 11), 
        key = "invoicesubtotal", align="right"),
    TextElement((7*72, 20), ("Helvetica", 11), 
        key = "invoicetotaltax", align="right"),
    TextElement((7*72, 40), ("Helvetica", 14), 
        key = "invoicetotal", align="right"),
    TextElement((150,20), ("Helvetica", 11),
        text = "Your prompt payment is appreciated.  Thank you for your business!", width=190, align="center"),
])

canvas = Canvas("invoice.pdf", (72*8.5, 72*11))
rpt.generate(canvas)
canvas.save()

