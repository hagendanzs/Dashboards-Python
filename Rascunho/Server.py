import paramiko
import os
import time
import msvcrt  # Teclado para Windows

# Importações da biblioteca Rich
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich.live import Live

# ==============================================================================
# CONFIGURAÇÕES DE ACESSO AO SERVIDOR LINUX (ASH/BUSYBOX)
# ==============================================================================
SSH_HOST = "172.16.35.1"  
SSH_USER = "root"    
SSH_PASS = "h4rdFlip"      

console = Console()
ULTIMO_ERRO = ""  # Armazena o erro real para exibir no painel se algo falhar

def obter_uso_cpu_real(ssh):
    """Calcula o uso real da CPU comparando dois estados do /proc/stat"""
    global ULTIMO_ERRO
    try:
        stdin, stdout, stderr = ssh.exec_command("cat /proc/stat")
        cpu1 = stdout.readline().strip().split()
        
        time.sleep(0.5) # Intervalo curto para medir a variação de ciclos
        
        stdin, stdout, stderr = ssh.exec_command("cat /proc/stat")
        cpu2 = stdout.readline().strip().split()
        
        if not cpu1 or not cpu2 or cpu1[0] != 'cpu' or cpu2[0] != 'cpu':
            return 0.0
            
        cpu1_valores = [int(x) for x in cpu1[1:]]
        cpu2_valores = [int(x) for x in cpu2[1:]]
        
        total1 = sum(cpu1_valores)
        idle1 = cpu1_valores[3]  # O índice 3 é o tempo ocioso (idle)
        
        total2 = sum(cpu2_valores)
        idle2 = cpu2_valores[3]
        
        diff_total = total2 - total1
        diff_idle = idle2 - idle1
        
        if diff_total == 0:
            return 0.0
            
        porcentagem = (1.0 - (diff_idle / diff_total)) * 100
        return round(porcentagem, 2)
    except Exception as e:
        ULTIMO_ERRO = f"Erro no cálculo de CPU: {e}"
        return 0.0

def coletar_dados_servidor(host, usuario, senha):
    global ULTIMO_ERRO
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, username=usuario, password=senha, timeout=3)
        
        # 1. Primeiro calculamos o uso real da CPU
        uso_cpu = obter_uso_cpu_real(ssh)
        
        # 2. Executa as demais métricas sem usar comandos pesados ou 'bc'
        comando_demais_metricas = (
            "cat /proc/sys/kernel/hostname ; "
            "cat /proc/meminfo | grep -E 'MemTotal|MemAvailable|MemFree' | awk '{print $2}' | tr '\\n' '|' ; echo ; "
            "df -h / | awk 'NR==2 {print $5}' || df -h / | awk 'NR==3 {print $4}' ; "
            "interface=$(ip route | grep default | awk '{print $5}') ; "
            "cat /proc/net/dev | grep \"$interface\" | awk '{print $2\"|\"$10}'"
        )
        
        stdin, stdout, stderr = ssh.exec_command(comando_demais_metricas)
        linhas = [linha.strip() for list_item in stdout.readlines() if (linha := list_item.strip())]
        erro_remoto = stderr.read().decode().strip()
        
        if erro_remoto:
            ULTIMO_ERRO = f"Erro remoto do comando: {erro_remoto}"
            return None

        if len(linhas) < 4:
            ULTIMO_ERRO = f"Resposta incompleta do servidor. Linhas recebidas: {len(linhas)}"
            return None
            
        # CORREÇÃO CRÍTICA: Adicionados os índices [0], [1], [2], [3] corretos para o fatiamento
        hostname = linhas[0]

        # Parse da Memória
        dados_mem = linhas[1].split('|')
        mem_total_kb = float(dados_mem[0])
        # Nem todo sistema compactado tem MemAvailable, se falhar usa MemFree (índice 1)
        mem_livre_kb = float(dados_mem[1]) if dados_mem[1] else float(dados_mem[2])
        mem_usada_kb = mem_total_kb - mem_livre_kb
        perc_mem = (mem_usada_kb / mem_total_kb) * 100
        tamanho_memoria = f"{mem_total_kb / (1024**2):.2f} GB"
        
        # Parse do Disco
        uso_disco_root = linhas[2]
        
        # Parse da Rede
        bytes_in, bytes_out = linhas[3].split('|')
        dados_in = f"{float(bytes_in) / (1024**2):.2f} MB"
        dados_out = f"{float(bytes_out) / (1024**2):.2f} MB"
        
        ULTIMO_ERRO = "" # Limpa erros antigos se tudo funcionou
        return {
            "IP": host,
            "HOSTNAME": hostname,
            "USO_CPU": uso_cpu,
            "USO_MEMORIA": round(perc_mem, 2),
            "TAMANHO_MEMORIA": tamanho_memoria,
            "DISCO_ROOT_OCUPADO": uso_disco_root,
            "REDE_DADOS_IN_TOTAL": dados_in,
            "REDE_DADOS_OUT_TOTAL": dados_out
        }
    except Exception as e:
        ULTIMO_ERRO = f"Falha de Conexão/Script: {e}"
        return None
    finally:
        ssh.close()

