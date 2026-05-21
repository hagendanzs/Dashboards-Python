import os
import sys
import time
from pylogix import PLC

# Função interna para detectar a tecla ESC sem travar o loop (Non-blocking)
def esc_pressionado():
    if sys.platform == "win32":
        import msvcrt
        if msvcrt.kbhit():
            # 27 é o código ASCII para a tecla ESC
            return ord(msvcrt.getch()) == 27
    else:
        # Implementação para Linux / MacOS usando a biblioteca padrão
        import select
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            rlist, _, _ = select.select([sys.stdin], [], [], 0.0)
            if rlist:
                ch = sys.stdin.read(1)
                return ord(ch) == 27
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return False

# Configurações do CLP (Altere de acordo com o seu cenário)
IP_CLP = '172.16.35.30'
SLOT_CLP = 2

# Lista de tags fornecida para leitura
tags_para_ler = [
    'Timers[0].acc',
    'Conta[0].acc',
    'Conta[1].acc',
    'relogio[0]',
    'relogio[1]',
    'relogio[2]',
    'relogio[3]',
    'relogio[4]',
    'relogio[5]',
    'relogio[6]'
]

# Limpa o terminal antes de iniciar (ajuda na estética da tabela fixa)
os.system('cls' if os.name == 'nt' else 'clear')

print("=== Monitoramento Dinâmico Iniciado ===")
print("Pressione a tecla [ESC] a qualquer momento para encerrar.\n")

# Mantém o driver PLC aberto para máxima velocidade de comunicação
with PLC() as comm:
    comm.IPAddress = IP_CLP
    comm.ProcessorSlot = SLOT_CLP
    
    while True:
        # Verifica se o usuário pressionou ESC para sair do loop
        if esc_pressionado():
            print("\nLeitura encerrada pelo usuário.")
            break
            
        # Realiza a leitura em lote (Batch Read) das tags
        resultados = comm.Read(tags_para_ler)
        
        # Move o cursor do terminal para o topo para atualizar a tabela no mesmo lugar
        # Isso evita que o terminal fique rolando para baixo infinitamente
        print("\033[H", end="") 
        print("=== MONITORAMENTO EM TEMPO REAL ===")
        print(f"IP do CLP: {IP_CLP} | Pressione [ESC] para sair\n")
        
        # Cabeçalho da tabela formatado com espaçamentos fixos
        print(f"{'TagName':<20} | {'Value':<15} | {'Status'}")
        print("-" * 55)
        
        # Varre os resultados e preenche as linhas da tabela
        for resultado in resultados:
            valor_str = str(resultado.Value) if resultado.Value is not None else "N/A"
            print(f"{resultado.TagName:<20} | {valor_str:<15} | {resultado.Status}")
            
        # Pequeno atraso (delay) para não sobrecarregar a CPU e a rede do CLP
        # 0.1 segundos equivale a uma taxa de atualização de 10Hz
        time.sleep(0.1)
