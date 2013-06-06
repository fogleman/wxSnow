import wx
import ctypes
import random
import math
import time

APP_NAME = 'wxSnow'
FRAME_RATE = 30

COUNTS = [100, 200, 300, 400, 500]
SPEEDS = [256, 128, 64, 32, 16]

COUNT = 200
SPEED = 64
ROTATE = False

def menu_item(menu, label, func, kind=wx.ITEM_NORMAL, icon=None):
    item = wx.MenuItem(menu, -1, label, kind=kind)
    if func:
        menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    if icon:
        item.SetBitmap(wx.Bitmap(icon))
    menu.AppendItem(item)
    return item
    
class Flake(object):
    RADIUS = 9
    def __init__(self, width, height, bitmap):
        self.bitmap = bitmap
        self.w = width
        self.h = height
        self.x = random.randint(0, width-1)
        self.y = random.randint(0, height-1)
        self.r = 0
        self.reset_speed()
    def __repr__(self):
        return '<%d, %d>' % (self.x, self.y)
    def reset_speed(self):
        self.dx = 0
        self.dy = random.randint(250, 500) / float(SPEED)
        self.dr = random.randint(-500, 500) / (SPEED / 2.0)
    @property
    def position(self):
        return int(round(self.x)), int(round(self.y))
    @property
    def rect(self):
        x, y = self.position
        r = Flake.RADIUS
        return x - r, y - r, r * 2, r * 2
    def update(self):
        self.dx += random.randint(-100, 100) / (SPEED * 5.0)
        if abs(self.dx) > 1:
            self.dx /= abs(self.dx)
        self.x += self.dx + 2
        self.y += self.dy
        self.r += self.dr
        if self.x < 0:
            self.x = self.w - 1
        if self.x >= self.w:
            self.x = 0
        if self.y >= self.h:
            self.y = 0
        if self.r >= 360:
            self.r = 0
    def draw(self, dc):
        if ROTATE:
            w, h = self.bitmap.GetSize()
            img = wx.ImageFromBitmap(self.bitmap)
            img = img.Rotate(math.radians(self.r), (w / 2, h / 2))
            bitmap = wx.BitmapFromImage(img)
        else:
            bitmap = self.bitmap
        w, h = bitmap.GetSize()
        x, y = self.position
        dc.DrawBitmap(bitmap, x - w / 2, y - h / 2)
        
class CollisionDetector(object):
    @staticmethod
    def cmp_x(a, b):
        return cmp(a.x, b.x)
    @staticmethod
    def cmp_y(a, b):
        return cmp(a.y, b.y)
    def __init__(self, objects):
        self.objects = list(objects)
        self.x_list = sorted(self.objects, cmp=CollisionDetector.cmp_x)
        self.y_list = sorted(self.objects, cmp=CollisionDetector.cmp_y)
    def get_collisions(self):
        self.x_list.sort(cmp=CollisionDetector.cmp_x)
        self.y_list.sort(cmp=CollisionDetector.cmp_y)
        xset = set()
        yset = set()
        n = len(self.objects)
        for i1 in range(n):
            a = self.x_list[i1]
            for i2 in range(i1+1, n):
                b = self.x_list[i2]
                if not self.test(a, b, 'x'):
                    break
                xset.add(frozenset((a, b)))
            a = self.y_list[i1]
            for i2 in range(i1+1, n):
                b = self.y_list[i2]
                if not self.test(a, b, 'y'):
                    break
                yset.add(frozenset((a, b)))
        collisions = list(xset & yset)
        return self.merge(collisions)
    def merge(self, sets):
        while True:
            n = len(sets)
            for i1 in range(n):
                a = sets[i1]
                for i2 in range(i1+1, n):
                    b = sets[i2]
                    if a & b:
                        sets[i1] = a | b
                        del sets[i2]
                        break
                else:
                    continue
                break
            else:
                break
        return sets
    def test(self, a, b, p):
        a1 = getattr(a, p)
        b1 = getattr(b, p)
        a2 = a1 + Flake.RADIUS * 2
        b2 = b1 + Flake.RADIUS * 2
        return \
            (a1 >= b1 and a1 <= b2) or \
            (a2 >= b1 and a2 <= b2) or \
            (b1 >= a1 and b1 <= a2) or \
            (b2 >= a1 and b2 <= a2)
            
