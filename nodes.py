
import os
import sys
import importlib
import importlib.util
import inspect
import tokenize
from PySide2 import QtCore, QtWidgets, QtGui


def load_module_from_path(path):
    name = os.path.basename(os.path.splitext(path)[0])

    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_module(pymodule_path):
    return importlib.import_module(pymodule_path)


def _parse_pymodule(self):
    self.module = self.load_module_from_path(self.pymodule_path)
    functions = inspect.getmembers(self.module, lambda m: inspect.isfunction(m))
    print(self.module)
    for f in functions:
        print(f[0])
        print(inspect.signature(f[1]))


class Node(QtWidgets.QGraphicsItem):
    def __init__(self, name, label, parentCanvas, inputs=None, outputs=None, x=0, y=0, w=125, h=50, pW=20, pH=15):
        QtWidgets.QGraphicsItem.__init__(self)

        self.name            = name
        self.label           = label
        self.parentCanvas     = parentCanvas
        self.inputsPlugs     = []
        self.outputsPlugs    = []
        self.pluggedOnInput  = {}
        self.pluggedOnOutput = {}

        if inputs:
            y += pH
            w += pH

        if outputs:
            w += pH

        self.nodeRect = QtCore.QRect(x, y, w, h)

        self.pen = QtGui.QPen(QtCore.Qt.SolidLine)
        self.pen.setColor(QtGui.QColor(QtCore.Qt.darkGray))

        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges)

        for nPlug, i in enumerate(inputs):
            newPlug = Plug(i, i, self, nPlug, 0, pW, pH)
            self.inputsPlugs.append(newPlug)

        for nPlug, o in enumerate(outputs):
            newPlug = Plug(o, o, self, nPlug, 1, pW, pH)
            self.outputsPlugs.append(newPlug)

    def boundingRect(self):
        #if self.connectedWire:
        #    self.connectedWire.update()
        return QtCore.QRectF(self.nodeRect)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            for p in self.inputsPlugs + self.outputsPlugs:
                if p.connectedWire:
                    p.connectedWire.update()

        return QtWidgets.QGraphicsItem.itemChange(self, change, value)

    def paint(self, painter, option, widget):
        painter.setPen(self.pen)
        painter.setBrush(QtCore.Qt.gray)
        painter.drawRect(self.nodeRect)

    def mousePressEvent(self, event):
        self.update()
        QtWidgets.QGraphicsItem.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        self.update()
        QtWidgets.QGraphicsItem.mouseReleaseEvent(self, event)


class Plug(QtWidgets.QGraphicsItem):
    def __init__(self, name, label, parentNode, num=0, type=0, w=20, h=15):
        QtWidgets.QGraphicsItem.__init__(self)

        self.plugName        = name
        self.plugLabel       = label
        self.plugNum         = num
        self.plugType        = type
        self.plugParent      = parentNode
        self.plugRect        = self.computeRect(w, h)
        self.connectedPlug   = None
        self.connectedWire   = None
        self.nodeGraphScene  = self.plugParent.parentCanvas

        self.setParentItem(self.plugParent)
        
        self.pen = QtGui.QPen(QtCore.Qt.SolidLine)
        self.pen.setColor(QtGui.QColor(QtCore.Qt.darkGray))

    def computeRect(self, w, h):
        x = self.plugNum * (w + 5)
        if self.plugType == 1:
            y = self.plugParent.nodeRect.bottom()
        else:
            y = 0

        return QtCore.QRect(x, y, w, h)

    def boundingRect(self):
        return QtCore.QRectF(self.plugRect)

    def _connectOnPlug(self, otherPlug, wire):
        self.connectedPlug = otherPlug
        self.connectedWire = wire

    def connectOnPlug(self, otherPlug):
        newWire = self.nodeGraphScene.createWire(self, otherPlug)
        self._connectOnPlug(otherPlug, newWire)
        otherPlug._connectOnPlug(self, newWire)

    def paint(self, painter, option, widget):
        painter.setPen(self.pen)
        painter.setBrush(QtCore.Qt.black)
        painter.drawRect(self.plugRect)

    def mousePressEvent(self, event):
        self.update()
        self.plugParent.parentCanvas.onPlugClicked(event, self)

    def mouseReleaseEvent(self, event):
        self.update()


