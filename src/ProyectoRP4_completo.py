# Copyright (c) 2025 Sebastián Vázquez
# This file is part of FSEM_ProyectoFinal and is licensed under the MIT License.
# See the LICENSE file in the root of this repository for details.

import os, subprocess, threading, time
import Manejador_USB
os.environ["DISPLAY"] = ":0"
os.environ["KIVY_LOG_LEVEL"] = "KIVY"
os.environ["KIVY_GL_BACKEND"] = "sdl2"

from kivy.config import Config
Config.set('input', 'gamepad', 'probesysfs,provider=hidinput')
Config.set('input', 'mouse', 'mouse,disable_multitouch')
from kivy.app import App  
from kivy.animation import Animation
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import NoTransition
from kivy.properties import StringProperty, BooleanProperty, ObjectProperty
from kivy.lang import Builder

class WindowManager(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class EmuladorPopUp(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.auto_dismiss = False 
        self.title = ""

    def apagar(self):
        args = ["sudo", "shutdown", "-h", "now"]
        subprocess.run(args)

class NuevosJuegos(RecycleDataViewBehavior, Label):
    text = StringProperty("")

    def refresh_view_attrs(self, rv, index, data):
        return super().refresh_view_attrs(rv, index, data)
    
class ListaNuevosJuegos(RecycleView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nombres = []

    def mostrar_juegos(self, diccionario):
        datos = []
        for consola, juegos in diccionario.items():
            datos.append({'text': consola[1:5]})
            for nombre_juego in juegos:
                datos.append({'text': nombre_juego})
        self.data = datos
        self.refresh_from_data()

class JuegoItem(RecycleDataViewBehavior, Label):
    indice = None
    seleccion = BooleanProperty(False)
    text = StringProperty("")

    def refresh_view_attrs(self, rv, indice, data):
        self.indice = indice
        return super().refresh_view_attrs(rv, indice, data)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.parent.parent.seleccionar_juego(self.indice)
            return True
        return super().on_touch_down(touch)
    
class ListaJuegos(RecycleView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.juegos = []
        self.indice_seleccionado = 0

    def cargar_juegos(self, ruta):
        if os.path.exists(ruta):
            archivos = [f for f in os.listdir(ruta) if f.lower().endswith(('.gba', '.smc', '.nes'))]
            self.juegos = archivos
            self.data = [{'text': juego} for juego in archivos]
            self.indice_seleccionado = 0
            self.seleccionar_juego(0)

    def seleccionar_juego(self, indice):
        self.indice_seleccionado = indice
        for i in range(len(self.data)):
            self.data[i]['seleccion'] = (i == indice)
        self.refresh_from_data()
        self.actualizar_scroll()

    def obtener_juego_actual(self):
        if 0 <= self.indice_seleccionado < len(self.juegos):
            return self.juegos[self.indice_seleccionado]
        return None
    
    def actualizar_scroll(self):
        if not self.data:
            return

        total_juegos = len(self.data)
        juegos_visibles = 3  
        indice_max = total_juegos - 1  

        primer_visible = int((1.0 - self.scroll_y) * (total_juegos - juegos_visibles))
        primer_visible = max(0, primer_visible)
        ultimo_visible = primer_visible + juegos_visibles - 1

        if self.indice_seleccionado < primer_visible:
            primer_visible = self.indice_seleccionado
        elif self.indice_seleccionado > ultimo_visible:
            primer_visible = self.indice_seleccionado - juegos_visibles + 1

        primer_visible = max(0, min(primer_visible, indice_max - juegos_visibles + 1))

        if indice_max - juegos_visibles + 1 == 0:
            porcentaje = 1.0
        else:
            porcentaje = 1.0 - (primer_visible / (indice_max - juegos_visibles + 1))
            porcentaje = max(0.0, min(1.0, porcentaje))

        self.scroll_y = porcentaje

class Caratula(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_enter(self):
        Clock.schedule_once(lambda dt: self.iniciar_parpadeo(), 0)

    def iniciar_parpadeo(self):
        def loop_anim(*args):
            anim = Animation(opacity=0, duration=0.5) + Animation(opacity=1, duration=0.5)
            anim.bind(on_complete=loop_anim)
            anim.start(self.ids.imagen_start)
        loop_anim()

class Apagado(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class MenuNuevosJuegos(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def mostrar_nuevos_juegos(self, diccionario):
        self.ids.recycleview_nuevosjuegos.mostrar_juegos(diccionario)

class MenuCopiado(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.avancebarra = 0
        self.avancetexto = "0%"
        self.popup_manager = ObjectProperty(None)

    def actualizar_avance(self, diccionario, porcentaje):
        self.ids.barra.value = porcentaje
        self.ids.porcentaje.text = str(self.ids.barra.value) + "%"
        if self.ids.barra.value == 100:
            self.popup_manager.get_screen('juegos_nuevos').mostrar_nuevos_juegos(diccionario)
            self.popup_manager.transition = NoTransition()
            self.popup_manager.current = 'juegos_nuevos'

class MenuConsolas(Screen):  
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id_consolas_actual = 0
        self.consolas = ["primeraconsola", "segundaconsola", "terceraconsola"]
        self.consolas_nombre = ["GBA", "SNES", "NES"]
        self.RUTA_RPI = "/home/sebas/roms"

    def obtener_nombre_consola(self):
        ruta_completa = os.path.join(self.RUTA_RPI, self.consolas_nombre[self.id_consolas_actual])
        self.manager.get_screen('MenuJuegos1').actualizar_lista_juegos(ruta_completa, self.consolas_nombre[self.id_consolas_actual])
        self.manager.current = 'MenuJuegos1'
        self.manager.transition.direction = "up" 

    def cambio_consolas_derecha(self):
        self.id_consolas_actual = (self.id_consolas_actual + 1) % len(self.consolas)
        self.ids.manager_centro.current = self.consolas[self.id_consolas_actual]
        self.ids.manager_centro.transition.direction = "left"

    def cambio_consolas_izquierda(self):
        self.id_consolas_actual = (self.id_consolas_actual - 1) % len(self.consolas)
        self.ids.manager_centro.current = self.consolas[self.id_consolas_actual]
        self.ids.manager_centro.transition.direction = "right"

class MenuJuegos(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.consola_actual = ""
        self.ruta_juegos = ""
        self.juego_activo = None 
    
    def actualizar_lista_juegos(self, ruta, consola):
        self.consola_actual = consola
        self.ruta_juegos = ruta
        self.ids.recycleview_juegos.cargar_juegos(ruta)

    def ejecutar_juego_seleccionado(self):
        juego = self.ids.recycleview_juegos.obtener_juego_actual()
        ruta_completa = os.path.join(self.ruta_juegos, juego)
        self.juego_activo = subprocess.run([
        "sudo", "openvt", "-c", "2", "-f", "-s", "--",
        "bash", "-c",
        f"export HOME=/home/sebas; export USER=sebas; cd /home/sebas; /usr/games/mednafen '{ruta_completa}'"])
        Clock.schedule_interval(lambda dt: self.verificar_juego_activo(self.juego_activo), 1)

    def verificar_juego_activo(self, proceso):
        if not proceso:
            return False
        
        if proceso.poll() is not None:
            self.juego_activo = None
            subprocess.call(["sudo", "openvt", "-c", "1", "-f", "-s"])
            return False
        
class ProyectoFinal(App):
    def build(self):
        Builder.load_file("ProyectoFinal.kv")
        Window.bind(on_joy_button_down=self.boton_presionado)
        Window.bind(on_joy_hat=self.gamepad_presionado)
        return WindowManager()

    def abrir_popup(self):
        self.popup_actual = EmuladorPopUp()
        self.popup_actual.bind(on_dismiss=self.limpiar_popup)
        self.popup_actual.open()
        self.menu_copiado = self.popup_actual.ids.barpro

    def abrir_popup_apagado(self):
        self.abrir_popup()
        self.popup_actual.ids.manager_popup.transition = NoTransition()
        self.popup_actual.ids.manager_popup.current = 'apagado'

    def limpiar_popup(self, *args):
        self.popup_actual = None

    def boton_presionado(self, window, stickid, buttonid):
        if hasattr(self, 'popup_actual') and self.popup_actual and self.popup_actual._window:
            if self.popup_actual.ids.manager_popup.current == 'juegos_nuevos': 
                if buttonid == 2: 
                    self.popup_actual.dismiss()
            elif self.popup_actual.ids.manager_popup.current == 'apagado': 
                if buttonid == 2:
                    self.popup_actual.apagar()
                elif buttonid == 1: 
                    self.popup_actual.dismiss()     

        elif self.root.current == 'MenuCaratula1':
            if buttonid == 9:
                self.root.current = 'MenuConsolas1'
                self.root.transition.direction = "up"
            elif buttonid == 8:
                self.abrir_popup_apagado() 
        elif self.root.current == 'MenuConsolas1':
            if buttonid == 2: 
                self.root.get_screen('MenuConsolas1').obtener_nombre_consola()  
            if buttonid == 1:
                self.root.transition.direction = "down"
                self.root.current = 'MenuCaratula1' 
            elif buttonid == 8:
                self.abrir_popup_apagado() 
        elif self.root.current == 'MenuJuegos1': 
            if buttonid == 1: 
                self.root.current = 'MenuConsolas1'
                self.root.transition.direction = "down" 
            elif buttonid == 2: 
                self.root.get_screen('MenuJuegos1').ejecutar_juego_seleccionado()
            elif buttonid == 8:
                self.abrir_popup_apagado() 
            
    def gamepad_presionado(self, window, stickid, axisid, value):
        if hasattr(self, 'popup_actual') and self.popup_actual and self.popup_actual._window:
            if self.popup_actual.ids.manager_popup.current == 'juegos_nuevos': 
                if value == (0,1):  
                    self.popup_actual.ids.juenue.ids.recycleview_nuevosjuegos.scroll_y = min(1.0, max(0.0, self.popup_actual.ids.juenue.ids.recycleview_nuevosjuegos.scroll_y + 0.2))
                elif value == (0,-1):  
                    self.popup_actual.ids.juenue.ids.recycleview_nuevosjuegos.scroll_y = min(1.0, max(0.0, self.popup_actual.ids.juenue.ids.recycleview_nuevosjuegos.scroll_y - 0.2))
  
        elif self.root.current == 'MenuConsolas1':
            if value == (-1,0):
                self.root.get_screen('MenuConsolas1').cambio_consolas_izquierda()
            if value == (1,0):
                self.root.get_screen('MenuConsolas1').cambio_consolas_derecha()  
        elif self.root.current == 'MenuJuegos1': 
            if value == (0,1): 
                nuevo_index = max(0, self.root.get_screen('MenuJuegos1').ids.recycleview_juegos.indice_seleccionado - 1)
                self.root.get_screen('MenuJuegos1').ids.recycleview_juegos.seleccionar_juego(nuevo_index)
            elif value == (0,-1): 
                nuevo_index = min(len(self.root.get_screen('MenuJuegos1').ids.recycleview_juegos.juegos) - 1, self.root.get_screen('MenuJuegos1').ids.recycleview_juegos.indice_seleccionado + 1)
                self.root.get_screen('MenuJuegos1').ids.recycleview_juegos.seleccionar_juego(nuevo_index)
 
def callback_progreso(diccionario, porcentaje):
    app = App.get_running_app()
    Clock.schedule_once(lambda dt: app.popup_actual.ids.manager_popup.get_screen('barra_progreso').actualizar_avance(diccionario, porcentaje))

def preparar_copiado():
    app = App.get_running_app()
    app.abrir_popup()
    app.popup_actual.ids.manager_popup.transition = NoTransition()
    app.popup_actual.ids.manager_popup.current = 'barra_progreso'

def detectar_usb():
    while True:
        usb_path, diccionario_juegos, nombre_USB = Manejador_USB.main()
        if diccionario_juegos:
            app = App.get_running_app()
            if app.root.get_screen('MenuJuegos1').juego_activo:
                app.root.get_screen('MenuJuegos1').juego_activo.terminate()
                app.root.get_screen('MenuJuegos1').juego_activo = None
                subprocess.call(["sudo", "openvt", "-c", "1", "-f", "-s"])
            Clock.schedule_once(lambda dt: preparar_copiado())
            Manejador_USB.copiar_juegos(diccionario_juegos, usb_path, nombre_USB, callback_progreso)

if __name__ == '__main__':
    hilo_usb = threading.Thread(target = detectar_usb, daemon = True)
    hilo_usb.start()
    ProyectoFinal().run()
