import sys
from PyQt6.QtWidgets import QApplication, QGraphicsScene, QGraphicsPixmapItem, QGraphicsBlurEffect
from PyQt6.QtGui import QPainter, QPixmap, QColor
from PyQt6.QtCore import Qt
import time

app = QApplication(sys.argv)

pix = QPixmap(1280, 720)
pix.fill(QColor("red"))

start = time.time()

effect = QGraphicsBlurEffect()
effect.setBlurRadius(20.0)

scene = QGraphicsScene()
item = QGraphicsPixmapItem(pix)
item.setGraphicsEffect(effect)
scene.addItem(item)

res = QPixmap(pix.size())
res.fill(Qt.GlobalColor.transparent)

ptr = QPainter(res)
scene.render(ptr)
ptr.end()

print("Time taken:", time.time() - start)
