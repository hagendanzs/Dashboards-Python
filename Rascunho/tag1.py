import os
import sys
import time
from pylogix import PLC
from art import text2art  # Importa o gerador de fontes ASCII

# [A função esc_pressionado() permanece exatamente igual ao script anterior]
def esc_pressionado():
    if sys.platform == "win32":
        import msvcrt
        if msvcrt.kbhit(): return ord(msvcrt.getch()) == 27
    else:
        import select, termios, tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            rlist, _, _ = select.select([sys.stdin], [], [], 0.0)
            if rlist: return ord(sys.stdin.read(1)) == 27
        finally: termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return False

IP_CLP = '172.16.35.30'
SLOT_CLP = 2
tags_para_ler = ['Conta[0].acc','Conta[1].acc','relogio[0]','relogio[1]','relogio[2]','relogio[3]','relogio[4]','relogio[5]']

os.system('cls' if os.name == 'nt' else 'clear')

with PLC() as comm:
    comm.IPAddress = IP_CLP
    comm.ProcessorSlot = SLOT_CLP
    
    while True:
        if esc_pressionado():
            print("\nLeitura encerrada.")
            break
            
        resultados = comm.Read(tags_para_ler)
        
        # Move o cursor para o topo
        print("\033[H", end="") 
        
        # GERANDO UM TÍTULO EM FONTE ESTILIZADA (Ex: Fonte tipo 'block' ou 'standard')
        # Você pode testar fontes como: 'block', 'caligraphy', 'banner3', 'digital'
        titulo_estilizado = text2art("CLP MONITOR", font='banner3')
        print(titulo_estilizado)
        
        print(f"IP: {IP_CLP} | Pressione [ESC] para sair\n")
        print(f"{'TagName':<20} | {'Value':<15} | {'Status'}")
        print("-" * 55)
        
        for resultado in resultados:
            valor_str = str(resultado.Value) if resultado.Value is not None else "N/A"
            print(f"{resultado.TagName:<20} | {valor_str:<15} | {resultado.Status}")
            
        time.sleep(0.1)
