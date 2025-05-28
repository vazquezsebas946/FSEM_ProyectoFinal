if [ "$(tty)" = "/dev/tty1" ]; then
    clear > /dev/tty1
    sleep 0.1 
    source /home/sebas/entornovirtual/bin/activate
    python /home/sebas/entornovirtual/proyectofinal/main.py
fi