def gerar_layout_dashboard(dados):
    """Gera a interface gráfica colorida baseada nos dados recebidos"""
    
    header_text = Text("📊 TELEMETRIA LINUX EM TEMPO REAL", style="bold white on blue", justify="center")
    header_panel = Panel(header_text, style="blue")
    
    if not dados:
        # Exibe o erro real na tela para sabermos exatamente o que quebrou
        erro_formatado = f"\n⚠️ Falha ao coletar dados do servidor.\n\n[bold yellow]Motivo:[/bold yellow] {ULTIMO_ERRO}\n"
        return Panel(Text(erro_formatado, style="bold red", justify="center"), title="Status do Sistema", border_style="red")

    cor_cpu = "green" if dados["USO_CPU"] < 50 else "yellow" if dados["USO_CPU"] < 80 else "bold red"
    cor_mem = "green" if dados["USO_MEMORIA"] < 70 else "yellow" if dados["USO_MEMORIA"] < 90 else "bold red"
    
    tabela = Table(show_header=True, header_style="bold cyan", expand=True, box=None)
    tabela.add_column("Métrica", style="bold white", width=25)
    tabela.add_column("Valor Atual", justify="right")

    tabela.add_row("Nome do Host (HOSTNAME)", f"[bold magenta]{dados['HOSTNAME']}[/bold magenta]")
    tabela.add_row("Endereço IP", f"[cyan]{dados['IP']}[/cyan]")
    tabela.add_row("Uso de Processador (CPU)", f"[{cor_cpu}]{dados['USO_CPU']}%[/{cor_cpu}]")
    tabela.add_row("Uso de Memória RAM", f"[{cor_mem}]{dados['USO_MEMORIA']}%[/{cor_mem}] (Total: {dados['TAMANHO_MEMORIA']})")
    tabela.add_row("Armazenamento (Disco /)", f"[yellow]{dados['DISCO_ROOT_OCUPADO']}[/yellow]")
    tabela.add_row("Tráfego de Rede (Download)", f"[blue]⬇ {dados['REDE_DADOS_IN_TOTAL']}[/blue]")
    tabela.add_row("Tráfego de Rede (Upload)", f"[blue]⬆ {dados['REDE_DADOS_OUT_TOTAL']}[/blue]")

    conteudo_completo = Layout()
    conteudo_completo.split_column(
        Layout(header_panel, size=3),
        Layout(Panel(tabela, title="Status dos Recursos", border_style="cyan"))
    )
    
    return conteudo_completo

# ==============================================================================
# LAÇO PRINCIPAL DE ATUALIZAÇÃO
# ==============================================================================
if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    
    with Live(gerar_layout_dashboard(None), refresh_per_second=1, screen=True) as live:
        while True:
            if msvcrt.kbhit():
                tecla = msvcrt.getch()
                if tecla == b'\x1b':  
                    break
            
            dados_atuais = coletar_dados_servidor(SSH_HOST, SSH_USER, SSH_PASS)
            live.update(gerar_layout_dashboard(dados_atuais))
            time.sleep(0.5)
            
    print("\n[bold green]Painel encerrado com sucesso![/bold green]")
