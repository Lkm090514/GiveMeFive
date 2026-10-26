from pathlib import Path
from reportlab.pdfgen import canvas
from docx import Document

def mixed_pdf(path):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);c=canvas.Canvas(str(path),pagesize=(612,792));c.setFont('Helvetica',11)
 lines=[(760,'GMF authored QA fixture - CC0 - NOT an official AP paper'),(735,'Section I: Multiple Choice'),(705,'Questions 1-2 refer to the following block diagram.'),(595,'1. A block has mass 2 kg. Use net F = ma. Find acceleration for 6 N.'),(570,'(A) 1 m/s^2'),(550,'(B) 3 m/s^2'),(530,'(C) 6 m/s^2'),(490,'2. The same block receives 8 N. Use net F = ma.'),(465,'(A) 2 m/s^2'),(445,'(B) 4 m/s^2'),(425,'(C) 8 m/s^2'),(375,'Section II: Free Response'),(350,'1. Derive an expression for the acceleration.'),(325,'(A) Explain the force model.'),(300,'(B) Explain the dimensions.'),(260,'Answer Key'),(235,'1 B   2 B')]
 for y,t in lines:c.drawString(40,y,t)
 c.rect(110,640,60,30);c.line(170,655,240,655);c.drawString(190,667,'F');c.save();return path

def docx_file(path):
 d=Document();
 for t in ['GMF authored DOCX QA fixture - CC0','Section I: Multiple Choice','1. A mass of 2 kg receives a net force of 6 N. Use net F = ma.','(A) 1 m/s^2','(B) 3 m/s^2','Answer: B','2. A mass of 2 kg receives 8 N. Use net F = ma.','(A) 2 m/s^2','(B) 4 m/s^2','Answer: B','Section II: Free Response','1. Explain a physical model.','(A) Describe your reasoning.','(B) Derive an equation.']:d.add_paragraph(t)
 d.save(path);return Path(path)
if __name__=='__main__':mixed_pdf(Path(__file__).parent/'fixtures/v4-mixed.pdf');docx_file(Path(__file__).parent/'fixtures/v4-mixed.docx')