class Wire(QtWidgets.QGraphicsItem):
    def __init__(self, plugSrc, plugDst):
        QtWidgets.QGraphicsItem.__init__(self)

        self.plugSrc = plugSrc
        self.plugDst = plugDst

        self.parentCanvas = plugSrc.plugParent.parentCanvas
        
        self.pen = QtGui.QPen(QtCore.Qt.SolidLine)
        self.pen.setColor(QtGui.QColor(QtCore.Qt.darkGray))

    def boundingRect(self):
        srcPoint = self.plugSrc.sceneBoundingRect().center()
        dstPoint = self.plugDst.sceneBoundingRect().center()

        rect = QtCore.QRectF(
            QtCore.QPoint(
                min(srcPoint.x(), dstPoint.x()),
                min(srcPoint.y(), dstPoint.y())
            ),
            QtCore.QPoint(
                max(srcPoint.x(), dstPoint.x()),
                max(srcPoint.y(), dstPoint.y())
            ),
        )

        return rect

    def paint(self, painter, option, widget):
        painter.setPen(self.pen)
        painter.setBrush(QtCore.Qt.black)

        if self.plugSrc and self.plugDst:
            painter.drawLine(self.plugSrc.sceneBoundingRect().center(), self.plugDst.sceneBoundingRect().center())


class GraphCanvasWidget(QtWidgets.QGraphicsView):
    def __init__(self):
        QtWidgets.QGraphicsView.__init__(self)

        self.scene = QtWidgets.QGraphicsScene(self)
        self.scene.setItemIndexMethod(QtWidgets.QGraphicsScene.NoIndex)
        #self.scene.setSceneRect(-200, -200, 400, 400)

        self.nodes = []
        self.wires = []
        self.setScene(self.scene)

        self.plugClicked = None

        self.setSceneRect(0, 0, 500, 500)
        self.setWindowTitle(self.tr("Nodes Test"))

    def onPlugClicked(self, event, plug):
        print("Plug clicked {}".format(plug))
        if self.plugClicked is None:
            self.plugClicked = plug
        else:
            self.plugClicked.connectOnPlug(plug)
            self.plugClicked = None

    def createWire(self, plugSrc, plugDst):
        newWire = Wire(plugSrc, plugDst)
        #self.wires.append(newWire)
        self.scene.addItem(newWire)
        return newWire

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space:
            # newNode = Node("test", "TestNode", self.scene, inputs=["lal", "lul"], outputs=["lal", "lul"])
            # self.nodes.append(newNode)
            # self.scene.addItem(newNode)

            script_node = FunctionNode(test, self)
            self.nodes.append(script_node)
            self.scene.addItem(script_node)


class FunctionNode(Node):
    def __init__(self, func, parentCanvas, x=0, y=0, w=125, h=50, pW=20, pH=15):
        self.func = func
        self.name = None
        self.args = None
        self.returns = None
        self._parse_pyfunction()

        Node.__init__(self, self.name, self.name, parentCanvas, inputs=self.get_inputs(), outputs=self.get_outputs(), x=x, y=y, w=w, h=h, pW=pW, pH=pH)

    def _parse_pyfunction(self):
        signature = inspect.signature(self.func)
        self.name = self.func.__name__
        self.args = signature.parameters
        self.returns = signature.return_annotation

    def get_inputs(self):
        return list(map(lambda a: a, self.args))

    def get_outputs(self):
        return ["return"]


def test(t1, t2, k1=3):
    return "caca"



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    QtCore.qsrand(QtCore.QTime(0,0,0).secsTo(QtCore.QTime.currentTime()))

    widget = GraphCanvasWidget()
    widget.show()

    sys.exit(app.exec_())
