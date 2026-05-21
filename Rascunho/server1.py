import paramiko
import os
import time
import msvcrt  # Teclado para Windows

# Importações avançadas da biblioteca Rich para gráficos e layouts
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich.live import Live
from rich.columns import Columns

# ==============================================================================
# CONFIGURAÇÕES DE ACESSO AO SERVIDOR LINUX (ASH/BUSYBOX)
# ==============================================================================
SSH_HOST = "172.16.35.1"  
SSH_USER = "root"    
SSH_PASS = "h4rdFlip"      

console = Console()
ULTIMO_ERRO = "" 

def obter_uso_cpu_real(ssh):
    global ULTIMO_ERRO
    try:
        stdin, stdout, stderr = ssh.exec_command("cat /proc/stat")
        cpu1 = stdout.readline().strip().split()
        
        time.sleep(0.5) 
        
        stdin, stdout, stderr = ssh.exec_command("cat /proc/stat")
        cpu2 = stdout.readline().strip().split()
        
        if not cpu1 or not cpu2 or cpu1[0] != 'cpu' or cpu2[0] != 'cpu':
            return 0.0
            
        cpu1_valores = [int(x) for x in cpu1[1:]]
        cpu2_valores = [int(x) for x in cpu2[1:]]
        
        total1 = sum(cpu1_valores)
        idle1 = cpu1_valores[3]
        
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
        uso_cpu = obter_uso_cpu_real(ssh)
        
        comando_demais_metricas = (
            "cat /proc/sys/kernel/hostname ; "
            "cat /proc/meminfo | grep -E 'MemTotal|MemAvailable|MemFree' | awk '{print $2}' | tr '\\n' '|' ; echo ; "
            "df -h / | awk 'NR==2 {print $5}' || df -h / | awk 'NR==3 {print $4}' ; "
            "interface=$(ip route | grep default | awk '{print $5}') ; "
            "cat /proc/net/dev | grep \"$interface\" | awk '{print $2\"|\"$10}'"
        )
        
        stdin, stdout, stderr = ssh.exec_command(comando_demais_metricas)
        linhas = [linha.strip() for list_item in stdout.readlines() if (linha := list_item.strip())]
        
        if len(linhas) < 4:
            ULTIMO_ERRO = f"Resposta incompleta do servidor."
            return None
            
        hostname = linhas[0]

        # Parse da Memória
        dados_mem = linhas[1].split('|')
        mem_total_kb = float(dados_mem[0])
        mem_livre_kb = float(dados_mem[2]) if dados_mem[2] else float(dados_mem[1])
        mem_usada_kb = mem_total_kb - mem_livre_kb
        perc_mem = (mem_usada_kb / mem_total_kb) * 100
        tamanho_memoria = f"{mem_total_kb / (1024**2):.2f} GB"
        
        # Parse do Disco
        uso_disco_root_str = linhas[2].replace('%', '')
        perc_disco = float(uso_disco_root_str)
        
        # Parse da Rede
        bytes_in, bytes_out = linhas[3].split('|')
        dados_in = f"{float(bytes_in) / (1024**2):.2f} MB"
        dados_out = f"{float(bytes_out) / (1024**2):.2f} MB"
        
        return {
            "IP": host,
            "HOSTNAME": hostname,
            "USO_CPU": uso_cpu,
            "USO_MEMORIA": round(perc_mem, 2),
            "TAMANHO_MEMORIA": tamanho_memoria,
            "DISCO_ROOT_PERC": perc_disco,
            "REDE_DADOS_IN_TOTAL": dados_in,
            "REDE_DADOS_OUT_TOTAL": dados_out
        }
    except Exception as e:
        ULTIMO_ERRO = f"Falha de Conexão/Script: {e}"
        return None
    finally:
        ssh.close()

def desenhar_barra(porcentagem, cor):
    """Gera uma barra gráfica horizontal baseada na porcentagem fornecida"""
    largura_maxima = 20
    blocos_preenchidos = int((porcentagem / 100) * largura_maxima)
    blocos_vazios = largura_maxima - blocos_preenchidos
    
    barra = f"[{cor}]" + "█" * blocos_preenchidos + "[/]"
    barra += "[grey37]" + "░" * blocos_vazios + "[/]"
    return f"{barra} [bold {cor}]{porcentagem}%[/]"