class Frame(wx.Frame):
    def __init__(self, handle):
        super(Frame, self).__init__(None, -1, '')
        self.running = True
        self.icon = TaskBarIcon(self)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.AssociateHandle(handle)
        w, h = self.GetSize()
        self.w, self.h = w, h
        self.bitmaps = [wx.Bitmap('images/flake%d.png' % n) for n in range(1, 9)]
        self.flakes = []
        self.create_flakes()
        self.update()
    def create_flakes(self):
        self.flakes = self.flakes[:COUNT]
        n = COUNT - len(self.flakes)
        flakes = [Flake(self.w, self.h, self.bitmaps[random.randint(0, 7)]) for i in range(n)]
        self.flakes.extend(flakes)
        self.detector = CollisionDetector(self.flakes)
    def update(self):
        if not self.running:
            return
        start = time.time()
        collisions = self.detector.get_collisions()
        drawn = set()
        dc = wx.WindowDC(self)
        for group in collisions:
            for flake in group:
                self.RefreshRect(flake.rect)
            self.Update()
            for flake in group:
                flake.update()
                flake.draw(dc)
                drawn.add(flake)
        for flake in self.flakes:
            if flake in drawn:
                continue
            self.RefreshRect(flake.rect)
            self.Update()
            flake.update()
            flake.draw(dc)
        dc.Destroy()
        end = time.time()
        millis = int((end - start) * 1000)
        desired = 1000 / FRAME_RATE
        sleep = max(desired - millis, 1)
        wx.CallLater(sleep, self.update)
    def close(self):
        self.running = False
        self.Refresh()
        self.DissociateHandle()
        self.Close()
    def on_close(self, event):
        event.Skip()
        wx.CallAfter(self.icon.Destroy)
        
class TaskBarIcon(wx.TaskBarIcon):
    def __init__(self, parent):
        super(TaskBarIcon, self).__init__()
        self.parent = parent
        self.set_icon('images/icon.png')
    def CreatePopupMenu(self):
        menu = wx.Menu()
        item = menu_item(menu, 'More', self.on_more, icon='images/add.png')
        if COUNT == COUNTS[-1]: item.Enable(False)
        item = menu_item(menu, 'Less', self.on_less, icon='images/delete.png')
        if COUNT == COUNTS[0]: item.Enable(False)
        menu.AppendSeparator()
        item = menu_item(menu, 'Faster', self.on_faster, icon='images/add.png')
        if SPEED == SPEEDS[-1]: item.Enable(False)
        item = menu_item(menu, 'Slower', self.on_slower, icon='images/delete.png')
        if SPEED == SPEEDS[0]: item.Enable(False)
        menu.AppendSeparator()
        if ROTATE:
            menu_item(menu, "Don't Rotate", self.on_rotate, icon='images/arrow_down.png')
        else:
            menu_item(menu, "Rotate", self.on_rotate, icon='images/arrow_rotate_clockwise.png')
        menu.AppendSeparator()
        menu_item(menu, 'Exit', self.on_exit, icon='images/door_out.png')
        return menu
    def set_icon(self, image_file, tooltip='wxSnow'):
        icon = wx.IconFromBitmap(wx.Bitmap(image_file))
        self.SetIcon(icon, tooltip)
    def update(self):
        wx.CallAfter(self._update)
    def _update(self):
        parent = self.parent
        parent.create_flakes()
        for flake in parent.flakes:
            flake.reset_speed()
        parent.Refresh()
    def on_rotate(self, event):
        global ROTATE
        ROTATE = not ROTATE
    def on_more(self, event):
        global COUNT, COUNTS
        COUNT = COUNTS[COUNTS.index(COUNT) + 1]
        self.update()
    def on_less(self, event):
        global COUNT, COUNTS
        COUNT = COUNTS[COUNTS.index(COUNT) - 1]
        self.update()
    def on_faster(self, event):
        global SPEED, SPEEDS
        SPEED = SPEEDS[SPEEDS.index(SPEED) + 1]
        self.update()
    def on_slower(self, event):
        global SPEED, SPEEDS
        SPEED = SPEEDS[SPEEDS.index(SPEED) - 1]
        self.update()
    def on_exit(self, event):
        wx.CallAfter(self.parent.close)
        
def find_window(parent, names):
    if not names:
        return parent
    name = unicode(names[0])
    child = 0
    while True:
        child = ctypes.windll.user32.FindWindowExW(parent, child, name, 0)
        if not child:
            return 0
        result = find_window(child, names[1:])
        if result:
            return result
            
if __name__ == '__main__':
    desktop = ctypes.windll.user32.GetDesktopWindow()
    handle = 0
    handle = handle or find_window(desktop, ['Progman', 'SHELLDLL_DefView', 'SysListView32'])
    handle = handle or find_window(desktop, ['WorkerW', 'SHELLDLL_DefView', 'SysListView32'])
    app = wx.PySimpleApp()
    frame = Frame(handle)
    app.MainLoop()
    