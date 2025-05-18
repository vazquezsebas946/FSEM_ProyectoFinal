# Copyright (c) 2025 Sebastián Vázquez
# This file is part of FSEM_ProyectoFinal and is licensed under the MIT License.
# See the LICENSE file in the root of this repository for details.

from collections import defaultdict
import os
#import pyudev
import time
import subprocess as sp
import shutil

destino = "/home/sebas/roms"

def auto_mount(path):
    args = ["udisksctl", "mount", "-b", path]
    sp.run(args)

def auto_unmount(path):
    args = ["udisksctl", "unmount", "-b", path]
    sp.run(args)

def get_mount_point(path):
    args = ["findmnt", "-unl", "-S", path]
    cp = sp.run(args, capture_output=True, text=True)
    out = cp.stdout.split(" ")[0]
    return out

def identificar_juegos(dir):
    archivos = [f for f in os.listdir(dir) if f.lower().endswith(('.gba', '.smc', '.nes'))]
    if archivos:
        por_consola = defaultdict(list)
        for juego in archivos:
            _, extension = os.path.splitext(juego)
            por_consola[extension.upper()].append(juego)
        if '.SMC' in por_consola:
            por_consola['.SNES'] = por_consola.pop('.SMC')
        return por_consola
    else:
        return archivos
    
def copiar_juegos(diccionario_por_consola, origen, nombre_dispositivo, callback_progreso=None):
    global destino
    if diccionario_por_consola:
        total_juegos = sum(len(juegos) for juegos in diccionario_por_consola.values())
        juegos_copiados = 0
        for consola, juegos in diccionario_por_consola.items():
            for nombre_juego in juegos:
                origen_completo = os.path.join(origen, nombre_juego)
                destino_unico = os.path.join(destino, consola[1:5], nombre_juego)
                with open(origen_completo, "rb") as fsrc, open(destino_unico, "wb") as fdst:
                    shutil.copyfileobj(fsrc, fdst, length=64 * 1024)
                juegos_copiados += 1
                porcentaje = int((juegos_copiados / total_juegos) * 100)

                if callback_progreso:
                    callback_progreso(diccionario_por_consola, porcentaje)
        auto_unmount("/dev/" + nombre_dispositivo)
    else:
        return

def main():
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem="block", device_type="partition")
    while True:
        action, device = monitor.receive_device()
        if action != "add":
            time.sleep(0.5)
            continue
        auto_mount("/dev/" + device.sys_name)
        mp = get_mount_point("/dev/" + device.sys_name)
        archivos_dicc = identificar_juegos(mp)
        return mp, archivos_dicc, device.sys_name