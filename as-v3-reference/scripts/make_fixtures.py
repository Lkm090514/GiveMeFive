"""GMF-authored physics fixtures, not official AP questions. No third-party questions embedded."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image,ImageDraw
import io


def make_pdf(path,answers="partial",two_columns=False):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    c=canvas.Canvas(str(path),pagesize=(612,792))
    c.setTitle("GMF authored mechanics test fixture")
    c.setFont("Helvetica",11)
    c.drawString(40,760,"GMF authored mechanics fixture - not an official AP exam")
    def text(x,y,s): c.drawString(x,y,s)
    if two_columns:
        for x,n in [(35,1),(325,2)]:
            text(x,710,f"{n}. A mass of 2 kg has net force 6 N.")
            text(x,690,"Find its acceleration using F = m*a.")
            for i,s in enumerate(["(A) 1 m/s^2","(B) 2 m/s^2","(C) 3 m/s^2","(D) 6 m/s^2"]):text(x,660-i*20,s)
        c.save();return path
    text(40,715,"1. A block of mass 2 kg is on a frictionless horizontal table.")
    text(40,696,"A net horizontal force of 6 N acts on it. Find its acceleration.")
    for y,s in [(671,"(A) 1 m/s^2"),(651,"(B) 2 m/s^2"),(631,"(C) 3 m/s^2"),(611,"(D) 6 m/s^2")]:text(50,y,s)
    if answers!="none":text(40,589,"Answer: C")
    text(40,540,"2. A uniform disk of mass M and radius R rotates about its center.")
    text(40,520,"A tangential force F acts at its rim as shown. Find angular acceleration.")
    text(50,494,"(A) F/(M*R)   (B) 2*F/(M*R)   (C) F*R/M   (D) 0")
    c.circle(140,410,42);c.line(140,410,182,410);text(149,416,"R")
    c.line(182,410,182,465);c.line(182,465,178,458);c.line(182,465,186,458);text(190,451,"F")
    text(90,350,"I = M*R^2/2     torque = F*R")
    if answers=="all":text(40,325,"Answer: B")
    text(40,285,"3. A spring of constant k is compressed by distance x.")
    text(40,265,"Which expression is its elastic potential energy?")
    text(50,240,"(A) k*x   (B) k*x^2/2   (C) k*x^2   (D) 2*k*x")
    graph=Image.new("RGB",(260,100),"white");draw=ImageDraw.Draw(graph)
    draw.line((10,70,250,70),fill="black",width=2)
    points=[(20,45)]+[(30+i*12,30 if i%2 else 60) for i in range(12)]+[(190,45)]
    draw.line(points,fill="black",width=2);draw.rectangle((190,25,230,65),outline="black",width=2)
    buf=io.BytesIO();graph.save(buf,format="PNG");buf.seek(0)
    c.drawImage(ImageReader(buf),50,130,width=260,height=100)
    if answers=="all":text(40,110,"Answer: B")
    if answers=="conflict":
        c.showPage();c.setFont("Helvetica",11);text(40,730,"Answer Key");text(40,700,"1 B   2 B   3 B")
    c.save();return path


def make_scanned(source,destination):
    import pdfplumber
    with pdfplumber.open(source) as pdf: image=pdf.pages[0].to_image(resolution=144).original.convert("RGB")
    c=canvas.Canvas(str(destination),pagesize=(612,792));c.drawImage(ImageReader(image),0,0,width=612,height=792);c.save()


if __name__=="__main__":
    make_pdf("examples/mechanics-partial.pdf","partial")
    make_pdf("examples/mechanics-no-answers.pdf","none")
    print("Created 2 GMF-authored reproducible physics fixture PDFs")