def gerar_layout_dashboard(dados):
    """Gera a interface avançada com gráficos em colunas divididas"""
    
    # Cabeçalho Superior
    header_text = Text("📊 DASHBOARD DE TELEMETRIA EM TEMPO REAL", style="bold white on navy_blue", justify="center")
    header_panel = Panel(header_text, style="blue", padding=(0, 1))
    
    if not dados:
        erro_formatado = f"\n⚠️ Conectando ao Servidor...\n\n[bold yellow]Status:[/bold yellow] {ULTIMO_ERRO}\n"
        return Panel(Text(erro_formatado, style="bold red", justify="center"), title="Status do Sistema", border_style="red")

    # Cores inteligentes para os gráficos
    cor_cpu = "green" if dados["USO_CPU"] < 50 else "yellow" if dados["USO_CPU"] < 80 else "red"
    cor_mem = "green" if dados["USO_MEMORIA"] < 70 else "yellow" if dados["USO_MEMORIA"] < 90 else "red"
    cor_disco = "green" if dados["DISCO_ROOT_PERC"] < 75 else "yellow" if dados["DISCO_ROOT_PERC"] < 90 else "red"

    # --- COLUNA DA ESQUERDA: GRÁFICOS EM BARRAS ---
    layout_graficos = Table(show_header=False, expand=True, box=None)
    layout_graficos.add_row("[bold white]Uso de CPU[/bold white]")
    layout_graficos.add_row(desenhar_barra(dados["USO_CPU"], cor_cpu))
    layout_graficos.add_row("")  # Linha em branco para espaçamento
    layout_graficos.add_row("[bold white]Uso de Memória RAM[/bold white]")
    layout_graficos.add_row(desenhar_barra(dados["USO_MEMORIA"], cor_mem))
    layout_graficos.add_row("")
    layout_graficos.add_row("[bold white]Armazenamento (Disco /)[/bold white]")
    layout_graficos.add_row(desenhar_barra(dados["DISCO_ROOT_PERC"], cor_disco))

    painel_graficos = Panel(layout_graficos, title="📊 Gráficos de Carga", border_style="cyan")

    # --- COLUNA DA DIREITA: INFORMAÇÕES TEXTUAIS E REDE ---
    layout_info = Table(show_header=False, expand=True, box=None)
    layout_info.add_row("[bold cyan]Servidor:[/bold cyan]", f"[bold magenta]{dados['HOSTNAME']}[/bold magenta]")
    layout_info.add_row("[bold cyan]IP Remoto:[/bold cyan]", f"{dados['IP']}")
    layout_info.add_row("[bold cyan]Total RAM:[/bold cyan]", f"{dados['TAMANHO_MEMORIA']}")
    layout_info.add_row("", "")  # Espaçamento
    layout_info.add_row("[bold green]⬇ Rede (Download):[/bold green]", f"[bold white]{dados['REDE_DADOS_IN_TOTAL']}[/bold white]")
    layout_info.add_row("[bold orange3]⬆ Rede (Upload):[/bold orange3]", f"[bold white]{dados['REDE_DADOS_OUT_TOTAL']}[/bold white]")

    painel_info = Panel(layout_info, title="ℹ️ Detalhes e Rede", border_style="magenta")

    # --- JUNÇÃO DO LAYOUT (Lado a Lado) ---
    # Dividimos a tela ao meio usando Columns
    corpo_dashboard = Columns([painel_graficos, painel_info], expand=True)

    layout_final = Layout()
    layout_final.split_column(
        Layout(header_panel, size=3),
        Layout(corpo_dashboard)
    )
    
    return layout_final

# ==============================================================================
# LAÇO PRINCIPAL DE ATUALIZAÇÃO
# ==============================================================================
if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    
    with Live(gerar_layout_dashboard(None), refresh_per_second=2, screen=True) as live:
        while True:
            if msvcrt.kbhit():
                tecla = msvcrt.getch()
                if tecla == b'\x1b':  
                    break
            
            dados_atuais = coletar_dados_servidor(SSH_HOST, SSH_USER, SSH_PASS)
            live.update(gerar_layout_dashboard(dados_atuais))
            time.sleep(0.3)
            
    print("\n[bold green]Painel encerrado com sucesso![/bold green]")
